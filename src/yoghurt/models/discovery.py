"""Typed models for search and instrument lookup.

Reconciled against ``tests/fixtures/corpus/search`` and
``tests/fixtures/corpus/lookup``, captured 2026-07-24.

Search has one unwrapped response object containing heterogeneous result
families. Its ``quotes`` array includes both Yahoo Finance instruments and,
when requested, private-company or cultural-asset profiles. Those non-finance
rows carry ``name``/``permalink`` instead of ``symbol``/``quoteType``. The
``explains`` and ``screenerFieldResults`` arrays were always empty in the
corpus, so their row schemas remain dynamic rather than speculative.

Lookup returns one ``finance.result[0]`` record. Its document schema is stable
across all seven observed asset types; pricing fields are optional because
``fetchPricingData=false`` omits them, while industry fields apply only to
some equities. An unmatched query is a valid result with an empty
``documents`` list.

Live ``fr-FR``/``FR`` probes on 2026-07-26 diverged from the US corpus:
search-news rows omitted ``relatedTickers`` and lookup documents omitted
``rank``. Both fields therefore remain typed but are optional.
"""

from __future__ import annotations

import datetime  # ruff:ignore[typing-only-standard-library-import] - pydantic resolves annotations at runtime
from enum import Enum

from pydantic import Field

from yoghurt.models._base import RawFloat, YahooModel
from yoghurt.models.enums import (  # ruff:ignore[typing-only-first-party-import] - pydantic resolves annotations at runtime
    QuoteType,
)


class LookupQuoteType(str, Enum):
    """Lowercase quote types observed in lookup documents."""

    CRYPTOCURRENCY = "cryptocurrency"
    CURRENCY = "currency"
    EQUITY = "equity"
    ETF = "etf"
    FUTURE = "future"
    INDEX = "index"
    MUTUALFUND = "mutualfund"


class SearchThumbnailResolution(YahooModel):
    """One image rendition in a search-news thumbnail.

    All fields were present on every captured thumbnail resolution.
    """

    height: int
    """Image height in pixels."""

    tag: str
    """Yahoo's rendition label, such as ``"original"`` or ``"140x140"``."""

    url: str
    """Image URL."""

    width: int
    """Image width in pixels."""


class SearchThumbnail(YahooModel):
    """Thumbnail renditions attached to a search-news record."""

    resolutions: list[SearchThumbnailResolution]
    """Available image renditions."""


class SearchNews(YahooModel):
    """One article returned by search (endpoint noun: search-news records)."""

    link: str
    """
    Article URL.

    Observed on: all search-news records.
    """

    provider_publish_time: datetime.datetime
    """
    Article publication time as an aware UTC datetime.

    Observed on: all search-news records.
    """

    publisher: str
    """
    Publisher display name.

    Observed on: all search-news records.
    """

    related_tickers: list[str] | None = None
    """
    Yahoo symbols associated with the article.

    Live-observed as absent on ``fr-FR``/``FR`` search-news records
    (Airbus, 2026-07-26), despite being universal in the US corpus.
    """

    thumbnail: SearchThumbnail | None = None
    """
    Available article imagery.

    Observed on: imaged search-news records.
    """

    title: str
    """
    Article headline.

    Observed on: all search-news records.
    """

    type: str
    """
    Yahoo content type; every captured row used ``"STORY"``.

    Observed on: all search-news records.
    """

    uuid: str
    """
    Yahoo article identifier.

    Observed on: all search-news records.
    """


