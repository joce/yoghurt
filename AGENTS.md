# AGENTS.md

## Project
Yoghurt exposes Yahoo Finance HTTP endpoints as an LLM-friendly CLI that prints the raw JSON Yahoo returns.

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
- `src/yoghurt/params.py` -> CLI parameter coercion and validation helpers.
- `src/yoghurt/cli.py` -> argparse command tree and stdout/stderr behavior.
- `tests/` -> pytest tests mirroring `src/yoghurt/`.

## Rules
- IMPORTANT: `--help` is the primary product surface; keep it complete, adaptive, and generated from command metadata where practical.
- Do not add `describe`, `endpoints`, `params`, or other discovery commands; discovery belongs under `yoghurt --help` and `yoghurt <endpoint> --help`.
- Print Yahoo response bodies to stdout exactly as returned; do not model, reshape, pretty-print, or interpret endpoint JSON.
- Keep Yahoo endpoint knowledge in metadata and validation only; do not create response classes.
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
- Mapping Yahoo JSON into Python domain models.
- Separate documentation/discovery subcommands.
- Secrets, API keys, or checked-in session-cache files.
