"""The typed ``Quote`` response model for Yahoo! Finance quote data.

Ported from Doubloon's ``YQuote`` and reconciled against the probe corpus
at ``tests/fixtures/corpus/quote/`` (28 records, 125 distinct keys, captured
2026-07-04). Deviations from Doubloon are called out per-field below;
overall reconciliation notes:

- Wire aliases were corrected where ``to_camel`` disagrees with Yahoo's
  actual spelling: ``forwardPE``, ``trailingPE``, ``stockStoryTopSixURL``,
  and ``stockStoryURL`` all keep their capitalized acronyms on the wire.
- Optionality is evidence-driven: a field is REQUIRED only if its wire
  alias is one of the 35 keys present on every one of the 28 corpus
  records (see ``tests/models/test_quote_corpus.py`` for the pinned set).
  Every other field is optional, including several Doubloon typed as
  required that this corpus never observed as universal.
- Every docstring ends with an applicability line generated from
  ``tools.quote_fields_report``: either an observed quoteType list dated
  to the corpus capture, or a note that the field is Doubloon-only and
  unobserved here.
- ``corporate_actions`` and the ``stock_story*``/crypto-supply/``industry``
  family are new since Doubloon; see ``CorporateAction`` below for the
  nested shape.
- ``options_type`` (observed, wire ``optionsType``, values like ``"Call"``)
  replaces Doubloon's ``option_type`` (wire ``optionType``, unobserved in
  this corpus). The two are not interchangeable: ``optionsType`` values are
  title-cased strings, not the ``OptionType`` enum's upper-case members, so
  ``options_type`` is typed ``str | None`` rather than ``OptionType``.
"""

from __future__ import annotations

import datetime  # noqa: TC003 - required at runtime for pydantic field validation

from pydantic import Field

from yoghurt.models._base import YahooModel

# These types are required in full for serialization purposes
from yoghurt.models.enums import (  # noqa: TC001
    MarketState,
    PriceAlertConfidence,
    QuoteType,
)


class CorporateAction(YahooModel):
    """One corporate action entry on a quote (split, spin-off, and so on).

    Every corpus observation of ``corporateActions`` is an empty list, so
    this sub-model's shape is thinly observed: no real corpus record
    supplies a populated entry to model fields from. It carries no fields
    of its own beyond what :class:`YahooModel` preserves via
    ``model_extra`` until a populated example is captured.

    Not observed in the corpus; known from prior use on EQUITY quotes.
    """


