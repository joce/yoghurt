# Yahoo response corpus

Raw Yahoo Finance response bodies captured by `uv run python -m tools.probe`,
one file per probe case (`<command>/<case>.json`), indexed by `manifest.json`.

This corpus is:

1. **Evidence** — the typed response models in `yoghurt` will be derived from
   these files, including per-field instrument-type applicability.
2. **Fixtures** — model parser tests round-trip these files; no network.
3. **A drift detector** — re-run the probe and diff to see what Yahoo changed.

Regenerate with `uv run python -m tools.probe` from the repo root (live Yahoo
access required, ~5 minutes, politely rate-limited). Review the diff before
committing a refresh; the manifest records argv and fetch timestamps.

Files under `<command>/ZZZZXYZQ.json` are deliberate invalid-symbol probes:
they capture Yahoo's error-payload shapes. `timeseries/AAPL_types_00.json` is
kept byte-for-byte as evidence of Yahoo-side corruption (HTTP 200 with an
invalid JSON escape inside `spEarningsReleaseEvents`) and does not parse as
JSON.

`timeseries/AAPL_analystRatings.json` and
`timeseries/AAPL_economicEventsLong.json` are surgical single-case captures:
hand-added `tools/probe.py` cases requesting one event type over a long
(2020-01-01 onward) window, rather than results carried by the all-types
sweep. The probe plan also includes a dedicated `AAPL_spEarnings` case; Yahoo
currently serves malformed JSON for `spEarningsReleaseEvents` on every
symbol, so that case is expected to record a manifest `status: "error"`
(no corpus file) on full probe runs, not a probe bug.
