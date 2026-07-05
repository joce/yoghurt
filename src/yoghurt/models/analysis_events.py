"""Typed models for the small symbol-bound analysis endpoints (batch 3d-1).

Reconciled against the probe corpus at ``tests/fixtures/corpus/``, captured
2026-07-04. Regenerate applicability evidence with
``uv run python -m tools.fields_report <stream>`` after a corpus refresh
(see ``tools/fields_report.py`` for the per-endpoint record streams this
evidence is built from). This module covers four of the six batch 3d-1
endpoints: ``calendar-events``, ``quote-type``, ``recommendations-by-symbol``,
and ``stock-recommender``. The remaining two (``price-insights``,
``insights``) live in the sibling :mod:`yoghurt.models.analysis_insights`;
see that module's docstring for the file-split rationale (both are deep,
prose-heavy AI/research payloads with their own large sub-model trees,
unlike this module's small, flat shapes).

**calendar-events** (endpoint noun: "calendar events"). The corpus is
thin and structurally lopsided: every default-module capture (24 symbols,
no ``--modules`` filter) is simply ``{"earnings": []}`` — Yahoo has no
earnings-calendar rows to report for any probed symbol right now — and
three additional AAPL captures each requested one non-default module in
isolation (``--modules economicEvents``, ``--modules ipoEvents``,
``--modules secReports``). ``ipoEvents``/``secReports`` are also empty in
their captures, so :class:`CalendarEventsResult`'s ``earnings``/
``ipo_events``/``sec_reports`` fields can only be typed as empty-observed
lists of an unmodeled row (:class:`UnmodeledCalendarRow`, the
``CorporateAction``-style empty-model precedent from
:class:`yoghurt.models.quote.CorporateAction`: no fields of its own, so the
corpus gate's nested-extras walker fails loudly the moment Yahoo finally
sends a populated row). ``economicEvents`` alone has a real, richly
populated capture (9 event rows across 2 day-buckets) and is fully typed via
:class:`EconomicEventDay`/:class:`EconomicEvent`. All four fields are
optional at the :class:`CalendarEventsResult` level: a request never shows
more than one module key populated at a time in this corpus (the default
request returns only ``earnings``; each ``--modules`` probe returns only
that one module's key), so there is no evidence either way for
multi-module requests, but nothing rules them out.

**quote-type** (endpoint noun: "quote-type records"). Rich, clean corpus:
23 valid captures spanning every ``QuoteType`` member captured elsewhere in
this codebase (EQUITY, ETF, MUTUALFUND, INDEX, CURRENCY, CRYPTOCURRENCY,
FUTURE, OPTION) plus the deliberate invalid-symbol probe (``ZZZZXYZQ``,
empty ``result: []`` — the only endpoint in this batch with a captured
empty-result shape; ``Ticker.quote_type()`` already raises
``SymbolNotFoundError`` for it and keeps doing so). Distinct from
:class:`~yoghurt.models.quote.Quote` and from
:class:`~yoghurt.models.summary_identity.SummaryQuoteType` (the
quote-summary ``quoteType`` module) per the plan's explicit instruction:
despite the near-identical field *names*, ``gmt_off_set_milliseconds`` is a
wire **string** here (``"28800000"``), not the numeric type
``SummaryQuoteType`` observes on its own endpoint — a genuine wire-shape
difference between endpoints, not a modeling inconsistency.

**recommendations-by-symbol** (endpoint noun: "recommendation records").
Small, clean, uniform corpus (4 captures, 20 total recommended-symbol rows,
every row carrying the same two fields).

**stock-recommender** (endpoint noun: "stock-recommender records"). A bare
(non-enveloped) payload, distinct in shape from every other endpoint in this
batch: ``pathId``/``id`` sit at the top level alongside a single ``fields``
object carrying the actual related-tickers payload. 3 captures, uniform
shape.
"""

from __future__ import annotations

import datetime  # noqa: TC003 - pydantic needs this at runtime to resolve annotations

from pydantic import Field

from yoghurt.models._base import YahooModel
from yoghurt.models.enums import QuoteType  # noqa: TC001


class UnmodeledCalendarRow(YahooModel):
    """One row of ``earnings``/``ipoEvents``/``secReports``, shape unknown.

    No corpus capture has ever populated any of these three lists; this
    carries no fields of its own beyond what :class:`YahooModel` preserves
    via ``model_extra`` until a populated example is captured, mirroring
    the :class:`~yoghurt.models.quote.CorporateAction` precedent — the
    corpus coverage gate's nested-extras walker fails loudly the moment
    Yahoo sends a populated row.

    Observed only as empty lists in the corpus.
    """


