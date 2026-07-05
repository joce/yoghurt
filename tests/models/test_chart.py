"""Round-trip tests for the typed ChartMeta/ChartEvents models against real captures."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from yoghurt.models import QuoteType
from yoghurt.models.chart import ChartEvents, ChartMeta

_CORPUS_CHART_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "chart"
)
_CORPUS_SPARK_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "spark"
)

_AAPL_REGULAR_MARKET_PRICE = 308.63
_AAPL_SPARK_PREVIOUS_CLOSE = 294.38
_AAPL_SPARK_SCALE = 3
_MSFT_DIVIDEND_COUNT = 4
_MAX_COMPACT_REPR_LENGTH = 120

_AAPL_PRE_START = 1782979200
_AAPL_POST_END = 1783036800
_AAPL_SPARK_PERIOD_START = 1782999000
_AAPL_SPARK_PERIOD_END = 1783022400
_AAPL_SPARK_PERIOD_GMTOFFSET = -14400
_MSFT_FIRST_DIVIDEND_DATE_EPOCH = 1755783000
_MSFT_FIRST_DIVIDEND_DATE = datetime.datetime.fromtimestamp(
    _MSFT_FIRST_DIVIDEND_DATE_EPOCH, tz=datetime.timezone.utc
)


def _load_chart_meta(filename: str) -> dict[str, object]:
    payload = json.loads((_CORPUS_CHART_DIR / filename).read_text(encoding="utf-8"))
    result: dict[str, object] = payload["chart"]["result"][0]
    meta: dict[str, object] = result["meta"]  # type: ignore[assignment]
    return meta


def _load_spark_meta(filename: str, index: int = 0) -> dict[str, object]:
    payload = json.loads((_CORPUS_SPARK_DIR / filename).read_text(encoding="utf-8"))
    result: dict[str, object] = payload["spark"]["result"][0]
    responses: list[dict[str, object]] = result["response"]  # type: ignore[assignment]
    meta: dict[str, object] = responses[index]["meta"]  # type: ignore[assignment]
    return meta


def test_chart_meta_validates_aapl_chart_record() -> None:
    """A real AAPL chart capture round-trips through typed attributes."""

    meta = _load_chart_meta("AAPL.json")
    chart_meta = ChartMeta.model_validate(meta)

    assert chart_meta.symbol == "AAPL"
    assert chart_meta.instrument_type is QuoteType.EQUITY
    assert chart_meta.regular_market_price == pytest.approx(_AAPL_REGULAR_MARKET_PRICE)
    assert chart_meta.exchange_timezone_name == "America/New_York"
    assert chart_meta.current_trading_period.regular.timezone == "EDT"
    assert chart_meta.current_trading_period.pre.start == _AAPL_PRE_START
    assert chart_meta.current_trading_period.post.end == _AAPL_POST_END
    # Chart meta (outside the one intraday capture) omits these spark-only fields.
    assert chart_meta.previous_close is None
    assert chart_meta.scale is None
    assert chart_meta.trading_periods is None
    assert chart_meta.model_extra in (None, {})


def test_chart_meta_validates_spark_record_with_trading_periods() -> None:
    """A spark meta record exercises previousClose/scale/tradingPeriods."""

    meta = _load_spark_meta("AAPL.json")
    chart_meta = ChartMeta.model_validate(meta)

    assert chart_meta.symbol == "AAPL"
    assert chart_meta.previous_close == pytest.approx(_AAPL_SPARK_PREVIOUS_CLOSE)
    assert chart_meta.scale == _AAPL_SPARK_SCALE
    assert chart_meta.trading_periods is not None
    assert len(chart_meta.trading_periods) == 1
    assert len(chart_meta.trading_periods[0]) == 1
    period = chart_meta.trading_periods[0][0]
    assert period.timezone == "EDT"
    assert period.start == _AAPL_SPARK_PERIOD_START
    assert period.end == _AAPL_SPARK_PERIOD_END
    assert period.gmtoffset == _AAPL_SPARK_PERIOD_GMTOFFSET
    assert chart_meta.model_extra in (None, {})


def test_chart_meta_mutualfund_spark_record_omits_spark_only_fields() -> None:
    """VTSAX (MUTUALFUND) spark meta lacks previousClose/scale/tradingPeriods."""

    meta = _load_spark_meta("VTSAX.json")
    chart_meta = ChartMeta.model_validate(meta)

    assert chart_meta.instrument_type is QuoteType.MUTUALFUND
    assert chart_meta.previous_close is None
    assert chart_meta.scale is None
    assert chart_meta.trading_periods is None
    assert chart_meta.model_extra in (None, {})


def test_chart_events_validates_msft_dividends_block() -> None:
    """MSFT_1y_events.json's dividends block round-trips through typed attributes."""

    payload = json.loads(
        (_CORPUS_CHART_DIR / "MSFT_1y_events.json").read_text(encoding="utf-8")
    )
    events: dict[str, object] = payload["chart"]["result"][0]["events"]
    chart_events = ChartEvents.model_validate(events)

    assert chart_events.dividends is not None
    assert len(chart_events.dividends) == _MSFT_DIVIDEND_COUNT
    assert chart_events.splits is None

    first = chart_events.dividends["1755783000"]
    assert first.amount == pytest.approx(0.83)
    assert first.date == _MSFT_FIRST_DIVIDEND_DATE
    assert chart_events.model_extra in (None, {})


