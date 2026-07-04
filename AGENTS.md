# AGENTS.md

## Project
Yoghurt exposes Yahoo Finance HTTP endpoints as a typed Python library and an LLM-friendly CLI that prints the raw JSON Yahoo returns.

## Stack
Python 3.10+, uv, httpx2, argparse, pytest, ruff, pyright, tox, hatchling.

## Parquet
Parquet is written with **polars** (a core dependency); chart/screener/visualization only.

## Commands
- Install/sync: `uv sync --all-groups`
- Run CLI: `uv run yoghurt --help`
- Test single: `uv run pytest path/to/test_file.py`
- Test all: `uv run pytest`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Type check: `uv run pyright`
- Spell check: `npm run spell` or `make spell`
- Spell changed files: `npm run spell:changed` or `make spell-changed`
- Full check: `uv run tox`

## Architecture
- `src/yoghurt/client.py` -> Yahoo HTTP session, cookies, crumbs, retries, raw response retrieval.
- `src/yoghurt/session_cache.py` -> persisted Yahoo cookie/crumb cache for one-shot CLI reuse.
- `src/yoghurt/commands.py` -> command metadata used to build CLI commands, validation, and help.
- `src/yoghurt/params.py` -> endpoint parameter metadata, coercion, and request (params/path) building.
- `src/yoghurt/cli.py` -> argparse command tree and stdout/stderr behavior.
- `src/yoghurt/_bridge.py` -> background-loop sync bridge.
- `src/yoghurt/_core.py` -> async endpoint core: envelopes, error mapping, shared client.
- `src/yoghurt/api.py` -> public sync Ticker + module functions.
- `src/yoghurt/frames.py` -> Frame/Chart result types.
- `src/yoghurt/tabular.py` -> response flattening shared by frames and parquet, including the timeseries fundamentals/geographic-segments/economic-events/analyst-ratings flattener.
- `src/yoghurt/parquet_writer.py` -> Parquet output for chart/screener/visualization.
- `src/yoghurt/query.py` -> screener/visualization DSL parsing.
- `src/yoghurt/exceptions.py` -> public exception hierarchy.
- `src/yoghurt/models/` -> typed pydantic response models (Part 3+): `_base.py` (YahooModel base), `enums.py` (closed vocabularies), `quote.py` (Quote), `chart.py` (ChartMeta/Spark meta/chart events), `options.py` (OptionChain/OptionContract/OptionExpiration).
- `src/yoghurt/__init__.py` -> lazy public surface, py.typed.
- `tests/` -> pytest tests mirroring `src/yoghurt/`.

## Rules
- IMPORTANT: `--help` is the primary product surface; keep it complete, adaptive, and generated from command metadata where practical.
- Do not add `describe`, `endpoints`, `params`, or other discovery commands; discovery belongs under `yoghurt --help` and `yoghurt <endpoint> --help`.
- CLI: Print Yahoo response bodies to stdout exactly as returned; do not model, reshape, pretty-print, or interpret endpoint JSON.
- Use `uv run python` for Python scripts; never use bare `python` or `python3`.
- Never log or print Yahoo cookies, crumbs, or full session-cache contents.
- Keep runtime dependencies narrow; do not add TUI, ORM, web framework, or rich formatting libraries.

## Help text
When adding or editing a CLI command:
1. **Summary**: active verb, ≤68 chars (over wraps two-line in top-level help). `Fetch` (data), `List` (catalog), `Run` (saved query), `Query` (DSL), `Show` (symbol-free), `Discover` (curated). Pair sibling commands with the same verb.
2. **Description**: describe response content, not yoghurt mechanics. Forbidden phrasings: `Calls Yahoo`, `writes to stdout`, `response-model mapping`. The root parser already covers output behavior. Do not paraphrase the summary.
3. **Notes**: real clarifications only — Yahoo quirks (typos, 500s, paywalled empties), switch-behavior surprises, instrument-type dependencies. Drop live-probe diary entries and redundant restatements.
4. **Order in `COMMANDS` tuple by importance**: daily-driver → discovery → symbol-bound analysis → market-wide state → schema introspection → `raw`. The DSL parsers (`visualization`, `screener`) slot inside the loop after `screener-predefined` in `cli.py`. Never append to the end.
5. **Param boilerplate is shared** (`--lang`, `--region`, `--formatted` use exact strings — copy them). Run `pytest -k help` before and after. Pinned-string assertions guard things like `INSIDER_TRANSACTION`, `snake_case`, `Module availability depends on instrument type`. Negative guards (`Calls Yahoo`, `Output:`) forbid implementation leak — do not reintroduce.

