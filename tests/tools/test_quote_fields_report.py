"""Tests for the quote field applicability report tool."""

from __future__ import annotations

from tools.quote_fields_report import CORPUS_DIR, collect_field_presence


def test_symbol_is_universal() -> None:
    """The symbol field appears on every quote record across the corpus."""

    report = collect_field_presence(CORPUS_DIR)
    assert report.fields["symbol"].universal
    assert report.fields["symbol"].count == report.fields["symbol"].total


def test_circulating_supply_is_crypto_only() -> None:
    """The circulatingSupply field only appears on CRYPTOCURRENCY records."""

    report = collect_field_presence(CORPUS_DIR)
    field = report.fields["circulatingSupply"]
    assert field.quote_types == ("CRYPTOCURRENCY",)
    assert not field.universal


def test_forward_pe_exact_spelling_present() -> None:
    """The forwardPE key keeps Yahoo's exact irregular spelling as-is."""

    report = collect_field_presence(CORPUS_DIR)
    assert "forwardPE" in report.fields
    assert report.fields["forwardPE"].count > 0


def test_universal_set_is_non_empty_and_contains_symbol() -> None:
    """At least one field, including symbol, is present on every record."""

    report = collect_field_presence(CORPUS_DIR)
    universal = {key for key, field in report.fields.items() if field.universal}
    assert universal
    assert "symbol" in universal


def test_circulating_supply_universal_within_cryptocurrency() -> None:
    """The circulatingSupply field is on every CRYPTOCURRENCY record."""

    report = collect_field_presence(CORPUS_DIR)
    assert report.universal_for("circulatingSupply", "CRYPTOCURRENCY")


def test_display_name_not_universal_within_equity() -> None:
    """The displayName field is on some, but not all, EQUITY records."""

    report = collect_field_presence(CORPUS_DIR)
    field = report.fields["displayName"]
    assert "EQUITY" in field.quote_types
    assert report.universal_for("displayName", "EQUITY") is False


def test_records_per_type_totals_are_consistent() -> None:
    """Per-type record totals sum to the overall total on every field."""

    report = collect_field_presence(CORPUS_DIR)
    assert report.records_per_type
    total = sum(report.records_per_type.values())
    assert total == report.fields["symbol"].total


def test_universal_for_unknown_inputs_is_false() -> None:
    """Unknown keys or quoteTypes never count as universal."""

    report = collect_field_presence(CORPUS_DIR)
    assert report.universal_for("symbol", "NOT_A_QUOTE_TYPE") is False
    assert report.universal_for("notARealYahooField", "EQUITY") is False
