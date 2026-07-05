"""Typed earnings-family models for the ``quote-summary`` endpoint.

Reconciled against the probe corpus at ``tests/fixtures/corpus/quote-summary/``
(23 valid captures across EQUITY, ETF, MUTUALFUND, CRYPTOCURRENCY, CURRENCY,
FUTURE, INDEX, and OPTION quoteTypes), captured 2026-07-04. Regenerate the
applicability evidence with
``uv run python -m tools.fields_report quote-summary:<module>`` after a
corpus refresh (see ``tools/fields_report.py`` for the generic per-module
stream this evidence is built from). This module covers the six
earnings-family modules of batch c2 (Part 3c plan): ``earnings``,
``earningsGaap``, ``earningsNonGaap``, ``earningsHistory``,
``earningsTrend``, and ``earningsCallTranscripts``. The remaining four
batch c2 modules (``financialData``, ``defaultKeyStatistics``,
``calendarEvents``, ``financialsTemplate``) live in
:mod:`yoghurt.models.summary_financials`.

File-split rationale: batch c1's single module file reached roughly 2100
lines: this batch's earnings modules carry the richest nested shapes of
the whole endpoint family so far (``earningsTrend.trend[]`` alone nests
four wrapped sub-shapes), so splitting by cohesion — financial headline
scalars in one file, earnings-history/trend/transcript detail in this one
— keeps each file under the same rough ceiling instead of growing one
file past it. Both modules stay under the shared ``yoghurt.models``
package and export through ``models/__init__.py`` exactly like a
single-file batch would.

All nine captures that carry any earnings-family module in this corpus are
EQUITY (the ETF/MUTUALFUND/INDEX/CURRENCY/FUTURE/CRYPTOCURRENCY/OPTION
captures carry none of these six modules at all).

Reconciliation notes:

- ``earnings``, ``earningsGaap``, and ``earningsNonGaap`` are the same
  wire shape (:class:`EarningsModule` below): every field, including the
  nested ``earningsChart``/``financialsChart`` blocks, matches
  field-for-field. They are genuinely different *data* though — Yahoo
  fills ``earnings`` with a copy of whichever of ``earningsGaap``/
  ``earningsNonGaap`` matches ``defaultMethodology`` (verified: ``earnings
  == earningsGaap`` on captures where ``defaultMethodology == "gaap"``,
  ``earnings == earningsNonGaap`` where it's ``"non-gaap"``, and
  ``earningsGaap != earningsNonGaap`` whenever GAAP and non-GAAP EPS
  diverge, for example ``AAPL``). All three modules share
  :class:`EarningsModule`.
- ``earningsChart.quarterly[]`` (:class:`EarningsChartQuarter`) rows for a
  quarter that hasn't reported yet omit ``actual``, ``difference``,
  ``reportedDate``, and ``surprisePct`` outright (not merely null) — the
  corpus's one forward-looking row (``OKLO``'s ``1Q2026``, still only an
  estimate) has none of the four. ``earningsChart.currentQuarterEstimate``
  is similarly absent (not null) on the two lowest-analyst-coverage
  captures (``7203.T``, ``BAC-PL``).
- Every date-shaped field in ``earningsChart``/``financialsChart`` was
  checked for midnight-alignment individually before typing, per the
  plan's instruction: ``periodEndDate`` and ``currentPeriodEndDate`` are
  midnight-UTC-aligned on every observed value (tier 1,
  ``datetime.date``), while ``reportedDate`` and ``earningsDate`` are
  never midnight-aligned (session-anchored announcement timestamps,
  for example 20:30 UTC after a US market close) and stay tier 3 (aware-UTC
  ``datetime.datetime``, no in-model timezone context), mirroring
  ``calendarEvents.earnings``'s identical divergence in
  :mod:`yoghurt.models.summary_financials`.
- ``financialsChart.yearly[].date`` is a bare *year* integer (for example
  ``2022``), while ``financialsChart.quarterly[].date`` and
  ``earningsChart.quarterly[].date`` are quarter-label *strings* (for
  example ``"2Q2025"``) — a genuine type divergence between sibling
  ``date`` keys at different nesting levels, not a spelling
  inconsistency; both stay as their wire types rather than being coerced
  to a shared shape.
- ``earningsHistory.history[]`` (:class:`EarningsHistoryEntry`) is the
  first ``RawDate`` usage outside batch c1's statement-adjacent fields:
  ``quarter`` wraps as ``{raw, fmt}`` (``fmt`` a human-readable
  ``"YYYY-MM-DD"`` string) on every one of the 32 corpus entries.
  ``epsActual``/``epsEstimate``/``epsDifference``/``surprisePercent`` wrap
  as ``{raw, fmt}`` too (``RawFloat``); ``epsActual``/``epsDifference``/
  ``surprisePercent`` are the same "not-yet-reported" absence as
  ``earningsChart``'s ``actual``/``difference``/``surprisePct`` (the
  corpus's one forward row, again ``OKLO``'s ``-1q``, omits all three
  outright rather than sending ``{}``).
- ``earningsTrend.trend[]`` (:class:`EarningsTrendEntry`) is this batch's
  proving ground for the ``{}``-means-``None`` extension to the ``Raw*``
  unwrap rule (see :mod:`yoghurt.models._base`): on ``BAC-PL`` (a
  preferred share with no analyst coverage), every wrapped field in
  ``growth``, ``earningsEstimate``, ``epsTrend``, and ``epsRevisions``
  is sent as ``{}`` rather than omitted or wrapped with a real ``raw``
  value, and their sibling plain-string currency fields
  (``earningsCurrency``, ``epsTrendCurrency``, ``epsRevisionsCurrency``)
  go ``null`` in the same rows. ``epsRevisions.downLast90days``
  specifically is ``{}`` on every single one of the 36 corpus trend rows
  (not just BAC-PL/``7203.T``) — Yahoo appears to never populate this
  particular revision window — so it is optional even where its sibling
  revision fields are required. ``endDate`` is a bare ISO calendar-date
  *string* (for example ``"2026-06-30"``), unlike this batch's other
  date-shaped fields, which are epoch-based; pydantic parses it directly
  into ``datetime.date``, mirroring
  ``AssetProfile.start_date``'s precedent in
  :mod:`yoghurt.models.summary_identity`. ``period`` has only ever been
  observed as ``"0q"``, ``"+1q"``, ``"0y"``, ``"+1y"`` (one of each per
  capture) — a small, evidently complete quarter/year-offset vocabulary,
  but four values is still thin evidence for a closed vocabulary here, so
  it stays plain ``str``, consistent with the batch c1 precedent for
  similarly small observed vocabularies (``pageViews`` trends).
  ``numberOfAnalysts`` wraps with a ``longFmt`` alongside
  ``raw``/``fmt`` in most sub-shapes (three keys) but only ``raw``/``fmt``
  (two keys) in ``earningsEstimate.numberOfAnalysts`` — both are valid
  ``Raw*`` shapes since the unwrap rule accepts any subset of
  ``{raw, fmt, longFmt}``.
- ``earningsCallTranscripts.transcripts[]`` (:class:`EarningsCallTranscript`)
  entries are universal in shape across all 396 corpus entries (every key
  present on every entry). ``date``/``updated`` are session-anchored
  timestamps (verified never midnight-aligned), tier 3 like this module's
  siblings above. ``type`` (``"IN_HOUSE"``, ``"RAW"``) and ``eventType``
  (``"Earnings call"``, ``"Earnings Call"`` — inconsistent capitalization
  from Yahoo, not a distinct value) each have only two observed forms
  across hundreds of entries; kept plain ``str`` rather than an enum,
  matching this batch's other thinly evidenced vocabularies.
"""

