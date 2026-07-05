"""Typed models for the small symbol-bound analysis endpoints (batch 3d-1).

Reconciled against the probe corpus at ``tests/fixtures/corpus/``, captured
2026-07-04 and extended 2026-07-05 with 18 windowed calendar-events
captures (15 populated + 3 split-hypothesis negative evidence; see below).
Regenerate applicability evidence with
``uv run python -m tools.fields_report <stream>`` after a corpus refresh
(see ``tools/fields_report.py`` for the per-endpoint record streams this
evidence is built from). This module covers four of the six batch 3d-1
endpoints: ``calendar-events``, ``quote-type``, ``recommendations-by-symbol``,
and ``stock-recommender``. The remaining two (``price-insights``,
``insights``) live in the sibling :mod:`yoghurt.models.analysis_insights`;
see that module's docstring for the file-split rationale (both are deep,
prose-heavy AI/research payloads with their own large sub-model trees,
unlike this module's small, flat shapes).

**calendar-events** (endpoint noun: "calendar events"). The original
2026-07-04 corpus was thin and structurally lopsided: every default-module
capture (24 symbols, no ``--modules`` filter, no ``--start-date``/
``--end-date``) was simply ``{"earnings": []}``, and three additional AAPL
captures each requested one non-default module in isolation — all also
empty except ``economicEvents``. That thinness turned out to be a probing
gap, not an endpoint limitation: the endpoint needs an explicit
``--start-date``/``--end-date`` window covering a day with real events;
the default (window-less, ``now-3d``..``now``) request has simply never
landed on such a day. Live UI cross-checking (2026-07-05) found real
windows for all three, since surgically captured (18 new files, per the
978eead precedent):

- ``earnings``: 4 small/mid-cap same-day reporters (``IVF``, ``HAWK``,
  ``EBF``, ``POWW``, all 2026-06-22) plus ``MSFT`` (2026-04-29, a
  materially larger ``rank``) populate one record each. Fully typed via
  :class:`EarningsEventDay`/:class:`EarningsEvent`; all 13 row fields are
  present on all 5 records.
- ``ipoEvents``: 6 same-day (2026-07-02) pricings spanning common stock
  (``COPR``, ``SECZ``), rights (``GSRVR``), warrants (``IQMXW``), units
  (``MIACU``), and ADSs (``VCRE``) populate one record each. Fully typed
  via :class:`IpoEventDay`/:class:`IpoEvent`; ``currency_name`` is a
  required key that is sometimes an empty string (``COPR``, ``SECZ``)
  rather than absent.
- ``secReports``: resolves a competing live hypothesis. The CLI help text
  ("SEC filing events (10-K, 10-Q, 8-K, etc.)") predates any real capture;
  a live UI check separately suggested this module might instead carry
  stock-split events. Both were tested and both are now corpus evidence:
  three split-day symbols (``BEOB``, ``CATTF``, ``6669.TW``) committed as
  ``*_secReports_split.json``, each a byte-for-byte empty ``{"secReports":
  []}`` over their known split window (2026-06-21/27) — ruling out the
  split hypothesis — while filing-heavy symbols over their known filing
  windows populated real 10-Q/8-K/DEFA14A rows (``BOXL``, ``HAWK``:
  2026-06-20/27; ``AAPL``: 2026-04-20/05-05, 3 day-buckets; ``MSFT``:
  2026-04-26/05-05, a same-day 10-Q+8-K bucket) — confirming the help
  text's description. Fully typed via
  :class:`SecReportDay`/:class:`SecReport`/:class:`SecReportExhibit`; all
  10 row fields (including the nested ``exhibits`` list) are present on
  all 9 filing records across the 4 populated captures. Wire quirk: the
  day-bucket's ``timestampString`` consistently sits one calendar day
  *before* its rows' ``filingDate`` (every MSFT/AAPL bucket in the
  corpus) — the two fields do not agree, and each is typed for what it
  individually says.

All three newly-typed fields, plus ``economicEvents``, remain optional at
the :class:`CalendarEventsResult` level: no single capture (old or new)
ever populates more than one module key at once (the default request
returns only ``earnings``; each ``--modules`` probe returns only that one
module's key), so there is no evidence either way for multi-module
requests, but nothing rules them out. The deliberate invalid-symbol probe
(``ZZZZXYZQ``, window-less) is likewise ``{"earnings": []}`` — byte-for-byte
the same valid-empty shape as an unremarkable symbol with no scheduled
events, not an error; ``Ticker.calendar_events()`` returns a normally-typed
(all-optional) result rather than raising, confirmed live 2026-07-05.

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
Small, clean, uniform corpus: 9 captures (EQUITY_SUBSET + ``^GSPC`` +
cross-asset ``SPY``/``BTC-USD``/``EURUSD=X``/``ES=F`` + the deliberate
``ZZZZXYZQ`` invalid-symbol probe), 7 populated records, 35 total
recommended-symbol rows, every row carrying the same two fields. Two of the
9 captures (``ES=F``, ``ZZZZXYZQ``) are a valid-but-empty ``{"result":
[]}`` shape rather than an error — corpus-confirmed 2026-07-05 for the
live-observed "some instrument types have no recommendations to report"
behavior documented on :meth:`~yoghurt.api.Ticker.recommendations`; both
surface identically as a ``RecommendationsResult`` model-validation
failure (``recommendedSymbols``/``symbol`` missing from ``{}``), mapped to
``YahooApiError(code="model-validation")``.

**stock-recommender** (endpoint noun: "stock-recommender records"). A bare
(non-enveloped) payload, distinct in shape from every other endpoint in this
batch: ``pathId``/``id`` sit at the top level alongside a single ``fields``
object carrying the actual related-tickers payload. 3 populated captures,
uniform shape, plus the deliberate ``ZZZZXYZQ`` invalid-symbol probe (a
4th file, excluded from :func:`~tools.fields_report.stock_recommender_records`):
unlike every other endpoint in this batch, its 404 body is
``{"message": "Not Found"}`` — no ``detail`` key — so
``yoghurt._core.map_http_error`` cannot map it to ``SymbolNotFoundError``
or any other typed error; it is truly unmappable and propagates as a bare
``YahooRequestError``, confirmed live 2026-07-05.
"""

