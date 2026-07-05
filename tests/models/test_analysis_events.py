"""Round-trip tests for typed batch 3d-1 event models against real captures.

The corpus coverage gate (``tests/models/test_analysis_events_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes: calendar-events' module-keyed optionality,
quote-type's FUTURE/OPTION-only fields, and recommendation/stock-recommender
row shapes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yoghurt.models.analysis_events import (
    CalendarEventsResult,
    QuoteTypeResult,
    RecommendationsResult,
    StockRecommenderResult,
)
from yoghurt.models.enums import QuoteType

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
