"""Typed identity/price/profile models for the ``quote-summary`` endpoint.

Reconciled against the probe corpus at ``tests/fixtures/corpus/quote-summary/``
(23 valid captures across EQUITY, ETF, MUTUALFUND, CRYPTOCURRENCY, CURRENCY,
FUTURE, INDEX, and OPTION quoteTypes), captured 2026-07-04. Regenerate the
applicability evidence with
``uv run python -m tools.fields_report quote-summary:<module>`` after a
corpus refresh (see ``tools/fields_report.py`` for the generic per-module
stream this evidence is built from). This module covers the first batch of
quote-summary modules (batch c1 of the Part 3c plan): ``price``,
``quoteType``, ``summaryDetail``, ``summaryProfile``, ``assetProfile``,
``pageViews``, ``corporateActions``, ``equityPerformance``, and
``quoteUnadjustedPerformanceOverview``. Applicability lines use "Observed
on: <types> summaries." per the plan's applicability-noun ruling for this
endpoint family.

Reconciliation notes:

- Every c1 module field is a bare scalar on the wire *except*
  ``assetProfile.companyOfficers[].totalPay``/``exercisedValue``/
  ``unexercisedValue``, which wrap their value as ``{raw, fmt, longFmt}``
  (occasionally ``fmt: null``, never ``{}``) — the first and only ``Raw*``
  usage in this batch; see :mod:`yoghurt.models._base` for the unwrap rule.
  :class:`CompanyOfficer` is this batch's RawFmt proving ground.
- A handful of fields (for example ``summaryDetail.algorithm``,
  ``.coinMarketCapLink``, ``.fromCurrency``, ``.lastMarket``,
  ``.toCurrency``; ``price.fromCurrency``/``.lastMarket``/``.toCurrency``/
  ``.underlyingSymbol``/``.longName``)
  are present on every corpus record but their value is null on all but
  one or two captures. Per the evidence-driven optionality rule (required
  iff the *key* is universal, independent of its value), these are
  required fields typed ``T | None`` with no default — the key is always
  sent, the value is frequently null.
- ``SummaryQuoteType`` (the ``quoteType`` module) is a *distinct* model
  from :class:`~yoghurt.models.quote.Quote`, per the plan's explicit
  instruction not to reuse it, and the corpus confirms why: for FUTURE
  captures, ``quoteType.symbol`` is the *contract* symbol (for example
  ``"CLQ26.NYM"``) while ``quoteType.underlyingSymbol`` is the requested
  continuous-contract symbol (``"CL=F"``) — the reverse of ``price.symbol``
  (the requested symbol) and ``price.underlyingSymbol`` (the contract).
  Corpus wins: ``SummaryQuoteType.symbol``/``.underlying_symbol`` keep
  their own wire semantics rather than being aligned with ``Quote``'s.
- ``corporateActions`` (the module) is a genuine shape divergence from
  ``Quote.corporate_actions``, not just a spelling difference, so it gets
  its own distinct models (:class:`CorporateActionMeta`,
  :class:`SummaryCorporateAction`, :class:`CorporateActions`) rather than
  reusing :class:`~yoghurt.models.quote.CorporateAction`. Every capture in
  this corpus but one has an empty list, matching ``Quote``'s own
  experience; the sole populated example (``RY.TO``) has ``header``,
  ``message``, and a nested ``meta`` block (``eventType``, ``dateEpochMs``,
  ``amount``) that ``Quote``'s never-populated placeholder does not carry
  at all. ``meta.dateEpochMs`` is an epoch in *milliseconds* (the sole
  example is 04:00 UTC — a session-anchored timestamp, NOT midnight-
  aligned, so only the derived ``.date()`` is exposed) rather than this
  corpus's usual seconds; per the
  ``first_trade_date_milliseconds`` precedent in
  :class:`~yoghurt.models.quote.Quote`, the wire ``int`` stays (named for
  its unit) and a ``@cached_property`` derives the ``datetime.date``.
  ``meta.amount`` is a wire *string* (``"1.76"``), not a float — corpus
  wins over the tempting reinterpretation. ``meta.eventType`` is typed
  plain ``str``: a single observed value (``"DIVIDEND"``) is not enough
  evidence for a closed vocabulary.
- ``equityPerformance`` and ``quoteUnadjustedPerformanceOverview`` share
  an identical nested shape (``benchmark``, ``performanceOverview``,
  ``performanceOverviewBenchmark``), verified field-for-field across every
  capture that carries either module, so both reuse the same
  :class:`Benchmark`/:class:`PerformanceOverview` sub-models. Both modules
  are present on every quoteType in this corpus, including INDEX, FUTURE,
  CURRENCY, and OPTION — "equity" in the name is a Yahoo-side misnomer, not
  an applicability restriction; ``benchmark``/``performanceOverviewBenchmark``
  themselves are optional (9 of 23 captures).
- ``summaryProfile`` and ``assetProfile`` share every ``summaryProfile``
  field; ``assetProfile`` additionally carries governance-risk fields
  (``auditRisk``, ``boardRisk``, ``compensationRisk``, ``overallRisk``,
  ``shareHolderRightsRisk``, ``compensationAsOfEpochDate``,
  ``governanceEpochDate`` — the epoch fields verified midnight-UTC-aligned)
  and is the only place ``companyOfficers`` is ever observed populated (87
  officers across 14 captures). Both modules' ``companyOfficers`` field
  reuses :class:`CompanyOfficer` — the same wire key, presumed the same
  shape, though ``summaryProfile``'s own list is empty in every capture.
  ``executiveTeam`` is a different, never-populated field in both modules;
  it gets its own empty-only placeholder, :class:`ExecutiveTeamMember`,
  mirroring :class:`~yoghurt.models.quote.CorporateAction`'s treatment of
  a field the corpus has never shown populated.
- ``assetProfile.startDate`` (BTC-USD only, value ``"2010-07-13"``) is an
  ISO calendar-date *string*, unlike every other date-shaped field in this
  batch (which are epoch seconds): pydantic parses the ISO string directly
  into ``datetime.date`` with no custom validator needed.
- ``summaryDetail.yield`` collides with the Python keyword; the field is
  named ``yield_`` with an explicit ``Field(alias="yield")``.
  ``summaryDetail.averageVolume10days`` has an irregular wire spelling
  (lowercase ``days``, unlike ``Quote``'s ``average_daily_volume_10_day``
  sibling concept) and keeps an explicit alias for the same reason as
  ``forwardPE``/``trailingPE``.
- Epoch fields without a wrapper follow the three-tier ruling directly:
  ``summaryDetail.exDividendDate``/``.expireDate``/``.startDate`` and
  ``PerformanceOverview.asOfDate`` are calendar-date epochs (verified
  midnight-UTC-aligned across every observed value) typed
  ``datetime.date``; ``SummaryQuoteType.first_trade_date_epoch_utc`` is a
  point-in-time epoch with in-model timezone context
  (``timeZoneFullName``), so it keeps the wire ``int`` plus a
  ``first_trade_datetime`` ``@cached_property``, mirroring
  ``Quote.first_trade_date_milliseconds``. ``price.regularMarketTime``/
  ``.postMarketTime`` are likewise point-in-time epochs with in-model
  timezone context, but the timezone lives on the *sibling* ``quoteType``
  module rather than in ``Price`` itself in this corpus, so (unlike
  ``Quote``) no localized ``@cached_property`` is added here — the wire
  ``int`` stands alone rather than guessing a timezone source.
- ``pageViews``'s three trend fields have only ever shown ``"UP"``/
  ``"DOWN"`` (2 of presumably more values) — not enough evidence for a
  closed vocabulary, so they stay plain ``str``.
"""

