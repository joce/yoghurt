"""Typed ``OptionChain`` response models for the ``options`` endpoint.

Reconciled against the probe corpus at ``tests/fixtures/corpus/options/``
(3 captures: AAPL, MSFT, SPY; 365 call+put contracts total), captured
2026-07-04. Regenerate the applicability evidence with
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
  ``str``; ``expiration``, ``lastTradeDate``, ``openInterest``, and
  ``volume`` are epoch/count ``int``; ``inTheMoney`` is ``bool``.
- ``OptionExpiration``'s four keys (``calls``, ``expirationDate``,
  ``hasMiniOptions``, ``puts``) are universal across all 3 captures'
  ``options[]`` entries (each capture carries exactly one).
- ``OptionChain``'s six top-level keys are universal across all 3
  captures' ``optionChain.result[0]`` records, including the embedded
  ``quote``, which validates as :class:`~yoghurt.models.quote.Quote` with
  zero extras on every capture — the first cross-model reuse in this
  package.
- Applicability-line wording: this family's "kinds" (call/put contracts,
  or the chain as a whole) are not instrument types the way quoteType or
  instrumentType are elsewhere in this package. Contract fields use
  "Observed on: call, put contracts." to name what varies (both kinds,
  here, since every contract field is universal or near-universal across
  both); chain- and expiration-level fields use the plain "Observed on
  option chains."/"Observed on option chain expirations." form since
  there is no kind axis to name at that level.
"""

from __future__ import annotations

from yoghurt.models._base import YahooModel
from yoghurt.models.quote import Quote  # noqa: TC001 - required for serialization


class OptionContract(YahooModel):
    """One call or put contract within an option chain expiration."""

    ask: float
    """
    Lowest price a seller is willing to accept for the contract.

    Observed on: call, put contracts.
    """

    bid: float
    """
    Highest price a buyer is willing to pay for the contract.

    Observed on: call, put contracts.
    """

    change: float
    """
    Change in the contract's last price from the previous session.

    Observed on: call, put contracts.
    """

    contract_size: str
    """
    Contract size category (observed value: ``"REGULAR"``).

    Observed on: call, put contracts.
    """

    contract_symbol: str
    """
    Yahoo's unique identifier for the option contract.

    Observed on: call, put contracts.
    """

    currency: str
    """
    Currency in which the contract is quoted.

    Observed on: call, put contracts.
    """

    expiration: int
    """
    Expiration date of the contract, as an epoch timestamp in seconds.

    Observed on: call, put contracts.
    """

    implied_volatility: float
    """
    Market's forecast of the underlying security's volatility implied by
    the contract's price.

    Observed on: call, put contracts.
    """

    in_the_money: bool
    """
    Whether the contract is currently in the money.

    Observed on: call, put contracts.
    """

    last_price: float
    """
    Price of the contract's most recent trade.

    Observed on: call, put contracts.
    """

    last_trade_date: int
    """
    Date and time of the contract's most recent trade, as an epoch
    timestamp in seconds.

    Observed on: call, put contracts.
    """

    open_interest: int
    """
    Total number of outstanding contracts that have not been settled.

    Observed on: call, put contracts.
    """

    percent_change: float
    """
    Percent change in the contract's last price from the previous session.

    Observed on: call, put contracts.
    """

    strike: float
    """
    Contractually specified price at which the contract can be exercised.

    Observed on: call, put contracts.
    """

    volume: int | None = None
    """
    Number of contracts traded during the most recent session.

    Absent on a minority of illiquid strikes (present on 353 of 365
    corpus contracts).

    Observed on: call, put contracts.
    """


class OptionExpiration(YahooModel):
    """One expiration date's full set of call and put contracts."""

    calls: list[OptionContract]
    """
    Call contracts for this expiration date.

    Observed on option chain expirations.
    """

    expiration_date: int
    """
    Expiration date for this set of contracts, as an epoch timestamp in
    seconds.

    Observed on option chain expirations.
    """

    has_mini_options: bool
    """
    Whether mini options (covering fewer underlying shares than a
    standard contract) are available for this expiration date.

    Observed on option chain expirations.
    """

    puts: list[OptionContract]
    """
    Put contracts for this expiration date.

    Observed on option chain expirations.
    """


class OptionChain(YahooModel):
    """The ``optionChain.result[0]`` record: a symbol's full option chain."""

    expiration_dates: list[int]
    """
    Every expiration date Yahoo offers for this symbol, as epoch
    timestamps in seconds.

    Observed on option chains.
    """

    has_mini_options: bool
    """
    Whether mini options are available for this symbol.

    Observed on option chains.
    """

    options: list[OptionExpiration]
    """
    Contracts grouped by expiration date. Yahoo returns exactly one entry
    per request (the expiration selected via the ``date`` parameter, or
    the nearest one by default); the field is a list because the wire
    shape allows for more.

    Observed on option chains.
    """

    quote: Quote
    """
    The full quote record for the underlying security.

    Observed on option chains.
    """

    strikes: list[float]
    """
    Every strike price Yahoo offers across this symbol's option chain.

    Observed on option chains.
    """

    underlying_symbol: str
    """
    Ticker symbol of the security underlying this option chain.

    Observed on option chains.
    """
