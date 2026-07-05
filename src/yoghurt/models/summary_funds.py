"""Typed fund-internals models for the ``quote-summary`` endpoint.

Reconciled against the probe corpus at ``tests/fixtures/corpus/quote-summary/``
(23 valid captures across EQUITY, ETF, MUTUALFUND, CRYPTOCURRENCY, CURRENCY,
FUTURE, INDEX, and OPTION quoteTypes), captured 2026-07-04. Regenerate the
applicability evidence with
``uv run python -m tools.fields_report quote-summary:<module>`` after a
corpus refresh (see ``tools/fields_report.py`` for the generic per-module
stream this evidence is built from). This module covers the remaining three
of the ten batch c4 modules (Part 3c plan): ``fundProfile``,
``fundPerformance``, and ``topHoldings``. The other seven batch c4 modules
live in the sibling :mod:`yoghurt.models.summary_holders`; see that module's
docstring for the file-split rationale.

**Thin evidence base.** Unlike every prior quote-summary batch, this file's
corpus support is only 4 captures total (``QQQ``, ``SPY``, ``VT`` — all
ETF — and ``VTSAX``, the corpus's sole MUTUALFUND capture), because
``fundProfile``/``fundPerformance``/``topHoldings`` are restricted to
ETF/MUTUALFUND quoteTypes. Every requiredness call in this module is
therefore drawn from at most 4 observations, and several MUTUALFUND-only
fields (``initInvestment``, ``subseqInvestment``, ``loadAdjustedReturns``,
``rankInCategory``, and ``managementInfo.startdate``) rest on the single
``VTSAX`` capture. None of the three modules carries a single ``Raw*``
wrapper — every field in this file is a bare scalar or a nested bare-scalar
structure, unlike the wrapper-heavy holder/statement modules elsewhere in
this endpoint family.

Reconciliation notes:

- ``fundProfile.feesExpensesInvestment``/``.feesExpensesInvestmentCat``
  (:class:`FundFees`) diverge in shape between ETF and MUTUALFUND: ETF
  captures carry ``annualHoldingsTurnover``/``totalNetAssets`` (always
  present, never on ``VTSAX``), while ``VTSAX`` alone carries
  ``netExpRatio``/``grossExpRatio`` (never on the three ETF captures).
  ``annualReportExpenseRatio`` is the only field universal across all 4.
  Rather than splitting into parallel ETF/MUTUALFUND fee shapes on a
  4-capture base, every field stays optional on one shared
  :class:`FundFees` model — corpus-honest given how thin the evidence is.
  ``projectionValues``/``projectionValuesCat`` are themselves a dynamic
  numeric bag (observed keys: ``"5y"``, ``"3y"``, ``"10y"`` on ``VTSAX``;
  an empty ``{}`` on all three ETF captures), so they are typed
  ``dict[str, float]`` rather than a fixed-field model, per the "resists
  honest typing" escape hatch for genuinely dynamic key sets (see the
  ``ChartEvents.dividends``/``.splits`` precedent in
  :mod:`yoghurt.models.chart` for the same ``dict[str, T]`` shape applied
  to a dynamic key set elsewhere in this codebase).
- ``fundProfile.managementInfo`` (:class:`FundManagementInfo`) sends
  ``managerName``/``managerBio`` as ``null`` on every ETF capture but
  populates both (plus a ``VTSAX``-only ``startdate`` epoch, verified
  midnight-UTC-aligned against the single observed value) on the
  MUTUALFUND capture — ETFs in this corpus are passively managed with no
  named portfolio manager to report, not a missing-field gap.
- ``fundProfile.legalType`` is ``null`` on ``VTSAX`` (mutual funds have no
  single-word wire classification in this corpus) but a populated string
  (``"Exchange Traded Fund"``) on every ETF capture; required-but-nullable,
  the key is present on all 4 captures.
- ``fundProfile.initInvestment``/``.subseqInvestment`` are present only on
  ``VTSAX`` (mutual-fund-specific minimum-investment figures that have no
  ETF analogue — ETFs trade in whole shares, not dollar minimums).
- ``fundPerformance.performanceOverview``/``.performanceOverviewCat``
  (:class:`FundPerformanceOverview`) gain seven MUTUALFUND-only fields on
  ``VTSAX`` (``bestOneYrTotalReturn``, ``bestThreeYrTotalReturn``,
  ``worstThreeYrTotalReturn``, ``morningStarReturnRating``,
  ``numYearsDown``, ``numYearsUp`` on the un-suffixed variant only — its
  ``Cat`` sibling never gains them in this corpus); the five fields shared
  with the ETF captures stay required, the rest optional.
- ``fundPerformance.trailingReturns``/``.trailingReturnsCat``
  (:class:`TrailingReturns`) are field-for-field identical (including
  ``lastBullMkt``/``lastBearMkt``) across all 4 captures;
  ``.trailingReturnsNav`` (:class:`TrailingReturnsNav`) shares every field
  except ``asOfDate``/``lastBullMkt``/``lastBearMkt`` — verified as a
  genuine, consistent subset rather than modeled as the same shape.
- ``fundPerformance.riskOverviewStatistics``/``.riskOverviewStatisticsCat``
  rows carry ``stdDev`` on all 4 ``riskStatistics`` captures but only on
  ``VTSAX``'s ``riskStatisticsCat`` (absent on the three ETF captures'
  ``Cat`` variant) — required-but-thin rather than dropped, typed optional
  given the narrower evidence on the ``Cat`` side (:class:`RiskStatisticsEntry`/
  :class:`RiskStatisticsCatEntry`). ``riskOverviewStatistics`` also carries
  a module-level ``riskRating`` (Morningstar-style overall risk score) only
  on ``VTSAX``, absent on every ETF capture.
- ``fundPerformance.annualTotalReturns.returns[]``/``.returnsCat[]``
  (:class:`AnnualReturn`) rows are universally ``{year: str, annualValue:
  float}`` except ``VTSAX``'s current partial year (``"2026"``), which
  omits ``annualValue`` outright (not merely null) because the year hasn't
  finished — ``annual_value`` is optional for this reason alone.
- ``fundPerformance.pastQuarterlyReturns.returns[]`` (:class:`QuarterlyReturn`)
  rows have a small, closed key set (only ``year``/``q1``/``q2``/``q3``/
  ``q4`` ever observed), unlike this file's genuinely dynamic bags
  (``projectionValues``, ``bondRatings``, ``sectorWeightings``): ``year``
  is required and ``q1``..``q4`` are four fixed optional fields —
  ``VTSAX``'s current-year row has only ``q1`` (the rest absent, not
  merely null, since the year hasn't finished), while every completed
  year has all four. Always an empty ``returns: []`` on the three ETF
  captures (Yahoo reports quarterly return history for mutual funds only
  in this corpus).
- ``fundPerformance.loadAdjustedReturns``/``.rankInCategory`` are present
  only on ``VTSAX`` — both are small fixed-key bags in the single observed
  example (``oneYear``/``threeYear``/``fiveYear``/``tenYear`` and
  ``ytd``/``oneMonth``/``threeMonth``/``oneYear``/``threeYear``/
  ``fiveYear`` respectively, the same period-label vocabulary used
  elsewhere in ``trailingReturns``), so both get dedicated models
  (:class:`LoadAdjustedReturns`, :class:`RankInCategory`) rather than
  dynamic bags, on the working assumption that Yahoo's period-label set is
  stable across this endpoint family; flag for re-verification once a
  second MUTUALFUND capture is available.
- ``topHoldings.holdings[]`` (:class:`Holding`) rows are field-for-field
  identical (``symbol``, ``holdingName``, ``holdingPercent``) across all 4
  captures. ``equityHoldings`` diverges sharply between ETF (4 valuation
  ratios) and MUTUALFUND (12 keys: the same 4 ratios plus a ``Cat``-suffixed
  sibling for each, plus ``medianMarketCap``/``medianMarketCapCat``/
  ``threeYearEarningsGrowth``/``threeYearEarningsGrowthCat``) — like
  ``fundProfile.feesExpensesInvestment`` above, both are small enough and
  thinly enough evidenced that ``equityHoldings``/``bondHoldings`` are
  typed ``dict[str, float]`` rather than fixed-field models.
  ``bondRatings``/``sectorWeightings`` are each a list of single-key
  dynamic dicts (a bond-rating grade or GICS-style sector name as the sole
  key, for example ``{"us_government": 0.0}``, ``{"technology":
  0.5865}``) — genuinely dynamic per-entry keys, typed
  ``list[dict[str, float]]``.
"""