from __future__ import annotations

import datetime  # noqa: TC003 - pydantic needs this at runtime to resolve annotations

from pydantic import Field

from yoghurt.models._base import YahooModel
from yoghurt.models.enums import QuoteType  # noqa: TC001


class EarningsEvent(YahooModel):
    """One earnings-release row in an :class:`EarningsEventDay`."""

    company_short_name: str
    """
    Short display name of the reporting company.
    """

    date_is_estimate: bool
    """
    Whether ``start_date_time`` is an estimate rather than a confirmed date.

    Always ``false`` on every corpus row (all captured rows are already-
    reported, confirmed dates).
    """

    earnings: bool
    """
    Always ``true`` on every corpus row; a type-discriminator flag rather
    than a meaningful per-row value.
    """

    eps_actual: float
    """
    Reported actual earnings per share.
    """

    eps_estimate: float
    """
    Consensus analyst earnings-per-share estimate ahead of the release.
    """

    fiscal_year: str
    """
    Fiscal year this release covers, as Yahoo's wire string (for example
    ``"2026"``).
    """

    gmt_offset_milliseconds: int = Field(alias="gmtOffsetMilliSeconds")
    """
    Offset from GMT of the reporting exchange, in milliseconds.

    Irregular wire spelling: ``gmtOffsetMilliSeconds`` (lowercase "offset",
    capital "S" in "MilliSeconds") — a different capitalization from
    ``QuoteTypeResult.gmt_off_set_milliseconds``'s ``gmtOffSetMilliseconds``
    (and that field is a wire string, not this numeric type); genuine
    per-endpoint wire divergence, not a modeling inconsistency.
    """

    quarter: str
    """
    Fiscal quarter this release covers (for example ``"Q1"``, ``"Q4"``).
    """

    rank: int
    """
    Yahoo's internal ranking/priority value for this release.
    """

    start_date_time: datetime.datetime
    """
    Point-in-time timestamp of the earnings release.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime. The parent :class:`EarningsEventDay` carries an IANA
    ``timezone`` name, but it is not threaded onto this row (same
    convention as :class:`EconomicEvent`'s ``event_time``).
    """

    start_date_time_type: str
    """
    Yahoo's classification of ``start_date_time``'s precision or session
    (always ``"TAS"`` — time-as-supplied — on every corpus row).
    """

    surprise_percent: float
    """
    Percentage difference between ``eps_actual`` and ``eps_estimate``.
    """

    ticker: str
    """
    Yahoo ticker symbol this release belongs to.
    """


