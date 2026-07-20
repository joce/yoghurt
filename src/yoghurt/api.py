"""Public synchronous yoghurt API.

Yahoo's shared ``lang``/``region`` wire params ride their CommandSpec
defaults; per-call overrides are deliberately unexposed (YAGNI — no caller
has needed one; revisit if a real need appears). Parameter names mirror the
CLI's command metadata, except booleans whose CLI flag inverts the wire
value — those use the wire name so the kwarg's meaning matches its effect.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Final, TypeAlias

import polars as pl

from yoghurt import _core
from yoghurt._bridge import run
from yoghurt.commands import COMMANDS_BY_NAME
from yoghurt.exceptions import SymbolNotFoundError, YahooApiError
from yoghurt.frames import Chart, Frame, History, Spark, Timeseries
from yoghurt.history import HISTORY_REQUEST_BATCH_SIZE
from yoghurt.history import concat_frames as concat_history_frames
from yoghurt.history import frame_from_chart_result as history_frame_from_result
from yoghurt.history import request_values as history_request_values
from yoghurt.models import (
    AnalystResult,
    CalendarEventsResult,
    ChartEvents,
    ChartMeta,
    Insights,
    MarketInfoResult,
    MarketSummaryQuote,
    MarketTimeResult,
    OptionChain,
    PriceInsights,
    Quote,
    QuoteSummary,
    QuoteTypeResult,
    RecommendationsResult,
    ScreenerDiscoverResult,
    ScreenerInstrumentFieldsResult,
    ScreenerPredefinedResult,
    SectorResult,
    StockRecommenderResult,
    TimeseriesFieldsResult,
    TopRatingsResult,
    TrendingResult,
    validate_model,
)
from yoghurt.tabular import (
    TabularShapeError,
    build_chart_frame,
    build_spark_frame,
    build_tabular_frame,
    build_timeseries_frames,
    collect_column_data,
    extract_chart_columns,
    parse_tabular_payload,
    reject_nested_cells,
    resolve_column_order,
)

if TYPE_CHECKING:
    from datetime import date

    from yoghurt.types import ParamValue

DateLike: TypeAlias = "int | str | date | datetime"


def _values(**kwargs: object) -> dict[str, object]:
    """Drop unset (None) kwargs; keys are wire param names.

    Returns:
        dict[str, object]: The present (non-``None``) keyword arguments.
    """

    return {key: value for key, value in kwargs.items() if value is not None}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _chart_from_payload(payload: dict[str, Any], fetched_at: datetime) -> Chart:
    """Build one typed Chart from a decoded endpoint payload.

    Returns:
        Chart: The typed bars, meta, and events.

    Raises:
        YahooApiError: If bars cannot be flattened or models cannot validate.
    """

    result = payload["chart"]["result"][0]
    try:
        timestamps, columns = extract_chart_columns(result)
        df = build_chart_frame(timestamps, columns)
    except TabularShapeError as exc:
        raise YahooApiError(code="malformed-response", description=str(exc)) from exc
    meta = validate_model(ChartMeta, result.get("meta", {}))
    raw_events = result.get("events")
    chart_events = validate_model(ChartEvents, raw_events) if raw_events else None
    return Chart(df=df, fetched_at=fetched_at, meta=meta, events=chart_events)


class Ticker:
    """Symbol-bound entry point; every method performs one HTTP call."""

    def __init__(self, symbol: str) -> None:
        """Bind the ticker to one Yahoo symbol (no I/O)."""

        self.symbol = symbol.strip()

    def __repr__(self) -> str:
        return f"Ticker({self.symbol!r})"

    def quote(  # noqa: PLR0913 - one keyword-only arg per quote wire param.
        self,
        *,
        fields: list[str] | None = None,
        formatted: bool | None = None,
        enable_private_company: bool | None = None,
        overnight_price: bool | None = None,
        top_pick_this_month: bool | None = None,
        img_heights: int | None = None,
        img_labels: list[str] | None = None,
        img_widths: int | None = None,
    ) -> Quote:
        """Fetch this symbol's quote record.

        ``enable_private_company=True`` includes private-company quote
        matches; ``overnight_price=True`` requests overnight price fields.

        Returns:
            Quote: The validated quote record.

        Raises:
            SymbolNotFoundError: If Yahoo returns no record for the symbol.
        """

        payload = run(
            _core.call_endpoint(
                "quote",
                symbol=self.symbol,
                values=_values(
                    symbols=self.symbol,
                    fields=fields,
                    formatted=formatted,
                    enablePrivateCompany=enable_private_company,
                    overnightPrice=overnight_price,
                    topPickThisMonth=top_pick_this_month,
                    imgHeights=img_heights,
                    imgLabels=img_labels,
                    imgWidths=img_widths,
                ),
            )
        )
        results = payload["quoteResponse"]["result"]
        if not results:
            raise SymbolNotFoundError(self.symbol)
        return validate_model(Quote, results[0])

    def chart(  # noqa: PLR0913 - one keyword-only arg per chart wire param.
        self,
        *,
        period1: DateLike | None = None,
        period2: DateLike | None = None,
        range: str | None = None,  # noqa: A002 - mirrors Yahoo's wire/CLI name
        interval: str | None = None,
        events: list[str] | None = None,
        include_pre_post: bool | None = None,
    ) -> Chart:
        """Fetch OHLCV bars.

        An unknown symbol raises ``SymbolNotFoundError`` via the shared
        error mapping (Yahoo answers with an enveloped 404; corpus:
        ``chart/ZZZZXYZQ.json``) before this method sees the payload.

        Returns:
            Chart: Typed bars frame plus the typed chart meta and (when
            requested) events blocks.

        Malformed bars surface as ``YahooApiError(code="malformed-response")``;
        invalid meta/events models use ``code="model-validation"``.
        """

        payload = run(
            _core.call_endpoint(
                "chart",
                symbol=self.symbol,
                values=_values(
                    symbol=self.symbol,
                    period1=period1,
                    period2=period2,
                    range=range,
                    interval=interval,
                    events=events,
                    includePrePost=include_pre_post,
                ),
            )
        )
        return _chart_from_payload(payload, _now_utc())

    def history(
        self,
        *,
        period: str | None = None,
        start: DateLike | None = None,
        end: DateLike | None = None,
        interval: str = "1d",
        include_pre_post: bool = False,
    ) -> History:
        """Fetch analysis-ready, corporate-action-adjusted OHLCV history.

        With no date arguments, the window defaults to one month. ``period``
        accepts Yahoo's relative ranges; use ``start`` and optional ``end``
        for an explicit window. Supported intervals are daily or coarser because
        Yahoo omits adjusted close from intraday responses. No heuristic price
        repair is applied.

        Returns:
            History: A long-form adjusted table with this ticker's symbol.
        """

        return history(
            [self.symbol],
            period=period,
            start=start,
            end=end,
            interval=interval,
            include_pre_post=include_pre_post,
        )

    def spark(  # noqa: PLR0913 - one keyword-only arg per spark wire param.
        self,
        *,
        range: str | None = None,  # noqa: A002 - mirrors Yahoo's wire/CLI name
        interval: str | None = None,
        indicators: list[str] | None = None,
        include_timestamps: bool | None = None,
        include_pre_post: bool | None = None,
        cors_domain: str | None = None,
        tsrc: str | None = None,
    ) -> Spark:
        """Fetch the sparkline price series for this symbol.

        The spark response nests per-symbol data as
        ``spark.result[].response[]``; this unwraps that shape into a typed
        single-column (``close``) :class:`~yoghurt.frames.Spark` frame.

        Returns:
            Spark: Typed close-price series plus the typed chart meta block.

        Raises:
            SymbolNotFoundError: If Yahoo returns no record for the symbol.
            YahooApiError: If the response cannot be flattened into the
                fixed ``close`` schema (code ``"malformed-response"``), or
                if the meta block fails model validation (code
                ``"model-validation"``).
        """

        payload = run(
            _core.call_endpoint(
                "spark",
                symbol=self.symbol,
                values=_values(
                    symbols=self.symbol,
                    range=range,
                    interval=interval,
                    indicators=indicators,
                    includeTimestamps=include_timestamps,
                    includePrePost=include_pre_post,
                    corsDomain=cors_domain,
                    **{".tsrc": tsrc},
                ),
            )
        )
        results = payload["spark"]["result"]
        if not results:
            raise SymbolNotFoundError(self.symbol)
        responses = results[0]["response"]
        if not responses:
            raise SymbolNotFoundError(self.symbol)
        response = responses[0]
        try:
            df = build_spark_frame(response)
        except TabularShapeError as exc:
            raise YahooApiError(
                code="malformed-response", description=str(exc)
            ) from exc
        meta = validate_model(ChartMeta, response.get("meta", {}))
        return Spark(df=df, fetched_at=_now_utc(), meta=meta)

    def quote_type(
        self,
        *,
        formatted: bool | None = None,
        enable_private_company: bool | None = None,
        overnight_price: bool | None = None,
    ) -> QuoteTypeResult:
        """Fetch instrument classification metadata for this symbol.

        ``enable_private_company=True`` includes private-company data;
        ``overnight_price=True`` requests overnight price fields.

        Returns:
            QuoteTypeResult: The validated quoteType record.

        Raises:
            SymbolNotFoundError: If Yahoo returns no record for the symbol.
        """

        payload = run(
            _core.call_endpoint(
                "quote-type",
                symbol=self.symbol,
                values=_values(
                    symbol=self.symbol,
                    formatted=formatted,
                    enablePrivateCompany=enable_private_company,
                    overnightPrice=overnight_price,
                ),
            )
        )
        results = payload["quoteType"]["result"]
        if not results:
            raise SymbolNotFoundError(self.symbol)
        return validate_model(QuoteTypeResult, results[0])

    def quote_summary(
        self,
        *,
        modules: list[str] | None = None,
        formatted: bool | None = None,
        enable_private_company: bool | None = None,
        enable_qsp_expanded_earnings: bool | None = None,
        overnight_price: bool | None = None,
    ) -> QuoteSummary:
        """Fetch quoteSummary modules for this symbol.

        ``enable_private_company=True`` includes private-company data;
        ``enable_qsp_expanded_earnings=True`` requests Yahoo's expanded
        earnings fields; ``overnight_price=True`` requests overnight price
        fields.

        ``balance_sheet_history``/``balance_sheet_history_quarterly`` and
        ``cashflow_statement_history``/``cashflow_statement_history_quarterly``
        carry only ``end_date``/``max_age`` (cashflow: plus ``net_income``)
        in the corpus this was typed against — Yahoo does not currently
        populate line items on these modules; see
        ``yoghurt.models.summary_statements``.

        Returns:
            QuoteSummary: The validated quote-summary record, with one
            optional field per requested (and applicable) module.

        Raises:
            SymbolNotFoundError: If Yahoo returns no record for the symbol.
        """

        payload = run(
            _core.call_endpoint(
                "quote-summary",
                symbol=self.symbol,
                values=_values(
                    symbol=self.symbol,
                    modules=modules,
                    formatted=formatted,
                    enablePrivateCompany=enable_private_company,
                    enableQSPExpandedEarnings=enable_qsp_expanded_earnings,
                    overnightPrice=overnight_price,
                ),
            )
        )
        results = payload["quoteSummary"]["result"]
        if not results:
            raise SymbolNotFoundError(self.symbol)
        return validate_model(QuoteSummary, results[0])

    def options(
        self,
        *,
        date: DateLike | None = None,
        formatted: bool | None = None,
        straddle: bool | None = None,
    ) -> OptionChain:
        """Fetch the option chain for this symbol.

        Returns:
            OptionChain: The validated option chain record, including the
            underlying security's typed :class:`~yoghurt.models.Quote`.

        Raises:
            SymbolNotFoundError: If Yahoo returns no record for the symbol.
        """

        payload = run(
            _core.call_endpoint(
                "options",
                symbol=self.symbol,
                values=_values(
                    symbol=self.symbol,
                    date=date,
                    formatted=formatted,
                    straddle=straddle,
                ),
            )
        )
        results = payload["optionChain"]["result"]
        if not results:
            raise SymbolNotFoundError(self.symbol)
        return validate_model(OptionChain, results[0])

    def timeseries(
        self,
        *,
        type: list[str] | None = None,  # noqa: A002 - mirrors Yahoo's wire/CLI name
        period1: DateLike | None = None,
        period2: DateLike | None = None,
        merge: bool | None = None,
        pad_time_series: bool | None = None,
    ) -> Timeseries:
        """Fetch fundamentals timeseries for this symbol as typed frames.

        ``pad_time_series=True`` asks Yahoo to pad missing timeseries values.

        Known Yahoo-side bug: requesting the ``spEarningsReleaseEvents``
        type currently fails with ``YahooApiError`` (code
        ``"malformed-response"``) because Yahoo serves invalid JSON for
        this type — for every symbol, even when it is requested alone. A
        request bundling it with other types fails wholesale, so keep it
        out of ``type`` lists until Yahoo fixes the feed.

        Returns:
            Timeseries: Four typed frames (fundamentals, geographic
            segments, economic events, analyst ratings) plus the
            ``empty_types``/``unrecognized_types`` bookkeeping tuples.

        Raises:
            YahooApiError: If the response cannot be flattened into the
                fixed timeseries schemas (code ``"malformed-response"``).
        """

        payload = run(
            _core.call_endpoint(
                "timeseries",
                symbol=self.symbol,
                values=_values(
                    symbol=self.symbol,
                    type=type,
                    period1=period1,
                    period2=period2,
                    merge=merge,
                    padTimeSeries=pad_time_series,
                ),
            )
        )
        try:
            tables = build_timeseries_frames(payload)
        except TabularShapeError as exc:
            raise YahooApiError(
                code="malformed-response", description=str(exc)
            ) from exc
        fetched_at = _now_utc()
        return Timeseries(
            fundamentals=Frame(df=tables.fundamentals, fetched_at=fetched_at),
            geographic_segments=Frame(
                df=tables.geographic_segments, fetched_at=fetched_at
            ),
            economic_events=Frame(df=tables.economic_events, fetched_at=fetched_at),
            analyst_ratings=Frame(df=tables.analyst_ratings, fetched_at=fetched_at),
            empty_types=tables.empty_types,
            unrecognized_types=tables.unrecognized_types,
            fetched_at=fetched_at,
        )

    def calendar_events(  # noqa: PLR0913 - one keyword-only arg per event filter.
        self,
        *,
        modules: list[str] | None = None,
        count_per_day: int | None = None,
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
        economic_events_high_importance_only: bool | None = None,
        economic_events_region_filter: str | None = None,
    ) -> CalendarEventsResult:
        """Fetch earnings, IPO, economic, and SEC filing events for this symbol.

        ``economic_events_high_importance_only=True`` limits economic events
        to high-importance ones. ``modules`` selects which event family the
        result populates; unrequested families are ``None``. ``earnings``/
        ``ipoEvents``/``secReports`` are empty unless ``start_date``/
        ``end_date`` cover a day the symbol actually had that kind of event
        on; the default (window-less) request is always empty for all three
        — live-confirmed 2026-07-05 (corpus:
        ``calendar-events/IVF_earnings.json`` and siblings). An unrecognized
        symbol is not an error: Yahoo returns the same valid-empty
        ``{"earnings": []}`` shape as a recognized symbol with no scheduled
        events, so this returns a normally-typed (all-``None``-but-
        ``earnings``) result rather than raising (corpus:
        ``calendar-events/ZZZZXYZQ.json``).

        Returns:
            CalendarEventsResult: The validated calendar-events record.
        """

        payload = run(
            _core.call_endpoint(
                "calendar-events",
                symbol=self.symbol,
                values=_values(
                    tickersFilter=self.symbol,
                    modules=modules,
                    countPerDay=count_per_day,
                    startDate=start_date,
                    endDate=end_date,
                    economicEventsHighImportanceOnly=(
                        economic_events_high_importance_only
                    ),
                    economicEventsRegionFilter=economic_events_region_filter,
                ),
            )
        )
        return validate_model(CalendarEventsResult, payload["finance"]["result"])

    def analyst(self, *, debug_flag: bool | None = None) -> AnalystResult:
        """Fetch analyst intelligence for this symbol.

        The corpus has no captured thin-but-valid shape for this endpoint,
        so an unrecognized symbol surfaces as a model-validation failure
        rather than ``SymbolNotFoundError`` (Yahoo's own not-found body is
        already mapped by ``_core.map_http_error``).

        Returns:
            AnalystResult: The validated analyst record.
        """

        payload = run(
            _core.call_endpoint(
                "analyst",
                symbol=self.symbol,
                values=_values(symbol=self.symbol, debug_flag=debug_flag),
            )
        )
        return validate_model(AnalystResult, payload)

    def ratings_top(
        self, *, exclude_noncurrent: bool | None = None
    ) -> TopRatingsResult:
        """Fetch top analyst rating buckets for this symbol.

        ``exclude_noncurrent=True`` drops non-current analyst records from
        the top scored buckets. An unrecognized symbol raises
        ``SymbolNotFoundError``: Yahoo's 404 body (``{"detail": "No top
        ratings found for symbol: ..."}``) is mapped by
        ``yoghurt._core.map_http_error`` — confirmed live 2026-07-05,
        corpus: ``ratings-top/ZZZZXYZQ.json``.

        Returns:
            TopRatingsResult: The validated top-ratings record.
        """

        payload = run(
            _core.call_endpoint(
                "ratings-top",
                symbol=self.symbol,
                values=_values(
                    symbol=self.symbol, exclude_noncurrent=exclude_noncurrent
                ),
            )
        )
        return validate_model(TopRatingsResult, payload)

    def price_insights(
        self,
        *,
        modules: list[str] | None = None,
        ai_modules: list[str] | None = None,
        check_anomaly: bool | None = None,
    ) -> PriceInsights:
        """Fetch AI-generated price insights for this symbol.

        ``modules``/``ai_modules`` narrow which blocks Yahoo populates;
        unrequested blocks are ``None``. ``check_anomaly=True`` requests
        Yahoo's price-anomaly detection. An unrecognized symbol is not an
        error: Yahoo returns HTTP 200 with a fully-shaped record (every
        top-level block present, ``has_price_anomaly=True``, empty
        news/analyst-rating/AI-analysis content) rather than a 404 or an
        empty result, so this never raises for a bad symbol — confirmed
        live 2026-07-05, corpus: ``price-insights/ZZZZXYZQ.json``.

        Returns:
            PriceInsights: The validated price-insights record.
        """

        payload = run(
            _core.call_endpoint(
                "price-insights",
                symbol=self.symbol,
                values=_values(
                    symbols=self.symbol,
                    modules=modules,
                    aiModules=ai_modules,
                    checkAnomaly=check_anomaly,
                ),
            )
        )
        record = payload["finance"]["result"].get(self.symbol, {})
        return validate_model(PriceInsights, record)

    def insights(
        self,
        *,
        disable_related_reports: bool | None = None,
        formatted: bool | None = None,
        get_all_research_reports: bool | None = None,
        reports_count: int | None = None,
        ssl: bool | None = None,
    ) -> Insights:
        """Fetch research reports and insights for this symbol.

        ``disable_related_reports=True`` omits related research reports;
        ``get_all_research_reports=True`` requests all available research
        reports; ``ssl=True`` requests SSL URLs in Yahoo response fields.
        An unrecognized symbol is not an error: Yahoo returns the same thin
        ``{"sigDevs": [], "symbol": ...}`` shape it sends for any symbol
        outside its analysis coverage (index/crypto/forex/futures symbols
        get this same thin shape live), so this never raises for a bad
        symbol — confirmed live 2026-07-05, corpus:
        ``insights/ZZZZXYZQ.json``.

        Returns:
            Insights: The validated insights record.
        """

        payload = run(
            _core.call_endpoint(
                "insights",
                symbol=self.symbol,
                values=_values(
                    symbols=self.symbol,
                    disableRelatedReports=disable_related_reports,
                    formatted=formatted,
                    getAllResearchReports=get_all_research_reports,
                    reportsCount=reports_count,
                    ssl=ssl,
                ),
            )
        )
        results: list[dict[str, Any]] = payload["finance"]["result"]
        record: dict[str, Any] = results[0] if results else {}
        return validate_model(Insights, record)

    def recommendations(
        self, *, fields: list[str] | None = None
    ) -> RecommendationsResult:
        """Fetch related-symbol recommendations for this symbol.

        An unrecognized symbol surfaces as a model-validation failure
        (``YahooApiError``, code ``"model-validation"``) rather than
        ``SymbolNotFoundError``: Yahoo returns HTTP 200 with a valid-but-
        empty ``{"result": []}`` shape, and ``RecommendationsResult``
        requires both ``recommended_symbols``/``symbol`` on every record, so
        validating the resulting ``{}`` fails — confirmed live 2026-07-05,
        corpus: ``recommendations-by-symbol/ZZZZXYZQ.json``. Yahoo sends the
        identical valid-empty shape (not an error) for some instrument types
        with no recommendations to report (corpus-confirmed on the FUTURE
        symbol ``ES=F``), which surfaces the same way.

        Returns:
            RecommendationsResult: The validated recommendations record.
        """

        payload = run(
            _core.call_endpoint(
                "recommendations-by-symbol",
                symbol=self.symbol,
                values=_values(symbol=self.symbol, fields=fields),
            )
        )
        results: list[dict[str, Any]] = payload["finance"]["result"]
        record: dict[str, Any] = results[0] if results else {}
        return validate_model(RecommendationsResult, record)

    def stock_recommender(self) -> StockRecommenderResult:
        """Fetch related-tickers peers for this equity symbol.

        An unrecognized symbol's 404 is truly unmappable and propagates as
        a bare ``YahooRequestError``: unlike every other endpoint in this
        batch, the 404 body is ``{"message": "Not Found"}`` (no ``detail``
        key), which ``yoghurt._core.map_http_error`` cannot map to
        ``SymbolNotFoundError`` or any other typed error — confirmed live
        2026-07-05, corpus: ``stock-recommender/ZZZZXYZQ.json``.

        Returns:
            StockRecommenderResult: The validated stock-recommender record.
        """

        payload = run(
            _core.call_endpoint(
                "stock-recommender",
                symbol=self.symbol,
                values=_values(symbol=self.symbol),
            )
        )
        return validate_model(StockRecommenderResult, payload)


def _tabular_frame(payload: dict[str, Any], route: str) -> Frame:
    """Flatten a screener/visualization payload into a Frame.

    Empty result sets (no records, or no documents) resolve to zero columns
    and produce an empty ``Frame`` rather than raising.

    Returns:
        Frame: The flattened result table plus a fetch timestamp.

    Raises:
        YahooApiError: If the response cannot be flattened into a tabular
            shape (code ``"malformed-response"``), or if a cell holds a
            nested object/list that cannot become a scalar column (code
            ``"unsupported-response-shape"``).
    """

    try:
        records, _total_rows, schema_hint = parse_tabular_payload(payload, route, route)
        columns = resolve_column_order(records, schema_hint)
        column_data = collect_column_data(records, columns)
    except TabularShapeError as exc:
        raise YahooApiError(code="malformed-response", description=str(exc)) from exc
    try:
        reject_nested_cells(column_data)
    except TabularShapeError as exc:
        message = (
            "Yahoo returned nested values that cannot form a tabular Frame; "
            "use raw() for this query"
        )
        raise YahooApiError(
            code="unsupported-response-shape", description=message
        ) from exc
    df = build_tabular_frame(column_data, columns) if columns else pl.DataFrame()
    return Frame(df=df, fetched_at=_now_utc())


async def _history_payloads(
    symbols: list[str], values: dict[str, object]
) -> list[dict[str, Any]]:
    """Fetch chart payloads concurrently for a multi-symbol history request.

    Returns:
        list[dict[str, Any]]: Decoded chart payloads in symbol order.
    """

    payloads: list[dict[str, Any]] = []
    for offset in range(0, len(symbols), HISTORY_REQUEST_BATCH_SIZE):
        batch = symbols[offset : offset + HISTORY_REQUEST_BATCH_SIZE]
        payloads.extend(
            await asyncio.gather(
                *(
                    _core.call_endpoint(
                        "chart",
                        symbol=symbol,
                        values={**values, "symbol": symbol},
                    )
                    for symbol in batch
                )
            )
        )
    return payloads


def history(  # noqa: PLR0913 - history's five orthogonal controls are public.
    symbols: list[str],
    *,
    period: str | None = None,
    start: DateLike | None = None,
    end: DateLike | None = None,
    interval: str = "1d",
    include_pre_post: bool = False,
) -> History:
    """Fetch adjusted OHLCV history for one or more symbols.

    The result is long-form and preserves the caller's symbol order, so it
    can be partitioned by ``symbol`` before passing OHLCV arrays to TA-Lib.
    With no date arguments, the window defaults to one month. Adjustment is
    derived from Yahoo's adjusted close. Supported intervals are daily or
    coarser because Yahoo omits adjusted close from intraday responses; no
    heuristic price repair is applied.

    Returns:
        History: Adjusted rows with the stable ``symbol, ts, open, high, low,
        close, volume`` schema.

    Raises:
        ValueError: If symbols is empty, contains an empty symbol, or the
            period/date arguments conflict.
        YahooApiError: If a chart response cannot form the history schema.
    """

    if not symbols:
        message = "symbols must not be empty"
        raise ValueError(message)
    normalized = [symbol.strip() for symbol in symbols]
    if any(not symbol for symbol in normalized):
        message = "symbols must not contain empty values"
        raise ValueError(message)
    values = history_request_values(
        period=period,
        start=start,
        end=end,
        interval=interval,
        include_pre_post=include_pre_post,
    )
    payloads = run(_history_payloads(normalized, values))
    try:
        frames = [
            history_frame_from_result(payload["chart"]["result"][0], symbol)
            for symbol, payload in zip(normalized, payloads, strict=True)
        ]
    except (KeyError, IndexError, TypeError, TabularShapeError) as exc:
        raise YahooApiError(code="malformed-response", description=str(exc)) from exc
    return History(df=concat_history_frames(frames), fetched_at=_now_utc())


def quotes(  # noqa: PLR0913 - one keyword-only arg per quote wire param.
    symbols: list[str],
    *,
    fields: list[str] | None = None,
    formatted: bool | None = None,
    enable_private_company: bool | None = None,
    overnight_price: bool | None = None,
    top_pick_this_month: bool | None = None,
    img_heights: int | None = None,
    img_labels: list[str] | None = None,
    img_widths: int | None = None,
) -> list[Quote]:
    """Fetch quote records for one or more symbols.

    ``enable_private_company=True`` includes private-company quote matches;
    ``overnight_price=True`` requests overnight price fields. Symbols Yahoo
    does not recognize are simply absent from the returned list rather than
    raising.

    Returns:
        list[Quote]: The validated ``quoteResponse.result`` records.

    Raises:
        ValueError: If ``symbols`` is empty.
    """

    if not symbols:
        message = "symbols must not be empty"
        raise ValueError(message)
    payload = run(
        _core.call_endpoint(
            "quote",
            values=_values(
                symbols=",".join(symbols),
                fields=fields,
                formatted=formatted,
                enablePrivateCompany=enable_private_company,
                overnightPrice=overnight_price,
                topPickThisMonth=top_pick_this_month,
                imgHeights=img_heights,
                imgLabels=img_labels,
                imgWidths=img_widths,
            ),
        )
    )
    return [
        validate_model(Quote, record) for record in payload["quoteResponse"]["result"]
    ]


def screener(query: str) -> Frame:
    """Run a screener DSL query and flatten the records into a table.

    Returns:
        Frame: One row per screener record. Empty result sets produce an
        empty Frame.

    See Also:
        :func:`_tabular_frame` for the ``YahooApiError`` codes a malformed
        or unsupported response shape can raise.
    """

    payload = run(_core.call_query("screener", query))
    return _tabular_frame(payload, "screener")


def visualization(query: str) -> Frame:
    """Run a visualization DSL query and flatten the rows into a table.

    Returns:
        Frame: One row per visualization document row. Empty result sets
        produce an empty Frame.

    See Also:
        :func:`_tabular_frame` for the ``YahooApiError`` codes a malformed
        or unsupported response shape can raise.
    """

    payload = run(_core.call_query("visualization", query))
    return _tabular_frame(payload, "visualization")


def screener_predefined(  # noqa: PLR0913 - one keyword-only arg per wire param.
    scr_ids: list[str],
    *,
    count: int | None = None,
    start: int | None = None,
    formatted: bool | None = None,
    use_records_response: bool | None = None,
    sort_field: str | None = None,
    sort_type: str | None = None,
) -> list[ScreenerPredefinedResult]:
    """Run one or more of Yahoo's predefined screeners.

    ``use_records_response=False`` requests Yahoo's non-records-style
    screener response shape; both shapes validate as
    :class:`ScreenerPredefinedResult`, but its ``records`` field is an
    open-ended, screener-id-specific field subset (see the model's module
    docstring), so it is left as ``list[dict[str, object]]`` rather than a
    fixed row model. This endpoint is market-wide, not symbol-bound: an
    empty ``records`` list for an unmatched screener id is valid data, not
    an error.

    Returns:
        list[ScreenerPredefinedResult]: The validated
        ``finance.result`` records, one per requested screener id.
    """

    payload = run(
        _core.call_endpoint(
            "screener-predefined",
            values=_values(
                scrIds=",".join(scr_ids),
                count=count,
                start=start,
                formatted=formatted,
                useRecordsResponse=use_records_response,
                sortField=sort_field,
                sortType=sort_type,
            ),
        )
    )
    return [
        validate_model(ScreenerPredefinedResult, record)
        for record in payload["finance"]["result"]
    ]


def _spec_default_str(command_name: str, param_name: str) -> str:
    """Read a command param's CommandSpec default, narrowed to ``str``.

    Returns:
        str: The spec's default value for the named param.

    Raises:
        TypeError: If the spec default is not a string (spec invariant).
    """

    command = COMMANDS_BY_NAME[command_name]
    default = next(
        param.default for param in command.params if param.name == param_name
    )
    if not isinstance(default, str):
        message = f"{command_name} param {param_name!r} default must be a string"
        raise TypeError(message)
    return default


_TRENDING_DEFAULT_REGION: Final[str] = _spec_default_str("trending", "region")


def trending(  # noqa: PLR0913 - one keyword-only arg per wire param.
    region: str | None = None,
    *,
    count: int | None = None,
    use_quotes: bool | None = None,
    fields: list[str] | None = None,
    quote_type: str | None = None,
    formatted: bool | None = None,
) -> TrendingResult:
    """List trending tickers for a region.

    ``region`` is substituted into the URL path, not sent as a query
    parameter; when omitted it falls back to the CommandSpec's region
    default. ``use_quotes=False`` omits inline quote data from trending
    results. This endpoint is market-wide, not symbol-bound: an empty
    ``quotes`` list is valid data for a region with no trending picks, not
    an error.

    Returns:
        TrendingResult: The validated ``finance.result[0]`` record.
    """

    payload = run(
        _core.call_endpoint(
            "trending",
            values=_values(
                region=region if region is not None else _TRENDING_DEFAULT_REGION,
                count=count,
                useQuotes=use_quotes,
                fields=fields,
                quoteType=quote_type,
                formatted=formatted,
            ),
        )
    )
    return validate_model(TrendingResult, payload["finance"]["result"][0])


def sector(
    slug: str,
    *,
    with_returns: bool | None = None,
    formatted: bool | None = None,
) -> SectorResult:
    """Fetch sector overview, performance, top holdings, and industries.

    ``slug`` is the wire/path value (Yahoo calls it ``sector``, for example
    ``"technology"``); renamed on the Python side to avoid shadowing this
    module's own ``sector`` function.

    Returns:
        SectorResult: The validated ``data`` record.
    """

    payload = run(
        _core.call_endpoint(
            "sector",
            values=_values(
                sector=slug,
                withReturns=with_returns,
                formatted=formatted,
            ),
        )
    )
    return validate_model(SectorResult, payload["data"])


def market_summary(*, formatted: bool | None = None) -> list[MarketSummaryQuote]:
    """Fetch a global market summary: indices, futures, forex, crypto.

    Returns:
        list[MarketSummaryQuote]: The validated
        ``marketSummaryResponse.result`` records.
    """

    payload = run(
        _core.call_endpoint(
            "market-summary",
            values=_values(formatted=formatted),
        )
    )
    return [
        validate_model(MarketSummaryQuote, record)
        for record in payload["marketSummaryResponse"]["result"]
    ]


def market_info(*, modules: list[str] | None = None) -> MarketInfoResult:
    """Fetch commodity and currency market data.

    ``modules`` selects which module Yahoo populates; an unrequested
    module is ``None`` on the returned record.

    Returns:
        MarketInfoResult: The validated ``finance.result`` record.
    """

    payload = run(
        _core.call_endpoint(
            "market-info",
            values=_values(modules=modules),
        )
    )
    return validate_model(MarketInfoResult, payload["finance"]["result"])


def market_time(
    *,
    formatted: bool | None = None,
    key: str | None = None,
) -> MarketTimeResult:
    """Show current market hours and session status.

    Returns:
        MarketTimeResult: The validated ``finance`` record.
    """

    payload = run(
        _core.call_endpoint(
            "market-time",
            values=_values(formatted=formatted, key=key),
        )
    )
    return validate_model(MarketTimeResult, payload["finance"])


def screener_instrument_fields(instrument: str) -> ScreenerInstrumentFieldsResult:
    """List every field available for a Yahoo data-platform entity.

    This endpoint is market-wide, not symbol-bound: an empty ``fields``
    mapping for a paywalled instrument (Yahoo's documented
    ``privatecompany`` quirk) is valid data, not an error.

    Returns:
        ScreenerInstrumentFieldsResult: The validated ``finance.result[0]``
        record.
    """

    payload = run(
        _core.call_endpoint(
            "screener-instrument-fields",
            values=_values(instrument=instrument),
        )
    )
    return validate_model(
        ScreenerInstrumentFieldsResult, payload["finance"]["result"][0]
    )


def timeseries_fields(
    *,
    type: str | None = None,  # noqa: A002 - mirrors Yahoo's wire/CLI name
) -> TimeseriesFieldsResult:
    """List available fundamentals timeseries field names for a type.

    Returns:
        TimeseriesFieldsResult: The validated ``timeseriesfields.result[0]``
        record.
    """

    payload = run(
        _core.call_endpoint(
            "timeseries-fields",
            values=_values(type=type),
        )
    )
    return validate_model(
        TimeseriesFieldsResult, payload["timeseriesfields"]["result"][0]
    )


def screener_discover(
    *,
    modules: list[str] | None = None,
    count: int | None = None,
    formatted: bool | None = None,
) -> ScreenerDiscoverResult:
    """Discover investment ideas from Yahoo screener modules.

    This endpoint is market-wide, not symbol-bound: an empty idea-module
    list is valid data, never an error.

    Returns:
        ScreenerDiscoverResult: The validated ``finance.result`` record.
    """

    payload = run(
        _core.call_endpoint(
            "screener-discover",
            values=_values(modules=modules, count=count, formatted=formatted),
        )
    )
    return validate_model(ScreenerDiscoverResult, payload["finance"]["result"])


def raw(
    path: str,
    params: dict[str, ParamValue] | None = None,
    *,
    use_crumb: bool = True,
) -> dict[str, Any]:
    """Call an arbitrary Yahoo path with pre-serialized wire params.

    This is the escape hatch: no path template, no param coercion or
    validation, and no envelope lookup on a *successful* response — a
    200 body is parsed and returned exactly as Yahoo sent it (a malformed
    body still raises ``YahooApiError``, code ``"malformed-response"``).
    HTTP-level failures are, however, still routed through the library's
    usual error mapping (:func:`yoghurt._core.map_http_error`): an HTTP
    error response whose body carries a recognizable Yahoo error envelope
    or a ``{"detail": ...}`` shape raises ``YahooApiError``; other HTTP
    failures raise ``YahooRequestError``.

    Returns:
        dict[str, Any]: The parsed response payload.
    """

    return run(_core.call_raw(path, params, use_crumb=use_crumb))
