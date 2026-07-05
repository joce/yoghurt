"""Typed financial-snapshot models for the ``quote-summary`` endpoint.

Reconciled against the probe corpus at ``tests/fixtures/corpus/quote-summary/``
(23 valid captures across EQUITY, ETF, MUTUALFUND, CRYPTOCURRENCY, CURRENCY,
FUTURE, INDEX, and OPTION quoteTypes), captured 2026-07-04. Regenerate the
applicability evidence with
``uv run python -m tools.fields_report quote-summary:<module>`` after a
corpus refresh (see ``tools/fields_report.py`` for the generic per-module
stream this evidence is built from). This module covers four of the ten
batch c2 modules of the Part 3c plan: ``financialData``,
``defaultKeyStatistics``, ``calendarEvents``, and ``financialsTemplate``.
The remaining six earnings-family modules live in
:mod:`yoghurt.models.summary_earnings` (see that module's docstring for the
file-split rationale). Applicability lines use "Observed on: <types>
summaries." per the plan's applicability-noun ruling for this endpoint
family.

Reconciliation notes:

- ``financialData`` and ``financialsTemplate`` are EQUITY-only in this
  corpus (9 of 9 captures each); ``calendarEvents`` is likewise EQUITY-only
  (9 of 9). ``defaultKeyStatistics`` is the widest of the four (18 of 23
  captures: EQUITY, ETF, INDEX, MUTUALFUND), and its shape genuinely
  narrows for non-EQUITY quoteTypes — the five INDEX captures carry only 9
  of its keys, all fund-oriented statistics fields (``bookValue``,
  ``sharesOutstanding``, and similar) are EQUITY/ETF/MUTUALFUND-only.
- Every field on all four modules is a bare scalar on the wire; no ``Raw*``
  wrapper is observed anywhere in this batch's headline modules (matching
  the plan's expectation that wrappers appear only in nested statement/
  earnings rows, which live in the sibling ``summary_earnings`` module).
- ``defaultKeyStatistics.category``, ``.fundFamily``, ``.legalType``,
  ``.lastSplitFactor``, ``.latestShareClass``, and ``.leadInvestor`` are
  the required-but-nullable pattern from batch c1: the key is present on
  every one of the 18 captures (EQUITY, ETF, INDEX, MUTUALFUND alike) but
  its value is null except for ``category``/``fundFamily``/``legalType``
  on the three ETF captures (``QQQ``, ``SPY``, ``VT``) that actually
  resolve a fund category/family/legal-type string.
  ``latestShareClass``/``leadInvestor`` are null on literally every
  capture in this corpus (including the fund ones) — still required
  because the key itself is universal, per the evidence-driven
  optionality rule (required iff the *key* is universal, independent of
  its value).
- Epoch fields on both ``defaultKeyStatistics`` and ``calendarEvents`` are
  calendar-date epochs, verified midnight-UTC-aligned against every
  observed value in the corpus, and typed ``datetime.date`` directly
  (tier 1 of the epoch-typing ruling):
  ``defaultKeyStatistics.dateShortInterest``, ``.fundInceptionDate``,
  ``.lastDividendDate``, ``.lastFiscalYearEnd``, ``.lastSplitDate``,
  ``.mostRecentQuarter``, ``.nextFiscalYearEnd``,
  ``.sharesShortPreviousMonthDate``; and ``calendarEvents.dividendDate``/
  ``.exDividendDate``. This is a genuine divergence from
  ``calendarEvents.earnings.earningsDate``/``.earningsCallDate``
  (see :class:`Earnings` below), which are session-anchored timestamps,
  never midnight-aligned, confirmed by explicitly checking every corpus
  value before typing (per the plan's instruction to verify
  midnight-alignment per field before applying tier 1) — those two stay
  tier 3 (aware-UTC ``datetime.datetime``, no in-model timezone context),
  matching ``ChartDividend.date``'s precedent in
  :mod:`yoghurt.models.chart`.
- ``financialsTemplate.code`` has only ever been observed as ``"N"``
  (6 captures), ``"B"`` (2), or ``"U"`` (1) — three values across nine
  captures is not enough evidence for a closed vocabulary, so it stays
  plain ``str``.
- ``calendarEvents.earnings`` (:class:`Earnings`) is a nested sub-model
  whose ``earningsAverage``/``.earningsLow``/``.earningsHigh`` fields are
  present on 7 of 9 captures (absent together on ``7203.T`` and
  ``BAC-PL``, both low-analyst-coverage symbols) while
  ``earningsDate``/``.earningsCallDate``/``.isEarningsDateEstimate``/
  ``.revenueAverage``/``.revenueLow``/``.revenueHigh`` are universal.
  ``earningsDate``/``.earningsCallDate`` are lists (Yahoo's shape allows
  more than one upcoming date, though every corpus example has 0 or 1
  entries — ``BAC-PL``'s ``earningsDate`` is the sole empty-list example).
"""

