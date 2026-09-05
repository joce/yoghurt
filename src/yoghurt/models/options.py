"""Typed ``OptionChain`` response models for the ``options`` endpoint.

Reconciled against the probe corpus at ``tests/fixtures/corpus/options/``
(3 chain captures: AAPL, MSFT, SPY; 365 call+put contracts total), captured
2026-07-04, plus the deliberate ``ZZZZXYZQ`` invalid-symbol probe added
2026-07-05 (P4-1): a valid HTTP 200 with an empty ``optionChain.result``
(``{"optionChain": {"result": [], "error": None}}``), not an error payload —
this is exactly the empty-result shape ``yoghurt.api.Ticker.options`` was
already written to catch and raise ``SymbolNotFoundError`` for, now
confirmed by a real capture. Regenerate the applicability evidence with
``uv run python -m tools.fields_report option-contracts`` and
``uv run python -m tools.fields_report option-chains`` after a corpus
refresh. Reconciliation notes:

- Doubloon has no option-chain models to port from, so every docstring in
  this module is written fresh from observed values rather than
  reconciled against prior art.
- ``OptionContract`` has 15 wire keys; 14 are universal across all 365
  contracts and ``volume`` is optional (present on 353/365 — absent on a
  handful of illiquid strikes). Every other contract field's type was
  checked directly against every one of the 365 records, not just a
  sample: ``ask``, ``bid``, ``change``, ``impliedVolatility``,
  ``lastPrice``, ``percentChange``, and ``strike`` are consistently
  ``float``; ``contractSize``, ``contractSymbol``, and ``currency`` are
  ``str``; ``openInterest`` and ``volume`` are ``int``; ``inTheMoney`` is
  ``bool``.
- Per the coordinator ruling on epoch fields (see ``AGENTS.md``):
  ``expiration`` is a calendar-date epoch, verified midnight-UTC-aligned
  on every one of the 365 corpus contracts, and is typed
  ``datetime.date``. ``lastTradeDate`` is a point-in-time epoch with no
  in-model timezone context (unlike ``Quote``, ``OptionContract`` carries
  no exchange timezone field), so it is typed an aware UTC
  ``datetime.datetime``.
- ``OptionExpiration``'s four keys (``calls``, ``expirationDate``,
  ``hasMiniOptions``, ``puts``) are universal across all 3 captures'
  ``options[]`` entries (each capture carries exactly one).
  ``expirationDate`` is the same calendar-date epoch shape as
  ``OptionContract.expiration`` (verified midnight-UTC-aligned) and is
  likewise typed ``datetime.date``.
- The 2026-09-05 straddle captures in ``options/variants/`` (AAPL, MSFT,
  SPY, OKLO) replace ``calls`` and ``puts`` with ``straddles``. Collection
  fields are therefore optional, with validation requiring either the
  ordinary pair or the straddle collection. Individual paired call and put
  legs can be absent; ``strike`` is universal across the captured pairs.
- ``OptionChain``'s six top-level keys are universal across all 3
  captures' ``optionChain.result[0]`` records, including the embedded
  ``quote``, which validates as :class:`~yoghurt.models.quote.Quote` with
  zero extras on every capture — the first cross-model reuse in this
  package. ``expirationDates`` is a list of the same calendar-date epoch
  shape (verified midnight-UTC-aligned) and is typed
  ``list[datetime.date]``.
- Applicability: this family's "kinds" (call/put contracts, or the chain
  as a whole) are not instrument types the way quoteType or
  instrumentType are elsewhere in this package, and applicability is
  uniform within every class here (each contract field is observed across
  both kinds; chain- and expiration-level fields have no kind axis at
  all), so no field carries a per-field applicability line.
"""

from __future__ import annotations

import datetime  # ruff:ignore[typing-only-standard-library-import] - required at runtime for pydantic field resolution

from pydantic import model_validator

from yoghurt.models._base import YahooModel
from yoghurt.models.quote import (
    Quote,  # ruff:ignore[typing-only-first-party-import] - required for serialization
)


