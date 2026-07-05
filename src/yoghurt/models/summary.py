"""The typed ``quote-summary`` endpoint container.

:class:`QuoteSummary` is the whole-endpoint model: one optional field per
quote-summary module (41 total, batches c1 through c4 of the Part 3c plan),
field name the module name snake_cased, wire alias the exact module name —
``to_camel``/``to_snake`` round-trip cleanly for all 41 module names with no
explicit alias overrides needed. A module is ``None`` whenever it was not
requested (``Ticker.quote_summary(modules=...)``) or does not apply to the
requested symbol's quoteType; the corpus coverage gate
(``tests/models/test_summary_corpus.py``) proves every one of the 23 valid
all-modules corpus captures validates as a :class:`QuoteSummary` with
``collect_nested_extras`` completely empty — the whole-endpoint drift alarm,
since a module family gaining an unmodeled field anywhere in its tree would
fail here even if that family's own corpus gate (in its own test file)
somehow missed it.

Sparse-module warnings consolidated from the per-batch model modules:

- ``balanceSheetHistory``/``balanceSheetHistoryQuarterly`` carry only
  ``endDate``/``maxAge`` in the corpus this was typed against — Yahoo does
  not currently populate any balance-sheet line item on these modules. See
  :mod:`yoghurt.models.summary_statements`.
- ``cashflowStatementHistory``/``cashflowStatementHistoryQuarterly`` add
  exactly one further line item, ``netIncome``, atop the same
  ``endDate``/``maxAge`` pair — every other cashflow line item is likewise
  unpopulated in this corpus. See :mod:`yoghurt.models.summary_statements`.
- ``incomeStatementHistory``/``incomeStatementHistoryQuarterly`` rows carry
  fifteen line items that are present as a *key* on every row but never
  resolve to a real value (always an empty ``{}`` wrapper) in this corpus;
  only seven line items (``costOfRevenue``, ``ebit``, ``grossProfit``,
  ``incomeTaxExpense``, ``netIncome``, ``totalOperatingExpenses``,
  ``totalRevenue``) are genuinely populated. See
  :mod:`yoghurt.models.summary_statements`.
- ``sectorTrend``/``industryTrend`` send a ``null`` ``symbol`` and an empty
  ``estimates`` list on every capture in this corpus — Yahoo appears to
  never populate sector/industry growth trends here, unlike their sibling
  ``indexTrend`` (always populated). See
  :mod:`yoghurt.models.summary_trends`.
- ``majorDirectHolders.holders`` is an empty list on every capture that
  carries this module in this corpus — a corpus-wide always-empty
  placeholder. See :mod:`yoghurt.models.summary_holders`.
- ``fundProfile``/``fundPerformance``/``topHoldings`` (the fund-internals
  modules, ETF/MUTUALFUND-only) rest on only 4 corpus captures — the
  thinnest evidence base of any module family here; several MUTUALFUND-only
  fields are typed from a single observed capture (``VTSAX``). See
  :mod:`yoghurt.models.summary_funds`.
- ``summaryProfile``/``assetProfile``'s ``executiveTeam`` and
  ``assetProfile.companyOfficers``' sibling ``summaryProfile.companyOfficers``
  are likewise never observed populated. See
  :mod:`yoghurt.models.summary_identity`.
"""

from __future__ import annotations

from yoghurt.models._base import YahooModel

# Every model below is required in full (not just for type checking): each
# backs a QuoteSummary field's runtime annotation, which pydantic resolves
# and validates against at class-creation time.
from yoghurt.models.summary_earnings import (  # noqa: TC001
    EarningsCallTranscripts,
    EarningsHistory,
    EarningsModule,
    EarningsTrend,
)
from yoghurt.models.summary_financials import (  # noqa: TC001
    CalendarEvents,
    DefaultKeyStatistics,
    FinancialData,
    FinancialsTemplate,
)
from yoghurt.models.summary_funds import (  # noqa: TC001
    FundPerformance,
    FundProfile,
    TopHoldings,
)
from yoghurt.models.summary_holders import (  # noqa: TC001
    FundOwnership,
    InsiderHolders,
    InsiderTransactions,
    InstitutionOwnership,
    MajorDirectHolders,
    MajorHoldersBreakdown,
    NetSharePurchaseActivity,
)
from yoghurt.models.summary_identity import (  # noqa: TC001
    AssetProfile,
    CorporateActions,
    EquityPerformance,
    PageViews,
    Price,
    QuoteUnadjustedPerformanceOverview,
    SummaryDetail,
    SummaryProfile,
    SummaryQuoteType,
)
from yoghurt.models.summary_statements import (  # noqa: TC001
    BalanceSheetHistory,
    BalanceSheetHistoryQuarterly,
    CashflowStatementHistory,
    CashflowStatementHistoryQuarterly,
    IncomeStatementHistory,
    IncomeStatementHistoryQuarterly,
)
from yoghurt.models.summary_trends import (  # noqa: TC001
    RecommendationTrend,
    SecFilings,
    TrendEstimateGroup,
    UpgradeDowngradeHistory,
)