class EconomicEvent(YahooModel):
    """One economic-indicator release in an :class:`EconomicEventDay`."""

    actual: str
    """
    Reported value for this release, as Yahoo's wire string (for example
    ``"57"``, ``"0.3"``).

    Observed on: calendar events.
    """

    country_code: str
    """
    ISO-ish country or region code the release applies to (for example
    ``"US"``, ``"EU"``, ``"JP"``).

    Observed on: calendar events.
    """

    description: str
    """
    Prose explanation of what this economic indicator measures.

    Observed on: calendar events.
    """

    economic_events: bool
    """
    Always ``true`` on every corpus row; a type-discriminator flag rather
    than a meaningful per-row value.

    Observed on: calendar events.
    """

    event: str
    """
    Name of the economic release (for example ``"Non-Farm Payrolls"``,
    ``"CPI YY"``).

    Observed on: calendar events.
    """

    event_time: datetime.datetime
    """
    Point-in-time release timestamp.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime. The parent :class:`EconomicEventDay` carries an IANA
    ``timezone`` name, but it is not threaded onto this row.

    Observed on: calendar events.
    """

    period: str
    """
    Reporting period the release covers (for example ``"Jun"``, ``"May"``).

    Observed on: calendar events.
    """

    prior: str
    """
    Previously reported value for this release, as Yahoo's wire string.

    Observed on: calendar events.
    """

    revised_from: str | None = None
    """
    Prior value before revision, when this release revised an earlier
    reading.

    Present on 2 of 9 corpus rows.

    Observed on: calendar events.
    """


class EconomicEventDay(YahooModel):
    """One calendar day's bucket of :class:`EconomicEvent` releases."""

    count: int
    """
    Number of releases in ``records`` for this day.

    Observed on: calendar events.
    """

    records: list[EconomicEvent]
    """
    Economic releases scheduled or reported for this day.

    Observed on: calendar events.
    """

    timestamp: datetime.datetime
    """
    Point-in-time timestamp for this day bucket.

    Wire value is epoch milliseconds; pydantic converts it to an aware UTC
    datetime. Matches ``timestamp_string``'s calendar date in the
    ``timezone`` local zone, not necessarily in UTC (verified against
    every corpus value); see ``timestamp_string`` for the authoritative
    calendar date.

    Observed on: calendar events.
    """

    timestamp_string: str
    """
    Calendar date for this bucket, as a bare ``"YYYY-MM-DD"`` string in the
    ``timezone`` local zone.

    Observed on: calendar events.
    """

    timezone: str
    """
    IANA timezone name ``timestamp``/``timestamp_string`` are local to (for
    example ``"America/New_York"``).

    Observed on: calendar events.
    """

    total_count: int
    """
    Total number of releases for this day, matching ``count`` on every
    corpus row (verified); kept as its own wire field rather than
    collapsed, per corpus honesty.

    Observed on: calendar events.
    """


class CalendarEventsResult(YahooModel):
    """The ``calendar-events`` endpoint's ``finance.result`` payload.

    Every field is optional: no corpus capture ever populates more than one
    module key at once (the default request returns only ``earnings``; each
    ``--modules`` probe returns only that one requested module's key). See
    the module docstring for the thin-evidence caveat on
    ``earnings``/``ipo_events``/``sec_reports``.
    """

    earnings: list[UnmodeledCalendarRow] | None = None
    """
    Earnings-calendar events for this symbol.

    Always an empty list in the corpus (the default, no-``--modules``
    request); see :class:`UnmodeledCalendarRow`.

    Observed on: calendar events.
    """

    economic_events: list[EconomicEventDay] | None = Field(
        default=None, alias="economicEvents"
    )
    """
    Economic-indicator release events, bucketed by day.

    Only requested (and only ever captured) via ``--modules
    economicEvents``; see :class:`EconomicEventDay`.

    Observed on: calendar events.
    """

    ipo_events: list[UnmodeledCalendarRow] | None = Field(
        default=None, alias="ipoEvents"
    )
    """
    IPO-calendar events for this symbol.

    Always an empty list in the corpus (only requested via ``--modules
    ipoEvents``); see :class:`UnmodeledCalendarRow`.

    Observed on: calendar events.
    """

    sec_reports: list[UnmodeledCalendarRow] | None = Field(
        default=None, alias="secReports"
    )
    """
    SEC filing events for this symbol.

    Always an empty list in the corpus (only requested via ``--modules
    secReports``); see :class:`UnmodeledCalendarRow`. Distinct from
    :class:`~yoghurt.models.analysis_insights.InsightsSecReport` (the
    ``insights`` endpoint's differently-shaped SEC filing rows) — no
    corpus evidence ties the two shapes together.

    Observed on: calendar events.
    """


