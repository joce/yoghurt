"""Round-trip tests for the typed Quote model against real corpus captures."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from yoghurt.models import MarketState, PriceAlertConfidence, QuoteType
from yoghurt.models.quote import Quote

_CORPUS_QUOTE_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote"
)

_AAPL_FORWARD_PE = 32.119114
_AAPL_TRAILING_PE = 37.319225
_AAPL_REGULAR_MARKET_PRICE = 308.63


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
    assert quote.options_type == "Call"
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
