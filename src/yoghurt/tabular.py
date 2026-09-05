"""Flatten Yahoo responses into typed polars frames.

This module contains the pure JSON-to-``pl.DataFrame`` flattening logic
shared by the ``chart``, ``screener``, and ``visualization`` Parquet writers
(see ``yoghurt.parquet_writer``). It has no knowledge of file I/O.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from functools import wraps
from typing import TYPE_CHECKING, Any, Final, ParamSpec, TypeVar

import polars as pl

from yoghurt.exceptions import YoghurtError

if TYPE_CHECKING:
    from collections.abc import Callable


class TabularShapeError(YoghurtError):
    """Raised when a Yahoo response cannot be flattened into a tabular shape."""


_P = ParamSpec("_P")
_R = TypeVar("_R")


def _shape_errors(function: Callable[_P, _R]) -> Callable[_P, _R]:
    """Translate scalar conversion failures at shared frame boundaries.

    Returns:
        Callable: The wrapped conversion with the shared error contract.
    """

    @wraps(function)
    def convert(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        try:
            return function(*args, **kwargs)
        except (TypeError, ValueError, OverflowError, pl.exceptions.PolarsError) as exc:
            message = f"invalid tabular value: {exc}"
            raise TabularShapeError(message) from exc

    return convert


def parse_chart_result(chart_json_text: str) -> dict[str, Any]:
    """Decode the chart response and return ``chart.result[0]``.

    Returns:
        dict[str, Any]: The first ``chart.result`` element.

    Raises:
        TabularShapeError: If the JSON is malformed or the expected path
            is missing.
    """

    try:
        payload = json.loads(chart_json_text)
    except json.JSONDecodeError as exc:
        message = f"chart response is not valid JSON: {exc}"
        raise TabularShapeError(message) from exc
    try:
        result = payload["chart"]["result"][0]
    except (KeyError, IndexError, TypeError) as exc:
        message = "chart response missing chart.result[0]"
        raise TabularShapeError(message) from exc
    if not isinstance(result, dict):
        message = "chart.result[0] must be an object"
        raise TabularShapeError(message)
    return result


def extract_chart_columns(
    result: dict[str, Any],
) -> tuple[list[int], dict[str, list[Any]]]:
    """Return validated timestamp + indicator arrays for the chart writer.

    Returns:
        tuple[list[int], dict[str, list[Any]]]: ``(timestamps,
        {column_name: values})`` keyed by Parquet column name.

    Raises:
        TabularShapeError: If the timestamp array, indicator block, or any
            indicator array has the wrong shape.
    """

    timestamps = result.get("timestamp", [])
    if not isinstance(timestamps, list):
        message = "chart.result[0].timestamp must be a list"
        raise TabularShapeError(message)

    indicators = result.get("indicators", {})
    if not isinstance(indicators, dict):
        message = "chart indicators must be an object"
        raise TabularShapeError(message)
    quote_blocks = indicators.get("quote", [{}])
    if not isinstance(quote_blocks, list):
        message = "chart indicators.quote must be a list"
        raise TabularShapeError(message)
    quote = quote_blocks[0] if quote_blocks else {}
    if not isinstance(quote, dict):
        message = "chart.result[0].indicators.quote[0] must be an object"
        raise TabularShapeError(message)

    adjclose_block = indicators.get("adjclose")
    if adjclose_block is not None and (
        not isinstance(adjclose_block, list)
        or any(not isinstance(block, dict) for block in adjclose_block)
    ):
        message = "chart indicators.adjclose must be a list of objects"
        raise TabularShapeError(message)
    if adjclose_block:
        adj_closes = adjclose_block[0].get("adjclose", [])
    else:
        adj_closes = [None] * len(timestamps)

    raw_columns: dict[str, Any] = {
        "open": quote.get("open", []),
        "high": quote.get("high", []),
        "low": quote.get("low", []),
        "close": quote.get("close", []),
        "volume": quote.get("volume", []),
        "adj_close": adj_closes,
    }
    expected = len(timestamps)
    columns: dict[str, list[Any]] = {}
    for label, values in raw_columns.items():
        if not isinstance(values, list):
            message = f"chart indicator {label!r} must be a list"
            raise TabularShapeError(message)
        if len(values) != expected:
            message = (
                f"chart indicator {label!r} has length {len(values)} but "
                f"timestamp has length {expected}"
            )
            raise TabularShapeError(message)
        columns[label] = values
    return list(timestamps), columns


@_shape_errors
def build_chart_frame(
    timestamps: list[int],
    columns: dict[str, list[Any]],
) -> pl.DataFrame:
    """Construct the chart Parquet ``pl.DataFrame`` with the required schema.

    Returns:
        pl.DataFrame: A typed DataFrame ready to write.
    """

    volume_ints = _coerce_volume_to_int(columns["volume"])
    ts = (
        pl.Series("ts", [int(t) * 1_000_000_000 for t in timestamps], dtype=pl.Int64)
        .cast(pl.Datetime("ns"))
        .dt.replace_time_zone("UTC")
    )
    return pl.DataFrame(
        {
            "ts": ts,
            "open": columns["open"],
            "high": columns["high"],
            "low": columns["low"],
            "close": columns["close"],
            "volume": pl.Series("volume", volume_ints, dtype=pl.Int64),
            "adj_close": columns["adj_close"],
        },
        schema={
            "ts": pl.Datetime("ns", "UTC"),
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "volume": pl.Int64,
            "adj_close": pl.Float64,
        },
    )


@_shape_errors
def build_spark_frame(response: dict[str, Any]) -> pl.DataFrame:
    """Construct the spark ``pl.DataFrame`` (``ts``, ``close``) from one spark response.

    Unlike ``chart``, spark's ``indicators.quote[0]`` carries only ``close``
    (no open/high/low/volume/adjclose), so this does not reuse
    :func:`build_chart_frame`'s seven-column flattener.

    Returns:
        pl.DataFrame: A two-column (``ts``, ``close``) DataFrame ready for
        :class:`~yoghurt.frames.Spark`.

    Raises:
        TabularShapeError: If the timestamp array, indicator block, or the
            ``close`` array has the wrong shape.
    """

    timestamps = response.get("timestamp", [])
    if not isinstance(timestamps, list):
        message = "spark response.timestamp must be a list"
        raise TabularShapeError(message)

    indicators = response.get("indicators", {})
    if not isinstance(indicators, dict):
        message = "spark indicators must be an object"
        raise TabularShapeError(message)
    quote_blocks = indicators.get("quote", [{}])
    if not isinstance(quote_blocks, list):
        message = "spark indicators.quote must be a list"
        raise TabularShapeError(message)
    quote = quote_blocks[0] if quote_blocks else {}
    if not isinstance(quote, dict):
        message = "spark response.indicators.quote[0] must be an object"
        raise TabularShapeError(message)

    closes = quote.get("close", [])
    if not isinstance(closes, list):
        message = "spark indicator 'close' must be a list"
        raise TabularShapeError(message)
    expected = len(timestamps)
    if len(closes) != expected:
        message = (
            f"spark indicator 'close' has length {len(closes)} but "
            f"timestamp has length {expected}"
        )
        raise TabularShapeError(message)

    ts = (
        pl.Series("ts", [int(t) * 1_000_000_000 for t in timestamps], dtype=pl.Int64)
        .cast(pl.Datetime("ns"))
        .dt.replace_time_zone("UTC")
    )
    return pl.DataFrame(
        {"ts": ts, "close": closes},
        schema={"ts": pl.Datetime("ns", "UTC"), "close": pl.Float64},
    )


def _coerce_volume_to_int(volumes: list[Any]) -> list[int | None]:
    """Return ``volumes`` as ints, raising if any value is non-integer.

    Returns:
        list[int | None]: Integers (or ``None``) one per input value.

    Raises:
        TabularShapeError: If any non-null value is not an integer.
    """

    result: list[int | None] = []
    for value in volumes:
        if value is None:
            result.append(None)
            continue
        if isinstance(value, bool):
            message = f"chart volume value must be an integer, got bool: {value!r}"
            raise TabularShapeError(message)
        if isinstance(value, int):
            result.append(value)
            continue
        if isinstance(value, float):
            if not value.is_integer():
                message = (
                    f"chart volume value must be an integer, got non-integer: {value!r}"
                )
                raise TabularShapeError(message)
            result.append(int(value))
            continue
        message = (
            f"chart volume value must be an integer, "
            f"got {type(value).__name__}: {value!r}"
        )
        raise TabularShapeError(message)
    return result


TIMESERIES_FUNDAMENTALS_SCHEMA: Final[dict[str, Any]] = {
    "type": pl.Utf8,
    "as_of_date": pl.Date,
    "period_type": pl.Utf8,
    "currency_code": pl.Utf8,
    "value": pl.Float64,
}

TIMESERIES_GEOGRAPHIC_SEGMENTS_SCHEMA: Final[dict[str, Any]] = {
    "type": pl.Utf8,
    "as_of_date": pl.Date,
    "segment_type": pl.Utf8,
    "segment_name": pl.Utf8,
    "is_primary_segment": pl.Boolean,
    "value": pl.Float64,
}

TIMESERIES_ECONOMIC_EVENTS_SCHEMA: Final[dict[str, Any]] = {
    "event_time": pl.Datetime("ms", "UTC"),
    "country_code": pl.Utf8,
    "event_name": pl.Utf8,
    "prior": pl.Utf8,
    "actual": pl.Utf8,
    "period": pl.Utf8,
    "revised_from": pl.Utf8,
}

TIMESERIES_ANALYST_RATINGS_SCHEMA: Final[dict[str, Any]] = {
    "rated_at": pl.Datetime("ms", "UTC"),
    "analyst": pl.Utf8,
    "current_rating": pl.Utf8,
    "rating_action": pl.Utf8,
    "prior_price_target": pl.Float64,
    "current_price_target": pl.Float64,
    "price_target_action": pl.Utf8,
    "time_zone_short_name": pl.Utf8,
    "prior_rating": pl.Utf8,
}


@dataclass(frozen=True, slots=True)
class TimeseriesTables:
    """Flattened timeseries payload: four typed tables plus type bookkeeping.

    ``empty_types`` lists requested types Yahoo answered with a meta-only
    entry (or only null rows); ``unrecognized_types`` lists types whose rows
    matched no known row family, so unexpected data surfaces by name instead
    of being silently eaten.
    """

    fundamentals: pl.DataFrame
    geographic_segments: pl.DataFrame
    economic_events: pl.DataFrame
    analyst_ratings: pl.DataFrame
    empty_types: tuple[str, ...]
    unrecognized_types: tuple[str, ...]


def _timeseries_result_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the validated ``timeseries.result`` entry list.

    A ``null`` result resolves to an empty list, mirroring the screener
    path's tolerance for empty result envelopes.

    Returns:
        list[dict[str, Any]]: One dict per result entry.

    Raises:
        TabularShapeError: If the result path is missing, not a list, or
            any entry is not an object.
    """

    try:
        result = payload["timeseries"]["result"]
    except (KeyError, TypeError) as exc:
        message = "timeseries response missing timeseries.result"
        raise TabularShapeError(message) from exc
    if result is None:
        return []
    if not isinstance(result, list):
        message = "timeseries response timeseries.result must be a list"
        raise TabularShapeError(message)
    entries: list[dict[str, Any]] = []
    for index, entry in enumerate(result):
        if not isinstance(entry, dict):
            message = f"timeseries.result[{index}] is not a JSON object"
            raise TabularShapeError(message)
        entries.append(entry)
    return entries


