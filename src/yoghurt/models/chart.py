"""Typed ``ChartMeta``/``ChartEvents`` response models for chart and spark data.

Reconciled against the probe corpus at ``tests/fixtures/corpus/chart/`` (24
valid captures, excluding the deliberate invalid-symbol probe) and
``tests/fixtures/corpus/spark/`` (24 valid captures), captured 2026-07-04.
``ChartMeta`` models the meta block shared verbatim by both endpoints
(``chart.result[0].meta`` and ``spark.result[].response[].meta``); the
combined 48-record stream is this module's evidence base for
applicability and requiredness. Regenerate with
``uv run python -m tools.fields_report chart-and-spark-meta`` after a
corpus refresh. Reconciliation notes:

- ``previousClose``, ``scale``, and ``tradingPeriods`` are present on every
  spark meta except the MUTUALFUND capture (Yahoo omits them for mutual
  funds), and are otherwise absent from chart meta except one intraday
  chart capture (``chart/AAPL_1m.json``) that happens to carry all three.
  None of the three is universal across the combined stream, so all three
  are optional.
- ``longName``, ``regularMarketDayHigh``, ``regularMarketDayLow``, and
  ``regularMarketVolume`` are each absent from exactly one MUTUALFUND
  capture and are optional for the same reason.
- ``instrument_type`` is typed :class:`~yoghurt.models.enums.QuoteType`: every
  observed ``instrumentType`` value (CRYPTOCURRENCY, CURRENCY, EQUITY, ETF,
  FUTURE, INDEX, MUTUALFUND) is a ``QuoteType`` member.
- ``first_trade_date`` and ``regular_market_time`` are point-in-time epochs
  with in-model timezone context (``exchange_timezone_name``): per the
  three-tier epoch ruling (see ``AGENTS.md``), the wire ``int`` stays and
  each gets a ``first_trade_datetime``/``regular_market_datetime``
  ``@cached_property`` convenience localized via
  :class:`~zoneinfo.ZoneInfo`, mirroring the
  :class:`~yoghurt.models.quote.Quote` template.
- ``TradingPeriod.start``/``end`` are point-in-time epochs whose only
  in-model timezone context is a short abbreviation (``timezone``, for
  example ``"EDT"``) that :class:`~zoneinfo.ZoneInfo` cannot resolve, so
  their ``start_datetime``/``end_datetime`` conveniences localize via a
  fixed-offset timezone built from ``gmtoffset`` instead.
- Chart events (``chart.result[0].events``) are observed only as a
  ``dividends`` block keyed by epoch-second string
  (``MSFT_1y_events.json``, ``BAC-PL.json``); no capture has ever shown
  ``splits`` or ``earnings``, so ``ChartSplit`` is modeled from prior use
  only and earnings events are deliberately not modeled at all.
  ``ChartDividend.date`` is confirmed (against every observed entry) to be
  a session timestamp rather than a midnight-aligned calendar date, and
  carries no in-model timezone context, so it is typed an aware UTC
  ``datetime.datetime`` despite its wire name — the ruling's Tier 3.
  ``ChartSplit.date`` is unobserved but shares the events-block mechanism
  and session-timestamp semantics of its dividend sibling, so it follows
  the same Tier 3 typing (aware UTC ``datetime.datetime``).
- The applicability lines below use "Observed on: <types> charts." rather
  than "quotes.", since the evidence stream here is chart/spark meta
  records (kind = instrumentType), not quoteResponse records.
"""

from __future__ import annotations

import datetime
from functools import cached_property
from zoneinfo import ZoneInfo

from pydantic import Field

from yoghurt.models._base import YahooModel

# QuoteType is required in full for serialization purposes
from yoghurt.models.enums import (
    QuoteType,  # ruff:ignore[typing-only-first-party-import]
)


