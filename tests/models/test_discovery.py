"""Focused behavior tests for search and lookup models."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from yoghurt.models.discovery import LookupQuoteType, LookupResult, SearchResult

_CORPUS = Path(__file__).parent.parent / "fixtures" / "corpus"


def _load(relative_path: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        (_CORPUS / relative_path).read_text(encoding="utf-8")
    )
    return payload


def test_search_distinguishes_finance_and_non_finance_quote_rows() -> None:
    """Cultural/private rows validate without inventing ticker symbols."""

    result = SearchResult.model_validate(_load("search/AAPL_content.json"))
    assert any(quote.symbol == "AAPL" for quote in result.quotes)
    assert any(
        not quote.is_yahoo_finance and quote.symbol is None for quote in result.quotes
    )


def test_search_name_change_date_is_a_calendar_date() -> None:
    """Instrument rename dates are typed as dates, not opaque strings."""

    result = SearchResult.model_validate(_load("search/Appel_fuzzy.json"))
    renamed = next(quote for quote in result.quotes if quote.prev_name is not None)
    assert isinstance(renamed.name_change_date, datetime.date)


def test_search_publication_times_are_aware_datetimes() -> None:
    """News seconds and report milliseconds both normalize to aware datetimes."""

    default = SearchResult.model_validate(_load("search/default.json"))
    content = SearchResult.model_validate(_load("search/AAPL_content.json"))
    values = [
        default.news[0].provider_publish_time,
        content.research_reports[0].report_date,
    ]
    assert all(value.tzinfo is not None for value in values)


def test_search_news_accepts_live_observed_missing_related_tickers() -> None:
    """French-region news may omit relatedTickers."""

    payload = _load("search/default.json")
    del payload["news"][0]["relatedTickers"]

    result = SearchResult.model_validate(payload)

    assert result.news[0].related_tickers is None


def test_lookup_unwraps_formatted_prices_and_types_quote_type() -> None:
    """Formatted wrappers expose raw floats and the lowercase lookup enum."""

    payload = _load("lookup/formatted.json")["finance"]["result"][0]
    result = LookupResult.model_validate(payload)
    assert isinstance(result.documents[0].regular_market_price, float)
    assert result.documents[0].quote_type is LookupQuoteType.EQUITY


def test_lookup_no_match_is_an_empty_typed_page() -> None:
    """An unmatched query returns empty documents and zero totals."""

    payload = _load("lookup/no_match.json")["finance"]["result"][0]
    result = LookupResult.model_validate(payload)
    assert result.documents == []
    assert result.total == 0
    assert result.lookup_totals.all == 0


def test_lookup_accepts_live_observed_missing_rank() -> None:
    """French-region lookup documents may omit rank."""

    payload = _load("lookup/formatted.json")["finance"]["result"][0]
    del payload["documents"][0]["rank"]

    result = LookupResult.model_validate(payload)

    assert result.documents[0].rank is None