class QuoteTypeResult(YahooModel):
    """The ``quote-type`` endpoint's single result record.

    Distinct from :class:`~yoghurt.models.quote.Quote` and from
    :class:`~yoghurt.models.summary_identity.SummaryQuoteType`; see the
    module docstring for the ``gmt_off_set_milliseconds`` wire-type
    divergence that rules out reuse.
    """

    exchange: str
    """
    Short code of the securities exchange (for example ``"NMS"``,
    ``"TOR"``, ``"CCC"``).

    Observed on: quote-type records.
    """

    exchange_timezone_name: str
    """
    IANA timezone name of the exchange (for example
    ``"America/New_York"``).

    Observed on: quote-type records.
    """

    exchange_timezone_short_name: str
    """
    Short abbreviation of the exchange timezone (for example ``"EDT"``,
    ``"JST"``).

    Observed on: quote-type records.
    """

    gmt_off_set_milliseconds: str
    """
    Offset from GMT of the exchange, in milliseconds, as a wire string (for
    example ``"-14400000"``).

    A string on this endpoint, unlike the numeric
    ``SummaryQuoteType.gmt_off_set_milliseconds``; see the module
    docstring.

    Observed on: quote-type records.
    """

    has_selerity_earnings: bool
    """
    Whether Yahoo has Selerity-sourced earnings data for this symbol.

    Observed on: quote-type records.
    """

    head_symbol: str | None = None
    """
    Root contract symbol for a futures continuation (for example
    ``"CL=F"``).

    Present only on FUTURE records.

    Observed on: quote-type records.
    """

    is_esg_populated: bool
    """
    Whether Yahoo has ESG (environmental/social/governance) data for this
    symbol.

    Always ``false`` in the corpus.

    Observed on: quote-type records.
    """

    long_name: str | None = None
    """
    Official long name of the company or security.

    Absent on CRYPTOCURRENCY, FUTURE, and OPTION records in the corpus.

    Observed on: quote-type records.
    """

    market: str
    """
    Yahoo's internal market-segment identifier (for example
    ``"us_ot_market"``, ``"ca_market"``).

    Observed on: quote-type records.
    """

    message_board_id: str | None = None
    """
    Identifier for the Yahoo! Finance message board for this security.

    Absent on FUTURE and OPTION records in the corpus.

    Observed on: quote-type records.
    """

    quartr_id: str | None = None
    """
    Quartr platform identifier for this company, when available.

    Present on 9 of 23 corpus records (EQUITY only).

    Observed on: quote-type records.
    """

    quote_type: QuoteType
    """
    Classification of this instrument.

    Observed on: quote-type records.
    """

    selerity_is_gaap: bool
    """
    Whether Yahoo's Selerity-sourced earnings data for this symbol is
    GAAP-based.

    Observed on: quote-type records.
    """

    short_name: str
    """
    Short display name of the company or security.

    Observed on: quote-type records.
    """

    symbol: str
    """
    Yahoo ticker symbol.

    Observed on: quote-type records.
    """

    underlying_exchange_symbol: str | None = None
    """
    Exchange-qualified symbol of the underlying contract (for example
    ``"CLQ26.NYM"``).

    Present only on FUTURE records.

    Observed on: quote-type records.
    """

    underlying_symbol: str | None = None
    """
    Symbol of the underlying security or continuation contract.

    Present on FUTURE and OPTION records.

    Observed on: quote-type records.
    """


class RecommendedSymbol(YahooModel):
    """One related-symbol row in a :class:`RecommendationsResult`."""

    score: float
    """
    Relatedness score for this recommendation (higher is more related).

    Observed on: recommendation records.
    """

    symbol: str
    """
    Yahoo ticker symbol of the recommended, related security.

    Observed on: recommendation records.
    """


class RecommendationsResult(YahooModel):
    """The ``recommendations-by-symbol`` endpoint's single result record."""

    recommended_symbols: list[RecommendedSymbol]
    """
    Related symbols, most related first.

    Observed on: recommendation records.
    """

    symbol: str
    """
    Yahoo ticker symbol the recommendations were requested for.

    Observed on: recommendation records.
    """


class StockRecommenderFields(YahooModel):
    """The ``fields`` block of a :class:`StockRecommenderResult`."""

    entity_type: str
    """
    Entity classification for this document (always ``"ticker"`` in the
    corpus).

    Observed on: stock-recommender records.
    """

    id: str
    """
    Entity identifier (for example ``"ticker:AAPL"``).

    Observed on: stock-recommender records.
    """

    related_tickers: list[str]
    """
    Related ticker symbols, in Yahoo's returned order.

    Observed on: stock-recommender records.
    """

    related_tickers_ts: datetime.datetime
    """
    Point-in-time timestamp the related-tickers list was computed at.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime.

    Observed on: stock-recommender records.
    """


class StockRecommenderResult(YahooModel):
    """The ``stock-recommender`` endpoint's bare (non-enveloped) payload."""

    fields: StockRecommenderFields
    """
    The related-tickers payload for this symbol.

    Observed on: stock-recommender records.
    """

    id: str
    """
    Full document identifier (for example
    ``"id:entity:entity::ticker:AAPL"``).

    Observed on: stock-recommender records.
    """

    path_id: str = Field(alias="pathId")
    """
    Document path identifier (for example
    ``"/document/v1/entity/entity/docid/ticker:AAPL"``).

    Observed on: stock-recommender records.
    """