## Library rules
- The library never prints, never prompts, never reads stdin; missing config raises immediately.
- Error contract: symbol lookups raise SymbolNotFoundError; Yahoo error payloads raise YahooApiError; empty query results return empty Frames (never None, never raise); transport failures raise YahooRequestError/YahooUnavailableError.
- One conversion vocabulary on every tabular result: to_polars, to_pandas, to_arrow, to_dicts, save_parquet. Conversions take no shaping arguments.
- One name per concept; no aliases; no value-dependent return types.
- Kwargs mirror CLI command metadata 1:1 (wire-name keys); booleans whose CLI flag inverts the wire value are named after the wire param. lang/region ride their defaults until the typed-model layer.
- Response models (Part 3+) are frozen pydantic models with extra="allow"; internal metadata records are frozen dataclasses; orchestrators are plain classes.
- The corpus at tests/fixtures/corpus/ is the evidence for response shapes; parser code and tests reference corpus files, not hand-invented JSON, wherever a real capture exists.

## Response model conventions
- All response models subclass yoghurt.models.YahooModel (frozen, to_camel aliases with explicit Field(alias=...) for irregular wire spellings, populate_by_name, extra="allow", str_strip_whitespace — the last is a quote-informed default; confirm per endpoint family).
- The corpus is authoritative for wire spellings, presence, and types; prior art (Doubloon) second; researched docs (src/yoghurt/docs/*.md) third.
- Optionality is evidence-driven: required exactly for keys present in 100% of that endpoint's corpus records (tools/fields_report.py-style report), else Optional.
- Closed vocabularies are (str, Enum) classes in yoghurt/models/enums.py with WIRE casing, defined once, corpus-coverage-tested; values known only from prior use are noted in the enum docstring.
- Closed vocabularies are reused across endpoint families when values coincide (e.g. QuoteType for chart's instrumentType); when a new family verifies an existing enum against its own corpus, note it in the enum's docstring rather than minting a duplicate.
- Every field docstring ends with exactly one applicability form: "Observed on: <types> <endpoint-noun>." / "Not observed in the corpus; known from prior use on <types> <endpoint-noun>." / "Observed only as empty lists in the corpus." The endpoint noun (quotes / charts / contracts / chains / …) is fixed per model module and stated in that module's docstring. The corpus capture date lives once in the module docstring.
- Fields are declared in alphabetical order; the coverage gate asserts it.
- Nested payload objects become nested YahooModel sub-models — never dict fields; keyed collections are dict[str, SubModel].
- Convenience accessors are plain functools.cached_property, never pydantic computed_field: model_dump() stays wire-shaped.
- Epoch fields are never bare ints in meaning: calendar-date epochs (midnight-UTC-aligned) type as `datetime.date` directly; point-in-time epochs with in-model timezone context keep the wire `int` plus a localized `@cached_property` datetime; point-in-time epochs without in-model timezone context type as aware-UTC `datetime.datetime` directly.
- Every model ships a corpus coverage gate: every relevant corpus record validates with EMPTY extras at EVERY nesting level (tests/conftest.py::collect_nested_extras), and the required-field set is pinned to the presence report.
- Validation failures surface as YahooApiError(code="model-validation") via yoghurt.models.validate_model(); pydantic never leaks through the public API.
- Large models get a compact custom __repr__ (symbol-forward); __str__ only if it adds real value.

## Workflow
- Make minimal changes and avoid unrelated refactors.
- When adding a command or parameter, update validation, adaptive help, and tests in the same change.
- Prefer focused unit tests with mocked HTTP; mark live Yahoo tests as integration.
- Before considering code changes done, run `uv run tox`. It is the expected bundled verification for formatting, lint, type check, tests, and spelling.
- For command or parameter changes, also run the app against Yahoo after `tox`:
  - `uv run yoghurt <command> --help`
  - `uv run yoghurt <command> <minimal required parameters>`
  - `uv run yoghurt <command> <parameters with each supported date/time format when dates are involved>`
  - `uv run yoghurt <command> <parameters with meaningful modules, types, field lists, booleans, or other values that could affect Yahoo's raw output>`
- When a command has open-ended value lists such as `modules`, `types`, or `fields`, test representative variations and an all-known-values request when practical.
- When a parameter has a default, test both omission and explicit override if the default affects the request sent to Yahoo.
- Ask before making architectural changes that affect the CLI grammar or session-cache behavior.

## Yahoo API state probes
- When checking the current quote-page API surface with browser tooling or live Yahoo calls, use a mixed symbol set so endpoint behavior is not inferred from US mega-cap equities only.
- Baseline probe symbols:
  - US stocks, high profile and smaller: `AAPL`, `MSFT`, `OKLO`
  - ETFs: `SPY`, `QQQ`, `VT`
  - Futures and commodities: `ES=F`, `CL=F`
  - Forex: `EURUSD=X`
  - Indices: `^GSPC`, `^DJI`, `^IXIC`
  - Crypto: `BTC-USD`
  - Foreign listings: `RY.TO`, `0700.HK`, `7203.T`, `SHEL.L`
- Add targeted probes when an endpoint is symbol-sensitive, but keep this baseline for broad API-surface discovery and for checking whether an observed endpoint applies across asset classes.

## Out of scope
- Separate documentation/discovery subcommands.
- Secrets, API keys, or checked-in session-cache files.
