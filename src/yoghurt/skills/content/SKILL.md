---
name: yoghurt
description: Fetch and analyze Yahoo Finance market data — quotes, adjusted history, charts, options chains, fundamentals, analyst research, and market screeners — through the yoghurt Python library (typed pydantic models, polars frames) or CLI. Use when a task needs live or historical market data, financial statements, options data, market-wide screening, or any Yahoo Finance API access.
---

# yoghurt

Yahoo Finance market data: quotes, adjusted history, charts, options,
fundamentals, analyst research, and SQL-flavored screeners — as a typed Python
library or CLI.

## Quickstart

```bash
pip install yoghurt
```

No API key, no configuration — the first call just works:

```python
import yoghurt

quote = yoghurt.Ticker("AAPL").quote()
```

No install needed for one-off shell use:

```bash
uvx yoghurt quote AAPL
```

## Two surfaces, one vocabulary

**Library primary:** `from yoghurt import Ticker` — typed pydantic models,
typed errors, polars-backed frames.

**CLI secondary:** shell one-offs and no-dependency contexts
(`uvx yoghurt …`). Same command names as the library; flags mirror kwargs
mechanically: `--start-date` ↔ `start_date=`, `--modules a,b` ↔
`modules=["a", "b"]`. Endpoint commands print Yahoo's raw wire JSON to
stdout; the derived `history` and `financial-analysis` commands instead emit
analysis-ready rows. The library returns typed models/frames and raises typed
errors.

Shell-quote symbols with special characters: `^GSPC`, `EURUSD=X`, `ES=F`.

```bash
uv run yoghurt chart "^GSPC" --interval 1d
```

```python
yoghurt.Ticker("^GSPC").chart(interval="1d")
```

## Routing table

| Task | Use |
| --- | --- |
| Typed, per-symbol data (quote, chart, options, fundamentals, analysis) | `Ticker` methods |
| Adjusted single- or multi-symbol OHLCV for analysis | `Ticker.history()` / `history()` |
| Financial statements, valuation, analyst, and ownership tables | `Ticker.financial_analysis()` |
| Typed, market-wide lists (trending, sectors, market summary) | module-level functions |
| Asset-class filtering (equities, ETFs, crypto, …) | `screener()` |
| Data-platform entities — cross-entity queries, splits/IPO/earnings calendars | `visualization()` |
| An endpoint with no typed wrapper yet | `raw()` |

## Errors

One contract everywhere: symbol lookups raise `SymbolNotFoundError`, Yahoo
error payloads raise `YahooApiError` (`.code`, `.description`), transport
failures raise `YahooRequestError`/`YahooUnavailableError`. Queries with
zero matches return **empty frames** — never `None`, never an exception.

## Parameters

Do not guess parameter names or values. Run `yoghurt <command> --help` —
it is generated, complete, and authoritative for both surfaces via the
flag↔kwarg mirror rule.

## Domain index

| Domain | Read when… |
| --- | --- |
| [market-data](market-data/README.md) | fetching quotes, adjusted history, charts, sparklines, or options chains |
| [fundamentals](fundamentals/README.md) | pulling quote-summary modules or fundamentals timeseries |
| [analysis](analysis/README.md) | working with insights, ratings, recommendations, or calendar events |
| [queries](queries/README.md) | writing a screener or visualization DSL query |
| [dataframes](dataframes/README.md) | converting or exporting result frames |
