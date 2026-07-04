"""Round-trip tests for the typed Quote model against real corpus captures."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from yoghurt.models import MarketState, OptionsType, PriceAlertConfidence, QuoteType
from yoghurt.models.quote import Quote

_CORPUS_QUOTE_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote"
)

_AAPL_FORWARD_PE = 32.119114
_AAPL_TRAILING_PE = 37.319225
_AAPL_REGULAR_MARKET_PRICE = 308.63
_MAX_COMPACT_REPR_LENGTH = 150


def _load_record(filename: str, index: int = 0) -> dict[str, object]:
    payload = json.loads((_CORPUS_QUOTE_DIR / filename).read_text(encoding="utf-8"))
    results: list[dict[str, object]] = payload.get("quoteResponse", {}).get(
        "result", []
    )
    return results[index]


def test_quote_validates_aapl_record_with_representative_fields() -> None:
    """A real AAPL quote capture round-trips through typed attributes.

    Covers: an irregular-alias field (forward_pe, wire forwardPE), an enum
    (quote_type), a date field (dividend_date), a corpus-new field
    (industry), and a spread of universal/optional scalars.
    """

    record = _load_record("AAPL.json")
    quote = Quote.model_validate(record)

    assert quote.symbol == "AAPL"
    assert quote.quote_type is QuoteType.EQUITY
    assert quote.market_state is MarketState.CLOSED
    assert quote.custom_price_alert_confidence is PriceAlertConfidence.HIGH
    assert quote.forward_pe == pytest.approx(_AAPL_FORWARD_PE)
    assert quote.trailing_pe == pytest.approx(_AAPL_TRAILING_PE)
    assert quote.dividend_date == datetime.date(2026, 5, 14)
    assert quote.industry == "Consumer Electronics"
    assert quote.morningstar_industry == "Consumer Electronics"
    assert quote.regular_market_price == pytest.approx(_AAPL_REGULAR_MARKET_PRICE)
    assert quote.short_name == "Apple Inc."
    assert quote.currency == "USD"
    assert quote.stock_story_top_six_url == (
        "https://stockstory.org/high-quality/top-6-to-buy-this-week"
        "?partner=yahoo&utm_source=yahoo"
    )
    assert quote.model_extra in (None, {})


def test_quote_corporate_actions_default_record_is_empty_list() -> None:
    """AAPL_default.json carries an explicit (empty) corporateActions list."""

    record = _load_record("AAPL_default.json")
    quote = Quote.model_validate(record)

    assert quote.corporate_actions == []
    assert quote.model_extra in (None, {})


def test_quote_validates_option_contract_record() -> None:
    """The OPTION corpus record exercises options_type and expire_date."""

    record = _load_record("OPTION_CONTRACT.json")
    quote = Quote.model_validate(record)

    assert quote.quote_type is QuoteType.OPTION
    assert quote.options_type is OptionsType.CALL
    assert quote.expire_date == datetime.date(2026, 7, 6)
    assert quote.underlying_symbol == "AAPL"
    assert quote.model_extra in (None, {})


def test_quote_validates_crypto_record() -> None:
    """A CRYPTOCURRENCY record exercises the crypto-supply fields."""

    record = _load_record("BTC-USD.json")
    quote = Quote.model_validate(record)

    assert quote.quote_type is QuoteType.CRYPTOCURRENCY
    assert quote.circulating_supply is not None
    assert isinstance(quote.circulating_supply, int)
    assert quote.model_extra in (None, {})


def test_datetime_conveniences_convert_epoch_to_aware_datetime() -> None:
    """Each epoch field converts to a tz-aware datetime anchored to the exchange.

    Computes the expected values independently with ``zoneinfo`` against
    the AAPL record's raw epoch fields, rather than trusting the
    implementation under test.
    """

    record = _load_record("AAPL.json")
    quote = Quote.model_validate(record)
    tz = ZoneInfo(quote.exchange_timezone_name)

    assert quote.earnings_timestamp is not None
    assert quote.earnings_datetime == datetime.datetime.fromtimestamp(
        quote.earnings_timestamp, tz
    )
    assert quote.earnings_timestamp_end is not None
    assert quote.earnings_datetime_end == datetime.datetime.fromtimestamp(
        quote.earnings_timestamp_end, tz
    )
    assert quote.earnings_timestamp_start is not None
    assert quote.earnings_datetime_start == datetime.datetime.fromtimestamp(
        quote.earnings_timestamp_start, tz
    )
    assert quote.first_trade_date_milliseconds is not None
    assert quote.first_trade_datetime == datetime.datetime.fromtimestamp(
        quote.first_trade_date_milliseconds // 1000, tz
    )
    assert quote.post_market_time is not None
    assert quote.post_market_datetime == datetime.datetime.fromtimestamp(
        quote.post_market_time, tz
    )
    assert quote.regular_market_datetime == datetime.datetime.fromtimestamp(
        quote.regular_market_time, tz
    )
    assert quote.regular_market_datetime.tzinfo is not None


def test_earnings_call_datetime_conveniences_match_quote_style_localization() -> None:
    """earnings_call_datetime_start/end mirror the other seven conveniences' pattern.

    Computes the expected values independently with ``zoneinfo`` against
    AAPL_default.json's raw epoch fields, rather than trusting the
    implementation under test.
    """

    record = _load_record("AAPL_default.json")
    quote = Quote.model_validate(record)
    tz = ZoneInfo(quote.exchange_timezone_name)

    assert quote.earnings_call_timestamp_start is not None
    assert quote.earnings_call_datetime_start is not None
    assert quote.earnings_call_datetime_start == datetime.datetime.fromtimestamp(
        quote.earnings_call_timestamp_start, tz
    )
    assert quote.earnings_call_datetime_start.tzinfo is not None
    assert quote.earnings_call_timestamp_end is not None
    assert quote.earnings_call_datetime_end is not None
    assert quote.earnings_call_datetime_end == datetime.datetime.fromtimestamp(
        quote.earnings_call_timestamp_end, tz
    )
    assert quote.earnings_call_datetime_end.tzinfo is not None

    assert quote.earnings_call_datetime_start is quote.earnings_call_datetime_start
    assert quote.earnings_call_datetime_end is quote.earnings_call_datetime_end


def test_pre_market_datetime_is_none_when_source_field_absent() -> None:
    """AAPL's record has no preMarketTime key; the convenience must propagate that."""

    record = _load_record("AAPL.json")
    quote = Quote.model_validate(record)

    assert "preMarketTime" not in record
    assert quote.pre_market_time is None
    assert quote.pre_market_datetime is None


