"""Round-trip tests for typed batch c4 fund models against real captures.

The corpus coverage gate (``tests/models/test_summary_funds_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes: the ETF-vs-MUTUALFUND shape divergence on
``fundProfile``/``fundPerformance``/``topHoldings``, the dynamic-bag fields,
and the not-yet-finished-year optionality on annual/quarterly returns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yoghurt.models.summary_funds import FundPerformance, FundProfile, TopHoldings

_CORPUS_QUOTE_SUMMARY_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote-summary"
)


def _load_module(filename: str, module: str) -> dict[str, Any]:
    payload = json.loads(
        (_CORPUS_QUOTE_SUMMARY_DIR / filename).read_text(encoding="utf-8")
    )
    result: dict[str, Any] = payload["quoteSummary"]["result"][0][module]
    return result


def test_fund_profile_etf_has_null_management_info() -> None:
    """QQQ's fundProfile has a populated legal_type and null manager fields."""

    profile = FundProfile.model_validate(_load_module("QQQ.json", "fundProfile"))

    assert profile.legal_type == "Exchange Traded Fund"
    assert profile.management_info.manager_name is None
    assert profile.management_info.manager_bio is None
    assert profile.init_investment is None
    assert profile.fees_expenses_investment.total_net_assets is not None
    assert profile.fees_expenses_investment.net_exp_ratio is None


def test_fund_profile_mutualfund_has_populated_management_info() -> None:
    """VTSAX's fundProfile has a null legal_type and populated manager fields."""

    profile = FundProfile.model_validate(_load_module("VTSAX.json", "fundProfile"))

    assert profile.legal_type is None
    assert profile.management_info.manager_bio is not None
    assert profile.management_info.startdate is not None
    assert profile.init_investment is not None
    assert profile.fees_expenses_investment.total_net_assets is None
    assert profile.fees_expenses_investment.net_exp_ratio is not None
    assert profile.brokerages  # populated only on the MUTUALFUND capture


def test_fund_performance_annual_returns_omit_value_for_partial_year() -> None:
    """VTSAX's current, not-yet-finished year has no annual_value."""

    performance = FundPerformance.model_validate(
        _load_module("VTSAX.json", "fundPerformance")
    )

    current_year = next(
        row for row in performance.annual_total_returns.returns if row.year == "2026"
    )
    assert current_year.annual_value is None

    finished_year = next(
        row for row in performance.annual_total_returns.returns if row.year == "2025"
    )
    assert finished_year.annual_value is not None


def test_fund_performance_past_quarterly_returns_partial_year_has_only_q1() -> None:
    """VTSAX's current-year quarterly-return row has only q1 populated."""

    performance = FundPerformance.model_validate(
        _load_module("VTSAX.json", "fundPerformance")
    )

    current_year_row = next(
        row for row in performance.past_quarterly_returns.returns if row.year == "2026"
    )
    assert current_year_row.q1 is not None
    assert current_year_row.q2 is None
    assert current_year_row.q3 is None
    assert current_year_row.q4 is None

    finished_year_row = next(
        row for row in performance.past_quarterly_returns.returns if row.year == "2025"
    )
    assert finished_year_row.q1 is not None
    assert finished_year_row.q4 is not None


def test_fund_performance_etf_has_empty_past_quarterly_returns() -> None:
    """QQQ's pastQuarterlyReturns.returns is empty (ETFs have none in this corpus)."""

    performance = FundPerformance.model_validate(
        _load_module("QQQ.json", "fundPerformance")
    )
    assert performance.past_quarterly_returns.returns == []
    assert performance.load_adjusted_returns is None
    assert performance.rank_in_category is None


_VTSAX_RISK_RATING = 4


def test_fund_performance_mutualfund_has_load_adjusted_and_rank_fields() -> None:
    """VTSAX populates loadAdjustedReturns/rankInCategory (MUTUALFUND-only)."""

    performance = FundPerformance.model_validate(
        _load_module("VTSAX.json", "fundPerformance")
    )
    assert performance.load_adjusted_returns is not None
    assert performance.rank_in_category is not None
    assert performance.risk_overview_statistics.risk_rating == _VTSAX_RISK_RATING


def test_top_holdings_dynamic_bags_carry_whatever_keys_the_capture_sends() -> None:
    """equityHoldings/bondHoldings/sectorWeightings are dynamic-keyed bags."""

    etf_holdings = TopHoldings.model_validate(_load_module("QQQ.json", "topHoldings"))
    fund_holdings = TopHoldings.model_validate(
        _load_module("VTSAX.json", "topHoldings")
    )

    assert set(etf_holdings.equity_holdings) == {
        "priceToEarnings",
        "priceToBook",
        "priceToSales",
        "priceToCashflow",
    }
    assert "medianMarketCap" in fund_holdings.equity_holdings
    assert etf_holdings.bond_holdings == {}
    assert fund_holdings.bond_holdings == {"durationCat": 4.6}
    assert all(len(entry) == 1 for entry in etf_holdings.sector_weightings)
    assert etf_holdings.holdings[0].symbol == "NVDA"
