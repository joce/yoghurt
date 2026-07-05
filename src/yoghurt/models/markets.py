"""Typed models for the market-wide endpoints (batch 3e-1).

Reconciled against the probe corpus at ``tests/fixtures/corpus/``, captured
2026-07-04. Regenerate applicability evidence with
``uv run python -m tools.fields_report <stream>`` after a corpus refresh
(see ``tools/fields_report.py`` for the per-endpoint record streams this
evidence is built from). This module covers all five batch 3e-1 endpoints:
``trending``, ``market-summary``, ``market-info``, ``market-time``, and
``sector``. Unlike every prior symbol-bound batch, these endpoints are
market-wide: an empty result is valid data, never a lookup miss, so none of
the flips in ``api.py`` raise ``SymbolNotFoundError`` — see each function's
docstring in ``api.py``.

**trending** (endpoint noun: "trending records"). A single capture (5
CRYPTOCURRENCY/INDEX rows). ``TrendingResult`` models the
``finance.result[0]`` envelope (``count``/``jobTimestamp``/``quotes``/
``startInterval``); each row is a mini-quote reference distinct from
:class:`~yoghurt.models.quote.Quote` (``TrendingQuote``) — thinner than a
full quote (no ``fiftyTwoWeek*``/``currency``/``regularMarketChange*``
family) but carrying its own ``trendingScore`` field ``Quote`` has no
equivalent for. Thin, single-capture evidence: only ``priceHint`` (1/5 rows)
is optional; every other observed key is universal across this small
sample.

**market-summary** (endpoint noun: "market-summary records"). 15 rows
spanning INDEX/FUTURE/CURRENCY/CRYPTOCURRENCY quoteTypes. Per the plan's
decision procedure, every row was first script-validated directly against
the existing :class:`~yoghurt.models.quote.Quote` model: zero rows land any
field on ``model_extra`` (every wire key across all 15 rows is already
known to ``Quote``), but 8 of ``Quote``'s 34 required fields are *not*
universally present here (``currency``: 3/15; ``priceHint``: 10/15; all six
required ``fiftyTwoWeek*`` fields: 0/15 — Yahoo's market-summary tiles never carry a
52-week range at all, the optional ``fiftyTwoWeekLowChangePercent``
included). Zero-extras held, but the required-set clause of the
decision procedure did not, so per the plan this endpoint gets its own
distinct :class:`MarketSummaryQuote` rather than reusing ``Quote``. It has
27 required fields: 26 also required on ``Quote``, plus
``firstTradeDateMilliseconds`` (universal here across all 15 rows, but
only optional on ``Quote`` since that endpoint's own corpus never observed
it as universal) — a genuine per-endpoint requiredness difference, not a
modeling inconsistency. The usual mini-quote optionality pattern (seen
already on ``TrendingQuote``) applies to the rest: ``currency`` (CURRENCY
rows only), ``contractSymbol``/``headSymbolAsString`` (FUTURE rows only),
``priceHint``/``longName``/``quoteSourceName`` optional and evidence-thin.

**market-info** (endpoint noun: "market-info tiles"). A single capture:
``finance.result`` is a *mapping* (``currencies``/``commodities`` keys),
not a list — distinct from every other ``finance``-enveloped endpoint in
this codebase, and from the plan's initial "result[]" assumption (verified
directly against the corpus). Both keys are modeled optional:
``--modules`` selects which module Yahoo populates (mirroring the
``calendar-events`` precedent in
:mod:`yoghurt.models.analysis_events`), and this single capture only
exercises the default (both-modules) request, so there is no direct
evidence for a single-module response, but nothing rules it out either.
Each populated module is a :class:`MarketInfoModule` (``type``/
``quoteType``/``tickers``).

**market-time** (endpoint noun: "market-time record"). A single capture,
thin evidence throughout. The wire shape nests unusually deeply for a
symbol-independent endpoint: ``finance.marketTimes`` is a list of one
element whose own ``marketTime`` is *again* a list (of
:class:`MarketTimeEntry` rows, one per named market/exchange group);
``timezone`` is, in turn, a single-element list wrapping one
:class:`MarketTimeZone` object rather than a bare object. All three
list-wrapping layers are preserved as observed (evidence-driven, not
collapsed) since only one capture has ever been seen and there is no
counter-example showing the wrapping is spurious. ``dst``/``gmtoffset`` are
wire strings (``"true"``, ``"-14400"``), not bool/int, and are kept as
``str`` rather than coerced, since pydantic's bool coercion of arbitrary
strings would silently accept typos.

**sector** (endpoint noun: "sector records"). Four captures (``energy``,
``real-estate``, ``technology``, and a ``--with-returns`` variant of
``technology``) under the ``data`` envelope (see ``_core.ENVELOPES``).
Verified the ``--with-returns`` variant is genuinely shape-identical to its
plain counterpart (every key set matches at every nesting level across both
``technology.json`` and ``technology_returns.json``; only leaf values and
list ordering differ) — the plan's flagged possible optionality never
materializes in this corpus, so no extra fields were added speculatively.
Sub-models per wire block: :class:`SectorOverview`, :class:`SectorPerformance`
(also used for ``performanceOverviewBenchmark``, identical shape plus a
``name`` field — modeled as :class:`SectorBenchmarkPerformance`, which
embeds the shared metrics), :class:`SectorCompany`, :class:`SectorFund`
(shared by ``topETFs``/``topMutualFunds``, identical shape),
:class:`SectorIndustry`, and :class:`SectorResearchReport`.
``SectorIndustry.key``/``.symbol`` are optional: every capture's first
``industries`` row (Yahoo's "All Industries" aggregate) omits both, while
every other row carries them. ``SectorResearchReport.investment_rating``/
``.target_price``/``.target_price_status`` are optional at the row level
(present on some but not all rows within the same capture, and the
``energy`` capture has none of the three on any row).
"""

