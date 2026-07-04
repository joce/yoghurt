"""The typed ``Quote`` response model for Yahoo! Finance quote data.

Ported from Doubloon's ``YQuote`` and reconciled against the probe corpus
at ``tests/fixtures/corpus/quote/`` (28 records, 125 distinct keys).
Applicability lines derive from the probe corpus captured 2026-07-04;
regenerate with ``tools/quote_fields_report.py`` after a corpus refresh.
Overall reconciliation notes:

- Wire aliases were corrected where ``to_camel`` disagrees with Yahoo's
  actual spelling: ``forwardPE``, ``trailingPE``, ``stockStoryTopSixURL``,
  and ``stockStoryURL`` all keep their capitalized acronyms on the wire.
- Optionality is evidence-driven: a field is REQUIRED only if its wire
  alias is one of the 35 keys present on every one of the 28 corpus
  records (see ``tests/models/test_quote_corpus.py`` for the pinned set).
  Every other field is optional, including several Doubloon typed as
  required that this corpus never observed as universal.
- Every field docstring ends with an applicability line generated from
  ``tools.quote_fields_report``, in one of three forms: an observed
  quoteType list (``Observed on: ... quotes.``), a Doubloon-only note
  (``Not observed in the corpus; known from prior use on ... quotes.``),
  or, for shapes only ever seen empty, ``Observed only as empty lists in
  the corpus.``
- ``corporate_actions`` and the ``stock_story*``/crypto-supply/``industry``
  family are new since Doubloon; see ``CorporateAction`` below for the
  nested shape.
- ``options_type`` (observed, wire ``optionsType``) replaces Doubloon's
  ``option_type`` (wire ``optionType``, unobserved in this corpus). The
  wire values are title-cased (``"Call"``, ``"Put"``), so the field is
  typed with the dedicated :class:`OptionsType` enum, which carries that
  casing.
"""

from __future__ import annotations

import datetime
from functools import cached_property
from typing import overload
from zoneinfo import ZoneInfo

from pydantic import Field

from yoghurt.models._base import YahooModel

# These types are required in full for serialization purposes
from yoghurt.models.enums import (  # noqa: TC001
    MarketState,
    OptionsType,
    PriceAlertConfidence,
    QuoteType,
)


class CorporateAction(YahooModel):
    """One corporate action entry on a quote (split, spin-off, and so on).

    This sub-model's shape is thinly observed: no corpus record supplies a
    populated entry to model fields from. It carries no fields of its own
    beyond what :class:`YahooModel` preserves via ``model_extra`` until a
    populated example is captured — and the corpus gate's nested-extras
    walker fails loudly the moment one appears.

    Observed only as empty lists in the corpus.
    """


