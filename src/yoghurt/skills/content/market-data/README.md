# Market data

Quotes, charts, sparklines, and option chains — the per-symbol, price-level
endpoints.

## Quotes

```python
from yoghurt import Ticker

quote = Ticker("AAPL").quote()
```

Multiple symbols at once with the module function:

```python
import yoghurt

records = yoghurt.quotes(["AAPL", "MSFT", "NVDA"])
```

CLI equivalent (comma-separated symbols, raw JSON to stdout):

```bash
uv run yoghurt quote AAPL,MSFT,NVDA
```

`Ticker.quote()` raises `SymbolNotFoundError` when Yahoo has no record for
the symbol; `quotes()` silently drops unrecognized symbols from the
returned list instead of raising.

## Charts

```python
bars = yoghurt.Ticker("AAPL").chart(interval="1d").to_polars()
```

`chart()` returns a `Chart` (a `Frame` subclass): OHLCV bars via
`to_polars()`/`to_pandas()`/etc., typed `.meta` (`ChartMeta`), and typed
`.events` when the response carries one (dividends/splits/earnings).
The bar columns are `ts, open, high, low, close, volume, adj_close`
(the time column is `ts`, not `timestamp` or `date`).
Omitted `period1`/`period2` default to a recent quote-page-shaped window.

CLI equivalent:

```bash
uv run yoghurt chart AAPL
```

## Sparklines

```python
spark = yoghurt.Ticker("AAPL").spark(range="1d", interval="1m")
```

`spark()` returns a `Spark` frame (single `close` column) plus typed
`.meta`. Raises `SymbolNotFoundError` for an unrecognized symbol.

## Options

Option-contract symbols (OCC format) are discovered from the chain, never
guessed:

```python
chain = yoghurt.Ticker("AAPL").options()
next_expiration = chain.expiration_dates[1]
next_chain = yoghurt.Ticker("AAPL").options(date=next_expiration)
```

`options()` returns a typed `OptionChain` — `expiration_dates` lists every
expiration Yahoo knows about, and the underlying security's own typed
`Quote` is included as `chain.quote`. Re-request with `date=` to pull a
specific expiration's contracts.

CLI equivalent:

```bash
uv run yoghurt options AAPL
```

## Parameters

Full parameter lists, defaults, and examples live in `--help`, not here:

```bash
uv run yoghurt quote --help
uv run yoghurt chart --help
uv run yoghurt options --help
```

See [SHARP-EDGES.md](SHARP-EDGES.md) for proven pitfalls in this domain.
