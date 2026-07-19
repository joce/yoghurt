"""Typed models for the screener-metadata endpoints (batch 3e-2, final).

Reconciled against the probe corpus at ``tests/fixtures/corpus/``, captured
2026-07-04. Regenerate applicability evidence with
``uv run python -m tools.fields_report <stream>`` after a corpus refresh
(see ``tools/fields_report.py`` for the per-endpoint record streams this
evidence is built from). This module covers three of batch 3e-2's four
endpoints: ``screener-instrument-fields``, ``timeseries-fields``, and
``screener-discover``. The fourth, ``screener-predefined``, is flipped in
``api.py`` but deliberately NOT modeled here beyond its envelope-level
metadata fields — see that section's docstring below for why.

**screener-instrument-fields** (endpoint noun: "screener instrument
fields"). The richest evidence in this whole family: 21 instrument
captures (``equity``, ``etf``, ``mutualfund``, ``cryptocurrency``,
``currency``, ``future``, ``index``, ``option``, ``bond``, ``commodity``,
``economic_event``, ``insider_transaction``, ``institutional_holdings``,
``institutional_interest``, ``ipo_info``, ``research_reports``,
``splits``, ``trade_idea``, ``tradingcentral_event_info``,
``analyst_ratings``, ``warrant``), 1666 field specs total.
``ScreenerInstrumentFieldsResult`` models the ``finance.result[0]``
envelope: a single ``fields`` mapping keyed by Yahoo's field id (for
example ``"beta"``, ``"peratio.lasttwelvemonths"``), each value a
:class:`ScreenerField`. Every one of ``ScreenerField``'s own top-level
keys (``fieldId``/``category``/``labels``/``type``/``deprecated``/
``displayName``/``dropdownSupported``/``sortable``/``isPremium``) is
universal across all 1666 specs; ``enableSearch``/``searchSource``
(17/1666, spread across 12 instruments including ``equity``/``etf``/
``mutualfund``/``analyst_ratings``) and ``dependFor``/``dependentField``
(7 and 5 of 1666, spread across 7 and 5 instruments respectively — each
instrument's own ``sector``/``industry`` field pair cross-referencing
itself) are genuinely rare and modeled optional. ``category`` is a
nested ``{categoryId, displayName}`` object
(48 distinct category ids observed), not a bare string. ``type`` is a
closed 4-value vocabulary (NUMBER/STRING/DATE/BOOLEAN, all observed) typed
as :class:`ScreenerFieldType`. Each :class:`ScreenerFieldLabel` is one
quick-pick filter chip Yahoo's screener UI offers for that field; its
nested :class:`ScreenerFieldCriteria` carries an ``operator`` (closed
5-value vocabulary EQ/BTWN/GTE/GT/LT, typed :class:`ScreenerCriteriaOperator`)
and ``operands`` — a heterogeneous list whose first element is always the
field id (a string) followed by zero or more numeric/string comparison
values depending on the operator (``BTWN`` sends two bounds, ``EQ`` on an
enum field sends the option's own string value), so it is typed
``list[str | float]`` rather than a fixed-arity tuple.
``dependentFilterLabel`` is nullable at the label level (present as a
string on 725 of 3597 corpus labels, ``None`` on the rest — a
dependent-field UI hint, not evidence of a wire-key applicability gap).

**timeseries-fields** (endpoint noun: "timeseries field classes"). A
single, thin capture. ``TimeseriesFieldsResult`` models the
``timeseriesfields.result[0]`` envelope: one ``timeSeriesDataClass`` list
of :class:`TimeseriesFieldClass` rows (``displayName``/``dataType``, both
universal across the 13-row single capture).

**screener-discover** (endpoint noun: "screener-discover records").
A single capture under the ``finance`` envelope (see ``_core.ENVELOPES``).
``ScreenerDiscoverResult`` models ``finance.result`` directly (not a
list — distinct from every ``finance.result[]``-shaped endpoint modeled
elsewhere): a ``sections`` mapping (only the ``neo_investment_ideas`` key
ever observed, modeled as a dedicated
:class:`ScreenerDiscoverSections`/:class:`ScreenerDiscoverIdeaSection`
pair rather than a fully dynamic mapping, since Yahoo's own UI-facing name
for this single section is stable across the corpus) plus a top-level
``quotes`` mapping (symbol -> quote-shaped record, 44 rows across the 9
idea modules' tickers). Per the plan's reuse-decision procedure (the
``MarketSummaryQuote`` template), ``quotes`` values were first
script-validated directly against :class:`~yoghurt.models.quote.Quote`:
validation itself fails (not just an extras check) because 7 of
``Quote``'s required fields (``currency``, all six required
``fiftyTwoWeek*`` fields) are missing outright on every row, so reuse is
ruled out on the same required-set clause that produced
``MarketSummaryQuote`` — this endpoint gets its own
:class:`ScreenerDiscoverQuote` rather than a second attempt at reuse. Its
29 required fields are the wire keys universal across all 44 corpus
rows; ``postMarketChange``/``postMarketChangePercent``/``postMarketPrice``/
``postMarketTime`` (43/44), ``longName`` (43/44), ``averageAnalystRating``
(31/44), and ``netAssets`` (5/44, ETF/fund rows only) are optional.
Each :class:`ScreenerDiscoverIdeaSection`'s own ``records`` list is left
untyped (``list[dict[str, object]]``): unlike ``quotes``, these rows are a
per-idea-module, Yahoo-selected field subset (the 9 corpus modules share
only a bare ``ticker`` field; ``ANALYST_STRONG_BUY_STOCKS`` rows carry 13
fields, plain momentum modules like ``DAY_GAINERS`` carry only ``ticker``)
— the same "dynamic row shape keyed by an open-ended Yahoo id" situation
``screener()``/``visualization()`` exist to handle as ``Frame``s, not a
fixed pydantic row model. See the ``screener-predefined`` section below,
which hits the identical situation and is the reason this endpoint's
``records`` gets the same treatment rather than a distinct one-off call.

**screener-predefined** (not modeled in this file beyond its own
envelope). DECISION PROCEDURE OUTCOME (the plan's assumption corrected by
evidence): the plan expected quote-shaped rows nested at
``finance.result[].quotes[]``. All 5 corpus captures
(``MOST_ACTIVES``, ``MOST_ACTIVES_CRYPTOCURRENCIES``, ``TOP_MUTUAL_FUNDS``,
``TOP_OPTIONS_OPEN_INTEREST``, ``52_WEEK_GAINERS_PRIVATE_COMPANY``) were
captured with Yahoo's default ``useRecordsResponse=true``
(``CommandSpec`` default; see ``commands.py``'s ``screener-predefined``
notes) and carry no ``quotes`` key at all — instead
``finance.result[0].records[]``, a records-style response whose row shape
is a screener-id-specific field subset driven by that capture's own
``criteriaMeta.includeFields``. Script-checked across all 5 captures: only
5 fields (``companyName``/``regularMarketChange``/
``regularMarketChangePercent``/``regularMarketPrice``/``ticker``) are
common to every screener id's rows out of a 53-field union; the fullest
row schema (``MOST_ACTIVES``, 22 keys) and the thinnest
(``52_WEEK_GAINERS_PRIVATE_COMPANY``, 13 keys, wholly different domain
fields like ``fundingToDate``/``latestImpliedValuation``) share nothing
resembling a stable superset. Screener ids are open-ended and
Yahoo-defined (``commands.py``: "yoghurt does not validate them"), so
there is no fixed enumeration of row shapes to model even in principle —
this is exactly the ``screener()``/``visualization()`` dynamic-columns
situation, not a candidate for a fixed pydantic row model or for
``Quote``/``ScreenerDiscoverQuote`` reuse (neither was ever on the wire
here). ``ScreenerPredefinedResult`` therefore types every envelope-level
field Yahoo sends around those rows (``canonicalName``/``count``/
``description``/``iconUrl``/``id``/``isPremium``/``predefinedScr``/
``rawCriteria``/``criteriaMeta``/``start``/``title``/``total``/
``useRecords``/``userHasReadRecord``/``versionId``, all universal across
the 5 captures) via :class:`ScreenerCriteriaMeta`/
:class:`ScreenerCriteriaMetaFilter`, while ``records`` stays
``list[dict[str, object]]`` — typed as far as the evidence supports and no
further, per this codebase's own precedent for genuinely dynamic,
open-ended-id-keyed row data.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from yoghurt.models._base import YahooModel
from yoghurt.models.enums import (  # ruff:ignore[typing-only-first-party-import] - pydantic needs these at runtime
    MarketState,
    PriceAlertConfidence,
    QuoteType,
)

# ---------------------------------------------------------------------------
# screener-instrument-fields
# ---------------------------------------------------------------------------


class ScreenerFieldType(str, Enum):
    """Wire data type of a screener field, per :class:`ScreenerField.type`.

    All four members are observed across the 1666-field-spec corpus.

    Deliberately module-local rather than in ``yoghurt.models.enums``:
    this vocabulary (like :class:`ScreenerCriteriaOperator`) is consumed
    only by this endpoint family, unlike the cross-family enums that
    ``enums.py`` exists to share.
    """

    STRING = "STRING"
    NUMBER = "NUMBER"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"


class ScreenerCriteriaOperator(str, Enum):
    """Comparison operator of a :class:`ScreenerFieldCriteria`.

    All five members are observed across the 3597 quick-pick filter chips
    in the ``screener-instrument-fields`` corpus.
    """

    EQ = "EQ"
    BTWN = "BTWN"
    GTE = "GTE"
    GT = "GT"
    LT = "LT"


class ScreenerFieldCategory(YahooModel):
    """The ``category`` block of a :class:`ScreenerField`."""

    category_id: str = Field(alias="categoryId")
    """
    URL-safe category slug (for example ``"keystats"``); 48 distinct
    values observed across the corpus.
    """

    display_name: str = Field(alias="displayName")
    """
    Human-readable category name (for example ``"Share Statistics"``).
    """


class ScreenerFieldCriteria(YahooModel):
    """The ``criteria`` block of a :class:`ScreenerFieldLabel`."""

    operands: list[str | float]
    """
    Comparison operands: always starts with the field's own id (a string),
    followed by zero or more numeric or string comparison values depending
    on ``operator`` and the field's own type (for example ``["beta",
    -0.2, 0.2]`` for a ``BTWN`` chip, ``["exchange", "NMS"]`` for an ``EQ``
    chip on a string-valued field).
    """

    operator: ScreenerCriteriaOperator
    """
    Comparison operator this quick-pick chip applies.
    """


class ScreenerFieldLabel(YahooModel):
    """One quick-pick filter chip in a :class:`ScreenerField`'s ``labels``."""

    criteria: ScreenerFieldCriteria
    """
    The filter criteria this chip applies when selected.
    """

    dependent_filter_label: str | None = Field(
        default=None, alias="dependentFilterLabel"
    )
    """
    Display label of a parent filter chip this one depends on (for
    example an ``industry`` label naming its parent ``sector`` label).

    Present on 725 of 3597 corpus labels; ``None`` on the rest.
    """

    display_name: str = Field(alias="displayName")
    """
    Human-readable chip label (for example ``"< -0.2"``, ``"NasdaqGS"``).
    """


class ScreenerField(YahooModel):
    """One field's metadata entry in a :class:`ScreenerInstrumentFieldsResult`."""

    category: ScreenerFieldCategory
    """
    The category this field is grouped under in Yahoo's screener UI.
    """

    depend_for: list[str] | None = Field(default=None, alias="dependFor")
    """
    Field ids whose available options depend on this field's selection
    (for example ``sector`` lists ``["industry"]``).

    Present on 7 of 1666 corpus field specs, spread across 7 instruments
    (each instrument's own ``sector`` field); absent elsewhere.
    """

    dependent_field: str | None = Field(default=None, alias="dependentField")
    """
    Field id this field's own available options depend on (the inverse of
    ``depend_for``; for example ``industry`` names ``"sector"``).

    Present on 5 of 1666 corpus field specs, spread across 5 instruments
    (each instrument's own ``industry`` field); absent elsewhere.
    """

    deprecated: bool
    """
    Whether Yahoo has marked this field deprecated.
    """

    display_name: str = Field(alias="displayName")
    """
    Human-readable field name (for example ``"Beta"``).
    """

    dropdown_supported: bool = Field(alias="dropdownSupported")
    """
    Whether Yahoo's screener UI offers this field as a dropdown filter.
    """

    enable_search: bool | None = Field(default=None, alias="enableSearch")
    """
    Whether this field can be used as a free-text search filter.

    Present on 17 of 1666 corpus field specs, spread across 12
    instruments; absent elsewhere.
    """

    field_id: str = Field(alias="fieldId")
    """
    Yahoo's field identifier, matching this entry's own key in the
    ``fields`` mapping (for example ``"beta"``,
    ``"peratio.lasttwelvemonths"``).
    """

    is_premium: bool = Field(alias="isPremium")
    """
    Whether the underlying data for this field is paywalled; the schema
    entry itself is always returned regardless.
    """

    labels: list[ScreenerFieldLabel]
    """
    Quick-pick filter chips Yahoo's screener UI offers for this field.
    Frequently empty (most ``NUMBER`` fields carry no preset chips).
    """

    search_source: str | None = Field(default=None, alias="searchSource")
    """
    Backing search index name for ``enable_search`` fields (for example
    ``"ticker"``).

    Present on 17 of 1666 corpus field specs, spread across 12
    instruments; absent elsewhere.
    """

    sortable: bool
    """
    Whether this field can be used as a screener/visualization sort key.
    """

    type: ScreenerFieldType
    """
    Wire data type of this field's values.
    """


class ScreenerInstrumentFieldsResult(YahooModel):
    """The ``screener-instrument-fields`` endpoint's ``finance.result[0]`` payload."""

    fields: dict[str, ScreenerField]
    """
    Every field Yahoo exposes for the requested instrument, keyed by field
    id. Can be empty (Yahoo's documented ``privatecompany`` quirk; no
    corpus capture for that instrument, but the shape trivially supports
    it).
    """


# ---------------------------------------------------------------------------
# timeseries-fields
# ---------------------------------------------------------------------------


class TimeseriesFieldClass(YahooModel):
    """One row of a :class:`TimeseriesFieldsResult`'s ``timeSeriesDataClass``."""

    data_type: str = Field(alias="dataType")
    """
    Wire field-class identifier (for example
    ``"sigdev_corporate_deals"``); the value used as a ``timeseries``
    ``type=`` selector.
    """

    display_name: str = Field(alias="displayName")
    """
    Human-readable field-class name (for example ``"Corporate Deals"``).
    """


class TimeseriesFieldsResult(YahooModel):
    """The ``timeseries-fields`` endpoint's ``timeseriesfields.result[0]`` payload.

    Thin, single-capture evidence throughout.
    """

    time_series_data_class: list[TimeseriesFieldClass] = Field(
        alias="timeSeriesDataClass"
    )
    """
    Every fundamentals timeseries field class Yahoo exposes (13 rows in
    the single corpus capture).
    """


# ---------------------------------------------------------------------------
# screener-discover
# ---------------------------------------------------------------------------


class ScreenerDiscoverQuote(YahooModel):
    """One value of a :class:`ScreenerDiscoverResult`'s ``quotes`` mapping.

    Distinct from :class:`~yoghurt.models.quote.Quote`: see the module
    docstring for the script-validated reuse-decision evidence (validation
    against ``Quote`` fails outright — 8 required ``Quote`` fields are
    missing on every row, not merely absent-from-universal as with
    :class:`~yoghurt.models.markets.MarketSummaryQuote`).
    """

    average_analyst_rating: str | None = Field(
        default=None, alias="averageAnalystRating"
    )
    """
    Aggregate analyst rating label (for example ``"1.5 - Buy"``).

    Present on 31 of 44 corpus rows (equities with analyst coverage; ETF
    rows never carry it).
    """

    crypto_tradeable: bool
    """
    Whether this instrument can be traded as cryptocurrency.
    """

    custom_price_alert_confidence: PriceAlertConfidence
    """
    Yahoo's confidence level for its price-alert feature on this symbol.
    """

    esg_populated: bool
    """
    Whether Yahoo has ESG (environmental/social/governance) data for this
    symbol.
    """

    exchange: str
    """
    Short code of the securities exchange (for example ``"NMS"``).
    """

    exchange_data_delayed_by: int
    """
    Minutes this exchange's data is delayed by.
    """

    exchange_timezone_name: str
    """
    IANA timezone name of the exchange.
    """

    exchange_timezone_short_name: str
    """
    Short abbreviation of the exchange timezone.
    """

    first_trade_date_milliseconds: int
    """
    Epoch-milliseconds timestamp of this instrument's first trade.
    """

    full_exchange_name: str
    """
    Full display name of the exchange.
    """

    gmt_off_set_milliseconds: int
    """
    Offset from GMT of the exchange, in milliseconds.
    """

    has_pre_post_market_data: bool
    """
    Whether pre-market/after-hours data is available for this symbol.
    """

    language: str
    """
    Locale Yahoo rendered this record in.
    """

    long_name: str | None = None
    """
    Official long name of the security.

    Present on 43 of 44 corpus rows.
    """

    market: str
    """
    Yahoo's internal market-segment identifier.
    """

    market_state: MarketState = Field(alias="marketState")
    """
    Current trading session phase.
    """

    net_assets: float | None = Field(default=None, alias="netAssets")
    """
    Total net assets under management.

    A bare wire float (unlike the ``sector`` endpoint's ``{raw, fmt,
    longFmt}``-wrapped fund fields). Present on 5 of 44 corpus rows (ETF
    rows only).
    """

    post_market_change: float | None = Field(default=None, alias="postMarketChange")
    """
    Absolute price change during the post-market session.

    Present on 43 of 44 corpus rows.
    """

    post_market_change_percent: float | None = Field(
        default=None, alias="postMarketChangePercent"
    )
    """
    Percent price change during the post-market session.

    Present on 43 of 44 corpus rows.
    """

    post_market_price: float | None = Field(default=None, alias="postMarketPrice")
    """
    Most recent post-market trade price.

    Present on 43 of 44 corpus rows.
    """

    post_market_time: int | None = Field(default=None, alias="postMarketTime")
    """
    Epoch-seconds timestamp of ``post_market_price``.

    Present on 43 of 44 corpus rows.
    """

    price_hint: int
    """
    Suggested decimal-place precision for displaying this symbol's price.

    Unlike :class:`~yoghurt.models.markets.MarketSummaryQuote`, universal
    across this endpoint's corpus rows.
    """

    quote_source_name: str = Field(alias="quoteSourceName")
    """
    Human-readable name of the quote data source (for example
    ``"Nasdaq Real Time Price"``, ``"Delayed Quote"``).
    """

    quote_type: QuoteType
    """
    Classification of this instrument.
    """

    region: str
    """
    Yahoo region this record was served for.
    """

    regular_market_change: float = Field(alias="regularMarketChange")
    """
    Absolute change from the previous regular-session close.
    """

    regular_market_change_percent: float = Field(alias="regularMarketChangePercent")
    """
    Percent change from the previous regular-session close.
    """

    regular_market_previous_close: float = Field(alias="regularMarketPreviousClose")
    """
    Previous regular-session closing price.
    """

    regular_market_price: float = Field(alias="regularMarketPrice")
    """
    Most recent regular-session trade price.
    """

    regular_market_time: int = Field(alias="regularMarketTime")
    """
    Epoch-seconds timestamp of ``regular_market_price``.
    """

    short_name: str
    """
    Short display name of the security.
    """

    source_interval: int
    """
    Refresh interval, in minutes, of the underlying data source.
    """

    symbol: str
    """
    Yahoo ticker symbol.
    """

    tradeable: bool
    """
    Whether this instrument can be traded through Yahoo's brokerage
    integration.
    """

    triggerable: bool
    """
    Whether this symbol supports Yahoo's price-alert triggers.
    """

    type_disp: str = Field(alias="typeDisp")
    """
    Human-readable display label for ``quote_type``.
    """


class ScreenerDiscoverIdeaSection(YahooModel):
    """One entry of a :class:`ScreenerDiscoverSections`'s idea-module list."""

    canonical_name: str = Field(alias="canonicalName")
    """
    Yahoo's stable identifier for this idea module (for example
    ``"MOST_ACTIVES"``, ``"DAY_GAINERS"``).
    """

    creation_date: int = Field(alias="creationDate")
    """
    Epoch-milliseconds timestamp this idea module was created.
    """

    description: str
    """
    Prose description of this idea module.
    """

    entity_id_type: str | None = Field(default=None, alias="entityIdType")
    """
    Row-identifier kind for non-quote idea modules (for example
    ``"TRADE_IDEA"``, ``"ANALYST_RATINGS"``).

    Present only on modules whose rows aren't plain ticker references;
    mutually exclusive with ``quote_type`` in the corpus.
    """

    id: str
    """
    Unique identifier for this idea module.
    """

    is_premium: bool = Field(alias="isPremium")
    """
    Whether this idea module requires a Yahoo premium subscription.
    """

    last_updated: int = Field(alias="lastUpdated")
    """
    Epoch-milliseconds timestamp this idea module's rows were last
    refreshed.
    """

    predefined_scr: bool = Field(alias="predefinedScr")
    """
    Whether this idea module is also queryable via ``screener-predefined``.

    Always ``True`` in the corpus.
    """

    quote_type: QuoteType | None = Field(default=None, alias="quoteType")
    """
    Instrument classification every row in this module shares, when the
    module is quote-scoped.

    Mutually exclusive with ``entity_id_type`` in the corpus.
    """

    records: list[dict[str, object]]
    """
    This idea module's rows.

    A dynamic, per-module field subset rather than a fixed-field model:
    the 9 corpus modules share only a bare ``ticker`` field among
    themselves (``ANALYST_STRONG_BUY_STOCKS`` rows carry 13 fields,
    ``DAY_GAINERS`` rows carry only ``ticker``). Deliberately left
    untyped, mirroring ``screener-predefined``'s ``records`` (see the
    module docstring's "screener-predefined" section) rather than
    inventing a misleading fixed schema for open-ended, Yahoo-selected
    field lists.
    """

    title: str
    """
    Display title for this idea module (for example ``"Most Actives"``).
    """

    total: int
    """
    Total number of rows Yahoo has for this idea module (can exceed
    ``len(records)``, which is capped short in the corpus).
    """

    version_id: int = Field(alias="versionId")
    """
    Yahoo-internal version counter for this idea module's definition.
    """


class NeoInvestmentIdeas(YahooModel):
    """The ``neo_investment_ideas`` value of a :class:`ScreenerDiscoverSections`."""

    screeners_list: list[ScreenerDiscoverIdeaSection] = Field(alias="screenersList")
    """
    Curated idea modules Yahoo surfaces on its discover page (9 in the
    single corpus capture).
    """


class ScreenerDiscoverSections(YahooModel):
    """The ``sections`` block of a :class:`ScreenerDiscoverResult`."""

    neo_investment_ideas: NeoInvestmentIdeas = Field(alias="neo_investment_ideas")
    """
    The single idea-section key observed in the corpus.
    """


class ScreenerDiscoverResult(YahooModel):
    """The ``screener-discover`` endpoint's ``finance.result`` payload.

    ``finance.result`` is a bare object here, not a list — distinct from
    every ``finance.result[]``-shaped endpoint modeled elsewhere in this
    codebase.
    """

    quotes: dict[str, ScreenerDiscoverQuote]
    """
    Quote-shaped detail for every ticker referenced anywhere in
    ``sections`` (keyed by symbol; 44 entries in the single corpus
    capture). See the module docstring for the reuse-decision evidence
    ruling out :class:`~yoghurt.models.quote.Quote`.
    """

    sections: ScreenerDiscoverSections
    """
    Curated idea-module groupings.
    """


# ---------------------------------------------------------------------------
# screener-predefined (envelope-level typing only; see module docstring)
# ---------------------------------------------------------------------------


class ScreenerCriteriaMetaFilter(YahooModel):
    """One applied filter in a :class:`ScreenerCriteriaMeta`'s ``criteria`` list."""

    dependent_values: list[object] = Field(alias="dependentValues")
    """
    Values selected for a dependent filter (for example an ``industry``
    filter dependent on a ``sector`` selection).

    Always empty in the corpus.
    """

    field: str
    """
    Screener field id this filter applies to (for example ``"dayvolume"``,
    matching a :class:`ScreenerField.field_id`).
    """

    labels_selected: list[int] = Field(alias="labelsSelected")
    """
    Indices into the field's quick-pick ``labels`` array that this filter
    corresponds to, when the filter was built from preset chips rather
    than a raw value.
    """

    operators: list[str]
    """
    Comparison operators this filter applies (wire values match
    :class:`ScreenerCriteriaOperator`, kept as bare ``str`` here since this
    is a distinct wire location and thin, single-endpoint-family evidence
    doesn't independently confirm the same closed vocabulary).
    """

    sub_field: str | None = Field(default=None, alias="subField")
    """
    Sub-field qualifier for a compound field, when applicable.

    Always ``None`` in the corpus.
    """

    values: list[str | int]
    """
    Raw comparison values for this filter (for example ``[15000]`` for a
    ``GT`` volume filter, ``["CCC"]`` for an ``EQ`` exchange filter).
    """


class ScreenerCriteriaMeta(YahooModel):
    """The ``criteriaMeta`` block of a :class:`ScreenerPredefinedResult`."""

    criteria: list[ScreenerCriteriaMetaFilter]
    """
    Applied filters defining this predefined screener (empty for the
    ``PRIVATE_COMPANY`` screener in the corpus, which instead filters
    purely by ``quote_type``).
    """

    include_fields: list[str] = Field(alias="includeFields")
    """
    Screener field ids Yahoo selected for this screener's ``records`` rows
    (for example ``["ticker", "fiftytwowkpercentchange", ...]``); this is
    what drives ``records``' per-screener row shape.
    """

    offset: int
    """
    Zero-based row offset this request started from.
    """

    quote_type: str = Field(alias="quoteType")
    """
    Instrument classification this screener's rows share (for example
    ``"EQUITY"``, ``"PRIVATE_COMPANY"``); kept as bare ``str`` rather than
    :class:`~yoghurt.models.enums.QuoteType` since the corpus shows
    lowercase variants inside ``rawCriteria`` for the same concept and a
    dedicated ``PRIVATE_COMPANY``-only enum member has no other corpus
    confirmation at this wire location.
    """

    size: int
    """
    Maximum number of rows requested.
    """

    sort_field: str = Field(alias="sortField")
    """
    Screener field id rows are sorted by.
    """

    sort_type: str = Field(alias="sortType")
    """
    Sort direction (``"ASC"``/``"DESC"``).
    """

    top_operator: str = Field(alias="topOperator")
    """
    How ``criteria`` filters combine (for example ``"AND"``,
    ``"MATCH_ALL"``).
    """


class ScreenerPredefinedResult(YahooModel):
    """The ``screener-predefined`` endpoint's ``finance.result[]`` row payload.

    See the module docstring's "screener-predefined" section for why
    ``records`` stays untyped while every other field here is fully typed
    from the 5-capture corpus.
    """

    canonical_name: str = Field(alias="canonicalName")
    """
    Yahoo's stable screener identifier (for example ``"MOST_ACTIVES"``),
    matching the ``scr_ids`` value used to request it.
    """

    count: int
    """
    Number of rows in ``records`` for this response page.
    """

    criteria_meta: ScreenerCriteriaMeta = Field(alias="criteriaMeta")
    """
    Structured filter/sort definition backing this screener.
    """

    description: str
    """
    Prose description of this screener.
    """

    icon_url: str = Field(alias="iconUrl")
    """
    URL of this screener's display icon.
    """

    id: str
    """
    Unique identifier for this screener.
    """

    is_premium: bool = Field(alias="isPremium")
    """
    Whether this screener requires a Yahoo premium subscription.
    """

    predefined_scr: bool = Field(alias="predefinedScr")
    """
    Whether this is one of Yahoo's own predefined screeners.

    Always ``True`` in the corpus (every capture is, by definition, a
    predefined-screener request).
    """

    raw_criteria: str = Field(alias="rawCriteria")
    """
    JSON-encoded string form of the filter/sort criteria (a serialized
    duplicate of ``criteria_meta``, kept as the raw wire string rather
    than double-parsed).
    """

    records: list[dict[str, object]]
    """
    This screener's result rows.

    A dynamic, per-screener-id field subset driven by
    ``criteria_meta.include_fields`` — see the module docstring's
    "screener-predefined" section for the full evidence. Deliberately
    left untyped rather than modeled as a fixed row schema or reused as
    :class:`~yoghurt.models.quote.Quote`/:class:`ScreenerDiscoverQuote`
    (neither shape appears on this wire location in the corpus).
    """

    start: int
    """
    Zero-based row offset of this response page (matches the requested
    ``start``).
    """

    title: str
    """
    Display title for this screener (for example ``"Most Actives"``).
    """

    total: int
    """
    Total number of rows Yahoo has for this screener (can exceed
    ``count``/``len(records)``).
    """

    use_records: bool = Field(alias="useRecords")
    """
    Whether this response used Yahoo's records-style shape.

    Always ``True`` in the corpus; corresponds to the
    ``use_records_response`` API/CLI parameter.
    """

    user_has_read_record: bool = Field(alias="userHasReadRecord")
    """
    Whether the requesting (anonymous) session has acknowledged this
    screener's disclosure record.

    Always ``False`` in the corpus.
    """

    version_id: int = Field(alias="versionId")
    """
    Yahoo-internal version counter for this screener's definition.
    """
