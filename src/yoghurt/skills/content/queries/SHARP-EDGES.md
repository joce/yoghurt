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

## Screener industry strings don't match assetProfile spelling

**Severity:** medium

The screener's `industry` field uses Yahoo's em-dash taxonomy
(`Software—Application`, `Software—Infrastructure`), while the
quoteSummary `assetProfile` module spells the same industry with a spaced
hyphen (`Software - Application`). Feeding the assetProfile string into a
screener `WHERE` clause silently returns an empty frame — zero matches is
the normal empty-frame contract, so nothing errors.

Wrong way: piping `asset_profile.industry` straight into a screener query:

```python
ind = Ticker("ADBE").quote_summary(modules=["assetProfile"]).asset_profile.industry
# 'Software - Application' — spaced hyphen; the screener will never match it
yoghurt.screener(f"SELECT ticker FROM EQUITY WHERE industry = '{ind}'")  # empty frame
```

Right way: read the screener's own spelling first — `SELECT` the
`industry` column on a broad query (or see `screener-instrument-fields
equity`; `industry` is dropdown-supported) — then filter with that string:

```python
tech = yoghurt.screener(
    "SELECT ticker, industry FROM EQUITY "
    "WHERE region = 'us' AND sector = 'Technology' "
    "ORDER BY intradaymarketcap DESC LIMIT 25"
).to_polars()
# industry column reads 'Software—Application' (em dash) — use that exact string
peers = yoghurt.screener(
    "SELECT ticker, companyshortname, intradaymarketcap FROM EQUITY "
    "WHERE region = 'us' AND industry = 'Software—Application' "
    "ORDER BY intradaymarketcap DESC LIMIT 12"
).to_polars()
```

Evidence: 2026-07-12, verified live. `assetProfile` for ADBE returns
`'Software - Application'`; a screener `WHERE` with that string returns an
empty frame, while `'Software—Application'` returns SAP/SHOP/CRM/ADBE/INTU.

## Screener and visualization use different key casings

**Severity:** low

The `screener()` route requests unformatted values and returns camelCase
record keys (`marketCap`,
`peRatioLtm`). The `visualization()` route returns snake_case or dotted
keys (`intradaymarketcap`, `peratio.lasttwelvemonths`) matching what you
wrote in `SELECT`.

Right way: expect `screener()` output columns to differ from your `SELECT`
clause's exact spelling (Yahoo remaps them); expect `visualization()`
output columns to match your `SELECT` clause verbatim.

Evidence: DSL grammar and endpoint behavior, ongoing.