from __future__ import annotations

import datetime  # noqa: TC003 - pydantic needs this at runtime to resolve annotations

from pydantic import Field

from yoghurt.models._base import RawFloat, YahooModel
from yoghurt.models.enums import (  # noqa: TC001 - pydantic needs these at runtime
    MarketState,
    PriceAlertConfidence,
    QuoteType,
)

# ---------------------------------------------------------------------------
# trending
# ---------------------------------------------------------------------------


class TrendingQuote(YahooModel):
    """One mini-quote reference in a :class:`TrendingResult`.

    Distinct from :class:`~yoghurt.models.quote.Quote`: thinner (no
    ``fiftyTwoWeek*``/``currency``/``regularMarketChange*`` family observed)
    but carries its own ``trending_score`` field with no ``Quote``
    equivalent. See the module docstring for the single-capture evidence
    caveat.
    """

    crypto_tradeable: bool
    """
    Whether this instrument can be traded as cryptocurrency.

    Observed on: trending records.
    """

    custom_price_alert_confidence: PriceAlertConfidence
    """
    Yahoo's confidence level for its price-alert feature on this symbol.

    Observed on: trending records.
    """

    esg_populated: bool
    """
    Whether Yahoo has ESG (environmental/social/governance) data for this
    symbol.

    Observed on: trending records.
    """

    exchange: str
    """
    Short code of the securities exchange (for example ``"CCC"``).

    Observed on: trending records.
    """

    exchange_data_delayed_by: int
    """
    Minutes this exchange's data is delayed by.

    Observed on: trending records.
    """

    exchange_timezone_name: str
    """
    IANA timezone name of the exchange (for example ``"UTC"``).

    Observed on: trending records.
    """

    exchange_timezone_short_name: str
    """
    Short abbreviation of the exchange timezone (for example ``"UTC"``).

    Observed on: trending records.
    """

    first_trade_date_milliseconds: int
    """
    Epoch-milliseconds timestamp of this instrument's first trade.

    Observed on: trending records.
    """

    full_exchange_name: str
    """
    Full display name of the exchange (for example ``"CCC"``).

    Observed on: trending records.
    """

    gmt_off_set_milliseconds: int
    """
    Offset from GMT of the exchange, in milliseconds.

    Observed on: trending records.
    """

    has_pre_post_market_data: bool
    """
    Whether pre-market/after-hours data is available for this symbol.

    Observed on: trending records.
    """

    language: str
    """
    Locale Yahoo rendered this record in (for example ``"en-US"``).

    Observed on: trending records.
    """

    market: str
    """
    Yahoo's internal market-segment identifier (for example
    ``"ccc_market"``).

    Observed on: trending records.
    """

    market_state: MarketState = Field(alias="marketState")
    """
    Current trading session phase.

    Observed on: trending records.
    """

    price_hint: int | None = None
    """
    Suggested decimal-place precision for displaying this symbol's price.

    Present on 1 of 5 corpus rows (the lone INDEX row); the four
    CRYPTOCURRENCY rows omit it.

    Observed on: trending records.
    """

    quote_source_name: str = Field(alias="quoteSourceName")
    """
    Human-readable name of the quote data source (for example
    ``"CoinMarketCap"``, ``"Delayed Quote"``).

    Observed on: trending records.
    """

    quote_type: QuoteType
    """
    Classification of this instrument.

    Observed on: trending records.
    """

    region: str
    """
    Yahoo region this record was served for (for example ``"US"``).

    Observed on: trending records.
    """

    regular_market_price: float = Field(alias="regularMarketPrice")
    """
    Most recent regular-session trade price.

    Observed on: trending records.
    """

    regular_market_time: int = Field(alias="regularMarketTime")
    """
    Epoch-seconds timestamp of ``regular_market_price``.

    Observed on: trending records.
    """

    source_interval: int
    """
    Refresh interval, in minutes, of the underlying data source.

    Observed on: trending records.
    """

    symbol: str
    """
    Yahoo ticker symbol.

    Observed on: trending records.
    """

    tradeable: bool
    """
    Whether this instrument can be traded through Yahoo's brokerage
    integration.

    Observed on: trending records.
    """

    trending_score: float = Field(alias="trendingScore")
    """
    Yahoo's internal trending-rank score for this symbol (higher is more
    trending); no equivalent field on
    :class:`~yoghurt.models.quote.Quote`.

    Observed on: trending records.
    """

    triggerable: bool
    """
    Whether this symbol supports Yahoo's price-alert triggers.

    Observed on: trending records.
    """

    type_disp: str = Field(alias="typeDisp")
    """
    Human-readable display label for ``quote_type`` (for example
    ``"Cryptocurrency"``, ``"Index"``).

    Observed on: trending records.
    """


