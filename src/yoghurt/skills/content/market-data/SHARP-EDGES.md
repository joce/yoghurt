# Sharp edges: market data

## Adjusted history is not repaired history

**Severity:** medium

`history()` adjusts OHLC for corporate actions using Yahoo's adjusted close,
but it does not guess whether a suspicious Yahoo price is wrong. It rejects a
response if any price-bearing row lacks a usable adjustment factor rather than
substituting raw prices. Empty responses remain empty.

Wrong way: assuming `history()` silently fixes currency-unit mixups, bad
splits, or isolated Yahoo anomalies.

Right way: use `history()` when adjusted OHLC is the required semantic; use
`chart()` when auditing Yahoo's raw OHLC, adjusted close, metadata, or events.
Add repair only when a corpus-backed defect establishes a safe rule.

Evidence: library design constraint, ongoing.

## Zero-based-percent gap on treasury-yield indices

**Severity:** medium

Treasury-yield indices report `fiftyTwoWeekLow: 0.0` and omit
`fiftyTwoWeekLowChangePercent` entirely rather than sending a real
percentage. The typed field is `float | None` — a `None` here means "Yahoo
did not send this field," not "zero change."

Wrong way: treating a present `fifty_two_week_low` of `0.0` as evidence
the percent field will also be populated.

Right way: always check for `None` before using
`fifty_two_week_low_change_percent`; do not assume presence follows from a
sibling field's value.

Evidence: 2026-07-05, corpus-confirmed on treasury-yield index quotes.

## Option-contract symbols are discovered, not guessed

**Severity:** medium

OCC-format option-contract symbols are Yahoo-generated and encode strike,
expiration, and type. There is no formula to construct one client-side that
is guaranteed to match Yahoo's own.

Wrong way: hand-building an OCC symbol string and requesting it directly.

Right way: call `Ticker(symbol).options()` to get `expiration_dates`, then
re-request `options(date=...)` for a specific expiration's real contracts.

Evidence: library design constraint; see
[market-data/README.md](README.md#options).

## Quote field availability varies by instrument type

**Severity:** low

Not every `Quote` field is populated for every asset class — futures,
indices, currencies, and crypto symbols carry a narrower field set than
equities.

Right way: treat absence of a field's "Observed on:" docstring line as
universal, and presence as a restriction to specific instrument types
(mirrors the model docs convention). Do not assume a field present on
`AAPL` is present on `ES=F` or `BTC-USD`.

Evidence: ongoing, per-field in `yoghurt.models.quote`.