class SearchQuote(YahooModel):
    """One instrument or non-finance profile returned in search quotes.

    Endpoint noun: search-quote records.
    """

    disp_sec_ind_flag: bool | None = None
    """
    Whether Yahoo displays sector and industry labels.

    Observed on: some equity search-quote records.
    """

    exch_disp: str | None = None
    """
    Human-readable exchange name.

    Observed on: public-instrument search-quote records.
    """

    exchange: str | None = None
    """
    Short exchange code.

    Observed on: public-instrument search-quote records.
    """

    index: str
    """
    Yahoo search index or entity identifier.

    Observed on: all search-quote records.
    """

    industry: str | None = None
    """
    Industry name.

    Observed on: some equity search-quote records.
    """

    industry_disp: str | None = None
    """
    Display-form industry name.

    Observed on: some equity search-quote records.
    """

    is_yahoo_finance: bool
    """
    Whether the row identifies a Yahoo Finance instrument.

    Observed on: all search-quote records.
    """

    long_name: str | None = Field(default=None, alias="longname")
    """
    Long instrument name.

    Observed on: public-instrument search-quote records.
    """

    name: str | None = None
    """
    Private-company or cultural-asset name.

    Observed on: non-finance search-quote records.
    """

    name_change_date: datetime.date | None = None
    """
    Effective calendar date of ``prev_name``.

    Observed on: renamed public-instrument search-quote records.
    """

    permalink: str | None = None
    """
    Private-company or cultural-asset profile slug.

    Observed on: non-finance search-quote records.
    """

    prev_name: str | None = None
    """
    Previous instrument name.

    Observed on: renamed public-instrument search-quote records.
    """

    quote_type: QuoteType | None = None
    """
    Yahoo Finance instrument classification.

    Observed on: public-instrument search-quote records.
    """

    score: float | None = None
    """
    Yahoo search relevance score.

    Observed on: public-instrument search-quote records.
    """

    sector: str | None = None
    """
    Sector name.

    Observed on: some equity search-quote records.
    """

    sector_disp: str | None = None
    """
    Display-form sector name.

    Observed on: some equity search-quote records.
    """

    short_name: str | None = Field(default=None, alias="shortname")
    """
    Short instrument name.

    Observed on: some public-instrument search-quote records.
    """

    symbol: str | None = None
    """
    Yahoo ticker symbol.

    Observed on: public-instrument search-quote records.
    """

    type_disp: str | None = None
    """
    Human-readable instrument classification.

    Observed on: public-instrument search-quote records.
    """


class SearchNavigation(YahooModel):
    """One Yahoo Finance navigation match.

    Endpoint noun: search-navigation records. Yahoo returned either a named
    URL or a ``navType`` token, so no field is universal.
    """

    nav_name: str | None = None
    """
    Navigation item label.

    Observed on: URL search-navigation records.
    """

    nav_type: str | None = None
    """
    Yahoo navigation destination token.

    Observed on: token-only search-navigation records.
    """

    nav_url: str | None = None
    """
    Navigation destination URL.

    Observed on: URL search-navigation records.
    """


class SearchList(YahooModel):
    """One saved-list or predefined-screener match.

    Endpoint noun: search-list records. ``ALGO_WATCHLIST`` and
    ``PREDEFINED_SCREENER`` rows have distinct optional metadata blocks.
    """

    brand_slug: str | None = None
    """
    Owner brand slug.

    Observed on: ALGO_WATCHLIST search-list records.
    """

    canonical_name: str | None = None
    """
    Stable predefined screener name.

    Observed on: PREDEFINED_SCREENER search-list records.
    """

    daily_percent_gain: float | None = None
    """
    Current aggregate daily percentage gain.

    Observed on: ALGO_WATCHLIST search-list records.
    """

    follower_count: int | None = None
    """
    Number of users following the list.

    Observed on: ALGO_WATCHLIST search-list records.
    """

    icon_url: str
    """
    List icon URL.

    Observed on: all search-list records.
    """

    id: str | None = None
    """
    Predefined screener identifier.

    Observed on: PREDEFINED_SCREENER search-list records.
    """

    index: str
    """
    Yahoo list search index.

    Observed on: all search-list records.
    """

    is_premium: bool | None = None
    """
    Whether access to the predefined screener requires a premium tier.

    Observed on: PREDEFINED_SCREENER search-list records.
    """

    name: str | None = None
    """
    Saved-list display name.

    Observed on: ALGO_WATCHLIST search-list records.
    """

    pf_id: str | None = None
    """
    Yahoo portfolio/list identifier.

    Observed on: ALGO_WATCHLIST search-list records.
    """

    score: float
    """
    Yahoo search relevance score.

    Observed on: all search-list records.
    """

    slug: str | None = None
    """
    Saved-list URL slug.

    Observed on: ALGO_WATCHLIST search-list records.
    """

    symbol_count: int | None = None
    """
    Number of instruments in the saved list.

    Observed on: ALGO_WATCHLIST search-list records.
    """

    title: str | None = None
    """
    Predefined screener title.

    Observed on: PREDEFINED_SCREENER search-list records.
    """

    total: int | None = None
    """
    Number of instruments matching the predefined screener.

    Observed on: PREDEFINED_SCREENER search-list records.
    """

    type: str
    """
    Search-list kind.

    Observed on: all search-list records.
    """

    user_id: str | None = None
    """
    Yahoo owner identifier.

    Observed on: ALGO_WATCHLIST search-list records.
    """


class SearchResearchReport(YahooModel):
    """Research-report metadata returned by search.

    Endpoint noun: search-research records.
    """

    author: str | None = None
    """
    Report author, when Yahoo names one.

    Observed on: authored search-research records.
    """

    id: str
    """
    Yahoo report identifier.

    Observed on: all search-research records.
    """

    provider: str
    """
    Research provider.

    Observed on: all search-research records.
    """

    report_date: datetime.datetime
    """
    Report publication time as an aware UTC datetime.

    Observed on: all search-research records.
    """

    report_headline: str
    """
    Report headline.

    Observed on: all search-research records.
    """


