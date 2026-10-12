## Overview

Yoghurt 0.7.0 adds Python 3.15 support and drops Python 3.10. The minimum supported version is now Python 3.11. On 3.15 the CLI starts noticeably faster because the HTTP and async stacks load only when a request is made.

## Highlights

- **Python 3.15 is supported.** On 3.15 yoghurt requires polars 2.x, and the `pandas` extra resolves to pandas 3.x and pyarrow 26. Python 3.11–3.14 keep the existing ranges.
- **Python 3.10 is no longer supported.** Installing on 3.10 resolves to yoghurt 0.6.1.
- **Faster CLI startup on 3.15.** `yoghurt --help` starts roughly 40% faster (about 182 ms to 105 ms in local measurements), and `import yoghurt` about 50% faster. Startup on 3.11–3.14 is unchanged.
- **Enums are now `StrEnum`.** `str()` and `format()` of a closed-vocabulary member such as `QuoteType.EQUITY` return the wire value (`"EQUITY"`) instead of `"QuoteType.EQUITY"`. Comparisons with plain strings and `.value` are unaffected.
- The `polars` dependency range now allows 2.x.

## Upgrade notes

- If you format enum members into strings and relied on the `ClassName.MEMBER` form, switch to `repr()` or build the string explicitly.
- On Python 3.15, an environment pinned to polars 1.x or pandas 2.x cannot install this release; those versions do not work on 3.15.

**Full Changelog:** https://github.com/joce/yoghurt/compare/v0.6.1...v0.7.0
