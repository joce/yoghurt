"""Public synchronous yoghurt API.

Yahoo's shared ``lang``/``region`` wire params ride their CommandSpec
defaults; per-call overrides are deliberately deferred (they will arrive
with the typed-model layer). Parameter names mirror the CLI's command
metadata, except booleans whose CLI flag inverts the wire value — those
use the wire name so the kwarg's meaning matches its effect.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Final, TypeAlias

import polars as pl

from yoghurt import _core
from yoghurt._bridge import run
from yoghurt.commands import COMMANDS_BY_NAME
from yoghurt.exceptions import SymbolNotFoundError, YahooApiError
from yoghurt.frames import Chart, Frame, Spark
from yoghurt.models import ChartEvents, ChartMeta, OptionChain, Quote, validate_model
from yoghurt.tabular import (
    TabularShapeError,
    build_chart_frame,
    build_spark_frame,
    build_tabular_frame,
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

    def chart(
        self,
        *,
        period1: DateLike | None = None,
        period2: DateLike | None = None,
        interval: str | None = None,
        events: list[str] | None = None,
        include_pre_post: bool | None = None,
    ) -> Chart:
        """Fetch OHLCV bars.

        Returns:
            Chart: Typed bars frame plus the typed chart meta and (when
            requested) events blocks.

        Raises:
            YahooApiError: If the response cannot be flattened into the
                fixed bars schema (code ``"malformed-response"``), or if
                the meta/events blocks fail model validation (code
                ``"model-validation"``).
        """

        payload = run(
            _core.call_endpoint(
                "chart",
                symbol=self.symbol,
                values=_values(
                    symbol=self.symbol,
                    period1=period1,
                    period2=period2,
                    interval=interval,
                    events=events,
                    includePrePost=include_pre_post,
                ),
            )
        )
        result = payload["chart"]["result"][0]
        try:
            timestamps, columns = extract_chart_columns(result)
            df = build_chart_frame(timestamps, columns)
        except TabularShapeError as exc:
            raise YahooApiError(
                code="malformed-response", description=str(exc)
            ) from exc
        meta = validate_model(ChartMeta, result.get("meta", {}))
        raw_events = result.get("events")
        chart_events = validate_model(ChartEvents, raw_events) if raw_events else None
        return Chart(
            df=df,
            fetched_at=_now_utc(),
            meta=meta,
            events=chart_events,
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
    ) -> dict[str, Any]:
        """Fetch instrument classification metadata for this symbol.

        ``enable_private_company=True`` includes private-company data;
        ``overnight_price=True`` requests overnight price fields.

        Returns:
            dict[str, Any]: The single quoteType record.

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
        return results[0]

    def quote_summary(
        self,
        *,
        modules: list[str] | None = None,
        formatted: bool | None = None,
        enable_private_company: bool | None = None,
        enable_qsp_expanded_earnings: bool | None = None,
        overnight_price: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch quoteSummary modules for this symbol.

        ``enable_private_company=True`` includes private-company data;
        ``enable_qsp_expanded_earnings=True`` requests Yahoo's expanded
        earnings fields; ``overnight_price=True`` requests overnight price
        fields.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
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
    ) -> dict[str, Any]:
        """Fetch fundamentals timeseries for this symbol.

        ``pad_time_series=True`` asks Yahoo to pad missing timeseries values.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
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

    def calendar_events(  # noqa: PLR0913 - one keyword-only arg per event filter.
        self,
        *,
        modules: list[str] | None = None,
        count_per_day: int | None = None,
        start_date: DateLike | None = None,
        end_date: DateLike | None = None,
        economic_events_high_importance_only: bool | None = None,
        economic_events_region_filter: str | None = None,
    ) -> dict[str, Any]:
        """Fetch earnings, IPO, economic, and SEC filing events for this symbol.

        ``economic_events_high_importance_only=True`` limits economic events
        to high-importance ones.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
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

    def analyst(self, *, debug_flag: bool | None = None) -> dict[str, Any]:
        """Fetch analyst intelligence for this symbol.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
            _core.call_endpoint(
                "analyst",
                symbol=self.symbol,
                values=_values(symbol=self.symbol, debug_flag=debug_flag),
            )
        )

    def ratings_top(self, *, exclude_noncurrent: bool | None = None) -> dict[str, Any]:
        """Fetch top analyst rating buckets for this symbol.

        ``exclude_noncurrent=True`` drops non-current analyst records from
        the top scored buckets.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
            _core.call_endpoint(
                "ratings-top",
                symbol=self.symbol,
                values=_values(
                    symbol=self.symbol, exclude_noncurrent=exclude_noncurrent
                ),
            )
        )

    def price_insights(
        self,
        *,
        modules: list[str] | None = None,
        ai_modules: list[str] | None = None,
        check_anomaly: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch AI-generated price insights for this symbol.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
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

    def insights(
        self,
        *,
        disable_related_reports: bool | None = None,
        formatted: bool | None = None,
        get_all_research_reports: bool | None = None,
        reports_count: int | None = None,
        ssl: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch research reports and insights for this symbol.

        ``disable_related_reports=True`` omits related research reports;
        ``get_all_research_reports=True`` requests all available research
        reports; ``ssl=True`` requests SSL URLs in Yahoo response fields.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
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

    def recommendations(self, *, fields: list[str] | None = None) -> dict[str, Any]:
        """Fetch related-symbol recommendations for this symbol.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
            _core.call_endpoint(
                "recommendations-by-symbol",
                symbol=self.symbol,
                values=_values(symbol=self.symbol, fields=fields),
            )
        )

    def stock_recommender(self) -> dict[str, Any]:
        """Fetch related-tickers peers for this equity symbol.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
            _core.call_endpoint(
                "stock-recommender",
                symbol=self.symbol,
                values=_values(symbol=self.symbol),
            )
        )


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
) -> dict[str, Any]:
    """Run one or more of Yahoo's predefined screeners.

    ``use_records_response=False`` requests Yahoo's non-records-style
    screener response shape.

    Returns:
        dict[str, Any]: The full parsed response payload.
    """

    return run(
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
) -> dict[str, Any]:
    """List trending tickers for a region.

    ``region`` is substituted into the URL path, not sent as a query
    parameter; when omitted it falls back to the CommandSpec's region
    default. ``use_quotes=False`` omits inline quote data from trending
    results.

    Returns:
        dict[str, Any]: The full parsed response payload.
    """

    return run(
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


def sector(
    sector: str,
    *,
    with_returns: bool | None = None,
    formatted: bool | None = None,
) -> dict[str, Any]:
    """Fetch sector overview, performance, top holdings, and industries.

    Returns:
        dict[str, Any]: The full parsed response payload.
    """

    return run(
        _core.call_endpoint(
            "sector",
            values=_values(
                sector=sector,
                withReturns=with_returns,
                formatted=formatted,
            ),
        )
    )


def market_summary(*, formatted: bool | None = None) -> dict[str, Any]:
    """Fetch a global market summary: indices, futures, forex, crypto.

    Returns:
        dict[str, Any]: The full parsed response payload.
    """

    return run(
        _core.call_endpoint(
            "market-summary",
            values=_values(formatted=formatted),
        )
    )


def market_info(*, modules: list[str] | None = None) -> dict[str, Any]:
    """Fetch commodity and currency market data.

    Returns:
        dict[str, Any]: The full parsed response payload.
    """

    return run(
        _core.call_endpoint(
            "market-info",
            values=_values(modules=modules),
        )
    )


def market_time(
    *,
    formatted: bool | None = None,
    key: str | None = None,
) -> dict[str, Any]:
    """Show current market hours and session status.

    Returns:
        dict[str, Any]: The full parsed response payload.
    """

    return run(
        _core.call_endpoint(
            "market-time",
            values=_values(formatted=formatted, key=key),
        )
    )


def screener_instrument_fields(instrument: str) -> dict[str, Any]:
    """List every field available for a Yahoo data-platform entity.

    Returns:
        dict[str, Any]: The full parsed response payload.
    """

    return run(
        _core.call_endpoint(
            "screener-instrument-fields",
            values=_values(instrument=instrument),
        )
    )


def timeseries_fields(
    *,
    type: str | None = None,  # noqa: A002 - mirrors Yahoo's wire/CLI name
) -> dict[str, Any]:
    """List available fundamentals timeseries field names for a type.

    Returns:
        dict[str, Any]: The full parsed response payload.
    """

    return run(
        _core.call_endpoint(
            "timeseries-fields",
            values=_values(type=type),
        )
    )


def screener_discover(
    *,
    modules: list[str] | None = None,
    count: int | None = None,
    formatted: bool | None = None,
) -> dict[str, Any]:
    """Discover investment ideas from Yahoo screener modules.

    Returns:
        dict[str, Any]: The full parsed response payload.
    """

    return run(
        _core.call_endpoint(
            "screener-discover",
            values=_values(modules=modules, count=count, formatted=formatted),
        )
    )


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