from __future__ import annotations

import datetime  # noqa: TC003 - pydantic needs this at runtime to resolve annotations

from pydantic import Field

from yoghurt.models._base import YahooModel


class Earnings(YahooModel):
    """The nested ``earnings`` block inside the ``calendarEvents`` module.

    Distinct from :class:`~yoghurt.models.summary_earnings.EarningsModule`
    (the standalone ``earnings``/``earningsGaap``/``earningsNonGaap``
    modules): same wire key, unrelated shape.
    """

    earnings_average: float | None = None
    """
    Mean analyst EPS estimate for the upcoming earnings report.

    Absent (not merely null) on low-analyst-coverage captures (``7203.T``,
    ``BAC-PL``); always accompanied by ``earnings_low``/``earnings_high``.

    Observed on: EQUITY summaries.
    """

    earnings_call_date: list[datetime.datetime]
    """
    Scheduled date(s) and time(s) of the earnings call.

    Session-anchored timestamps (never midnight-aligned, verified against
    every corpus value), unlike this module's sibling
    ``exDividendDate``/``dividendDate``; typed as aware-UTC
    ``datetime.datetime`` per tier 3 of the epoch-typing ruling (no
    in-model timezone context), mirroring
    :class:`~yoghurt.models.chart.ChartDividend`'s precedent.

    Observed on: EQUITY summaries.
    """

    earnings_date: list[datetime.datetime]
    """
    Scheduled date(s) and time(s) of the earnings announcement.

    Session-anchored timestamps (never midnight-aligned, verified against
    every corpus value); typed as aware-UTC ``datetime.datetime`` per tier
    3 of the epoch-typing ruling, same as ``earnings_call_date``. Can be an
    empty list (``BAC-PL``'s sole observed example).

    Observed on: EQUITY summaries.
    """

    earnings_high: float | None = None
    """
    Highest analyst EPS estimate for the upcoming earnings report.

    Absent (not merely null) on low-analyst-coverage captures (``7203.T``,
    ``BAC-PL``); always accompanied by ``earnings_average``/``earnings_low``.

    Observed on: EQUITY summaries.
    """

    earnings_low: float | None = None
    """
    Lowest analyst EPS estimate for the upcoming earnings report.

    Absent (not merely null) on low-analyst-coverage captures (``7203.T``,
    ``BAC-PL``); always accompanied by ``earnings_average``/``earnings_high``.

    Observed on: EQUITY summaries.
    """

    is_earnings_date_estimate: bool
    """
    Whether the earnings announcement date is an estimate rather than confirmed.

    Observed on: EQUITY summaries.
    """

    revenue_average: float
    """
    Mean analyst revenue estimate for the upcoming earnings report.

    Observed on: EQUITY summaries.
    """

    revenue_high: float
    """
    Highest analyst revenue estimate for the upcoming earnings report.

    Observed on: EQUITY summaries.
    """

    revenue_low: float
    """
    Lowest analyst revenue estimate for the upcoming earnings report.

    Observed on: EQUITY summaries.
    """


