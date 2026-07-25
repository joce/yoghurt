# Market data

Symbol discovery, quotes, adjusted history, charts, sparklines, and option
chains — the market-data surfaces.

## Search and lookup

Use broad `search()` when the task may need instruments, private-company
profiles, related news, saved lists, navigation, or research metadata:

```python
matches = yoghurt.search("Appel", fuzzy=True, quotes_count=5)
symbols = [
    match.symbol for match in matches.quotes if match.symbol is not None
]
```

Use `lookup()` for instrument-only, paged results with an optional asset-type
filter:

```python
page = yoghurt.lookup("Apple", type="equity", count=25)
instruments = page.documents
```

An unmatched lookup has an empty `documents` list. Search result families are
also empty lists when no category matches. Private-company and cultural-asset
search rows have no ticker symbol.

CLI equivalents print Yahoo's raw JSON. Locale overrides are CLI-only:

```bash
uv run yoghurt search Airbus --lang fr-FR --region FR
uv run yoghurt lookup Bitcoin --type cryptocurrency --count 25
```

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

Use a relative raw chart window with `range=`/`--range`, or explicit
`period1`/`period2` dates. These modes cannot be combined.

## Adjusted history

`history` is a separate analysis-ready surface. It scales the complete OHLC
bar by Yahoo's `adj_close / close` factor, leaves volume unchanged, and always
returns `symbol, ts, open, high, low, close, volume`:

```python
single = yoghurt.Ticker("AAPL").history(period="1y").to_polars()
multi = yoghurt.history(["AAPL", "MSFT"], period="1y").to_polars()
```

With no period or dates the window is `1mo`; the default interval is `1d`.
Use `start=` and optional `end=` instead of `period=` for explicit dates.
Supported intervals are `1d`, `5d`, `1wk`, `1mo`, and `3mo`; use `chart()` for
intraday data because Yahoo omits adjusted close from intraday responses.
The multi-symbol result is long-form in caller-supplied symbol order, ready
to group by `symbol` before feeding each OHLCV block to TA-Lib.

CLI equivalent (derived JSON rows, not Yahoo's raw response envelope):

```bash
uv run yoghurt history AAPL,MSFT --period 1y --interval 1d
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
uv run yoghurt search --help
uv run yoghurt lookup --help
uv run yoghurt chart --help
uv run yoghurt history --help
uv run yoghurt options --help
```

See [SHARP-EDGES.md](SHARP-EDGES.md) for proven pitfalls in this domain.