class SearchResult(YahooModel):
    """Complete search response.

    Every field was present in all six corpus captures. Empty result families
    remain empty lists rather than ``None``.
    """

    count: int
    """Combined search result count reported by Yahoo."""

    explains: list[dict[str, object]]
    """Explanation rows; always empty in the corpus, so rows stay dynamic."""

    lists: list[SearchList]
    """Matching saved lists and predefined screeners."""

    nav: list[SearchNavigation]
    """Matching Yahoo Finance navigation destinations."""

    news: list[SearchNews]
    """Related news articles."""

    quotes: list[SearchQuote]
    """Public instruments plus requested private or cultural profiles."""

    research_reports: list[SearchResearchReport]
    """Matching research-report metadata."""

    screener_field_results: list[dict[str, object]]
    """Screener-field matches; always empty in the corpus, so rows stay dynamic."""

    time_taken_for_algo_watchlist: int = Field(alias="timeTakenForAlgowatchlist")
    """Yahoo timing metric for saved-list search."""

    time_taken_for_crunchbase: int
    """Yahoo timing metric for private-company search."""

    time_taken_for_cultural_assets: int
    """Yahoo timing metric for cultural-asset search."""

    time_taken_for_nav: int
    """Yahoo timing metric for navigation search."""

    time_taken_for_news: int
    """Yahoo timing metric for news search."""

    time_taken_for_predefined_screener: int
    """Yahoo timing metric for predefined-screener search."""

    time_taken_for_quotes: int
    """Yahoo timing metric for instrument search."""

    time_taken_for_research_reports: int
    """Yahoo timing metric for research-report search."""

    time_taken_for_screener_field: int
    """Yahoo timing metric for screener-field search."""

    time_taken_for_search_lists: int
    """Yahoo timing metric for search-list processing."""

    total_time: int
    """Yahoo's aggregate search timing metric."""


class LookupDocument(YahooModel):
    """One instrument returned by lookup (endpoint noun: lookup documents)."""

    exchange: str
    """
    Short exchange code.

    Observed on: all lookup documents.
    """

    industry_link: str | None = None
    """
    Yahoo Finance industry page URL.

    Observed on: some equity lookup documents.
    """

    industry_name: str | None = None
    """
    Industry display name.

    Observed on: some equity lookup documents.
    """

    quote_type: LookupQuoteType
    """
    Lowercase lookup asset classification.

    Observed on: all lookup documents.
    """

    rank: int | None = None
    """
    Yahoo lookup rank.

    Live-observed as absent on ``fr-FR``/``FR`` lookup documents
    (Airbus, 2026-07-26), despite being universal in the US corpus.
    """

    regular_market_change: RawFloat | None = None
    """
    Current regular-session absolute price change.

    Observed on: pricing-enabled lookup documents.
    """

    regular_market_percent_change: RawFloat | None = None
    """
    Current regular-session percentage price change.

    Observed on: pricing-enabled lookup documents.
    """

    regular_market_price: RawFloat | None = None
    """
    Current regular-session price.

    Observed on: pricing-enabled lookup documents.
    """

    short_name: str | None = None
    """
    Instrument display name; absent on 2 of 45 corpus documents.

    Observed on: most lookup documents.
    """

    symbol: str
    """
    Yahoo ticker symbol.

    Observed on: all lookup documents.
    """


class LookupTotals(YahooModel):
    """Per-type match counts returned by lookup.

    All fields were present in every captured lookup response.
    """

    all: int
    """Matches across all asset types."""

    cryptocurrency: int
    """Cryptocurrency matches."""

    currency: int
    """Currency-pair matches."""

    equity: int
    """Equity matches."""

    etf: int
    """Exchange-traded fund matches."""

    future: int
    """Futures-contract matches."""

    index: int
    """Index matches."""

    mutualfund: int
    """Mutual-fund matches."""

    private_company: int
    """Private-company matches."""


class LookupResult(YahooModel):
    """One lookup result page.

    Every field was present in all eleven corpus captures. ``documents`` is
    empty for an unmatched query.
    """

    count: int
    """Requested page size."""

    documents: list[LookupDocument]
    """Instrument documents in this page."""

    lookup_totals: LookupTotals
    """Available match counts by asset type."""

    start: int
    """Zero-based page offset."""

    total: int
    """Number of documents returned in this page."""