class CalendarEvents(YahooModel):
    """The ``calendarEvents`` module: upcoming earnings and dividend dates."""

    dividend_date: datetime.date | None = None
    """
    Date the next dividend is expected to be paid.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    earnings: Earnings
    """
    Details of the upcoming earnings announcement and call.

    Observed on: EQUITY summaries.
    """

    ex_dividend_date: datetime.date | None = None
    """
    Date on which a buyer would no longer be entitled to the next dividend.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """


class FinancialsTemplate(YahooModel):
    """The ``financialsTemplate`` module: which statement layout Yahoo uses."""

    code: str
    """
    Financial statement template code (observed values: ``"N"``, ``"B"``,
    ``"U"``).

    Three values across nine captures is not enough evidence for a closed
    vocabulary, so this stays plain ``str``.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """


class FinancialData(YahooModel):
    """The ``financialData`` module: profitability, cash, and analyst-target metrics."""

    current_price: float
    """
    Latest market price used as the basis for these financial metrics.

    Observed on: EQUITY summaries.
    """

    current_ratio: float | None = None
    """
    Current assets divided by current liabilities.

    Observed on: EQUITY summaries.
    """

    debt_to_equity: float | None = None
    """
    Total debt divided by total shareholder equity, as a percentage.

    Observed on: EQUITY summaries.
    """

    earnings_growth: float | None = None
    """
    Year-over-year growth in earnings.

    Observed on: EQUITY summaries.
    """

    ebitda: float | None = None
    """
    Earnings before interest, taxes, depreciation, and amortization.

    Observed on: EQUITY summaries.
    """

    ebitda_margins: float
    """
    EBITDA as a percentage of total revenue.

    Observed on: EQUITY summaries.
    """

    financial_currency: str
    """
    Currency in which these financial figures are reported.

    Observed on: EQUITY summaries.
    """

    free_cashflow: float | None = None
    """
    Operating cash flow minus capital expenditures.

    Observed on: EQUITY summaries.
    """

    gross_margins: float
    """
    Gross profit as a percentage of total revenue.

    Observed on: EQUITY summaries.
    """

    gross_profits: float | None = None
    """
    Total revenue minus cost of goods sold.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """

    number_of_analyst_opinions: int | None = None
    """
    Number of analysts contributing to the price-target consensus.

    Observed on: EQUITY summaries.
    """

    operating_cashflow: float
    """
    Cash generated from normal business operations.

    Observed on: EQUITY summaries.
    """

    operating_margins: float
    """
    Operating income as a percentage of total revenue.

    Observed on: EQUITY summaries.
    """

    profit_margins: float
    """
    Net income as a percentage of total revenue.

    Observed on: EQUITY summaries.
    """

    quick_ratio: float | None = None
    """
    Liquid assets (excluding inventory) divided by current liabilities.

    Observed on: EQUITY summaries.
    """

    recommendation_key: str
    """
    Analyst consensus recommendation (for example ``"buy"``, ``"none"``).

    Not typed as a closed vocabulary: this batch's corpus has only two
    distinct values (``"buy"``, ``"none"``), too little evidence to
    enumerate Yahoo's full recommendation-key set.

    Observed on: EQUITY summaries.
    """

    recommendation_mean: float | None = None
    """
    Mean analyst recommendation score (lower is more bullish).

    Observed on: EQUITY summaries.
    """

    return_on_assets: float
    """
    Net income as a percentage of total assets.

    Observed on: EQUITY summaries.
    """

    return_on_equity: float
    """
    Net income as a percentage of shareholder equity.

    Observed on: EQUITY summaries.
    """

    revenue_growth: float | None = None
    """
    Year-over-year growth in total revenue.

    Observed on: EQUITY summaries.
    """

    revenue_per_share: float | None = None
    """
    Total revenue divided by shares outstanding.

    Observed on: EQUITY summaries.
    """

    target_high_price: float | None = None
    """
    Highest analyst price target.

    Observed on: EQUITY summaries.
    """

    target_low_price: float | None = None
    """
    Lowest analyst price target.

    Observed on: EQUITY summaries.
    """

    target_mean_price: float | None = None
    """
    Mean analyst price target.

    Observed on: EQUITY summaries.
    """

    target_median_price: float | None = None
    """
    Median analyst price target.

    Observed on: EQUITY summaries.
    """

    total_cash: float
    """
    Total cash and cash equivalents held by the company.

    Observed on: EQUITY summaries.
    """

    total_cash_per_share: float
    """
    Total cash divided by shares outstanding.

    Observed on: EQUITY summaries.
    """

    total_debt: float
    """
    Total interest-bearing debt held by the company.

    Observed on: EQUITY summaries.
    """

    total_revenue: float | None = None
    """
    Total revenue over the trailing twelve months.

    Observed on: EQUITY summaries.
    """


class DefaultKeyStatistics(YahooModel):
    """The ``defaultKeyStatistics`` module: valuation, share, and fund statistics.

    The widest-applicability module in this batch (EQUITY, ETF, INDEX, and
    MUTUALFUND in this corpus); its shape genuinely narrows for INDEX
    captures, which carry only the fund-agnostic subset (see the module
    docstring).
    """

    annual_holdings_turnover: float | None = None
    """
    Percentage of the fund's holdings replaced over the past year.

    Observed on: MUTUALFUND summaries.
    """

    annual_report_expense_ratio: float | None = None
    """
    Fund's annual operating expenses as a percentage of average net assets.

    Observed on: MUTUALFUND summaries.
    """

    beta: float | None = None
    """
    Measure of the security's volatility relative to the overall market.

    Observed on: EQUITY summaries.
    """

    beta_3_year: float | None = None
    """
    Fund's beta measured over the trailing 3 years.

    Observed on: ETF, MUTUALFUND summaries.
    """

    book_value: float | None = None
    """
    Net asset value per share based on the company's balance sheet.

    Observed on: EQUITY summaries.
    """

    category: str | None
    """
    Morningstar-style fund category (for example ``"Large Blend"``).

    Present on every capture in this corpus (EQUITY, ETF, INDEX,
    MUTUALFUND alike) but only ever non-null on the three ETF captures
    (``QQQ``, ``SPY``, ``VT``); required-but-nullable per the batch c1
    precedent.

    Observed on: EQUITY, ETF, INDEX, MUTUALFUND summaries.
    """

    date_short_interest: datetime.date | None = None
    """
    Date the short-interest figures were current as of.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    earnings_quarterly_growth: float | None = None
    """
    Year-over-year growth in quarterly earnings.

    Observed on: EQUITY summaries.
    """

    enterprise_to_ebitda: float | None = None
    """
    Enterprise value divided by EBITDA.

    Observed on: EQUITY summaries.
    """

    enterprise_to_revenue: float | None = None
    """
    Enterprise value divided by total revenue.

    Observed on: EQUITY summaries.
    """

    enterprise_value: float | None = None
    """
    Market capitalization plus debt, minority interest, and preferred
    equity, minus total cash and cash equivalents.

    Observed on: EQUITY summaries.
    """

    fifty_two_week_change: float | None = Field(default=None, alias="52WeekChange")
    """
    Total return over the trailing 52 weeks.

    Wire spelling is ``52WeekChange`` (a leading digit); ``to_camel`` alone
    would produce ``fiftyTwoWeekChange``, so this field carries an
    explicit alias override.

    Observed on: EQUITY, INDEX summaries.
    """

    five_year_average_return: float | None = None
    """
    Fund's average annual return over the trailing 5 years.

    Observed on: ETF summaries.
    """

    float_shares: int | None = None
    """
    Number of shares available for public trading.

    Observed on: EQUITY summaries.
    """

    forward_eps: float | None = None
    """
    Projected earnings per share for the next fiscal year.

    Observed on: EQUITY summaries.
    """

    forward_pe: float | None = Field(default=None, alias="forwardPE")
    """
    Projected price-to-earnings ratio for the next 12 months.

    Wire spelling is ``forwardPE`` (capitalized acronym); ``to_camel``
    alone would produce ``forwardPe``, so this field carries an explicit
    alias override.

    Observed on: EQUITY summaries.
    """

    fund_family: str | None
    """
    Company or family managing the fund (for example ``"Vanguard"``).

    Present on every capture in this corpus (EQUITY, ETF, INDEX,
    MUTUALFUND alike) but only ever non-null on the three ETF captures
    (``QQQ``, ``SPY``, ``VT``); required-but-nullable per the batch c1
    precedent.

    Observed on: EQUITY, ETF, INDEX, MUTUALFUND summaries.
    """

    fund_inception_date: datetime.date | None = None
    """
    Date the fund was first offered to investors.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: ETF, MUTUALFUND summaries.
    """

    held_percent_insiders: float | None = None
    """
    Percentage of shares held by company insiders.

    Observed on: EQUITY summaries.
    """

    held_percent_institutions: float | None = None
    """
    Percentage of shares held by institutional investors.

    Observed on: EQUITY summaries.
    """

    implied_shares_outstanding: int | None = None
    """
    Shares outstanding implied by market capitalization and price.

    Observed on: EQUITY summaries.
    """

    last_cap_gain: float | None = None
    """
    Most recent capital gains distribution per share.

    Observed on: MUTUALFUND summaries.
    """

    last_dividend_date: datetime.date | None = None
    """
    Date of the most recent dividend payment.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY, MUTUALFUND summaries.
    """

    last_dividend_value: float | None = None
    """
    Amount of the most recent dividend payment per share.

    Observed on: EQUITY, MUTUALFUND summaries.
    """

    last_fiscal_year_end: datetime.date | None = None
    """
    End date of the company's most recently completed fiscal year.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    last_split_date: datetime.date | None = None
    """
    Date of the company's most recent stock split.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    last_split_factor: str | None
    """
    Ratio of the company's most recent stock split (for example ``"4:1"``).

    Present on every capture in this corpus (EQUITY, ETF, INDEX,
    MUTUALFUND alike) but only ever non-null on a subset of EQUITY
    captures; required-but-nullable per the batch c1 precedent.

    Observed on: EQUITY, ETF, INDEX, MUTUALFUND summaries.
    """

    latest_share_class: str | None
    """
    Most recently issued share class of the fund.

    Present on every capture in this corpus but never observed non-null;
    required-but-nullable per the batch c1 precedent.

    Observed on: EQUITY, ETF, INDEX, MUTUALFUND summaries.
    """

    lead_investor: str | None
    """
    Lead investor in the company's most recent funding round.

    Present on every capture in this corpus but never observed non-null;
    required-but-nullable per the batch c1 precedent.

    Observed on: EQUITY, ETF, INDEX, MUTUALFUND summaries.
    """

    legal_type: str | None
    """
    Fund's legal structure (for example ``"Exchange Traded Fund"``).

    Present on every capture in this corpus (EQUITY, ETF, INDEX,
    MUTUALFUND alike) but only ever non-null on the three ETF captures
    (``QQQ``, ``SPY``, ``VT``); required-but-nullable per the batch c1
    precedent.

    Observed on: EQUITY, ETF, INDEX, MUTUALFUND summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY, ETF, INDEX, MUTUALFUND summaries.
    """

    morning_star_overall_rating: float | None = None
    """
    Morningstar's overall star rating for the fund.

    Observed on: MUTUALFUND summaries.
    """

    morning_star_risk_rating: float | None = None
    """
    Morningstar's risk rating for the fund.

    Observed on: MUTUALFUND summaries.
    """

    most_recent_quarter: datetime.date | None = None
    """
    End date of the company's most recently reported fiscal quarter.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    net_income_to_common: float | None = None
    """
    Net income attributable to common shareholders.

    Observed on: EQUITY summaries.
    """

    next_fiscal_year_end: datetime.date | None = None
    """
    End date of the company's next fiscal year.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    peg_ratio: float | None = None
    """
    Price/earnings ratio divided by projected earnings growth.

    Observed on: EQUITY summaries.
    """

    price_hint: int
    """
    Decimal precision indicator for price values.

    Observed on: EQUITY, ETF, INDEX, MUTUALFUND summaries.
    """

    price_to_book: float | None = None
    """
    Market price per share divided by book value per share.

    Observed on: EQUITY summaries.
    """

    profit_margins: float | None = None
    """
    Net income as a percentage of total revenue.

    Observed on: EQUITY summaries.
    """

    s_and_p_52_week_change: float | None = Field(
        default=None, alias="SandP52WeekChange"
    )
    """
    S&P 500 index's total return over the trailing 52 weeks, for comparison.

    Wire spelling is ``SandP52WeekChange``; the Python field carries an
    explicit alias override since ``to_camel`` cannot reproduce a
    ``&``-derived abbreviation from a snake_case name.

    Observed on: EQUITY summaries.
    """

    shares_outstanding: int | None = None
    """
    Total number of shares currently outstanding.

    Observed on: EQUITY summaries.
    """

    shares_percent_shares_out: float | None = None
    """
    Shares short as a percentage of shares outstanding.

    Observed on: EQUITY summaries.
    """

    shares_short: int | None = None
    """
    Number of shares currently sold short.

    Observed on: EQUITY summaries.
    """

    shares_short_previous_month_date: datetime.date | None = None
    """
    Date the prior month's short-interest figures were current as of.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    shares_short_prior_month: int | None = None
    """
    Number of shares sold short as of the prior month.

    Observed on: EQUITY summaries.
    """

    short_percent_of_float: float | None = None
    """
    Shares short as a percentage of float shares.

    Observed on: EQUITY summaries.
    """

    short_ratio: float | None = None
    """
    Average daily trading volume it would take to cover all short positions.

    Observed on: EQUITY summaries.
    """

    three_year_average_return: float | None = None
    """
    Fund's average annual return over the trailing 3 years.

    Observed on: ETF summaries.
    """

    total_assets: int | None = None
    """
    Total net assets of the fund.

    Observed on: ETF, MUTUALFUND summaries.
    """

    trailing_eps: float | None = None
    """
    Earnings per share over the trailing twelve months.

    Observed on: EQUITY summaries.
    """

    yield_: float | None = Field(default=None, alias="yield")
    """
    Distribution yield of the fund.

    Wire spelling is the reserved word ``yield``; the Python field is
    named ``yield_`` with an explicit alias.

    Observed on: ETF summaries.
    """

    ytd_return: float | None = None
    """
    Year-to-date return on the fund.

    Observed on: MUTUALFUND summaries.
    """