from __future__ import annotations

import datetime  # noqa: TC003 - pydantic needs this at runtime to resolve annotations

from pydantic import Field

from yoghurt.models._base import (
    RawDate,
    RawFloat,
    RawFloatOrNone,
    RawInt,
    RawIntOrNone,
    YahooModel,
)


class EarningsChartQuarter(YahooModel):
    """One quarterly row in an :class:`EarningsModule`'s ``earningsChart``."""

    actual: float | None = None
    """
    Actual reported EPS for this quarter.

    Absent (not merely null) on a quarter that hasn't reported yet (the
    corpus's one example: ``OKLO``'s ``1Q2026`` row).

    Observed on: EQUITY summaries.
    """

    calendar_quarter: str
    """
    Calendar-quarter label for this row (for example ``"2Q2025"``).

    Observed on: EQUITY summaries.
    """

    date: str
    """
    Quarter label for this row (for example ``"2Q2025"``), matching
    ``fiscal_quarter``/``calendar_quarter`` in every observed row.

    A bare quarter-label string, not an epoch — a genuine type divergence
    from ``financialsChart.yearly[].date`` (a year integer) despite the
    shared wire key; see the module docstring.

    Observed on: EQUITY summaries.
    """

    difference: str | None = None
    """
    Difference between actual and estimated EPS, as a decimal string (for
    example ``"0.14"``).

    Wire value is a string, not a float — corpus wins over the tempting
    reinterpretation, mirroring ``CorporateActionMeta.amount``'s precedent
    in :mod:`yoghurt.models.summary_identity`. Absent (not merely null) on
    a quarter that hasn't reported yet.

    Observed on: EQUITY summaries.
    """

    estimate: float
    """
    Analyst-estimated EPS for this quarter.

    Observed on: EQUITY summaries.
    """

    fiscal_quarter: str
    """
    Fiscal-quarter label for this row (for example ``"3Q2025"``), which
    may differ from the calendar quarter depending on the company's fiscal
    calendar.

    Observed on: EQUITY summaries.
    """

    period_end_date: datetime.date
    """
    Last calendar day of this fiscal quarter.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    reported_date: datetime.datetime | None = None
    """
    Date and time this quarter's earnings were reported.

    Session-anchored timestamp (never midnight-aligned, verified against
    every corpus value), typed as aware-UTC ``datetime.datetime`` per tier
    3 of the epoch-typing ruling (no in-model timezone context). Absent
    (not merely null) on a quarter that hasn't reported yet.

    Observed on: EQUITY summaries.
    """

    surprise_pct: str | None = None
    """
    Percentage surprise between actual and estimated EPS, as a decimal
    string (for example ``"10.12"``).

    Wire value is a string, not a float — corpus wins over the tempting
    reinterpretation. Absent (not merely null) on a quarter that hasn't
    reported yet.

    Observed on: EQUITY summaries.
    """


class EarningsChart(YahooModel):
    """The ``earningsChart`` block of an :class:`EarningsModule`."""

    current_calendar_quarter: str
    """
    Label of the current calendar quarter (for example ``"2Q2026"``).

    Observed on: EQUITY summaries.
    """

    current_fiscal_quarter: str
    """
    Label of the current fiscal quarter (for example ``"3Q2026"``).

    Observed on: EQUITY summaries.
    """

    current_period_end_date: datetime.date
    """
    Last calendar day of the current fiscal quarter.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    current_quarter_estimate: float | None = None
    """
    Analyst-estimated EPS for the current quarter.

    Absent (not merely null) on the corpus's two lowest-analyst-coverage
    captures (``7203.T``, ``BAC-PL``).

    Observed on: EQUITY summaries.
    """

    current_quarter_estimate_date: str
    """
    Fiscal-quarter-within-year label for the current estimate (for example
    ``"2Q"``).

    Observed on: EQUITY summaries.
    """

    current_quarter_estimate_year: int
    """
    Calendar year of the current quarter estimate.

    Observed on: EQUITY summaries.
    """

    earnings_date: list[datetime.datetime]
    """
    Scheduled date(s) and time(s) of the upcoming earnings announcement.

    Session-anchored timestamps (never midnight-aligned, verified against
    every corpus value); typed as aware-UTC ``datetime.datetime`` per tier
    3 of the epoch-typing ruling, mirroring
    ``calendarEvents.earnings.earnings_date`` in
    :mod:`yoghurt.models.summary_financials`.

    Observed on: EQUITY summaries.
    """

    is_earnings_date_estimate: bool
    """
    Whether the earnings announcement date is an estimate rather than confirmed.

    Observed on: EQUITY summaries.
    """

    quarterly: list[EarningsChartQuarter]
    """
    Historical quarterly EPS actuals and estimates, oldest first.

    Observed on: EQUITY summaries.
    """