from __future__ import annotations

import datetime  # noqa: TC003 - pydantic needs this at runtime to resolve annotations

from yoghurt.models._base import YahooModel


class FundManagementInfo(YahooModel):
    """The ``managementInfo`` block of a :class:`FundProfile`.

    ``manager_name``/``manager_bio`` are ``null`` on every ETF capture in
    this corpus and populated only on the sole MUTUALFUND capture
    (``VTSAX``); see the module docstring.
    """

    manager_bio: str | None
    """
    Biography of the fund's portfolio manager.

    Present (though null on every ETF capture) on all 4 corpus captures;
    only ever non-null on the sole MUTUALFUND capture.

    Observed on: ETF, MUTUALFUND summaries.
    """

    manager_name: str | None
    """
    Name of the fund's portfolio manager.

    Present (though null on every ETF capture, empty string on the sole
    MUTUALFUND capture) on all 4 corpus captures.

    Observed on: ETF, MUTUALFUND summaries.
    """

    startdate: datetime.date | None = None
    """
    Date the current manager began managing the fund.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds
    (verified against the sole observed value); pydantic converts it to a
    UTC calendar date. Only ever observed on ``VTSAX`` (this file's sole
    MUTUALFUND capture); see the module docstring.

    Observed on: MUTUALFUND summaries.
    """


