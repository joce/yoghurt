# Queries

`screener()` and `visualization()` share one SQL-flavored DSL, compiled to
the JSON body Yahoo's `/v1/finance/screener` and `/v1/finance/visualization`
endpoints expect. Both are library functions that return a `Frame`; the CLI
commands of the same name print the raw JSON instead.

## Two routes, one grammar

| Route | Use it for | Response keys |
| --- | --- | --- |
| `screener()` | Filtering a single Yahoo asset class (`EQUITY`, `ETF`, `MUTUALFUND`, `INDEX`, `BOND`, `CURRENCY`, `COMMODITY`, `FUTURE`, `OPTION`, `WARRANT`, `CRYPTOCURRENCY`) | camelCase (`marketCap`, `peRatioLtm`) |
| `visualization()` | Data-platform entities: earnings/economic/IPO/split calendars, insider transactions, research reports, cross-entity aggregations | snake_case or dotted (`intradaymarketcap`, `peratio.lasttwelvemonths`) |

The `FROM` clause routes automatically: an all-uppercase, no-underscore
bareword (`EQUITY`) picks the screener's asset-class routing; anything else
(`sp_earnings`, `INSIDER_TRANSACTION`, multiple entities) picks the
data-platform entity routing.

## Screener example

```python
import yoghurt

tech = yoghurt.screener(
    "SELECT ticker, intradaymarketcap FROM EQUITY "
    "WHERE region = 'us' AND sector = 'Technology' "
    "ORDER BY intradaymarketcap DESC LIMIT 25"
).to_polars()
```

CLI equivalent:

```bash
uv run yoghurt screener --query "SELECT ticker, intradaymarketcap FROM EQUITY WHERE region = 'us' AND sector = 'Technology' ORDER BY intradaymarketcap DESC LIMIT 25"
```

## Visualization example

```python
insiders = yoghurt.visualization(
    "SELECT ticker, transactiondate, shares "
    "FROM INSIDER_TRANSACTION WHERE ticker = 'AAPL' "
    "ORDER BY transactiondate DESC LIMIT 50"
).to_polars()
```

## Custom market-wide stock splits

Use `market_calendar("splits")` for the standard normalized date-window
surface. Reach for the lower-level `visualization()` entity when custom fields
or predicates are required:

```python
splits = yoghurt.visualization(
    "SELECT ticker, startdatetime FROM splits "
    "WHERE startdatetime BETWEEN '2026-05-09' AND '2026-05-16' LIMIT 25"
).to_polars()
```

See [SHARP-EDGES.md](SHARP-EDGES.md#stock-splits-are-not-symbol-bound) —
per-symbol `calendar-events` `secReports` is SEC filings, not splits.

## Discovering fields

```bash
uv run yoghurt screener-instrument-fields equity
uv run yoghurt screener-instrument-fields insider_transaction
```

Lists every field, type, and quick-pick operator available for an asset
class or data-platform entity — use it before writing a `WHERE` clause
against an unfamiliar entity.

## Grammar

Beyond `SELECT ... FROM ... WHERE ... ORDER BY ... LIMIT`, the DSL supports
`BETWEEN`/`IN`/`NOT IN` predicates, `AND`/`OR`/`NOT` with parentheses for
grouping, and an `AGGREGATE date_hist(field, '1d') FROM ... JOIN BY ...
FILL ...` form for cross-entity time histograms. Single-quoted strings only
(`'us'`, not `"us"`). Command-level parameters and more examples live in
`--help`:

```bash
uv run yoghurt screener --help
uv run yoghurt visualization --help
```