def test_chart_meta_datetime_conveniences_match_quote_style_localization() -> None:
    """regular_market_datetime/first_trade_datetime localize like Quote's conveniences.

    Computes the expected values independently with ``zoneinfo`` against the
    raw epoch fields, rather than trusting the implementation under test.
    """

    meta = _load_chart_meta("AAPL.json")
    chart_meta = ChartMeta.model_validate(meta)
    tz = ZoneInfo(chart_meta.exchange_timezone_name)

    assert chart_meta.regular_market_datetime == datetime.datetime.fromtimestamp(
        chart_meta.regular_market_time, tz
    )
    assert chart_meta.regular_market_datetime.tzinfo is not None
    assert chart_meta.first_trade_datetime == datetime.datetime.fromtimestamp(
        chart_meta.first_trade_date, tz
    )
    assert chart_meta.first_trade_datetime.tzinfo is not None


def test_chart_meta_datetime_conveniences_are_cached() -> None:
    """Repeated access returns the identical object, proving caching."""

    meta = _load_chart_meta("AAPL.json")
    chart_meta = ChartMeta.model_validate(meta)

    assert chart_meta.regular_market_datetime is chart_meta.regular_market_datetime
    assert chart_meta.first_trade_datetime is chart_meta.first_trade_datetime


def test_chart_meta_model_dump_excludes_datetime_convenience_properties() -> None:
    """The convenience properties must never leak into the wire-shaped dump."""

    meta = _load_chart_meta("AAPL.json")
    chart_meta = ChartMeta.model_validate(meta)

    # Access every property first so caching can't hide a leak.
    _ = (chart_meta.regular_market_datetime, chart_meta.first_trade_datetime)

    dumped = chart_meta.model_dump()

    assert "regularMarketDatetime" not in dumped
    assert "regular_market_datetime" not in dumped
    assert "firstTradeDatetime" not in dumped
    assert "first_trade_datetime" not in dumped


def test_trading_period_datetimes_carry_fixed_gmtoffset() -> None:
    """TradingPeriod's start_datetime/end_datetime use a fixed gmtoffset, not ZoneInfo.

    The wire ``timezone`` field is a short abbreviation ("EDT") that
    ZoneInfo cannot resolve, so the conveniences must localize via a fixed
    offset built from ``gmtoffset`` instead.
    """

    meta = _load_chart_meta("AAPL.json")
    chart_meta = ChartMeta.model_validate(meta)
    period = chart_meta.current_trading_period.pre

    expected_tzinfo = datetime.timezone(datetime.timedelta(seconds=period.gmtoffset))

    assert period.start_datetime == datetime.datetime.fromtimestamp(
        period.start, expected_tzinfo
    )
    assert period.start_datetime.utcoffset() == datetime.timedelta(
        seconds=period.gmtoffset
    )
    assert period.end_datetime == datetime.datetime.fromtimestamp(
        period.end, expected_tzinfo
    )
    assert period.start_datetime is period.start_datetime
    assert period.end_datetime is period.end_datetime


def test_chart_meta_repr_is_compact_and_symbol_forward() -> None:
    """The custom __repr__ mirrors Quote's symbol-forward convention."""

    meta = _load_chart_meta("AAPL.json")
    chart_meta = ChartMeta.model_validate(meta)

    representation = repr(chart_meta)

    assert representation == (
        "ChartMeta(symbol='AAPL', "
        f"regular_market_price={chart_meta.regular_market_price!r}, "
        "instrument_type=<QuoteType.EQUITY: 'EQUITY'>)"
    )
    assert len(representation) < _MAX_COMPACT_REPR_LENGTH