class FundFees(YahooModel):
    """The ``feesExpensesInvestment``/``feesExpensesInvestmentCat`` blocks.

    Every field is optional on this thinly evidenced (4-capture), shape-
    divergent-by-quoteType shared model; see the module docstring.
    """

    annual_holdings_turnover: float | None = None
    """
    Percentage of the fund's holdings replaced over the past year.

    Present on every ETF capture; never observed on the sole MUTUALFUND
    capture.

    Observed on: ETF summaries.
    """

    annual_report_expense_ratio: float
    """
    Annual expense ratio as reported in the fund's prospectus.

    Universal across all 4 corpus captures, the only field shared by every
    quoteType this module has been observed on.

    Observed on: ETF, MUTUALFUND summaries.
    """

    gross_exp_ratio: float | None = None
    """
    Gross expense ratio before any fee waivers.

    Only ever observed on ``VTSAX`` (this file's sole MUTUALFUND capture).

    Observed on: MUTUALFUND summaries.
    """

    net_exp_ratio: float | None = None
    """
    Net expense ratio after fee waivers.

    Only ever observed on ``VTSAX``.

    Observed on: MUTUALFUND summaries.
    """

    projection_values: dict[str, float]
    """
    Projected cumulative expense per $10,000 invested, keyed by a
    dynamic year-horizon label (observed keys: ``"5y"``, ``"3y"``,
    ``"10y"``, ``VTSAX``-only).

    A dynamic numeric bag rather than a fixed-field model; see the module
    docstring. Always an empty ``{}`` on every ETF capture.

    Observed on: ETF, MUTUALFUND summaries.
    """

    total_net_assets: float | None = None
    """
    Total net assets of the fund, in millions.

    Present on every ETF capture; never observed on the sole MUTUALFUND
    capture.

    Observed on: ETF summaries.
    """


class FundFeesCat(YahooModel):
    """The category-average sibling of :class:`FundFees`.

    Wire key ``feesExpensesInvestmentCat``; the same shape-divergence-by-
    quoteType caveats apply, with ``projectionValuesCat`` as this
    variant's dynamic bag (wire key differs from ``FundFees``'s
    ``projectionValues``, otherwise identical treatment).
    """

    annual_holdings_turnover: float | None = None
    """
    Category-average percentage of fund holdings replaced over the past year.

    Present on every ETF capture; never observed on the sole MUTUALFUND
    capture.

    Observed on: ETF summaries.
    """

    annual_report_expense_ratio: float
    """
    Category-average annual expense ratio.

    Universal across all 4 corpus captures.

    Observed on: ETF, MUTUALFUND summaries.
    """

    projection_values_cat: dict[str, float]
    """
    Category-average projected cumulative expense per $10,000 invested,
    keyed by a dynamic year-horizon label.

    A dynamic numeric bag; see :class:`FundFees.projection_values` and the
    module docstring. Always an empty ``{}`` on every ETF capture.

    Observed on: ETF, MUTUALFUND summaries.
    """

    total_net_assets: float | None = None
    """
    Category-average total net assets, in millions.

    Present on every ETF capture; never observed on the sole MUTUALFUND
    capture.

    Observed on: ETF summaries.
    """