class FinancialsChartYear(YahooModel):
    """One annual row in an :class:`EarningsModule`'s ``financialsChart``."""

    date: int
    """
    Calendar year for this row (for example ``2022``).

    A bare year integer, not an epoch or quarter-label string — a genuine
    type divergence from ``earningsChart.quarterly[].date`` and
    ``financialsChart.quarterly[].date`` despite the shared wire key; see
    the module docstring.

    Observed on: EQUITY summaries.
    """

    earnings: float
    """
    Total annual earnings (net income).

    Observed on: EQUITY summaries.
    """

    profit_margin: float
    """
    Annual earnings as a percentage of annual revenue.

    Observed on: EQUITY summaries.
    """

    revenue: float
    """
    Total annual revenue.

    Observed on: EQUITY summaries.
    """


class FinancialsChartQuarter(YahooModel):
    """One quarterly row in an :class:`EarningsModule`'s ``financialsChart``."""

    date: str
    """
    Quarter label for this row (for example ``"2Q2025"``).

    A bare quarter-label string, matching
    ``earningsChart.quarterly[].date``'s shape but distinct from
    ``financialsChart.yearly[].date`` (a year integer); see the module
    docstring.

    Observed on: EQUITY summaries.
    """

    earnings: float
    """
    Total quarterly earnings (net income).

    Observed on: EQUITY summaries.
    """

    fiscal_quarter: str
    """
    Fiscal-quarter label for this row (for example ``"3Q2025"``).

    Observed on: EQUITY summaries.
    """

    profit_margin: float
    """
    Quarterly earnings as a percentage of quarterly revenue.

    Observed on: EQUITY summaries.
    """

    revenue: float
    """
    Total quarterly revenue.

    Observed on: EQUITY summaries.
    """


