"""Tests for the Yahoo quote enums, corpus-driven for coverage."""

from __future__ import annotations

from yoghurt.models import MarketState, OptionsType, PriceAlertConfidence, QuoteType


def _records_with_key(
    records: list[dict[str, object]], key: str
) -> list[dict[str, object]]:
    """Filter to records carrying ``key``, asserting the key is universal."""

    with_key = [r for r in records if key in r]
    message = (
        f"{key} present on {len(with_key)}/{len(records)} records, expected universal"
    )
    assert len(with_key) == len(records), message
    return with_key


def test_quote_type_is_str_enum() -> None:
    """QuoteType members compare equal to their raw Yahoo string."""

    assert QuoteType.EQUITY == "EQUITY"


def test_corpus_quote_type_values_all_construct(
    quote_corpus_records: list[dict[str, object]],
) -> None:
    """Every quoteType value seen in the corpus maps to a QuoteType member."""

    assert quote_corpus_records, "expected at least one quote corpus record"
    for record in _records_with_key(quote_corpus_records, "quoteType"):
        QuoteType(record["quoteType"])


def test_corpus_market_state_values_all_construct(
    quote_corpus_records: list[dict[str, object]],
) -> None:
    """Every marketState value seen in the corpus maps to a MarketState member."""

    assert quote_corpus_records, "expected at least one quote corpus record"
    for record in _records_with_key(quote_corpus_records, "marketState"):
        MarketState(record["marketState"])


def test_corpus_price_alert_confidence_values_all_construct(
    quote_corpus_records: list[dict[str, object]],
) -> None:
    """Every customPriceAlertConfidence value maps to a PriceAlertConfidence."""

    assert quote_corpus_records, "expected at least one quote corpus record"
    key = "customPriceAlertConfidence"
    for record in _records_with_key(quote_corpus_records, key):
        PriceAlertConfidence(record[key])


def test_options_type_members_carry_wire_casing() -> None:
    """OptionsType has exactly CALL and PUT with Yahoo's title-cased values."""

    assert {member.value for member in OptionsType} == {"Call", "Put"}


def test_corpus_options_type_values_all_construct(
    quote_corpus_records: list[dict[str, object]],
) -> None:
    """Every optionsType value seen in the corpus maps to an OptionsType member.

    The key is not universal (OPTION quotes only), so this filters rather
    than using the universal-key helper.
    """

    with_key = [r for r in quote_corpus_records if "optionsType" in r]
    assert with_key, "expected at least one record carrying optionsType"
    for record in with_key:
        OptionsType(record["optionsType"])
