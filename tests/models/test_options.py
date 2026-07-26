"""Round-trip tests for the typed OptionChain models against real corpus captures."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import cast

import pytest

from yoghurt.models.options import OptionChain
from yoghurt.models.quote import Quote

_CORPUS_OPTIONS_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "options"
)

_AAPL_CALL_STRIKE = 240.0
_AAPL_CALL_ASK = 70.2
_AAPL_CALL_LAST_TRADE_DATE_EPOCH = 1782492175
_AAPL_CALL_LAST_TRADE_DATE = datetime.datetime.fromtimestamp(
    _AAPL_CALL_LAST_TRADE_DATE_EPOCH, tz=datetime.timezone.utc
)
_AAPL_OTM_STRIKE = 310.0


def _load_chain(filename: str) -> dict[str, object]:
    payload = json.loads((_CORPUS_OPTIONS_DIR / filename).read_text(encoding="utf-8"))
    result: dict[str, object] = payload["optionChain"]["result"][0]
    return result


def test_option_chain_validates_aapl_record() -> None:
    """A real AAPL options capture round-trips through typed attributes."""

    record = _load_chain("AAPL.json")
    chain = OptionChain.model_validate(record)

    assert chain.underlying_symbol == "AAPL"
    assert chain.has_mini_options is False
    assert isinstance(chain.expiration_dates, list)
    assert all(isinstance(date, datetime.date) for date in chain.expiration_dates)
    assert not any(
        isinstance(date, datetime.datetime) for date in chain.expiration_dates
    )
    assert isinstance(chain.strikes, list)
    assert all(isinstance(strike, float) for strike in chain.strikes)
    assert chain.model_extra in (None, {})


def test_option_chain_embeds_typed_quote() -> None:
    """The embedded quote validates as Quote, the first cross-model reuse."""

    record = _load_chain("AAPL.json")
    chain = OptionChain.model_validate(record)

    assert isinstance(chain.quote, Quote)
    assert chain.quote.symbol == "AAPL"
    assert chain.quote.model_extra in (None, {})


def test_option_chain_single_expiration_has_typed_calls_and_puts() -> None:
    """The chain's one expiration entry carries typed call/put contracts."""

    record = _load_chain("AAPL.json")
    chain = OptionChain.model_validate(record)

    assert len(chain.options) == 1
    expiration = chain.options[0]
    assert expiration.has_mini_options is False
    assert len(expiration.calls) > 0
    assert len(expiration.puts) > 0

    call = expiration.calls[0]
    assert call.strike == pytest.approx(_AAPL_CALL_STRIKE)
    assert call.ask == pytest.approx(_AAPL_CALL_ASK)
    assert call.contract_size == "REGULAR"
    assert call.contract_symbol == "AAPL260706C00240000"
    assert call.currency == "USD"
    assert call.in_the_money is True
    assert call.last_trade_date == _AAPL_CALL_LAST_TRADE_DATE
    assert call.last_trade_date.tzinfo is not None
    assert isinstance(call.volume, int)
    assert call.model_extra in (None, {})


def test_option_contract_expiration_equals_utc_date_of_raw_epoch() -> None:
    """OptionContract.expiration is the UTC calendar date of the raw wire epoch."""

    record = _load_chain("AAPL.json")
    raw_call = record["options"][0]["calls"][0]  # type: ignore[index]
    raw_epoch = cast("int", raw_call["expiration"])
    expected = datetime.datetime.fromtimestamp(
        raw_epoch, tz=datetime.timezone.utc
    ).date()

    chain = OptionChain.model_validate(record)
    call = chain.options[0].calls[0]

    assert call.expiration == expected
    assert isinstance(call.expiration, datetime.date)
    assert not isinstance(call.expiration, datetime.datetime)


def test_option_expiration_date_equals_utc_date_of_raw_epoch() -> None:
    """OptionExpiration.expiration_date is the UTC calendar date of the raw epoch."""

    record = _load_chain("AAPL.json")
    raw_epoch = cast(
        "int",
        record["options"][0]["expirationDate"],  # type: ignore[index]
    )
    expected = datetime.datetime.fromtimestamp(
        raw_epoch, tz=datetime.timezone.utc
    ).date()

    chain = OptionChain.model_validate(record)

    assert chain.options[0].expiration_date == expected
    assert isinstance(chain.options[0].expiration_date, datetime.date)
    assert not isinstance(chain.options[0].expiration_date, datetime.datetime)


def test_option_chain_expiration_dates_equal_utc_dates_of_raw_epochs() -> None:
    """OptionChain.expiration_dates matches the UTC calendar dates of raw epochs."""

    record = _load_chain("AAPL.json")
    raw_epochs: list[int] = record["expirationDates"]  # type: ignore[assignment]
    expected = [
        datetime.datetime.fromtimestamp(epoch, tz=datetime.timezone.utc).date()
        for epoch in raw_epochs
    ]

    chain = OptionChain.model_validate(record)

    assert chain.expiration_dates == expected


def test_option_contract_out_of_the_money_flag_varies() -> None:
    """A higher strike in the same chain is correctly flagged out of the money."""

    record = _load_chain("AAPL.json")
    chain = OptionChain.model_validate(record)
    calls = chain.options[0].calls

    otm_call = next(c for c in calls if c.strike == pytest.approx(_AAPL_OTM_STRIKE))
    assert otm_call.in_the_money is False


def test_option_contract_last_trade_date_is_aware_utc() -> None:
    """OptionContract.last_trade_date is an aware UTC datetime, not naive/local."""

    record = _load_chain("AAPL.json")
    chain = OptionChain.model_validate(record)
    call = chain.options[0].calls[0]

    assert call.last_trade_date.tzinfo == datetime.timezone.utc


def test_option_chain_msft_and_spy_records_also_validate() -> None:
    """The other two captures (MSFT, SPY) validate cleanly as well."""

    msft = OptionChain.model_validate(_load_chain("MSFT.json"))
    spy = OptionChain.model_validate(_load_chain("SPY.json"))

    assert msft.underlying_symbol == "MSFT"
    assert msft.quote.symbol == "MSFT"
    assert spy.underlying_symbol == "SPY"
    assert spy.quote.symbol == "SPY"


def test_option_contract_accepts_live_observed_missing_bid() -> None:
    """A contract may omit bid in a non-US locale response."""

    record = _load_chain("AAPL.json")
    options = cast("list[dict[str, object]]", record["options"])
    puts = cast("list[dict[str, object]]", options[0]["puts"])
    del puts[0]["bid"]

    chain = OptionChain.model_validate(record)

    assert chain.options[0].puts[0].bid is None