from __future__ import annotations

import datetime
from functools import cached_property
from zoneinfo import ZoneInfo

from pydantic import Field

from yoghurt.models._base import RawInt, YahooModel

# QuoteType is required in full for serialization purposes
from yoghurt.models.enums import (
    QuoteType,  # ruff:ignore[typing-only-first-party-import]
)


class Benchmark(YahooModel):
    """The comparison index used by a performance-overview module.

    Shared by :class:`EquityPerformance` and
    :class:`QuoteUnadjustedPerformanceOverview`, whose ``benchmark`` field
    validated against this shape with zero extras on every one of the 9
    corpus captures that carry it.
    """

    short_name: str
    """
    Short, user-friendly name of the benchmark index.
    """

    symbol: str
    """
    Ticker symbol of the benchmark index.
    """


class PerformanceOverview(YahooModel):
    """One return-performance snapshot: the subject or its benchmark.

    Shared by :class:`EquityPerformance` and
    :class:`QuoteUnadjustedPerformanceOverview`'s ``performanceOverview``
    and ``performanceOverviewBenchmark`` fields, verified field-for-field
    identical across both modules and every corpus capture that carries
    either. Every field but ``asOfDate`` is absent on the one OPTION
    capture in the corpus (options have no return history to report).
    """

    as_of_date: datetime.date
    """
    Date this performance snapshot was computed as of.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    five_days_return: float | None = None
    """
    Total return over the trailing 5 trading days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    five_year_total_return: float | None = None
    """
    Total return over the trailing 5 years.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    max_return: float | None = None
    """
    Total return since the earliest data point available for this security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    one_month_return: float | None = None
    """
    Total return over the trailing 1 month.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    one_year_total_return: float | None = None
    """
    Total return over the trailing 1 year.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    six_month_return: float | None = None
    """
    Total return over the trailing 6 months.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    ten_year_total_return: float | None = None
    """
    Total return over the trailing 10 years.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    three_month_return: float | None = None
    """
    Total return over the trailing 3 months.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    three_year_total_return: float | None = None
    """
    Total return over the trailing 3 years.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    two_year_total_return: float | None = None
    """
    Total return over the trailing 2 years.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    ytd_return_pct: float | None = None
    """
    Year-to-date return.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """


class EquityPerformance(YahooModel):
    """The ``equityPerformance`` module: return performance vs. a benchmark.

    Despite the name, this module is observed on every quoteType in the
    corpus, not just EQUITY (see the module docstring).
    """

    benchmark: Benchmark | None = None
    """
    The comparison index used for ``performance_overview_benchmark``.

    Observed on: EQUITY, ETF summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    performance_overview: PerformanceOverview
    """
    Return performance for the requested security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    performance_overview_benchmark: PerformanceOverview | None = None
    """
    Return performance for ``benchmark``, for comparison.

    Observed on: EQUITY, ETF summaries.
    """


class QuoteUnadjustedPerformanceOverview(YahooModel):
    """The ``quoteUnadjustedPerformanceOverview`` module.

    Field-for-field identical in shape to :class:`EquityPerformance` (see
    the module docstring); Yahoo returns both modules side by side with
    slightly different return figures (unadjusted vs. adjusted for
    dividends/splits), not a shape difference.
    """

    benchmark: Benchmark | None = None
    """
    The comparison index used for ``performance_overview_benchmark``.

    Observed on: EQUITY, ETF summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    performance_overview: PerformanceOverview
    """
    Unadjusted return performance for the requested security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    performance_overview_benchmark: PerformanceOverview | None = None
    """
    Unadjusted return performance for ``benchmark``, for comparison.

    Observed on: EQUITY, ETF summaries.
    """


class Price(YahooModel):
    """The ``price`` module: a compact real-time price snapshot."""

    average_daily_volume_10_day: int | None = None
    """
    Average number of units traded each day over the last 10 days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    average_daily_volume_3_month: int | None = None
    """
    Average number of units traded each day over the last 3 months.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    circulating_supply: int | None = None
    """
    Number of cryptocurrency units currently in public circulation.

    Observed on: CRYPTOCURRENCY summaries.
    """

    currency: str
    """
    Currency in which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    currency_symbol: str
    """
    Symbol of the currency in which the security is traded (for example, ``"$"``).

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    exchange: str
    """
    Short code of the securities exchange on which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    exchange_data_delayed_by: int
    """
    Delay in data from the exchange, typically in minutes.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    exchange_name: str
    """
    Short name of the securities exchange on which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    expire_date: int | None = None
    """
    Raw timestamp of the contract's expiration date.

    Observed on: FUTURE, OPTION summaries.
    """

    from_currency: str | None
    """
    Base currency in an exchange pair.

    Present (though usually null) on every summary; only ever non-null on
    CRYPTOCURRENCY summaries.
    """

    last_market: str | None
    """
    Last market in which the security was traded.

    Present (though usually null) on every summary; only ever non-null on
    CRYPTOCURRENCY summaries.
    """

    long_name: str | None
    """
    Official name of the company or security.

    Present on every summary in the corpus; null on FUTURE summaries.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, INDEX, MUTUALFUND,
    OPTION summaries.
    """

    market_cap: int | None = None
    """
    Total market value of the security in trading currency.

    Observed on: CRYPTOCURRENCY, EQUITY summaries.
    """

    market_state: str
    """
    Current state of the market for a security (for example, ``"CLOSED"``).

    Not typed :class:`~yoghurt.models.enums.MarketState`: every value
    observed here is also a member of that enum, but this field is
    reconciled independently rather than assumed compatible without a
    dedicated corpus check; revisit once one is done.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    open_interest: int | None = None
    """
    Total number of outstanding contracts that have not been settled.

    Observed on: FUTURE, OPTION summaries.
    """

    post_market_change: float | None = None
    """
    Change in the security's price in post-market trading.

    Observed on: EQUITY, ETF summaries.
    """

    post_market_change_percent: float | None = None
    """
    Percent change in the security's price in post-market trading.

    Observed on: EQUITY, ETF summaries.
    """

    post_market_price: float | None = None
    """
    Price of the security in post-market trading.

    Observed on: EQUITY, ETF summaries.
    """

    post_market_source: str | None = None
    """
    Data source for the post-market price (observed values: ``"FREE_REALTIME"``,
    ``"DELAYED"``).

    Observed on: EQUITY, ETF summaries.
    """

    post_market_time: int | None = None
    """
    Raw timestamp of the most recent post-market trade.

    Observed on: EQUITY, ETF summaries.
    """

    pre_market_source: str | None = None
    """
    Data source for the pre-market price (observed values: ``"FREE_REALTIME"``,
    ``"DELAYED"``).

    Observed alone, without accompanying pre-market price/change/time
    fields, on every corpus capture that carries it.

    Observed on: EQUITY, ETF summaries.
    """

    price_hint: int
    """
    Decimal precision indicator for price values.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    quote_source_name: str | None = None
    """
    Name of the source providing the quote.

    Absent on the two bond-yield INDEX captures in the corpus (``^IRX``,
    ``^TNX``); present on every other INDEX capture.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    quote_type: QuoteType
    """
    Type of quote.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    regular_market_change: float
    """
    Change in the security's price in regular trading.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    regular_market_change_percent: float
    """
    Percent change in the security's price in regular trading.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    regular_market_day_high: float | None = None
    """
    Highest price during the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    regular_market_day_low: float | None = None
    """
    Lowest price during the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    regular_market_open: float | None = None
    """
    Opening price for the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    regular_market_previous_close: float
    """
    Closing price of the security in the previous regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    regular_market_price: float
    """
    Latest price from the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    regular_market_source: str
    """
    Data source for the regular-session price (observed values:
    ``"FREE_REALTIME"``, ``"DELAYED"``).

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    regular_market_time: int
    """
    Raw timestamp of the most recent trade in the regular trading session.

    Unlike ``Quote.regular_market_time``, no localized datetime convenience
    is derived here: the exchange timezone lives on the sibling
    ``quoteType`` module (:class:`SummaryQuoteType`), not on ``Price``
    itself, in this corpus.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    regular_market_volume: int | None = None
    """
    Number of units traded in the regular session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    short_name: str
    """
    Short, user-friendly name for the quote or security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    strike_price: float | None = None
    """
    Contractually specified price for options exercise.

    Observed on: OPTION summaries.
    """

    symbol: str
    """
    Requested ticker symbol.

    For FUTURE summaries, this is the requested continuous-contract symbol
    (for example ``"CL=F"``); the resolved contract symbol is
    ``underlying_symbol`` instead — the reverse of
    ``SummaryQuoteType.symbol``/``.underlying_symbol``. See the module
    docstring.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    to_currency: str | None
    """
    Counter currency in an exchange pair.

    Present (though usually null) on every summary; only ever non-null on
    CRYPTOCURRENCY summaries.
    """

    underlying_symbol: str | None
    """
    For FUTURE and OPTION summaries, the resolved contract symbol (for
    example ``"CLQ26.NYM"``); the requested symbol is ``symbol`` instead.
    See the module docstring.

    Present (though usually null) on every summary; only ever non-null on
    FUTURE and OPTION summaries.
    """

    volume_24_hr: int | None = None
    """
    Total trading volume of a cryptocurrency in the past 24 hours.

    Observed on: CRYPTOCURRENCY summaries.
    """

    volume_all_currencies: int | None = None
    """
    Aggregate 24-hour volume across all currency pairs.

    Observed on: CRYPTOCURRENCY summaries.
    """

    def __repr__(self) -> str:
        """Return a compact developer-friendly representation."""

        return (
            f"Price(symbol={self.symbol!r}, "
            f"regular_market_price={self.regular_market_price!r}, "
            f"quote_type={self.quote_type!r})"
        )


