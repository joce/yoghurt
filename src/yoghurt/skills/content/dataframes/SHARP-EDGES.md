# Sharp edges: dataframes

## `to_pandas()` and `to_arrow()` need an extra

**Severity:** medium

`to_polars()` works out of the box (polars is a core dependency).
`to_pandas()` and `to_arrow()` raise unless the optional `pandas` extra is
installed.

Wrong way: calling `frame.to_pandas()` in an environment where only
`pip install yoghurt` was run.

Right way:

```bash
pip install "yoghurt[pandas]"
```

then `to_pandas()`/`to_arrow()` work normally.

Evidence: library design constraint, ongoing — `to_pandas()`/`to_arrow()`
raise a clear message naming the extra when it is missing.
