# Changelog

All notable changes to yoghurt are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Yoghurt is now also an importable Python library: `yoghurt.Ticker` plus
  module-level functions (`quotes`, `screener`, `visualization`, `trending`,
  etc.), typed `Frame`/`Chart` results with `to_polars`/`to_pandas`/
  `to_arrow`/`to_dicts`/`save_parquet`, a `SymbolNotFoundError`/`YahooApiError`/
  `YahooRequestError`/`YahooUnavailableError` error contract, `configure()`,
  `py.typed`, and an optional `yoghurt[pandas]` extra.
- Typed `Quote` response model (131 fields, corpus-verified against 28
  real quote captures) plus `QuoteType`/`MarketState`/`OptionsType`/
  `PriceAlertConfidence` enums, in a new `yoghurt.models` package.
- Typed `ChartMeta`/`ChartEvents` response models (shared by the `chart` and
  `spark` endpoints, corpus-verified against 48 chart+spark meta captures)
  plus `TradingPeriod`/`CurrentTradingPeriod`/`ChartDividend`/`ChartSplit`,
  in `yoghurt.models`. `yoghurt.Spark`, a `Frame` subclass for the sparkline
  close-price series.
- Typed `OptionChain`/`OptionExpiration`/`OptionContract` response models for
  the `options` endpoint, corpus-verified against 3 option chain captures
  (365 call+put contracts); `OptionChain.quote` embeds the typed `Quote`
  model for the underlying security.
- `yoghurt.Timeseries`, a frozen container of four typed frames built from
  the `timeseries` endpoint: long-format `fundamentals` (with
  `reportedValue.raw` as `value`), `geographic_segments` (the per-region
  breakdowns some fundamentals rows attach), `economic_events`, and
  `analyst_ratings` (corpus-verified against an 830-row capture), plus
  `empty_types`/`unrecognized_types` bookkeeping so no returned type is
  silently dropped. Every frame keeps its declared schema even when empty.
- Typed response models for all 41 `quote-summary` modules (corpus-verified
  against 23 real quote-summary captures across EQUITY, ETF, MUTUALFUND,
  CRYPTOCURRENCY, CURRENCY, FUTURE, INDEX, and OPTION quoteTypes), plus a new
  `QuoteSummary` container model (one optional field per module) in
  `yoghurt.models`. Introduces the `Raw*`/`Raw*OrNone` family
  (`RawFloat`/`RawInt`/`RawDate` and their nullable counterparts) for
  fields that wrap a value as `{raw, fmt, longFmt}` instead of sending it
  bare. `fundProfile`/`fundPerformance`/`topHoldings` (ETF/MUTUALFUND-only)
  rest on a thinner 4-capture evidence base than the rest of this endpoint
  family; see their module docstrings for the fields typed from a single
  observation.
- Typed `QuoteTypeResult`, `CalendarEventsResult` (plus `EconomicEvent`/
  `EconomicEventDay`), `RecommendationsResult`/`RecommendedSymbol`, and
  `StockRecommenderResult`/`StockRecommenderFields` response models for the
  `quote-type`, `calendar-events`, `recommendations-by-symbol`, and
  `stock-recommender` endpoints, in the new `yoghurt.models.analysis_events`.
- Typed `PriceInsights` and `Insights` response models for the
  `price-insights` and `insights` endpoints, in the new
  `yoghurt.models.analysis_insights`. `PriceInsights` validates all three
  captured shape variants (a full default response, an AI-analysis-only
  response, and a price-anomaly-only response) from one model; every field
  except `has_price_anomaly` is optional as a result.

### Changed

- `Ticker.quote()` and the module-level `quotes()` now return typed `Quote`
  models instead of raw dicts.
- `Ticker.chart()`'s `Chart.meta` is now a typed `ChartMeta` instead of a raw
  dict, and `Chart` gained a typed `events: ChartEvents | None` field.
  `Ticker.spark()` now returns a typed `Spark` frame (`to_polars()` columns
  `ts`, `close`; `Spark.meta` is `ChartMeta`) instead of the raw parsed
  payload.
- `Ticker.options()` now returns a typed `OptionChain` instead of a raw dict.
- `Ticker.timeseries()` now returns a typed `Timeseries` instead of the raw
  parsed payload. Known Yahoo-side bug: requesting the
  `spEarningsReleaseEvents` type currently fails with
  `YahooApiError("malformed-response")` because Yahoo serves invalid JSON
  for that type (every symbol, even requested alone); keep it out of `type`
  lists until Yahoo fixes the feed.
- Epoch fields on the option and chart models now carry date/datetime
  meaning instead of bare wire ints: `OptionContract.expiration`,
  `OptionExpiration.expiration_date`, and `OptionChain.expiration_dates`
  are `datetime.date`/`list[datetime.date]`; `OptionContract.last_trade_date`
  and `ChartDividend.date` are aware UTC `datetime.datetime`. `ChartMeta`
  gained `regular_market_datetime`/`first_trade_datetime` and
  `TradingPeriod` gained `start_datetime`/`end_datetime` `cached_property`
  conveniences (the latter localized via a fixed `gmtoffset`, since its
  `timezone` field is a short abbreviation `ZoneInfo` cannot resolve).
  `Quote` gained matching `earnings_call_datetime_start`/
  `earnings_call_datetime_end` conveniences for parity with its other
  epoch fields.
- `Ticker.quote_summary()` now returns a typed `QuoteSummary` instead of the
  raw parsed payload; `modules` still narrows which fields Yahoo populates
  (unrequested or inapplicable modules validate as `None`).
- `Ticker.quote_type()` now returns a typed `QuoteTypeResult` instead of a raw
  dict; empty results still raise `SymbolNotFoundError`.
