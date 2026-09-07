## Overview

Yoghurt 0.6.0 expands quarterly financial coverage and improves typed responses, authentication, and file safety, with breaking Python API and CLI changes.

## Highlights

### Added

- Quarterly balance-sheet and cash-flow coverage with 46 additional timeseries types, plus corrected financial metric classification.
- Typed option straddle responses with optionally absent call and put legs.
- A generated Python API reference, three executable workflows, and complete command references through `--help --verbose` or `-h -v`.
- Opt-in live contract probes and installed-wheel release checks.

### Changed

- **Python API:** `Ticker.quote()` and `quotes()` no longer accept `fields`. Use CLI projections or `raw()` when selecting wire fields.
- **Python API:** typed wrappers no longer accept `formatted`; they request unformatted values. Remove that keyword from typed calls. CLI and raw requests retain formatting controls.
- **Python API:** `TrendingResult.job_timestamp` is now a timezone-aware UTC `datetime`. Use `.timestamp()` when an epoch value is needed.
- **CLI:** replace `--help-verbose` with `--help --verbose` or `-h -v`.

### Fixed

- Corrected quote and options response handling, trading-currency metadata, and screener columns that first appear in later records.
- Standardized malformed-response and missing-symbol errors, and returned typed empty recommendations when coverage is unavailable.
- Corrected millisecond date inputs, pre-1970 timestamp handling, chart event defaults, and rejection of non-finite history values.
- Improved concurrent authentication recovery and bounded retries while avoiding unnecessary authentication for public chart requests and excluding credentials from diagnostics.
- Preserved existing cache, Parquet, and installed skill files on replacement failure; preserved POSIX Parquet permissions and protected foreign skill files.
- Fixed the public `history()` import collision and rejected unsupported output formats before making requests.

**Full Changelog:** https://github.com/joce/yoghurt/compare/v0.5.1...v0.6.0
