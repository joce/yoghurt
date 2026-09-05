# Dataframes

Every tabular result in yoghurt — `Chart`, `History`, `Spark`, `Timeseries`'s
four frames, `FinancialAnalysis`'s 17 frames, and
`screener()`/`visualization()` results — shares one conversion vocabulary.
Conversions take no shaping arguments: the frame's columns and row order are
already final.

## Conversion vocabulary

```python
frame = yoghurt.screener(
    "SELECT ticker, intradaymarketcap FROM EQUITY "
    "WHERE region = 'us' AND sector = 'Technology' "
    "ORDER BY intradaymarketcap DESC LIMIT 25"
)

frame.to_polars()
frame.to_pandas()
frame.to_arrow()
frame.to_dicts()
frame.save_parquet("tech.parquet")
```

Polars is a core dependency, so `to_polars()` always works. `to_pandas()`
and `to_arrow()` need the optional `pandas` extra — see
[SHARP-EDGES.md](SHARP-EDGES.md#topandas-and-toarrow-need-an-extra).

## Price and timeseries frames

`Chart`/`Spark` are `Frame` subclasses with extra typed attributes
(`.meta`, and `.events` on `Chart`):

```python
chart = yoghurt.Ticker("AAPL").chart(interval="1d")
bars = chart.to_polars()
meta = chart.meta
```

`History` is a plain `Frame` subclass with one stable long-form adjusted
schema, including a leading `symbol` column for both single- and multi-symbol
requests:

```python
history = yoghurt.history(["AAPL", "MSFT"], period="1y")
bars = history.to_polars().partition_by("symbol", as_dict=True)
```

`Timeseries` bundles four separate frames rather than one:

```python
data = yoghurt.Ticker("AAPL").timeseries()
fundamentals_df = data.fundamentals.to_polars()
ratings_df = data.analyst_ratings.to_polars()
```

`FinancialAnalysis` similarly bundles 17 schema-stable frames:

```python
analysis = yoghurt.Ticker("AAPL").financial_analysis()
cash_flow_df = analysis.cash_flow.to_polars()
eps_revisions_df = analysis.eps_revisions.to_polars()
```

## Pandas-wide history

Keep multi-symbol history long-form for grouping and TA-Lib. Pivot only when
the analysis needs an aligned timestamp-by-symbol Pandas matrix:

```python
wide = (
    yoghurt.history(["AAPL", "MSFT"], period="1y")
    .to_pandas()
    .pivot(
        index="ts",
        columns="symbol",
        values=["open", "high", "low", "close", "volume"],
    )
)
```

The result has hierarchical `(field, symbol)` columns without changing
yoghurt's history return shape.

## Parquet from the CLI

`chart`, `history`, `screener`, and `visualization` can write Parquet directly instead
of JSON:

```bash
uv run yoghurt chart AAPL --interval 1d --format parquet --out aapl_1d.parquet
uv run yoghurt history AAPL,MSFT --period 1y --format parquet --out history.parquet
```

The derived `financial-analysis` CLI is JSON-only. In Python, call
`save_parquet()` on whichever bundle fields need separate files.

## Empty results

A query with zero matches returns an empty `Frame` (zero rows, not `None`
and not an exception). `to_polars()` on an empty frame returns a
zero-row `DataFrame`; check `.height` (polars) or `len(...)` before
assuming rows exist.

## Workflow: adjusted history and returns

Prerequisites: install `yoghurt`; network access to Yahoo and a writable current
directory. Install `yoghurt[pandas]` only for the optional reshape below.

```python
import polars as pl
import yoghurt

history = yoghurt.history(["AAPL", "MSFT"], period="1y", interval="1d")
bars = history.to_polars().sort(["symbol", "ts"])
returns = bars.with_columns(
    (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1).alias("return")
)
history.save_parquet("history.parquet")
returns.write_parquet("returns.parquet")
```

Result: long-form `symbol`, `ts`, adjusted OHLC, and volume rows; `return` is a
fraction (0.01 means 1%). Each symbol's first return is null, and missing
closes propagate null rather than bridging gaps. Sorting and grouping prevent
one symbol's last price from becoming another symbol's previous price.

Optional, continuing the same example:

```python
wide = history.to_pandas().pivot(index="ts", columns="symbol", values="close")
wide.to_parquet("close_wide.parquet")
```

The matrix aligns timestamps across symbols and preserves gaps. Yahoo transport
errors raise typed exceptions; unknown symbols fail the request. Missing usable
adjusted-close factors raise `YahooApiError`; audit `chart()` instead of mixing
raw and adjusted prices. Empty histories produce empty output tables. Returns
are within each security's quote units, not a currency-converted portfolio return.

## Python reference

Use these signatures for accepted kwargs; CLI flag names describe the CLI only.
`DateLike` accepts Unix seconds, date/datetime objects, and documented ISO date
strings. Omitted `None` endpoint arguments use command defaults. Python typed
wrappers use default locales; `lang` and locale `region` are per-call CLI/raw controls. The explicit
`trending(region=...)` parameter selects a regional route rather than a locale.
Typed quote calls fetch complete models with no `fields` projection. Typed
wrappers request unformatted values; use CLI `--formatted` or `raw()` for display
wrappers. For example, CLI `--disable-private-company` corresponds to Python
`include_private_companies=False`; `--no-pad-time-series` corresponds to
`pad_time_series=False`. Lists are Python lists, not comma-separated strings.

Returns: models retain extra Yahoo fields and are frozen; tabular results use
[the conversion vocabulary](#conversion-vocabulary). `Timeseries` and
`FinancialAnalysis` bundle separate frames. `raw()` returns decoded, unmodeled
JSON. Empty queries return collections/frames; they do not return `None`.

Errors: catch `YoghurtError` for library failures; `SymbolNotFoundError` for
missing symbol lookups, `YahooApiError` for Yahoo payload/shape failures
(`code`, `description`), and `YahooRequestError`/`YahooUnavailableError` for
transport failures. Invalid local arguments raise `ValueError`. Endpoint-specific
exceptions and observed limitations are in each domain's SHARP-EDGES notes.

Configuration: call `configure()` before the first data call. It replaces the
whole option set; omitted values reset to defaults. Calling it after the shared
client exists raises `RuntimeError`. The library never prints or prompts.
Synchronous calls share a client; independent and async typed clients are not
provided. Refresh this generated section with
`uv run python tools/generate_python_reference.py` in the source checkout.

<!-- BEGIN GENERATED PYTHON REFERENCE -->

Signatures and return types generated from the implementation.

### Ticker methods

Create `yoghurt.Ticker(symbol)`; construction performs no request.

`Ticker.quote(*, include_private_companies: bool | None=None, overnight_price: bool | None=None, top_pick_this_month: bool | None=None, img_heights: int | None=None, img_labels: list[str] | None=None, img_widths: int | None=None) -> Quote`

Fetch this symbol's quote record.

`Ticker.chart(*, period1: DateLike | None=None, period2: DateLike | None=None, range: str | None=None, interval: str | None=None, events: list[str] | None=None, include_pre_post: bool | None=None) -> Chart`

Fetch OHLCV bars.

`Ticker.history(*, period: str | None=None, start: DateLike | None=None, end: DateLike | None=None, interval: str='1d', include_pre_post: bool=False) -> History`

Fetch analysis-ready, corporate-action-adjusted OHLCV history.

`Ticker.spark(*, range: str | None=None, interval: str | None=None, indicators: list[str] | None=None, include_timestamps: bool | None=None, include_pre_post: bool | None=None, cors_domain: str | None=None, tsrc: str | None=None) -> Spark`

Fetch the sparkline price series for this symbol.

`Ticker.quote_type(*, include_private_companies: bool | None=None, overnight_price: bool | None=None) -> QuoteTypeResult`

Fetch instrument classification metadata for this symbol.

`Ticker.quote_summary(*, modules: list[str] | None=None, include_private_companies: bool | None=None, include_expanded_earnings: bool | None=None, overnight_price: bool | None=None) -> QuoteSummary`

Fetch quoteSummary modules for this symbol.

`Ticker.options(*, date: DateLike | None=None, straddle: bool | None=None) -> OptionChain`

Fetch the option chain for this symbol.

`Ticker.timeseries(*, type: list[str] | None=None, period1: DateLike | None=None, period2: DateLike | None=None, merge: bool | None=None, pad_time_series: bool | None=None) -> Timeseries`

Fetch fundamentals timeseries for this symbol as typed frames.

`Ticker.financial_analysis() -> FinancialAnalysis`

Fetch analysis-ready financial, analyst, and ownership tables.

`Ticker.calendar_events(*, modules: list[str] | None=None, count_per_day: int | None=None, start_date: DateLike | None=None, end_date: DateLike | None=None, economic_events_high_importance_only: bool | None=None, economic_events_region_filter: str | None=None) -> CalendarEventsResult`

Fetch earnings, IPO, economic, and SEC filing events for this symbol.

`Ticker.analyst(*, debug_flag: bool | None=None) -> AnalystResult`

Fetch analyst intelligence for this symbol.

`Ticker.ratings_top(*, exclude_noncurrent: bool | None=None) -> TopRatingsResult`

Fetch top analyst rating buckets for this symbol.

`Ticker.price_insights(*, modules: list[str] | None=None, ai_modules: list[str] | None=None, check_anomaly: bool | None=None) -> PriceInsights`

Fetch AI-generated price insights for this symbol.

`Ticker.insights(*, disable_related_reports: bool | None=None, get_all_research_reports: bool | None=None, reports_count: int | None=None, ssl: bool | None=None) -> Insights`

Fetch research reports and insights for this symbol.

`Ticker.recommendations(*, fields: list[str] | None=None) -> RecommendationsResult`

Fetch related-symbol recommendations for this symbol.

`Ticker.stock_recommender() -> StockRecommenderResult`

Fetch related-tickers peers for this equity symbol.

`yoghurt.history(symbols: list[str], *, period: str | None=None, start: DateLike | None=None, end: DateLike | None=None, interval: str='1d', include_pre_post: bool=False) -> History`

Fetch adjusted OHLCV history for one or more symbols.

`yoghurt.quotes(symbols: list[str], *, include_private_companies: bool | None=None, overnight_price: bool | None=None, top_pick_this_month: bool | None=None, img_heights: int | None=None, img_labels: list[str] | None=None, img_widths: int | None=None) -> list[Quote]`

Fetch quote records for one or more symbols.

`yoghurt.search(query: str, *, quotes_count: int | None=None, news_count: int | None=None, lists_count: int | None=None, recommended_count: int | None=None, fuzzy: bool | None=None, include_private_companies: bool | None=None, include_navigation_links: bool | None=None, include_research_reports: bool | None=None, include_cultural_assets: bool | None=None) -> SearchResult`

Search instruments and related Yahoo Finance content.

`yoghurt.lookup(query: str, *, type: str | None=None, start: int | None=None, count: int | None=None, fetch_pricing_data: bool | None=None) -> LookupResult`

Look up a page of instruments, optionally filtered by asset type.

`yoghurt.screener(query: str) -> Frame`

Run a screener DSL query and flatten the records into a table.

`yoghurt.visualization(query: str) -> Frame`

Run a visualization DSL query and flatten the rows into a table.

`yoghurt.screener_predefined(scr_ids: list[str], *, count: int | None=None, start: int | None=None, use_records_response: bool | None=None, sort_field: str | None=None, sort_type: str | None=None) -> list[ScreenerPredefinedResult]`

Run one or more of Yahoo's predefined screeners.

`yoghurt.trending(region: str | None=None, *, count: int | None=None, use_quotes: bool | None=None, fields: list[str] | None=None, quote_type: str | None=None) -> TrendingResult`

List trending tickers for a region.

`yoghurt.market_calendar(kind: MarketCalendarKind, *, start_date: DateLike | None=None, end_date: DateLike | None=None, limit: int=100, offset: int=0) -> Frame`

Fetch one analysis-ready market-wide event calendar.

`yoghurt.sector(slug: str, *, with_returns: bool | None=None) -> SectorResult`

Fetch sector overview, performance, top holdings, and industries.

`yoghurt.market_summary() -> list[MarketSummaryQuote]`

Fetch a global market summary: indices, futures, forex, crypto.

`yoghurt.market_info(*, modules: list[str] | None=None) -> MarketInfoResult`

Fetch commodity and currency market data.

`yoghurt.market_time(*, key: str | None=None) -> MarketTimeResult`

Show current market hours and session status.

`yoghurt.screener_instrument_fields(instrument: str) -> ScreenerInstrumentFieldsResult`

List every field available for a Yahoo data-platform entity.

`yoghurt.timeseries_fields(*, type: str | None=None) -> TimeseriesFieldsResult`

List available fundamentals timeseries field names for a type.

`yoghurt.screener_discover(*, modules: list[str] | None=None, count: int | None=None) -> ScreenerDiscoverResult`

Discover investment ideas from Yahoo screener modules.

`yoghurt.raw(path: str, params: dict[str, ParamValue] | None=None, *, use_crumb: bool=True) -> dict[str, Any]`

Call an arbitrary Yahoo path with pre-serialized wire params.

`yoghurt.configure(*, timeout: httpx.Timeout | None=None, use_session_cache: bool=True, refresh_session: bool=False, session_cache_path: Path | None=None) -> None`

Set options for the library's shared Yahoo client.

<!-- END GENERATED PYTHON REFERENCE -->
