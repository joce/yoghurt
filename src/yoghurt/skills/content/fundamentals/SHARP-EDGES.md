# Sharp edges: fundamentals

## `spEarningsReleaseEvents` is permanently broken

**Severity:** high

Yahoo serves malformed JSON for the `spEarningsReleaseEvents` timeseries
type — for every symbol, even when requested alone. A request bundling it
with other types fails wholesale, not just for that one type.

Wrong way:

```python
Ticker("AAPL").timeseries(type=["spEarningsReleaseEvents", "quarterlyTotalRevenue"])
```

Right way: keep `spEarningsReleaseEvents` out of every `type` list. Use the
default type list, or list only the types you need, and expect
`YahooApiError` (code `"malformed-response"`) if it's ever accidentally
requested.

Evidence: 2026-07-05, retested repeatedly; every attempt reproduces the
same malformed-response failure.