def _timeseries_entry_rows(
    entry: dict[str, Any], index: int
) -> tuple[str, list[dict[str, Any] | None]]:
    """Return an entry's type name and its (possibly empty) row list.

    A meta-only entry (the type key absent) resolves to an empty row list.
    Null rows are preserved here (fundamentals arrays pad gaps with nulls);
    callers filter them.

    Returns:
        tuple[str, list[dict[str, Any] | None]]: ``(type_name, rows)``.

    Raises:
        TabularShapeError: If ``meta.type[0]`` is missing or not a string,
            the rows value is not a list, or a row is neither an object
            nor null.
    """

    try:
        types = entry["meta"]["type"]
    except (KeyError, IndexError, TypeError) as exc:
        message = f"timeseries.result[{index}] missing meta.type[0]"
        raise TabularShapeError(message) from exc
    if not isinstance(types, list) or not types:
        message = f"timeseries.result[{index}] meta.type must be a nonempty list"
        raise TabularShapeError(message)
    type_name = types[0]
    if not isinstance(type_name, str):
        message = f"timeseries.result[{index}] meta.type[0] must be a string"
        raise TabularShapeError(message)
    rows_raw = entry.get(type_name)
    if rows_raw is None:
        return type_name, []
    if not isinstance(rows_raw, list):
        message = f"timeseries type {type_name!r} rows must be a list"
        raise TabularShapeError(message)
    rows: list[dict[str, Any] | None] = []
    for row_index, row in enumerate(rows_raw):
        if row is not None and not isinstance(row, dict):
            message = (
                f"timeseries type {type_name!r} row {row_index} is not a "
                f"JSON object (got {type(row).__name__})"
            )
            raise TabularShapeError(message)
        rows.append(row)
    return type_name, rows