class FundProfile(YahooModel):
    """The ``fundProfile`` module: fund family, category, and fee overview.

    Thinly evidenced (4 captures: 3 ETF, 1 MUTUALFUND); several fields are
    MUTUALFUND-only on the strength of the single ``VTSAX`` observation.
    See the module docstring.
    """

    brokerages: list[str]
    """
    Brokerages through which this fund can be purchased.

    Always empty on ETF captures in this corpus; populated (122 entries)
    only on ``VTSAX``.

    Observed on: ETF, MUTUALFUND summaries.
    """

    category_name: str
    """
    Morningstar-style category classification (for example ``"Large
    Growth"``, ``"Large Blend"``).

    Observed on: ETF, MUTUALFUND summaries.
    """

    family: str
    """
    Fund family or sponsor (for example ``"Invesco"``, ``"Vanguard"``).

    Observed on: ETF, MUTUALFUND summaries.
    """

    fees_expenses_investment: FundFees
    """
    Fee and expense details for this fund.

    Observed on: ETF, MUTUALFUND summaries.
    """

    fees_expenses_investment_cat: FundFeesCat
    """
    Category-average fee and expense details, for comparison.

    Observed on: ETF, MUTUALFUND summaries.
    """

    init_investment: float | None = None
    """
    Minimum initial investment amount.

    Only ever observed on ``VTSAX`` (mutual funds have dollar minimums;
    ETFs trade in whole shares).

    Observed on: MUTUALFUND summaries.
    """

    legal_type: str | None
    """
    Legal structure of the fund (for example ``"Exchange Traded Fund"``).

    Present on every corpus capture; null on the sole MUTUALFUND capture.

    Observed on: ETF summaries.
    """

    management_info: FundManagementInfo
    """
    Portfolio manager details for this fund.

    Observed on: ETF, MUTUALFUND summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: ETF, MUTUALFUND summaries.
    """

    style_box_url: str
    """
    URL of the fund's Morningstar-style style-box image.

    Observed on: ETF, MUTUALFUND summaries.
    """

    subseq_investment: float | None = None
    """
    Minimum subsequent investment amount.

    Only ever observed on ``VTSAX``; see ``init_investment``.

    Observed on: MUTUALFUND summaries.
    """


class FundPerformanceOverview(YahooModel):
    """The ``performanceOverview`` block of a :class:`FundPerformance`.

    Gains six MUTUALFUND-only fields on ``VTSAX``; see the module
    docstring.
    """

    as_of_date: datetime.date
    """
    Date this performance snapshot was computed as of.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds
    (verified against every corpus value); pydantic converts it to a UTC
    calendar date.

    Observed on: ETF, MUTUALFUND summaries.
    """

    best_one_yr_total_return: float | None = None
    """
    Best trailing one-year total return in the fund's history.

    Only ever observed on ``VTSAX``.

    Observed on: MUTUALFUND summaries.
    """

    best_three_yr_total_return: float | None = None
    """
    Best trailing three-year annualized total return in the fund's history.

    Only ever observed on ``VTSAX``.

    Observed on: MUTUALFUND summaries.
    """

    five_yr_avg_return_pct: float
    """
    Average annual return over the trailing 5 years.

    Observed on: ETF, MUTUALFUND summaries.
    """

    morning_star_return_rating: float | None = None
    """
    Morningstar star rating for return, on Morningstar's rating scale.

    Only ever observed on ``VTSAX``.

    Observed on: MUTUALFUND summaries.
    """

    num_years_down: int | None = None
    """
    Number of calendar years with a negative total return.

    Only ever observed on ``VTSAX``.

    Observed on: MUTUALFUND summaries.
    """

    num_years_up: int | None = None
    """
    Number of calendar years with a positive total return.

    Only ever observed on ``VTSAX``.

    Observed on: MUTUALFUND summaries.
    """

    one_year_total_return: float
    """
    Total return over the trailing 1 year.

    Observed on: ETF, MUTUALFUND summaries.
    """

    three_year_total_return: float
    """
    Total return over the trailing 3 years.

    Observed on: ETF, MUTUALFUND summaries.
    """

    worst_three_yr_total_return: float | None = None
    """
    Worst trailing three-year annualized total return in the fund's history.

    Only ever observed on ``VTSAX``.

    Observed on: MUTUALFUND summaries.
    """

    ytd_return_pct: float
    """
    Year-to-date return.

    Observed on: ETF, MUTUALFUND summaries.
    """


