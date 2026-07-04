"""Tests for the quote field applicability report tool."""

from __future__ import annotations

from tools.quote_fields_report import CORPUS_DIR, collect_field_presence


def test_symbol_is_universal() -> None:
    """The symbol field appears on every quote record across the corpus."""

    presence = collect_field_presence(CORPUS_DIR)
    assert presence["symbol"].universal
    assert presence["symbol"].count == presence["symbol"].total


def test_circulating_supply_is_crypto_only() -> None:
    """The circulatingSupply field only appears on CRYPTOCURRENCY records."""

    presence = collect_field_presence(CORPUS_DIR)
    field = presence["circulatingSupply"]
    assert field.quote_types == ("CRYPTOCURRENCY",)
    assert not field.universal


def test_forward_pe_exact_spelling_present() -> None:
    """The forwardPE key keeps Yahoo's exact irregular spelling as-is."""

    presence = collect_field_presence(CORPUS_DIR)
    assert "forwardPE" in presence
    assert presence["forwardPE"].count > 0


def test_universal_set_is_non_empty_and_contains_symbol() -> None:
    """At least one field, including symbol, is present on every record."""

    presence = collect_field_presence(CORPUS_DIR)
    universal = {key for key, field in presence.items() if field.universal}
    assert universal
    assert "symbol" in universal
