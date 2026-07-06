# Fundamentals

Company financials and structured fundamentals data: quote-summary modules
and the fundamentals timeseries endpoint.

## Quote summary

```python
from yoghurt import Ticker

summary = Ticker("AAPL").quote_summary(modules=["price", "summaryDetail", "financialsTemplate"])
```

`quote_summary()` returns a typed `QuoteSummary` with one optional field per
requested-and-applicable module — 41 modules total, all typed. A module
that does not apply to the symbol's instrument type comes back `None`
rather than raising.

CLI equivalent:

```bash
uv run yoghurt quote-summary AAPL --modules price,summaryDetail,financialsTemplate
```

The full module list (41 modules, with descriptions) is in
`yoghurt quote-summary --help`.

## Fundamentals timeseries

```python
data = Ticker("AAPL").timeseries()
fundamentals = data.fundamentals.to_polars()
```

`timeseries()` returns a `Timeseries` object: four typed frames
(`fundamentals`, `geographic_segments`, `economic_events`,
`analyst_ratings`) plus `empty_types`/`unrecognized_types` bookkeeping
tuples for any requested `type` Yahoo didn't recognize or returned no data
for. Omitted `period1`/`period2` default to a recent quote-page-style
window.

CLI equivalent:

```bash
uv run yoghurt timeseries AAPL
```

The observed `--type` reference is in `yoghurt timeseries --help`. See
[SHARP-EDGES.md](SHARP-EDGES.md) before requesting
`spEarningsReleaseEvents`.

## Parameters

Full parameter lists, module names, and type names live in `--help`:

```bash
uv run yoghurt quote-summary --help
uv run yoghurt timeseries --help
```
