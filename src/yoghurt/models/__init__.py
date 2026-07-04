"""Typed Yahoo response models and quote enums.

Every model here is a frozen pydantic model built on :class:`YahooModel`:
snake_case fields, camelCase wire aliases, unknown fields preserved rather
than dropped. See :mod:`yoghurt.models._base` for the full template. The
package also carries the quote enums (:class:`QuoteType`,
:class:`MarketState`, :class:`OptionsType`, :class:`PriceAlertConfidence`),
whose members are corpus-verified except where an enum's docstring notes a
value known only from prior use.
"""

from __future__ import annotations

from yoghurt.models._base import YahooModel, validate_model
from yoghurt.models.chart import (
    ChartDividend,
    ChartEvents,
    ChartMeta,
    ChartSplit,
    CurrentTradingPeriod,
    TradingPeriod,
)
from yoghurt.models.enums import (
    MarketState,
    OptionsType,
    PriceAlertConfidence,
    QuoteType,
)
from yoghurt.models.options import OptionChain, OptionContract, OptionExpiration
from yoghurt.models.quote import CorporateAction, Quote
from yoghurt.models.summary_identity import (
    AssetProfile,
    Benchmark,
    CompanyOfficer,
    CorporateActionMeta,
    CorporateActions,
    EquityPerformance,
    ExecutiveTeamMember,
    PageViews,
    PerformanceOverview,
    Price,
    QuoteUnadjustedPerformanceOverview,
    SummaryCorporateAction,
    SummaryDetail,
    SummaryProfile,
    SummaryQuoteType,
)

__all__ = [
    "AssetProfile",
    "Benchmark",
    "ChartDividend",
    "ChartEvents",
    "ChartMeta",
    "ChartSplit",
    "CompanyOfficer",
    "CorporateAction",
    "CorporateActionMeta",
    "CorporateActions",
    "CurrentTradingPeriod",
    "EquityPerformance",
    "ExecutiveTeamMember",
    "MarketState",
    "OptionChain",
    "OptionContract",
    "OptionExpiration",
    "OptionsType",
    "PageViews",
    "PerformanceOverview",
    "Price",
    "PriceAlertConfidence",
    "Quote",
    "QuoteType",
    "QuoteUnadjustedPerformanceOverview",
    "SummaryCorporateAction",
    "SummaryDetail",
    "SummaryProfile",
    "SummaryQuoteType",
    "TradingPeriod",
    "YahooModel",
    "validate_model",
]