class FundPerformanceOverviewCat(YahooModel):
    """The category-average sibling of :class:`FundPerformanceOverview`.

    Wire key ``performanceOverviewCat``; unlike its un-suffixed sibling,
    this variant never gains the MUTUALFUND-only fields even on ``VTSAX``
    in this corpus.
    """

    five_yr_avg_return_pct: float
    """
    Category-average return over the trailing 5 years.
    """

    one_year_total_return: float
    """
    Category-average return over the trailing 1 year.
    """

    three_year_total_return: float
    """
    Category-average return over the trailing 3 years.
    """

    ytd_return_pct: float
    """
    Category-average year-to-date return.
    """


class TrailingReturns(YahooModel):
    """The ``trailingReturns`` block of a :class:`FundPerformance`.

    ``trailingReturnsCat`` (:class:`TrailingReturnsCat`) shares every field
    except ``as_of_date``; ``trailingReturnsNav`` (:class:`TrailingReturnsNav`)
    additionally drops ``last_bull_mkt``/``last_bear_mkt``. See the module
    docstring.
    """

    as_of_date: datetime.date
    """
    Date these trailing returns were computed as of.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds
    (verified against every corpus value); pydantic converts it to a UTC
    calendar date.
    """

    five_year: float
    """
    Annualized total return over the trailing 5 years.
    """

    last_bear_mkt: float
    """
    Total return during the most recent bear market.
    """

    last_bull_mkt: float
    """
    Total return during the most recent bull market.
    """

    one_month: float
    """
    Total return over the trailing 1 month.
    """

    one_year: float
    """
    Total return over the trailing 1 year.
    """

    ten_year: float
    """
    Annualized total return over the trailing 10 years.
    """

    three_month: float
    """
    Total return over the trailing 3 months.
    """

    three_year: float
    """
    Annualized total return over the trailing 3 years.
    """

    ytd: float
    """
    Year-to-date return.
    """


class TrailingReturnsCat(YahooModel):
    """The ``trailingReturnsCat`` block of a :class:`FundPerformance`.

    Shares every field with :class:`TrailingReturns` except ``as_of_date``
    (the category benchmark has no single as-of date to report), verified
    as a consistent subset across all 4 corpus captures.
    """

    five_year: float
    """
    Category-average annualized total return over the trailing 5 years.
    """

    last_bear_mkt: float
    """
    Category-average total return during the most recent bear market.
    """

    last_bull_mkt: float
    """
    Category-average total return during the most recent bull market.
    """

    one_month: float
    """
    Category-average total return over the trailing 1 month.
    """

    one_year: float
    """
    Category-average total return over the trailing 1 year.
    """

    ten_year: float
    """
    Category-average annualized total return over the trailing 10 years.
    """

    three_month: float
    """
    Category-average total return over the trailing 3 months.
    """

    three_year: float
    """
    Category-average annualized total return over the trailing 3 years.
    """

    ytd: float
    """
    Category-average year-to-date return.
    """


