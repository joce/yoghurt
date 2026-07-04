"""Tests for the timeseries flattener (``build_timeseries_frames``)."""

# polars' DataFrame.filter overloads and the raw-JSON payload walks below
# surface as partially-unknown types under strict pyright; relax only the
# Unknown-type checks here, as test_frames.py does for its optional deps.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from yoghurt.tabular import (
    TIMESERIES_ANALYST_RATINGS_SCHEMA,
    TIMESERIES_ECONOMIC_EVENTS_SCHEMA,
    TIMESERIES_FUNDAMENTALS_SCHEMA,
    TIMESERIES_GEOGRAPHIC_SEGMENTS_SCHEMA,
    TabularShapeError,
    build_timeseries_frames,
)

_CORPUS_TIMESERIES_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "corpus" / "timeseries"
)

# Pinned against tests/fixtures/corpus/timeseries/AAPL_analystRatings.json
# (830 rows): the absent-key counts below are the frame's expected null
# counts. If a corpus refresh moves them, re-verify against the raw JSON.
_ANALYST_ROW_COUNT = 830
_ANALYST_NULL_PRIOR_RATING = 268
_ANALYST_NULL_PRIOR_PRICE_TARGET = 110
_ANALYST_NULL_CURRENT_PRICE_TARGET = 15
_ANALYST_NULL_PRICE_TARGET_ACTION = 15

_ECONOMIC_LONG_ROW_COUNT = 6
_DEFAULT_ECONOMIC_ROW_COUNT = 2

_OPERATING_INCOME_ROW_COUNT = 4
_OPERATING_INCOME_SEGMENT_COUNT = 27
_OPERATING_INCOME_2022 = 119437000000.0
_EUROPE_SEGMENT_2022 = 35233000000.0
_NET_INCOME_2022 = 99803000000.0


def _payload(name: str) -> dict[str, Any]:
    """Load one timeseries corpus capture as a parsed payload.

    Returns:
        dict[str, Any]: The parsed response payload.
    """

    return json.loads(
        (_CORPUS_TIMESERIES_DIR / name).read_text(encoding="utf-8"),
    )


def _epoch_ms(value: int) -> datetime:
    """Convert epoch milliseconds to an aware UTC datetime.

    Returns:
        datetime: The UTC instant.
    """

    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def test_default_capture_economic_rows_and_empty_types() -> None:
    """The AAPL default capture yields economic rows plus two empty event types."""

    tables = build_timeseries_frames(_payload("AAPL.json"))
    assert tables.economic_events.height == _DEFAULT_ECONOMIC_ROW_COUNT
    assert tables.empty_types == ("spEarningsReleaseEvents", "analystRatings")
    assert tables.unrecognized_types == ()
    assert tables.fundamentals.height == 0
    assert tables.geographic_segments.height == 0
    assert tables.analyst_ratings.height == 0
    first = tables.economic_events.to_dicts()[0]
    assert first == {
        "event_time": _epoch_ms(1782914400000),
        "country_code": "US",
        "event_name": "ISM Manuf Employment Idx",
        "prior": "48.6",
        "actual": "49.7",
        "period": "Jun",
        "revised_from": None,
    }


def test_economic_events_long_capture_nullable_columns() -> None:
    """The long-window capture exercises absent period and revisedFrom keys."""

    tables = build_timeseries_frames(_payload("AAPL_economicEventsLong.json"))
    frame = tables.economic_events
    assert frame.height == _ECONOMIC_LONG_ROW_COUNT
    assert frame["period"].null_count() == 1
    assert frame["revised_from"].null_count() == _ECONOMIC_LONG_ROW_COUNT - 1
    revised = frame.filter(pl.col("revised_from").is_not_null()).to_dicts()
    assert len(revised) == 1
    assert revised[0]["revised_from"] == "2.4"
    assert revised[0]["event_name"] == "Dallas Fed PCE*"


