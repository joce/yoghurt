"""Tests for the Yahoo quote enums, corpus-driven for coverage."""

from __future__ import annotations

import json
from pathlib import Path

from yoghurt.models import MarketState, OptionType, PriceAlertConfidence, QuoteType

_CORPUS_QUOTE_DIR = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "corpus" / "quote"
)


def _quote_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(_CORPUS_QUOTE_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.extend(payload.get("quoteResponse", {}).get("result", []))
    return records


def test_quote_type_is_str_enum() -> None:
    """QuoteType members compare equal to their raw Yahoo string."""

    assert QuoteType.EQUITY == "EQUITY"


def test_corpus_quote_type_values_all_construct() -> None:
    """Every quoteType value seen in the corpus maps to a QuoteType member."""

    records = _quote_records()
    assert records, "expected at least one quote corpus record"
    with_key = [r for r in records if "quoteType" in r]
    assert len(with_key) == len(records), "quoteType is not universal in corpus"
    for record in with_key:
        QuoteType(record["quoteType"])


def test_corpus_market_state_values_all_construct() -> None:
    """Every marketState value seen in the corpus maps to a MarketState member."""

    records = _quote_records()
    assert records, "expected at least one quote corpus record"
    with_key = [r for r in records if "marketState" in r]
    assert len(with_key) == len(records), "marketState is not universal in corpus"
    for record in with_key:
        MarketState(record["marketState"])


def test_corpus_price_alert_confidence_values_all_construct() -> None:
    """Every customPriceAlertConfidence value maps to a PriceAlertConfidence."""

    records = _quote_records()
    assert records, "expected at least one quote corpus record"
    key = "customPriceAlertConfidence"
    with_key = [r for r in records if key in r]
    assert len(with_key) == len(records), f"{key} is not universal in corpus"
    for record in with_key:
        PriceAlertConfidence(record[key])


def test_option_type_members() -> None:
    """OptionType has exactly CALL and PUT, matching Yahoo's option payloads."""

    assert {member.value for member in OptionType} == {"CALL", "PUT"}
