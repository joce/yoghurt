"""Tests for analysis-ready historical price transformation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from yoghurt.history import frame_from_chart_result, request_values
from yoghurt.tabular import TabularShapeError

EXPECTED_FIRST_VOLUME = 1000


def test_partial_btc_history_capture_is_rejected() -> None:
    """The BTC capture cannot mix a latest raw bar with adjusted history."""
    path = Path(__file__).parent / "fixtures" / "corpus" / "chart" / "BTC-USD.json"
    result = json.loads(path.read_text(encoding="utf-8"))["chart"]["result"][0]
    with pytest.raises(TabularShapeError, match=r"adj_close|adjusted"):
        frame_from_chart_result(result, "BTC-USD")


def test_history_adjusts_entire_ohlc_bar_from_adjusted_close() -> None:
    """Adjusted close supplies one factor for open, high, low, and close."""

    result = {
        "timestamp": [1, 2],
        "indicators": {
            "quote": [
                {
                    "open": [90.0, 190.0],
                    "high": [110.0, 210.0],
                    "low": [80.0, 180.0],
                    "close": [100.0, 200.0],
                    "volume": [1000, 2000],
                }
            ],
            "adjclose": [{"adjclose": [50.0, 100.0]}],
        },
    }

    rows = frame_from_chart_result(result, "TEST").to_dicts()

    assert rows[0]["symbol"] == "TEST"
    assert rows[0]["open"] == pytest.approx(45.0)
    assert rows[0]["high"] == pytest.approx(55.0)
    assert rows[0]["low"] == pytest.approx(40.0)
    assert rows[0]["close"] == pytest.approx(50.0)
    assert rows[0]["volume"] == EXPECTED_FIRST_VOLUME
    assert rows[1]["open"] == pytest.approx(95.0)
    assert rows[1]["close"] == pytest.approx(100.0)


def test_history_rejects_any_price_row_without_adjusted_close() -> None:
    """Adjusted history never mixes adjusted and raw price rows."""

    result = {
        "timestamp": [1, 2],
        "indicators": {
            "quote": [
                {
                    "open": [90.0, 190.0],
                    "high": [110.0, 210.0],
                    "low": [80.0, 180.0],
                    "close": [100.0, 200.0],
                    "volume": [1000, 2000],
                }
            ],
            "adjclose": [{"adjclose": [50.0, None]}],
        },
    }

    with pytest.raises(TabularShapeError, match="without usable adjusted close"):
        frame_from_chart_result(result, "TEST")


def test_history_allows_empty_response_without_adjusted_close() -> None:
    """An empty Yahoo history remains an empty adjusted History frame."""

    result: dict[str, Any] = {"timestamp": [], "indicators": {"quote": [{}]}}

    assert frame_from_chart_result(result, "TEST").is_empty()


def test_history_request_defaults_to_one_month_daily() -> None:
    """No explicit window gets yfinance-style one-month daily ergonomics."""

    values = request_values(
        period=None,
        start=None,
        end=None,
        interval="1d",
        include_pre_post=False,
    )

    assert values == {
        "range": "1mo",
        "interval": "1d",
        "includePrePost": False,
    }


def test_history_request_resolves_omitted_end_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit start gets one fixed end shared by every symbol batch."""

    expected_end = 1_800_000_000
    monkeypatch.setattr("yoghurt.history.time", lambda: expected_end)

    values = request_values(
        period=None,
        start="2025-01-01",
        end=None,
        interval="1d",
        include_pre_post=False,
    )

    assert values["period2"] == expected_end


def test_history_request_rejects_period_with_dates() -> None:
    """Relative and explicit windows are separate, unambiguous modes."""

    with pytest.raises(ValueError, match="period cannot be combined"):
        request_values(
            period="1y",
            start="2025-01-01",
            end=None,
            interval="1d",
            include_pre_post=False,
        )


def test_history_request_rejects_intraday_interval() -> None:
    """Adjusted history rejects intervals where Yahoo omits adjusted close."""

    with pytest.raises(ValueError, match="expected one of: 1d, 5d, 1wk, 1mo, 3mo"):
        request_values(
            period="1d",
            start=None,
            end=None,
            interval="1m",
            include_pre_post=False,
        )
