# Unreleased

- Breaking Python API change: typed `quote()` and `quotes()` no longer accept
  `fields`. Use CLI projections or `raw()` for selected fields.
- Breaking Python API change: typed wrappers no longer accept `formatted`.
  They explicitly request unformatted values. CLI and raw requests retain control.
- Options support straddle responses with typed, optionally absent call/put legs.
- Analyst targets use trading currency, and screener tables preserve columns
  first appearing in later records.
- Malformed responses and numeric literals raise the documented errors.
- Credentials are excluded from HTTP diagnostics. Stale authentication refreshes
  once, concurrent failures share recovery, and crumb-free calls skip crumb lookup.
- Cache and Parquet replacement preserve prior files on failure. Skill updates
  are staged before replacement and restore the prior installation on failure.
- Wheel smoke checks and targeted Windows CI cover installed behavior.