class SummaryQuoteType(YahooModel):
    """The ``quoteType`` module: identity fields.

    Distinct from :class:`~yoghurt.models.quote.Quote` (per the plan's
    explicit instruction, not a reuse): its ``symbol``/``underlying_symbol``
    carry opposite semantics from ``price.symbol``/``.underlying_symbol``
    for FUTURE summaries. See the module docstring.
    """

    exchange: str
    """
    Short code of the securities exchange on which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    first_trade_date_epoch_utc: int | None = None
    """
    Raw timestamp of the first trade of this security.

    See ``first_trade_datetime`` for a timezone-aware convenience
    localized via ``time_zone_full_name``.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    gmt_off_set_milliseconds: int
    """
    Offset from GMT of the exchange, in milliseconds.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    long_name: str | None = None
    """
    Official name of the company or security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, INDEX, MUTUALFUND,
    OPTION summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    message_board_id: str | None = None
    """
    Identifier for the Yahoo! Finance message board for this security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, INDEX, MUTUALFUND
    summaries.
    """

    quote_type: QuoteType
    """
    Type of quote.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    short_name: str
    """
    Short, user-friendly name for the quote or security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    symbol: str
    """
    Resolved identifier for the quote-summary record.

    For FUTURE summaries, this is the resolved contract symbol (for
    example ``"CLQ26.NYM"``), the reverse of ``price.symbol`` (the
    requested continuous-contract symbol). See the module docstring.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    time_zone_full_name: str
    """
    Name of the timezone of the exchange.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    time_zone_short_name: str
    """
    Short name of the timezone of the exchange.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    underlying_symbol: str
    """
    For FUTURE summaries, the requested continuous-contract symbol (for
    example ``"CL=F"``); the resolved contract symbol is ``symbol``
    instead. Equal to ``symbol`` for every other observed quoteType. See
    the module docstring.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    uuid: str
    """
    Yahoo's internal unique identifier for this security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    # --- Convenience accessors (not part of the wire model) ---

    @cached_property
    def first_trade_datetime(self) -> datetime.datetime | None:
        """Date and time of the first trade of this security.

        Availability mirrors ``first_trade_date_epoch_utc``.
        """

        if self.first_trade_date_epoch_utc is None:
            return None
        tz_info = ZoneInfo(self.time_zone_full_name)
        return datetime.datetime.fromtimestamp(self.first_trade_date_epoch_utc, tz_info)

    def __repr__(self) -> str:
        """Return a compact developer-friendly representation."""

        return (
            f"SummaryQuoteType(symbol={self.symbol!r}, quote_type={self.quote_type!r})"
        )


class SummaryDetail(YahooModel):
    """The ``summaryDetail`` module: a wider price/valuation snapshot."""

    algorithm: str | None
    """
    Internal Yahoo! Finance field with undocumented and unknown purpose.

    Present on every summary in the corpus; never observed non-null.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    all_time_high: float | None = None
    """
    Highest price the security has ever traded at.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    all_time_low: float | None = None
    """
    Lowest price the security has ever traded at.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    ask: float | None = None
    """
    Lowest price a seller is willing to accept for the security.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION summaries.
    """

    ask_size: int | None = None
    """
    Number of units available at the current ask price.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX summaries.
    """

    average_daily_volume_10_day: int | None = None
    """
    Average number of units traded each day over the last 10 days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    average_volume: int | None = None
    """
    Average number of units traded each day (Yahoo's default averaging window).

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    average_volume_10_days: int | None = Field(
        default=None, alias="averageVolume10days"
    )
    """
    Average number of units traded each day over the last 10 days.

    Wire spelling is ``averageVolume10days`` (lowercase ``days``);
    ``to_camel`` alone would produce ``averageVolume10Days``, so this
    field carries an explicit alias override.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    beta: float | None = None
    """
    Measure of the security's volatility relative to the overall market.

    Observed on: EQUITY, ETF summaries.
    """

    bid: float | None = None
    """
    Highest price a buyer is willing to pay for the security.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION summaries.
    """

    bid_size: int | None = None
    """
    Total number of units buyers want to buy at the bid price.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX summaries.
    """

    circulating_supply: int | None = None
    """
    Number of cryptocurrency units currently in public circulation.

    Observed on: CRYPTOCURRENCY summaries.
    """

    coin_market_cap_link: str | None
    """
    URL of the MarketCap site for the cryptocurrency.

    Present on every summary in the corpus; only ever non-null on
    CRYPTOCURRENCY summaries.
    """

    currency: str
    """
    Currency in which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    day_high: float | None = None
    """
    Highest price during the current trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    day_low: float | None = None
    """
    Lowest price during the current trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    dividend_rate: float | None = None
    """
    Amount of dividends that a company is expected to pay over the next year.

    Observed on: EQUITY, ETF summaries.
    """

    dividend_yield: float | None = None
    """
    Annual dividend as a percentage of the security's current price.

    Observed on: EQUITY, ETF summaries.
    """

    ex_dividend_date: datetime.date | None = None
    """
    Date on which a buyer would no longer be entitled to the next dividend.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY, ETF summaries.
    """

    expire_date: datetime.date | None = None
    """
    Expiration date of the contract.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: FUTURE, OPTION summaries.
    """

    fifty_day_average: float | None = None
    """
    Average closing price of the security over the past 50 trading days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    fifty_two_week_high: float
    """
    Highest price the security has traded at in the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    fifty_two_week_low: float
    """
    Lowest price the security has traded at in the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    five_year_avg_dividend_yield: float | None = None
    """
    Average dividend yield over the past 5 years.

    Observed on: EQUITY, ETF summaries.
    """

    forward_pe: float | None = Field(default=None, alias="forwardPE")
    """
    Projected price-to-earnings ratio for the next 12 months.

    Wire spelling is ``forwardPE`` (capitalized acronym); ``to_camel``
    alone would produce ``forwardPe``, so this field carries an explicit
    alias override.

    Observed on: EQUITY summaries.
    """

    from_currency: str | None
    """
    Base currency in an exchange pair.

    Present (though usually null) on every summary; only ever non-null on
    CRYPTOCURRENCY summaries.
    """

    fully_diluted_value: int | None = None
    """
    Fully diluted market value, accounting for all convertible securities.

    Observed on: CRYPTOCURRENCY summaries.
    """

    last_market: str | None
    """
    Last market in which the security was traded.

    Present (though usually null) on every summary; only ever non-null on
    CRYPTOCURRENCY summaries.
    """

    market_cap: int | None = None
    """
    Total market value of the security in trading currency.

    Observed on: CRYPTOCURRENCY, EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    max_supply: int | None = None
    """
    Maximum number of cryptocurrency units that will ever exist.

    Observed on: CRYPTOCURRENCY summaries.
    """

    nav_price: float | None = None
    """
    Net asset value (NAV) per share.

    Observed on: ETF, MUTUALFUND summaries.
    """

    non_diluted_market_cap: int | None = None
    """
    Market value of the security excluding convertible securities.

    Observed on: EQUITY, ETF summaries.
    """

    open: float | None = None
    """
    Opening price for the current trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    open_interest: int | None = None
    """
    Total number of outstanding contracts that have not been settled.

    Observed on: FUTURE, OPTION summaries.
    """

    payout_ratio: float | None = None
    """
    Proportion of earnings paid out as dividends.

    Observed on: EQUITY, ETF summaries.
    """

    previous_close: float
    """
    Closing price of the security in the previous session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    price_hint: int
    """
    Decimal precision indicator for price values.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    price_to_sales_trailing_12_months: float | None = None
    """
    Ratio of market capitalization to trailing twelve-month revenue.

    Observed on: EQUITY, ETF summaries.
    """

    regular_market_day_high: float | None = None
    """
    Highest price during the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    regular_market_day_low: float | None = None
    """
    Lowest price during the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    regular_market_open: float | None = None
    """
    Opening price for the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    regular_market_previous_close: float
    """
    Closing price of the security in the previous regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    regular_market_volume: int | None = None
    """
    Number of units traded in the regular session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    start_date: datetime.date | None = None
    """
    Date on which the coin started trading.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date.

    Observed on: CRYPTOCURRENCY summaries.
    """

    strike_price: float | None = None
    """
    Contractually specified price for options exercise.

    Observed on: OPTION summaries.
    """

    to_currency: str | None
    """
    Counter currency in an exchange pair.

    Present (though usually null) on every summary; only ever non-null on
    CRYPTOCURRENCY summaries.
    """

    total_assets: int | None = None
    """
    Total net assets of the fund.

    Observed on: ETF, MUTUALFUND summaries.
    """

    total_supply: int | None = None
    """
    Total number of cryptocurrency units in existence, including those not
    yet in circulation.

    Observed on: CRYPTOCURRENCY summaries.
    """

    tradeable: bool
    """
    Whether the security is currently tradeable.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND, OPTION summaries.
    """

    trailing_annual_dividend_rate: float | None = None
    """
    Dividend payment per share over the past 12 months.

    Observed on: EQUITY, ETF summaries.
    """

    trailing_annual_dividend_yield: float | None = None
    """
    Dividend yield over the past 12 months.

    Observed on: EQUITY, ETF summaries.
    """

    trailing_pe: float | None = Field(default=None, alias="trailingPE")
    """
    Trailing price-to-earnings ratio based on past twelve-month results.

    Wire spelling is ``trailingPE`` (capitalized acronym); ``to_camel``
    alone would produce ``trailingPe``, so this field carries an explicit
    alias override.

    Observed on: EQUITY, ETF summaries.
    """

    two_hundred_day_average: float | None = None
    """
    Average closing price of the security over the past 200 trading days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    volume: int | None = None
    """
    Number of units traded in the current trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND summaries.
    """

    volume_24_hr: int | None = None
    """
    Total trading volume of a cryptocurrency in the past 24 hours.

    Observed on: CRYPTOCURRENCY summaries.
    """

    volume_24_hr_market_cap_percent: float | None = None
    """
    24-hour trading volume as a percentage of market capitalization.

    Observed on: CRYPTOCURRENCY summaries.
    """

    volume_all_currencies: int | None = None
    """
    Aggregate 24-hour volume across all currency pairs.

    Observed on: CRYPTOCURRENCY summaries.
    """

    yield_: float | None = Field(default=None, alias="yield")
    """
    Distribution yield of the fund.

    Wire spelling is the reserved word ``yield``; the Python field is
    named ``yield_`` with an explicit alias.

    Observed on: ETF, MUTUALFUND summaries.
    """

    ytd_return: float | None = None
    """
    Year-to-date return on the fund.

    Observed on: MUTUALFUND summaries.
    """


class CompanyOfficer(YahooModel):
    """One executive officer entry in ``assetProfile``/``summaryProfile``.

    The RawFmt proving ground for this batch: ``total_pay``,
    ``exercised_value``, and ``unexercised_value`` wrap their value as
    ``{raw, fmt, longFmt}`` (``fmt`` is null more often than not — for
    example a ``$0`` value has no formatted string) rather than sending it
    bare. Every one of the 87 corpus officer entries with these keys
    resolved a valid ``raw`` value with the ``Raw*`` unwrap rule; see
    :mod:`yoghurt.models._base`.
    """

    age: int | None = None
    """
    Officer's age.

    Always present alongside ``year_born`` or absent alongside it (never
    one without the other) across every corpus officer entry.

    Observed on: EQUITY, ETF, MUTUALFUND summaries.
    """

    exercised_value: RawInt
    """
    Value of stock options this officer has already exercised.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus
    officer entry (universal — present on all 87); see
    :mod:`yoghurt.models._base`.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    fiscal_year: int
    """
    Fiscal year this officer's compensation figures apply to.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    name: str
    """
    Officer's full name, often with an honorific prefix (for example
    ``"Mr. Timothy D. Cook"``).

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    title: str
    """
    Officer's title (for example ``"CEO & Director"``).

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    total_pay: RawInt | None = None
    """
    Total compensation reported for this officer for ``fiscal_year``.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus
    officer entry that carries this key; see :mod:`yoghurt.models._base`.
    Absent (not merely zero) on roughly 60% of corpus officer entries.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    unexercised_value: RawInt
    """
    Value of stock options this officer holds but has not yet exercised.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus
    officer entry (universal — present on all 87); see
    :mod:`yoghurt.models._base`.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    year_born: int | None = None
    """
    Officer's birth year.

    Always present alongside ``age`` or absent alongside it (never one
    without the other) across every corpus officer entry.

    Observed on: EQUITY, ETF, MUTUALFUND summaries.
    """


class ExecutiveTeamMember(YahooModel):
    """One entry in ``assetProfile``/``summaryProfile``'s ``executiveTeam``.

    This sub-model's shape is thinly observed: no corpus record supplies a
    populated entry to model fields from (every one of the 14 captures
    that carry ``executiveTeam`` has it as an empty list) — unlike the
    sibling ``companyOfficers`` field, which is populated in
    ``assetProfile``. It carries no fields of its own beyond what
    :class:`YahooModel` preserves via ``model_extra`` until a populated
    example is captured, mirroring
    :class:`~yoghurt.models.quote.CorporateAction`'s treatment of a
    never-populated field.

    Observed only as empty lists in the corpus.
    """


class SummaryProfile(YahooModel):
    """The ``summaryProfile`` module: company/fund description and contact details.

    Every field here is also present, identically spelled, on
    :class:`AssetProfile`; ``AssetProfile`` additionally carries
    governance-risk fields and is the only place ``company_officers`` is
    ever observed populated. See the module docstring.
    """

    address1: str | None = None
    """
    Primary street address of the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """

    address2: str | None = None
    """
    Secondary address line of the company's headquarters.

    Observed on: EQUITY summaries.
    """

    address3: str | None = None
    """
    Tertiary address line of the company's headquarters.

    Observed on: EQUITY summaries.
    """

    block_number: int | None = None
    """
    Most recent block number processed for this cryptocurrency.

    Observed on: CRYPTOCURRENCY summaries.
    """

    block_reward: float | None = None
    """
    Number of coins awarded to miners for processing a block.

    Observed on: CRYPTOCURRENCY summaries.
    """

    block_reward_reduction: str | None = None
    """
    Description of the next scheduled reduction in block reward (for
    example ``"50%"``).

    Observed on: CRYPTOCURRENCY summaries.
    """

    city: str | None = None
    """
    City of the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """

    company_officers: list[CompanyOfficer]
    """
    Executive officers of the company.

    Always an empty list in this module (see :class:`AssetProfile` for the
    only corpus examples of this field populated); reuses
    :class:`CompanyOfficer` on the assumption that a populated
    ``summaryProfile.companyOfficers`` shares its sibling module's shape,
    since it is the same wire key.

    Observed only as empty lists in the corpus.
    """

    country: str | None = None
    """
    Country of the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """

    description: str | None = None
    """
    Description of the cryptocurrency.

    Observed on: CRYPTOCURRENCY summaries.
    """

    executive_team: list[ExecutiveTeamMember]
    """
    Executive team members, in a shape never observed populated.

    Observed only as empty lists in the corpus.
    """

    fax: str | None = None
    """
    Fax number for the company's headquarters.

    Observed on: EQUITY summaries.
    """

    full_time_employees: int | None = None
    """
    Number of full-time employees at the company.

    Observed on: EQUITY, ETF summaries.
    """

    industry: str | None = None
    """
    Industry classification of the company.

    Observed on: EQUITY, ETF summaries.
    """

    industry_disp: str | None = None
    """
    Display-friendly industry classification of the company.

    Observed on: EQUITY, ETF summaries.
    """

    industry_key: str | None = None
    """
    Machine-friendly key for the company's industry classification.

    Observed on: EQUITY, ETF summaries.
    """

    ir_website: str | None = None
    """
    URL of the company's investor-relations website.

    Observed on: EQUITY summaries.
    """

    long_business_summary: str | None = None
    """
    Extended description of the company's business.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    name: str | None = None
    """
    Name of the cryptocurrency.

    Observed on: CRYPTOCURRENCY summaries.
    """

    net_hashes_per_second: str | None = None
    """
    Aggregate network hash rate securing the cryptocurrency, as a decimal
    string (the raw value exceeds standard 64-bit integer range).

    Observed on: CRYPTOCURRENCY summaries.
    """

    phone: str | None = None
    """
    Phone number for the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """

    sector: str | None = None
    """
    Sector classification of the company.

    Observed on: EQUITY, ETF summaries.
    """

    sector_disp: str | None = None
    """
    Display-friendly sector classification of the company.

    Observed on: EQUITY, ETF summaries.
    """

    sector_key: str | None = None
    """
    Machine-friendly key for the company's sector classification.

    Observed on: EQUITY, ETF summaries.
    """

    start_date: datetime.date | None = None
    """
    Date on which the coin started trading.

    Wire value is an ISO calendar-date string (for example
    ``"2010-07-13"``), unlike every epoch-shaped date elsewhere in this
    module; pydantic parses it directly into ``datetime.date``.

    Observed on: CRYPTOCURRENCY summaries.
    """

    state: str | None = None
    """
    State or province of the company's headquarters.

    Observed on: EQUITY summaries.
    """

    website: str | None = None
    """
    URL of the company's website.

    Observed on: EQUITY, ETF summaries.
    """

    whitepaper: str | None = None
    """
    URL of the cryptocurrency's whitepaper.

    Observed on: CRYPTOCURRENCY summaries.
    """

    zip: str | None = None
    """
    Postal code of the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """


class AssetProfile(YahooModel):
    """The ``assetProfile`` module: company profile plus governance-risk scores.

    Every field on :class:`SummaryProfile` is also present here, identically
    spelled; this module additionally carries the governance-risk fields
    below and is the only place ``company_officers`` is ever observed
    populated (87 officers across 14 captures). See the module docstring.
    """

    address1: str | None = None
    """
    Primary street address of the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """

    address2: str | None = None
    """
    Secondary address line of the company's headquarters.

    Observed on: EQUITY summaries.
    """

    address3: str | None = None
    """
    Tertiary address line of the company's headquarters.

    Observed on: EQUITY summaries.
    """

    audit_risk: int | None = None
    """
    Governance risk score for audit practices (lower is better).

    Observed on: EQUITY summaries.
    """

    block_number: int | None = None
    """
    Most recent block number processed for this cryptocurrency.

    Observed on: CRYPTOCURRENCY summaries.
    """

    block_reward: float | None = None
    """
    Number of coins awarded to miners for processing a block.

    Observed on: CRYPTOCURRENCY summaries.
    """

    block_reward_reduction: str | None = None
    """
    Description of the next scheduled reduction in block reward (for
    example ``"50%"``).

    Observed on: CRYPTOCURRENCY summaries.
    """

    board_risk: int | None = None
    """
    Governance risk score for board structure (lower is better).

    Observed on: EQUITY summaries.
    """

    city: str | None = None
    """
    City of the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """

    company_officers: list[CompanyOfficer]
    """
    Executive officers of the company.

    The only module where this field is ever observed populated (87
    officers across 9 of 14 captures, all EQUITY; empty elsewhere,
    including CRYPTOCURRENCY, ETF, and MUTUALFUND); see
    :class:`CompanyOfficer`.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    compensation_as_of_epoch_date: datetime.date | None = None
    """
    Date the officer compensation figures were current as of.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    compensation_risk: int | None = None
    """
    Governance risk score for executive compensation (lower is better).

    Observed on: EQUITY summaries.
    """

    country: str | None = None
    """
    Country of the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """

    description: str | None = None
    """
    Description of the cryptocurrency.

    Observed on: CRYPTOCURRENCY summaries.
    """

    executive_team: list[ExecutiveTeamMember]
    """
    Executive team members, in a shape never observed populated.

    Observed only as empty lists in the corpus.
    """

    fax: str | None = None
    """
    Fax number for the company's headquarters.

    Observed on: EQUITY summaries.
    """

    full_time_employees: int | None = None
    """
    Number of full-time employees at the company.

    Observed on: EQUITY, ETF summaries.
    """

    governance_epoch_date: datetime.date | None = None
    """
    Date the governance-risk scores were current as of.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds;
    pydantic converts it to a UTC calendar date (verified against every
    corpus value).

    Observed on: EQUITY summaries.
    """

    industry: str | None = None
    """
    Industry classification of the company.

    Observed on: EQUITY, ETF summaries.
    """

    industry_disp: str | None = None
    """
    Display-friendly industry classification of the company.

    Observed on: EQUITY, ETF summaries.
    """

    industry_key: str | None = None
    """
    Machine-friendly key for the company's industry classification.

    Observed on: EQUITY, ETF summaries.
    """

    ir_website: str | None = None
    """
    URL of the company's investor-relations website.

    Observed on: EQUITY summaries.
    """

    long_business_summary: str | None = None
    """
    Extended description of the company's business.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: CRYPTOCURRENCY, EQUITY, ETF, MUTUALFUND summaries.
    """

    name: str | None = None
    """
    Name of the cryptocurrency.

    Observed on: CRYPTOCURRENCY summaries.
    """

    net_hashes_per_second: str | None = None
    """
    Aggregate network hash rate securing the cryptocurrency, as a decimal
    string (the raw value exceeds standard 64-bit integer range).

    Observed on: CRYPTOCURRENCY summaries.
    """

    overall_risk: int | None = None
    """
    Overall governance risk score (lower is better).

    Observed on: EQUITY summaries.
    """

    phone: str | None = None
    """
    Phone number for the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """

    sector: str | None = None
    """
    Sector classification of the company.

    Observed on: EQUITY, ETF summaries.
    """

    sector_disp: str | None = None
    """
    Display-friendly sector classification of the company.

    Observed on: EQUITY, ETF summaries.
    """

    sector_key: str | None = None
    """
    Machine-friendly key for the company's sector classification.

    Observed on: EQUITY, ETF summaries.
    """

    share_holder_rights_risk: int | None = None
    """
    Governance risk score for shareholder rights (lower is better).

    Observed on: EQUITY summaries.
    """

    start_date: datetime.date | None = None
    """
    Date on which the coin started trading.

    Wire value is an ISO calendar-date string (for example
    ``"2010-07-13"``), unlike every epoch-shaped date elsewhere in this
    module; pydantic parses it directly into ``datetime.date``.

    Observed on: CRYPTOCURRENCY summaries.
    """

    state: str | None = None
    """
    State or province of the company's headquarters.

    Observed on: EQUITY summaries.
    """

    website: str | None = None
    """
    URL of the company's website.

    Observed on: EQUITY, ETF summaries.
    """

    whitepaper: str | None = None
    """
    URL of the cryptocurrency's whitepaper.

    Observed on: CRYPTOCURRENCY summaries.
    """

    zip: str | None = None
    """
    Postal code of the company's headquarters.

    Observed on: EQUITY, ETF summaries.
    """


