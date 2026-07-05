"""Round-trip tests for typed batch 3d-1 event models against real captures.

The corpus coverage gate (``tests/models/test_analysis_events_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes: calendar-events' module-keyed optionality
(including the windowed earnings/ipoEvents/secReports captures added
2026-07-05), quote-type's FUTURE/OPTION-only fields, and recommendation/
stock-recommender row shapes.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import pytest

from yoghurt.models.analysis_events import (
    CalendarEventsResult,
    QuoteTypeResult,
    RecommendationsResult,
    StockRecommenderResult,
)
from yoghurt.models.enums import QuoteType

_IVF_EPS_ACTUAL = -3.36
_IVF_EPS_ESTIMATE = -10.0
_MSFT_SEC_REPORTS_DAY_COUNT = 2
_AAPL_SEC_REPORTS_DAY_COUNT = 3

_CORPUS_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "corpus"


def _load(relative_path: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        (_CORPUS_ROOT / relative_path).read_text(encoding="utf-8")
    )
    return payload


def test_calendar_events_default_request_only_populates_earnings() -> None:
    """The no-``--modules`` request populates only earnings (empty list)."""

    payload = _load("calendar-events/AAPL.json")
    result = CalendarEventsResult.model_validate(payload["finance"]["result"])

    assert result.earnings == []
    assert result.economic_events is None
    assert result.ipo_events is None
    assert result.sec_reports is None


def test_calendar_events_economic_events_module_populates_only_that_key() -> None:
    """``--modules economicEvents`` populates economic_events, not earnings."""

    payload = _load("calendar-events/AAPL_economicEvents.json")
    result = CalendarEventsResult.model_validate(payload["finance"]["result"])

    assert result.earnings is None
    assert result.economic_events is not None
    day = result.economic_events[0]
    assert day.timezone == "America/New_York"
    assert day.count == len(day.records)
    first_event = day.records[0]
    assert first_event.economic_events is True
    assert first_event.revised_from is None


def test_calendar_events_economic_event_revised_from_is_optional() -> None:
    """Only some economic-event rows carry revised_from."""

    payload = _load("calendar-events/AAPL_economicEvents.json")
    result = CalendarEventsResult.model_validate(payload["finance"]["result"])
    assert result.economic_events is not None

    all_records = [record for day in result.economic_events for record in day.records]
    revised = [record for record in all_records if record.revised_from is not None]
    assert revised
    assert len(revised) < len(all_records)


def test_calendar_events_economic_event_actual_is_optional() -> None:
    """A not-yet-released event validates without ``actual``.

    Live-observed 2026-07-05: pending releases (June trade figures) omit
    ``actual`` until publication; every committed corpus row carries it,
    so the pin removes the key from a real capture's row.
    """

    payload = _load("calendar-events/AAPL_economicEvents.json")
    first_day = payload["finance"]["result"]["economicEvents"][0]
    del first_day["records"][0]["actual"]

    result = CalendarEventsResult.model_validate(payload["finance"]["result"])
    assert result.economic_events is not None
    assert result.economic_events[0].records[0].actual is None


def test_calendar_events_earnings_populates_with_explicit_date_window() -> None:
    """A --start-date/--end-date window covering a real report day populates.

    Live-found 2026-07-05: the default (window-less) request is always
    empty; IVF/HAWK/EBF/POWW all reported 2026-06-22.
    """

    payload = _load("calendar-events/IVF_earnings.json")
    result = CalendarEventsResult.model_validate(payload["finance"]["result"])

    assert result.earnings is not None
    day = result.earnings[0]
    assert day.timestamp_string == "2026-06-22"
    assert day.count == len(day.records)
    row = day.records[0]
    assert row.ticker == "IVF"
    assert row.earnings is True
    assert row.eps_actual == pytest.approx(_IVF_EPS_ACTUAL)
    assert row.eps_estimate == pytest.approx(_IVF_EPS_ESTIMATE)


def test_calendar_events_ipo_events_populates_with_explicit_date_window() -> None:
    """A --start-date/--end-date window covering a real pricing day populates.

    Live-found 2026-07-05: COPR/GSRVR/IQMXW/MIACU/VCRE/SECZ all priced
    2026-07-02, spanning common stock, rights, warrants, units, and ADSs.
    """

    payload = _load("calendar-events/GSRVR_ipoEvents.json")
    result = CalendarEventsResult.model_validate(payload["finance"]["result"])

    assert result.ipo_events is not None
    row = result.ipo_events[0].records[0]
    assert row.ticker == "GSRVR"
    assert row.ipo_events is True
    assert row.currency_name == "USD"
    assert row.deal_type == "Expected"


def test_calendar_events_ipo_events_currency_name_can_be_empty_string() -> None:
    """currency_name is a required key but sometimes an empty string.

    COPR (NYSE American common-stock pricing) carries currencyName: "".
    """

    payload = _load("calendar-events/COPR_ipoEvents.json")
    result = CalendarEventsResult.model_validate(payload["finance"]["result"])

    assert result.ipo_events is not None
    assert not result.ipo_events[0].records[0].currency_name


def test_calendar_events_sec_reports_populates_with_explicit_date_window() -> None:
    """A --start-date/--end-date window covering a real filing day populates.

    Live-found 2026-07-05: resolves the competing split-vs-filings
    hypothesis in favor of filings — MSFT's 10-Q/8-K same-day bucket.
    """

    payload = _load("calendar-events/MSFT_secReports_filed.json")
    result = CalendarEventsResult.model_validate(payload["finance"]["result"])

    assert result.sec_reports is not None
    day = result.sec_reports[0]
    assert day.count == len(day.records) == _MSFT_SEC_REPORTS_DAY_COUNT
    types = {row.type for row in day.records}
    assert types == {"10-Q", "8-K"}


def test_calendar_events_sec_reports_multi_day_bucket_and_exhibits() -> None:
    """AAPL's window spans 3 day-buckets; each filing carries exhibits."""

    payload = _load("calendar-events/AAPL_secReports_filed.json")
    result = CalendarEventsResult.model_validate(payload["finance"]["result"])

    assert result.sec_reports is not None
    assert len(result.sec_reports) == _AAPL_SEC_REPORTS_DAY_COUNT
    quarterly_day = next(
        day for day in result.sec_reports if day.records[0].type == "10-Q"
    )
    quarterly_filing = quarterly_day.records[0]
    assert quarterly_filing.category == "Periodic Financial Reports"
    assert quarterly_filing.filing_date == datetime.date(2026, 5, 1)
    assert any(exhibit.type == "EX-31.1" for exhibit in quarterly_filing.exhibits)


