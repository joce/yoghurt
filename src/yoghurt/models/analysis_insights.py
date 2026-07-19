"""Typed models for the deep AI/research analysis endpoints (batch 3d-1).

Reconciled against the probe corpus at ``tests/fixtures/corpus/``, captured
2026-07-04, widened with 6 cross-asset-class captures per endpoint
(``SPY``/``^GSPC``/``BTC-USD``/``EURUSD=X``/``ES=F`` plus the deliberate
``ZZZZXYZQ`` invalid-symbol probe) on 2026-07-05 — see the P4-1 corpus
reinforcement note in ``tests/fixtures/corpus/README.md``. Regenerate
applicability evidence with ``uv run python -m tools.fields_report <stream>``
after a corpus refresh. This module covers the two deepest, prose-heavy
endpoints of batch 3d-1: ``price-insights`` and ``insights``. The remaining
four (smaller, flatter) batch 3d-1 endpoints live in the sibling
:mod:`yoghurt.models.analysis_events`; see that module's docstring for the
file-split rationale.

**price-insights** (endpoint noun: "price-insights records"). 11 captures
(5 from 2026-07-04, 6 from 2026-07-05) reveal three distinct shape
*variants* of the same per-symbol record, all of which :class:`PriceInsights`
must validate:

- **default** (``AAPL``/``MSFT``/``RY.TO``/``SPY``/``^GSPC``/``BTC-USD``/
  ``EURUSD=X``/``ES=F``/``ZZZZXYZQ``, no ``--modules``/``--ai-modules``
  filter): every field populated on every symbol tried, including every
  non-EQUITY asset class and the deliberate invalid-symbol probe (which
  returns ``has_price_anomaly=True`` with otherwise-empty content rather
  than an error or a thinner shape) — this endpoint's shape does not
  narrow by instrument type or symbol validity, only by the
  ``--modules``/``--ai-modules``/``--check-anomaly`` variants below.
  ``RY.TO``/non-EQUITY/``ZZZZXYZQ`` all still show empty
  ``news``/``aiAnalysis.data`` (thin-coverage symbols, not a distinct
  shape).
- **AI-only** (``AAPL_ai``, ``--ai-modules aiAnalysis``): only
  ``aiAnalysis``/``hasPriceAnomaly`` present; ``newsFirstParty``/
  ``newsThirdParty``/``analystRating`` are entirely absent from the
  payload, not merely empty.
- **anomaly-only** (``AAPL_anomaly``, ``--check-anomaly`` alone): only
  ``hasPriceAnomaly`` present; every other top-level field is absent.

Consequently every :class:`PriceInsights` field except ``has_price_anomaly``
is optional (absent-not-null), evidenced directly by the anomaly-only
variant. Within ``aiAnalysis.data.price_movement.data``,
``recent_insider_transactions``/``recent_analyst_upgrades_summary`` are
``null`` on every capture that has the block at all — the corpus has never
shown a populated value, so both are typed loosely (``object | None``,
always observed null) rather than guessed. ``aiAnalysis.data.price_movement
.debug``/``.news_summary.debug`` are always an empty ``{}`` (a dynamic bag
with no observed keys, typed ``dict[str, object]``).
``analystRating.history`` is always an empty list (row shape unmodeled;
mirrors the :class:`~yoghurt.models.quote.CorporateAction` "observed only
as empty lists" precedent, but as a plain typed-empty list since no
partially-populated example exists to justify a dedicated empty row
model). The ``price_movement``/``news_summary`` sub-trees are an
externally-generated AI-service payload embedded in the Yahoo response:
unlike the rest of yoghurt's modeled endpoints, most of their fields are
already snake_case (or irregularly cased, for example
``SPX_percentage_price_change``) on the wire, so every field in those two
sub-trees carries an explicit ``Field(alias=...)`` rather than relying on
``to_camel``.

**insights** (endpoint noun: "insights reports"). 9 captures (3 from
2026-07-04, 6 from 2026-07-05): ``AAPL``/``MSFT`` are rich EQUITY captures;
``RY.TO``/``^GSPC``/``BTC-USD``/``EURUSD=X``/``ES=F``/``ZZZZXYZQ`` are all
thin, carrying only ``sigDevs``/``symbol`` (``RY.TO`` additionally carries
``recommendation``/``upsell`` — see below); ``SPY`` is the corpus's first
non-EQUITY *rich* capture, carrying ``events``/``instrumentInfo``/
``secReports``/``sigDevs``/``symbol``. Every field but ``sig_devs``/
``symbol`` is therefore optional, evidenced directly by the thin captures.
The 2026-07-05 widening replaces what was previously live-only evidence
(gathered during development against ETF/index/crypto/forex symbols, never
backed by a corpus capture) with real corpus captures: ``SPY`` confirms
``events``/``instrument_info``/``sec_reports`` extend to ETF but
``recommendation``/``upsell``/``company_snapshot``/``reports``/
``upsell_search_d_d`` do not (EQUITY-only, absent even on ``SPY``), and the
index/crypto/forex/futures captures confirm the endpoint thins all the way
down to ``sigDevs``/``symbol`` for those asset classes. Within ``SPY``'s
``instrumentInfo.technicalEvents``, ``sector``/``sectorDirection``/
``sectorScore``/``sectorScoreDescription`` are absent and
``indexDirection``/``indexScore``/``indexScoreDescription`` are present on
two of three outlook terms but absent on the third
(``shortTermOutlook``) — corpus-confirmed instances of the same
per-outlook-row inconsistency the field docstrings already documented from
live observation; ``instrumentInfo.valuation`` thins to ``provider`` alone
on ``SPY``, also corpus-confirmed. ``instrumentInfo.technicalEvents``'s
``direction``/``sectorDirection``/``indexDirection`` fields are typed
``str`` rather than a closed-vocabulary enum: only ``"Bullish"``/
``"Bearish"`` are observed across the 3 populated captures (AAPL/MSFT/SPY),
too thin a base to rule out a ``"Neutral"`` (or similar) member Yahoo may
send. ``InsightsSecReport`` is distinct from
:class:`~yoghurt.models.analysis_events.CalendarEventsResult`'s
``sec_reports`` (the ``calendar-events`` endpoint's differently-shaped,
always-empty SEC filing rows) — no corpus evidence ties the two shapes
together, despite the similar English name.
"""

