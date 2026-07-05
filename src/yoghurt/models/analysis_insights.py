"""Typed models for the deep AI/research analysis endpoints (batch 3d-1).

Reconciled against the probe corpus at ``tests/fixtures/corpus/``, captured
2026-07-04. Regenerate applicability evidence with
``uv run python -m tools.fields_report <stream>`` after a corpus refresh.
This module covers the two deepest, prose-heavy endpoints of batch 3d-1:
``price-insights`` and ``insights``. The remaining four (smaller, flatter)
batch 3d-1 endpoints live in the sibling
:mod:`yoghurt.models.analysis_events`; see that module's docstring for the
file-split rationale.

**price-insights** (endpoint noun: "price-insights records"). Five
captures reveal three distinct shape *variants* of the same per-symbol
record, all of which :class:`PriceInsights` must validate:

- **default** (``AAPL``/``MSFT``/``RY.TO``, no ``--modules``/``--ai-modules``
  filter): every field populated, though ``RY.TO`` still shows empty
  ``news``/``aiAnalysis.data`` (a thin-coverage symbol, not a distinct
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

**insights** (endpoint noun: "insights reports"). Only 3 captures
(``AAPL``, ``MSFT``, ``RY.TO``); ``RY.TO`` is a thin capture carrying only
``recommendation``/``upsell``/``sigDevs`` — every other
:class:`Insights` field is therefore optional, evidenced directly by that
capture rather than assumed. ``instrumentInfo.technicalEvents``'s
``direction``/``sectorDirection``/``indexDirection`` fields are typed
``str`` rather than a closed-vocabulary enum: only ``"Bullish"``/
``"Bearish"`` are observed across the 2 populated captures, too thin a
base to rule out a ``"Neutral"`` (or similar) member Yahoo may send.
``InsightsSecReport`` is distinct from
:class:`~yoghurt.models.analysis_events.CalendarEventsResult`'s
``sec_reports`` (the ``calendar-events`` endpoint's differently-shaped,
always-empty SEC filing rows) — no corpus evidence ties the two shapes
together, despite the similar English name.
"""

from __future__ import annotations

