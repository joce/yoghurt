# Fundamentals

Company financials and structured fundamentals data: quote-summary modules
and the fundamentals timeseries endpoint.

## Quote summary

```python
from yoghurt import Ticker

summary = Ticker("AAPL").quote_summary(
    modules=["price", "summaryDetail", "financialsTemplate"]
)
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
`yoghurt quote-summary --help --verbose`.

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

The observed `--type` reference is in `yoghurt timeseries --help --verbose`. See
[SHARP-EDGES.md](SHARP-EDGES.md) before requesting
`spEarningsReleaseEvents`.

## Financial analysis bundle

Use the convenience orchestrator when the task needs statements, valuation,
analyst estimates, and ownership together:

```python
analysis = Ticker("AAPL").financial_analysis()
income = analysis.income_statement.to_polars()
valuation = analysis.valuation_history.to_polars()
ownership = analysis.institutional_ownership.to_polars()
```

`financial_analysis()` deliberately performs one `timeseries()` request and
one `quote_summary()` request. It returns 17 stable `Frame` fields; modules
that do not apply to the symbol are empty frames with declared columns.

The derived CLI form emits one JSON object keyed by table name:

```bash
uv run yoghurt financial-analysis AAPL
```

Use `timeseries()` or `quote_summary()` directly when raw retrieval or a
different type/module selection is required.

## Parameters

Use ordinary help for parameters and verbose help for full module/type catalogs:

```bash
uv run yoghurt quote-summary --help --verbose
uv run yoghurt timeseries --help --verbose
uv run yoghurt financial-analysis --help
```

## Workflow: financial tables and currencies

Prerequisites: install `yoghurt`, allow Yahoo access, and use a writable directory.
This example uses an operating company; an ETF may have empty statement tables.

```python
import yoghurt

company = yoghurt.Ticker("AAPL")
quote = company.quote()
analysis = company.financial_analysis()
tables = {
    "income_statement": analysis.income_statement,
    "cash_flow": analysis.cash_flow,
    "valuation_history": analysis.valuation_history,
}
for name, table in tables.items():
    table.save_parquet(f"{name}.parquet")
income = tables["income_statement"].to_polars()
trading_currency = quote.currency
reporting_currencies = (
    income.get_column("currency_code").drop_nulls().unique().to_list()
)
```

`analysis` contains 17 frames. The three selected tables have `type`,
`as_of_date`, `period_type`, `currency_code`, and `value` columns. Each file is
independent; the bundle itself has no `save_parquet()` method. Empty tables
retain their schema. Missing fields/values remain missing, not zero earnings.

Compare `trading_currency` with each row's `currency_code`; a listing's trading
currency need not be its reporting currency. No foreign-exchange conversion or
unit normalization is performed. Monetary amounts, per-share amounts, share
counts, and valuation ratios coexist under different `type` values: select a
metric and period before summing or comparing. Do not assume values are millions
or every numeric field is money. Currency metadata may itself be absent.

`financial_analysis()` makes two source requests; a Yahoo/transport failure or
invalid source shape raises a typed error instead of returning a partial bundle.
Use `timeseries()`/`quote_summary()` to inspect sources and request narrower
selections. Empty tables can mean instrument-specific absence, not failed
transport; inspect the source before concluding the company has no data.