class OptionContract(YahooModel):
    """One call or put contract within an option chain expiration."""

    ask: float
    """
    Lowest price a seller is willing to accept for the contract.
    """

    bid: float
    """
    Highest price a buyer is willing to pay for the contract.
    """

    change: float
    """
    Change in the contract's last price from the previous session.
    """

    contract_size: str
    """
    Contract size category (observed value: ``"REGULAR"``).
    """

    contract_symbol: str
    """
    Yahoo's unique identifier for the option contract.
    """

    currency: str
    """
    Currency in which the contract is quoted.
    """

    expiration: datetime.date
    """
    Expiration date of the contract.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus contract).
    """

    implied_volatility: float
    """
    Market's forecast of the underlying security's volatility implied by
    the contract's price.
    """

    in_the_money: bool
    """
    Whether the contract is currently in the money.
    """

    last_price: float
    """
    Price of the contract's most recent trade.
    """

    last_trade_date: datetime.datetime
    """
    Date and time of the contract's most recent trade.

    Wire value is an epoch timestamp in seconds with no in-model timezone
    context to localize against; pydantic converts it to an aware UTC
    datetime.
    """

    open_interest: int
    """
    Total number of outstanding contracts that have not been settled.
    """

    percent_change: float
    """
    Percent change in the contract's last price from the previous session.
    """

    strike: float
    """
    Contractually specified price at which the contract can be exercised.
    """

    volume: int | None = None
    """
    Number of contracts traded during the most recent session.

    Absent on a minority of illiquid strikes (present on 353 of 365
    corpus contracts).
    """


class OptionStraddle(YahooModel):
    """Contracts paired by strike, captured on AAPL/MSFT/SPY/OKLO 2026-09-05.

    Both legs are independently absent on illiquid strikes in the variant corpus.
    """

    call: OptionContract | None = None
    """Call leg, when Yahoo returns one for this strike."""

    put: OptionContract | None = None
    """Put leg, when Yahoo returns one for this strike."""

    strike: float
    """Strike price shared by the paired contracts."""

    @model_validator(mode="after")
    def require_leg(self) -> OptionStraddle:
        """Reject a pair with neither contract.

        Returns:
            OptionStraddle: The validated pair.

        Raises:
            ValueError: If neither leg is present.
        """
        if self.call is None and self.put is None:
            message = "straddle must contain a call or put"
            raise ValueError(message)
        return self


class OptionExpiration(YahooModel):
    """One expiration date's full set of call and put contracts."""

    calls: list[OptionContract] | None = None
    """
    Call contracts; absent in straddle responses (AAPL/MSFT/SPY/OKLO, 2026-09-05).
    """

    expiration_date: datetime.date
    """
    Expiration date for this set of contracts.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus expiration).
    """

    has_mini_options: bool
    """
    Whether mini options (covering fewer underlying shares than a
    standard contract) are available for this expiration date.
    """

    puts: list[OptionContract] | None = None
    """
    Put contracts; absent in straddle responses (AAPL/MSFT/SPY/OKLO, 2026-09-05).
    """

    straddles: list[OptionStraddle] | None = None
    """Paired contracts, present only when requesting the straddle response."""

    @model_validator(mode="after")
    def require_response_family(self) -> OptionExpiration:
        """Require the ordinary pair of collections or the straddle collection.

        Returns:
            OptionExpiration: The validated expiration.

        Raises:
            ValueError: If collections are missing or mix response families.
        """
        ordinary = self.calls is not None and self.puts is not None
        paired = self.straddles is not None
        if not (ordinary or paired) or (
            paired and (self.calls is not None or self.puts is not None)
        ):
            message = "expiration must contain calls and puts, or straddles"
            raise ValueError(message)
        return self


class OptionChain(YahooModel):
    """The ``optionChain.result[0]`` record: a symbol's full option chain."""

    expiration_dates: list[datetime.date]
    """
    Every expiration date Yahoo offers for this symbol.

    Wire values are midnight-UTC-aligned epoch timestamps in seconds;
    pydantic converts each to a UTC calendar date (verified against every
    corpus value).
    """

    has_mini_options: bool
    """
    Whether mini options are available for this symbol.
    """

    options: list[OptionExpiration]
    """
    Contracts grouped by expiration date. Yahoo returns exactly one entry
    per request (the expiration selected via the ``date`` parameter, or
    the nearest one by default); the field is a list because the wire
    shape allows for more.
    """

    quote: Quote
    """
    The full quote record for the underlying security.
    """

    strikes: list[float]
    """
    Every strike price Yahoo offers across this symbol's option chain.
    """

    underlying_symbol: str
    """
    Ticker symbol of the security underlying this option chain.
    """