class EarningsEventDay(YahooModel):
    """One calendar day's bucket of :class:`EarningsEvent` releases.

    Same wrapper shape as :class:`EconomicEventDay`.
    """

    count: int
    """
    Number of releases in ``records`` for this day.
    """

    records: list[EarningsEvent]
    """
    Earnings releases scheduled or reported for this day.
    """

    timestamp: datetime.datetime
    """
    Point-in-time timestamp for this day bucket.

    Wire value is epoch milliseconds; pydantic converts it to an aware UTC
    datetime.
    """

    timestamp_string: str
    """
    Calendar date for this bucket, as a bare ``"YYYY-MM-DD"`` string in the
    ``timezone`` local zone.
    """

    timezone: str
    """
    IANA timezone name ``timestamp``/``timestamp_string`` are local to (for
    example ``"America/New_York"``).
    """

    total_count: int
    """
    Total number of releases for this day, matching ``count`` on every
    corpus row (verified).
    """


class IpoEvent(YahooModel):
    """One IPO-pricing row in an :class:`IpoEventDay`."""

    company_short_name: str
    """
    Short display name of the company going public.
    """

    currency_name: str
    """
    Currency code of the deal (for example ``"USD"``).

    Present as an empty string on some corpus rows (for example a NYSE
    American common-stock pricing) rather than absent; still a required
    key on every row.
    """

    deal_id: str
    """
    Yahoo's internal identifier for this IPO deal.
    """

    deal_type: str
    """
    Status of the deal (``"Expected"`` on every corpus row).
    """

    exchange_short_name: str
    """
    Short name of the listing exchange (for example ``"Nasdaq"``, ``"NYSE
    American"``).
    """

    ipo_events: bool
    """
    Always ``true`` on every corpus row; a type-discriminator flag rather
    than a meaningful per-row value.
    """

    start_date_time: datetime.datetime
    """
    Point-in-time timestamp of the IPO pricing.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime. Matches the parent :class:`IpoEventDay`'s own ``timestamp``
    on every corpus row (verified), but kept as its own field since nothing
    in the corpus rules out the two ever diverging. The parent's IANA
    ``timezone`` is not threaded onto this row (same convention as
    :class:`EconomicEvent`'s ``event_time``).
    """

    ticker: str
    """
    Yahoo ticker symbol of the security being priced (for example a rights,
    warrants, or units symbol distinct from the parent company's common
    stock).
    """


class IpoEventDay(YahooModel):
    """One calendar day's bucket of :class:`IpoEvent` pricings.

    Same wrapper shape as :class:`EconomicEventDay`.
    """

    count: int
    """
    Number of pricings in ``records`` for this day.
    """

    records: list[IpoEvent]
    """
    IPO pricings scheduled or completed for this day.
    """

    timestamp: datetime.datetime
    """
    Point-in-time timestamp for this day bucket.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime.
    """

    timestamp_string: str
    """
    Calendar date for this bucket, as a bare ``"YYYY-MM-DD"`` string in the
    ``timezone`` local zone.
    """

    timezone: str
    """
    IANA timezone name ``timestamp``/``timestamp_string`` are local to (for
    example ``"America/New_York"``).
    """

    total_count: int
    """
    Total number of pricings for this day, matching ``count`` on every
    corpus row (verified).
    """


class SecReportExhibit(YahooModel):
    """One entry in a :class:`SecReport`'s ``exhibits`` list.

    Distinct from
    :class:`~yoghurt.models.analysis_insights.InsightsSecReportExhibit`
    (the ``insights`` endpoint's differently-shaped exhibit rows, which
    additionally carry an optional ``downloadUrl``) — no corpus evidence
    ties the two shapes together.
    """

    type: str
    """
    Exhibit type or form code (for example ``"8-K"``, ``"EX-99.1"``).
    """

    url: str
    """
    URL of the exhibit document.
    """


class SecReport(YahooModel):
    """One SEC-filing row in a :class:`SecReportDay`.

    Distinct from
    :class:`~yoghurt.models.analysis_insights.InsightsSecReport` (the
    ``insights`` endpoint's differently-shaped SEC filing rows: ``edgarUrl``/
    ``formType``/no ``category`` or ``thumbnailUrl``) — no corpus evidence
    ties the two shapes together.
    """

    category: str
    """
    Yahoo's category label for this filing (for example ``"Periodic
    Financial Reports"``, ``"Corporate Changes & Voting Matters"``,
    ``"Proxy Statements"``).
    """

    company_name: str
    """
    Full name of the filing company.
    """

    description: str
    """
    Prose description of this filing (for example ``"Quarterly report
    pursuant to Section 13 or 15(d)"``).
    """

    exhibits: list[SecReportExhibit]
    """
    Individual documents attached to this filing.
    """

    filing_date: datetime.date
    """
    Calendar date the filing was made.

    Wire value is a midnight-UTC-aligned epoch timestamp in milliseconds
    (verified against every corpus value); pydantic converts it to a UTC
    calendar date.
    """

    id: str
    """
    Yahoo's internal identifier for this filing (for example
    ``"0001213900-26-070452_1624512"``).
    """

    sec_reports: bool = Field(alias="secReports")
    """
    Always ``true`` on every corpus row; a type-discriminator flag rather
    than a meaningful per-row value.
    """

    thumbnail_url: str
    """
    URL of a thumbnail image representing this filing.
    """

    ticker: str
    """
    Yahoo ticker symbol this filing belongs to.
    """

    type: str
    """
    SEC form type of this filing (for example ``"10-Q"``, ``"8-K"``,
    ``"DEFA14A"``).
    """


class SecReportDay(YahooModel):
    """One calendar day's bucket of :class:`SecReport` filings.

    Same wrapper shape as :class:`EconomicEventDay`.
    """

    count: int
    """
    Number of filings in ``records`` for this day.
    """

    records: list[SecReport]
    """
    SEC filings made on this day.
    """

    timestamp: datetime.datetime
    """
    Point-in-time timestamp for this day bucket.

    Wire value is epoch milliseconds; pydantic converts it to an aware UTC
    datetime.
    """

    timestamp_string: str
    """
    Calendar date for this bucket, as a bare ``"YYYY-MM-DD"`` string in the
    ``timezone`` local zone.
    """

    timezone: str
    """
    IANA timezone name ``timestamp``/``timestamp_string`` are local to (for
    example ``"America/New_York"``).
    """

    total_count: int
    """
    Total number of filings for this day, matching ``count`` on every
    corpus row (verified).
    """


class EconomicEvent(YahooModel):
    """One economic-indicator release in an :class:`EconomicEventDay`."""

    actual: str | None = None
    """
    Reported value for this release, as Yahoo's wire string (for example
    ``"57"``, ``"0.3"``).

    Live-observed as absent on not-yet-released events (June trade-figure
    releases still pending publication, 2026-07-05); not yet backed by a
    corpus capture — every committed corpus row carries it.
    """

    country_code: str
    """
    ISO-ish country or region code the release applies to (for example
    ``"US"``, ``"EU"``, ``"JP"``).
    """

    description: str
    """
    Prose explanation of what this economic indicator measures.
    """

    economic_events: bool
    """
    Always ``true`` on every corpus row; a type-discriminator flag rather
    than a meaningful per-row value.
    """

    event: str
    """
    Name of the economic release (for example ``"Non-Farm Payrolls"``,
    ``"CPI YY"``).
    """

    event_time: datetime.datetime
    """
    Point-in-time release timestamp.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime. The parent :class:`EconomicEventDay` carries an IANA
    ``timezone`` name, but it is not threaded onto this row.
    """

    period: str
    """
    Reporting period the release covers (for example ``"Jun"``, ``"May"``).
    """

    prior: str
    """
    Previously reported value for this release, as Yahoo's wire string.
    """

    revised_from: str | None = None
    """
    Prior value before revision, when this release revised an earlier
    reading.

    Present on 2 of 9 corpus rows.
    """


class EconomicEventDay(YahooModel):
    """One calendar day's bucket of :class:`EconomicEvent` releases."""

    count: int
    """
    Number of releases in ``records`` for this day.
    """

    records: list[EconomicEvent]
    """
    Economic releases scheduled or reported for this day.
    """

    timestamp: datetime.datetime
    """
    Point-in-time timestamp for this day bucket.

    Wire value is epoch milliseconds; pydantic converts it to an aware UTC
    datetime. Matches ``timestamp_string``'s calendar date in the
    ``timezone`` local zone, not necessarily in UTC (verified against
    every corpus value); see ``timestamp_string`` for the authoritative
    calendar date.
    """

    timestamp_string: str
    """
    Calendar date for this bucket, as a bare ``"YYYY-MM-DD"`` string in the
    ``timezone`` local zone.
    """

    timezone: str
    """
    IANA timezone name ``timestamp``/``timestamp_string`` are local to (for
    example ``"America/New_York"``).
    """

    total_count: int
    """
    Total number of releases for this day, matching ``count`` on every
    corpus row (verified); kept as its own wire field rather than
    collapsed, per corpus honesty.
    """


class CalendarEventsResult(YahooModel):
    """The ``calendar-events`` endpoint's ``finance.result`` payload.

    Every field is optional: no corpus capture ever populates more than one
    module key at once (the default request returns only ``earnings``; each
    ``--modules`` probe returns only that one requested module's key). See
    the module docstring for how ``earnings``/``ipo_events``/``sec_reports``
    were finally populated — they need an explicit ``--start-date``/
    ``--end-date`` window over a day with real events; the default
    (window-less) request is always empty for all three.
    """

    earnings: list[EarningsEventDay] | None = None
    """
    Earnings-calendar events for this symbol, bucketed by day.

    Empty list on the default request (no window covers a real earnings
    day); populated when ``--start-date``/``--end-date`` cover a day the
    symbol actually reported on. See :class:`EarningsEventDay`.
    """

    economic_events: list[EconomicEventDay] | None = Field(
        default=None, alias="economicEvents"
    )
    """
    Economic-indicator release events, bucketed by day.

    Only requested (and only ever captured) via ``--modules
    economicEvents``; see :class:`EconomicEventDay`.
    """

    ipo_events: list[IpoEventDay] | None = Field(default=None, alias="ipoEvents")
    """
    IPO-calendar events for this symbol, bucketed by day.

    Empty list on the default request; populated when ``--start-date``/
    ``--end-date`` cover a day the symbol actually priced on. See
    :class:`IpoEventDay`.
    """

    sec_reports: list[SecReportDay] | None = Field(default=None, alias="secReports")
    """
    SEC filing events for this symbol, bucketed by day.

    Empty list on the default request; populated when ``--start-date``/
    ``--end-date`` cover a day the symbol actually filed on. Confirms the
    CLI help text's "SEC filing events (10-K, 10-Q, 8-K, etc.)" description
    against real 10-Q/8-K/DEFA14A rows — a live hypothesis that this module
    instead carried stock-split events did not hold up (split-day symbols
    BEOB/CATTF/6669.TW captured empty ``secReports`` on retest, 2026-07-05).
    Distinct from :class:`~yoghurt.models.analysis_insights.InsightsSecReport`
    (the ``insights`` endpoint's differently-shaped SEC filing rows) — no
    corpus evidence ties the two shapes together. See :class:`SecReportDay`.
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
    """

    exchange_timezone_name: str
    """
    IANA timezone name of the exchange (for example
    ``"America/New_York"``).
    """

    exchange_timezone_short_name: str
    """
    Short abbreviation of the exchange timezone (for example ``"EDT"``,
    ``"JST"``).
    """

    gmt_off_set_milliseconds: str
    """
    Offset from GMT of the exchange, in milliseconds, as a wire string (for
    example ``"-14400000"``).

    A string on this endpoint, unlike the numeric
    ``SummaryQuoteType.gmt_off_set_milliseconds``; see the module
    docstring.
    """

    has_selerity_earnings: bool
    """
    Whether Yahoo has Selerity-sourced earnings data for this symbol.
    """

    head_symbol: str | None = None
    """
    Root contract symbol for a futures continuation (for example
    ``"CL=F"``).

    Present only on FUTURE records.
    """

    is_esg_populated: bool
    """
    Whether Yahoo has ESG (environmental/social/governance) data for this
    symbol.

    Always ``false`` in the corpus.
    """

    long_name: str | None = None
    """
    Official long name of the company or security.

    Absent on CRYPTOCURRENCY, FUTURE, and OPTION records in the corpus.
    """

    market: str
    """
    Yahoo's internal market-segment identifier (for example
    ``"us_ot_market"``, ``"ca_market"``).
    """

    message_board_id: str | None = None
    """
    Identifier for the Yahoo! Finance message board for this security.

    Absent on FUTURE and OPTION records in the corpus.
    """

    quartr_id: str | None = None
    """
    Quartr platform identifier for this company, when available.

    Present on 9 of 23 corpus records (EQUITY only).
    """

    quote_type: QuoteType
    """
    Classification of this instrument.
    """

    selerity_is_gaap: bool
    """
    Whether Yahoo's Selerity-sourced earnings data for this symbol is
    GAAP-based.
    """

    short_name: str
    """
    Short display name of the company or security.
    """

    symbol: str
    """
    Yahoo ticker symbol.
    """

    underlying_exchange_symbol: str | None = None
    """
    Exchange-qualified symbol of the underlying contract (for example
    ``"CLQ26.NYM"``).

    Present only on FUTURE records.
    """

    underlying_symbol: str | None = None
    """
    Symbol of the underlying security or continuation contract.

    Present on FUTURE and OPTION records.
    """


class RecommendedSymbol(YahooModel):
    """One related-symbol row in a :class:`RecommendationsResult`."""

    score: float
    """
    Relatedness score for this recommendation (higher is more related).
    """

    symbol: str
    """
    Yahoo ticker symbol of the recommended, related security.
    """


class RecommendationsResult(YahooModel):
    """The ``recommendations-by-symbol`` endpoint's single result record."""

    recommended_symbols: list[RecommendedSymbol]
    """
    Related symbols, most related first.
    """

    symbol: str
    """
    Yahoo ticker symbol the recommendations were requested for.
    """


class StockRecommenderFields(YahooModel):
    """The ``fields`` block of a :class:`StockRecommenderResult`."""

    entity_type: str
    """
    Entity classification for this document (always ``"ticker"`` in the
    corpus).
    """

    id: str
    """
    Entity identifier (for example ``"ticker:AAPL"``).
    """

    related_tickers: list[str]
    """
    Related ticker symbols, in Yahoo's returned order.
    """

    related_tickers_ts: datetime.datetime
    """
    Point-in-time timestamp the related-tickers list was computed at.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime.
    """


class StockRecommenderResult(YahooModel):
    """The ``stock-recommender`` endpoint's bare (non-enveloped) payload."""

    fields: StockRecommenderFields
    """
    The related-tickers payload for this symbol.
    """

    id: str
    """
    Full document identifier (for example
    ``"id:entity:entity::ticker:AAPL"``).
    """

    path_id: str = Field(alias="pathId")
    """
    Document path identifier (for example
    ``"/document/v1/entity/entity/docid/ticker:AAPL"``).
    """