def test_fundamentals_capture_row_counts_match_raw_json() -> None:
    """The flat fundamentals frame has one row per non-null raw data row."""

    payload = _payload("AAPL_types_01.json")
    tables = build_timeseries_frames(payload)

    expected_rows = 0
    expected_empty: list[str] = []
    for entry in payload["timeseries"]["result"]:
        type_name = entry["meta"]["type"][0]
        data_rows = [row for row in entry.get(type_name) or [] if row is not None]
        if data_rows:
            expected_rows += len(data_rows)
        else:
            expected_empty.append(type_name)

    assert tables.fundamentals.height == expected_rows
    assert tables.empty_types == tuple(expected_empty)
    # An all-null row array (annualCommonStockIssuance in this capture)
    # counts as an empty type, exactly like a meta-only entry.
    assert "annualCommonStockIssuance" in tables.empty_types
    assert tables.unrecognized_types == ()


def test_fundamentals_value_spot_check() -> None:
    """reportedValue.raw lands in ``value``; fmt is dropped."""

    tables = build_timeseries_frames(_payload("AAPL_types_01.json"))
    row = tables.fundamentals.filter(
        (pl.col("type") == "annualNetIncomeContinuousOperations")
        & (pl.col("as_of_date") == date(2022, 9, 30))
    ).to_dicts()
    assert row == [
        {
            "type": "annualNetIncomeContinuousOperations",
            "as_of_date": date(2022, 9, 30),
            "period_type": "12M",
            "currency_code": "USD",
            "value": _NET_INCOME_2022,
        }
    ]


def test_fundamentals_with_segment_data_appear_in_both_frames() -> None:
    """A row carrying geographicSegmentData lands in both frames appropriately."""

    tables = build_timeseries_frames(_payload("AAPL_types_01.json"))

    flat = tables.fundamentals.filter(pl.col("type") == "annualOperatingIncome")
    assert flat.height == _OPERATING_INCOME_ROW_COUNT
    flat_2022 = flat.filter(pl.col("as_of_date") == date(2022, 9, 30)).to_dicts()
    assert flat_2022[0]["value"] == _OPERATING_INCOME_2022

    segments = tables.geographic_segments.filter(
        pl.col("type") == "annualOperatingIncome"
    )
    assert segments.height == _OPERATING_INCOME_SEGMENT_COUNT
    europe_2022 = segments.filter(
        (pl.col("as_of_date") == date(2022, 9, 30))
        & (pl.col("segment_name") == "Europe")
    ).to_dicts()
    assert europe_2022 == [
        {
            "type": "annualOperatingIncome",
            "as_of_date": date(2022, 9, 30),
            "segment_type": "Geographic",
            "segment_name": "Europe",
            "is_primary_segment": False,
            "value": _EUROPE_SEGMENT_2022,
        }
    ]


def test_analyst_ratings_full_frame_and_null_count_pins() -> None:
    """The 830-row capture maps keys to columns; absent keys become nulls."""

    tables = build_timeseries_frames(_payload("AAPL_analystRatings.json"))
    frame = tables.analyst_ratings
    assert frame.height == _ANALYST_ROW_COUNT
    assert frame.columns == list(TIMESERIES_ANALYST_RATINGS_SCHEMA)
    # The five always-present keys map to null-free columns.
    for column in (
        "rated_at",
        "analyst",
        "current_rating",
        "rating_action",
        "time_zone_short_name",
    ):
        assert frame[column].null_count() == 0, column
    # The optional keys' null counts match the raw capture's absent-key
    # counts exactly.
    assert frame["prior_rating"].null_count() == _ANALYST_NULL_PRIOR_RATING
    assert frame["prior_price_target"].null_count() == _ANALYST_NULL_PRIOR_PRICE_TARGET
    assert (
        frame["current_price_target"].null_count() == _ANALYST_NULL_CURRENT_PRICE_TARGET
    )
    assert (
        frame["price_target_action"].null_count() == _ANALYST_NULL_PRICE_TARGET_ACTION
    )
    first = frame.to_dicts()[0]
    assert first == {
        "rated_at": _epoch_ms(1578052611000),
        "analyst": "RBC Capital",
        "current_rating": "Outperform",
        "rating_action": "Maintains",
        "prior_price_target": 295.0,
        "current_price_target": 330.0,
        "price_target_action": "Raises",
        "time_zone_short_name": "EDT",
        "prior_rating": None,
    }


