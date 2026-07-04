"""Public synchronous yoghurt API.

Yahoo's shared ``lang``/``region`` wire params ride their CommandSpec
defaults; per-call overrides are deliberately deferred (they will arrive
with the typed-model layer). Every other endpoint parameter is mirrored
1:1 from the CLI's command metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, TypeAlias

from yoghurt import _core
from yoghurt._bridge import run
from yoghurt.exceptions import SymbolNotFoundError
from yoghurt.frames import Chart
from yoghurt.tabular import build_chart_frame, extract_chart_columns

if TYPE_CHECKING:
    from datetime import date

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
        disable_private_company: bool | None = None,
        no_overnight_price: bool | None = None,
        top_pick_this_month: bool | None = None,
        img_heights: int | None = None,
        img_labels: list[str] | None = None,
        img_widths: int | None = None,
    ) -> dict[str, Any]:
        """Fetch this symbol's quote record.

        Returns:
            dict[str, Any]: The single quote record.

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
                    enablePrivateCompany=disable_private_company,
                    overnightPrice=no_overnight_price,
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
        return results[0]

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
            Chart: Typed bars frame plus the chart meta block.
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
        timestamps, columns = extract_chart_columns(result)
        return Chart(
            df=build_chart_frame(timestamps, columns),
            fetched_at=_now_utc(),
            meta=result.get("meta", {}),
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
    ) -> dict[str, Any]:
        """Fetch the sparkline price series for this symbol.

        The spark response nests per-symbol data as ``spark.result[].response[]``
        rather than the ``chart``-compatible shape, so this returns the raw
        payload rather than a :class:`~yoghurt.frames.Chart`.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
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

    def quote_type(
        self,
        *,
        formatted: bool | None = None,
        disable_private_company: bool | None = None,
        no_overnight_price: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch instrument classification metadata for this symbol.

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
                    enablePrivateCompany=disable_private_company,
                    overnightPrice=no_overnight_price,
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
        disable_private_company: bool | None = None,
        disable_qsp_expanded_earnings: bool | None = None,
        no_overnight_price: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch quoteSummary modules for this symbol.

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
                    enablePrivateCompany=disable_private_company,
                    enableQSPExpandedEarnings=disable_qsp_expanded_earnings,
                    overnightPrice=no_overnight_price,
                ),
            )
        )

    def options(
        self,
        *,
        date: DateLike | None = None,
        formatted: bool | None = None,
        straddle: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch the option chain for this symbol.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
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

    def timeseries(
        self,
        *,
        type: list[str] | None = None,  # noqa: A002 - mirrors Yahoo's wire/CLI name
        period1: DateLike | None = None,
        period2: DateLike | None = None,
        merge: bool | None = None,
        no_pad_time_series: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch fundamentals timeseries for this symbol.

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
                    padTimeSeries=no_pad_time_series,
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
        include_all_economic_events: bool | None = None,
        economic_events_region_filter: str | None = None,
    ) -> dict[str, Any]:
        """Fetch earnings, IPO, economic, and SEC filing events for this symbol.

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
                    economicEventsHighImportanceOnly=include_all_economic_events,
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

    def ratings_top(self, *, include_noncurrent: bool | None = None) -> dict[str, Any]:
        """Fetch top analyst rating buckets for this symbol.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
            _core.call_endpoint(
                "ratings-top",
                symbol=self.symbol,
                values=_values(
                    symbol=self.symbol, exclude_noncurrent=include_noncurrent
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
        enable_related_reports: bool | None = None,
        formatted: bool | None = None,
        skip_all_research_reports: bool | None = None,
        reports_count: int | None = None,
        no_ssl: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch research reports and insights for this symbol.

        Returns:
            dict[str, Any]: The full parsed response payload.
        """

        return run(
            _core.call_endpoint(
                "insights",
                symbol=self.symbol,
                values=_values(
                    symbols=self.symbol,
                    disableRelatedReports=enable_related_reports,
                    formatted=formatted,
                    getAllResearchReports=skip_all_research_reports,
                    reportsCount=reports_count,
                    ssl=no_ssl,
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
