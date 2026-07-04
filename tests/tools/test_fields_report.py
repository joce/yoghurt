"""Tests for the corpus field applicability report tool."""

from __future__ import annotations

from tools.fields_report import (
    CORPUS_DIR,
    chart_and_spark_meta_records,
    chart_meta_records,
    collect_field_presence,
    collect_presence,
    contract_kind,
    option_chain_records,
    option_contract_records,
)


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


def test_chart_meta_currency_is_universal() -> None:
    """Every valid chart capture's meta carries a currency."""

    report = collect_presence(
        chart_meta_records(),
        kind_of=lambda record: str(record.get("instrumentType", "")),
    )
    assert report.fields["currency"].universal


def test_chart_meta_previous_close_is_not_universal() -> None:
    """The previousClose field only shows up on some chart-meta captures."""

    report = collect_presence(
        chart_meta_records(),
        kind_of=lambda record: str(record.get("instrumentType", "")),
    )
    assert "previousClose" in report.fields
    assert not report.fields["previousClose"].universal


def test_combined_chart_and_spark_meta_currency_is_universal() -> None:
    """The combined chart+spark meta stream still shows currency as universal."""

    report = collect_presence(
        chart_and_spark_meta_records(),
        kind_of=lambda record: str(record.get("instrumentType", "")),
    )
    assert report.fields["currency"].universal


def test_option_contract_volume_is_not_universal() -> None:
    """Not every option contract in the corpus carries a volume figure."""

    report = collect_presence(option_contract_records(), kind_of=contract_kind)
    assert "volume" in report.fields
    assert not report.fields["volume"].universal
    assert 0 < report.fields["volume"].count < report.fields["volume"].total


def test_option_contract_strike_is_universal() -> None:
    """Every option contract in the corpus carries a strike price."""

    report = collect_presence(option_contract_records(), kind_of=contract_kind)
    assert report.fields["strike"].universal


def test_option_chain_records_report_symbol_as_universal() -> None:
    """Every options capture's chain-level record carries underlyingSymbol."""

    report = collect_presence(option_chain_records(), kind_of=lambda _record: "chain")
    assert report.fields["underlyingSymbol"].universal