class TrailingReturnsNav(YahooModel):
    """The ``trailingReturnsNav`` block of a :class:`FundPerformance`.

    Shares every field with :class:`TrailingReturns` except
    ``as_of_date``/``last_bull_mkt``/``last_bear_mkt``, verified as a
    consistent subset across all 4 corpus captures rather than a shape
    reuse; see the module docstring.
    """

    five_year: float
    """
    Annualized NAV-based total return over the trailing 5 years.
    """

    one_month: float
    """
    NAV-based total return over the trailing 1 month.
    """

    one_year: float
    """
    NAV-based total return over the trailing 1 year.
    """

    ten_year: float
    """
    Annualized NAV-based total return over the trailing 10 years.
    """

    three_month: float
    """
    NAV-based total return over the trailing 3 months.
    """

    three_year: float
    """
    Annualized NAV-based total return over the trailing 3 years.
    """

    ytd: float
    """
    NAV-based year-to-date return.
    """


class RiskStatisticsEntry(YahooModel):
    """One period's row in ``riskOverviewStatistics.riskStatistics``."""

    alpha: float
    """
    Jensen's alpha versus the fund's benchmark for ``year``.
    """

    beta: float
    """
    Beta versus the fund's benchmark for ``year``.
    """

    mean_annual_return: float
    """
    Mean annual return over ``year``.
    """

    r_squared: float
    """
    R-squared versus the fund's benchmark for ``year``.
    """

    sharpe_ratio: float
    """
    Sharpe ratio over ``year``.
    """

    std_dev: float
    """
    Standard deviation of returns over ``year``.
    """

    treynor_ratio: float
    """
    Treynor ratio over ``year``.
    """

    year: str
    """
    Trailing-period label for this row (observed values: ``"5y"``,
    ``"3y"``, ``"10y"``).
    """


class RiskStatisticsCatEntry(YahooModel):
    """One period's row in ``riskOverviewStatisticsCat.riskStatisticsCat``.

    Field-for-field identical to :class:`RiskStatisticsEntry` except
    ``std_dev``, which is present on ``VTSAX`` but absent on all three ETF
    captures' category-average rows; see the module docstring.
    """

    alpha: float
    """
    Category-average Jensen's alpha for ``year``.

    Observed on: ETF, MUTUALFUND summaries.
    """

    beta: float
    """
    Category-average beta for ``year``.

    Observed on: ETF, MUTUALFUND summaries.
    """

    mean_annual_return: float
    """
    Category-average mean annual return over ``year``.

    Observed on: ETF, MUTUALFUND summaries.
    """

    r_squared: float
    """
    Category-average R-squared for ``year``.

    Observed on: ETF, MUTUALFUND summaries.
    """

    sharpe_ratio: float
    """
    Category-average Sharpe ratio over ``year``.

    Observed on: ETF, MUTUALFUND summaries.
    """

    std_dev: float | None = None
    """
    Category-average standard deviation of returns over ``year``.

    Only ever observed on ``VTSAX``; absent on all three ETF captures.

    Observed on: MUTUALFUND summaries.
    """

    treynor_ratio: float
    """
    Category-average Treynor ratio over ``year``.

    Observed on: ETF, MUTUALFUND summaries.
    """

    year: str
    """
    Trailing-period label for this row (observed values: ``"5y"``,
    ``"3y"``, ``"10y"``).

    Observed on: ETF, MUTUALFUND summaries.
    """


class RiskOverviewStatistics(YahooModel):
    """The ``riskOverviewStatistics`` block of a :class:`FundPerformance`."""

    risk_rating: int | None = None
    """
    Morningstar-style overall risk rating.

    Only ever observed on ``VTSAX``; see the module docstring.

    Observed on: MUTUALFUND summaries.
    """

    risk_statistics: list[RiskStatisticsEntry]
    """
    Risk/return statistics by trailing period.

    Observed on: ETF, MUTUALFUND summaries.
    """


class RiskOverviewStatisticsCat(YahooModel):
    """The ``riskOverviewStatisticsCat`` block of a :class:`FundPerformance`."""

    risk_statistics_cat: list[RiskStatisticsCatEntry]
    """
    Category-average risk/return statistics by trailing period.
    """


class AnnualReturn(YahooModel):
    """One entry in an ``annualTotalReturns`` block's ``returns``/``returnsCat``."""

    annual_value: float | None = None
    """
    Total return for this calendar year.

    Absent (not merely null) for the current, not-yet-finished calendar
    year (the corpus's example: ``VTSAX``'s ``"2026"`` row).
    """

    year: str
    """
    Calendar year for this row, as a wire string (for example ``"2025"``).
    """