class FinancialsChart(YahooModel):
    """The ``financialsChart`` block of an :class:`EarningsModule`."""

    quarterly: list[FinancialsChartQuarter]
    """
    Historical quarterly revenue, earnings, and margin, oldest first.

    Observed on: EQUITY summaries.
    """

    yearly: list[FinancialsChartYear]
    """
    Historical annual revenue, earnings, and margin, oldest first.

    Observed on: EQUITY summaries.
    """


class EarningsModule(YahooModel):
    """The ``earnings``/``earningsGaap``/``earningsNonGaap`` modules.

    All three modules share this exact shape; see the module docstring for
    why ``earnings`` mirrors whichever of the GAAP/non-GAAP siblings
    matches ``default_methodology`` rather than being a distinct shape.
    """

    default_methodology: str
    """
    Which EPS methodology (``"gaap"``/``"non-gaap"``) the ``earnings``
    module mirrors.

    Observed on: EQUITY summaries.
    """

    earnings_chart: EarningsChart
    """
    Quarterly EPS actuals, estimates, and the current quarter's outlook.

    Observed on: EQUITY summaries.
    """

    financial_currency: str
    """
    Currency in which these earnings figures are reported.

    Observed on: EQUITY summaries.
    """

    financials_chart: FinancialsChart
    """
    Annual and quarterly revenue/earnings/margin history.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """


class EarningsHistoryEntry(YahooModel):
    """One quarterly row in the ``earningsHistory`` module's ``history`` list."""

    currency: str
    """
    Currency in which this entry's EPS figures are reported.

    Observed on: EQUITY summaries.
    """

    eps_actual: RawFloat | None = None
    """
    Actual reported EPS for this quarter.

    Wire value is a ``{raw, fmt}`` wrapper when present. Absent (not
    merely null or ``{}``) on a quarter that hasn't reported yet (the
    corpus's one example: ``OKLO``'s ``-1q`` row).

    Observed on: EQUITY summaries.
    """

    eps_difference: RawFloat | None = None
    """
    Difference between actual and estimated EPS.

    Wire value is a ``{raw, fmt}`` wrapper when present. Absent (not
    merely null or ``{}``) on a quarter that hasn't reported yet.

    Observed on: EQUITY summaries.
    """

    eps_estimate: RawFloat
    """
    Analyst-estimated EPS for this quarter.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal); see :mod:`yoghurt.models._base`.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Observed on: EQUITY summaries.
    """

    period: str
    """
    Relative-quarter label for this entry (observed values: ``"-4q"``,
    ``"-3q"``, ``"-2q"``, ``"-1q"``).

    Observed on: EQUITY summaries.
    """

    quarter: RawDate
    """
    Last calendar day of this quarter.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal), with ``raw`` an epoch-seconds calendar date (verified
    midnight-UTC-aligned) and ``fmt`` a human-readable ``"YYYY-MM-DD"``
    string; see :mod:`yoghurt.models._base`.

    Observed on: EQUITY summaries.
    """

    surprise_percent: RawFloat | None = None
    """
    Percentage surprise between actual and estimated EPS.

    Wire value is a ``{raw, fmt}`` wrapper when present. Absent (not
    merely null or ``{}``) on a quarter that hasn't reported yet.

    Observed on: EQUITY summaries.
    """