def _timeseries_as_of_date(
    value: Any,  # ruff:ignore[any-type] - shape comes from json.loads.
    type_name: str,
) -> date | None:
    """Parse an ``asOfDate`` string into a date.

    Returns:
        date | None: The parsed date, or ``None`` for a missing value.

    Raises:
        TabularShapeError: If the value is not an ISO ``YYYY-MM-DD`` date.
    """

    if value is None:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        message = f"timeseries type {type_name!r} asOfDate {value!r} is not an ISO date"
        raise TabularShapeError(message) from exc


def _timeseries_epoch_ms(
    value: Any,  # ruff:ignore[any-type] - shape comes from json.loads.
    type_name: str,
    field: str,
) -> int | None:
    """Validate an epoch-milliseconds field as an integer.

    Returns:
        int | None: The epoch value, or ``None`` for a missing value.

    Raises:
        TabularShapeError: If the value is not an integer.
    """

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        message = (
            f"timeseries type {type_name!r} {field} must be an integer "
            f"epoch in milliseconds, got {type(value).__name__}: {value!r}"
        )
        raise TabularShapeError(message)
    return value


def _geographic_segment_records(
    type_name: str,
    as_of_date: date | None,
    segments_raw: Any,  # ruff:ignore[any-type] - shape comes from json.loads.
) -> list[dict[str, Any]]:
    """Flatten one fundamentals row's ``geographicSegmentData`` list.

    ``dataValue`` is a bare number on the wire (never a ``{raw, fmt}``
    pair), so it maps to ``value`` directly.

    Returns:
        list[dict[str, Any]]: One record per segment; empty when the row
        carries no segment data.

    Raises:
        TabularShapeError: If the segment block is not a list of objects.
    """

    if segments_raw is None:
        return []
    if not isinstance(segments_raw, list):
        message = f"timeseries type {type_name!r} geographicSegmentData must be a list"
        raise TabularShapeError(message)
    records: list[dict[str, Any]] = []
    for index, segment in enumerate(segments_raw):
        if not isinstance(segment, dict):
            message = (
                f"timeseries type {type_name!r} geographicSegmentData[{index}] "
                "is not a JSON object"
            )
            raise TabularShapeError(message)
        is_primary_raw = segment.get("isPrimarySegment")
        records.append(
            {
                "type": type_name,
                "as_of_date": as_of_date,
                "segment_type": segment.get("segmentType"),
                "segment_name": segment.get("segmentName"),
                "is_primary_segment": (
                    None if is_primary_raw is None else bool(is_primary_raw)
                ),
                "value": segment.get("dataValue"),
            }
        )
    return records