- `Ticker.calendar_events()`, `.recommendations()`, `.stock_recommender()`,
  `.price_insights()`, and `.insights()` now return typed models
  (`CalendarEventsResult`, `RecommendationsResult`, `StockRecommenderResult`,
  `PriceInsights`, `Insights`) instead of raw parsed payloads. None of these
  five endpoints has a captured invalid-symbol response shape, so an
  unrecognized symbol surfaces as `YahooApiError` (code `"model-validation"`)
  rather than `SymbolNotFoundError`.

### Internal

- `YahooRequestError` now exposes a public `body` attribute with Yahoo's raw
  error response body, when available.

## [0.3.3] - 2026-06-30

Maintenance release — dependency updates only; no user-facing changes.

### Internal

- Bump `polars` from 1.41.2 to 1.42.0 (performance improvements: cloud IO
  concurrency control, streaming struct unnest optimization).
- Bump `tox` from 4.55.1 to 4.56.1.
- Bump `coverage` from 7.14.1 to 7.14.3.
- Bump `pyright` from 1.1.410 to 1.1.411.
- Bump `ruff` from 0.15.18 to 0.15.20.

## [0.3.2] - 2026-06-26

Maintenance release — runtime HTTP and tooling dependency updates. No CLI output changes.

### Internal

- Replace `httpx` with `httpx2` for Yahoo HTTP requests and use `httpx2.MockTransport`
  in client tests.
- Bump `codecov/codecov-action` GitHub Action from 6 to 7 (signing key migrated to
  `codecovsecops` account); add `codecovsecops` to the spell-check word list.
- Bump `actions/checkout` GitHub Action from 6 to 7.
- Bump `ruff` from 0.15.16 to 0.15.18 (bug fixes, rule tweaks, performance improvements).
- Bump `pylint` from 4.0.5 to 4.0.6 (crash fixes in decorator, enum, and typecheck checkers).
- Bump `pytest` from 9.0.3 to 9.1.1 (bug fixes for `RaisesGroup`, parametrize, and test configuration loading).

## [0.3.1] - 2026-06-09

Maintenance release — internal tooling bumps only, no user-facing changes.

### Internal

- Bump `tox` from 4.55.0 to 4.55.1 (config-override propagation fix).
- Bump `ruff` from 0.15.15 to 0.15.16 (bug fixes, rule tweaks).
- Bump `astral-sh/setup-uv` GitHub Action from 8.1.0 to 8.2.0 (new `quiet` and
  `download-from-astral-mirror` inputs, security and reliability fixes).

## [0.3.0]

### Changed

- Parquet output is now written with **polars** instead of pyarrow, and polars is
  a core dependency. The `parquet` optional extra is removed — parquet works with a
    plain install. **Breaking:** `pip install "yoghurt[parquet]"` no longer resolves.

### Internal

- Dependency bumps (uv-dependencies group).

## [0.2.2] - 2026-05-29

Maintenance release — release tooling only, no user-facing changes.

### Changed

- Version is now derived from the git tag via `hatch-vcs`; the hardcoded
  `__version__` (which had drifted to `0.2.0`) is gone.
- The publish workflow runs `twine check` before upload, and CI/publish jobs
  check out full history so the version can be derived from tags.

### Added

- `CHANGELOG.md` and `RELEASING.md`.

## [0.2.1] - 2026-05-27

Maintenance release. No user-facing changes.

### Changed

- Bumped artifact and Codecov actions to their Node 24 versions; migrated the
  deprecated `codecov/test-results-action` to `codecov-action`.
- Enabled Dependabot for uv dependencies.
- Extracted `_dispatch_command` to satisfy ruff `PLW0717`.
- Dev dependency bumps (tox, tox-uv, coverage, black, ruff).

## [0.2.0] - 2026-05-16

### Added

- Parquet output for `chart`, `screener`, and `visualization`:
  `--format parquet --out PATH` writes typed binary tables instead of JSON
  (optional `parquet` extra; the JSON path pays zero import cost).
  - `chart` uses a fixed schema (`ts`, `open`, `high`, `low`, `close`,
    `volume`, `adj_close`) with UTC timestamps.
  - `screener` / `visualization` infer schema from the response; columns mirror
    Yahoo's response keys. AGGREGATE visualization queries are rejected pre-call.
  - Missing parent directories are auto-created; OS write failures surface as
    user-facing errors. A single-line JSON descriptor is emitted on success.

### Changed

- **Breaking:** `screener --formatted` is now a real opt-in toggle defaulting to
  `false` (previously a no-op that always sent `formatted=true`). By default,
  responses come back as plain scalar cells; pass `--formatted` for Yahoo's
  wrapped `{raw, fmt, longFmt}` shape. `--format parquet --formatted` is rejected.
- Coverage excludes type-only `types.py`.

## [0.1.1] - 2026-05-15

First PyPI release.

### Added

- LLM-friendly CLI for raw Yahoo Finance endpoint JSON, with 22
  endpoint-specific commands (`quote`, `quote-summary`, `chart`, `timeseries`,
  `screener`, `visualization`, etc.).
- SQL-flavored DSL for `screener` and `visualization`, with `--help-verbose`
  for the full DSL reference inline.
- Reusable Yahoo session cache for faster one-shot calls.
- `raw` escape hatch for query paths yoghurt doesn't model yet.

[Unreleased]: https://github.com/joce/yoghurt/compare/v0.3.3...HEAD
[0.3.3]: https://github.com/joce/yoghurt/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/joce/yoghurt/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/joce/yoghurt/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/joce/yoghurt/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/joce/yoghurt/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/joce/yoghurt/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/joce/yoghurt/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/joce/yoghurt/releases/tag/v0.1.1