from __future__ import annotations

import datetime  # ruff:ignore[typing-only-standard-library-import] - pydantic needs this at runtime to resolve annotations
from typing import Annotated

from pydantic import Field

from yoghurt.models._base import YahooModel

# ---------------------------------------------------------------------------
# price-insights
# ---------------------------------------------------------------------------


class PriceInsightsNewsUrl(YahooModel):
    """A ``{"url": ...}`` wrapper used by news-article link fields."""

    url: str
    """
    The wrapped URL.
    """


class PriceInsightsNewsProvider(YahooModel):
    """The ``provider`` block of a :class:`PriceInsightsNewsArticle`."""

    display_name: str
    """
    Human-readable name of the news provider (for example ``"Yahoo
    Finance"``).
    """

    source_id: str
    """
    Provider identifier (for example ``"yahoofinance.com"``).
    """


class PriceInsightsNewsStockTicker(YahooModel):
    """One entry in a news article's ``finance.stockTickers`` list."""

    symbol: str
    """
    Yahoo ticker symbol this article is tagged with.
    """


class PriceInsightsNewsPremiumFinance(YahooModel):
    """The ``finance.premiumFinance`` block of a news article."""

    is_premium_free_news: bool
    """
    Whether this premium article is offered free of charge.
    """

    is_premium_news: bool
    """
    Whether this article requires a premium subscription to read.
    """


class PriceInsightsNewsFinance(YahooModel):
    """The ``finance`` block of a :class:`PriceInsightsNewsArticle`."""

    premium_finance: PriceInsightsNewsPremiumFinance
    """
    Premium-access flags for this article.
    """

    stock_tickers: list[PriceInsightsNewsStockTicker]
    """
    Ticker symbols this article is tagged with.
    """


class PriceInsightsNewsThumbnailResolution(YahooModel):
    """One entry in a news article's ``thumbnail.resolutions`` list."""

    height: int
    """
    Thumbnail image height, in pixels.
    """

    tag: str
    """
    Resolution variant tag (for example ``"resized"``).
    """

    url: str
    """
    URL of this thumbnail resolution.
    """

    width: int
    """
    Thumbnail image width, in pixels.
    """


class PriceInsightsNewsThumbnail(YahooModel):
    """The ``thumbnail`` block of a :class:`PriceInsightsNewsArticle`."""

    resolutions: list[PriceInsightsNewsThumbnailResolution]
    """
    Available thumbnail image resolutions.
    """