class EarningsHistory(YahooModel):
    """The ``earningsHistory`` module: trailing quarterly EPS actuals vs. estimates."""

    default_methodology: str
    """
    Which EPS methodology (``"gaap"``/``"non-gaap"``) these figures use.

    Observed on: EQUITY summaries.
    """

    history: list[EarningsHistoryEntry]
    """
    Trailing quarterly EPS actual-vs-estimate entries, oldest first.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """


class EarningsEstimate(YahooModel):
    """The ``earningsEstimate`` block of one :class:`EarningsTrendEntry`."""

    avg: RawFloatOrNone = None
    """
    Mean analyst EPS estimate for this period.

    Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period (the
    corpus's example: ``BAC-PL``); see :mod:`yoghurt.models._base`.

    Observed on: EQUITY summaries.
    """

    earnings_currency: str | None = None
    """
    Currency in which these earnings estimates are reported.

    Null (rather than a wrapper) alongside the rest of this group's
    ``{}`` fields on the corpus's no-analyst-coverage example (``BAC-PL``).

    Observed on: EQUITY summaries.
    """

    growth: RawFloatOrNone = None
    """
    Projected year-over-year EPS growth for this period.

    Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """

    high: RawFloatOrNone = None
    """
    Highest analyst EPS estimate for this period.

    Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """

    low: RawFloatOrNone = None
    """
    Lowest analyst EPS estimate for this period.

    Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """

    number_of_analysts: RawIntOrNone = None
    """
    Number of analysts contributing to this estimate.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """

    year_ago_eps: RawFloatOrNone = None
    """
    Actual EPS for the same period one year prior.

    Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """


class RevenueEstimate(YahooModel):
    """The ``revenueEstimate`` block of one :class:`EarningsTrendEntry`."""

    avg: RawFloat
    """
    Mean analyst revenue estimate for this period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry
    (universal, unlike its ``earningsEstimate`` counterpart — this group
    is never observed fully ``{}`` in this corpus); see
    :mod:`yoghurt.models._base`.

    Observed on: EQUITY summaries.
    """

    growth: RawFloat
    """
    Projected year-over-year revenue growth for this period.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry.

    Observed on: EQUITY summaries.
    """

    high: RawFloat
    """
    Highest analyst revenue estimate for this period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry.

    Observed on: EQUITY summaries.
    """

    low: RawFloat
    """
    Lowest analyst revenue estimate for this period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry.

    Observed on: EQUITY summaries.
    """

    number_of_analysts: RawInt
    """
    Number of analysts contributing to this estimate.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry.

    Observed on: EQUITY summaries.
    """

    revenue_currency: str
    """
    Currency in which these revenue estimates are reported.

    Observed on: EQUITY summaries.
    """

    year_ago_revenue: RawFloat
    """
    Actual revenue for the same period one year prior.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry.

    Observed on: EQUITY summaries.
    """


