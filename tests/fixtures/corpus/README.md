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

Line endings: the single-line capture JSON files are committed with a
trailing CRLF (a repo-wide convention dating to the original Part 1 capture
run); `README.md`, `manifest.json`, and all tooling files are LF. Match the
existing convention when adding captures — do not "fix" either side.

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
(no corpus file) on full probe runs, not a probe bug. Retested live
2026-07-05 (P4-1): still corrupt, same invalid-JSON-escape failure as the
original 2026-07-04 capture. Retested again later on 2026-07-05 after a
session reported the feed fixed: two independent pulls returned byte-identical
bodies (34,621 bytes), both still carrying the same invalid `\'` escape — the
"fixed" report was a false positive caused by the probe formerly recording
`status: "ok"` and writing a file for an HTTP-200 body that does not parse as
JSON. `tools/probe.py` now records such bodies as `status: "error"` with no
file, so a manifest `"ok"` always means the capture parses; judge feed health
only by `json.loads` on the raw bytes. Next retest should be opportunistic
(no fixed date), on the next corpus refresh.

**2026-07-05 surgical addition (P4-1, corpus reinforcement):** invalid-symbol
(`ZZZZXYZQ`) cases added for the seven endpoints that previously lacked one
(`calendar-events`, `recommendations-by-symbol`, `stock-recommender`,
`price-insights`, `insights`, `ratings-top`, `options`), plus cross-asset
(`SPY`, `^GSPC`, `BTC-USD`, `EURUSD=X`, `ES=F`) cases for `insights`,
`price-insights`, and `recommendations-by-symbol` (widening those three
endpoints beyond `EQUITY_SUBSET`). All new captures parsed as valid JSON and
are committed; see `src/yoghurt/models/analysis_events.py` and
`src/yoghurt/models/analysis_insights.py`'s module docstrings for what the
widened evidence confirmed (several fields previously typed Optional from
live-only observation during Part 3d are now backed by real corpus
captures). `recommendations-by-symbol/^GSPC.json` was refetched (same shape,
fresh live recommendation scores) since it now rides the cross-asset case
instead of a standalone one.

**2026-07-05 surgical addition (calendar-events populated windows):** every
prior `calendar-events` capture used the default (no `--start-date`/
`--end-date`) window, which is always empty for `earnings`/`ipoEvents`/
`secReports`. 18 new cases add an explicit date window, found via Yahoo's
calendar UI: 15 populated-window cases plus 3 negative-evidence cases for a
competing hypothesis.

Populated: `IVF_earnings`/`HAWK_earnings`/`EBF_earnings`/`POWW_earnings`
(2026-06-20 to 2026-06-27, all reported 2026-06-22) and `MSFT_earnings`
(2026-04-26 to 2026-05-05, reported 2026-04-29); `COPR_ipoEvents`/
`GSRVR_ipoEvents`/`IQMXW_ipoEvents`/`MIACU_ipoEvents`/`VCRE_ipoEvents`/
`SECZ_ipoEvents` (2026-06-29 to 2026-07-03, all priced 2026-07-02 — common
stock, rights, warrants, units, and ADSs); `BOXL_secReports`/
`HAWK_secReports` (2026-06-20 to 2026-06-27) and
`AAPL_secReports_filed`/`MSFT_secReports_filed` (2026-04-20/2026-04-26 to
2026-05-05).

The `secReports` captures resolve a competing hypothesis from a live UI
check (stock splits vs. SEC filings) in favor of the CLI help text's
existing "SEC filing events" description: the populated captures above show
real 10-Q/8-K/DEFA14A rows, not split events, and three additional negative-
evidence cases confirm the split hypothesis does not hold —
`BEOB_secReports_split`/`CATTF_secReports_split`/`6669.TW_secReports_split`
each capture a byte-for-byte empty `{"secReports": []}` over the symbols'
known 2026-06-22 split date (window 2026-06-21 to 2026-06-27). See
`src/yoghurt/models/analysis_events.py`'s module docstring for the full
per-module evidence writeup and the new `EarningsEvent`/`EarningsEventDay`,
`IpoEvent`/`IpoEventDay`, and `SecReport`/`SecReportDay`/`SecReportExhibit`
models these captures back.

**2026-07-05 surgical addition (agent-skills, visualization/splits):** the
`queries` skill domain documents market-wide stock splits via
`visualization()`'s `splits` entity, but no corpus fixture backed that
snippet before this addition (only `insider_transaction` and `sp_earnings`
existed under `visualization/`). Added one `tools/probe.py` case
(`visualization/splits`, `_dsl_cases()`) and captured it live with the same
query the skill content shows: `SELECT ticker, startdatetime FROM splits
WHERE startdatetime BETWEEN '2026-05-09' AND '2026-05-16' LIMIT 25`. The
capture returned a populated, real result (135 total matches, 25 rows
across mixed foreign listings), confirming `splits` is a live, working
data-platform entity distinct from `sp_earnings`/`INSIDER_TRANSACTION`.
One live call, politeness delay respected, merged into `manifest.json` with
no changes to any pre-existing entry (`case_count` 284 -> 285,
`fetched_at` unchanged, per the surgical-addition precedent above).