class PriceInsightsNewsArticle(YahooModel):
    """One entry in a ``newsFirstParty``/``newsThirdParty`` ``news`` list.

    Thinly evidenced: only 2 populated corpus rows (one per symbol on
    ``AAPL``/``MSFT``); every field is nonetheless present on both, so both
    are typed required.
    """

    canonical_url: PriceInsightsNewsUrl
    """
    Canonical URL wrapper for this article.
    """

    click_through_url: PriceInsightsNewsUrl
    """
    Click-through URL wrapper for this article.
    """

    content_type: str
    """
    Content classification (observed values: ``"STORY"``, ``"VIDEO"``).
    """

    duration: float
    """
    Video duration in seconds; ``0.0`` for non-video content.
    """

    finance: PriceInsightsNewsFinance
    """
    Ticker tagging and premium-access metadata for this article.
    """

    has_video: bool
    """
    Whether this article embeds a video.

    Observed ``false`` on both corpus rows, including the ``"VIDEO"``
    ``content_type`` row.
    """

    id: str
    """
    Unique identifier for this article.
    """

    is_hosted: bool
    """
    Whether Yahoo hosts this content directly.
    """

    preview_url: str | None
    """
    Preview URL for this article.

    Present but ``null`` on both corpus rows.
    """

    provider: PriceInsightsNewsProvider
    """
    Publisher of this article.
    """

    provider_content_url: str
    """
    Provider's own URL for this content.

    Present but empty-string on both corpus rows.
    """

    pub_date: datetime.datetime
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.
    """

    summary: str
    """
    Short summary or dek for this article.
    """

    thumbnail: PriceInsightsNewsThumbnail
    """
    Thumbnail image for this article.
    """

    title: str
    """
    Headline of this article.
    """


class PriceInsightsNewsBlock(YahooModel):
    """The ``newsFirstParty``/``newsThirdParty`` block of a :class:`PriceInsights`."""

    news: list[PriceInsightsNewsArticle]
    """
    News articles in this block, most relevant first.

    Always empty on ``newsFirstParty`` in the corpus; populated only on
    ``newsThirdParty`` for ``AAPL``/``MSFT``.
    """

    rank: int
    """
    Display rank of this block among a symbol's price-insights sections.
    """


class PriceMovementArticle(YahooModel):
    """One entry in ``price_movement.data.recent_news_articles``."""

    article_id: str = Field(alias="article_id")
    """
    Unique identifier for this article.
    """

    provider_name: str = Field(alias="provider_name")
    """
    Publisher display name (for example ``"24/7 Wall St."``).
    """

    provider_url: str = Field(alias="provider_url")
    """
    Publisher's home page URL.
    """

    published_date: datetime.datetime = Field(alias="published_date")
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.
    """

    summary: str
    """
    AI-generated summary of this article's content.
    """

    thumbnail_url: str = Field(alias="thumbnail_url")
    """
    URL of this article's thumbnail image.
    """

    title: str
    """
    Headline of this article.
    """

    yahoo_url: str = Field(alias="yahoo_url")
    """
    Yahoo Finance URL for this article.
    """


class PriceMovementData(YahooModel):
    """The ``price_movement.data`` block: market-context metrics."""

    beta: float
    """
    Beta of the security versus its market benchmark.
    """

    industry: str
    """
    Industry classification (for example ``"Consumer Electronics"``).
    """

    market_benchmark_ticker: str = Field(alias="market_benchmark_ticker")
    """
    Ticker symbol of the market benchmark used for comparison (for example
    ``"SPX"``).
    """

    recent_analyst_upgrades_summary: object | None = Field(
        alias="recent_analyst_upgrades_summary"
    )
    """
    Summary of recent analyst rating changes.

    Always ``null`` in the corpus; true populated shape unknown.
    """

    recent_insider_transactions: object | None = Field(
        alias="recent_insider_transactions"
    )
    """
    Summary of recent insider buy/sell transactions.

    Always ``null`` in the corpus; true populated shape unknown.
    """

    recent_news_articles: list[PriceMovementArticle] = Field(
        alias="recent_news_articles"
    )
    """
    News articles used as context for this price-movement analysis.
    """

    sector: str
    """
    Sector classification (for example ``"Technology"``).
    """

    sector_benchmark_ticker: str = Field(alias="sector_benchmark_ticker")
    """
    Ticker symbol of the sector benchmark used for comparison (for example
    ``"XLK"``).
    """

    sector_percentage_price_change: float = Field(
        alias="sector_percentage_price_change"
    )
    """
    Percentage price change of the sector benchmark over the analysis
    window.
    """

    spx_percentage_price_change: float = Field(alias="SPX_percentage_price_change")
    """
    Percentage price change of the S&P 500 over the analysis window.

    Wire key is irregularly cased (``SPX_percentage_price_change``), unlike
    every sibling field in this block.
    """

    stock_percentage_price_change: float = Field(alias="stock_percentage_price_change")
    """
    Percentage price change of this security over the analysis window.
    """

    stock_ticker: str = Field(alias="stock_ticker")
    """
    Ticker symbol this analysis covers.
    """


class DynamicQuestion(YahooModel):
    """One AI-suggested follow-up question."""

    id: str
    """
    Unique identifier for this suggested question.
    """

    text: str
    """
    The suggested question's text.
    """


class PriceMovementExplanation(YahooModel):
    """The ``price_movement.explanation`` block: AI-generated narrative."""

    bottom_line: str = Field(alias="bottom_line")
    """
    One-sentence takeaway for this price movement.
    """

    observations: dict[str, str]
    """
    Supporting observations, keyed by a dynamic, AI-generated headline
    (for example ``"Market context"``, ``"Jim Cramer support"``) rather
    than a fixed key set.
    """

    tldr: str
    """
    Short AI-generated summary of this price movement.
    """