class QuoteSummary(YahooModel):
    """The full ``quote-summary`` endpoint response: one field per module.

    Every field is optional (``None`` when the module was not requested or
    does not apply to this quoteType); see the module docstring for the
    consolidated sparse-module warnings.
    """

    asset_profile: AssetProfile | None = None
    """
    Company profile plus governance-risk scores.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    balance_sheet_history: BalanceSheetHistory | None = None
    """
    Annual balance-sheet rows.

    Carries only ``end_date``/``max_age`` in the corpus this was typed
    against; see the module docstring.

    Observed on: EQUITY summaries.
    """

    balance_sheet_history_quarterly: BalanceSheetHistoryQuarterly | None = None
    """
    Quarterly balance-sheet rows.

    Carries only ``end_date``/``max_age`` in the corpus this was typed
    against; see the module docstring.

    Observed on: EQUITY summaries.
    """

    calendar_events: CalendarEvents | None = None
    """
    Upcoming earnings call and dividend calendar events.

    Observed on: EQUITY summaries.
    """

    cashflow_statement_history: CashflowStatementHistory | None = None
    """
    Annual cashflow-statement rows.

    Carries only ``end_date``/``max_age``/``net_income`` in the corpus this
    was typed against; see the module docstring.

    Observed on: EQUITY summaries.
    """

    cashflow_statement_history_quarterly: CashflowStatementHistoryQuarterly | None = (
        None
    )
    """
    Quarterly cashflow-statement rows.

    Carries only ``end_date``/``max_age``/``net_income`` in the corpus this
    was typed against; see the module docstring.

    Observed on: EQUITY summaries.
    """

    corporate_actions: CorporateActions | None = None
    """
    Recent corporate actions (splits, dividends, and similar events).
    """

    default_key_statistics: DefaultKeyStatistics | None = None
    """
    Valuation ratios and share statistics.

    Observed on: EQUITY, ETF, MUTUALFUND summaries.
    """

    earnings: EarningsModule | None = None
    """
    EPS actuals/estimates using Yahoo's default methodology.

    Mirrors whichever of ``earnings_gaap``/``earnings_non_gaap`` matches
    ``default_methodology``; see
    :mod:`yoghurt.models.summary_earnings`.

    Observed on: EQUITY summaries.
    """

    earnings_call_transcripts: EarningsCallTranscripts | None = None
    """
    Earnings call transcript listings.

    Observed on: EQUITY summaries.
    """

    earnings_gaap: EarningsModule | None = None
    """
    EPS actuals/estimates using GAAP methodology.

    Observed on: EQUITY summaries.
    """

    earnings_history: EarningsHistory | None = None
    """
    Trailing quarterly EPS actuals vs. estimates.

    Observed on: EQUITY summaries.
    """

    earnings_non_gaap: EarningsModule | None = None
    """
    EPS actuals/estimates using non-GAAP methodology.

    Observed on: EQUITY summaries.
    """

    earnings_trend: EarningsTrend | None = None
    """
    Forward EPS/revenue estimates and trends.

    Observed on: EQUITY summaries.
    """

    equity_performance: EquityPerformance | None = None
    """
    Return performance vs. a benchmark.

    Despite the name, observed on every quoteType in the corpus this was
    typed against, not just EQUITY.
    """

    financial_data: FinancialData | None = None
    """
    Headline financial metrics and analyst targets.

    Observed on: EQUITY summaries.
    """

    financials_template: FinancialsTemplate | None = None
    """
    Which financial-statement template Yahoo uses for this company.

    Observed on: EQUITY summaries.
    """

    fund_ownership: FundOwnership | None = None
    """
    Mutual/index fund ownership positions.

    Observed on: EQUITY summaries.
    """

    fund_performance: FundPerformance | None = None
    """
    Fund return/risk performance overview.

    Thinly evidenced (4 corpus captures: 3 ETF, 1 MUTUALFUND); see
    :mod:`yoghurt.models.summary_funds`.

    Observed on: ETF, MUTUALFUND summaries.
    """

    fund_profile: FundProfile | None = None
    """
    Fund family, category, and fee overview.

    Thinly evidenced (4 corpus captures: 3 ETF, 1 MUTUALFUND); see
    :mod:`yoghurt.models.summary_funds`.

    Observed on: ETF, MUTUALFUND summaries.
    """

    income_statement_history: IncomeStatementHistory | None = None
    """
    Annual income-statement rows.

    Fifteen of its line items are universal-but-always-``{}`` in the
    corpus this was typed against; see the module docstring.

    Observed on: EQUITY summaries.
    """

    income_statement_history_quarterly: IncomeStatementHistoryQuarterly | None = None
    """
    Quarterly income-statement rows.

    Fifteen of its line items are universal-but-always-``{}`` in the
    corpus this was typed against; see the module docstring.

    Observed on: EQUITY summaries.
    """

    index_trend: TrendEstimateGroup | None = None
    """
    Forward growth-rate estimates for a benchmark index.

    Observed on: EQUITY summaries.
    """

    industry_trend: TrendEstimateGroup | None = None
    """
    Forward growth-rate estimates for an industry.

    Always empty (null ``symbol``, no ``estimates``) in the corpus this was
    typed against; see the module docstring.

    Observed on: EQUITY summaries.
    """

    insider_holders: InsiderHolders | None = None
    """
    Current insider share positions.

    Observed on: EQUITY summaries.
    """

    insider_transactions: InsiderTransactions | None = None
    """
    Recent insider trading activity.

    Observed on: EQUITY summaries.
    """

    institution_ownership: InstitutionOwnership | None = None
    """
    Institutional ownership positions.

    Observed on: EQUITY summaries.
    """

    major_direct_holders: MajorDirectHolders | None = None
    """
    Direct major shareholders.

    Always an empty ``holders`` list in the corpus this was typed against;
    see the module docstring.

    Observed on: EQUITY summaries.
    """

    major_holders_breakdown: MajorHoldersBreakdown | None = None
    """
    Aggregate ownership percentages (insiders/institutions).

    Observed on: EQUITY summaries.
    """

    net_share_purchase_activity: NetSharePurchaseActivity | None = None
    """
    Aggregate insider buy/sell activity.

    Observed on: EQUITY summaries.
    """

    page_views: PageViews | None = None
    """
    Yahoo Finance page-view trend indicators.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    price: Price | None = None
    """
    Compact real-time price snapshot.
    """

    quote_type: SummaryQuoteType | None = None
    """
    Identity fields for this quote-summary record.

    Distinct from :class:`~yoghurt.models.quote.Quote`; see
    :mod:`yoghurt.models.summary_identity`.
    """

    quote_unadjusted_performance_overview: QuoteUnadjustedPerformanceOverview | None = (
        None
    )
    """
    Unadjusted (dividend/split-naive) return performance vs. a benchmark.
    """

    recommendation_trend: RecommendationTrend | None = None
    """
    Analyst buy/hold/sell counts over time.

    Observed on: EQUITY summaries.
    """

    sec_filings: SecFilings | None = None
    """
    SEC filing listings with exhibit links.

    Observed on: EQUITY summaries.
    """

    sector_trend: TrendEstimateGroup | None = None
    """
    Forward growth-rate estimates for a sector.

    Always empty (null ``symbol``, no ``estimates``) in the corpus this was
    typed against; see the module docstring.

    Observed on: EQUITY summaries.
    """

    summary_detail: SummaryDetail | None = None
    """
    Wider price/valuation snapshot.
    """

    summary_profile: SummaryProfile | None = None
    """
    Company/fund description and contact details.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    top_holdings: TopHoldings | None = None
    """
    Fund composition and top holdings.

    Thinly evidenced (4 corpus captures: 3 ETF, 1 MUTUALFUND); see
    :mod:`yoghurt.models.summary_funds`.

    Observed on: ETF, MUTUALFUND summaries.
    """

    upgrade_downgrade_history: UpgradeDowngradeHistory | None = None
    """
    Analyst rating/price-target actions.

    Observed on: EQUITY summaries.
    """