class AnnualTotalReturns(YahooModel):
    """The ``annualTotalReturns`` block of a :class:`FundPerformance`."""

    returns: list[AnnualReturn]
    """
    Fund annual total returns, most recent year first.
    """

    returns_cat: list[AnnualReturn]
    """
    Category-average annual total returns, most recent year first.
    """


class QuarterlyReturn(YahooModel):
    """One entry in the ``pastQuarterlyReturns`` block's ``returns`` list.

    Unlike ``fundProfile``'s ``projectionValues``/``bondRatings``-style
    genuinely dynamic bags, this row's key set is small and closed (only
    ``year``, ``q1``, ``q2``, ``q3``, ``q4`` ever observed across every row
    in the corpus), so it is modeled as four fixed optional fields rather
    than a ``dict[str, float]`` bag; see the module docstring.
    """

    q1: float | None = None
    """
    Return for the first calendar quarter of ``year``.
    """

    q2: float | None = None
    """
    Return for the second calendar quarter of ``year``.

    Absent (not merely null) on the current, not-yet-finished year (the
    corpus's example: ``VTSAX``'s ``"2026"`` row has only ``q1``).
    """

    q3: float | None = None
    """
    Return for the third calendar quarter of ``year``.

    Absent (not merely null) on the current, not-yet-finished year; see ``q2``.
    """

    q4: float | None = None
    """
    Return for the fourth calendar quarter of ``year``.

    Absent (not merely null) on the current, not-yet-finished year; see ``q2``.
    """

    year: str
    """
    Calendar year for this row, as a wire string (for example ``"2025"``).
    """


class PastQuarterlyReturns(YahooModel):
    """The ``pastQuarterlyReturns`` block of a :class:`FundPerformance`.

    ``returns`` is always empty on ETF captures in this corpus; Yahoo
    reports quarterly return history for mutual funds only.
    """

    returns: list[QuarterlyReturn]
    """
    Historical quarterly returns, most recent year first.

    Always an empty list on ETF captures; populated only on ``VTSAX``.
    """


class LoadAdjustedReturns(YahooModel):
    """The ``loadAdjustedReturns`` block of a :class:`FundPerformance`.

    Only ever observed on ``VTSAX``; see the module docstring for the
    single-capture caveat.
    """

    five_year: float
    """
    Load-adjusted annualized total return over the trailing 5 years.
    """

    one_year: float
    """
    Load-adjusted total return over the trailing 1 year.
    """

    ten_year: float
    """
    Load-adjusted annualized total return over the trailing 10 years.
    """

    three_year: float
    """
    Load-adjusted annualized total return over the trailing 3 years.
    """


class RankInCategory(YahooModel):
    """The ``rankInCategory`` block of a :class:`FundPerformance`.

    Only ever observed on ``VTSAX``; see the module docstring for the
    single-capture caveat.
    """

    five_year: int
    """
    Percentile rank within category over the trailing 5 years (lower is better).
    """

    one_month: int
    """
    Percentile rank within category over the trailing 1 month.
    """

    one_year: int
    """
    Percentile rank within category over the trailing 1 year.
    """

    three_month: int
    """
    Percentile rank within category over the trailing 3 months.
    """

    three_year: int
    """
    Percentile rank within category over the trailing 3 years.
    """

    ytd: int
    """
    Percentile rank within category, year-to-date.
    """