import datetime  # noqa: TC003 - pydantic needs this at runtime to resolve annotations
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

    Observed on: price-insights records.
    """


class PriceInsightsNewsProvider(YahooModel):
    """The ``provider`` block of a :class:`PriceInsightsNewsArticle`."""

    display_name: str
    """
    Human-readable name of the news provider (for example ``"Yahoo
    Finance"``).

    Observed on: price-insights records.
    """

    source_id: str
    """
    Provider identifier (for example ``"yahoofinance.com"``).

    Observed on: price-insights records.
    """


class PriceInsightsNewsStockTicker(YahooModel):
    """One entry in a news article's ``finance.stockTickers`` list."""

    symbol: str
    """
    Yahoo ticker symbol this article is tagged with.

    Observed on: price-insights records.
    """


class PriceInsightsNewsPremiumFinance(YahooModel):
    """The ``finance.premiumFinance`` block of a news article."""

    is_premium_free_news: bool
    """
    Whether this premium article is offered free of charge.

    Observed on: price-insights records.
    """

    is_premium_news: bool
    """
    Whether this article requires a premium subscription to read.

    Observed on: price-insights records.
    """


class PriceInsightsNewsFinance(YahooModel):
    """The ``finance`` block of a :class:`PriceInsightsNewsArticle`."""

    premium_finance: PriceInsightsNewsPremiumFinance
    """
    Premium-access flags for this article.

    Observed on: price-insights records.
    """

    stock_tickers: list[PriceInsightsNewsStockTicker]
    """
    Ticker symbols this article is tagged with.

    Observed on: price-insights records.
    """


class PriceInsightsNewsThumbnailResolution(YahooModel):
    """One entry in a news article's ``thumbnail.resolutions`` list."""

    height: int
    """
    Thumbnail image height, in pixels.

    Observed on: price-insights records.
    """

    tag: str
    """
    Resolution variant tag (for example ``"resized"``).

    Observed on: price-insights records.
    """

    url: str
    """
    URL of this thumbnail resolution.

    Observed on: price-insights records.
    """

    width: int
    """
    Thumbnail image width, in pixels.

    Observed on: price-insights records.
    """


class PriceInsightsNewsThumbnail(YahooModel):
    """The ``thumbnail`` block of a :class:`PriceInsightsNewsArticle`."""

    resolutions: list[PriceInsightsNewsThumbnailResolution]
    """
    Available thumbnail image resolutions.

    Observed on: price-insights records.
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

    Observed on: price-insights records.
    """

    click_through_url: PriceInsightsNewsUrl
    """
    Click-through URL wrapper for this article.

    Observed on: price-insights records.
    """

    content_type: str
    """
    Content classification (observed values: ``"STORY"``, ``"VIDEO"``).

    Observed on: price-insights records.
    """

    duration: float
    """
    Video duration in seconds; ``0.0`` for non-video content.

    Observed on: price-insights records.
    """

    finance: PriceInsightsNewsFinance
    """
    Ticker tagging and premium-access metadata for this article.

    Observed on: price-insights records.
    """

    has_video: bool
    """
    Whether this article embeds a video.

    Observed ``false`` on both corpus rows, including the ``"VIDEO"``
    ``content_type`` row.

    Observed on: price-insights records.
    """

    id: str
    """
    Unique identifier for this article.

    Observed on: price-insights records.
    """

    is_hosted: bool
    """
    Whether Yahoo hosts this content directly.

    Observed on: price-insights records.
    """

    preview_url: str | None
    """
    Preview URL for this article.

    Present but ``null`` on both corpus rows.

    Observed on: price-insights records.
    """

    provider: PriceInsightsNewsProvider
    """
    Publisher of this article.

    Observed on: price-insights records.
    """

    provider_content_url: str
    """
    Provider's own URL for this content.

    Present but empty-string on both corpus rows.

    Observed on: price-insights records.
    """

    pub_date: datetime.datetime
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.

    Observed on: price-insights records.
    """

    summary: str
    """
    Short summary or dek for this article.

    Observed on: price-insights records.
    """

    thumbnail: PriceInsightsNewsThumbnail
    """
    Thumbnail image for this article.

    Observed on: price-insights records.
    """

    title: str
    """
    Headline of this article.

    Observed on: price-insights records.
    """


class PriceInsightsNewsBlock(YahooModel):
    """The ``newsFirstParty``/``newsThirdParty`` block of a :class:`PriceInsights`."""

    news: list[PriceInsightsNewsArticle]
    """
    News articles in this block, most relevant first.

    Always empty on ``newsFirstParty`` in the corpus; populated only on
    ``newsThirdParty`` for ``AAPL``/``MSFT``.

    Observed on: price-insights records.
    """

    rank: int
    """
    Display rank of this block among a symbol's price-insights sections.

    Observed on: price-insights records.
    """


class PriceMovementArticle(YahooModel):
    """One entry in ``price_movement.data.recent_news_articles``."""

    article_id: str = Field(alias="article_id")
    """
    Unique identifier for this article.

    Observed on: price-insights records.
    """

    provider_name: str = Field(alias="provider_name")
    """
    Publisher display name (for example ``"24/7 Wall St."``).

    Observed on: price-insights records.
    """

    provider_url: str = Field(alias="provider_url")
    """
    Publisher's home page URL.

    Observed on: price-insights records.
    """

    published_date: datetime.datetime = Field(alias="published_date")
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.

    Observed on: price-insights records.
    """

    summary: str
    """
    AI-generated summary of this article's content.

    Observed on: price-insights records.
    """

    thumbnail_url: str = Field(alias="thumbnail_url")
    """
    URL of this article's thumbnail image.

    Observed on: price-insights records.
    """

    title: str
    """
    Headline of this article.

    Observed on: price-insights records.
    """

    yahoo_url: str = Field(alias="yahoo_url")
    """
    Yahoo Finance URL for this article.

    Observed on: price-insights records.
    """


class PriceMovementData(YahooModel):
    """The ``price_movement.data`` block: market-context metrics."""

    beta: float
    """
    Beta of the security versus its market benchmark.

    Observed on: price-insights records.
    """

    industry: str
    """
    Industry classification (for example ``"Consumer Electronics"``).

    Observed on: price-insights records.
    """

    market_benchmark_ticker: str = Field(alias="market_benchmark_ticker")
    """
    Ticker symbol of the market benchmark used for comparison (for example
    ``"SPX"``).

    Observed on: price-insights records.
    """

    recent_analyst_upgrades_summary: object | None = Field(
        alias="recent_analyst_upgrades_summary"
    )
    """
    Summary of recent analyst rating changes.

    Always ``null`` in the corpus; true populated shape unknown.

    Observed on: price-insights records.
    """

    recent_insider_transactions: object | None = Field(
        alias="recent_insider_transactions"
    )
    """
    Summary of recent insider buy/sell transactions.

    Always ``null`` in the corpus; true populated shape unknown.

    Observed on: price-insights records.
    """

    recent_news_articles: list[PriceMovementArticle] = Field(
        alias="recent_news_articles"
    )
    """
    News articles used as context for this price-movement analysis.

    Observed on: price-insights records.
    """

    sector: str
    """
    Sector classification (for example ``"Technology"``).

    Observed on: price-insights records.
    """

    sector_benchmark_ticker: str = Field(alias="sector_benchmark_ticker")
    """
    Ticker symbol of the sector benchmark used for comparison (for example
    ``"XLK"``).

    Observed on: price-insights records.
    """

    sector_percentage_price_change: float = Field(
        alias="sector_percentage_price_change"
    )
    """
    Percentage price change of the sector benchmark over the analysis
    window.

    Observed on: price-insights records.
    """

    spx_percentage_price_change: float = Field(alias="SPX_percentage_price_change")
    """
    Percentage price change of the S&P 500 over the analysis window.

    Wire key is irregularly cased (``SPX_percentage_price_change``), unlike
    every sibling field in this block.

    Observed on: price-insights records.
    """

    stock_percentage_price_change: float = Field(alias="stock_percentage_price_change")
    """
    Percentage price change of this security over the analysis window.

    Observed on: price-insights records.
    """

    stock_ticker: str = Field(alias="stock_ticker")
    """
    Ticker symbol this analysis covers.

    Observed on: price-insights records.
    """


class DynamicQuestion(YahooModel):
    """One AI-suggested follow-up question."""

    id: str
    """
    Unique identifier for this suggested question.

    Observed on: price-insights records.
    """

    text: str
    """
    The suggested question's text.

    Observed on: price-insights records.
    """


class PriceMovementExplanation(YahooModel):
    """The ``price_movement.explanation`` block: AI-generated narrative."""

    bottom_line: str = Field(alias="bottom_line")
    """
    One-sentence takeaway for this price movement.

    Observed on: price-insights records.
    """

    observations: dict[str, str]
    """
    Supporting observations, keyed by a dynamic, AI-generated headline
    (for example ``"Market context"``, ``"Jim Cramer support"``) rather
    than a fixed key set.

    Observed on: price-insights records.
    """

    tldr: str
    """
    Short AI-generated summary of this price movement.

    Observed on: price-insights records.
    """


class PriceMovement(YahooModel):
    """The ``price_movement`` block of an :class:`AiAnalysisData`."""

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this analysis was generated.

    Observed on: price-insights records.
    """

    data: PriceMovementData
    """
    Market-context metrics backing this analysis.

    Observed on: price-insights records.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.

    Observed on: price-insights records.
    """

    dynamic_questions: list[DynamicQuestion] = Field(alias="dynamic_questions")
    """
    Suggested AI follow-up questions.

    Always empty in the corpus for this block (populated only on the
    sibling ``news_summary`` block).

    Observed on: price-insights records.
    """

    explanation: PriceMovementExplanation
    """
    AI-generated narrative explaining this price movement.

    Observed on: price-insights records.
    """

    id: str
    """
    Unique identifier for this analysis.

    Observed on: price-insights records.
    """

    query: str
    """
    Natural-language query this analysis answers (for example ``"Explain
    the price movement in AAPL today"``).

    Observed on: price-insights records.
    """

    show_insight: bool = Field(alias="show_insight")
    """
    Whether Yahoo's UI should surface this insight.

    Observed on: price-insights records.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the analyzed symbol.

    Observed on: price-insights records.
    """

    ticker: str
    """
    Ticker symbol this analysis covers.

    Observed on: price-insights records.
    """

    trace_id: str = Field(alias="trace_id")
    """
    Tracing identifier for this analysis request.

    Observed on: price-insights records.
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this analysis was last updated.

    Matches ``created_at`` on every corpus record.

    Observed on: price-insights records.
    """


class NewsSummaryTheme(YahooModel):
    """One entry in ``news_summary.news_summary.themes``."""

    theme_description: str = Field(alias="theme_description")
    """
    Explanation of this theme.

    Observed on: price-insights records.
    """

    theme_name: str = Field(alias="theme_name")
    """
    Short name of this theme.

    Observed on: price-insights records.
    """


class NewsSummaryDynamicSection(YahooModel):
    """One entry in ``news_summary.news_summary.dynamic_sections``."""

    section_content: str = Field(alias="section_content")
    """
    Body text of this dynamic section.

    Observed on: price-insights records.
    """

    section_title: str = Field(alias="section_title")
    """
    Heading of this dynamic section.

    Observed on: price-insights records.
    """


class NewsSummaryBody(YahooModel):
    """The nested ``news_summary.news_summary`` block."""

    dynamic_sections: list[NewsSummaryDynamicSection] = Field(alias="dynamic_sections")
    """
    AI-generated topical sections expanding on the summary.

    Observed on: price-insights records.
    """

    id: str
    """
    Symbol this summary covers.

    Observed on: price-insights records.
    """

    key_events: list[str] = Field(alias="key_events")
    """
    Notable events cited in this summary, as free-text bullet strings.

    Observed on: price-insights records.
    """

    summary: str
    """
    Full AI-generated news summary.

    Observed on: price-insights records.
    """

    themes: list[NewsSummaryTheme]
    """
    Recurring themes identified across the summarized news.

    Observed on: price-insights records.
    """

    tldr: str
    """
    Short AI-generated summary.

    Observed on: price-insights records.
    """


class NewsSummaryArticleInfo(YahooModel):
    """One entry in ``news_summary.articles_info``."""

    article_id: str = Field(alias="article_id")
    """
    Unique identifier for this article.

    Observed on: price-insights records.
    """

    provider_name: str = Field(alias="provider_name")
    """
    Publisher display name.

    Observed on: price-insights records.
    """

    provider_url: str = Field(alias="provider_url")
    """
    Publisher's home page URL.

    Observed on: price-insights records.
    """

    published_date: datetime.datetime = Field(alias="published_date")
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.

    Observed on: price-insights records.
    """

    thumbnail_url: str = Field(alias="thumbnail_url")
    """
    URL of this article's thumbnail image.

    Observed on: price-insights records.
    """

    title: str
    """
    Headline of this article.

    Observed on: price-insights records.
    """

    yahoo_url: str = Field(alias="yahoo_url")
    """
    Yahoo Finance URL for this article.

    Observed on: price-insights records.
    """


class NewsSummaryBlock(YahooModel):
    """The ``news_summary`` block of an :class:`AiAnalysisData`."""

    articles_info: list[NewsSummaryArticleInfo] = Field(alias="articles_info")
    """
    Source articles backing this news summary.

    Observed on: price-insights records.
    """

    created_at: datetime.datetime = Field(alias="created_at")
    """
    Timestamp this summary was generated.

    Observed on: price-insights records.
    """

    debug: dict[str, object]
    """
    Debug metadata bag.

    Always an empty ``{}`` in the corpus.

    Observed on: price-insights records.
    """

    dynamic_questions: list[DynamicQuestion] = Field(alias="dynamic_questions")
    """
    Suggested AI follow-up questions about this summary.

    Observed on: price-insights records.
    """

    generation_start_time: datetime.datetime = Field(alias="generation_start_time")
    """
    Timestamp generation of this summary began.

    Observed on: price-insights records.
    """

    id: str
    """
    Unique identifier for this summary.

    Observed on: price-insights records.
    """

    limit: int
    """
    Maximum number of source articles considered.

    Observed on: price-insights records.
    """

    min_score: float = Field(alias="min_score")
    """
    Minimum relevance score a source article needed to be considered.

    Always ``0.0`` in the corpus.

    Observed on: price-insights records.
    """

    news_summary: NewsSummaryBody = Field(alias="news_summary")
    """
    The generated summary content.

    Observed on: price-insights records.
    """

    symbol_id: str = Field(alias="symbol_id")
    """
    Yahoo's internal identifier for the summarized symbol.

    Observed on: price-insights records.
    """

    trace_id: str = Field(alias="trace_id")
    """
    Tracing identifier for this summary request.

    Observed on: price-insights records.
    """

    updated_at: datetime.datetime = Field(alias="updated_at")
    """
    Timestamp this summary was last updated.

    Observed on: price-insights records.
    """


class AiAnalysisData(YahooModel):
    """The ``aiAnalysis.data`` block of a :class:`PriceInsights`.

    Always an empty ``{}`` on thin-coverage symbols (the corpus's ``RY.TO``
    example) — see :class:`AiAnalysisBlock`.
    """

    news_summary: NewsSummaryBlock = Field(alias="news_summary")
    """
    AI-generated news summary for this symbol.

    Observed on: price-insights records.
    """

    price_movement: PriceMovement
    """
    AI-generated price-movement analysis for this symbol.

    Observed on: price-insights records.
    """

    symbol: str
    """
    Ticker symbol this analysis covers.

    Observed on: price-insights records.
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
    "smart" union mode does not reliably prefer the more specific
    ``AiAnalysisData`` branch over the permissive ``dict[str, object]``
    branch for a populated payload, so a real AI analysis would otherwise
    sometimes validate as a bare dict instead of the typed model.

    Observed on: price-insights records.
    """

    rank: int
    """
    Display rank of this block among a symbol's price-insights sections.

    Observed on: price-insights records.
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

    Observed on: price-insights records.
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

    Observed on: price-insights records.
    """

    analyst_rating: AnalystRatingBlock | None = Field(
        default=None, alias="analystRating"
    )
    """
    Analyst rating history for this symbol.

    Absent on the AI-only and anomaly-only variants.

    Observed on: price-insights records.
    """

    has_price_anomaly: bool = Field(alias="hasPriceAnomaly")
    """
    Whether Yahoo detected an anomalous price movement for this symbol.

    The only field present on every captured variant, including the
    anomaly-only one.

    Observed on: price-insights records.
    """

    news_first_party: PriceInsightsNewsBlock | None = Field(
        default=None, alias="newsFirstParty"
    )
    """
    Yahoo-authored news for this symbol.

    Absent on the AI-only and anomaly-only variants; always empty ``news``
    on the default variant in this corpus.

    Observed on: price-insights records.
    """

    news_third_party: PriceInsightsNewsBlock | None = Field(
        default=None, alias="newsThirdParty"
    )
    """
    Third-party-authored news for this symbol.

    Absent on the AI-only and anomaly-only variants.

    Observed on: price-insights records.
    """


# ---------------------------------------------------------------------------
# insights
# ---------------------------------------------------------------------------


class TechnicalOutlook(YahooModel):
    """One term's outlook block in :class:`TechnicalEvents`.

    ``direction``/``sector_direction``/``index_direction`` are typed
    ``str``, not a closed-vocabulary enum; see the module docstring.
    """

    direction: str
    """
    Overall directional outlook for this term (observed values:
    ``"Bullish"``, ``"Bearish"``).

    Observed on: insights reports.
    """

    index_direction: str = Field(alias="indexDirection")
    """
    Directional outlook for the broader index over this term (observed
    values: ``"Bullish"``, ``"Bearish"``).

    Observed on: insights reports.
    """

    index_score: int = Field(alias="indexScore")
    """
    Strength score backing ``index_direction``.

    Observed on: insights reports.
    """

    index_score_description: str = Field(alias="indexScoreDescription")
    """
    Prose description of ``index_score`` (for example ``"Bullish
    Evidence"``).

    Observed on: insights reports.
    """

    score: int
    """
    Strength score backing ``direction``.

    Observed on: insights reports.
    """

    score_description: str = Field(alias="scoreDescription")
    """
    Prose description of ``score`` (for example ``"Very Strong Bullish
    Evidence"``).

    Observed on: insights reports.
    """

    sector_direction: str = Field(alias="sectorDirection")
    """
    Directional outlook for the sector over this term (observed values:
    ``"Bullish"``, ``"Bearish"``).

    Observed on: insights reports.
    """

    sector_score: int = Field(alias="sectorScore")
    """
    Strength score backing ``sector_direction``.

    Observed on: insights reports.
    """

    sector_score_description: str = Field(alias="sectorScoreDescription")
    """
    Prose description of ``sector_score``.

    Observed on: insights reports.
    """

    state_description: str = Field(alias="stateDescription")
    """
    Prose summary of the technical state driving this outlook.

    Observed on: insights reports.
    """


class TechnicalEvents(YahooModel):
    """The ``instrumentInfo.technicalEvents`` block of an :class:`Insights`."""

    intermediate_term_outlook: TechnicalOutlook = Field(alias="intermediateTermOutlook")
    """
    Technical outlook over the intermediate term.

    Observed on: insights reports.
    """

    long_term_outlook: TechnicalOutlook = Field(alias="longTermOutlook")
    """
    Technical outlook over the long term.

    Observed on: insights reports.
    """

    provider: str
    """
    Source of this technical analysis (always ``"Trading Central"`` in the
    corpus).

    Observed on: insights reports.
    """

    sector: str
    """
    Sector classification (for example ``"Technology"``).

    Observed on: insights reports.
    """

    short_term_outlook: TechnicalOutlook = Field(alias="shortTermOutlook")
    """
    Technical outlook over the short term.

    Observed on: insights reports.
    """


class KeyTechnicals(YahooModel):
    """The ``instrumentInfo.keyTechnicals`` block of an :class:`Insights`."""

    provider: str
    """
    Source of this technical analysis (always ``"Trading Central"`` in the
    corpus).

    Observed on: insights reports.
    """

    resistance: float
    """
    Technical resistance price level.

    Observed on: insights reports.
    """

    stop_loss: float = Field(alias="stopLoss")
    """
    Suggested stop-loss price level.

    Observed on: insights reports.
    """

    support: float
    """
    Technical support price level.

    Observed on: insights reports.
    """


class Valuation(YahooModel):
    """The ``instrumentInfo.valuation`` block of an :class:`Insights`."""

    color: float
    """
    Numeric valuation-gauge position (observed range: ``0.0``-``0.5``).

    Observed on: insights reports.
    """

    description: str
    """
    Prose valuation assessment (for example ``"Overvalued"``, ``"Near Fair
    Value"``).

    Observed on: insights reports.
    """

    discount: str
    """
    Discount or premium to fair value, as a signed wire percentage string
    (for example ``"-6%"``, ``"14%"``).

    Observed on: insights reports.
    """

    provider: str
    """
    Source of this valuation assessment (always ``"Trading Central"`` in
    the corpus).

    Observed on: insights reports.
    """

    relative_value: str | None = Field(default=None, alias="relativeValue")
    """
    Relative valuation label (for example ``"Premium"``).

    Present on 1 of 2 populated corpus captures.

    Observed on: insights reports.
    """


class InstrumentInfo(YahooModel):
    """The ``instrumentInfo`` block of an :class:`Insights`.

    Absent entirely on the corpus's thin ``RY.TO`` capture.
    """

    key_technicals: KeyTechnicals = Field(alias="keyTechnicals")
    """
    Key technical price levels for this symbol.

    Observed on: insights reports.
    """

    technical_events: TechnicalEvents = Field(alias="technicalEvents")
    """
    Technical outlook across short/intermediate/long terms.

    Observed on: insights reports.
    """

    valuation: Valuation
    """
    Valuation assessment for this symbol.

    Observed on: insights reports.
    """


class CompanySnapshotScores(YahooModel):
    """A ``company``/``sector`` score block in a :class:`CompanySnapshot`.

    Both blocks share this fixed six-metric shape (verified against every
    populated corpus capture).
    """

    dividends: float
    """
    Dividend-strength score, on a 0-1 scale.

    Observed on: insights reports.
    """

    earnings_reports: float = Field(alias="earningsReports")
    """
    Earnings-report-strength score, on a 0-1 scale.

    Observed on: insights reports.
    """

    hiring: float
    """
    Hiring-momentum score, on a 0-1 scale.

    Observed on: insights reports.
    """

    innovativeness: float
    """
    Innovation score, on a 0-1 scale.

    Observed on: insights reports.
    """

    insider_sentiments: float = Field(alias="insiderSentiments")
    """
    Insider-sentiment score, on a 0-1 scale.

    Observed on: insights reports.
    """

    sustainability: float
    """
    Sustainability score, on a 0-1 scale.

    Observed on: insights reports.
    """


class CompanySnapshot(YahooModel):
    """The ``companySnapshot`` block of an :class:`Insights`.

    Absent entirely on the corpus's thin ``RY.TO`` capture. ``sector`` is
    always the fixed midpoint ``0.5`` on every metric in the corpus (a
    category-average baseline, not a per-sector-specific figure).
    """

    company: CompanySnapshotScores
    """
    This company's scores.

    Observed on: insights reports.
    """

    sector: CompanySnapshotScores
    """
    Sector-average baseline scores for comparison.

    Observed on: insights reports.
    """

    sector_info: str = Field(alias="sectorInfo")
    """
    Sector classification (for example ``"Technology"``).

    Observed on: insights reports.
    """


class InsightsRecommendation(YahooModel):
    """The ``recommendation`` block of an :class:`Insights`."""

    provider: str
    """
    Source of this recommendation (always ``"Argus Research"`` in the
    corpus).

    Observed on: insights reports.
    """

    rating: str
    """
    Recommendation rating (always ``"BUY"`` in the corpus).

    Observed on: insights reports.
    """

    target_price: float = Field(alias="targetPrice")
    """
    Analyst target price.

    Observed on: insights reports.
    """


class InsightsUpsell(YahooModel):
    """The ``upsell`` block of an :class:`Insights`."""

    company_name: str = Field(alias="companyName")
    """
    Full company name.

    Observed on: insights reports.
    """


class ResearchReport(YahooModel):
    """The ``upsellSearchDD.researchReports`` block of an :class:`Insights`."""

    investment_rating: str = Field(alias="investmentRating")
    """
    Provider's investment rating (for example ``"Neutral"``,
    ``"Bullish"``).

    Observed on: insights reports.
    """

    provider: str
    """
    Source of this research report (always ``"Morningstar"`` in the
    corpus).

    Observed on: insights reports.
    """

    report_date: datetime.datetime = Field(alias="reportDate")
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.

    Observed on: insights reports.
    """

    report_id: str = Field(alias="reportId")
    """
    Unique identifier for this report.

    Observed on: insights reports.
    """

    summary: str
    """
    Report summary text.

    Observed on: insights reports.
    """

    title: str
    """
    Report title.

    Observed on: insights reports.
    """


class UpsellSearchDD(YahooModel):
    """The ``upsellSearchDD`` block of an :class:`Insights`.

    Absent entirely on the corpus's thin ``RY.TO`` capture.
    """

    research_reports: ResearchReport = Field(alias="researchReports")
    """
    A featured research report for this symbol.

    Observed on: insights reports.
    """


class InsightsEvent(YahooModel):
    """One entry in an :class:`Insights`'s ``events`` list."""

    end_date: datetime.datetime = Field(alias="endDate")
    """
    Point-in-time end of this technical event's window.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime. Matches ``start_date`` on every corpus row.

    Observed on: insights reports.
    """

    event_type: str = Field(alias="eventType")
    """
    Name of the technical event (for example ``"Commodity Channel
    Index"``).

    Observed on: insights reports.
    """

    image_url: str = Field(alias="imageUrl")
    """
    URL of an icon representing this event.

    Observed on: insights reports.
    """

    price_period: str = Field(alias="pricePeriod")
    """
    Price bar period this event was detected on (observed value:
    ``"D"``, daily).

    Observed on: insights reports.
    """

    start_date: datetime.datetime = Field(alias="startDate")
    """
    Point-in-time start of this technical event's window.

    Wire value is epoch seconds; pydantic converts it to an aware UTC
    datetime.

    Observed on: insights reports.
    """

    trade_type: str = Field(alias="tradeType")
    """
    Trade direction this event signals (observed value: ``"L"``, long).

    Observed on: insights reports.
    """

    trading_horizon: str = Field(alias="tradingHorizon")
    """
    Trading horizon this event applies to (observed value: ``"S"``,
    short-term).

    Observed on: insights reports.
    """


class InsightsReport(YahooModel):
    """One entry in an :class:`Insights`'s ``reports`` list."""

    head_html: str = Field(alias="headHtml")
    """
    Short headline for this report.

    Observed on: insights reports.
    """

    id: str
    """
    Unique identifier for this report.

    Observed on: insights reports.
    """

    investment_rating: str | None = Field(default=None, alias="investmentRating")
    """
    Provider's investment rating for the discussed security.

    Present only on the corpus's single ``"Analyst Report"``-type row (1 of
    8); absent on every other report type (stock-pick lists, technical
    assessments, thematic portfolios, insider-activity digests).

    Observed on: insights reports.
    """

    provider: str
    """
    Source of this report (always ``"Argus Research"`` in the corpus).

    Observed on: insights reports.
    """

    report_date: datetime.datetime = Field(alias="reportDate")
    """
    Publication timestamp.

    Wire value is an ISO-8601 string with an explicit UTC offset; pydantic
    parses it directly.

    Observed on: insights reports.
    """

    report_title: str = Field(alias="reportTitle")
    """
    Full report body text.

    Matches ``title`` on every corpus row (verified); kept as its own wire
    field rather than collapsed, per corpus honesty.

    Observed on: insights reports.
    """

    target_price: float | None = Field(default=None, alias="targetPrice")
    """
    Analyst target price for the discussed security.

    Present only on the corpus's single ``"Analyst Report"``-type row (1 of
    8); see ``investment_rating``.

    Observed on: insights reports.
    """

    tickers: list[str]
    """
    Ticker symbols this report discusses.

    Observed on: insights reports.
    """

    title: str
    """
    Full report body text.

    Matches ``report_title`` on every corpus row; see ``report_title``.

    Observed on: insights reports.
    """


class SignificantDevelopment(YahooModel):
    """One entry in an :class:`Insights`'s ``sigDevs`` list."""

    date: datetime.date
    """
    Calendar date of this development, as a bare ``"YYYY-MM-DD"`` wire
    string.

    Observed on: insights reports.
    """

    headline: str
    """
    Headline describing this significant development.

    Observed on: insights reports.
    """


class InsightsSecReportExhibit(YahooModel):
    """One entry in an :class:`InsightsSecReport`'s ``exhibits`` list."""

    download_url: str | None = Field(default=None, alias="downloadUrl")
    """
    Yahoo redirect URL for downloading this exhibit.

    Present on 34 of 290 corpus exhibits, always alongside ``type:
    "EXCEL"`` (Yahoo's Excel-format financial-report exhibits).

    Observed on: insights reports.
    """

    type: str
    """
    Exhibit type or form code (for example ``"10-Q"``, ``"EX-31.1"``).

    Observed on: insights reports.
    """

    url: str
    """
    URL of the exhibit document.

    Observed on: insights reports.
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

    Observed on: insights reports.
    """

    edgar_url: str = Field(alias="edgarUrl")
    """
    URL of the filing's Yahoo Finance SEC-filing page.

    Observed on: insights reports.
    """

    exhibits: list[InsightsSecReportExhibit]
    """
    Individual documents attached to this filing.

    Observed on: insights reports.
    """

    filing_date: datetime.date = Field(alias="filingDate")
    """
    Calendar date the filing was made.

    Wire value is a midnight-UTC-aligned epoch timestamp in milliseconds
    (verified against every corpus value); pydantic converts it to a UTC
    calendar date.

    Observed on: insights reports.
    """

    form_type: str = Field(alias="formType")
    """
    SEC form code (for example ``"10-Q"``, ``"8-K"``).

    Observed on: insights reports.
    """

    id: str
    """
    Unique identifier for this filing.

    Observed on: insights reports.
    """

    snapshot_url: str = Field(alias="snapshotUrl")
    """
    URL of a thumbnail image of this filing.

    Observed on: insights reports.
    """

    title: str
    """
    Filing title (for example ``"10-Q : Periodic Financial Reports"``).

    Observed on: insights reports.
    """

    type: str
    """
    Filing category (for example ``"Periodic Financial Reports"``).

    Observed on: insights reports.
    """


class Insights(YahooModel):
    """The ``insights`` endpoint's single per-symbol record.

    Every field except ``recommendation``/``sig_devs``/``symbol``/
    ``upsell`` is optional: the corpus's thin ``RY.TO`` capture omits
    ``company_snapshot``/``events``/``instrument_info``/``reports``/
    ``sec_reports``/``upsell_search_d_d`` entirely. See the module
    docstring.
    """

    company_snapshot: CompanySnapshot | None = Field(
        default=None, alias="companySnapshot"
    )
    """
    Company-vs-sector scoring snapshot for this symbol.

    Absent on the corpus's thin ``RY.TO`` capture.

    Observed on: insights reports.
    """

    events: list[InsightsEvent] | None = None
    """
    Detected technical events for this symbol.

    Absent on the corpus's thin ``RY.TO`` capture.

    Observed on: insights reports.
    """

    instrument_info: InstrumentInfo | None = Field(default=None, alias="instrumentInfo")
    """
    Technical outlook, key levels, and valuation for this symbol.

    Absent on the corpus's thin ``RY.TO`` capture.

    Observed on: insights reports.
    """

    recommendation: InsightsRecommendation
    """
    Headline analyst recommendation for this symbol.

    Observed on: insights reports.
    """

    reports: list[InsightsReport] | None = None
    """
    Research report summaries mentioning this symbol.

    Absent on the corpus's thin ``RY.TO`` capture.

    Observed on: insights reports.
    """

    sec_reports: list[InsightsSecReport] | None = Field(
        default=None, alias="secReports"
    )
    """
    Recent SEC filings for this symbol.

    Absent on the corpus's thin ``RY.TO`` capture.

    Observed on: insights reports.
    """

    sig_devs: list[SignificantDevelopment] = Field(alias="sigDevs")
    """
    Significant recent developments for this symbol.

    Observed on: insights reports.
    """

    symbol: str
    """
    Yahoo ticker symbol this record covers.

    Observed on: insights reports.
    """

    upsell: InsightsUpsell
    """
    Basic company identity used for upsell display.

    Observed on: insights reports.
    """

    upsell_search_d_d: UpsellSearchDD | None = None
    """
    A featured research report used for upsell display.

    Absent on the corpus's thin ``RY.TO`` capture.

    Observed on: insights reports.
    """
