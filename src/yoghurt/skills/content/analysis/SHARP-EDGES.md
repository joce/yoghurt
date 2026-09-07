# Sharp edges: analysis

## Calendar events needs an explicit date window

**Severity:** high

The July 5 corpus probes returned empty `calendar-events` results
without an explicit `start_date`/`end_date` window covering a day that
actually had events. The default window is roughly now−3 days to now,
which may not cover a relevant event. A no-window empty response is not
evidence about future earnings. The date-window behavior is relevant to
the `earnings` (default), `economicEvents`, `ipoEvents`, and `secReports`
modules.

Wrong way: calling `Ticker("AAPL").calendar_events()` with no window and
concluding the symbol has no upcoming earnings.

Right way: pass a `start_date`/`end_date` window known to cover a real
event day for the module you requested.

Evidence: 2026-07-05, corpus- and live-confirmed across `earnings`,
`ipoEvents`, and `secReports`.

## Price insights never confirms a symbol exists

**Severity:** high

`price_insights()` returns a fully-populated, valid-shaped record even for
invalid or unknown symbols — Yahoo answers HTTP 200 with
`has_price_anomaly=True` and empty content blocks, not a 404 or an empty
result.

Wrong way: using a successful `price_insights()` call as proof a symbol is
valid.

Right way: confirm a symbol exists via `quote()` or `quote_type()` (both
raise `SymbolNotFoundError` for unknown symbols); never infer validity from
`price_insights()`.

Evidence: 2026-07-05.

## `stock_recommender` maps its unusual 404

**Severity:** medium

`stock_recommender()`'s unknown-symbol 404 body carries no `detail` key
(just `{"message": "Not Found"}`). Yoghurt recognizes that exact shape for
this endpoint and raises `SymbolNotFoundError`.

Right way: catch `SymbolNotFoundError` around `stock_recommender()` calls
when symbol validity is uncertain.

Evidence: 2026-07-05.

## Recommendations cannot distinguish absence from an unknown symbol

**Severity:** medium

Some instrument types (for example futures) have no recommendations to
report. Yahoo answers with the same empty result list for those instruments
and unknown symbols. Yoghurt returns an empty `RecommendationsResult` with
the requested symbol for both cases.

Right way: treat an empty `recommended_symbols` list as no recommendation
data, not proof that the symbol exists.

Evidence: 2026-07-05.

## `EconomicEvent.actual` is None for not-yet-released events

**Severity:** low

`EconomicEvent.actual` is `None` when the release has not happened yet
(the value only exists after Yahoo has real data to report).

Right way: check for `None` before formatting `actual`; do not assume every
row in an economic-events window has a reported value.

Evidence: 2026-07-05.

## `secReports` is SEC filings, not stock splits

**Severity:** medium

Per-symbol `calendar-events` with `modules=["secReports"]` returns SEC
filing events (10-K, 10-Q, 8-K, etc.) — not stock splits, despite the two
sometimes being confused. Market-wide stock splits live on the
`visualization()` route instead; see
[queries/SHARP-EDGES.md](../queries/SHARP-EDGES.md#stock-splits-are-not-symbol-bound).

Wrong way: requesting `calendar_events(modules=["secReports"])` to find a
symbol's upcoming split.

Right way: use `visualization()` with `FROM splits` for split data; use
`secReports` only for SEC filing history.

Evidence: 2026-07-05, corpus-confirmed — split-day symbols return
byte-for-byte empty `secReports` over their known split windows, ruling
out the split hypothesis.