class TrendingResult(YahooModel):
    """The ``trending`` endpoint's ``finance.result[0]`` payload."""

    count: int
    """
    Number of rows in ``quotes``, matching ``len(quotes)`` on the corpus
    capture.

    Observed on: trending records.
    """

    job_timestamp: int = Field(alias="jobTimestamp")
    """
    Epoch-milliseconds timestamp of the batch job that computed this
    trending list.

    Observed on: trending records.
    """

    quotes: list[TrendingQuote]
    """
    Trending symbols, most trending first.

    Observed on: trending records.
    """

    start_interval: int = Field(alias="startInterval")
    """
    Yahoo-internal interval identifier for this trending computation (for
    example ``202607040300``); exact encoding unconfirmed.

    Observed on: trending records.
    """


# ---------------------------------------------------------------------------
# market-summary
# ---------------------------------------------------------------------------


class MarketSummaryQuote(YahooModel):
    """One row of the ``market-summary`` endpoint's result list.

    Distinct from :class:`~yoghurt.models.quote.Quote`; see the module
    docstring for the script-validated reuse-decision evidence (zero
    extras, but 8 of ``Quote``'s 34 required fields are not universal here).
    """

    contract_symbol: bool | None = Field(default=None, alias="contractSymbol")
    """
    Whether this is a continuation-contract symbol.

    Present only on FUTURE rows (3 of 15 corpus rows).

    Observed on: market-summary records.
    """

    crypto_tradeable: bool
    """
    Whether this instrument can be traded as cryptocurrency.

    Observed on: market-summary records.
    """

    currency: str | None = None
    """
    ISO currency code this quote is denominated in.

    Present only on CURRENCY rows (3 of 15 corpus rows).

    Observed on: market-summary records.
    """

    custom_price_alert_confidence: PriceAlertConfidence
    """
    Yahoo's confidence level for its price-alert feature on this symbol.

    Observed on: market-summary records.
    """

    esg_populated: bool
    """
    Whether Yahoo has ESG (environmental/social/governance) data for this
    symbol.

    Observed on: market-summary records.
    """

    exchange: str
    """
    Short code of the securities exchange (for example ``"SNP"``,
    ``"NYM"``, ``"CCY"``).

    Observed on: market-summary records.
    """

    exchange_data_delayed_by: int
    """
    Minutes this exchange's data is delayed by.

    Observed on: market-summary records.
    """

    exchange_timezone_name: str
    """
    IANA timezone name of the exchange.

    Observed on: market-summary records.
    """

    exchange_timezone_short_name: str
    """
    Short abbreviation of the exchange timezone.

    Observed on: market-summary records.
    """

    first_trade_date_milliseconds: int
    """
    Epoch-milliseconds timestamp of this instrument's first trade.

    Observed on: market-summary records.
    """

    full_exchange_name: str
    """
    Full display name of the exchange.

    Observed on: market-summary records.
    """

    gmt_off_set_milliseconds: int
    """
    Offset from GMT of the exchange, in milliseconds.

    Observed on: market-summary records.
    """

    has_pre_post_market_data: bool
    """
    Whether pre-market/after-hours data is available for this symbol.

    Observed on: market-summary records.
    """

    head_symbol_as_string: str | None = Field(default=None, alias="headSymbolAsString")
    """
    Root contract symbol for a futures continuation (for example
    ``"CL=F"``).

    Present only on FUTURE rows (3 of 15 corpus rows).

    Observed on: market-summary records.
    """

    language: str
    """
    Locale Yahoo rendered this record in.

    Observed on: market-summary records.
    """

    long_name: str | None = None
    """
    Official long name of the security.

    Present on 12 of 15 corpus rows.

    Observed on: market-summary records.
    """

    market: str
    """
    Yahoo's internal market-segment identifier.

    Observed on: market-summary records.
    """

    market_state: MarketState = Field(alias="marketState")
    """
    Current trading session phase.

    Observed on: market-summary records.
    """

    price_hint: int | None = None
    """
    Suggested decimal-place precision for displaying this symbol's price.

    Present on 10 of 15 corpus rows; unlike
    :class:`~yoghurt.models.quote.Quote`, where this field is universal,
    it is not consistently sent here.

    Observed on: market-summary records.
    """

    quote_source_name: str | None = Field(default=None, alias="quoteSourceName")
    """
    Human-readable name of the quote data source (for example
    ``"Delayed Quote"``).

    Present on 14 of 15 corpus rows.

    Observed on: market-summary records.
    """

    quote_type: QuoteType
    """
    Classification of this instrument.

    Observed on: market-summary records.
    """

    region: str
    """
    Yahoo region this record was served for.

    Observed on: market-summary records.
    """

    regular_market_change: float = Field(alias="regularMarketChange")
    """
    Absolute change from the previous regular-session close.

    A bare wire float here, matching
    :class:`~yoghurt.models.quote.Quote`'s field of the same name (not
    ``{raw, fmt}``-wrapped).

    Observed on: market-summary records.
    """

    regular_market_change_percent: float = Field(alias="regularMarketChangePercent")
    """
    Percent change from the previous regular-session close.

    Observed on: market-summary records.
    """

    regular_market_previous_close: float = Field(alias="regularMarketPreviousClose")
    """
    Previous regular-session closing price.

    Observed on: market-summary records.
    """

    regular_market_price: float = Field(alias="regularMarketPrice")
    """
    Most recent regular-session trade price.

    Observed on: market-summary records.
    """

    regular_market_time: int = Field(alias="regularMarketTime")
    """
    Epoch-seconds timestamp of ``regular_market_price``.

    Observed on: market-summary records.
    """

    short_name: str
    """
    Short display name of the security.

    Observed on: market-summary records.
    """

    source_interval: int
    """
    Refresh interval, in minutes, of the underlying data source.

    Observed on: market-summary records.
    """

    symbol: str
    """
    Yahoo ticker symbol.

    Observed on: market-summary records.
    """

    tradeable: bool
    """
    Whether this instrument can be traded through Yahoo's brokerage
    integration.

    Observed on: market-summary records.
    """

    triggerable: bool
    """
    Whether this symbol supports Yahoo's price-alert triggers.

    Observed on: market-summary records.
    """

    type_disp: str = Field(alias="typeDisp")
    """
    Human-readable display label for ``quote_type``.

    Observed on: market-summary records.
    """