class Quote(YahooModel):
    """Structured representation of financial market quote data from Yahoo! Finance."""

    ask: float | None = None
    """
    Lowest price a seller is willing to accept for the security.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes (corpus
    2026-07-04).
    """

    ask_size: int | None = None
    """
    Number of units available at current ask price.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX quotes (corpus 2026-07-04).
    """

    average_analyst_rating: str | None = None
    """
    Consensus rating from financial analysts for the quote.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    average_daily_volume_10_day: int | None = None
    """
    Average number of shares traded each day over the last 10 days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    average_daily_volume_3_month: int | None = None
    """
    Average number of shares traded each day over the last 3 months.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    bid: float | None = None
    """
    Highest price a buyer is willing to pay for the security.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes (corpus
    2026-07-04).
    """

    bid_size: int | None = None
    """
    Total number of shares that buyers want to buy at the bid price.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX quotes (corpus 2026-07-04).
    """

    book_value: float | None = None
    """
    Net accounting value of a company's assets.

    Observed on: EQUITY, ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    circulating_supply: int | None = None
    """
    Number of cryptocurrency units currently in public circulation.

    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    coin_image_url: str | None = None
    """
    URL of the image representing the cryptocurrency.

    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    coin_market_cap_link: str | None = None
    """
    URL of the MarketCap site for the cryptocurrency.

    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    company_logo_url: str | None = None
    """
    URL of the company's logo, as returned alongside ``logo_url``.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    contract_symbol: bool | None = None
    """
    Whether this quote is identified by a futures contract symbol.

    Applies to FUTURE quotes. Despite the name, the wire value is a
    boolean flag, not a symbol string.

    Observed on: FUTURE quotes (corpus 2026-07-04).
    """

    corporate_actions: list[CorporateAction] | None = None
    """
    Corporate actions (splits, spin-offs, and similar events) on the quote.

    New since Doubloon. Every corpus observation is an empty list; see
    :class:`CorporateAction` for the thinly-observed nested shape.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, OPTION quotes (corpus 2026-07-04).
    """

    crypto_tradeable: bool
    """
    Whether the cryptocurrency can be traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    custom_price_alert_confidence: PriceAlertConfidence
    """
    Value whose meaning is not clear at the moment.

    Seen values have been NONE, LOW and HIGH.
    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    currency: str
    """
    Currency in which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    display_name: str | None = None
    """
    User-friendly name of the quote or security.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    dividend_date: datetime.date | None = None
    """
    Date when the company is expected to pay its next dividend.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    dividend_rate: float | None = None
    """
    Amount of dividends that a company is expected to pay over the next year.

    Observed on: EQUITY, MUTUALFUND quotes (corpus 2026-07-04).
    """

    dividend_yield: float | None = None
    """
    Annual dividend as a percentage of the security's current price.

    Observed on: EQUITY, ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    earnings_call_timestamp_end: int | None = None
    """
    Raw timestamp of the end of the company's earnings call.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    earnings_call_timestamp_start: int | None = None
    """
    Raw timestamp of the start of the company's earnings call.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    earnings_timestamp: int | None = None
    """
    Raw timestamp value of the date and time of the company's earnings announcement.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    earnings_timestamp_end: int | None = None
    """
    Raw timestamp value of the date and time of the end of the company's earnings
    announcement.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    earnings_timestamp_start: int | None = None
    """
    Raw timestamp value of the date and time of the start of the company's earnings
    announcement.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    eps_current_year: float | None = None
    """
    Company's earnings per share (EPS) for the current year.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    eps_forward: float | None = None
    """
    Company's projected earnings per share (EPS) for the next fiscal year.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    eps_trailing_twelve_months: float | None = None
    """
    Company's earnings per share (EPS) for the past 12 months.

    Observed on: EQUITY, ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    esg_populated: bool
    """
    Availability status of ESG ratings data.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    exchange: str
    """
    Securities exchange on which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    exchange_data_delayed_by: int
    """
    Delay in data from the exchange, typically in minutes.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    exchange_timezone_name: str
    """
    Name of the timezone of the exchange.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    exchange_timezone_short_name: str
    """
    Short name of the timezone of the exchange.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    expire_date: datetime.date | None = None
    """
    Date on which the option contract expires.

    Observed on: FUTURE, OPTION quotes (corpus 2026-07-04).
    """

    expire_iso_date: str | None = None
    """
    Date on which the option contract expires, in ISO 8601 format.

    Observed on: FUTURE, OPTION quotes (corpus 2026-07-04).
    """

    fifty_day_average: float | None = None
    """
    Average closing price of the quote over the past 50 trading days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    fifty_day_average_change: float | None = None
    """
    Change in the 50-day average price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    fifty_day_average_change_percent: float | None = None
    """
    Percent change in the 50-day average price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    fifty_two_week_change_percent: float | None = None
    """
    Percentage change in price over the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    fifty_two_week_high: float
    """
    Highest price the quote has traded at in the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    fifty_two_week_high_change: float
    """
    Change in the 52-week high price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    fifty_two_week_high_change_percent: float
    """
    Percent change in the 52-week high price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    fifty_two_week_low: float
    """
    Lowest price the quote has traded at in the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    fifty_two_week_low_change: float
    """
    Change in the 52-week low price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    fifty_two_week_low_change_percent: float
    """
    Percent change in the 52-week low price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    fifty_two_week_range: str
    """
    Trading price range over the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    financial_currency: str | None = None
    """
    Currency in which the company reports its financial results.

    Observed on: EQUITY, ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    first_trade_date_milliseconds: int | None = None
    """
    Raw value of the date and time of first trade of this security, in milliseconds.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    forward_pe: float | None = Field(default=None, alias="forwardPE")
    """
    Projected price-to-earnings ratio for the next 12 months.

    Wire spelling is ``forwardPE`` (capitalized acronym); ``to_camel``
    alone would produce ``forwardPe``, so this field carries an explicit
    alias override.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    from_currency: str | None = None
    """
    Base currency in exchange pair.

    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    from_exchange: str | None = None
    """
    Source exchange for a currency or conversion pair.

    New since Doubloon.
    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    full_exchange_name: str
    """
    Full name of the securities exchange on which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    gmt_off_set_milliseconds: int
    """
    Offset from GMT of the exchange, in milliseconds.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    has_pre_post_market_data: bool
    """
    Whether pre-market and post-market data is available for this quote.

    New since Doubloon.
    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    head_symbol_as_string: str | None = None
    """
    Symbol of the contract's underlying security.

    Observed on: FUTURE quotes (corpus 2026-07-04).
    """

    implied_shares_outstanding: int | None = None
    """
    Shares outstanding implied by market capitalization and price.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    industry: str | None = None
    """
    Industry classification of the company.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    ipo_expected_date: datetime.date | None = None
    """
    Expected date of the initial public offering (IPO).

    Not observed in the corpus; known from prior use on EQUITY quotes.
    """

    is_earnings_date_estimate: bool | None = None
    """
    Whether the earnings announcement date is an estimate rather than confirmed.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    language: str
    """
    Language in which financial results are reported.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    last_market: str | None = None
    """
    Last market in which the security was traded.

    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    logo_url: str | None = None
    """
    URL of the company's logo.

    Observed on: CRYPTOCURRENCY, EQUITY quotes (corpus 2026-07-04).
    """

    long_name: str | None = None
    """
    Official name of the company.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, INDEX, MUTUALFUND, OPTION quotes
    (corpus 2026-07-04).
    """

    market: str
    """
    Primary market for the security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    market_cap: int | None = None
    """
    Total market value of the security in trading currency.

    Observed on: CRYPTOCURRENCY, EQUITY quotes (corpus 2026-07-04).
    """

    market_state: MarketState
    """
    Current state of the market for a security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    max_supply: int | None = None
    """
    Maximum number of cryptocurrency units that will ever exist.

    New since Doubloon.
    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    message_board_id: str | None = None
    """
    Identifier for the Yahoo! Finance message board for this security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, INDEX, MUTUALFUND quotes (corpus
    2026-07-04).
    """

    morningstar_industry: str | None = None
    """
    Morningstar industry classification for the company.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    name_change_date: datetime.date | None = None
    """
    Date on which the company last changed its name.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    net_assets: float | None = None
    """
    Total net assets of the company.

    Observed on: ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    net_expense_ratio: float | None = None
    """
    Ratio of total expenses to total net assets.

    Observed on: ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    open_interest: int | None = None
    """
    Total number of open contracts on a futures or options market.

    Observed on: FUTURE, OPTION quotes (corpus 2026-07-04).
    """

    options_type: str | None = None
    """
    Yahoo option-type metadata returned by quote-page requests.

    Replaces Doubloon's ``option_type`` (wire ``optionType``), which this
    corpus never observed. The corpus-observed wire key is ``optionsType``,
    with values such as ``"Call"`` — title-cased strings, not the
    ``OptionType`` enum's upper-case members — so this field is typed
    ``str | None`` rather than ``OptionType``.

    Observed on: OPTION quotes (corpus 2026-07-04).
    """

    post_market_change: float | None = None
    """
    Change in the security's price in post-market trading.

    Observed on: EQUITY, ETF quotes (corpus 2026-07-04).
    """

    post_market_change_percent: float | None = None
    """
    Percent change in the security's price in post-market trading.

    Observed on: EQUITY, ETF quotes (corpus 2026-07-04).
    """

    post_market_price: float | None = None
    """
    Price of the security in post-market trading.

    Observed on: EQUITY, ETF quotes (corpus 2026-07-04).
    """

    post_market_time: int | None = None
    """
    Raw timestamp of the most recent post-market trade.

    Observed on: EQUITY, ETF quotes (corpus 2026-07-04).
    """

    pre_market_change: float | None = None
    """
    Change in the security's price in pre-market trading.

    Not observed in the corpus; known from prior use on EQUITY quotes.
    """

    pre_market_change_percent: float | None = None
    """
    Percent change in the security's price in pre-market trading.

    Not observed in the corpus; known from prior use on EQUITY quotes.
    """

    pre_market_price: float | None = None
    """
    Price of the security in pre-market trading.

    Not observed in the corpus; known from prior use on EQUITY quotes.
    """

    pre_market_time: int | None = None
    """
    Raw timestamp of the most recent pre-market trade.

    Not observed in the corpus; known from prior use on EQUITY quotes.
    """

    prev_name: str | None = None
    """
    Name of the company prior to its most recent name change.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    price_eps_current_year: float | None = None
    """
    Current-year price-to-earnings ratio.

    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    price_hint: int
    """
    Decimal precision indicator for price values.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    price_to_book: float | None = None
    """
    Market value relative to book value per share.

    Observed on: EQUITY, ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    quartr_id: str | None = None
    """
    Yahoo Quartr identifier for the company's earnings materials.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    quote_source_name: str | None = None
    """
    Name of the source providing the quote.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    quote_type: QuoteType
    """
    Type of quote.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    region: str
    """
    Region in which the company is located.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    regular_market_change: float
    """
    Change in the security's price in regular trading.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    regular_market_change_percent: float
    """
    Percent change in the security's price in regular trading.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    regular_market_day_high: float | None = None
    """
    Highest price during regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes
    (corpus 2026-07-04).
    """

    regular_market_day_low: float | None = None
    """
    Lowest price during regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes
    (corpus 2026-07-04).
    """

    regular_market_day_range: str | None = None
    """
    Price range during regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes
    (corpus 2026-07-04).
    """

    regular_market_open: float | None = None
    """
    Opening price for regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes
    (corpus 2026-07-04).
    """

    regular_market_previous_close: float
    """
    Closing price of the security in the previous regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    regular_market_price: float
    """
    Latest price from regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    regular_market_time: int
    """
    Raw timestamp of the most recent trade in the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    regular_market_volume: int | None = None
    """
    Number of units traded in regular session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes
    (corpus 2026-07-04).
    """

    shares_outstanding: int | None = None
    """
    Number of shares currently held by all shareholders.

    Observed on: EQUITY, ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    short_name: str
    """
    Short, user-friendly name for the quote or security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    source_interval: int
    """
    Interval at which the data source provides updates, in seconds.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    start_date: datetime.date | None = None
    """
    Date on which the coin started trading.

    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    stock_story_is_top_six_this_week: bool | None = None
    """
    Whether the company is featured in StockStory's top-six list this week.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    stock_story_quality: str | None = None
    """
    Yahoo StockStory quality rating for the company.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    stock_story_top_six_url: str | None = Field(
        default=None, alias="stockStoryTopSixURL"
    )
    """
    URL of Yahoo StockStory's top-six-to-buy-this-week page.

    Wire spelling is ``stockStoryTopSixURL`` (capitalized acronym);
    ``to_camel`` alone would produce ``stockStoryTopSixUrl``, so this
    field carries an explicit alias override.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    stock_story_url: str | None = Field(default=None, alias="stockStoryURL")
    """
    URL of the company's Yahoo StockStory page.

    Wire spelling is ``stockStoryURL`` (capitalized acronym); ``to_camel``
    alone would produce ``stockStoryUrl``, so this field carries an
    explicit alias override.

    New since Doubloon.
    Observed on: EQUITY quotes (corpus 2026-07-04).
    """

    strike: float | None = None
    """
    Contractually specified price for options exercise.

    Observed on: OPTION quotes (corpus 2026-07-04).
    """

    symbol: str
    """
    Ticker symbol of the security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    to_currency: str | None = None
    """
    Counter currency in exchange pair.

    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    to_exchange: str | None = None
    """
    Destination exchange for a currency or conversion pair.

    New since Doubloon.
    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    total_supply: int | None = None
    """
    Total number of cryptocurrency units in existence, including those not
    yet in circulation.

    New since Doubloon.
    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    tradeable: bool
    """
    Whether the security is currently tradeable.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    trailing_annual_dividend_rate: float | None = None
    """
    Dividend payment per share over the past 12 months.

    Observed on: EQUITY, ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    trailing_annual_dividend_yield: float | None = None
    """
    Dividend yield over the past 12 months.

    Observed on: EQUITY, ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    trailing_pe: float | None = Field(default=None, alias="trailingPE")
    """
    Trailing price-to-earnings ratio based on past twelve-month results.

    Wire spelling is ``trailingPE`` (capitalized acronym); ``to_camel``
    alone would produce ``trailingPe``, so this field carries an explicit
    alias override.

    Observed on: EQUITY, ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    trailing_three_month_nav_returns: float | None = None
    """
    Trailing 3-month net asset value (NAV) returns.

    Observed on: ETF quotes (corpus 2026-07-04).
    """

    trailing_three_month_returns: float | None = None
    """
    Trailing 3-month returns.

    Observed on: ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """

    triggerable: bool
    """
    Internal Yahoo! Finance flag with undocumented and unknown purpose.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    two_hundred_day_average: float | None = None
    """
    Average closing price of the quote over the past 200 trading days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    two_hundred_day_average_change: float | None = None
    """
    Change in the 200-day average price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    two_hundred_day_average_change_percent: float | None = None
    """
    Percent change in the 200-day average price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND quotes
    (corpus 2026-07-04).
    """

    type_disp: str
    """
    User-friendly representation of the QuoteType.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes (corpus 2026-07-04).
    """

    underlying_exchange_symbol: str | None = None
    """
    Exchange symbol for the underlying asset's trading venue.

    Observed on: FUTURE quotes (corpus 2026-07-04).
    """

    underlying_short_name: str | None = None
    """
    Short name of the underlying security of a derivative.

    Not observed in the corpus; known from prior use on OPTION quotes.
    """

    underlying_symbol: str | None = None
    """
    Ticker symbol of the underlying security of a derivative.

    Observed on: FUTURE, OPTION quotes (corpus 2026-07-04).
    """

    volume_24_hr: int | None = None
    """
    Total trading volume of a cryptocurrency in the past 24 hours.

    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    volume_all_currencies: int | None = None
    """
    Aggregate 24-hour volume across all currency pairs.

    Observed on: CRYPTOCURRENCY quotes (corpus 2026-07-04).
    """

    ytd_return: float | None = None
    """
    Year-to-date return on the security.

    Observed on: ETF, MUTUALFUND quotes (corpus 2026-07-04).
    """
