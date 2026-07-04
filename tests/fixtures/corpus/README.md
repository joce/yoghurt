# Yahoo response corpus

Raw Yahoo Finance response bodies captured by `uv run python -m tools.probe`,
one file per probe case (`<command>/<case>.json`), indexed by `manifest.json`.

This corpus is:

1. **Evidence** — the typed response models in `yoghurt` are derived from
   these files, including per-field instrument-type applicability.
2. **Fixtures** — model parser tests round-trip these files; no network.
3. **A drift detector** — re-run the probe and diff to see what Yahoo changed.

Regenerate with `uv run python -m tools.probe` from the repo root (live Yahoo
access required, ~5 minutes, politely rate-limited). Review the diff before
committing a refresh; the manifest records argv and fetch timestamps.

Files under `<command>/ZZZZXYZQ.json` are deliberate invalid-symbol probes:
they capture Yahoo's error-payload shapes.