# ---------------------------------------------------------------------------
# market-info
# ---------------------------------------------------------------------------


class MarketInfoModule(YahooModel):
    """One module tile of a :class:`MarketInfoResult`.

    Either the ``currencies`` or ``commodities`` module.
    """

    quote_type: QuoteType = Field(alias="quoteType")
    """
    Instrument classification every symbol in ``tickers`` shares (for
    example ``CURRENCY`` for the ``currencies`` module, ``FUTURE`` for
    ``commodities``).

    Observed on: market-info tiles.
    """

    tickers: list[str]
    """
    Symbols belonging to this module (for example ``["EURUSD=X", ...]``).

    May contain duplicate symbols (the corpus ``currencies`` module repeats
    ``"EURJPY=X"``); preserved as observed, not de-duplicated.

    Observed on: market-info tiles.
    """

    type: str
    """
    Yahoo's internal payload-kind tag; always ``"screener_payload"`` in the
    corpus.

    Observed on: market-info tiles.
    """


class MarketInfoResult(YahooModel):
    """The ``market-info`` endpoint's ``finance.result`` payload.

    ``finance.result`` is a *mapping* here (``currencies``/``commodities``
    keys), not a list — distinct from every other ``finance``-enveloped
    endpoint in this codebase. Both fields are optional: ``--modules``
    selects which module Yahoo populates, mirroring the ``calendar-events``
    precedent in :mod:`yoghurt.models.analysis_events`, though this
    single-capture corpus has only ever exercised the default (both-module)
    request.
    """

    commodities: MarketInfoModule | None = None
    """
    Commodity futures tile.

    Observed on: market-info tiles.
    """

    currencies: MarketInfoModule | None = None
    """
    Currency-pair tile.

    Observed on: market-info tiles.
    """


