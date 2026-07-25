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
