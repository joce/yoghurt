# Dataframes

Every tabular result in yoghurt — `Chart`, `Spark`, `Timeseries`'s four
frames, and `screener()`/`visualization()` results — shares one conversion
vocabulary. Conversions take no shaping arguments: the frame's columns and
row order are already final.

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

## Chart and timeseries frames

`Chart`/`Spark` are `Frame` subclasses with extra typed attributes
(`.meta`, and `.events` on `Chart`):

```python
chart = yoghurt.Ticker("AAPL").chart(interval="1d")
bars = chart.to_polars()
meta = chart.meta
```

`Timeseries` bundles four separate frames rather than one:

```python
data = yoghurt.Ticker("AAPL").timeseries()
fundamentals_df = data.fundamentals.to_polars()
ratings_df = data.analyst_ratings.to_polars()
```

## Parquet from the CLI

`chart`, `screener`, and `visualization` can write Parquet directly instead
of JSON:

```bash
uv run yoghurt chart AAPL --interval 1d --format parquet --out aapl_1d.parquet
```

## Empty results

A query with zero matches returns an empty `Frame` (zero rows, not `None`
and not an exception). `to_polars()` on an empty frame returns a
zero-row `DataFrame`; check `.height` (polars) or `len(...)` before
assuming rows exist.