# ---------------------------------------------------------------------------
# market-time
# ---------------------------------------------------------------------------


class MarketTimeZone(YahooModel):
    """The single-element ``timezone`` list entry of a :class:`MarketTimeEntry`."""

    dst: str
    """
    Whether daylight-saving time is active, as Yahoo's wire string
    (``"true"``/``"false"``) rather than a bool — kept as-is since coercing
    arbitrary strings to bool risks silently accepting typos.

    Observed on: market-time record.
    """

    gmtoffset: str
    """
    Offset from GMT, in seconds, as a wire string (for example
    ``"-14400"``).

    Observed on: market-time record.
    """

    short: str
    """
    Short timezone abbreviation (for example ``"EDT"``).

    Observed on: market-time record.
    """

    text: str = Field(alias="$text")
    """
    IANA timezone name (for example ``"America/New_York"``).

    Wire key is ``"$text"``, an XML-derived artifact of Yahoo's underlying
    data source.

    Observed on: market-time record.
    """


class MarketTimeEntry(YahooModel):
    """One named market/exchange group in a :class:`MarketTimeResult`."""

    close: datetime.datetime
    """
    This session's close time.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.

    Observed on: market-time record.
    """

    id: str
    """
    Short market identifier (for example ``"us"``).

    Observed on: market-time record.
    """

    message: str
    """
    Human-readable session-status message (for example ``"U.S. markets
    closed"``).

    Observed on: market-time record.
    """

    name: str
    """
    Display name of the market group (for example ``"U.S. markets"``).

    Observed on: market-time record.
    """

    open: datetime.datetime
    """
    This session's open time.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.

    Observed on: market-time record.
    """

    status: str
    """
    Session status label (for example ``"closed"``).

    Only ``"closed"`` observed in this single-capture corpus; too thin to
    type as a closed-vocabulary enum.

    Observed on: market-time record.
    """

    time: datetime.datetime
    """
    Point-in-time timestamp this record was computed at.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.

    Observed on: market-time record.
    """

    timezone: list[MarketTimeZone]
    """
    Single-element list wrapping this market's timezone details.

    Observed on: market-time record.
    """

    yfit_market_id: str = Field(alias="yfit_market_id")
    """
    Yahoo-internal market identifier (for example ``"us_market"``).

    Observed on: market-time record.
    """

    yfit_market_status: str = Field(alias="yfit_market_status")
    """
    Yahoo-internal market status code (for example
    ``"YFT_MARKET_CLOSED"``).

    Only this one value observed in this single-capture corpus; too thin
    to type as a closed-vocabulary enum.

    Observed on: market-time record.
    """


