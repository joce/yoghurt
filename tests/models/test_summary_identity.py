"""Round-trip tests for typed batch c1 quote-summary models against real captures.

The corpus coverage gate (``tests/models/test_summary_identity_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes for a handful of models per the batch c1
dispatch: RawFmt unwrapping in ``CompanyOfficer``, the ``SummaryQuoteType``/
``Price`` symbol-swap divergence for FUTURE summaries, the sole populated
``corporateActions`` example, and epoch-to-date conversions.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from yoghurt.models.summary_identity import (
    AssetProfile,
    CorporateActions,
    PageViews,
    Price,
    SummaryDetail,
    SummaryQuoteType,
)

_CORPUS_QUOTE_SUMMARY_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote-summary"
)

_AAPL_OFFICER_TOTAL_PAY = 16759518
_AAPL_OFFICER_AGE = 64
_RY_TO_DIVIDEND_AMOUNT = "1.76"
_RY_TO_DATE_EPOCH_MS = 1785124800000


def _load_module(filename: str, module: str) -> dict[str, Any]:
    payload = json.loads(
        (_CORPUS_QUOTE_SUMMARY_DIR / filename).read_text(encoding="utf-8")
    )
    result: dict[str, Any] = payload["quoteSummary"]["result"][0][module]
    return result


def test_company_officer_unwraps_raw_fmt_wrapper_from_real_capture() -> None:
    """AAPL's assetProfile officer pay fields unwrap {raw, fmt, longFmt} to raw."""

    asset_profile = AssetProfile.model_validate(
        _load_module("AAPL.json", "assetProfile")
    )
    cook = asset_profile.company_officers[0]

    assert cook.name == "Mr. Timothy D. Cook"
    assert cook.title == "CEO & Director"
    assert cook.age == _AAPL_OFFICER_AGE
    assert cook.total_pay == _AAPL_OFFICER_TOTAL_PAY
    assert isinstance(cook.total_pay, int)
    assert cook.exercised_value == 0
    assert cook.unexercised_value == 0
    assert asset_profile.model_extra in (None, {})


def test_summary_quote_type_and_price_symbols_are_swapped_for_future() -> None:
    """CL=F's quoteType.symbol is the contract; price.symbol is the request.

    This is the documented divergence that keeps SummaryQuoteType distinct
    from Quote: quoteType and price disagree about which field holds the
    requested vs. resolved symbol for FUTURE summaries.
    """

    quote_type = SummaryQuoteType.model_validate(_load_module("CL_F.json", "quoteType"))
    price = Price.model_validate(_load_module("CL_F.json", "price"))

    assert quote_type.symbol == "CLQ26.NYM"
    assert quote_type.underlying_symbol == "CL=F"
    assert price.symbol == "CL=F"
    assert price.underlying_symbol == "CLQ26.NYM"


def test_summary_quote_type_first_trade_datetime_localizes_via_timezone() -> None:
    """SummaryQuoteType.first_trade_datetime localizes via time_zone_full_name."""

    quote_type = SummaryQuoteType.model_validate(_load_module("AAPL.json", "quoteType"))

    assert quote_type.first_trade_date_epoch_utc is not None
    first_trade = quote_type.first_trade_datetime
    assert first_trade is not None
    assert first_trade.tzinfo is not None
    assert first_trade == datetime.datetime.fromtimestamp(
        quote_type.first_trade_date_epoch_utc,
        tz=first_trade.tzinfo,
    )


def test_corporate_actions_populated_example_validates_ry_to() -> None:
    """RY.TO's corporateActions is the corpus's sole populated example."""

    corporate_actions = CorporateActions.model_validate(
        _load_module("RY.TO.json", "corporateActions")
    )

    assert len(corporate_actions.corporate_actions) == 1
    action = corporate_actions.corporate_actions[0]
    assert action.header == "Dividend"
    assert action.meta.event_type == "DIVIDEND"
    assert action.meta.amount == _RY_TO_DIVIDEND_AMOUNT
    assert isinstance(action.meta.amount, str)
    assert action.meta.date_epoch_ms == _RY_TO_DATE_EPOCH_MS
    assert action.meta.date == datetime.date(2026, 7, 27)


def test_corporate_actions_empty_for_aapl() -> None:
    """Every other corpus capture (for example AAPL) has an empty action list."""

    corporate_actions = CorporateActions.model_validate(
        _load_module("AAPL.json", "corporateActions")
    )

    assert corporate_actions.corporate_actions == []


def test_summary_detail_ex_dividend_date_is_calendar_date() -> None:
    """summaryDetail.exDividendDate is a bare UTC calendar date, not a datetime."""

    summary_detail = SummaryDetail.model_validate(
        _load_module("AAPL.json", "summaryDetail")
    )

    assert isinstance(summary_detail.ex_dividend_date, datetime.date)
    assert not isinstance(summary_detail.ex_dividend_date, datetime.datetime)


def test_summary_detail_yield_field_uses_wire_alias() -> None:
    """summaryDetail.yield (a Python keyword) is exposed as yield_."""

    summary_detail = SummaryDetail.model_validate(
        _load_module("QQQ.json", "summaryDetail")
    )

    assert summary_detail.yield_ is not None
    assert isinstance(summary_detail.yield_, float)


def test_page_views_trends_validate_from_real_capture() -> None:
    """PageViews trend fields round-trip as plain strings."""

    page_views = PageViews.model_validate(_load_module("AAPL.json", "pageViews"))

    trend_values = {"UP", "DOWN"}
    assert page_views.short_term_trend in trend_values
    assert page_views.mid_term_trend in trend_values
    assert page_views.long_term_trend in trend_values