class EpsTrend(YahooModel):
    """The ``epsTrend`` block of one :class:`EarningsTrendEntry`."""

    current: RawFloatOrNone = None
    """
    Current consensus EPS estimate for this period.

    Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """

    eps_trend_currency: str | None = None
    """
    Currency in which these EPS trend figures are reported.

    Null (rather than a wrapper) alongside the rest of this group's
    ``{}`` fields on the corpus's no-analyst-coverage example (``BAC-PL``).

    Observed on: EQUITY summaries.
    """

    ninety_days_ago: RawFloatOrNone = Field(default=None, alias="90daysAgo")
    """
    Consensus EPS estimate as of 90 days ago.

    Wire spelling is ``90daysAgo`` (a leading digit); ``to_camel`` alone
    cannot reproduce it from a snake_case name, so this field carries an
    explicit alias override. Wire value is a ``{raw, fmt}`` wrapper, or
    ``{}`` (unwraps to ``None``) when Yahoo has no analyst coverage for
    this period.

    Observed on: EQUITY summaries.
    """

    seven_days_ago: RawFloatOrNone = Field(default=None, alias="7daysAgo")
    """
    Consensus EPS estimate as of 7 days ago.

    Wire spelling is ``7daysAgo``; see ``ninety_days_ago`` for the alias
    rationale. Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps
    to ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """

    sixty_days_ago: RawFloatOrNone = Field(default=None, alias="60daysAgo")
    """
    Consensus EPS estimate as of 60 days ago.

    Wire spelling is ``60daysAgo``; see ``ninety_days_ago`` for the alias
    rationale. Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps
    to ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """

    thirty_days_ago: RawFloatOrNone = Field(default=None, alias="30daysAgo")
    """
    Consensus EPS estimate as of 30 days ago.

    Wire spelling is ``30daysAgo``; see ``ninety_days_ago`` for the alias
    rationale. Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps
    to ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """


class EpsRevisions(YahooModel):
    """The ``epsRevisions`` block of one :class:`EarningsTrendEntry`."""

    down_last_30_days: RawIntOrNone = Field(default=None, alias="downLast30days")
    """
    Number of downward EPS estimate revisions in the last 30 days.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """

    down_last_7_days: RawIntOrNone = Field(default=None, alias="downLast7Days")
    """
    Number of downward EPS estimate revisions in the last 7 days.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period, or when
    ``fmt`` would be a literal zero (Yahoo omits ``fmt`` rather than
    sending ``"0"`` — the wrapper still resolves ``raw`` in that case).

    Observed on: EQUITY summaries.
    """

    down_last_90_days: RawIntOrNone = Field(default=None, alias="downLast90days")
    """
    Number of downward EPS estimate revisions in the last 90 days.

    Wire spelling is ``downLast90days`` (lowercase ``days``, unlike its
    ``downLast7Days``/``downLast30days``... siblings' mix of casing);
    ``to_camel`` alone would produce ``downLast90Days``, so this field
    carries an explicit alias override.

    Wire value is ``{}`` (unwraps to ``None``) on every one of the 36
    corpus trend rows, not merely the no-analyst-coverage examples —
    Yahoo appears to never populate this particular revision window in
    this corpus.

    Observed on: EQUITY summaries.
    """

    eps_revisions_currency: str | None = None
    """
    Currency in which these EPS revision counts are reported.

    Null (rather than a wrapper) alongside the rest of this group's
    ``{}`` fields on the corpus's no-analyst-coverage example (``BAC-PL``).

    Observed on: EQUITY summaries.
    """

    up_last_30_days: RawIntOrNone = Field(default=None, alias="upLast30days")
    """
    Number of upward EPS estimate revisions in the last 30 days.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """

    up_last_7_days: RawIntOrNone = Field(default=None, alias="upLast7days")
    """
    Number of upward EPS estimate revisions in the last 7 days.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period.

    Observed on: EQUITY summaries.
    """


