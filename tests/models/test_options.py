"""Round-trip tests for the typed OptionChain models against real corpus captures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from yoghurt.models.options import OptionChain
from yoghurt.models.quote import Quote

_CORPUS_OPTIONS_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "options"
)

_AAPL_CALL_STRIKE = 240.0
_AAPL_CALL_ASK = 70.2
_AAPL_CALL_LAST_TRADE_DATE = 1782492175
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
    assert all(isinstance(date, int) for date in chain.expiration_dates)
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
    assert isinstance(call.volume, int)
    assert call.model_extra in (None, {})


def test_option_contract_out_of_the_money_flag_varies() -> None:
    """A higher strike in the same chain is correctly flagged out of the money."""

    record = _load_chain("AAPL.json")
    chain = OptionChain.model_validate(record)
    calls = chain.options[0].calls

    otm_call = next(c for c in calls if c.strike == pytest.approx(_AAPL_OTM_STRIKE))
    assert otm_call.in_the_money is False


def test_option_chain_msft_and_spy_records_also_validate() -> None:
    """The other two captures (MSFT, SPY) validate cleanly as well."""

    msft = OptionChain.model_validate(_load_chain("MSFT.json"))
    spy = OptionChain.model_validate(_load_chain("SPY.json"))

    assert msft.underlying_symbol == "MSFT"
    assert msft.quote.symbol == "MSFT"
    assert spy.underlying_symbol == "SPY"
    assert spy.quote.symbol == "SPY"