class PageViews(YahooModel):
    """The ``pageViews`` module: Yahoo Finance page-view trend indicators."""

    long_term_trend: str
    """
    Long-term page-view trend (observed values: ``"UP"``, ``"DOWN"``).
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """

    mid_term_trend: str
    """
    Mid-term page-view trend (observed values: ``"UP"``, ``"DOWN"``).
    """

    short_term_trend: str
    """
    Short-term page-view trend (observed values: ``"UP"``, ``"DOWN"``).
    """


class CorporateActionMeta(YahooModel):
    """The ``meta`` block of one :class:`SummaryCorporateAction` entry.

    Thinly observed: the corpus has exactly one populated corporate-action
    entry (``RY.TO``, a dividend announcement), so this shape is evidenced
    by a single example rather than cross-checked against many.
    """

    amount: str
    """
    Amount associated with the corporate action, as a decimal string (for
    example ``"1.76"``) rather than a float — corpus wins over the
    tempting reinterpretation.
    """

    date_epoch_ms: int
    """
    Raw timestamp of the corporate action's effective date, in
    milliseconds (unlike this module's other epoch fields, which are in
    seconds).

    See ``date`` for a UTC calendar-date convenience.
    """

    event_type: str
    """
    Kind of corporate action (observed value: ``"DIVIDEND"``).

    A single observed value is not enough evidence for a closed
    vocabulary, so this stays plain ``str``.
    """

    # --- Convenience accessors (not part of the wire model) ---

    @cached_property
    def date(self) -> datetime.date:
        """The corporate action's effective date.

        ``date_epoch_ms`` is milliseconds; this divides by 1000 before
        converting, mirroring the
        ``Quote.first_trade_date_milliseconds`` precedent. Verified
        midnight-UTC-aligned against the sole corpus example.
        """

        return datetime.datetime.fromtimestamp(
            self.date_epoch_ms // 1000, datetime.timezone.utc
        ).date()


class SummaryCorporateAction(YahooModel):
    """One entry in the ``corporateActions`` module's list.

    A genuine shape divergence from
    :class:`~yoghurt.models.quote.CorporateAction`, not just a spelling
    difference: see the module docstring. Thinly observed, like its
    ``Quote`` counterpart was before this endpoint: the corpus has exactly
    one populated entry (``RY.TO``).
    """

    header: str
    """
    Short label for the corporate action (observed value: ``"Dividend"``).
    """

    message: str
    """
    Human-readable description of the corporate action.
    """

    meta: CorporateActionMeta
    """
    Structured details of the corporate action.
    """


class CorporateActions(YahooModel):
    """The ``corporateActions`` module: recent corporate actions on the quote.

    Every capture in the corpus but one has an empty
    ``corporate_actions`` list; see :class:`SummaryCorporateAction` for the
    sole populated example's shape.
    """

    corporate_actions: list[SummaryCorporateAction]
    """
    Corporate actions (splits, dividends, and similar events) on the quote.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """
