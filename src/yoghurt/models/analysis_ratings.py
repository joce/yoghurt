"""Typed models for the deep analyst-research and top-ratings endpoints (batch 3d-2).

Reconciled against the probe corpus at ``tests/fixtures/corpus/``, captured
2026-07-04. Regenerate applicability evidence with
``uv run python -m tools.fields_report <stream>`` after a corpus refresh
(see ``tools/fields_report.py`` for the ``analyst``/``ratings-top`` record
streams this evidence is built from). This module covers the two remaining
bare-payload (non-enveloped) symbol-bound analysis endpoints: ``analyst``
and ``ratings-top``.

**analyst** (endpoint noun: "analyst records"). Only 2 populated captures
(``AAPL``, ``MSFT``) plus 2 error captures: ``ZZZZXYZQ`` is the expected
``{"detail": "Symbol not found for ZZZZXYZQ"}`` 404 shape, and ``RY.TO`` —
despite the plan's expectation of a "thin-but-valid" capture — is *also* an
error body (``{"detail": "Symbol not found for RY.TO"}``), not a valid thin
record. There is therefore no thin-coverage example for this endpoint at
all: every field below is evidenced by exactly 2 (AAPL/MSFT) identically
shaped, fully populated records, and required exactly for the keys both
captures share (which is all of them). A future corpus refresh that adds a
genuinely thin symbol should be treated as the real requiredness test.

The wire payload is a deeply nested tree of AI-generated research
sub-reports, each following the same envelope shape (``id``/``trace_id``/
``symbol_id``/``created_at``/``updated_at``/``debug`` alongside its own
payload key). Two sub-trees — ``price_movement`` and ``news_summary`` —
are **byte-for-byte shape-identical** to
:class:`~yoghurt.models.analysis_insights.PriceMovement` and
:class:`~yoghurt.models.analysis_insights.NewsSummaryBlock` (verified by
validating both AAPL/MSFT captures directly against those existing models
with zero extras at every nesting level): this endpoint's ``analyst``
service and the ``price-insights`` endpoint's ``aiAnalysis.data`` block are
almost certainly proxying the same underlying AI-analysis service. Per the
one-name-per-concept rule, :class:`AnalystResult` reuses those exact
classes rather than minting duplicates; see :class:`AnalystResult` for the
import.

Every other sub-tree (``options_analysis``, ``holdings_insights``,
``overview``, ``rtr``, ``financial_insights``,
``earnings_transcripts_insights``) is distinct prose content with its own
shape, modeled fresh below. Most nested keys are already snake_case (or
irregularly cased) on the wire, matching the ``analysis_insights.py``
AI-service precedent: every field in this module's sub-trees carries an
explicit ``Field(alias=...)`` rather than relying on ``to_camel``.
Several blocks (``options_analysis.key_takeaways``,
``financial_insights.categories``, ``overview.overview.key_observations``,
``earnings_transcripts_insights.earnings_analysis.key_insights``/
``.key_insights_structured``) carry AI-generated, dynamically-headlined
prose keyed by a headline string rather than a fixed vocabulary (mirroring
:class:`~yoghurt.models.analysis_insights.PriceMovementExplanation`'s
``observations`` field) and are typed ``dict[str, str]``/
``dict[str, dict[str, str]]`` accordingly. ``options_data``/
``options_window_data`` are always an empty ``{}`` in the corpus (a
dynamic bag with no observed keys, typed ``dict[str, object]``, mirroring
``analysis_insights.py``'s ``debug`` fields).

**ratings-top** (endpoint noun: "top-rating buckets"). 2 populated
captures (``AAPL``, ``MSFT``); ``RY.TO`` is a genuine 404
(``{"detail": "No top ratings found for symbol: RY.TO"}``, confirmed to
contain the case-insensitive substring ``"not found"`` that
``yoghurt._core.map_http_error`` already maps to ``SymbolNotFoundError``).
The endpoint's four top-level keys (``dir``, ``mm``, ``pt``, ``fin_score``)
each identify which scored metric that analyst is the top pick *for*; the
:class:`AnalystRatingRow` occupying each bucket separately carries its own
``dir``/``mm``/``pt``/``fin_score`` sub-fields, which are that analyst's
*own* scores across all four metrics — the two same-named concepts are
unrelated beyond sharing a label, and are documented as such on
:class:`TopRatingsResult` and :class:`AnalystRatingRow` respectively.
``rating_sentiment`` is always ``1`` and ``rating_current`` only ever
``"Outperform"``/``"Buy"`` across this 2-capture, 8-row corpus — both are
typed as their thinly-evidenced primitive (``int``/``str``) rather than a
closed-vocabulary enum. ``announcement_date`` is a bare ``"YYYY-MM-DD"``
wire string that pydantic parses directly into :class:`datetime.date` (no
``Raw*`` wrapper involved, unlike the row's own ``dir``/``mm``/``pt``/
``fin_score`` scores, which are ``{"raw": ..., "fmt": ...}`` wrapped).
"""

from __future__ import annotations

import datetime  # noqa: TC003 - pydantic needs this at runtime to resolve annotations

from pydantic import Field

from yoghurt.models._base import RawFloat, YahooModel
from yoghurt.models.analysis_insights import (  # noqa: TC001 - pydantic needs these at runtime
    NewsSummaryBlock,
    PriceMovement,
)

# ---------------------------------------------------------------------------
# analyst
# ---------------------------------------------------------------------------


class OptionsAnalysisPcr(YahooModel):
    """The ``options_analysis.pcr`` block of an :class:`OptionsAnalysis`."""

    pcr_notional: float = Field(alias="pcr_notional")
    """
    Put/call ratio computed by notional value.
    """

    pcr_volume: float = Field(alias="pcr_volume")
    """
    Put/call ratio computed by contract volume.
    """

    quote_date: str = Field(alias="quote_date")
    """
    Timestamp this ratio was computed for, as Yahoo's wire
    ``"YYYY-MM-DD HH:MM:SS"`` string (no UTC offset; not parsed as a
    datetime to avoid guessing an implied timezone).
    """

    underlying_symbol: str = Field(alias="underlying_symbol")
    """
    Ticker symbol this ratio covers.
    """


class OptionsAnalysisTimeframeInsights(YahooModel):
    """The ``options_analysis.key_takeaways.timeframe_insights`` block."""

    one_month: str = Field(alias="one_month")
    """
    AI-generated commentary on the one-month put/call ratio trend.
    """

    one_week: str = Field(alias="one_week")
    """
    AI-generated commentary on the one-week put/call ratio trend.
    """

    one_year: str = Field(alias="one_year")
    """
    AI-generated commentary on the one-year put/call ratio trend.
    """


class OptionsAnalysisKeyTakeaways(YahooModel):
    """The ``options_analysis.key_takeaways`` block of an :class:`OptionsAnalysis`."""

    teaser: str
    """
    Short, headline-style teaser summarizing the options analysis.
    """

    timeframe_insights: OptionsAnalysisTimeframeInsights = Field(
        alias="timeframe_insights"
    )
    """
    Put/call ratio commentary across three lookback windows.
    """

    tldr: str
    """
    Short AI-generated summary of the options analysis.
    """


class OptionsAnalysis(YahooModel):
    """The ``options_analysis`` block of an :class:`AnalystResult`."""

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this analysis was generated.
    """

    date: str
    """
    Timestamp this analysis covers, as Yahoo's wire
    ``"YYYY-MM-DD HH:MM:SS"`` string (no UTC offset; not parsed as a
    datetime to avoid guessing an implied timezone). Matches
    ``pcr.quote_date`` on every corpus record.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.
    """

    id: str
    """
    Unique identifier for this analysis.

    Matches ``trace_id`` on every corpus record.
    """

    key_takeaways: OptionsAnalysisKeyTakeaways = Field(alias="key_takeaways")
    """
    AI-generated narrative summarizing this symbol's options positioning.
    """

    options_data: dict[str, object] = Field(alias="options_data")
    """
    Raw options-chain data bag.

    Always an empty ``{}`` in the corpus; true populated shape unknown.
    """

    options_window_data: dict[str, object] = Field(alias="options_window_data")
    """
    Windowed options-chain data bag.

    Always an empty ``{}`` in the corpus; true populated shape unknown.
    """

    pcr: OptionsAnalysisPcr
    """
    Put/call ratio figures backing this analysis.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the analyzed symbol.
    """

    ticker: str
    """
    Ticker symbol this analysis covers.
    """

    trace_id: str = Field(alias="trace_id")
    """
    Tracing identifier for this analysis request.

    Matches ``id`` on every corpus record.
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this analysis was last updated.

    Matches ``created_at`` on every corpus record.
    """


class InsiderActivity(YahooModel):
    """The ``insiderActivity`` block of a :class:`HoldingsInsights`."""

    analysis_update_time: str = Field(alias="analysis_update_time")
    """
    Timestamp this analysis was last refreshed, as a bare naive-local
    ISO-8601 string with no UTC offset (unlike this module's other
    timestamps; not parsed as a datetime to avoid guessing an implied
    timezone).
    """

    highlights: str
    """
    Short AI-generated summary of recent insider transaction activity.
    """

    key_takeaways: str = Field(alias="key_takeaways")
    """
    AI-generated narrative expanding on ``highlights``, in Markdown.
    """

    key_takeaways_structured: list[str] = Field(alias="key_takeaways_structured")
    """
    ``key_takeaways``, split into individual bullet-point strings.
    """


class HoldingsInsights(YahooModel):
    """The ``holdings_insights`` block of an :class:`AnalystResult`."""

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this analysis was generated.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.
    """

    id: str
    """
    Unique identifier for this analysis.

    Matches ``trace_id`` on every corpus record.
    """

    insider_activity: InsiderActivity = Field(alias="insiderActivity")
    """
    AI-generated summary of recent insider buy/sell/award activity.

    The only field in this module carrying a camelCase wire key
    (``insiderActivity``) rather than snake_case; explicit alias, per the
    module docstring.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the analyzed symbol.
    """

    trace_id: str = Field(alias="trace_id")
    """
    Tracing identifier for this analysis request.

    Matches ``id`` on every corpus record.
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this analysis was last updated.

    Matches ``created_at`` on every corpus record.
    """


class AnalystOverviewBody(YahooModel):
    """The ``overview.overview`` block of an :class:`AnalystOverview`."""

    key_observations: dict[str, str] = Field(alias="key_observations")
    """
    Supporting observations, keyed by a dynamic, AI-generated headline
    (for example ``"Rising Component Costs"``, ``"AI Investment"``) rather
    than a fixed key set.
    """

    tldr: str
    """
    Short AI-generated summary of this symbol's overall outlook.
    """


class AnalystOverview(YahooModel):
    """The ``overview`` block of an :class:`AnalystResult`."""

    analysis_update_time: str = Field(alias="analysis_update_time")
    """
    Timestamp this analysis was last refreshed, as a bare naive-local
    ISO-8601 string with no UTC offset; see
    :class:`InsiderActivity`'s field of the same name.
    """

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this analysis was generated.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.
    """

    dynamic_questions: list[object] = Field(alias="dynamic_questions")
    """
    Suggested AI follow-up questions.

    Always an empty list in the corpus; row shape unmodeled. Unlike
    :class:`~yoghurt.models.analysis_insights.DynamicQuestion`'s use
    elsewhere in this AI-service family, no populated example exists here
    to justify reusing that model over an untyped placeholder.

    Observed only as empty lists in the corpus.
    """

    id: str
    """
    Unique identifier for this analysis.

    Matches ``trace_id`` on every corpus record.
    """

    overview: AnalystOverviewBody
    """
    The generated overview content.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the analyzed symbol.
    """

    ticker: str
    """
    Ticker symbol this analysis covers.
    """

    trace_id: str = Field(alias="trace_id")
    """
    Tracing identifier for this analysis request.

    Matches ``id`` on every corpus record.
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this analysis was last updated.

    Matches ``created_at`` on every corpus record.
    """


class RtrSummary(YahooModel):
    """The ``rtr.rtr_summary`` block of an :class:`Rtr`."""

    id: str
    """
    Symbol this summary covers.
    """

    price_target: str = Field(alias="price_target")
    """
    AI-generated narrative on the analyst price-target range.
    """

    ratings_summary: str = Field(alias="ratings_summary")
    """
    AI-generated narrative summarizing current analyst ratings.
    """

    recent_upgrades: str = Field(alias="recent_upgrades")
    """
    AI-generated narrative on recent rating changes.
    """

    tldr: str
    """
    Short AI-generated summary of analyst sentiment.
    """

    viewpoint: str
    """
    Short label for the dominant analyst viewpoint (for example
    ``"Diverse Analyst Opinions"``, ``"Consensus"``).
    """

    viewpoint_details: str = Field(alias="viewpoint_details")
    """
    AI-generated narrative expanding on ``viewpoint``.
    """


class Rtr(YahooModel):
    """The ``rtr`` block of an :class:`AnalystResult`.

    Holds an AI-generated ratings/price-target summary.
    """

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this analysis was generated.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.
    """

    generation_start_time: datetime.datetime = Field(alias="generation_start_time")
    """
    Timestamp generation of this summary began.
    """

    id: str
    """
    Unique identifier for this summary.

    Matches ``trace_id`` on every corpus record.
    """

    rtr_summary: RtrSummary = Field(alias="rtr_summary")
    """
    The generated ratings/price-target summary content.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the analyzed symbol.
    """

    trace_id: str = Field(alias="trace_id")
    """
    Tracing identifier for this summary request.

    Matches ``id`` on every corpus record.
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this summary was last updated.
    """


class FinancialInsightsEarningsCalendarEntry(YahooModel):
    """One entry in ``financial_insights.earnings_calendar``."""

    earnings_release: datetime.datetime = Field(alias="earnings_release")
    """
    Point-in-time earnings release timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.
    """

    fiscal_period: str = Field(alias="fiscal_period")
    """
    Fiscal quarter label (for example ``"Q3"``).
    """

    fiscal_year: int = Field(alias="fiscal_year")
    """
    Fiscal year this release covers.

    A wire integer here, unlike
    ``earnings_transcripts_insights.fiscal_year`` on the sibling
    :class:`EarningsTranscriptsInsights` block, which sends the same
    concept as a string; a genuine wire-type divergence between blocks of
    this same endpoint, not a modeling inconsistency.
    """


class LatestEarningsMetadata(YahooModel):
    """The ``financial_insights.latest_earnings_metadata`` block."""

    earnings_disclosed_at: datetime.date = Field(alias="earnings_disclosed_at")
    """
    Calendar date the latest earnings were disclosed, as a bare
    ``"YYYY-MM-DD"`` wire string.
    """

    fiscal_period: str = Field(alias="fiscal_period")
    """
    Fiscal quarter label (for example ``"Q2"``).
    """

    fiscal_year: int = Field(alias="fiscal_year")
    """
    Fiscal year of the latest disclosed earnings.

    A wire integer, matching
    :class:`FinancialInsightsEarningsCalendarEntry`'s ``fiscal_year``; see
    that field's docstring for the sibling block's differing wire type.
    """

    period_end_date: datetime.date = Field(alias="period_end_date")
    """
    Calendar date the latest disclosed fiscal period ended, as a bare
    ``"YYYY-MM-DD"`` wire string.
    """

    period_start_date: datetime.date = Field(alias="period_start_date")
    """
    Calendar date the latest disclosed fiscal period started, as a bare
    ``"YYYY-MM-DD"`` wire string.
    """


class FinancialInsights(YahooModel):
    """The ``financial_insights`` block of an :class:`AnalystResult`."""

    categories: dict[str, str]
    """
    AI-generated valuation/profitability/growth commentary, keyed by a
    dynamic category headline (for example ``"Valuation"``,
    ``"Profitability"``, ``"Growth Metrics"``) rather than a fixed key set.
    """

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this analysis was generated.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.
    """

    earnings_calendar: list[FinancialInsightsEarningsCalendarEntry] = Field(
        alias="earnings_calendar"
    )
    """
    Recent and upcoming earnings-release dates.
    """

    id: str
    """
    Unique identifier for this analysis.

    Matches ``trace_id`` on every corpus record.
    """

    latest_earnings_metadata: LatestEarningsMetadata = Field(
        alias="latest_earnings_metadata"
    )
    """
    Metadata describing the most recently disclosed earnings period.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the analyzed symbol.
    """

    tldr: str
    """
    Short AI-generated summary of this symbol's financial profile.
    """

    trace_id: str = Field(alias="trace_id")
    """
    Tracing identifier for this analysis request.

    Matches ``id`` on every corpus record.
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this analysis was last updated.

    Matches ``created_at`` on every corpus record.
    """


class EarningsAnalystFocusQuestion(YahooModel):
    """One entry in ``earnings_analysis.analyst_focus.key_questions_and_responses``."""

    question: str
    """
    Analyst question, as paraphrased by the AI summary.
    """

    response: str
    """
    Management's response, as paraphrased by the AI summary.
    """

    significance: str
    """
    AI-generated commentary on why this exchange matters to investors.
    """


class EarningsAnalystFocus(YahooModel):
    """The ``earnings_analysis.analyst_focus`` block."""

    key_questions_and_responses: list[EarningsAnalystFocusQuestion] = Field(
        alias="key_questions_and_responses"
    )
    """
    Notable analyst questions and management's responses from the
    earnings call.
    """

    overall_sentiment: str = Field(alias="overall_sentiment")
    """
    AI-generated summary of the analysts' overall tone on the call.
    """


class EarningsQaHighlights(YahooModel):
    """The ``earnings_analysis.qa_highlights`` block."""

    analyst_sentiment: str = Field(alias="analyst_sentiment")
    """
    AI-generated summary of analyst sentiment during the Q&A session.
    """

    key_themes: str = Field(alias="key_themes")
    """
    AI-generated summary of recurring Q&A themes.
    """

    management_tone: str = Field(alias="management_tone")
    """
    AI-generated assessment of management's tone during the Q&A session.
    """

    notable_exchanges: str = Field(alias="notable_exchanges")
    """
    AI-generated summary of the most notable Q&A exchanges.
    """


class EarningsNotableQuote(YahooModel):
    """One entry in ``earnings_analysis.notable_quotes``."""

    context: str
    """
    AI-generated commentary on why this quote matters.
    """

    quote: str
    """
    Verbatim (or near-verbatim) quote from the earnings call.
    """

    speaker: str
    """
    Name and title of the person quoted (for example ``"Tim Cook, CEO"``).
    """


class EarningsAnalysis(YahooModel):
    """The ``earnings_transcripts_insights.earnings_analysis`` block."""

    analyst_focus: EarningsAnalystFocus = Field(alias="analyst_focus")
    """
    Analyst questions and management's responses from the call, plus
    overall analyst sentiment.
    """

    key_insights: dict[str, str] = Field(alias="key_insights")
    """
    AI-generated prose per topic, keyed by a dynamic, AI-generated topic
    headline (for example ``"Outlook"``, ``"Segment Insights"``) rather
    than a fixed key set. Every value is the same content as the matching
    :class:`key_insights_structured <EarningsAnalysis>` entry, flattened to
    a single prose block instead of itemized sub-points.
    """

    key_insights_structured: dict[str, dict[str, str]] = Field(
        alias="key_insights_structured"
    )
    """
    ``key_insights``, itemized: each topic headline maps to a further
    dynamic, AI-generated sub-point headline (for example ``"iPhone"``
    under ``"Segment Insights"``) rather than a fixed key set at either
    level.
    """

    notable_quotes: list[EarningsNotableQuote] = Field(alias="notable_quotes")
    """
    Notable verbatim quotes from the earnings call.
    """

    qa_highlights: EarningsQaHighlights = Field(alias="qa_highlights")
    """
    AI-generated summary of the earnings call's Q&A session.
    """

    teaser_tldr: str = Field(alias="teaser_tldr")
    """
    Short, headline-style teaser summarizing the earnings call.
    """

    tldr: str
    """
    Short AI-generated summary of the earnings call.
    """


class EarningsTranscriptsInsights(YahooModel):
    """The ``earnings_transcripts_insights`` block of an :class:`AnalystResult`."""

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this analysis was generated.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.
    """

    earnings_analysis: EarningsAnalysis = Field(alias="earnings_analysis")
    """
    The generated earnings-call analysis content.
    """

    fiscal_period: str = Field(alias="fiscal_period")
    """
    Fiscal quarter label (for example ``"Q2"``).
    """

    fiscal_year: str = Field(alias="fiscal_year")
    """
    Fiscal year this earnings call covers.

    A wire string here (for example ``"2026"``), unlike
    :class:`FinancialInsightsEarningsCalendarEntry`'s/
    :class:`LatestEarningsMetadata`'s ``fiscal_year``, which send the same
    concept as an integer; see those fields' docstrings.
    """

    id: str
    """
    Unique identifier for this analysis.

    Matches ``trace_id`` on every corpus record.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the analyzed symbol.
    """

    trace_id: str = Field(alias="trace_id")
    """
    Tracing identifier for this analysis request.

    Matches ``id`` on every corpus record.
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this analysis was last updated.

    Matches ``created_at`` on every corpus record.
    """


class AnalystResult(YahooModel):
    """The ``analyst`` endpoint's bare (non-enveloped) single-symbol payload.

    Only 2 populated captures (``AAPL``/``MSFT``); every field below is
    required because both share the identical top-level key set (see the
    module docstring's thin-evidence caveat — this endpoint has no captured
    thin-but-valid example, unlike its siblings). ``price_movement``/
    ``news_summary`` reuse :class:`~yoghurt.models.analysis_insights.PriceMovement`/
    :class:`~yoghurt.models.analysis_insights.NewsSummaryBlock` rather than
    minting duplicate models; see the module docstring for the shape-match
    evidence.
    """

    earnings_transcripts_insights: EarningsTranscriptsInsights = Field(
        alias="earnings_transcripts_insights"
    )
    """
    AI-generated analysis of the most recent earnings call transcript.
    """

    financial_insights: FinancialInsights = Field(alias="financial_insights")
    """
    AI-generated valuation/profitability/growth commentary.
    """

    holdings_insights: HoldingsInsights = Field(alias="holdings_insights")
    """
    AI-generated summary of recent insider trading activity.
    """

    news_summary: NewsSummaryBlock = Field(alias="news_summary")
    """
    AI-generated news summary for this symbol.

    Reused from :mod:`yoghurt.models.analysis_insights`; see the module
    docstring.
    """

    options_analysis: OptionsAnalysis = Field(alias="options_analysis")
    """
    Put/call ratio analysis and commentary for this symbol.
    """

    overview: AnalystOverview
    """
    AI-generated high-level overview of this symbol.
    """

    price_movement: PriceMovement = Field(alias="price_movement")
    """
    AI-generated price-movement analysis for this symbol.

    Reused from :mod:`yoghurt.models.analysis_insights`; see the module
    docstring. Wire key is snake_case (``price_movement``), unlike every
    other field in this module that happens to also be spelled snake_case
    but is a single word (so ``to_camel`` cannot tell the difference) —
    this one is genuinely multi-word and needs the explicit alias to avoid
    the auto-generated ``priceMovement``.
    """

    rtr: Rtr
    """
    AI-generated ratings/price-target summary for this symbol.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the analyzed symbol.
    """


# ---------------------------------------------------------------------------
# ratings-top
# ---------------------------------------------------------------------------


class AnalystRatingRow(YahooModel):
    """One analyst's rating row occupying a bucket in a :class:`TopRatingsResult`.

    Carries this analyst's own scores across all four metrics
    (``dir``/``mm``/``pt``/``fin_score``) — distinct from the
    :class:`TopRatingsResult` bucket key of the same name, which instead
    identifies which single metric this analyst is the top pick *for*; see
    that class's docstring.
    """

    adjusted_pt_current: float = Field(alias="adjusted_pt_current")
    """
    This analyst's current price target, adjusted for corporate actions
    (for example stock splits) since it was issued.

    Matches ``pt_current`` on every corpus row.
    """

    analyst: str
    """
    Name of the rating firm (for example ``"CLSA"``, ``"Bernstein"``).
    """

    announcement_date: datetime.date = Field(alias="announcement_date")
    """
    Calendar date this rating was announced, as a bare ``"YYYY-MM-DD"``
    wire string.
    """

    datapoints: int
    """
    Number of historical rating/price-target data points backing this
    analyst's scores.
    """

    dir: RawFloat = Field(alias="dir")
    """
    This analyst's "direction" score.

    Wire key collides with Python's builtin ``dir()``; the field keeps the
    wire name via an explicit alias rather than renaming to avoid shadowing
    (mirrors ``yield_``'s python-keyword resolution in
    :class:`~yoghurt.models.summary_identity.SummaryDetail`, except this
    identifier is a builtin, not a reserved keyword, so no trailing
    underscore is needed on the Python side — only the ``dir=`` positional
    use would shadow the builtin locally, which this model never does).

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire, unlike the sibling
    bucket key of the same name at the :class:`TopRatingsResult` level,
    which is not wrapped; see that class's docstring.
    """

    fin_score: RawFloat = Field(alias="fin_score")
    """
    This analyst's overall financial score.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.
    """

    mm: RawFloat = Field(alias="mm")
    """
    This analyst's "market maker" (or similar) score.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.
    """

    pt: RawFloat = Field(alias="pt")
    """
    This analyst's price-target score.

    Wrapped as ``{"raw": ..., "fmt": ...}`` on the wire.
    """

    pt_current: float = Field(alias="pt_current")
    """
    This analyst's current (unadjusted) price target.

    Matches ``adjusted_pt_current`` on every corpus row.
    """

    rating_current: str = Field(alias="rating_current")
    """
    This analyst's current rating label.

    Only ``"Outperform"``/``"Buy"`` observed across this 2-capture,
    8-row corpus — too thin to type as a closed-vocabulary enum.
    """

    rating_sentiment: int = Field(alias="rating_sentiment")
    """
    Numeric sentiment classification backing ``rating_current``.

    Always ``1`` across this 2-capture, 8-row corpus; too thin to
    characterize its full range.
    """

    ticker: str
    """
    Ticker symbol this rating covers.
    """

    uuid: str
    """
    Unique identifier for this analyst's rating record.
    """


class TopRatingsResult(YahooModel):
    """The ``ratings-top`` endpoint's bare (non-enveloped) single-symbol payload.

    Each of the four keys names a scored metric and holds the single
    analyst rating that currently ranks highest on that metric — not to be
    confused with the identically-named ``dir``/``mm``/``pt``/``fin_score``
    fields nested inside each :class:`AnalystRatingRow`, which are that
    analyst's own scores across all four metrics; see that class's
    docstring. Only 2 populated captures (``AAPL``/``MSFT``); both share
    all four keys, so every field is required.
    """

    dir: AnalystRatingRow = Field(alias="dir")
    """
    The analyst currently ranking highest on the "direction" metric.
    """

    fin_score: AnalystRatingRow = Field(alias="fin_score")
    """
    The analyst currently ranking highest on overall financial score.
    """

    mm: AnalystRatingRow = Field(alias="mm")
    """
    The analyst currently ranking highest on the "market maker" (or
    similar) metric.
    """

    pt: AnalystRatingRow = Field(alias="pt")
    """
    The analyst currently ranking highest on price-target score.
    """