def test_quote_type_future_has_underlying_and_head_symbol() -> None:
    """FUTURE records carry underlying_symbol/underlying_exchange_symbol/head_symbol."""

    payload = _load("quote-type/CL_F.json")
    result = QuoteTypeResult.model_validate(payload["quoteType"]["result"][0])

    assert result.quote_type is QuoteType.FUTURE
    assert result.underlying_symbol == "CLQ26.NYM"
    assert result.underlying_exchange_symbol == "CLQ26.NYM"
    assert result.head_symbol == "CL=F"
    assert result.quartr_id is None


def test_quote_type_option_has_underlying_symbol_but_no_head_symbol() -> None:
    """OPTION records carry underlying_symbol but not head_symbol."""

    payload = _load("quote-type/OPTION_CONTRACT.json")
    result = QuoteTypeResult.model_validate(payload["quoteType"]["result"][0])

    assert result.quote_type is QuoteType.OPTION
    assert result.underlying_symbol == "AAPL"
    assert result.head_symbol is None
    assert result.underlying_exchange_symbol is None


def test_quote_type_equity_has_quartr_id_and_no_future_fields() -> None:
    """EQUITY records carry quartr_id but never the FUTURE-only fields."""

    payload = _load("quote-type/AAPL.json")
    result = QuoteTypeResult.model_validate(payload["quoteType"]["result"][0])

    assert result.quote_type is QuoteType.EQUITY
    assert result.quartr_id == "4742"
    assert result.underlying_symbol is None
    assert result.head_symbol is None
    assert result.gmt_off_set_milliseconds == "-14400000"


def test_recommendations_rows_are_sorted_by_relatedness() -> None:
    """recommended_symbols rows come back most-related first."""

    payload = _load("recommendations-by-symbol/AAPL.json")
    result = RecommendationsResult.model_validate(payload["finance"]["result"][0])

    scores = [row.score for row in result.recommended_symbols]
    assert scores == sorted(scores, reverse=True)
    assert result.recommended_symbols[0].symbol == "AMZN"


def test_stock_recommender_fields_carry_related_tickers() -> None:
    """The bare payload's fields block carries the related-tickers list."""

    payload = _load("stock-recommender/AAPL.json")
    result = StockRecommenderResult.model_validate(payload)

    assert result.path_id == "/document/v1/entity/entity/docid/ticker:AAPL"
    assert result.fields.entity_type == "ticker"
    assert "SONY" in result.fields.related_tickers