def test_first_trade_datetime_is_none_when_source_field_absent() -> None:
    """OPTION records lack firstTradeDateMilliseconds.

    Unlike Doubloon's YQuote (which types this non-optional), our corpus
    shows the field absent on OPTION quotes, so the convenience must
    return None rather than raise.
    """

    record = _load_record("OPTION_CONTRACT.json")
    quote = Quote.model_validate(record)

    assert "firstTradeDateMilliseconds" not in record
    assert quote.first_trade_datetime is None


def test_datetime_conveniences_are_cached() -> None:
    """Repeated access returns the identical object, proving caching."""

    record = _load_record("AAPL.json")
    quote = Quote.model_validate(record)

    first_access = quote.regular_market_datetime
    second_access = quote.regular_market_datetime

    assert first_access is second_access


def test_model_dump_excludes_datetime_convenience_properties() -> None:
    """The convenience properties must never leak into the wire-shaped dump.

    They are plain ``cached_property``, not pydantic ``computed_field``,
    specifically so ``model_dump()`` stays wire-shaped.
    """

    record = _load_record("AAPL_default.json")
    quote = Quote.model_validate(record)

    # Access every property first so caching can't hide a leak.
    _ = (
        quote.earnings_call_datetime_end,
        quote.earnings_call_datetime_start,
        quote.earnings_datetime,
        quote.earnings_datetime_end,
        quote.earnings_datetime_start,
        quote.first_trade_datetime,
        quote.post_market_datetime,
        quote.pre_market_datetime,
        quote.regular_market_datetime,
    )

    dumped = quote.model_dump()

    assert "earningsDatetime" not in dumped
    assert "earnings_datetime" not in dumped
    assert "regularMarketDatetime" not in dumped
    assert "regular_market_datetime" not in dumped
    assert "firstTradeDatetime" not in dumped
    assert "first_trade_datetime" not in dumped
    assert "earningsCallDatetimeStart" not in dumped
    assert "earnings_call_datetime_start" not in dumped
    assert "earningsCallDatetimeEnd" not in dumped
    assert "earnings_call_datetime_end" not in dumped


def test_repr_is_compact_and_symbol_forward() -> None:
    """The custom __repr__ replaces pydantic's unusable 131-field default."""

    record = _load_record("AAPL.json")
    quote = Quote.model_validate(record)

    representation = repr(quote)

    assert representation == (
        "Quote(symbol='AAPL', "
        f"regular_market_price={quote.regular_market_price!r}, "
        "quote_type=<QuoteType.EQUITY: 'EQUITY'>)"
    )
    assert len(representation) < _MAX_COMPACT_REPR_LENGTH
