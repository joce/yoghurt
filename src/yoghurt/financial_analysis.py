"""Analysis-ready financial statement, analyst, and ownership tables."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

import polars as pl

from yoghurt.commands import TIMESERIES_TYPE_REFERENCES
from yoghurt.frames import Frame, Timeseries

if TYPE_CHECKING:
    from yoghurt.models import FundOwnership, InstitutionOwnership, QuoteSummary

_VALUATION_METRICS: Final[frozenset[str]] = frozenset(
    {
        "EnterpriseValue",
        "EnterprisesValueEBITDARatio",
        "EnterprisesValueRevenueRatio",
        "ForwardPeRatio",
        "MarketCap",
        "PbRatio",
        "PeRatio",
        "PegRatio",
        "PsRatio",
    }
)
_INCOME_METRICS: Final[frozenset[str]] = frozenset(
    {
        "BasicAverageShares",
        "BasicEPS",
        "CostOfRevenue",
        "DilutedAverageShares",
        "DilutedEPS",
        "EBITDA",
        "GrossProfit",
        "ImpairmentOfCapitalAssets",
        "InterestExpense",
        "NetIncome",
        "NetIncomeContinuousOperations",
        "NormalizedEBITDA",
        "OperatingExpense",
        "OperatingIncome",
        "OtherIncomeExpense",
        "OtherSpecialCharges",
        "PretaxIncome",
        "ResearchAndDevelopment",
        "RestructuringAndMergernAcquisition",
        "SellingAndMarketingExpense",
        "SellingGeneralAndAdministration",
        "SpecialIncomeCharges",
        "TaxProvision",
        "TotalRevenue",
        "WriteOff",
    }
)
_BALANCE_SHEET_METRICS: Final[frozenset[str]] = frozenset(
    {
        "AccountsPayable",
        "AccountsReceivable",
        "CapitalLeaseObligations",
        "CashCashEquivalentsAndShortTermInvestments",
        "CurrentAssets",
        "CurrentLiabilities",
        "Goodwill",
        "GoodwillAndOtherIntangibleAssets",
        "Inventory",
        "InvestedCapital",
        "LongTermDebt",
        "NetDebt",
        "NetPPE",
        "StockholdersEquity",
        "TangibleBookValue",
        "TotalAssets",
        "TotalDebt",
        "TotalLiabilitiesNetMinorityInterest",
        "TotalNonCurrentAssets",
        "TotalNonCurrentLiabilitiesNetMinorityInterest",
        "WorkingCapital",
    }
)
_CASH_FLOW_METRICS: Final[frozenset[str]] = frozenset(
    {
        "BeginningCashPosition",
        "CapitalExpenditure",
        "CashDividendsPaid",
        "CashFlowFromContinuingFinancingActivities",
        "ChangeInAccountPayable",
        "ChangeInCashSupplementalAsReported",
        "ChangeInInventory",
        "ChangeInWorkingCapital",
        "ChangesInAccountReceivables",
        "CommonStockIssuance",
        "DeferredIncomeTax",
        "DepreciationAndAmortization",
        "EndCashPosition",
        "FreeCashFlow",
        "InvestingCashFlow",
        "NetIncome",
        "NetOtherFinancingCharges",
        "NetOtherInvestingChanges",
        "OperatingCashFlow",
        "OtherNonCashItems",
        "PurchaseOfBusiness",
        "PurchaseOfInvestment",
        "RepaymentOfDebt",
        "RepurchaseOfCapitalStock",
        "SaleOfInvestment",
        "StockBasedCompensation",
    }
)


def _matches(type_name: str, metrics: frozenset[str]) -> bool:
    return any(type_name.endswith(metric) for metric in metrics)


def _types_for_metrics(metrics: frozenset[str]) -> tuple[str, ...]:
    return tuple(
        reference.name
        for reference in TIMESERIES_TYPE_REFERENCES
        if _matches(reference.name, metrics)
    )


FINANCIAL_ANALYSIS_TIMESERIES_TYPES: Final[tuple[str, ...]] = _types_for_metrics(
    _VALUATION_METRICS | _INCOME_METRICS | _BALANCE_SHEET_METRICS | _CASH_FLOW_METRICS
)

# quoteType is a universally applicable anchor: Yahoo rejects a quote-summary
# request containing only inapplicable equity modules instead of returning them empty.
FINANCIAL_ANALYSIS_QUOTE_SUMMARY_MODULES: Final[tuple[str, ...]] = (
    "quoteType",
    "earningsHistory",
    "earningsTrend",
    "financialData",
    "indexTrend",
    "industryTrend",
    "sectorTrend",
    "majorHoldersBreakdown",
    "institutionOwnership",
    "fundOwnership",
    "insiderHolders",
    "insiderTransactions",
    "netSharePurchaseActivity",
)

_EARNINGS_ESTIMATES_SCHEMA: Final[dict[str, Any]] = {
    "period": pl.Utf8,
    "end_date": pl.Date,
    "currency": pl.Utf8,
    "avg": pl.Float64,
    "low": pl.Float64,
    "high": pl.Float64,
    "year_ago_eps": pl.Float64,
    "growth": pl.Float64,
    "number_of_analysts": pl.Int64,
}
_REVENUE_ESTIMATES_SCHEMA: Final[dict[str, Any]] = {
    "period": pl.Utf8,
    "end_date": pl.Date,
    "currency": pl.Utf8,
    "avg": pl.Float64,
    "low": pl.Float64,
    "high": pl.Float64,
    "year_ago_revenue": pl.Float64,
    "growth": pl.Float64,
    "number_of_analysts": pl.Int64,
}
_EARNINGS_HISTORY_SCHEMA: Final[dict[str, Any]] = {
    "period": pl.Utf8,
    "quarter": pl.Date,
    "currency": pl.Utf8,
    "eps_estimate": pl.Float64,
    "eps_actual": pl.Float64,
    "eps_difference": pl.Float64,
    "surprise_percent": pl.Float64,
}
_EPS_TRENDS_SCHEMA: Final[dict[str, Any]] = {
    "period": pl.Utf8,
    "end_date": pl.Date,
    "currency": pl.Utf8,
    "current": pl.Float64,
    "seven_days_ago": pl.Float64,
    "thirty_days_ago": pl.Float64,
    "sixty_days_ago": pl.Float64,
    "ninety_days_ago": pl.Float64,
}
_EPS_REVISIONS_SCHEMA: Final[dict[str, Any]] = {
    "period": pl.Utf8,
    "end_date": pl.Date,
    "currency": pl.Utf8,
    "up_last_7_days": pl.Int64,
    "up_last_30_days": pl.Int64,
    "down_last_7_days": pl.Int64,
    "down_last_30_days": pl.Int64,
    "down_last_90_days": pl.Int64,
}
_ANALYST_PRICE_TARGETS_SCHEMA: Final[dict[str, Any]] = {
    "currency": pl.Utf8,
    "current_price": pl.Float64,
    "target_low_price": pl.Float64,
    "target_mean_price": pl.Float64,
    "target_median_price": pl.Float64,
    "target_high_price": pl.Float64,
    "number_of_analyst_opinions": pl.Int64,
    "recommendation_key": pl.Utf8,
    "recommendation_mean": pl.Float64,
}
_GROWTH_COMPARISON_SCHEMA: Final[dict[str, Any]] = {
    "source": pl.Utf8,
    "symbol": pl.Utf8,
    "period": pl.Utf8,
    "end_date": pl.Date,
    "growth": pl.Float64,
}
_MAJOR_HOLDERS_BREAKDOWN_SCHEMA: Final[dict[str, Any]] = {
    "insiders_percent_held": pl.Float64,
    "institutions_count": pl.Int64,
    "institutions_float_percent_held": pl.Float64,
    "institutions_percent_held": pl.Float64,
}
_OWNERSHIP_SCHEMA: Final[dict[str, Any]] = {
    "organization": pl.Utf8,
    "report_date": pl.Date,
    "pct_held": pl.Float64,
    "pct_change": pl.Float64,
    "position": pl.Int64,
    "value": pl.Int64,
}
_INSIDER_ROSTER_SCHEMA: Final[dict[str, Any]] = {
    "name": pl.Utf8,
    "relation": pl.Utf8,
    "latest_transaction_date": pl.Date,
    "transaction_description": pl.Utf8,
    "position_direct": pl.Int64,
    "position_direct_date": pl.Date,
    "position_indirect": pl.Int64,
    "position_indirect_date": pl.Date,
    "position_summary": pl.Int64,
    "position_summary_date": pl.Date,
}
_INSIDER_TRANSACTIONS_SCHEMA: Final[dict[str, Any]] = {
    "filer_name": pl.Utf8,
    "filer_relation": pl.Utf8,
    "start_date": pl.Date,
    "ownership": pl.Utf8,
    "shares": pl.Int64,
    "value": pl.Int64,
    "transaction_text": pl.Utf8,
}
_INSIDER_PURCHASE_ACTIVITY_SCHEMA: Final[dict[str, Any]] = {
    "period": pl.Utf8,
    "buy_info_count": pl.Int64,
    "buy_info_shares": pl.Int64,
    "buy_percent_insider_shares": pl.Float64,
    "sell_info_count": pl.Int64,
    "sell_info_shares": pl.Int64,
    "sell_percent_insider_shares": pl.Float64,
    "net_info_count": pl.Int64,
    "net_info_shares": pl.Int64,
    "net_percent_insider_shares": pl.Float64,
    "total_insider_shares": pl.Int64,
    "net_inst_shares_buying": pl.Int64,
    "net_inst_buying_percent": pl.Float64,
}


@dataclass(frozen=True, slots=True)
class FinancialAnalysis:
    """Stable long-form tables for one symbol's financial analysis.

    Statement and valuation fields share the fundamentals schema: ``type``,
    ``as_of_date``, ``period_type``, ``currency_code``, and ``value``. Analyst
    and ownership fields use one row per natural Yahoo record and retain dates
    and currencies where their source modules provide them. Every field keeps
    its declared schema when the source module is absent or inapplicable.
    """

    income_statement: Frame
    balance_sheet: Frame
    cash_flow: Frame
    valuation_history: Frame
    earnings_estimates: Frame
    revenue_estimates: Frame
    earnings_history: Frame
    eps_trends: Frame
    eps_revisions: Frame
    analyst_price_targets: Frame
    growth_comparison: Frame
    major_holders_breakdown: Frame
    institutional_ownership: Frame
    fund_ownership: Frame
    insider_roster: Frame
    insider_transactions: Frame
    insider_purchase_activity: Frame


def _frame(
    records: list[dict[str, Any]], schema: dict[str, Any], timeseries: Timeseries
) -> Frame:
    return Frame(
        df=(
            pl.DataFrame(records, schema=schema)
            if records
            else pl.DataFrame(schema=schema)
        ),
        fetched_at=timeseries.fetched_at,
    )


def _timeseries_frame(timeseries: Timeseries, metrics: frozenset[str]) -> Frame:
    source = timeseries.fundamentals.to_polars()
    # Polars' Python 3.10 stub leaves DataFrame.filter partially Unknown.
    table = source.filter(  # pyright: ignore[reportUnknownMemberType]
        pl.col("type").is_in(_types_for_metrics(metrics))
    )
    return Frame(df=table, fetched_at=timeseries.fetched_at)


def build_financial_analysis(
    timeseries: Timeseries, summary: QuoteSummary
) -> FinancialAnalysis:
    """Build stable analysis tables from existing typed retrieval results.

    Returns:
        FinancialAnalysis: The analysis-ready table bundle.
    """

    trend = summary.earnings_trend.trend if summary.earnings_trend else []
    earnings_history = (
        summary.earnings_history.history if summary.earnings_history else []
    )
    earnings_estimates: list[dict[str, Any]] = [
        {
            "period": entry.period,
            "end_date": entry.end_date,
            "currency": entry.earnings_estimate.earnings_currency,
            "avg": entry.earnings_estimate.avg,
            "low": entry.earnings_estimate.low,
            "high": entry.earnings_estimate.high,
            "year_ago_eps": entry.earnings_estimate.year_ago_eps,
            "growth": entry.earnings_estimate.growth,
            "number_of_analysts": entry.earnings_estimate.number_of_analysts,
        }
        for entry in trend
        if any(
            value is not None
            for value in (
                entry.earnings_estimate.avg,
                entry.earnings_estimate.low,
                entry.earnings_estimate.high,
                entry.earnings_estimate.year_ago_eps,
                entry.earnings_estimate.growth,
                entry.earnings_estimate.number_of_analysts,
            )
        )
    ]
    revenue_estimates: list[dict[str, Any]] = [
        {
            "period": entry.period,
            "end_date": entry.end_date,
            "currency": entry.revenue_estimate.revenue_currency,
            "avg": entry.revenue_estimate.avg,
            "low": entry.revenue_estimate.low,
            "high": entry.revenue_estimate.high,
            "year_ago_revenue": entry.revenue_estimate.year_ago_revenue,
            "growth": entry.revenue_estimate.growth,
            "number_of_analysts": entry.revenue_estimate.number_of_analysts,
        }
        for entry in trend
    ]
    history_rows: list[dict[str, Any]] = [
        {
            "period": entry.period,
            "quarter": entry.quarter,
            "currency": entry.currency,
            "eps_estimate": entry.eps_estimate,
            "eps_actual": entry.eps_actual,
            "eps_difference": entry.eps_difference,
            "surprise_percent": entry.surprise_percent,
        }
        for entry in earnings_history
    ]
    eps_trends: list[dict[str, Any]] = [
        {
            "period": entry.period,
            "end_date": entry.end_date,
            "currency": entry.eps_trend.eps_trend_currency,
            "current": entry.eps_trend.current,
            "seven_days_ago": entry.eps_trend.seven_days_ago,
            "thirty_days_ago": entry.eps_trend.thirty_days_ago,
            "sixty_days_ago": entry.eps_trend.sixty_days_ago,
            "ninety_days_ago": entry.eps_trend.ninety_days_ago,
        }
        for entry in trend
        if any(
            value is not None
            for value in (
                entry.eps_trend.current,
                entry.eps_trend.seven_days_ago,
                entry.eps_trend.thirty_days_ago,
                entry.eps_trend.sixty_days_ago,
                entry.eps_trend.ninety_days_ago,
            )
        )
    ]
    eps_revisions: list[dict[str, Any]] = [
        {
            "period": entry.period,
            "end_date": entry.end_date,
            "currency": entry.eps_revisions.eps_revisions_currency,
            "up_last_7_days": entry.eps_revisions.up_last_7_days,
            "up_last_30_days": entry.eps_revisions.up_last_30_days,
            "down_last_7_days": entry.eps_revisions.down_last_7_days,
            "down_last_30_days": entry.eps_revisions.down_last_30_days,
            "down_last_90_days": entry.eps_revisions.down_last_90_days,
        }
        for entry in trend
        if any(
            value is not None
            for value in (
                entry.eps_revisions.up_last_7_days,
                entry.eps_revisions.up_last_30_days,
                entry.eps_revisions.down_last_7_days,
                entry.eps_revisions.down_last_30_days,
                entry.eps_revisions.down_last_90_days,
            )
        )
    ]
    price_targets: list[dict[str, Any]] = []
    if summary.financial_data is not None:
        data = summary.financial_data
        if (
            data.recommendation_key != "none"
            or (data.number_of_analyst_opinions or 0) > 0
            or any(
                value is not None
                for value in (
                    data.target_low_price,
                    data.target_mean_price,
                    data.target_median_price,
                    data.target_high_price,
                    data.recommendation_mean,
                )
            )
        ):
            price_targets.append(
                {
                    "currency": data.financial_currency,
                    "current_price": data.current_price,
                    "target_low_price": data.target_low_price,
                    "target_mean_price": data.target_mean_price,
                    "target_median_price": data.target_median_price,
                    "target_high_price": data.target_high_price,
                    "number_of_analyst_opinions": data.number_of_analyst_opinions,
                    "recommendation_key": data.recommendation_key,
                    "recommendation_mean": data.recommendation_mean,
                }
            )
    growth_comparison: list[dict[str, Any]] = [
        {
            "source": "stock",
            "symbol": None,
            "period": entry.period,
            "end_date": entry.end_date,
            "growth": entry.growth,
        }
        for entry in trend
    ]
    for source, group in (
        ("industry", summary.industry_trend),
        ("sector", summary.sector_trend),
        ("index", summary.index_trend),
    ):
        if group is not None:
            growth_comparison.extend(
                {
                    "source": source,
                    "symbol": group.symbol,
                    "period": estimate.period,
                    "end_date": None,
                    "growth": estimate.growth,
                }
                for estimate in group.estimates
            )
    major_holders: list[dict[str, Any]] = []
    if summary.major_holders_breakdown is not None:
        data = summary.major_holders_breakdown
        major_holders.append(
            {
                "insiders_percent_held": data.insiders_percent_held,
                "institutions_count": data.institutions_count,
                "institutions_float_percent_held": data.institutions_float_percent_held,
                "institutions_percent_held": data.institutions_percent_held,
            }
        )

    def ownership_rows(
        module: FundOwnership | InstitutionOwnership | None,
    ) -> list[dict[str, Any]]:
        if module is None:
            return []
        return [
            {
                "organization": entry.organization,
                "report_date": entry.report_date,
                "pct_held": entry.pct_held,
                "pct_change": entry.pct_change,
                "position": entry.position,
                "value": entry.value,
            }
            for entry in module.ownership_list
        ]

    insider_roster: list[dict[str, Any]] = [
        {
            "name": entry.name,
            "relation": entry.relation,
            "latest_transaction_date": entry.latest_trans_date,
            "transaction_description": entry.transaction_description,
            "position_direct": entry.position_direct,
            "position_direct_date": entry.position_direct_date,
            "position_indirect": entry.position_indirect,
            "position_indirect_date": entry.position_indirect_date,
            "position_summary": entry.position_summary,
            "position_summary_date": entry.position_summary_date,
        }
        for entry in (
            summary.insider_holders.holders if summary.insider_holders else []
        )
    ]
    insider_transactions: list[dict[str, Any]] = [
        {
            "filer_name": entry.filer_name,
            "filer_relation": entry.filer_relation,
            "start_date": entry.start_date,
            "ownership": entry.ownership,
            "shares": entry.shares,
            "value": entry.value,
            "transaction_text": entry.transaction_text,
        }
        for entry in (
            summary.insider_transactions.transactions
            if summary.insider_transactions
            else []
        )
    ]
    insider_purchase_activity: list[dict[str, Any]] = []
    if summary.net_share_purchase_activity is not None:
        data = summary.net_share_purchase_activity
        insider_purchase_activity.append(
            {name: getattr(data, name) for name in _INSIDER_PURCHASE_ACTIVITY_SCHEMA}
        )
    return FinancialAnalysis(
        income_statement=_timeseries_frame(timeseries, _INCOME_METRICS),
        balance_sheet=_timeseries_frame(timeseries, _BALANCE_SHEET_METRICS),
        cash_flow=_timeseries_frame(
            timeseries,
            _CASH_FLOW_METRICS - {"NetIncome"} | {"annualNetIncome"},
        ),
        valuation_history=_timeseries_frame(timeseries, _VALUATION_METRICS),
        earnings_estimates=_frame(
            earnings_estimates, _EARNINGS_ESTIMATES_SCHEMA, timeseries
        ),
        revenue_estimates=_frame(
            revenue_estimates, _REVENUE_ESTIMATES_SCHEMA, timeseries
        ),
        earnings_history=_frame(history_rows, _EARNINGS_HISTORY_SCHEMA, timeseries),
        eps_trends=_frame(eps_trends, _EPS_TRENDS_SCHEMA, timeseries),
        eps_revisions=_frame(eps_revisions, _EPS_REVISIONS_SCHEMA, timeseries),
        analyst_price_targets=_frame(
            price_targets, _ANALYST_PRICE_TARGETS_SCHEMA, timeseries
        ),
        growth_comparison=_frame(
            growth_comparison, _GROWTH_COMPARISON_SCHEMA, timeseries
        ),
        major_holders_breakdown=_frame(
            major_holders, _MAJOR_HOLDERS_BREAKDOWN_SCHEMA, timeseries
        ),
        institutional_ownership=_frame(
            ownership_rows(summary.institution_ownership),
            _OWNERSHIP_SCHEMA,
            timeseries,
        ),
        fund_ownership=_frame(
            ownership_rows(summary.fund_ownership), _OWNERSHIP_SCHEMA, timeseries
        ),
        insider_roster=_frame(insider_roster, _INSIDER_ROSTER_SCHEMA, timeseries),
        insider_transactions=_frame(
            insider_transactions, _INSIDER_TRANSACTIONS_SCHEMA, timeseries
        ),
        insider_purchase_activity=_frame(
            insider_purchase_activity,
            _INSIDER_PURCHASE_ACTIVITY_SCHEMA,
            timeseries,
        ),
    )
