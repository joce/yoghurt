# Sharp edges: queries

## Stock splits are not symbol-bound

**Severity:** medium

Stock splits are not available on any per-symbol endpoint. Market-wide
splits live on the `visualization()` route as the `splits` entity.
Per-symbol `calendar-events` with `modules=["secReports"]` is SEC filings
(10-K, 10-Q, 8-K, etc.), not stock splits — see
[analysis/SHARP-EDGES.md](../analysis/SHARP-EDGES.md#secreports-is-sec-filings-not-stock-splits).

Wrong way: looking for a symbol's split history via `Ticker(...).calendar_events(modules=["secReports"])`.

Right way:

```python
splits = yoghurt.visualization(
    "SELECT ticker, startdatetime FROM splits WHERE ticker = 'AAPL' "
    "ORDER BY startdatetime DESC LIMIT 10"
).to_polars()
```

Evidence: 2026-07-05, network-inspected and verified through
`visualization()`.

## Screener and visualization use different key casings

**Severity:** low

The `screener()` route only responds with `formatted=true` (yoghurt sets
this by default) and returns camelCase record keys (`marketCap`,
`peRatioLtm`). The `visualization()` route returns snake_case or dotted
keys (`intradaymarketcap`, `peratio.lasttwelvemonths`) matching what you
wrote in `SELECT`.

Right way: expect `screener()` output columns to differ from your `SELECT`
clause's exact spelling (Yahoo remaps them); expect `visualization()`
output columns to match your `SELECT` clause verbatim.

Evidence: DSL grammar and endpoint behavior, ongoing.