class TradingPeriod(YahooModel):
    """One trading-session window (pre-market, regular, post-market, or spark bar).

    Appears as each of ``currentTradingPeriod``'s ``pre``/``regular``/``post``
    entries (universal across the combined chart+spark meta corpus) and as
    the inner elements of spark's ``tradingPeriods`` (present whenever
    ``tradingPeriods`` itself is present).
    """

    end: int
    """
    End of the trading period, as an epoch timestamp in seconds.

    See ``end_datetime`` for a timezone-aware convenience localized via a
    fixed offset built from ``gmtoffset``.
    """

    gmtoffset: int
    """
    Offset from GMT of the trading period, in seconds.
    """

    start: int
    """
    Start of the trading period, as an epoch timestamp in seconds.

    See ``start_datetime`` for a timezone-aware convenience localized via a
    fixed offset built from ``gmtoffset``.
    """

    timezone: str
    """
    Timezone abbreviation in effect for the trading period.
    """

    # --- Convenience accessors (not part of the wire model) ---

    @cached_property
    def start_datetime(self) -> datetime.datetime:
        """Start of the trading period as an aware datetime.

        ``timezone`` is a short abbreviation (for example ``"EDT"``) that
        :class:`~zoneinfo.ZoneInfo` cannot resolve, so this localizes via a
        fixed-offset timezone built from ``gmtoffset`` instead of anchoring
        to a named zone.

        Availability mirrors ``start``.
        """

        return datetime.datetime.fromtimestamp(self.start, self._fixed_offset())

    @cached_property
    def end_datetime(self) -> datetime.datetime:
        """End of the trading period as an aware datetime.

        ``timezone`` is a short abbreviation (for example ``"EDT"``) that
        :class:`~zoneinfo.ZoneInfo` cannot resolve, so this localizes via a
        fixed-offset timezone built from ``gmtoffset`` instead of anchoring
        to a named zone.

        Availability mirrors ``end``.
        """

        return datetime.datetime.fromtimestamp(self.end, self._fixed_offset())

    def _fixed_offset(self) -> datetime.timezone:
        """Build the fixed-offset timezone backing this period's datetimes.

        Returns:
            A fixed-offset timezone built from ``gmtoffset``, since
            ``timezone`` is a short abbreviation ZoneInfo cannot resolve.
        """

        return datetime.timezone(datetime.timedelta(seconds=self.gmtoffset))


class CurrentTradingPeriod(YahooModel):
    """The pre-market, regular, and post-market windows for the current session."""

    post: TradingPeriod
    """
    The post-market trading window.
    """

    pre: TradingPeriod
    """
    The pre-market trading window.
    """

    regular: TradingPeriod
    """
    The regular trading session window.
    """


class ChartMeta(YahooModel):
    """Metadata shared by ``chart`` and ``spark`` responses.

    ``chart.result[0].meta`` and ``spark.result[].response[].meta`` are the
    same shape on the wire; this model is validated against both streams
    (see ``tests/models/test_chart_corpus.py``).
    """

    chart_previous_close: float
    """
    Closing price of the security in the previous session, as reported by
    the chart endpoint.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    currency: str
    """
    Currency in which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    current_trading_period: CurrentTradingPeriod
    """
    The current session's pre-market, regular, and post-market windows.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    data_granularity: str
    """
    Interval between data points in the chart (for example, ``"1d"``).

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    exchange_name: str
    """
    Short code of the securities exchange on which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    exchange_timezone_name: str
    """
    Name of the timezone of the exchange.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    fifty_two_week_high: float
    """
    Highest price the security has traded at in the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    fifty_two_week_low: float
    """
    Lowest price the security has traded at in the past 52 weeks.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    first_trade_date: int
    """
    Epoch timestamp in seconds of the first trade of this security.

    See ``first_trade_datetime`` for a timezone-aware convenience localized
    via ``exchange_timezone_name``.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    full_exchange_name: str
    """
    Full name of the securities exchange on which the security is traded.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    gmtoffset: int
    """
    Offset from GMT of the exchange, in seconds.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    has_pre_post_market_data: bool
    """
    Whether pre-market and post-market data is available for this security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    instrument_type: QuoteType
    """
    Type of financial instrument.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    long_name: str | None = None
    """
    Official name of the company or security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, INDEX, MUTUALFUND
    charts.
    """

    previous_close: float | None = None
    """
    Closing price of the security in the previous session.

    Absent from every chart capture but one (an intraday request); present
    on every spark capture except MUTUALFUND, where Yahoo omits it.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX
    charts.
    """

    price_hint: int
    """
    Decimal precision indicator for price values.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    range: str
    """
    The requested chart range (empty string when the request used explicit
    ``period1``/``period2`` bounds instead of a named range).

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    regular_market_day_high: float | None = None
    """
    Highest price during the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX
    charts.
    """

    regular_market_day_low: float | None = None
    """
    Lowest price during the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX
    charts.
    """

    regular_market_price: float
    """
    Latest price from the regular trading session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    regular_market_time: int
    """
    Epoch timestamp in seconds of the most recent trade in the regular
    trading session.

    See ``regular_market_datetime`` for a timezone-aware convenience
    localized via ``exchange_timezone_name``.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    regular_market_volume: int | None = None
    """
    Number of units traded in the regular session.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX
    charts.
    """

    scale: int | None = None
    """
    Scale factor applied to spark price values.

    Absent from every chart capture but one (an intraday request); present
    on every spark capture except MUTUALFUND, where Yahoo omits it.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX
    charts.
    """

    short_name: str
    """
    Short, user-friendly name for the security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    symbol: str
    """
    Ticker symbol of the security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    timezone: str
    """
    Timezone abbreviation in effect at the exchange.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    trading_periods: list[list[TradingPeriod]] | None = None
    """
    Spark bar trading-period windows, one inner list per requested day.

    Absent from every chart capture; present on every spark capture except
    MUTUALFUND, where Yahoo omits it.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX
    charts.
    """

    valid_ranges: list[str]
    """
    Chart ranges Yahoo accepts for this security.

    Observed on: CRYPTOCURRENCY, CURRENCY, EQUITY, ETF, FUTURE, INDEX,
    MUTUALFUND charts.
    """

    # --- Convenience accessors (not part of the wire model) ---

    @cached_property
    def regular_market_datetime(self) -> datetime.datetime:
        """Date and time of the most recent trade in the regular trading session.

        Availability mirrors ``regular_market_time``.
        """

        return self._get_datetime(self.regular_market_time)

    @cached_property
    def first_trade_datetime(self) -> datetime.datetime:
        """Date and time of the first trade of this security.

        Availability mirrors ``first_trade_date``.
        """

        return self._get_datetime(self.first_trade_date)

    def _get_datetime(self, timestamp: int) -> datetime.datetime:
        """Convert an epoch timestamp in seconds to an aware datetime.

        Args:
            timestamp: Epoch timestamp in UTC seconds.

        Returns:
            Timezone-aware datetime anchored to ``exchange_timezone_name``.
        """

        tz_info = ZoneInfo(self.exchange_timezone_name)
        return datetime.datetime.fromtimestamp(timestamp, tz_info)

    def __repr__(self) -> str:
        """Return a compact developer-friendly representation."""

        return (
            f"ChartMeta(symbol={self.symbol!r}, "
            f"regular_market_price={self.regular_market_price!r}, "
            f"instrument_type={self.instrument_type!r})"
        )