class Quote(YahooModel):
    """Structured representation of financial market quote data from Yahoo! Finance.

    Template rule: datetime conveniences derived from epoch fields are plain
    ``@cached_property``, never pydantic ``@computed_field``, so
    ``model_dump()`` stays wire-shaped.
    """

    ask: float | None = None
    """
    Lowest price a seller is willing to accept for the security.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes.
    """

    ask_size: int | None = None
    """
    Number of units available at current ask price.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX quotes.
    """

    average_analyst_rating: str | None = None
    """
    Consensus rating from financial analysts for the quote.

    Observed on: EQUITY quotes.
    """

    average_daily_volume_10_day: int | None = None
    """
    Average number of shares traded each day over the last 10 days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    average_daily_volume_3_month: int | None = None
    """
    Average number of shares traded each day over the last 3 months.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    bid: float | None = None
    """
    Highest price a buyer is willing to pay for the security.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes.
    """

    bid_size: int | None = None
    """
    Total number of shares that buyers want to buy at the bid price.

    Observed on: CURRENCY, EQUITY, ETF, FUTURE, INDEX quotes.
    """

    book_value: float | None = None
    """
    Net accounting value of a company's assets.

    Observed on: EQUITY, ETF, MUTUALFUND quotes.
    """

    circulating_supply: int | None = None
    """
    Number of cryptocurrency units currently in public circulation.

    Observed on: CRYPTOCURRENCY quotes.
    """

    coin_image_url: str | None = None
    """
    URL of the image representing the cryptocurrency.

    Observed on: CRYPTOCURRENCY quotes.
    """

    coin_market_cap_link: str | None = None
    """
    URL of the MarketCap site for the cryptocurrency.

    Observed on: CRYPTOCURRENCY quotes.
    """

    company_logo_url: str | None = None
    """
    URL of the company's logo, as returned alongside ``logo_url``.

    Observed on: EQUITY quotes.
    """

    contract_symbol: bool | None = None
    """
    Whether this quote is identified by a futures contract symbol.

    Applies to FUTURE quotes. Despite the name, the wire value is a
    boolean flag, not a symbol string.

    Observed on: FUTURE quotes.
    """

    corporate_actions: list[CorporateAction] | None = None
    """
    Corporate actions (splits, spin-offs, and similar events) on the quote.

    Every corpus observation is an empty list; see :class:`CorporateAction`
    for the thinly-observed nested shape.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, OPTION quotes.
    """

    crypto_tradeable: bool
    """
    Whether the cryptocurrency can be traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    currency: str
    """
    Currency in which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    custom_price_alert_confidence: PriceAlertConfidence
    """
    Value whose meaning is not clear at the moment.

    Seen values have been NONE, LOW and HIGH.
    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    display_name: str | None = None
    """
    User-friendly name of the quote or security.

    Observed on: EQUITY quotes.
    """

    dividend_date: datetime.date | None = None
    """
    Date when the company is expected to pay its next dividend.

    Observed on: EQUITY quotes.
    """

    dividend_rate: float | None = None
    """
    Amount of dividends that a company is expected to pay over the next year.

    Observed on: EQUITY, MUTUALFUND quotes.
    """

    dividend_yield: float | None = None
    """
    Annual dividend as a percentage of the security's current price.

    Observed on: EQUITY, ETF, MUTUALFUND quotes.
    """

    earnings_call_timestamp_end: int | None = None
    """
    Raw timestamp of the end of the company's earnings call.

    Observed on: EQUITY quotes.
    """

    earnings_call_timestamp_start: int | None = None
    """
    Raw timestamp of the start of the company's earnings call.

    Observed on: EQUITY quotes.
    """

    earnings_timestamp: int | None = None
    """
    Raw timestamp value of the date and time of the company's earnings announcement.

    Observed on: EQUITY quotes.
    """

    earnings_timestamp_end: int | None = None
    """
    Raw timestamp value of the date and time of the end of the company's earnings
    announcement.

    Observed on: EQUITY quotes.
    """

    earnings_timestamp_start: int | None = None
    """
    Raw timestamp value of the date and time of the start of the company's earnings
    announcement.

    Observed on: EQUITY quotes.
    """

    eps_current_year: float | None = None
    """
    Company's earnings per share (EPS) for the current year.

    Observed on: EQUITY quotes.
    """

    eps_forward: float | None = None
    """
    Company's projected earnings per share (EPS) for the next fiscal year.

    Observed on: EQUITY quotes.
    """

    eps_trailing_twelve_months: float | None = None
    """
    Company's earnings per share (EPS) for the past 12 months.

    Observed on: EQUITY, ETF, MUTUALFUND quotes.
    """

    esg_populated: bool
    """
    Availability status of ESG ratings data.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    exchange: str
    """
    Securities exchange on which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    exchange_data_delayed_by: int
    """
    Delay in data from the exchange, typically in minutes.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    exchange_timezone_name: str
    """
    Name of the timezone of the exchange.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    exchange_timezone_short_name: str
    """
    Short name of the timezone of the exchange.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    expire_date: datetime.date | None = None
    """
    Date on which the option contract expires.

    Observed on: FUTURE, OPTION quotes.
    """

    expire_iso_date: str | None = None
    """
    Date on which the option contract expires, in ISO 8601 format.

    Observed on: FUTURE, OPTION quotes.
    """

    fifty_day_average: float | None = None
    """
    Average closing price of the quote over the past 50 trading days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    fifty_day_average_change: float | None = None
    """
    Change in the 50-day average price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    fifty_day_average_change_percent: float | None = None
    """
    Percent change in the 50-day average price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    fifty_two_week_change_percent: float | None = None
    """
    Percentage change in price over the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    fifty_two_week_high: float
    """
    Highest price the quote has traded at in the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    fifty_two_week_high_change: float
    """
    Change in the 52-week high price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    fifty_two_week_high_change_percent: float
    """
    Percent change in the 52-week high price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    fifty_two_week_low: float
    """
    Lowest price the quote has traded at in the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    fifty_two_week_low_change: float
    """
    Change in the 52-week low price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    fifty_two_week_low_change_percent: float
    """
    Percent change in the 52-week low price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    fifty_two_week_range: str
    """
    Trading price range over the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    financial_currency: str | None = None
    """
    Currency in which the company reports its financial results.

    Observed on: EQUITY, ETF, MUTUALFUND quotes.
    """

    first_trade_date_milliseconds: int | None = None
    """
    Raw value of the date and time of first trade of this security, in milliseconds.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    forward_pe: float | None = Field(default=None, alias="forwardPE")
    """
    Projected price-to-earnings ratio for the next 12 months.

    Wire spelling is ``forwardPE`` (capitalized acronym); ``to_camel``
    alone would produce ``forwardPe``, so this field carries an explicit
    alias override.

    Observed on: EQUITY quotes.
    """

    from_currency: str | None = None
    """
    Base currency in exchange pair.

    Observed on: CRYPTOCURRENCY quotes.
    """

    from_exchange: str | None = None
    """
    Source exchange for a currency or conversion pair.

    Observed on: CRYPTOCURRENCY quotes.
    """

    full_exchange_name: str
    """
    Full name of the securities exchange on which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    gmt_off_set_milliseconds: int
    """
    Offset from GMT of the exchange, in milliseconds.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    has_pre_post_market_data: bool
    """
    Whether pre-market and post-market data is available for this quote.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    head_symbol_as_string: str | None = None
    """
    Symbol of the contract's underlying security.

    Observed on: FUTURE quotes.
    """

    implied_shares_outstanding: int | None = None
    """
    Shares outstanding implied by market capitalization and price.

    Observed on: EQUITY quotes.
    """

    industry: str | None = None
    """
    Industry classification of the company.

    Observed on: EQUITY quotes.
    """

    ipo_expected_date: datetime.date | None = None
    """
    Expected date of the initial public offering (IPO).

    Not observed in the corpus; known from prior use on EQUITY quotes.
    """

    is_earnings_date_estimate: bool | None = None
    """
    Whether the earnings announcement date is an estimate rather than confirmed.

    Observed on: EQUITY quotes.
    """

    language: str
    """
    Language in which financial results are reported.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    last_market: str | None = None
    """
    Last market in which the security was traded.

    Observed on: CRYPTOCURRENCY quotes.
    """

    logo_url: str | None = None
    """
    URL of the company's logo.

    Observed on: CRYPTOCURRENCY, EQUITY quotes.
    """

    long_name: str | None = None
    """
    Official name of the company.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, INDEX, MUTUALFUND, OPTION
    quotes.
    """

    market: str
    """
    Primary market for the security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    market_cap: int | None = None
    """
    Total market value of the security in trading currency.

    Observed on: CRYPTOCURRENCY, EQUITY quotes.
    """

    market_state: MarketState
    """
    Current state of the market for a security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    max_supply: int | None = None
    """
    Maximum number of cryptocurrency units that will ever exist.

    Observed on: CRYPTOCURRENCY quotes.
    """

    message_board_id: str | None = None
    """
    Identifier for the Yahoo! Finance message board for this security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, INDEX, MUTUALFUND quotes.
    """

    morningstar_industry: str | None = None
    """
    Morningstar industry classification for the company.

    Observed on: EQUITY quotes.
    """

    name_change_date: datetime.date | None = None
    """
    Date on which the company last changed its name.

    Observed on: EQUITY quotes.
    """

    net_assets: float | None = None
    """
    Total net assets of the company.

    Observed on: ETF, MUTUALFUND quotes.
    """

    net_expense_ratio: float | None = None
    """
    Ratio of total expenses to total net assets.

    Observed on: ETF, MUTUALFUND quotes.
    """

    open_interest: int | None = None
    """
    Total number of open contracts on a futures or options market.

    Observed on: FUTURE, OPTION quotes.
    """

    options_type: OptionsType | None = None
    """
    Type of option contract: the right the contract grants its holder.

    The wire key is ``optionsType`` with title-cased values (``"Call"``,
    ``"Put"``); :class:`OptionsType` carries that casing. See the module
    docstring for the ``option_type`` -> ``options_type`` rename.

    Observed on: OPTION quotes.
    """

    post_market_change: float | None = None
    """
    Change in the security's price in post-market trading.

    Observed on: EQUITY, ETF quotes.
    """

    post_market_change_percent: float | None = None
    """
    Percent change in the security's price in post-market trading.

    Observed on: EQUITY, ETF quotes.
    """

    post_market_price: float | None = None
    """
    Price of the security in post-market trading.

    Observed on: EQUITY, ETF quotes.
    """

    post_market_time: int | None = None
    """
    Raw timestamp of the most recent post-market trade.

    Observed on: EQUITY, ETF quotes.
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

    Observed on: EQUITY quotes.
    """

    price_eps_current_year: float | None = None
    """
    Current-year price-to-earnings ratio.

    Observed on: EQUITY quotes.
    """

    price_hint: int
    """
    Decimal precision indicator for price values.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    price_to_book: float | None = None
    """
    Market value relative to book value per share.

    Observed on: EQUITY, ETF, MUTUALFUND quotes.
    """

    quartr_id: str | None = None
    """
    Yahoo Quartr identifier for the company's earnings materials.

    Observed on: EQUITY quotes.
    """

    quote_source_name: str | None = None
    """
    Name of the source providing the quote.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    quote_type: QuoteType
    """
    Type of quote.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    region: str
    """
    Region in which the company is located.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    regular_market_change: float
    """
    Change in the security's price in regular trading.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    regular_market_change_percent: float
    """
    Percent change in the security's price in regular trading.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    regular_market_day_high: float | None = None
    """
    Highest price during regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes.
    """

    regular_market_day_low: float | None = None
    """
    Lowest price during regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes.
    """

    regular_market_day_range: str | None = None
    """
    Price range during regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes.
    """

    regular_market_open: float | None = None
    """
    Opening price for regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes.
    """

    regular_market_previous_close: float
    """
    Closing price of the security in the previous regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    regular_market_price: float
    """
    Latest price from regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    regular_market_time: int
    """
    Raw timestamp of the most recent trade in the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    regular_market_volume: int | None = None
    """
    Number of units traded in regular session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, OPTION quotes.
    """

    shares_outstanding: int | None = None
    """
    Number of shares currently held by all shareholders.

    Observed on: EQUITY, ETF, MUTUALFUND quotes.
    """

    short_name: str
    """
    Short, user-friendly name for the quote or security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    source_interval: int
    """
    Interval at which the data source provides updates, in seconds.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    start_date: datetime.date | None = None
    """
    Date on which the coin started trading.

    Observed on: CRYPTOCURRENCY quotes.
    """

    stock_story_is_top_six_this_week: bool | None = None
    """
    Whether the company is featured in StockStory's top-six list this week.

    Observed on: EQUITY quotes.
    """

    stock_story_quality: str | None = None
    """
    Yahoo StockStory quality rating for the company.

    Observed on: EQUITY quotes.
    """

    stock_story_top_six_url: str | None = Field(
        default=None, alias="stockStoryTopSixURL"
    )
    """
    URL of Yahoo StockStory's top-six-to-buy-this-week page.

    Wire spelling is ``stockStoryTopSixURL`` (capitalized acronym);
    ``to_camel`` alone would produce ``stockStoryTopSixUrl``, so this
    field carries an explicit alias override.

    Observed on: EQUITY quotes.
    """

    stock_story_url: str | None = Field(default=None, alias="stockStoryURL")
    """
    URL of the company's Yahoo StockStory page.

    Wire spelling is ``stockStoryURL`` (capitalized acronym); ``to_camel``
    alone would produce ``stockStoryUrl``, so this field carries an
    explicit alias override.

    Observed on: EQUITY quotes.
    """

    strike: float | None = None
    """
    Contractually specified price for options exercise.

    Observed on: OPTION quotes.
    """

    symbol: str
    """
    Ticker symbol of the security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    to_currency: str | None = None
    """
    Counter currency in exchange pair.

    Observed on: CRYPTOCURRENCY quotes.
    """

    to_exchange: str | None = None
    """
    Destination exchange for a currency or conversion pair.

    Observed on: CRYPTOCURRENCY quotes.
    """

    total_supply: int | None = None
    """
    Total number of cryptocurrency units in existence, including those not
    yet in circulation.

    Observed on: CRYPTOCURRENCY quotes.
    """

    tradeable: bool
    """
    Whether the security is currently tradeable.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    trailing_annual_dividend_rate: float | None = None
    """
    Dividend payment per share over the past 12 months.

    Observed on: EQUITY, ETF, MUTUALFUND quotes.
    """

    trailing_annual_dividend_yield: float | None = None
    """
    Dividend yield over the past 12 months.

    Observed on: EQUITY, ETF, MUTUALFUND quotes.
    """

    trailing_pe: float | None = Field(default=None, alias="trailingPE")
    """
    Trailing price-to-earnings ratio based on past twelve-month results.

    Wire spelling is ``trailingPE`` (capitalized acronym); ``to_camel``
    alone would produce ``trailingPe``, so this field carries an explicit
    alias override.

    Observed on: EQUITY, ETF, MUTUALFUND quotes.
    """

    trailing_three_month_nav_returns: float | None = None
    """
    Trailing 3-month net asset value (NAV) returns.

    Observed on: ETF quotes.
    """

    trailing_three_month_returns: float | None = None
    """
    Trailing 3-month returns.

    Observed on: ETF, MUTUALFUND quotes.
    """

    triggerable: bool
    """
    Internal Yahoo! Finance flag with undocumented and unknown purpose.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    two_hundred_day_average: float | None = None
    """
    Average closing price of the quote over the past 200 trading days.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    two_hundred_day_average_change: float | None = None
    """
    Change in the 200-day average price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    two_hundred_day_average_change_percent: float | None = None
    """
    Percent change in the 200-day average price from the previous trading day.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND
    quotes.
    """

    type_disp: str
    """
    User-friendly representation of the QuoteType.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX, MUTUALFUND,
    OPTION quotes.
    """

    underlying_exchange_symbol: str | None = None
    """
    Exchange symbol for the underlying asset's trading venue.

    Observed on: FUTURE quotes.
    """

    underlying_short_name: str | None = None
    """
    Short name of the underlying security of a derivative.

    Not observed in the corpus; known from prior use on OPTION quotes.
    """

    underlying_symbol: str | None = None
    """
    Ticker symbol of the underlying security of a derivative.

    Observed on: FUTURE, OPTION quotes.
    """

    volume_24_hr: int | None = None
    """
    Total trading volume of a cryptocurrency in the past 24 hours.

    Observed on: CRYPTOCURRENCY quotes.
    """

    volume_all_currencies: int | None = None
    """
    Aggregate 24-hour volume across all currency pairs.

    Observed on: CRYPTOCURRENCY quotes.
    """

    ytd_return: float | None = None
    """
    Year-to-date return on the security.

    Observed on: ETF, MUTUALFUND quotes.
    """

    # --- Convenience accessors (not part of the wire model) ---

    @cached_property
    def earnings_datetime(self) -> datetime.datetime | None:
        """Date and time of the company's earnings announcement.

        Availability mirrors ``earnings_timestamp``.
        """

        return self._get_datetime(self.earnings_timestamp)

    @cached_property
    def earnings_datetime_end(self) -> datetime.datetime | None:
        """Date and time of the end of the company's earnings announcement.

        Availability mirrors ``earnings_timestamp_end``.
        """

        return self._get_datetime(self.earnings_timestamp_end)

    @cached_property
    def earnings_datetime_start(self) -> datetime.datetime | None:
        """Date and time of the start of the company's earnings announcement.

        Availability mirrors ``earnings_timestamp_start``.
        """

        return self._get_datetime(self.earnings_timestamp_start)

    @cached_property
    def first_trade_datetime(self) -> datetime.datetime | None:
        """Date and time of the first trade of this security.

        Unlike Doubloon's ``YQuote``, this is optional: the source field
        ``first_trade_date_milliseconds`` is absent on OPTION records in
        this corpus, so a non-optional return would be a lie for that
        quote type.

        Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
        MUTUALFUND quotes.
        """

        if self.first_trade_date_milliseconds is None:
            return None
        timestamp_seconds = self.first_trade_date_milliseconds // 1000
        return self._get_datetime(timestamp_seconds)

    @cached_property
    def post_market_datetime(self) -> datetime.datetime | None:
        """Date and time of the most recent post-market trade.

        Observed on: EQUITY, ETF quotes.
        """

        return self._get_datetime(self.post_market_time)

    @cached_property
    def pre_market_datetime(self) -> datetime.datetime | None:
        """Date and time of the most recent pre-market trade.

        Not observed in the corpus; known from prior use on EQUITY quotes.
        """

        return self._get_datetime(self.pre_market_time)

    @cached_property
    def regular_market_datetime(self) -> datetime.datetime:
        """Date and time of the most recent trade in the regular trading session.

        Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
        MUTUALFUND, OPTION quotes.
        """

        return self._get_datetime(self.regular_market_time)

    @overload
    def _get_datetime(self, timestamp: int) -> datetime.datetime: ...

    @overload
    def _get_datetime(self, timestamp: None) -> None: ...

    def _get_datetime(self, timestamp: int | None) -> datetime.datetime | None:
        """Convert an epoch timestamp in seconds to an aware datetime.

        Args:
            timestamp: Epoch timestamp in UTC seconds, or None.

        Returns:
            Timezone-aware datetime anchored to ``exchange_timezone_name``,
            or None if ``timestamp`` is None.
        """

        if timestamp is None:
            return None

        tz_info = ZoneInfo(self.exchange_timezone_name)
        return datetime.datetime.fromtimestamp(timestamp, tz_info)

    def __repr__(self) -> str:
        """Return a compact developer-friendly representation.

        The default pydantic repr lists all 131 fields, which is unusable
        for a model this wide; this mirrors Doubloon's symbol-forward
        convention instead.
        """

        return (
            f"Quote(symbol={self.symbol!r}, "
            f"regular_market_price={self.regular_market_price!r}, "
            f"quote_type={self.quote_type!r})"
        )
