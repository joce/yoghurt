# Focused claim baselines

Captured live on 2026-09-05 using `YahooClient` with shared command metadata.
These are raw Yahoo responses; historical timeseries captures are unchanged.

All requests used `timeseries SYMBOL --period1 2026-01-01 --period2 2026-09-05`.
The `earnings` cases used `--type spEarningsReleaseEvents`; the `mixed` cases
used `--type spEarningsReleaseEvents,quarterlyTotalRevenue`. No other parameter
overrides were supplied. `AAPL_earnings.json` and `AAPL_mixed.json` contain
three earnings observations; the latter also contains two revenue observations.
Both SPY captures contain only metadata for their requested families.

`tools/probe.py --claims --report PATH` repeats these four cases and compares
family classifications and observation counts with this dated baseline. It
writes only a report, never these files. Valid JSON does not imply populated
data or support for other instruments/date windows.