class ChartDividend(YahooModel):
    """One dividend event entry in a chart response's events block."""

    amount: float
    """
    Dividend amount paid per share.

    Not observed in the corpus; known from prior use on EQUITY charts.
    """

    date: datetime.datetime
    """
    Date and time of the dividend event.

    Despite the wire name ``date``, the value is a session timestamp (for
    example, 13:30 UTC on a US market day), not a midnight-aligned
    calendar date — confirmed against every observed dividend entry in the
    corpus. There is no in-model timezone context to localize against, so
    pydantic converts the epoch-seconds wire value to an aware UTC
    datetime; the field keeps its wire name despite the type.
    """


class ChartSplit(YahooModel):
    """One stock-split event entry in a chart response's events block.

    Never observed in the corpus (only ``dividends`` events have been
    captured); modeled from prior use so ``ChartEvents.splits`` has a typed
    shape ready the day Yahoo returns one.
    """

    date: datetime.datetime
    """
    Date and time of the split event, timezone-aware in UTC.

    Yahoo sends an epoch-seconds session timestamp here, mirroring
    ``ChartDividend.date`` (tier 3: no in-model timezone context).

    Not observed in the corpus; known from prior use on EQUITY charts.
    """

    denominator: int
    """
    Denominator of the split ratio (for example, 2 in a 2-for-1 split).

    Not observed in the corpus; known from prior use on EQUITY charts.
    """

    numerator: int
    """
    Numerator of the split ratio (for example, 1 in a 2-for-1 split).

    Not observed in the corpus; known from prior use on EQUITY charts.
    """

    split_ratio: str = Field(alias="splitRatio")
    """
    Split ratio as a formatted string (for example, ``"2:1"``).

    Not observed in the corpus; known from prior use on EQUITY charts.
    """


class ChartEvents(YahooModel):
    """The ``chart.result[0].events`` block: dividend and split history.

    Only ``dividends`` has ever been observed (``MSFT_1y_events.json``,
    ``BAC-PL.json``), each keyed by the event's epoch-second timestamp as a
    string. ``splits`` is modeled from prior use; earnings events are
    deliberately not modeled here (Yahoo has never been observed to send
    them alongside chart events, and their shape is undocumented).
    """

    dividends: dict[str, ChartDividend] | None = None
    """
    Dividend events, keyed by epoch-second timestamp string.
    """

    splits: dict[str, ChartSplit] | None = None
    """
    Stock-split events, keyed by epoch-second timestamp string.

    Not observed in the corpus; known from prior use on EQUITY charts.
    """
