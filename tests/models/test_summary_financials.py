"""Round-trip tests for typed batch c2 financial-snapshot models against real captures.

The corpus coverage gate (``tests/models/test_summary_financials_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes: the required-but-nullable fund fields on
``defaultKeyStatistics``, tier-1 epoch-to-date conversions, and the
tier-3 session-anchored ``calendarEvents.earnings`` timestamps.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from yoghurt.models.summary_financials import (
    CalendarEvents,
    DefaultKeyStatistics,
    FinancialData,
    FinancialsTemplate,
)

_CORPUS_QUOTE_SUMMARY_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote-summary"
)


def _load_module(filename: str, module: str) -> dict[str, Any]:
    payload = json.loads(
        (_CORPUS_QUOTE_SUMMARY_DIR / filename).read_text(encoding="utf-8")
    )
    result: dict[str, Any] = payload["quoteSummary"]["result"][0][module]
    return result


def test_financial_data_validates_bare_scalars_from_real_capture() -> None:
    """The financialData headline metrics are bare scalars, no Raw* wrappers."""

    financial_data = FinancialData.model_validate(
        _load_module("AAPL.json", "financialData")
    )

    assert financial_data.recommendation_key == "buy"
    assert isinstance(financial_data.total_cash, float)
    assert financial_data.model_extra in (None, {})


def test_default_key_statistics_fund_fields_are_required_but_null_for_equity() -> None:
    """category/fundFamily/legalType are present-but-null on an EQUITY capture."""

    stats = DefaultKeyStatistics.model_validate(
        _load_module("AAPL.json", "defaultKeyStatistics")
    )

    assert stats.category is None
    assert stats.fund_family is None
    assert stats.legal_type is None
    assert stats.latest_share_class is None
    assert stats.lead_investor is None
    assert stats.last_split_factor == "4:1"


def test_default_key_statistics_fund_fields_resolve_for_etf() -> None:
    """category/fundFamily/legalType resolve to real values on an ETF capture."""

    stats = DefaultKeyStatistics.model_validate(
        _load_module("QQQ.json", "defaultKeyStatistics")
    )

    assert stats.category == "Large Growth"
    assert stats.fund_family == "Invesco"
    assert stats.legal_type == "Exchange Traded Fund"
    assert stats.latest_share_class is None
    assert stats.lead_investor is None


def test_default_key_statistics_epoch_fields_are_calendar_dates() -> None:
    """The defaultKeyStatistics epoch fields are tier-1 UTC calendar dates."""

    stats = DefaultKeyStatistics.model_validate(
        _load_module("AAPL.json", "defaultKeyStatistics")
    )

    assert stats.last_fiscal_year_end == datetime.date(2025, 9, 27)
    assert isinstance(stats.last_fiscal_year_end, datetime.date)
    assert not isinstance(stats.last_fiscal_year_end, datetime.datetime)


def test_calendar_events_ex_dividend_date_is_calendar_date() -> None:
    """calendarEvents.exDividendDate is a tier-1 UTC calendar date."""

    calendar_events = CalendarEvents.model_validate(
        _load_module("AAPL.json", "calendarEvents")
    )

    assert calendar_events.ex_dividend_date == datetime.date(2026, 5, 11)
    assert isinstance(calendar_events.ex_dividend_date, datetime.date)
    assert not isinstance(calendar_events.ex_dividend_date, datetime.datetime)


def test_calendar_events_earnings_dates_are_session_anchored_datetimes() -> None:
    """calendarEvents.earnings.earningsDate/.earningsCallDate are tier-3 datetimes.

    Unlike the module's own exDividendDate/dividendDate, these are
    session-anchored (never midnight-aligned) and carry a time component.
    """

    calendar_events = CalendarEvents.model_validate(
        _load_module("AAPL.json", "calendarEvents")
    )

    earnings_date = calendar_events.earnings.earnings_date[0]
    assert isinstance(earnings_date, datetime.datetime)
    assert earnings_date.tzinfo is not None
    assert earnings_date.time() != datetime.time(0, 0, 0)


def test_financials_template_code_round_trips() -> None:
    """financialsTemplate.code is a plain string, not a closed vocabulary."""

    template = FinancialsTemplate.model_validate(
        _load_module("AAPL.json", "financialsTemplate")
    )

    assert template.code == "N"
    assert isinstance(template.code, str)
