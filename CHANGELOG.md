# Changelog

All notable changes to yoghurt are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Parquet output is now written with **polars** instead of pyarrow, and polars is
  a core dependency. The `parquet` optional extra is removed — parquet works with a
  plain install. **Breaking:** `pip install "yoghurt[parquet]"` no longer resolves.

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

[Unreleased]: https://github.com/joce/yoghurt/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/joce/yoghurt/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/joce/yoghurt/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/joce/yoghurt/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/joce/yoghurt/releases/tag/v0.1.1
