# yoghurt

[![CI](https://github.com/joce/yoghurt/actions/workflows/ci.yml/badge.svg)](https://github.com/joce/yoghurt/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/joce/yoghurt/graph/badge.svg)](https://codecov.io/gh/joce/yoghurt)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub License](https://img.shields.io/github/license/joce/yoghurt)](https://github.com/joce/yoghurt/blob/main/LICENSE)

Yahoo!-Originated Graphs, Histories, Updates, Returns & Tickers.

Yoghurt brings Yahoo Finance data to Python, agents, and the command line.
Use the CLI when you want Yahoo's raw JSON; use the typed Python API when you
want models and analysis-ready tables.

## Features

- Raw Yahoo Finance JSON on stdout, with no pretty-printing or interpretation.
- Analysis-ready adjusted history for one or more symbols in the library and
  CLI, with JSON and Parquet output.
- Analysis-ready financial statement, valuation, analyst, and ownership tables
  for one symbol in the library and JSON-only CLI.
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

## Agent skill

Yoghurt ships an Agent Skills–standard skill (a `SKILL.md` package readable
by Claude Code, Codex CLI, Cursor, Gemini CLI, Copilot, Pi, and other
agents) that teaches coding agents both the library and the CLI: idiomatic
patterns, endpoint routing, and corpus-proven pitfalls. Install it into an
agent's skill directory by name:

```powershell
yoghurt skills install --agent claude
```

Named targets: `claude`, `codex`, `copilot`, `cursor`, `gemini`, `pi`
(comma-separable). Add `--project` to install into the current repository's
agent directories instead of your user-level ones, or `--to PATH` for any
other skills root. Installs are plain copies — re-run `yoghurt skills
install` after upgrading yoghurt. `yoghurt skills list` shows every named
location with its installed version, and `yoghurt skills uninstall` removes
installs (it never touches a directory it does not own). See
`yoghurt skills --help`.

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

Fetch one month of adjusted daily history (the default), or a multi-symbol
year for analysis:

```powershell
uv run yoghurt history AAPL
uv run yoghurt history AAPL,MSFT --period 1y --interval 1d
```

Library equivalents return the same stable long-form schema:

```python
aapl = yoghurt.Ticker("AAPL").history().to_polars()
portfolio = yoghurt.history(["AAPL", "MSFT"], period="1y").to_polars()
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

## Python library

Yoghurt is also an importable, typed Python library. `Ticker` methods and
module-level functions return typed pydantic models or analysis-ready frames;
frames provide `to_polars()`, `to_pandas()` (`pip install yoghurt[pandas]`),
`to_arrow()`, `to_dicts()`, and `save_parquet()`.

```python
import yoghurt

bars = yoghurt.Ticker("AAPL").chart(interval="1d").to_polars()
history = yoghurt.history(["AAPL", "MSFT"], period="1y").to_polars()
earnings = yoghurt.market_calendar("earnings").to_polars()
quote = yoghurt.Ticker("AAPL").quote()
analysis = yoghurt.Ticker("AAPL").financial_analysis()
income_statement = analysis.income_statement.to_polars()
tech = yoghurt.screener(
    "SELECT ticker, intradaymarketcap FROM EQUITY "
    "WHERE region = 'us' AND sector = 'Technology' "
    "ORDER BY intradaymarketcap DESC LIMIT 25"
).to_polars()
```

Use `yoghurt.raw(path, params)` for any Yahoo query path without a dedicated
typed wrapper. Symbol lookups raise `SymbolNotFoundError`, Yahoo-reported
failures raise `YahooApiError`, empty queries return empty collections or
frames, and transport failures raise `YahooRequestError` or
`YahooUnavailableError`.

Typed `quote()` and `quotes()` return complete `Quote` objects. For exact field
projections, use `raw("/v7/finance/quote", {"symbols": "AAPL", "fields":
"symbol,regularMarketPrice"})` or the CLI `--fields` option. Typed methods
always request unformatted values; CLI and `raw()` retain formatting control.
`Ticker.options(straddle=True)` returns paired `straddles` on each expiration;
either contract leg can be absent. Ordinary responses contain `calls` and `puts`.

Models and frame wrappers are shallowly frozen: nested lists, dictionaries,
and the underlying Polars frame can still be mutated. History rejects incomplete
adjustment data, including a latest bar without adjusted close, rather than
mixing raw and adjusted prices. Initialize the shared client after a POSIX fork;
using an already initialized client in a forked child is unsupported.

### Pandas-wide history

Multi-symbol history is long-form by default. Pivot it after conversion when
an analysis needs a timestamp-by-symbol Pandas matrix, such as portfolio
returns or correlations:

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

This produces hierarchical `(field, symbol)` columns without adding a second
history return shape. Keep the long-form table for per-symbol processing such
as TA-Lib.

## Parquet output

`chart`, `history`, `screener`, and `visualization` can write a typed Parquet table
instead of raw JSON. Parquet is built in — no extra install step needed.

Pass `--format parquet --out PATH`:

```powershell
uv run yoghurt chart AAPL --interval 1d --format parquet --out aapl_1d.parquet
uv run yoghurt history AAPL,MSFT --period 1y --format parquet --out history.parquet
uv run yoghurt screener --query "SELECT ticker, intradaymarketcap FROM EQUITY \
  WHERE region = 'us' AND sector = 'Technology' ORDER BY intradaymarketcap DESC LIMIT 50" \
  --format parquet --out tech.parquet
uv run yoghurt visualization --query "SELECT ticker, startdatetime FROM sp_earnings \
  WHERE region = 'us' AND startdatetime BETWEEN '2026-05-09' AND '2026-05-16' LIMIT 25" \
  --format parquet --out earnings.parquet
```

On success a single JSON descriptor line goes to stdout (the file format,
out path, row count, byte size). Parquet writes are scoped to these four
intrinsically tabular commands; every other command stays JSON-only. The
chart schema is fixed (`ts`, `open`, `high`, `low`, `close`, `volume`,
`adj_close`). History uses `symbol`, `ts`, adjusted `open`, `high`, `low`,
`close`, and unadjusted `volume`; screener and visualization tables are
inferred from the response. AGGREGATE visualization queries cannot be flattened and are
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
| `history` | Fetch adjusted historical OHLC data for one or more symbols. |
| `options` | Fetch the option chain for a symbol. |
| `quote-summary` | Fetch quoteSummary modules for a symbol. |
| `quote-type` | Fetch instrument classification metadata for a symbol. |
| `spark` | Fetch sparkline price series for one or more symbols. |

**Discovery (find symbols, build custom queries)**

| Command | Yahoo data |
| --- | --- |
| `search` | Search instruments, news, lists, navigation, and research metadata. |
| `lookup` | Search paged instruments with optional asset-type filters. |
| `screener-predefined` | Run one or more of Yahoo's predefined screeners. |
| `visualization` | Query any Yahoo data-platform entity via a SQL-flavored DSL. |
| `screener` | Query any Yahoo asset class via a SQL-flavored DSL. |
| `screener-discover` | Discover investment ideas from Yahoo screener modules. |

**Symbol-bound analysis**

| Command | Yahoo data |
| --- | --- |
| `timeseries` | Fetch fundamentals timeseries for a symbol. |
| `financial-analysis` | Fetch analysis-ready financial tables for a symbol. |
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
| `market-calendar` | Fetch earnings, IPO, economic, or split events across the market. |
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

### Search and lookup

Use `search` for Yahoo's broad search experience: public instruments,
private-company profiles, related news, saved lists, navigation links, and
research-report metadata. Use `lookup` when the result should be only
instruments, paged and optionally filtered by asset type:

```python
matches = yoghurt.search(
    "Appel",
    fuzzy=True,
    quotes_count=5,
    include_research_reports=True,
)
symbols = [match.symbol for match in matches.quotes if match.symbol is not None]

page = yoghurt.lookup("Apple", type="equity", count=25)
equities = page.documents
```

Both functions return typed pydantic models. An unmatched lookup is a
`LookupResult` with an empty `documents` list. Search keeps each empty result
family as an empty list. Private-company and cultural-asset matches share
search's `quotes` list but have no symbol.

The CLI prints the unchanged Yahoo response and additionally exposes
`--lang`/`--region`; the Python functions deliberately use their command
defaults and do not accept per-call locale overrides:

```powershell
uv run yoghurt search Airbus --lang fr-FR --region FR
uv run yoghurt lookup Bitcoin --type cryptocurrency --count 25
```

### Market-wide calendars

`market_calendar()` returns analysis-ready earnings, IPO, economic-event, or
stock-split rows across the market:

```python
earnings = yoghurt.market_calendar(
    "earnings",
    start_date="2026-07-20",
    end_date="2026-07-25",
    limit=100,
).to_polars()
```

The date window is inclusive and defaults to today through seven days ahead
in UTC. Results are chronological; `offset` supports manual pagination. Each
kind keeps a stable schema even when no rows match:

| Kind | Columns |
| --- | --- |
| `earnings` | `symbol`, `company_name`, `market_cap`, `event_name`, `event_at`, `timing`, `eps_estimate`, `eps_actual`, `eps_surprise_percent` |
| `ipo` | `symbol`, `company_name`, `exchange`, `filing_date`, `event_at`, `amended_date`, `price_from`, `price_to`, `offer_price`, `currency`, `shares`, `deal_type` |
| `economic` | `event`, `country_code`, `event_at`, `period`, `actual`, `expected`, `prior`, `revised` |
| `splits` | `symbol`, `company_name`, `payable_at`, `optionable`, `old_share_worth`, `new_share_worth` |

The CLI emits the same rows as JSON or Parquet and exposes locale overrides:

```powershell
uv run yoghurt market-calendar earnings --start-date 2026-07-20 --end-date 2026-07-25
uv run yoghurt market-calendar economic --format parquet --out economic.parquet
```

Use `Ticker.calendar_events()` for symbol-bound events. Use `visualization()`
when custom calendar fields or filters matter more than the stable schemas.

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
`--include-pre-post`. Use `--range` for a relative window (`1d`, `5d`, `1mo`,
`3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, or `max`) instead of
`--period1`/`--period2`. Supported intervals are `1m`, `2m`, `5m`, `15m`,
`30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, and `3mo`.

### History

`history` is intentionally separate from `chart`. `chart` is pure retrieval:
raw OHLC and adjusted close plus typed metadata/events in the library, or the
unchanged Yahoo response in the CLI. `history` is analysis-ready: it computes
`adj_close / close` per row, applies that factor to open/high/low/close, leaves
volume unchanged, and combines requested symbols into one long-form table.
Supported intervals are `1d`, `5d`, `1wk`, `1mo`, and `3mo`; use `chart` for
intraday data because Yahoo omits adjusted close from intraday responses.

```powershell
uv run yoghurt history AAPL,MSFT --period 1y --interval 1d
uv run yoghurt history SPY --start 2025-01-01 --end 2026-01-01
```

No heuristic price repair is applied. If any price-bearing row lacks a usable
adjustment factor, `history` rejects the response instead of mixing raw and
adjusted prices. Empty responses remain empty tables. Repair can be revisited
if corpus-backed Yahoo defects establish a safe rule.

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

### Financial analysis

`Ticker.financial_analysis()` deliberately makes one `timeseries()` request
for statement and valuation history and one `quote_summary()` request for
analyst and ownership data. It returns a frozen `FinancialAnalysis` bundle:

```python
analysis = yoghurt.Ticker("AAPL").financial_analysis()
income = analysis.income_statement.to_polars()
targets = analysis.analyst_price_targets.to_polars()
institutions = analysis.institutional_ownership.to_polars()
```

The 17 fields cover income statement, balance sheet, cash flow, valuation
history, earnings and revenue estimates, earnings history, EPS trends and
revisions, analyst price targets, stock/industry/sector/index growth,
major/institutional/fund ownership, insider holdings and transactions, and
insider purchase activity. Every field is a `Frame`; unavailable or
inapplicable data is an empty frame with the same stable columns.

The derived CLI command emits one JSON object keyed by those table field names,
with row arrays as values:

```powershell
uv run yoghurt financial-analysis AAPL
```

It is JSON-only. Use each library frame's `save_parquet()` method when Parquet
files are needed.

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

Endpoint commands write Yahoo response bodies to stdout exactly as returned.
The derived `history`, `financial-analysis`, and `market-calendar` commands
emit normalized analysis tables instead. Raw endpoint output remains easy to
pipe into tools that expect JSON:

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