class PriceMovement(YahooModel):
    """The ``price_movement`` block of an :class:`AiAnalysisData`."""

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this analysis was generated.
    """

    data: PriceMovementData
    """
    Market-context metrics backing this analysis.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.
    """

    dynamic_questions: list[DynamicQuestion] = Field(alias="dynamic_questions")
    """
    Suggested AI follow-up questions.

    Always empty in the corpus for this block (populated only on the
    sibling ``news_summary`` block).
    """

    explanation: PriceMovementExplanation
    """
    AI-generated narrative explaining this price movement.
    """

    id: str
    """
    Unique identifier for this analysis.
    """

    query: str
    """
    Natural-language query this analysis answers (for example ``"Explain
    the price movement in AAPL today"``).
    """

    show_insight: bool = Field(alias="show_insight")
    """
    Whether Yahoo's UI should surface this insight.
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
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this analysis was last updated.

    Matches ``created_at`` on every corpus record.
    """


class NewsSummaryTheme(YahooModel):
    """One entry in ``news_summary.news_summary.themes``."""

    theme_description: str = Field(alias="theme_description")
    """
    Explanation of this theme.
    """

    theme_name: str = Field(alias="theme_name")
    """
    Short name of this theme.
    """


class NewsSummaryDynamicSection(YahooModel):
    """One entry in ``news_summary.news_summary.dynamic_sections``."""

    section_content: str = Field(alias="section_content")
    """
    Body text of this dynamic section.
    """

    section_title: str = Field(alias="section_title")
    """
    Heading of this dynamic section.
    """


class NewsSummaryBody(YahooModel):
    """The nested ``news_summary.news_summary`` block."""

    dynamic_sections: list[NewsSummaryDynamicSection] = Field(alias="dynamic_sections")
    """
    AI-generated topical sections expanding on the summary.
    """

    id: str
    """
    Symbol this summary covers.
    """

    key_events: list[str] = Field(alias="key_events")
    """
    Notable events cited in this summary, as free-text bullet strings.
    """

    summary: str
    """
    Full AI-generated news summary.
    """

    themes: list[NewsSummaryTheme]
    """
    Recurring themes identified across the summarized news.
    """

    tldr: str
    """
    Short AI-generated summary.
    """


class NewsSummaryArticleInfo(YahooModel):
    """One entry in ``news_summary.articles_info``."""

    article_id: str = Field(alias="article_id")
    """
    Unique identifier for this article.
    """

    provider_name: str = Field(alias="provider_name")
    """
    Publisher display name.
    """

    provider_url: str = Field(alias="provider_url")
    """
    Publisher's home page URL.
    """

    published_date: datetime.datetime = Field(alias="published_date")
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.
    """

    thumbnail_url: str = Field(alias="thumbnail_url")
    """
    URL of this article's thumbnail image.
    """

    title: str
    """
    Headline of this article.
    """

    yahoo_url: str = Field(alias="yahoo_url")
    """
    Yahoo Finance URL for this article.
    """


class NewsSummaryBlock(YahooModel):
    """The ``news_summary`` block of an :class:`AiAnalysisData`."""

    articles_info: list[NewsSummaryArticleInfo] = Field(alias="articles_info")
    """
    Source articles backing this news summary.
    """

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this summary was generated.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.
    """

    dynamic_questions: list[DynamicQuestion] = Field(alias="dynamic_questions")
    """
    Suggested AI follow-up questions about this summary.
    """

    generation_start_time: datetime.datetime = Field(alias="generation_start_time")
    """
    Timestamp generation of this summary began.
    """

    id: str
    """
    Unique identifier for this summary.
    """

    limit: int
    """
    Maximum number of source articles considered.
    """

    min_score: float = Field(alias="min_score")
    """
    Minimum relevance score a source article needed to be considered.

    Always ``0.0`` in the corpus.
    """

    news_summary: NewsSummaryBody = Field(alias="news_summary")
    """
    The generated summary content.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the summarized symbol.
    """

    trace_id: str = Field(alias="trace_id")
    """
    Tracing identifier for this summary request.
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this summary was last updated.
    """


class AiAnalysisData(YahooModel):
    """The ``aiAnalysis.data`` block of a :class:`PriceInsights`.

    Always an empty ``{}`` on thin-coverage symbols (the corpus's ``RY.TO``
    example) — see :class:`AiAnalysisBlock`.
    """

    news_summary: NewsSummaryBlock = Field(alias="news_summary")
    """
    AI-generated news summary for this symbol.
    """

    price_movement: PriceMovement
    """
    AI-generated price-movement analysis for this symbol.
    """

    symbol: str
    """
    Ticker symbol this analysis covers.
    """


class AiAnalysisBlock(YahooModel):
    """The ``aiAnalysis`` block of a :class:`PriceInsights`."""

    data: Annotated[
        AiAnalysisData | dict[str, object], Field(union_mode="left_to_right")
    ]
    """
    The AI analysis payload, or an empty ``{}`` on thin-coverage symbols
    (the corpus's ``RY.TO`` example) where Yahoo has no AI analysis to
    report.

    ``union_mode="left_to_right"`` is required here: pydantic's default
    "smart" union mode consistently fails to prefer the more specific
    ``AiAnalysisData`` branch over the permissive ``dict[str, object]``
    branch (verified 3/3 populated corpus captures pick the dict branch
    under smart mode — ``extra="allow"`` makes both branches valid and
    the exact-match dict scores higher), so a real AI analysis would
    otherwise always validate as a bare dict instead of the typed model.
    """

    rank: int
    """
    Display rank of this block among a symbol's price-insights sections.
    """


class AnalystRatingBlock(YahooModel):
    """The ``analystRating`` block of a :class:`PriceInsights`."""

    history: list[object]
    """
    Historical analyst rating changes.

    Always an empty list in the corpus; row shape unmodeled.

    Observed only as empty lists in the corpus.
    """

    rank: int
    """
    Display rank of this block among a symbol's price-insights sections.
    """


class PriceInsights(YahooModel):
    """The ``price-insights`` endpoint's single per-symbol record.

    Every field except ``has_price_anomaly`` is optional (absent, not
    merely null): the corpus's anomaly-only variant (``--check-anomaly``
    alone) omits every other top-level field entirely. See the module
    docstring for the three captured shape variants this model must
    validate.
    """

    ai_analysis: AiAnalysisBlock | None = Field(default=None, alias="aiAnalysis")
    """
    AI-generated analysis for this symbol.

    Absent on the anomaly-only variant; present (with empty ``data``) on
    thin-coverage symbols.
    """

    analyst_rating: AnalystRatingBlock | None = Field(
        default=None, alias="analystRating"
    )
    """
    Analyst rating history for this symbol.

    Absent on the AI-only and anomaly-only variants.
    """

    has_price_anomaly: bool = Field(alias="hasPriceAnomaly")
    """
    Whether Yahoo detected an anomalous price movement for this symbol.

    The only field present on every captured variant, including the
    anomaly-only one.
    """

    news_first_party: PriceInsightsNewsBlock | None = Field(
        default=None, alias="newsFirstParty"
    )
    """
    Yahoo-authored news for this symbol.

    Absent on the AI-only and anomaly-only variants; always empty ``news``
    on the default variant in this corpus.
    """

    news_third_party: PriceInsightsNewsBlock | None = Field(
        default=None, alias="newsThirdParty"
    )
    """
    Third-party-authored news for this symbol.

    Absent on the AI-only and anomaly-only variants.
    """


# ---------------------------------------------------------------------------
# insights
# ---------------------------------------------------------------------------


class TechnicalOutlook(YahooModel):
    """One term's outlook block in :class:`TechnicalEvents`.

    ``direction``/``sector_direction``/``index_direction`` are typed
    ``str``, not a closed-vocabulary enum; see the module docstring.
    Corpus-confirmed (2026-07-05 ``SPY`` capture; see the module docstring):
    ``sector_direction``/``sector_score``/``sector_score_description`` are
    EQUITY-only (absent on ``SPY``'s outlook rows) and
    ``index_direction``/``index_score``/``index_score_description`` are
    present on EQUITY and most ETF captures but absent even on some ETF
    outlooks (``SPY``'s ``shortTermOutlook`` lacked them while its
    ``intermediateTermOutlook``/``longTermOutlook`` had them), so all six
    are optional.
    """

    direction: str
    """
    Overall directional outlook for this term (observed values:
    ``"Bullish"``, ``"Bearish"``).
    """

    index_direction: str | None = Field(default=None, alias="indexDirection")
    """
    Directional outlook for the broader index over this term (observed
    values: ``"Bullish"``, ``"Bearish"``).

    Corpus-confirmed as absent on at least one ETF outlook row (``SPY``'s
    ``shortTermOutlook``) even when sibling outlook rows on the same
    capture carry it; see the class docstring.
    """

    index_score: int | None = Field(default=None, alias="indexScore")
    """
    Strength score backing ``index_direction``.
    """

    index_score_description: str | None = Field(
        default=None, alias="indexScoreDescription"
    )
    """
    Prose description of ``index_score`` (for example ``"Bullish
    Evidence"``).
    """

    score: int
    """
    Strength score backing ``direction``.
    """

    score_description: str = Field(alias="scoreDescription")
    """
    Prose description of ``score`` (for example ``"Very Strong Bullish
    Evidence"``).
    """

    sector_direction: str | None = Field(default=None, alias="sectorDirection")
    """
    Directional outlook for the sector over this term (observed values:
    ``"Bullish"``, ``"Bearish"``).

    Corpus-confirmed as EQUITY-only (absent on every ``SPY`` outlook row);
    see the class docstring.
    """

    sector_score: int | None = Field(default=None, alias="sectorScore")
    """
    Strength score backing ``sector_direction``.
    """

    sector_score_description: str | None = Field(
        default=None, alias="sectorScoreDescription"
    )
    """
    Prose description of ``sector_score``.
    """

    state_description: str = Field(alias="stateDescription")
    """
    Prose summary of the technical state driving this outlook.
    """


class TechnicalEvents(YahooModel):
    """The ``instrumentInfo.technicalEvents`` block of an :class:`Insights`."""

    intermediate_term_outlook: TechnicalOutlook = Field(alias="intermediateTermOutlook")
    """
    Technical outlook over the intermediate term.
    """

    long_term_outlook: TechnicalOutlook = Field(alias="longTermOutlook")
    """
    Technical outlook over the long term.
    """

    provider: str
    """
    Source of this technical analysis (always ``"Trading Central"`` in the
    corpus).
    """

    sector: str | None = None
    """
    Sector classification (for example ``"Technology"``).

    Corpus-confirmed as EQUITY-only (absent on the ``SPY`` capture; see the
    module docstring).
    """

    short_term_outlook: TechnicalOutlook = Field(alias="shortTermOutlook")
    """
    Technical outlook over the short term.
    """


class KeyTechnicals(YahooModel):
    """The ``instrumentInfo.keyTechnicals`` block of an :class:`Insights`."""

    provider: str
    """
    Source of this technical analysis (always ``"Trading Central"`` in the
    corpus).
    """

    resistance: float
    """
    Technical resistance price level.
    """

    stop_loss: float = Field(alias="stopLoss")
    """
    Suggested stop-loss price level.
    """

    support: float
    """
    Technical support price level.
    """


class Valuation(YahooModel):
    """The ``instrumentInfo.valuation`` block of an :class:`Insights`.

    Corpus-confirmed as far thinner on ETF symbols (``SPY`` carries only
    ``provider``) than on the corpus's EQUITY captures; see the module
    docstring.
    """

    color: float | None = None
    """
    Numeric valuation-gauge position (observed range: ``0.0``-``0.5``).

    Corpus-confirmed as EQUITY-only (absent on ``SPY``).
    """

    description: str | None = None
    """
    Prose valuation assessment (for example ``"Overvalued"``, ``"Near Fair
    Value"``).

    Corpus-confirmed as EQUITY-only (absent on ``SPY``).
    """

    discount: str | None = None
    """
    Discount or premium to fair value, as a signed wire percentage string
    (for example ``"-6%"``, ``"14%"``).

    Corpus-confirmed as EQUITY-only (absent on ``SPY``).
    """

    provider: str
    """
    Source of this valuation assessment (always ``"Trading Central"`` in
    the corpus).
    """

    relative_value: str | None = Field(default=None, alias="relativeValue")
    """
    Relative valuation label (for example ``"Premium"``).

    Present on 1 of 2 populated corpus captures.
    """


class InstrumentInfo(YahooModel):
    """The ``instrumentInfo`` block of an :class:`Insights`.

    Absent entirely on the corpus's thin ``RY.TO`` capture.
    """

    key_technicals: KeyTechnicals = Field(alias="keyTechnicals")
    """
    Key technical price levels for this symbol.
    """

    technical_events: TechnicalEvents = Field(alias="technicalEvents")
    """
    Technical outlook across short/intermediate/long terms.
    """

    valuation: Valuation
    """
    Valuation assessment for this symbol.
    """


class CompanySnapshotScores(YahooModel):
    """A ``company``/``sector`` score block in a :class:`CompanySnapshot`.

    Both blocks share this fixed six-metric key vocabulary, but every
    field is optional: live checks during development (not yet backed by
    a corpus capture beyond the two rich EQUITY corpus captures, see the
    module docstring) found ``company`` genuinely drops keys per symbol
    (for example OKLO carries only ``earnings_reports``/
    ``insider_sentiments``; BABA carries ``dividends``/``hiring``/
    ``innovativeness``/``sustainability`` but not ``earnings_reports``),
    unlike the corpus's AAPL/MSFT captures where ``company`` happened to
    carry all six. ``sector`` has only ever been observed with all six
    keys present (always the fixed midpoint ``0.5`` on every metric in
    the corpus — a category-average baseline, not a per-sector-specific
    figure) but is typed the same way for consistency between the two
    uses of this shared model.
    """

    dividends: float | None = None
    """
    Dividend-strength score, on a 0-1 scale.
    """

    earnings_reports: float | None = Field(default=None, alias="earningsReports")
    """
    Earnings-report-strength score, on a 0-1 scale.
    """

    hiring: float | None = None
    """
    Hiring-momentum score, on a 0-1 scale.
    """

    innovativeness: float | None = None
    """
    Innovation score, on a 0-1 scale.
    """

    insider_sentiments: float | None = Field(default=None, alias="insiderSentiments")
    """
    Insider-sentiment score, on a 0-1 scale.
    """

    sustainability: float | None = None
    """
    Sustainability score, on a 0-1 scale.
    """


class CompanySnapshot(YahooModel):
    """The ``companySnapshot`` block of an :class:`Insights`.

    Absent entirely on the corpus's thin ``RY.TO`` capture, and
    live-observed as absent on foreign listings (0700.HK/7203.T/SHEL.L;
    not yet backed by a corpus capture, see the module docstring).
    """

    company: CompanySnapshotScores
    """
    This company's scores.
    """

    sector: CompanySnapshotScores
    """
    Sector-average baseline scores for comparison.
    """

    sector_info: str = Field(alias="sectorInfo")
    """
    Sector classification (for example ``"Technology"``).
    """


class InsightsRecommendation(YahooModel):
    """The ``recommendation`` block of an :class:`Insights`.

    ``rating``/``target_price`` are typed ``str``/``float``, not a
    closed-vocabulary enum or always-required field, respectively; see
    each field's docstring.
    """

    provider: str
    """
    Source of this recommendation (always ``"Argus Research"`` in the
    corpus).
    """

    rating: str
    """
    Recommendation rating (always ``"BUY"`` in the corpus; live-observed
    as also ``"HOLD"``, not yet backed by a corpus capture, see the module
    docstring).
    """

    target_price: float | None = Field(default=None, alias="targetPrice")
    """
    Analyst target price.

    Live-observed as absent on a ``"HOLD"``-rated recommendation (BABA);
    not yet backed by a corpus capture, see the module docstring.
    """


class InsightsUpsell(YahooModel):
    """The ``upsell`` block of an :class:`Insights`."""

    company_name: str = Field(alias="companyName")
    """
    Full company name.
    """


class ResearchReport(YahooModel):
    """The ``upsellSearchDD.researchReports`` block of an :class:`Insights`."""

    investment_rating: str = Field(alias="investmentRating")
    """
    Provider's investment rating (for example ``"Neutral"``,
    ``"Bullish"``).
    """

    provider: str
    """
    Source of this research report (always ``"Morningstar"`` in the
    corpus).
    """

    report_date: datetime.datetime = Field(alias="reportDate")
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.
    """

    report_id: str = Field(alias="reportId")
    """
    Unique identifier for this report.
    """

    summary: str
    """
    Report summary text.
    """

    title: str
    """
    Report title.
    """


class UpsellSearchDD(YahooModel):
    """The ``upsellSearchDD`` block of an :class:`Insights`.

    Absent entirely on the corpus's thin ``RY.TO`` capture.
    """

    research_reports: ResearchReport = Field(alias="researchReports")
    """
    A featured research report for this symbol.
    """


class InsightsEvent(YahooModel):
    """One entry in an :class:`Insights`'s ``events`` list."""

    end_date: datetime.datetime = Field(alias="endDate")
    """
    Point-in-time end of this technical event's window.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime. Matches ``start_date`` on every corpus row.
    """

    event_type: str = Field(alias="eventType")
    """
    Name of the technical event (for example ``"Commodity Channel
    Index"``).
    """

    image_url: str = Field(alias="imageUrl")
    """
    URL of an icon representing this event.
    """

    price_period: str = Field(alias="pricePeriod")
    """
    Price bar period this event was detected on (observed value:
    ``"D"``, daily).
    """

    start_date: datetime.datetime = Field(alias="startDate")
    """
    Point-in-time start of this technical event's window.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime.
    """

    trade_type: str = Field(alias="tradeType")
    """
    Trade direction this event signals (observed value: ``"L"``, long).
    """

    trading_horizon: str = Field(alias="tradingHorizon")
    """
    Trading horizon this event applies to (observed value: ``"S"``,
    short-term).
    """


class InsightsReport(YahooModel):
    """One entry in an :class:`Insights`'s ``reports`` list."""

    head_html: str = Field(alias="headHtml")
    """
    Short headline for this report.
    """

    id: str
    """
    Unique identifier for this report.
    """

    investment_rating: str | None = Field(default=None, alias="investmentRating")
    """
    Provider's investment rating for the discussed security.

    Present only on the corpus's single ``"Analyst Report"``-type row (1 of
    8); absent on every other report type (stock-pick lists, technical
    assessments, thematic portfolios, insider-activity digests).
    """

    provider: str
    """
    Source of this report (always ``"Argus Research"`` in the corpus).
    """

    report_date: datetime.datetime = Field(alias="reportDate")
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.
    """

    report_title: str = Field(alias="reportTitle")
    """
    Full report body text.

    Matches ``title`` on every corpus row (verified); kept as its own wire
    field rather than collapsed, per corpus honesty.
    """

    target_price: float | None = Field(default=None, alias="targetPrice")
    """
    Analyst target price for the discussed security.

    Present only on the corpus's single ``"Analyst Report"``-type row (1 of
    8); see ``investment_rating``.
    """

    tickers: list[str]
    """
    Ticker symbols this report discusses.
    """

    title: str
    """
    Full report body text.

    Matches ``report_title`` on every corpus row; see ``report_title``.
    """


class SignificantDevelopment(YahooModel):
    """One entry in an :class:`Insights`'s ``sigDevs`` list."""

    date: datetime.date
    """
    Calendar date of this development, as a bare ``"YYYY-MM-DD"`` wire
    string.
    """

    headline: str
    """
    Headline describing this significant development.
    """


class InsightsSecReportExhibit(YahooModel):
    """One entry in an :class:`InsightsSecReport`'s ``exhibits`` list."""

    download_url: str | None = Field(default=None, alias="downloadUrl")
    """
    Yahoo redirect URL for downloading this exhibit.

    Present on 34 of 290 corpus exhibits, always alongside ``type:
    "EXCEL"`` (Yahoo's Excel-format financial-report exhibits).
    """

    type: str
    """
    Exhibit type or form code (for example ``"10-Q"``, ``"EX-31.1"``).
    """

    url: str
    """
    URL of the exhibit document.
    """


class InsightsSecReport(YahooModel):
    """One entry in an :class:`Insights`'s ``secReports`` list.

    Distinct from :class:`~yoghurt.models.analysis_events.CalendarEventsResult`'s
    ``sec_reports``; see the module docstring.
    """

    description: str
    """
    Prose description of this filing (for example ``"Quarterly report
    pursuant to Section 13 or 15(d)"``).
    """

    edgar_url: str = Field(alias="edgarUrl")
    """
    URL of the filing's Yahoo Finance SEC-filing page.
    """

    exhibits: list[InsightsSecReportExhibit]
    """
    Individual documents attached to this filing.
    """

    filing_date: datetime.date = Field(alias="filingDate")
    """
    Calendar date the filing was made.

    Wire value is a midnight-UTC-aligned epoch timestamp in milliseconds
    (verified against every corpus value); pydantic converts it to a UTC
    calendar date.
    """

    form_type: str = Field(alias="formType")
    """
    SEC form code (for example ``"10-Q"``, ``"8-K"``).
    """

    id: str
    """
    Unique identifier for this filing.
    """

    snapshot_url: str = Field(alias="snapshotUrl")
    """
    URL of a thumbnail image of this filing.
    """

    title: str
    """
    Filing title (for example ``"10-Q : Periodic Financial Reports"``).
    """

    type: str
    """
    Filing category (for example ``"Periodic Financial Reports"``).
    """


class Insights(YahooModel):
    """The ``insights`` endpoint's single per-symbol record.

    Only ``sig_devs``/``symbol`` are required — corpus-confirmed exactly
    (see the module docstring): the original 3-capture corpus was
    EQUITY-only (AAPL/MSFT rich, RY.TO thin), but the 2026-07-05 cross-asset
    widening (``SPY`` rich-ETF; ``^GSPC``/``BTC-USD``/``EURUSD=X``/``ES=F``/
    ``ZZZZXYZQ`` thin) now backs what was previously live-only evidence:
    ``recommendation``/``upsell``/``company_snapshot``/``reports``/
    ``upsell_search_d_d`` are EQUITY-only in practice (absent even on
    ``SPY``), ``instrument_info``/``events`` extend to ETF but not further
    (absent on index/crypto/forex), and ``sec_reports`` can appear on some
    ETFs (present on ``SPY``) though absent on every non-EQUITY,
    non-``SPY`` capture.
    """

    company_snapshot: CompanySnapshot | None = Field(
        default=None, alias="companySnapshot"
    )
    """
    Company-vs-sector scoring snapshot for this symbol.

    Absent on the corpus's thin ``RY.TO`` capture; corpus-confirmed
    EQUITY-only (absent on ``SPY`` and every index/crypto/forex/futures
    capture). See the module docstring.
    """

    events: list[InsightsEvent] | None = None
    """
    Detected technical events for this symbol.

    Absent on the corpus's thin ``RY.TO`` capture; corpus-confirmed present
    on EQUITY and ETF (``SPY``), absent on index/crypto/forex/futures. See
    the module docstring.
    """

    instrument_info: InstrumentInfo | None = Field(default=None, alias="instrumentInfo")
    """
    Technical outlook, key levels, and valuation for this symbol.

    Absent on the corpus's thin ``RY.TO`` capture; corpus-confirmed present
    on EQUITY and ETF (``SPY``), absent on index/crypto/forex/futures. See
    the module docstring.
    """

    recommendation: InsightsRecommendation | None = None
    """
    Headline analyst recommendation for this symbol.

    Corpus-confirmed EQUITY-only (absent on ``SPY`` and every
    index/crypto/forex/futures capture). See the module docstring.
    """

    reports: list[InsightsReport] | None = None
    """
    Research report summaries mentioning this symbol.

    Absent on the corpus's thin ``RY.TO`` capture; corpus-confirmed
    EQUITY-only. See the module docstring.
    """

    sec_reports: list[InsightsSecReport] | None = Field(
        default=None, alias="secReports"
    )
    """
    Recent SEC filings for this symbol.

    Absent on the corpus's thin ``RY.TO`` capture; corpus-confirmed present
    on EQUITY symbols and at least one ETF (``SPY``). See the module
    docstring.
    """

    sig_devs: list[SignificantDevelopment] = Field(alias="sigDevs")
    """
    Significant recent developments for this symbol.

    The only field, besides ``symbol``, ever observed universal — present
    (though often empty) on every corpus record, EQUITY through
    index/crypto/forex/futures.
    """

    symbol: str
    """
    Yahoo ticker symbol this record covers.
    """

    upsell: InsightsUpsell | None = None
    """
    Basic company identity used for upsell display.

    Corpus-confirmed EQUITY-only (absent on ``SPY`` and every
    index/crypto/forex/futures capture). See the module docstring.
    """

    upsell_search_d_d: UpsellSearchDD | None = None
    """
    A featured research report used for upsell display.

    Absent on the corpus's thin ``RY.TO`` capture.
    """