class MarketTimeGroup(YahooModel):
    """One element of ``finance.marketTimes``, wrapping a list of markets."""

    market_time: list[MarketTimeEntry] = Field(alias="marketTime")
    """
    Markets/exchanges reported in this group.

    Observed on: market-time record.
    """


class MarketTimeMeta(YahooModel):
    """One element of the ``finance.meta`` status list."""

    status: str
    """
    Request status label; always ``"success"`` in the corpus.

    Observed on: market-time record.
    """


class MarketTimeResult(YahooModel):
    """The ``market-time`` endpoint's ``finance`` payload.

    Thin, single-capture evidence throughout; see the module docstring for
    the unusual triple-nested list wrapping (``marketTimes`` ->
    ``marketTime`` -> ``timezone``), preserved as observed rather than
    collapsed.
    """

    lang: str
    """
    Locale Yahoo rendered this record in.

    Observed on: market-time record.
    """

    market_times: list[MarketTimeGroup] = Field(alias="marketTimes")
    """
    Market-group entries; a single-element list in the corpus.

    Observed on: market-time record.
    """

    meta: list[MarketTimeMeta]
    """
    Request status metadata.

    Observed on: market-time record.
    """

    version: int
    """
    Envelope schema version; always ``5`` in the corpus.

    Observed on: market-time record.
    """


# ---------------------------------------------------------------------------
# sector
# ---------------------------------------------------------------------------