def test_invalid_symbol_capture_is_all_empty_with_schemas() -> None:
    """The ZZZZXYZQ capture (three meta-only entries) yields all-empty tables."""

    tables = build_timeseries_frames(_payload("ZZZZXYZQ.json"))
    assert tables.empty_types == (
        "economicEvents",
        "spEarningsReleaseEvents",
        "analystRatings",
    )
    assert tables.unrecognized_types == ()
    assert tables.fundamentals.schema == pl.Schema(TIMESERIES_FUNDAMENTALS_SCHEMA)
    assert tables.geographic_segments.schema == pl.Schema(
        TIMESERIES_GEOGRAPHIC_SEGMENTS_SCHEMA
    )
    assert tables.economic_events.schema == pl.Schema(TIMESERIES_ECONOMIC_EVENTS_SCHEMA)
    assert tables.analyst_ratings.schema == pl.Schema(TIMESERIES_ANALYST_RATINGS_SCHEMA)
    for frame in (
        tables.fundamentals,
        tables.geographic_segments,
        tables.economic_events,
        tables.analyst_ratings,
    ):
        assert frame.height == 0


def test_empty_result_yields_all_empty_tables_with_schemas() -> None:
    """An empty result list still yields every declared schema."""

    tables = build_timeseries_frames({"timeseries": {"result": []}})
    assert tables.empty_types == ()
    assert tables.unrecognized_types == ()
    assert tables.fundamentals.schema == pl.Schema(TIMESERIES_FUNDAMENTALS_SCHEMA)
    assert tables.geographic_segments.schema == pl.Schema(
        TIMESERIES_GEOGRAPHIC_SEGMENTS_SCHEMA
    )
    assert tables.economic_events.schema == pl.Schema(TIMESERIES_ECONOMIC_EVENTS_SCHEMA)
    assert tables.analyst_ratings.schema == pl.Schema(TIMESERIES_ANALYST_RATINGS_SCHEMA)


def test_null_result_is_treated_as_empty() -> None:
    """A null result resolves to the all-empty tables, like the screener path."""

    tables = build_timeseries_frames({"timeseries": {"result": None}})
    assert tables.fundamentals.height == 0
    assert tables.empty_types == ()


def test_unrecognized_family_surfaces_by_name() -> None:
    """Rows matching no known family land in unrecognized_types, not a frame."""

    payload = {
        "timeseries": {
            "result": [
                {
                    "meta": {"symbol": ["AAPL"], "type": ["mysteryEvents"]},
                    "mysteryEvents": [{"someKey": 1}],
                }
            ],
            "error": None,
        }
    }
    tables = build_timeseries_frames(payload)
    assert tables.unrecognized_types == ("mysteryEvents",)
    assert tables.empty_types == ()
    for frame in (
        tables.fundamentals,
        tables.geographic_segments,
        tables.economic_events,
        tables.analyst_ratings,
    ):
        assert frame.height == 0


def test_mixed_shape_type_lands_in_fundamentals_with_a_null_and_a_value() -> None:
    """A type with [no-reportedValue, with-reportedValue] rows is fundamentals-shaped.

    Dispatch sniffs whether ANY row in the type carries ``reportedValue``,
    not just the first row: a row lacking it still lands in the flat
    frame with a null ``value`` instead of the whole type wrongly landing
    in ``unrecognized_types``.
    """

    payload = {
        "timeseries": {
            "result": [
                {
                    "meta": {"symbol": ["AAPL"], "type": ["annualTotalRevenue"]},
                    "annualTotalRevenue": [
                        {"asOfDate": "2021-09-30", "periodType": "12M"},
                        {
                            "asOfDate": "2022-09-30",
                            "periodType": "12M",
                            "currencyCode": "USD",
                            "reportedValue": {"raw": 394328000000.0, "fmt": "394.33B"},
                        },
                    ],
                }
            ]
        }
    }
    tables = build_timeseries_frames(payload)
    assert tables.unrecognized_types == ()
    assert tables.empty_types == ()
    rows = tables.fundamentals.sort("as_of_date").to_dicts()
    assert rows == [
        {
            "type": "annualTotalRevenue",
            "as_of_date": date(2021, 9, 30),
            "period_type": "12M",
            "currency_code": None,
            "value": None,
        },
        {
            "type": "annualTotalRevenue",
            "as_of_date": date(2022, 9, 30),
            "period_type": "12M",
            "currency_code": "USD",
            "value": 394328000000.0,
        },
    ]