class FundPerformance(YahooModel):
    """The ``fundPerformance`` module: fund return/risk performance overview.

    Thinly evidenced (4 captures: 3 ETF, 1 MUTUALFUND); several fields are
    MUTUALFUND-only on the strength of the single ``VTSAX`` observation.
    See the module docstring.
    """

    annual_total_returns: AnnualTotalReturns
    """
    Historical annual total returns, fund and category.

    Observed on: ETF, MUTUALFUND summaries.
    """

    fund_category_name: str
    """
    Morningstar-style category classification (for example ``"Large
    Growth"``).

    Observed on: ETF, MUTUALFUND summaries.
    """

    load_adjusted_returns: LoadAdjustedReturns | None = None
    """
    Trailing returns adjusted for sales loads.

    Only ever observed on ``VTSAX``.

    Observed on: MUTUALFUND summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: ETF, MUTUALFUND summaries.
    """

    past_quarterly_returns: PastQuarterlyReturns
    """
    Historical quarterly returns.

    Observed on: ETF, MUTUALFUND summaries.
    """

    performance_overview: FundPerformanceOverview
    """
    Headline performance metrics for this fund.

    Observed on: ETF, MUTUALFUND summaries.
    """

    performance_overview_cat: FundPerformanceOverviewCat
    """
    Category-average headline performance metrics, for comparison.

    Observed on: ETF, MUTUALFUND summaries.
    """

    rank_in_category: RankInCategory | None = None
    """
    Percentile ranks within the fund's category by trailing period.

    Only ever observed on ``VTSAX``.

    Observed on: MUTUALFUND summaries.
    """

    risk_overview_statistics: RiskOverviewStatistics
    """
    Risk/return statistics for this fund by trailing period.

    Observed on: ETF, MUTUALFUND summaries.
    """

    risk_overview_statistics_cat: RiskOverviewStatisticsCat
    """
    Category-average risk/return statistics, for comparison.

    Observed on: ETF, MUTUALFUND summaries.
    """

    trailing_returns: TrailingReturns
    """
    Trailing total returns by period.

    Observed on: ETF, MUTUALFUND summaries.
    """

    trailing_returns_cat: TrailingReturnsCat
    """
    Category-average trailing total returns, for comparison.

    Observed on: ETF, MUTUALFUND summaries.
    """

    trailing_returns_nav: TrailingReturnsNav
    """
    NAV-based trailing total returns by period.

    Observed on: ETF, MUTUALFUND summaries.
    """


class Holding(YahooModel):
    """One entry in the ``topHoldings`` module's ``holdings`` list."""

    holding_name: str
    """
    Name of the held security (for example ``"NVIDIA Corp"``).
    """

    holding_percent: float
    """
    Percentage of the fund's assets allocated to this holding.
    """

    symbol: str
    """
    Ticker symbol of the held security.
    """


class TopHoldings(YahooModel):
    """The ``topHoldings`` module: fund composition and top holdings.

    Thinly evidenced (4 captures: 3 ETF, 1 MUTUALFUND);
    ``equity_holdings``/``bond_holdings`` diverge sharply in key set
    between the two quoteTypes. See the module docstring.
    """

    bond_holdings: dict[str, float]
    """
    Bond-portfolio characteristics, keyed by a dynamic metric name.

    A dynamic numeric bag rather than a fixed-field model (only
    ``durationCat`` has ever been observed, on ``VTSAX``; always an empty
    ``{}`` on ETF captures); see the module docstring.
    """

    bond_position: float
    """
    Fraction of fund assets allocated to bonds.
    """

    bond_ratings: list[dict[str, float]]
    """
    Bond credit-rating allocation, one single-key dict per rating grade
    (for example ``{"us_government": 0.0}``).

    A dynamic per-entry key rather than a fixed-field model; see the
    module docstring.
    """

    cash_position: float
    """
    Fraction of fund assets held in cash (can be slightly negative when
    the fund uses leverage).
    """

    convertible_position: float
    """
    Fraction of fund assets allocated to convertible securities.
    """

    equity_holdings: dict[str, float]
    """
    Equity-portfolio valuation ratios, keyed by a dynamic metric name.

    A dynamic numeric bag: ETF captures carry 4 keys
    (``priceToEarnings``/``priceToBook``/``priceToSales``/
    ``priceToCashflow``); the sole MUTUALFUND capture carries 12,
    including a ``Cat``-suffixed sibling for each and
    ``medianMarketCap``/``threeYearEarningsGrowth``; see the module
    docstring.
    """

    holdings: list[Holding]
    """
    Individual top holdings, largest first.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """

    other_position: float
    """
    Fraction of fund assets allocated to other, uncategorized instruments.
    """

    preferred_position: float
    """
    Fraction of fund assets allocated to preferred shares.
    """

    sector_weightings: list[dict[str, float]]
    """
    Sector allocation, one single-key dict per sector (for example
    ``{"technology": 0.5865}``).

    A dynamic per-entry key rather than a fixed-field model; see the
    module docstring.
    """

    stock_position: float
    """
    Fraction of fund assets allocated to equities.
    """