class SectorOverview(YahooModel):
    """The ``overview`` block of a :class:`SectorResult`."""

    companies_count: int = Field(alias="companiesCount")
    """
    Number of companies classified under this sector.

    Observed on: sector records.
    """

    description: str
    """
    Prose description of the industries and companies this sector covers.

    Observed on: sector records.
    """

    employee_count: RawFloat = Field(alias="employeeCount")
    """
    Aggregate employee headcount across this sector's companies.

    Wrapped as ``{"raw": ..., "fmt": ..., "longFmt": ...}`` on the wire.

    Observed on: sector records.
    """

    industries_count: int = Field(alias="industriesCount")
    """
    Number of industries this sector is broken down into.

    Observed on: sector records.
    """

    market_cap: RawFloat = Field(alias="marketCap")
    """
    Aggregate market capitalization across this sector's companies.

    Wrapped as ``{"raw": ..., "fmt": ..., "longFmt": ...}`` on the wire.

    Observed on: sector records.
    """

    market_weight: RawFloat = Field(alias="marketWeight")
    """
    This sector's share of the overall market, as a fraction (for example
    ``0.31`` for 31%).

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    message_board_id: str = Field(alias="messageBoardId")
    """
    Identifier for the Yahoo! Finance message board for this sector.

    Observed on: sector records.
    """


class SectorPerformance(YahooModel):
    """The ``performance`` block of a :class:`SectorResult`."""

    five_year_change_percent: RawFloat = Field(alias="fiveYearChangePercent")
    """
    Percent price change over the trailing five years, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    one_year_change_percent: RawFloat = Field(alias="oneYearChangePercent")
    """
    Percent price change over the trailing one year, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    reg_market_change_percent: RawFloat = Field(alias="regMarketChangePercent")
    """
    Percent price change during the current/most recent regular session,
    as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    three_year_change_percent: RawFloat = Field(alias="threeYearChangePercent")
    """
    Percent price change over the trailing three years, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    ytd_change_percent: RawFloat = Field(alias="ytdChangePercent")
    """
    Percent price change year-to-date, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """


class SectorBenchmarkPerformance(YahooModel):
    """The ``performanceOverviewBenchmark`` block of a :class:`SectorResult`.

    Shares every metric field with :class:`SectorPerformance` (modeled
    fresh rather than via inheritance, per this codebase's flat
    one-model-per-wire-block template), plus a ``name`` identifying the
    benchmark index.
    """

    five_year_change_percent: RawFloat = Field(alias="fiveYearChangePercent")
    """
    Percent price change over the trailing five years, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    name: str
    """
    Display name of the benchmark index (for example ``"S&P 500"``).

    Observed on: sector records.
    """

    one_year_change_percent: RawFloat = Field(alias="oneYearChangePercent")
    """
    Percent price change over the trailing one year, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    reg_market_change_percent: RawFloat = Field(alias="regMarketChangePercent")
    """
    Percent price change during the current/most recent regular session,
    as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    three_year_change_percent: RawFloat = Field(alias="threeYearChangePercent")
    """
    Percent price change over the trailing three years, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    ytd_change_percent: RawFloat = Field(alias="ytdChangePercent")
    """
    Percent price change year-to-date, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """


class SectorCompany(YahooModel):
    """One row of a :class:`SectorResult`'s ``topCompanies`` list."""

    last_price: RawFloat = Field(alias="lastPrice")
    """
    Most recent trade price.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    market_cap: RawFloat = Field(alias="marketCap")
    """
    Market capitalization.

    Wrapped as ``{"raw": ..., "fmt": ..., "longFmt": ...}`` on the wire.

    Observed on: sector records.
    """

    market_weight: RawFloat = Field(alias="marketWeight")
    """
    This company's share of the sector's overall market weight, as a
    fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    name: str | None = None
    """
    Company display name.

    Absent on 1 of 200 corpus rows (symbol ``AHR``).

    Observed on: sector records.
    """

    rating: str
    """
    Aggregate analyst rating label (for example ``"Strong Buy"``).

    Observed on: sector records.
    """

    reg_market_change_percent: RawFloat = Field(alias="regMarketChangePercent")
    """
    Percent price change during the current/most recent regular session,
    as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    symbol: str
    """
    Yahoo ticker symbol.

    Observed on: sector records.
    """

    target_price: RawFloat = Field(alias="targetPrice")
    """
    Aggregate analyst price target.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    ytd_return: RawFloat = Field(alias="ytdReturn")
    """
    Year-to-date return, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """


class SectorFund(YahooModel):
    """One row of a :class:`SectorResult`'s ``topETFs``/``topMutualFunds`` list.

    Both lists share this identical shape (verified across all 4 corpus
    captures).
    """

    expense_ratio: RawFloat = Field(alias="expenseRatio")
    """
    Annual fund expense ratio, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    last_price: RawFloat = Field(alias="lastPrice")
    """
    Most recent trade price (NAV).

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    name: str | None = None
    """
    Fund display name.

    Absent on 10 of 40 ``topMutualFunds`` rows (Fidelity share-class
    tickers such as ``FFONX``/``FFOJX``/``FFOTX``/``FFOQX``/``FFOMX``,
    which omit it consistently); always present on ``topETFs`` rows.

    Observed on: sector records.
    """

    net_assets: RawFloat = Field(alias="netAssets")
    """
    Total net assets under management.

    Wrapped as ``{"raw": ..., "fmt": ..., "longFmt": ...}`` on the wire.

    Observed on: sector records.
    """

    symbol: str
    """
    Yahoo ticker symbol.

    Observed on: sector records.
    """

    ytd_return: RawFloat = Field(alias="ytdReturn")
    """
    Year-to-date return, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """


class SectorIndustry(YahooModel):
    """One row of a :class:`SectorResult`'s ``industries`` list."""

    key: str | None = None
    """
    URL-safe industry slug.

    Absent on the first ``industries`` row of every corpus capture (Yahoo's
    "All Industries" aggregate row); present on every other row.

    Observed on: sector records.
    """

    market_weight: RawFloat = Field(alias="marketWeight")
    """
    This industry's share of the sector's overall market weight, as a
    fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    name: str
    """
    Industry display name (for example ``"All Industries"``,
    ``"Semiconductors"``).

    Observed on: sector records.
    """

    reg_market_change_percent: RawFloat = Field(alias="regMarketChangePercent")
    """
    Percent price change during the current/most recent regular session,
    as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """

    symbol: str | None = None
    """
    Yahoo symbol for this industry's tracking index.

    Absent on the first ``industries`` row of every corpus capture (Yahoo's
    "All Industries" aggregate row); present on every other row.

    Observed on: sector records.
    """

    ytd_return: RawFloat = Field(alias="ytdReturn")
    """
    Year-to-date return, as a fraction.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.

    Observed on: sector records.
    """


class SectorResearchReport(YahooModel):
    """One row of a :class:`SectorResult`'s ``researchReports`` list."""

    head_html: str = Field(alias="headHtml")
    """
    Short report headline (for example ``"Analyst Report: Entegris,
    Inc."``).

    Observed on: sector records.
    """

    id: str
    """
    Unique identifier for this report.

    Observed on: sector records.
    """

    investment_rating: str | None = Field(default=None, alias="investmentRating")
    """
    Analyst investment rating label (for example ``"Neutral"``,
    ``"Bullish"``, ``"Bearish"``).

    Optional at the row level: absent on some rows within the same capture,
    and absent on every row of the ``energy`` capture.

    Observed on: sector records.
    """

    provider: str
    """
    Research provider name (for example ``"Morningstar"``).

    Observed on: sector records.
    """

    report_date: datetime.datetime = Field(alias="reportDate")
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.

    Observed on: sector records.
    """

    report_title: str = Field(alias="reportTitle")
    """
    Prose report summary/abstract.

    Observed on: sector records.
    """

    report_type: str = Field(alias="reportType")
    """
    Report classification label; always ``"Analyst Report"`` in the
    corpus.

    Observed on: sector records.
    """

    target_price: float | None = Field(default=None, alias="targetPrice")
    """
    Analyst price target.

    A bare wire float, unlike this module's other ``target_price``-shaped
    fields (:class:`SectorCompany.target_price`), which are ``{raw, fmt}``
    wrapped; optional at the row level, per the same evidence as
    ``investment_rating``.

    Observed on: sector records.
    """

    target_price_status: str | None = Field(default=None, alias="targetPriceStatus")
    """
    Status of ``target_price`` (for example ``"Maintained"``).

    Optional at the row level, per the same evidence as
    ``investment_rating``.

    Observed on: sector records.
    """


class SectorResult(YahooModel):
    """The ``sector`` endpoint's ``data`` envelope payload."""

    industries: list[SectorIndustry]
    """
    Industry breakdown within this sector.

    Observed on: sector records.
    """

    key: str
    """
    URL-safe sector slug (for example ``"technology"``); the wire value
    for the ``sector`` path parameter.

    Observed on: sector records.
    """

    name: str
    """
    Sector display name (for example ``"Technology"``).

    Observed on: sector records.
    """

    overview: SectorOverview
    """
    Aggregate sector-level statistics.

    Observed on: sector records.
    """

    performance: SectorPerformance
    """
    This sector's own price-performance metrics.

    Observed on: sector records.
    """

    performance_overview_benchmark: SectorBenchmarkPerformance = Field(
        alias="performanceOverviewBenchmark"
    )
    """
    A benchmark index's price-performance metrics, for comparison (always
    the S&P 500 in the corpus).

    Observed on: sector records.
    """

    research_reports: list[SectorResearchReport] = Field(alias="researchReports")
    """
    Recent analyst research reports on companies within this sector.

    Observed on: sector records.
    """

    symbol: str
    """
    Yahoo symbol for this sector's tracking index (for example
    ``"^YH311"``).

    Observed on: sector records.
    """

    top_companies: list[SectorCompany] = Field(alias="topCompanies")
    """
    Largest companies by market weight within this sector.

    Observed on: sector records.
    """

    top_etfs: list[SectorFund] = Field(alias="topETFs")
    """
    Largest ETFs tracking this sector.

    Observed on: sector records.
    """

    top_mutual_funds: list[SectorFund] = Field(alias="topMutualFunds")
    """
    Largest mutual funds tracking this sector.

    Observed on: sector records.
    """