def test_type_with_no_reported_value_rows_anywhere_is_unrecognized() -> None:
    """A type where no row carries reportedValue lands in unrecognized_types."""

    payload = {
        "timeseries": {
            "result": [
                {
                    "meta": {"symbol": ["AAPL"], "type": ["annualTotalRevenue"]},
                    "annualTotalRevenue": [
                        {"asOfDate": "2021-09-30", "periodType": "12M"},
                        {"asOfDate": "2022-09-30", "periodType": "12M"},
                    ],
                }
            ]
        }
    }
    tables = build_timeseries_frames(payload)
    assert tables.unrecognized_types == ("annualTotalRevenue",)
    assert tables.empty_types == ()
    assert tables.fundamentals.height == 0


def test_missing_result_path_raises_shape_error() -> None:
    """A payload without timeseries.result is a shape error."""

    with pytest.raises(TabularShapeError, match=r"missing timeseries\.result"):
        build_timeseries_frames({})


def test_non_list_result_raises_shape_error() -> None:
    """A non-list result is a shape error."""

    with pytest.raises(TabularShapeError, match="must be a list"):
        build_timeseries_frames({"timeseries": {"result": {"a": 1}}})


def test_non_object_entry_raises_shape_error() -> None:
    """A result entry that is not an object is a shape error."""

    with pytest.raises(TabularShapeError, match=r"result\[0\] is not a JSON object"):
        build_timeseries_frames({"timeseries": {"result": [1]}})


def test_entry_missing_meta_type_raises_shape_error() -> None:
    """An entry without meta.type[0] is a shape error."""

    with pytest.raises(TabularShapeError, match=r"missing meta.type\[0\]"):
        build_timeseries_frames({"timeseries": {"result": [{"meta": {}}]}})


def test_non_list_rows_raise_shape_error() -> None:
    """A type key whose value is not a list is a shape error."""

    payload = {
        "timeseries": {
            "result": [
                {
                    "meta": {"symbol": ["AAPL"], "type": ["economicEvents"]},
                    "economicEvents": "nope",
                }
            ]
        }
    }
    with pytest.raises(TabularShapeError, match="rows must be a list"):
        build_timeseries_frames(payload)


def test_non_object_row_raises_shape_error() -> None:
    """A row that is neither an object nor null is a shape error."""

    payload = {
        "timeseries": {
            "result": [
                {
                    "meta": {"symbol": ["AAPL"], "type": ["economicEvents"]},
                    "economicEvents": [1],
                }
            ]
        }
    }
    with pytest.raises(TabularShapeError, match="row 0 is not a JSON object"):
        build_timeseries_frames(payload)


def test_bad_as_of_date_raises_shape_error() -> None:
    """A fundamentals asOfDate that is not an ISO date is a shape error."""

    payload = {
        "timeseries": {
            "result": [
                {
                    "meta": {"symbol": ["AAPL"], "type": ["annualTotalRevenue"]},
                    "annualTotalRevenue": [
                        {
                            "asOfDate": "not-a-date",
                            "reportedValue": {"raw": 1.0, "fmt": "1"},
                        }
                    ],
                }
            ]
        }
    }
    with pytest.raises(TabularShapeError, match="not an ISO date"):
        build_timeseries_frames(payload)


def test_bad_event_time_raises_shape_error() -> None:
    """An economicEvents eventTime that is not an integer is a shape error."""

    payload = {
        "timeseries": {
            "result": [
                {
                    "meta": {"symbol": ["AAPL"], "type": ["economicEvents"]},
                    "economicEvents": [{"eventTime": "soon"}],
                }
            ]
        }
    }
    with pytest.raises(TabularShapeError, match="integer epoch in milliseconds"):
        build_timeseries_frames(payload)


def test_bad_segment_block_raises_shape_error() -> None:
    """A non-list geographicSegmentData block is a shape error."""

    payload = {
        "timeseries": {
            "result": [
                {
                    "meta": {"symbol": ["AAPL"], "type": ["annualTotalRevenue"]},
                    "annualTotalRevenue": [
                        {
                            "asOfDate": "2022-09-30",
                            "reportedValue": {"raw": 1.0, "fmt": "1"},
                            "geographicSegmentData": {"nope": 1},
                        }
                    ],
                }
            ]
        }
    }
    with pytest.raises(TabularShapeError, match="geographicSegmentData must be a list"):
        build_timeseries_frames(payload)