def _fundamentals_records(
    type_name: str, rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Flatten one fundamentals entry into long-format and segment records.

    ``reportedValue.raw`` becomes ``value``; ``reportedValue.fmt`` is
    presentation-only and dropped. Rows carrying ``geographicSegmentData``
    additionally contribute segment records (the flat record keeps its
    ``reportedValue``; segment data supplements, it does not replace).

    Returns:
        tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        ``(fundamentals_records, segment_records)``.

    Raises:
        TabularShapeError: If a reported value is not an object or null.
    """

    fundamentals: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    for row in rows:
        as_of_date = _timeseries_as_of_date(row.get("asOfDate"), type_name)
        reported = row.get("reportedValue")
        if reported is not None and not isinstance(reported, dict):
            message = f"timeseries type {type_name!r} reportedValue must be an object"
            raise TabularShapeError(message)
        value = reported.get("raw") if isinstance(reported, dict) else None
        fundamentals.append(
            {
                "type": type_name,
                "as_of_date": as_of_date,
                "period_type": row.get("periodType"),
                "currency_code": row.get("currencyCode"),
                "value": value,
            }
        )
        segments.extend(
            _geographic_segment_records(
                type_name, as_of_date, row.get("geographicSegmentData")
            )
        )
    return fundamentals, segments


def _economic_event_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten ``economicEvents`` rows into records.

    Returns:
        list[dict[str, Any]]: One record per event row.
    """

    return [
        {
            "event_time": _timeseries_epoch_ms(
                row.get("eventTime"), "economicEvents", "eventTime"
            ),
            "country_code": row.get("countryCode"),
            "event_name": row.get("eventName"),
            "prior": row.get("prior"),
            "actual": row.get("actual"),
            "period": row.get("period"),
            "revised_from": row.get("revisedFrom"),
        }
        for row in rows
    ]


def _analyst_rating_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten ``analystRatings`` rows into records.

    Only the five keys present on every observed row (``analyst``,
    ``currentRating``, ``ratingAction``, ``epochDateInMillis``,
    ``timeZoneShortName``) are expected to be non-null; the price-target
    trio and ``priorRating`` are frequently absent and map to nulls.

    Returns:
        list[dict[str, Any]]: One record per rating row.
    """

    return [
        {
            "rated_at": _timeseries_epoch_ms(
                row.get("epochDateInMillis"), "analystRatings", "epochDateInMillis"
            ),
            "analyst": row.get("analyst"),
            "current_rating": row.get("currentRating"),
            "rating_action": row.get("ratingAction"),
            "prior_price_target": row.get("priorPriceTarget"),
            "current_price_target": row.get("currentPriceTarget"),
            "price_target_action": row.get("priceTargetAction"),
            "time_zone_short_name": row.get("timeZoneShortName"),
            "prior_rating": row.get("priorRating"),
        }
        for row in rows
    ]


def _epoch_ms_series(name: str, values: list[Any]) -> pl.Series:
    """Build a UTC millisecond-datetime Series from epoch-ms integers.

    Returns:
        pl.Series: A ``Datetime("ms", "UTC")`` series.
    """

    return (
        pl.Series(name, values, dtype=pl.Int64)
        .cast(pl.Datetime("ms"))
        .dt.replace_time_zone("UTC")
    )


def _timeseries_table(
    records: list[dict[str, Any]],
    schema: dict[str, Any],
    epoch_ms_columns: tuple[str, ...] = (),
) -> pl.DataFrame:
    """Assemble one timeseries DataFrame with its declared schema.

    An empty record list still yields the declared schema (not a
    schemaless empty frame), so callers can rely on the columns.

    Returns:
        pl.DataFrame: A typed DataFrame.
    """

    if not records:
        return pl.DataFrame(schema=schema)
    data: dict[str, Any] = {
        name: [record[name] for record in records] for name in schema
    }
    for column in epoch_ms_columns:
        data[column] = _epoch_ms_series(column, data[column])
    return pl.DataFrame(data, schema=schema)


@_shape_errors
def build_timeseries_frames(payload: dict[str, Any]) -> TimeseriesTables:
    """Flatten a timeseries payload into four typed tables.

    Walks ``timeseries.result[]`` and routes each entry by row family:
    a type is fundamentals-shaped if ANY of its rows carries
    ``reportedValue`` (long format, plus a separate geographic-segments
    table for rows that also carry ``geographicSegmentData``); rows in a
    fundamentals-shaped type that lack ``reportedValue`` still contribute
    a record, with ``value`` (and any other reportedValue-derived field)
    null — the flat frame already tolerates nulls, so no row is dropped or
    silently routed wrong. ``economicEvents`` and ``analystRatings`` entries
    get their own event tables. Entries with no (non-null) rows are
    collected in ``empty_types``; entries whose rows match no known
    family (no row carries ``reportedValue``) are collected in
    ``unrecognized_types``.

    Returns:
        TimeseriesTables: The four tables plus type-name bookkeeping.
    """

    fundamentals: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    economic: list[dict[str, Any]] = []
    ratings: list[dict[str, Any]] = []
    empty_types: list[str] = []
    unrecognized_types: list[str] = []
    for index, entry in enumerate(_timeseries_result_entries(payload)):
        type_name, rows = _timeseries_entry_rows(entry, index)
        data_rows = [row for row in rows if row is not None]
        if not data_rows:
            empty_types.append(type_name)
        elif type_name == "economicEvents":
            economic.extend(_economic_event_records(data_rows))
        elif type_name == "analystRatings":
            ratings.extend(_analyst_rating_records(data_rows))
        elif any("reportedValue" in row for row in data_rows):
            fundamental_records, segment_records = _fundamentals_records(
                type_name, data_rows
            )
            fundamentals.extend(fundamental_records)
            segments.extend(segment_records)
        else:
            unrecognized_types.append(type_name)
    return TimeseriesTables(
        fundamentals=_timeseries_table(fundamentals, TIMESERIES_FUNDAMENTALS_SCHEMA),
        geographic_segments=_timeseries_table(
            segments, TIMESERIES_GEOGRAPHIC_SEGMENTS_SCHEMA
        ),
        economic_events=_timeseries_table(
            economic,
            TIMESERIES_ECONOMIC_EVENTS_SCHEMA,
            epoch_ms_columns=("event_time",),
        ),
        analyst_ratings=_timeseries_table(
            ratings,
            TIMESERIES_ANALYST_RATINGS_SCHEMA,
            epoch_ms_columns=("rated_at",),
        ),
        empty_types=tuple(empty_types),
        unrecognized_types=tuple(unrecognized_types),
    )


TABULAR_ROUTE_RECORD_KEY: Final[dict[str, str]] = {
    "screener": "records",
    "visualization": "documents",
}


def _records_from_visualization_documents(
    documents_raw: Any,  # ruff:ignore[any-type] - shape comes from json.loads.
    command: str,
) -> tuple[list[dict[str, Any]], list[str] | None]:
    """Flatten the visualization SELECT response into per-row dicts.

    The visualization route returns ``documents[0].columns`` (each ``{id,
    label, type}``) and ``documents[0].rows`` (positional arrays). We zip
    columns to rows here so the tabular writer's downstream logic stays
    uniform with the screener path. The column ``id`` list is also returned
    separately so the schema survives when ``rows`` is empty.

    Returns:
        tuple[list[dict[str, Any]], list[str] | None]: ``(records,
        column_ids)``. ``column_ids`` is ``None`` when the response had no
        documents at all (no schema to preserve).

    Raises:
        TabularShapeError: If the shape is unexpected.
    """

    if not isinstance(documents_raw, list):
        message = f"{command} response 'documents' must be a list"
        raise TabularShapeError(message)
    documents: list[Any] = documents_raw
    if not documents:
        return [], None
    first: Any = documents[0]
    if not isinstance(first, dict):
        message = f"{command} response documents[0] is not an object"
        raise TabularShapeError(message)
    first_dict: dict[str, Any] = first
    columns_obj: Any = first_dict.get("columns")
    rows_obj: Any = first_dict.get("rows")
    if not isinstance(columns_obj, list) or not isinstance(rows_obj, list):
        message = f"{command} response documents[0] must have list 'columns' and 'rows'"
        raise TabularShapeError(message)
    columns: list[Any] = columns_obj
    rows: list[Any] = rows_obj
    column_ids: list[str] = []
    for index, column in enumerate(columns):
        if not isinstance(column, dict) or "id" not in column:
            message = f"{command} response documents[0].columns[{index}] missing 'id'"
            raise TabularShapeError(message)
        column_dict: dict[str, Any] = column
        column_ids.append(str(column_dict["id"]))
    records: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, list):
            message = f"{command} response documents[0].rows[{row_index}] is not a list"
            raise TabularShapeError(message)
        row_list: list[Any] = row
        if len(row_list) != len(column_ids):
            message = (
                f"{command} response documents[0].rows[{row_index}] has "
                f"{len(row_list)} values but columns has {len(column_ids)}"
            )
            raise TabularShapeError(message)
        record: dict[str, Any] = dict(zip(column_ids, row_list, strict=True))
        records.append(record)
    return records, column_ids


def parse_tabular_payload(
    payload: dict[str, Any], command: str, route: str
) -> tuple[list[dict[str, Any]], int, list[str] | None]:
    """Return records, ``total_rows``, and an optional schema hint.

    Dict-accepting core of :func:`parse_tabular_response`, for callers
    that already hold a parsed payload (see ``yoghurt.api``).

    The schema hint is populated only for visualization responses, where
    ``documents[0].columns`` provides column IDs even when ``rows`` is
    empty. Screener responses carry their schema inline in each record,
    so the hint is ``None``.

    Returns:
        tuple[list[dict[str, Any]], int, list[str] | None]: ``(records,
        total_rows, schema_hint)``.

    Raises:
        TabularShapeError: If the records path has the wrong type.
    """

    record_key = TABULAR_ROUTE_RECORD_KEY.get(route)
    if record_key is None:
        message = f"Unsupported route for Parquet output: {route!r}"
        raise TabularShapeError(message)

    try:
        results = payload["finance"]["result"]
    except (KeyError, TypeError) as exc:
        message = f"{command} response missing finance.result"
        raise TabularShapeError(message) from exc
    if not isinstance(results, list) or any(
        not isinstance(row, dict) for row in results
    ):
        message = f"{command} response finance.result must be a list of objects"
        raise TabularShapeError(message)
    if not results:
        return [], 0, None
    result = results[0]
    records_raw = result.get(record_key)

    schema_hint: list[str] | None = None
    records: list[dict[str, Any]]
    if route == "visualization":
        records, schema_hint = _records_from_visualization_documents(
            records_raw, command
        )
    else:
        if not isinstance(records_raw, list):
            message = f"{command} response {record_key!r} must be a list"
            raise TabularShapeError(message)
        records = []
        for index, item in enumerate(records_raw):
            if not isinstance(item, dict):
                message = (
                    f"{command} response row {index} is not a JSON object "
                    f"(got {type(item).__name__})"
                )
                raise TabularShapeError(message)
            records.append(item)

    total_rows = result.get("total") if isinstance(result, dict) else None
    if not isinstance(total_rows, int):
        total_rows = len(records)
    return records, total_rows, schema_hint


def parse_tabular_response(
    response_json_text: str, command: str, route: str
) -> tuple[list[dict[str, Any]], int, list[str] | None]:
    """Decode a raw response body and delegate to :func:`parse_tabular_payload`.

    Returns:
        tuple[list[dict[str, Any]], int, list[str] | None]: ``(records,
        total_rows, schema_hint)``.

    Raises:
        TabularShapeError: If the response JSON is malformed.
    """

    try:
        payload = json.loads(response_json_text)
    except json.JSONDecodeError as exc:
        message = f"{command} response is not valid JSON: {exc}"
        raise TabularShapeError(message) from exc
    return parse_tabular_payload(payload, command, route)


def collect_column_data(
    records: list[dict[str, Any]], columns: list[str]
) -> dict[str, list[Any]]:
    """Project ``records`` onto the resolved column order.

    Returns:
        dict[str, list[Any]]: One entry per column in ``columns``.
    """

    column_data: dict[str, list[Any]] = {name: [] for name in columns}
    for record in records:
        for name in columns:
            column_data[name].append(record.get(name))
    return column_data


def reject_nested_cells(column_data: dict[str, list[Any]]) -> None:
    """Raise if any cell contains a nested object or list.

    Raises:
        TabularShapeError: If any cell value is a dict or list.
    """

    for name, values in column_data.items():
        for value in values:
            if isinstance(value, (dict, list)):
                message = (
                    f"column {name!r} contains nested cell; Parquet output "
                    "requires scalar cells. Drop --formatted or switch to "
                    "--format json."
                )
                raise TabularShapeError(message)


def _infer_polars_dtype(values: list[Any]) -> Any:  # ruff:ignore[any-type]
    """Pick the most specific common polars dtype for ``values``.

    Returns:
        Any: The chosen polars dtype class. Defaults to ``Utf8`` for empty,
        all-null, or mixed-type columns.
    """

    non_null = [v for v in values if v is not None]
    if not non_null:
        return pl.Utf8
    if all(isinstance(v, bool) for v in non_null):
        return pl.Boolean
    if all(isinstance(v, int) and not isinstance(v, bool) for v in non_null):
        return pl.Int64
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_null):
        return pl.Float64
    return pl.Utf8


def _build_column(values: list[Any], dtype: Any) -> list[Any]:  # ruff:ignore[any-type]
    """Coerce ``values`` to match ``dtype`` for safe Series construction.

    Returns:
        list[Any]: Coerced values suitable for the given dtype.
    """

    if dtype == pl.Utf8:
        return [None if v is None else _coerce_to_string(v) for v in values]
    if dtype == pl.Float64:
        return [None if v is None else float(v) for v in values]
    return values  # Boolean / Int64 pass through


@_shape_errors
def build_tabular_frame(
    column_data: dict[str, list[Any]],
    columns: list[str],
) -> pl.DataFrame:
    """Assemble the tabular Parquet DataFrame with inferred dtypes.

    Returns:
        pl.DataFrame: A typed DataFrame ready to write.
    """

    if not columns:
        return pl.DataFrame()
    schema: dict[str, Any] = {}
    data: dict[str, list[Any]] = {}
    for name in columns:
        dtype = _infer_polars_dtype(column_data[name])
        schema[name] = dtype
        data[name] = _build_column(column_data[name], dtype)
    return pl.DataFrame(data, schema=schema)


def resolve_column_order(
    records: list[dict[str, Any]], schema_hint: list[str] | None
) -> list[str]:
    """Pick the column order for the Parquet schema from the response itself.

    Parquet columns reflect what Yahoo actually returned, not what the
    user asked for in a ``SELECT`` clause. Yahoo's screener route translates
    DSL field names to camelCase response keys (e.g. ``intradaymarketcap``
    becomes ``marketCap``) and may include unrequested fields such as
    ``logoUrl``; the visualization route preserves DSL names verbatim.
    Mirroring the response makes the Parquet file faithful to the JSON the
    user would see, so downstream consumers see no surprises.

    The ``schema_hint`` carries the visualization response's
    ``documents[0].columns[].id`` list so an empty ``rows`` array still
    produces a Parquet file with a faithful schema. Screener responses
    have no such out-of-band schema and pass ``None``.

    Returns:
        list[str]: Column names in the order they should appear, or
        ``[]`` when the response had no schema information to draw from.
    """

    columns = list(dict.fromkeys(key for record in records for key in record))
    if columns:
        return columns
    if schema_hint is not None:
        return list(schema_hint)
    return []


def _coerce_to_string(
    value: Any,  # ruff:ignore[any-type] - cell values are untyped JSON scalars.
) -> str:
    """Render a scalar cell to a Parquet string value.

    Returns:
        str: The stringified value.
    """

    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