class EarningsTrendEntry(YahooModel):
    """One period's row in the ``earningsTrend`` module's ``trend`` list.

    The corpus's proving ground for the ``{}``-means-``None`` extension to
    the ``Raw*`` unwrap rule; see the module docstring.
    """

    earnings_estimate: EarningsEstimate
    """
    Consensus EPS estimate details for this period.

    Observed on: EQUITY summaries.
    """

    end_date: datetime.date
    """
    Last calendar day of this period.

    A bare ISO calendar-date string (for example ``"2026-06-30"``) on the
    wire, unlike this batch's other date-shaped fields, which are
    epoch-based; pydantic parses it directly into ``datetime.date``.

    Observed on: EQUITY summaries.
    """

    eps_revisions: EpsRevisions
    """
    Counts of recent upward/downward EPS estimate revisions.

    Observed on: EQUITY summaries.
    """

    eps_trend: EpsTrend
    """
    Consensus EPS estimate as tracked over the past 7/30/60/90 days.

    Observed on: EQUITY summaries.
    """

    growth: RawFloatOrNone = None
    """
    Projected year-over-year EPS growth for this period.

    Wire value is a ``{raw, fmt}`` wrapper, or ``{}`` (unwraps to
    ``None``) when Yahoo has no analyst coverage for this period (the
    corpus's examples: ``7203.T``, ``BAC-PL``).

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Observed on: EQUITY summaries.
    """

    period: str
    """
    Relative period label for this entry (observed values: ``"0q"``,
    ``"+1q"``, ``"0y"``, ``"+1y"``).

    Only four values, one of each per capture; not enough evidence for a
    closed vocabulary, so this stays plain ``str``.

    Observed on: EQUITY summaries.
    """

    revenue_estimate: RevenueEstimate
    """
    Consensus revenue estimate details for this period.

    Observed on: EQUITY summaries.
    """


class EarningsTrend(YahooModel):
    """The ``earningsTrend`` module: forward EPS/revenue estimates and trends."""

    default_methodology: str
    """
    Which EPS methodology (``"gaap"``/``"non-gaap"``) these figures use.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """

    trend: list[EarningsTrendEntry]
    """
    Forward-looking earnings/revenue estimate entries, one per tracked
    period (observed: current and next quarter, current and next year).

    Observed on: EQUITY summaries.
    """


class EarningsCallTranscript(YahooModel):
    """One entry in the ``earningsCallTranscripts`` module's ``transcripts`` list."""

    date: datetime.datetime
    """
    Date and time of the earnings call.

    Session-anchored timestamp (never midnight-aligned, verified against
    every corpus value), typed as aware-UTC ``datetime.datetime`` per tier
    3 of the epoch-typing ruling (no in-model timezone context).

    Observed on: EQUITY summaries.
    """

    event_id: int
    """
    Yahoo's internal identifier for the earnings event.

    Observed on: EQUITY summaries.
    """

    event_type: str
    """
    Kind of event this transcript covers (observed values: ``"Earnings
    call"``, ``"Earnings Call"`` — inconsistent capitalization from
    Yahoo, not a distinct value).

    Two observed forms across 396 entries is not enough evidence for a
    closed vocabulary, so this stays plain ``str``.

    Observed on: EQUITY summaries.
    """

    fiscal_period: str
    """
    Fiscal quarter this transcript covers (observed values: ``"Q1"``,
    ``"Q2"``, ``"Q3"``, ``"Q4"``).

    Observed on: EQUITY summaries.
    """

    fiscal_year: int
    """
    Fiscal year this transcript covers.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Observed on: EQUITY summaries.
    """

    s3_url: str
    """
    Internal storage URL for the transcript's underlying data.

    Observed on: EQUITY summaries.
    """

    title: str
    """
    Human-readable title of the transcript (for example ``"AAPL Q2 FY2026
    earnings call transcript"``).

    Observed on: EQUITY summaries.
    """

    transcript_id: int
    """
    Yahoo's internal identifier for this transcript.

    Observed on: EQUITY summaries.
    """

    type: str
    """
    Source of the transcript (observed values: ``"IN_HOUSE"``, ``"RAW"``).

    Two observed values across 396 entries is not enough evidence for a
    closed vocabulary, so this stays plain ``str``.

    Observed on: EQUITY summaries.
    """

    updated: datetime.datetime
    """
    Date and time this transcript record was last updated.

    Session-anchored timestamp (never midnight-aligned, verified against
    every corpus value), typed as aware-UTC ``datetime.datetime`` per tier
    3 of the epoch-typing ruling.

    Observed on: EQUITY summaries.
    """

    url: str
    """
    URL of the transcript's Yahoo Finance page.

    Observed on: EQUITY summaries.
    """


class EarningsCallTranscripts(YahooModel):
    """The ``earningsCallTranscripts`` module: earnings call transcript listings."""

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """

    transcripts: list[EarningsCallTranscript]
    """
    Earnings call transcript entries, most recent first.

    Observed on: EQUITY summaries.
    """
