# Analysis

Research, ratings, recommendations, and calendar events for a symbol.

## Financial analysis tables

```python
analysis = Ticker("AAPL").financial_analysis()
estimates = analysis.earnings_estimates.to_polars()
targets = analysis.analyst_price_targets.to_polars()
growth = analysis.growth_comparison.to_polars()
insiders = analysis.insider_transactions.to_polars()
```

The bundle includes earnings/revenue estimates, earnings history, EPS trends
and revisions, price targets, stock/industry/sector/index growth comparison,
and ownership/insider tables. Treat empty frames as unavailable or
instrument-inapplicable data, not as `None`.

## Calendar events

```python
from yoghurt import Ticker

events = Ticker("AAPL").calendar_events(
    modules=["earnings"], start_date="2026-04-29", end_date="2026-04-30"
)
```

`modules` selects which event family the result populates (`earnings`,
`economicEvents`, `ipoEvents`, `secReports`); unrequested families come
back `None`. See
[SHARP-EDGES.md](SHARP-EDGES.md#calendar-events-needs-an-explicit-date-window)
before assuming an empty result means "no events."

CLI equivalent:

```bash
uv run yoghurt calendar-events AAPL --modules earnings --start-date 2026-04-29 --end-date 2026-04-30
```

## Analyst intelligence

```python
analyst = Ticker("AAPL").analyst()
top = Ticker("AAPL").ratings_top()
```

`analyst()` fetches put/call ratio, news summary, price targets, and
ratings in one call. `ratings_top()` fetches top analyst rating buckets and
raises `SymbolNotFoundError` for an unrecognized symbol.

## Recommendations

```python
related = Ticker("AAPL").recommendations()
```

`recommendations()` fetches related-symbol recommendations. See
[SHARP-EDGES.md](SHARP-EDGES.md#recommendations-empty-result-surfaces-as-a-validation-error)
— some instrument types have none to report, and that surfaces
differently than a normal empty result.

`stock_recommender()` fetches related-ticker peers for an equity symbol;
see
[SHARP-EDGES.md](SHARP-EDGES.md#stockrecommenders-404-is-unmappable)
for its unusual 404 behavior.

## Price insights and research insights

```python
insights = Ticker("AAPL").price_insights()
research = Ticker("AAPL").insights()
```

`price_insights()` returns AI-generated price analysis; `insights()`
returns research reports and significant developments. Neither raises for
an unrecognized symbol — see
[SHARP-EDGES.md](SHARP-EDGES.md#price-insights-never-confirms-a-symbol-exists).

## Parameters

Full parameter lists live in `--help`:

```bash
uv run yoghurt calendar-events --help
uv run yoghurt financial-analysis --help
uv run yoghurt analyst --help
uv run yoghurt insights --help
```
