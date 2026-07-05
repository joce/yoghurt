# yoghurt

[![CI](https://github.com/joce/yoghurt/actions/workflows/ci.yml/badge.svg)](https://github.com/joce/yoghurt/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/joce/yoghurt/graph/badge.svg)](https://codecov.io/gh/joce/yoghurt)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub License](https://img.shields.io/github/license/joce/yoghurt)](https://github.com/joce/yoghurt/blob/main/LICENSE)

Yahoo!-Originated Graphs, Histories, Updates, Returns & Tickers.

Yoghurt brings Yahoo Finance's HTTP endpoints to the command line and to
Python. It is built for scripts, agents, and quick terminal work that needs
the JSON returned by Yahoo's finance endpoints.

The CLI stays deliberately close to the source: it prints Yahoo's response
bodies as-is and adds no discovery API beyond CLI help. The library layer
(below) does model Yahoo's responses as typed pydantic structures, with two
deliberate exceptions (`screener()`/`visualization()`, dynamic-column DSL
results returned as `Frame`s).

## Library

Yoghurt is also an importable, typed Python library:

```python
import yoghurt

bars = yoghurt.Ticker("AAPL").chart(interval="1d").to_polars()
quote = yoghurt.Ticker("AAPL").quote()
tech = yoghurt.screener(
    "SELECT ticker, intradaymarketcap FROM EQUITY "
    "WHERE region = 'us' AND sector = 'Technology' "
    "ORDER BY intradaymarketcap DESC LIMIT 25"
).to_polars()
```

Three tiers, all sharing one Yahoo session (cookies and crumb cached exactly
like the CLI):

1. **Typed** — `Ticker` methods and module-level functions. Every endpoint
   returns a typed result except `screener()`/`visualization()`, which
   return a `Frame` with `to_polars()`, `to_pandas()`
   (`pip install yoghurt[pandas]`), `to_arrow()`, `to_dicts()`, and
   `save_parquet()`: both are SQL-flavored DSLs over caller-chosen,
   dynamic column lists, so their row shape is a table, not a fixed
   pydantic model, by design. `chart`/`spark` return `Chart`/`Spark` (also
   `Frame` subclasses) whose `.meta` is typed `ChartMeta` (pydantic) and
   whose `.events` is typed `ChartEvents` when the response carries one.
   `Ticker.timeseries()` returns `Timeseries`: four typed frames
   (fundamentals, geographic segments, economic events, analyst ratings)
   plus `empty_types`/`unrecognized_types` bookkeeping. `Ticker.quote()`/
   `quotes()` return `Quote` (pydantic) models. `Ticker.options()` returns
   a typed `OptionChain` (pydantic), including the underlying security's
   `Quote`. `Ticker.quote_summary()` returns a typed `QuoteSummary`
   (pydantic), with one optional field per requested-and-applicable
   `quote-summary` module (41 total, all typed). Every other `Ticker`
   method and market-wide/introspection function (`quote_type`,
   `calendar_events`, `recommendations`, `stock_recommender`,
   `price_insights`, `insights`, `analyst`, `ratings_top`, `trending`,
   `market_summary`, `market_info`, `market_time`, `sector`,
   `screener_predefined`, `screener_instrument_fields`,
   `timeseries_fields`, `screener_discover`) returns its own typed
   pydantic model.
2. **Parsed raw** — `yoghurt.raw(path, params)` for any Yahoo query path.
3. **Raw async** — `yoghurt.YahooClient`, the async client the CLI itself
   uses.

Errors follow one contract: symbol lookups raise `SymbolNotFoundError`
(carrying `.symbol`), Yahoo-reported failures raise `YahooApiError`
(`.code`, `.description`), queries with zero matches return empty frames,
and transport failures raise `YahooRequestError` or `YahooUnavailableError`.
The library never prints and never prompts; `yoghurt.configure(...)` adjusts
session-cache behavior before first use.

## Features

- Raw Yahoo Finance JSON on stdout, with no pretty-printing or interpretation.
- Endpoint-specific commands for common Yahoo Finance data.
- A SQL-flavored DSL (`screener`, `visualization`) for ad-hoc filters and
  cross-entity queries against Yahoo's data-platform endpoints.
- Generated help that includes examples, parameters, field references, modules,
  or types when yoghurt knows them.
- Reusable Yahoo session cache for faster one-shot CLI calls.
- A `raw` command for Yahoo query paths that do not have dedicated metadata yet.

## Install

Yoghurt requires Python 3.10+.

```powershell
pip install yoghurt
```

`screener`/`visualization` results support `to_pandas()` when the optional
`pandas` extra is installed:

```powershell
pip install "yoghurt[pandas]"
```

```powershell
yoghurt --help
```

### Install From Source

For development, or to run against an unreleased checkout, use
[uv](https://docs.astral.sh/uv/):

```powershell
uv sync --all-groups
```

Run the CLI from the repository:

```powershell
uv run yoghurt --help
```

Or install it as a package from a local checkout:

```powershell
uv tool install .
yoghurt --help
```

## Quick Start

Fetch quotes for a few symbols:

```powershell
uv run yoghurt quote AAPL,MSFT,NVDA
```

Request specific quote fields:

```powershell
uv run yoghurt quote AAPL,MSFT --fields symbol,longName,companyLogoUrl,regularMarketPrice,overnightMarketPrice
```

See [QUOTE_FIELDS.md](src/yoghurt/docs/QUOTE_FIELDS.md) for the full quote field reference and
best-effort meanings.

Fetch selected quote summary modules:

```powershell
uv run yoghurt quote-summary ^GSPC --modules price,summaryDetail,pageViews,financialsTemplate
```

See [QUOTE_SUMMARY_MODULES.md](src/yoghurt/docs/QUOTE_SUMMARY_MODULES.md) for the researched
quote-summary module list and descriptions.

Fetch quote-type metadata using Yahoo's path-symbol endpoint:

```powershell
uv run yoghurt quote-type ^GSPC
```

Fetch chart data for a recent window:

```powershell
uv run yoghurt chart AAPL
```

Fetch quote-page sparkline data:

```powershell
uv run yoghurt spark AAPL,MSFT
```

Quote-page probes have observed `1d` and `24h` spark ranges; pass values such
as `--range 24h` through when Yahoo supports them.

Fetch recommended symbols for a quote page:

```powershell
uv run yoghurt recommendations-by-symbol AAPL
```

Fetch Yahoo calendar events:

```powershell
uv run yoghurt calendar-events AAPL
uv run yoghurt calendar-events AAPL --modules ipoEvents
uv run yoghurt calendar-events AAPL --modules secReports
uv run yoghurt calendar-events AAPL --modules economicEvents --include-all-economic-events
```

Confirmed `--modules` values for `calendar-events`:

| Module | Returns |
| --- | --- |
| `earnings` | Upcoming and recent earnings dates and EPS estimates (default). |
| `economicEvents` | Macro economic calendar events (CPI, Fed decisions, employment reports, etc.). |
| `ipoEvents` | Upcoming and recent IPO events. |
| `secReports` | Recent SEC filing events (10-K, 10-Q, 8-K, etc.). |

Fetch sector data:

```powershell
uv run yoghurt sector technology
uv run yoghurt sector financial-services --with-returns
```

Confirmed sector slugs: `technology`, `financial-services`, `consumer-cyclical`,
`communication-services`, `healthcare`, `industrials`, `consumer-defensive`,
`energy`, `basic-materials`, `real-estate`, `utilities`.

Run a predefined Yahoo screener:

```powershell
uv run yoghurt screener-predefined MOST_ACTIVES
uv run yoghurt screener-predefined DAY_GAINERS_CRYPTOCURRENCIES
uv run yoghurt screener-predefined TOP_OPTIONS_OPEN_INTEREST
```

Confirmed predefined screener IDs:

**Equities — movers and volume**
`MOST_ACTIVES`, `MOST_ACTIVE_PENNY_STOCKS`, `UNUSUAL_VOLUME_STOCKS`,
`DAY_GAINERS`, `DAY_LOSERS`, `MOST_SHORTED_STOCKS`

**Equities — size and price**
`SMALL_CAP_STOCKS`, `LARGE_CAP_STOCKS`, `MOST_EXPENSIVE_STOCKS`,
`HIGHEST_BETA_STOCKS`, `PINK_SHEET_STOCKS`, `SMALL_CAP_GAINERS`

**Equities — technical signals**
`RECENT_52_WEEK_HIGHS`, `RECENT_52_WEEK_LOWS`,
`BULLISH_STOCKS_RIGHT_NOW`, `BEARISH_STOCKS_RIGHT_NOW`

**Equities — analyst and value**
`ANALYST_STRONG_BUY_STOCKS`, `MORNINGSTAR_FIVE_STAR_STOCKS`,
`UNDERVALUED_GROWTH_STOCKS`, `UNDERVALUED_LARGE_CAPS`,
`UNDERVALUED_WIDE_MOAT_STOCKS`, `GROWTH_TECHNOLOGY_STOCKS`,
`AGGRESSIVE_SMALL_CAPS`, `HIGHEST_DIVIDEND_STOCKS`

**Equities — institutional**
`MOST_INSTITUTIONALLY_BOUGHT_LARGE_CAP_STOCKS`,
`MOST_INSTITUTIONALLY_HELD_LARGE_CAP_STOCKS`,
`TOP_STOCKS_OWNED_BY_CATHIE_WOOD`

**Funds and ETFs**
`TOP_MUTUAL_FUNDS`, `SOLID_LARGE_GROWTH_FUNDS`, `SOLID_MIDCAP_GROWTH_FUNDS`,
`CONSERVATIVE_FOREIGN_FUNDS`, `HIGH_YIELD_BOND`, `LARGE_BLEND_ETFS`,
`TECHNOLOGY_ETFS`, `PORTFOLIO_ANCHORS`

**Crypto**
`MOST_ACTIVES_CRYPTOCURRENCIES`, `DAY_GAINERS_CRYPTOCURRENCIES`,
`DAY_LOSERS_CRYPTOCURRENCIES`

**Private companies**
`52_WEEK_GAINERS_PRIVATE_COMPANY`, `RECENTLY_FUNDED_PRIVATE_COMPANY`

**Options**
`DAY_GAINERS_OPTIONS`, `DAY_LOSERS_OPTIONS`,
`TOP_OPTIONS_OPEN_INTEREST`, `TOP_OPTIONS_IMPLIED_VOLATALITY` *(Yahoo typo)*

Fetch an option chain using Yahoo's default expiration:

```powershell
uv run yoghurt options AAPL
```

Fetch current market session status and trading hours:

```powershell
uv run yoghurt market-time
```

Fetch analyst intelligence for a symbol (put/call ratio, news summary, price
targets, and ratings):

```powershell
uv run yoghurt analyst AAPL
```

Run a custom screener or cross-entity query with the SQL-flavored DSL:

```powershell
uv run yoghurt screener --query "
  SELECT ticker, intradaymarketcap, sector, peratio.lasttwelvemonths
  FROM EQUITY
  WHERE region = 'us'
    AND sector = 'Technology'
    AND intradaymarketcap >= 10e9
  ORDER BY intradaymarketcap DESC
  LIMIT 25"

uv run yoghurt visualization --query "
  SELECT ticker, transactiondate, shares
  FROM INSIDER_TRANSACTION
  WHERE ticker = 'AAPL'
  ORDER BY transactiondate DESC
  LIMIT 50"
```

List the fields, types, and operators available for a given asset class or
entity (e.g. for use in a `screener` or `visualization` query):

```powershell
uv run yoghurt screener-instrument-fields equity
uv run yoghurt screener-instrument-fields insider_transaction
```

See [QUERY_DSL.md](src/yoghurt/docs/QUERY_DSL.md) for the full DSL reference: grammar,
operators, entity routing, body shape, premium-locked entities, and more
examples.

Pass through a Yahoo query path directly:

```powershell
uv run yoghurt raw /v7/finance/quote --param symbols=AAPL,MSFT --param formatted=true
```

## Parquet output

`chart`, `screener`, and `visualization` can write a typed Parquet table
instead of raw JSON. Parquet is built in — no extra install step needed.

Pass `--format parquet --out PATH`:

```powershell
uv run yoghurt chart AAPL --interval 1d --format parquet --out aapl_1d.parquet
uv run yoghurt screener --query "SELECT ticker, intradaymarketcap FROM EQUITY \
  WHERE region = 'us' AND sector = 'Technology' ORDER BY intradaymarketcap DESC LIMIT 50" \
  --format parquet --out tech.parquet
uv run yoghurt visualization --query "SELECT ticker, startdatetime FROM sp_earnings \
  WHERE region = 'us' AND startdatetime BETWEEN '2026-05-09' AND '2026-05-16' LIMIT 25" \
  --format parquet --out earnings.parquet
```

On success a single JSON descriptor line goes to stdout (the file format,
out path, row count, byte size). Parquet writes are scoped to these three
intrinsically tabular commands; every other command stays JSON-only. The
chart schema is fixed (`ts`, `open`, `high`, `low`, `close`, `volume`,
`adj_close`); screener and visualization tables are inferred from the
response. AGGREGATE visualization queries cannot be flattened and are
rejected — use `--format json` for those. Parquet requires scalar cells,
so `--format parquet --formatted` is rejected.

### Screener column names

For the `screener` route, Parquet column names mirror Yahoo's response
record keys, not the names in your `SELECT` clause. Yahoo translates many
DSL filter names (lowercase, dotted) to camelCase keys with suffixes like
`Ltm` or `Percent`. For example, `SELECT intradaymarketcap` produces a
Parquet column named `marketCap`, and responses often include unrequested
columns such as `logoUrl`. See [`docs/screener-fields.md`](docs/screener-fields.md)
for the mapping table.

The `visualization` route preserves SELECT-clause names verbatim, so its
Parquet schema matches what you asked for.

## Commands

Use root help to see the command list:

```powershell
uv run yoghurt --help
```

Current commands, grouped roughly by how often they're reached for:

**Daily-driver fetches**

| Command | Yahoo data |
| --- | --- |
| `quote` | Fetch quotes for one or more symbols. |
| `chart` | Fetch historical OHLC chart data for a symbol. |
| `options` | Fetch the option chain for a symbol. |
| `quote-summary` | Fetch quoteSummary modules for a symbol. |
| `quote-type` | Fetch instrument classification metadata for a symbol. |
| `spark` | Fetch sparkline price series for one or more symbols. |

**Discovery (find symbols, build custom queries)**

| Command | Yahoo data |
| --- | --- |
| `screener-predefined` | Run one or more of Yahoo's predefined screeners. |
| `visualization` | Query any Yahoo data-platform entity via a SQL-flavored DSL. |
| `screener` | Query any Yahoo asset class via a SQL-flavored DSL. |
| `screener-discover` | Discover investment ideas from Yahoo screener modules. |

**Symbol-bound analysis**

| Command | Yahoo data |
| --- | --- |
| `timeseries` | Fetch fundamentals timeseries for a symbol. |
| `calendar-events` | Fetch earnings, IPO, economic, and SEC filing events for a symbol. |
| `analyst` | Fetch analyst intelligence for a symbol. |
| `ratings-top` | Fetch top analyst rating buckets for a symbol. |
| `recommendations-by-symbol` | Fetch related-symbol recommendations for a symbol. |
| `price-insights` | Fetch AI-generated price insights for one or more symbols. |
| `insights` | Fetch research reports and insights for one or more symbols. |

**Market-wide state**

| Command | Yahoo data |
| --- | --- |
| `trending` | List trending tickers for a region. |
| `sector` | Fetch sector overview, performance, top holdings, and industries. |
| `market-summary` | Fetch global market summary: indices, futures, forex, crypto. |
| `market-info` | Fetch commodity and currency market data. |
| `market-time` | Show current market hours and session status. |

**Schema introspection**

| Command | Yahoo data |
| --- | --- |
| `screener-instrument-fields` | List every field available for a Yahoo data-platform entity. |
| `timeseries-fields` | List available fundamentals timeseries field names for a type. |

**Escape hatch**

| Command | Yahoo data |
| --- | --- |
| `raw` | Send raw parameters to any Yahoo query path. |

Each endpoint has its own adaptive help:

```powershell
uv run yoghurt quote --help
uv run yoghurt quote-summary --help
uv run yoghurt calendar-events --help
uv run yoghurt timeseries --help
```

Endpoint help is the primary documentation surface. It shows Yahoo's target
endpoint, accepted parameters, defaults, examples, and common open-ended values
where available.

### Chart

The `chart` command calls Yahoo's `/v8/finance/chart/{symbol}` endpoint without
requesting a crumb:

```powershell
uv run yoghurt chart AAPL
```

When period arguments are omitted, yoghurt uses a recent quote-page-shaped
window: `period1` defaults to three days before execution time, `period2`
defaults to execution time, `--interval` defaults to `1m`, and `--events`
defaults to `div,split,earn`. User-provided events are comma-separated; yoghurt
packs them for Yahoo internally. Extended-hours data is opt-in with
`--include-pre-post`.

### Timeseries

The `timeseries` command can also run with only a ticker:

```powershell
uv run yoghurt timeseries AAPL
```

Its default type list matches the Yahoo quote/analysis page request for
earnings-release, analyst-rating, and economic-event timeseries data. When
period arguments are omitted, yoghurt uses a recent quote-page-style window:
`period1` defaults to three days before execution time and `period2` defaults
to execution time.

See [TIMESERIES_TYPES.md](src/yoghurt/docs/TIMESERIES_TYPES.md) for the observed `--type`
reference with descriptions.

## Dates and Booleans

Date and datetime parameters accept:

- Unix timestamps, such as `1510876800`.
- Date-only values, such as `2017-11-17`.
- ISO datetime values.

Date-only values are converted at UTC midnight before they are sent to Yahoo.
For endpoints with `period1` and `period2`, documented defaults let ticker-only
requests run, `period2` defaults to the current Unix timestamp when omitted, and
yoghurt rejects windows where `period2` is not greater than `period1`. Supplying
`period2` without `period1` is also rejected.

Boolean parameters accept common true and false forms such as `true`, `false`,
`1`, `0`, `yes`, and `no`.

## Session Cache

Most Yahoo endpoints require a cookie and crumb. Yoghurt establishes that session
state automatically and caches it for reuse across CLI calls.

Useful global options:

```powershell
uv run yoghurt --refresh-session quote AAPL
uv run yoghurt --no-session-cache quote AAPL
uv run yoghurt --session-cache C:\tmp\yoghurt-session.json quote AAPL
```

Yoghurt never prints cookies, crumbs, or full session-cache contents.

## Output Contract

Yoghurt writes the Yahoo response body to stdout exactly as returned. This makes
it easy to pipe into tools that expect JSON:

```powershell
uv run yoghurt quote AAPL | jq .
```

Diagnostics and errors are written to stderr.

## Development

Install development dependencies:

```powershell
uv sync --all-groups
```

Run the test suite:

```powershell
uv run pytest
```

Run checks locally:

```powershell
uv run black --check .
uv run ruff format --check --diff .
uv run ruff check .
uv run pyright
uv run pytest -n auto
```

Run the full project check, including Python checks and spelling:

```powershell
uv run tox
```

When adding or changing command metadata, update validation, adaptive help, and
tests together. Then verify the relevant command against Yahoo with its help,
minimal required parameters, and representative optional parameters.

## License

Yoghurt is released under the MIT License. See [LICENSE](LICENSE).
