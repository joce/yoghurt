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
    quote_summary_module_kind,
    quote_summary_module_records,
)

_EXPECTED_FUND_PROFILE_RECORD_COUNT = 4


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


def test_quote_summary_price_stream_universal_keys_are_sane() -> None:
    """The price module's universal keys look like the always-there quote basics.

    Every quote-summary capture (across every quoteType) carries a price
    module, so symbol/currency/exchange/maxAge should be universal — this
    is the sanity check that the generic module-record stream and its
    quoteType-derived kind tagging both work end to end.
    """

    report = collect_presence(
        quote_summary_module_records("price"), kind_of=quote_summary_module_kind
    )
    for key in ("symbol", "currency", "exchange", "maxAge", "quoteType"):
        assert report.fields[key].universal, key


def test_quote_summary_fund_profile_stream_is_etf_and_mutualfund_only() -> None:
    """The fundProfile module's 4 captures are all ETF or MUTUALFUND, never EQUITY."""

    records = list(quote_summary_module_records("fundProfile"))
    assert len(records) == _EXPECTED_FUND_PROFILE_RECORD_COUNT
    kinds = {quote_summary_module_kind(record) for record in records}
    assert kinds == {"ETF", "MUTUALFUND"}


def test_quote_summary_stream_skips_invalid_symbol_capture() -> None:
    """The ZZZZXYZQ capture has no quoteSummary.result and yields nothing."""

    records = list(quote_summary_module_records("price"))
    assert all(quote_summary_module_kind(record) != "?" for record in records)


def test_quote_summary_module_kind_returns_placeholder_for_untagged_record() -> None:
    """A record that never went through the tagging wrapper reports '?'."""

    assert quote_summary_module_kind({"symbol": "AAPL"}) == "?"
