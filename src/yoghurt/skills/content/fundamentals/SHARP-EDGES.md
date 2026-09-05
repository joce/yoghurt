# Sharp edges: fundamentals

## `spEarningsReleaseEvents` has returned malformed JSON

**Severity:** medium

Historical Yahoo rejection/response corruption is not a permanent unsupported
library feature. The 2026-07-04 AAPL all-types capture contained an invalid JSON
escape inside `spEarningsReleaseEvents`; July 5 repeat requests reproduced it.
On 2026-09-05, explicit 2026-01-01 through 2026-09-05 requests for AAPL and SPY,
alone and mixed with `quarterlyTotalRevenue`, returned valid JSON with no Yahoo
error. AAPL had three earnings observations and, in the mixed request, two
revenue observations. SPY had metadata-only results without observation arrays.
The typed timeseries bundle has no earnings-release frame: inspect `raw()` for
these records. Other symbol/date combinations remain unverified.

A historically affected combination:

```python
Ticker("AAPL").timeseries(type=["spEarningsReleaseEvents", "quarterlyTotalRevenue"])
```

If corruption recurs, expect `YahooApiError(code="malformed-response")`; retry
without this type or request the needed financial types separately. Do not
silently treat a malformed response as an empty financial statement.

Evidence: corpus `timeseries/AAPL_types_00.json` (2026-07-04), documented July 5
retests, and the scoped 2026-09-05 live requests above.
