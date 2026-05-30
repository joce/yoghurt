"""Parquet writers for the ``chart``, ``screener``, and ``visualization`` commands.

This module is a documented, scoped exception to the ``AGENTS.md`` rule that
yoghurt prints Yahoo bodies to stdout exactly as returned. The exception
applies only when the user opts in to Parquet output on one of the three
tabular commands.

PyArrow is imported lazily inside each writer so JSON-path users do not pay
the import cost or require the optional ``pyarrow`` dependency.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from yoghurt import __version__
from yoghurt.exceptions import YoghurtError

if TYPE_CHECKING:
    from pathlib import Path


class ParquetWriterError(YoghurtError):
    """Raised when Parquet writing fails for a user-visible reason."""


@dataclass(frozen=True, slots=True)
class _ChartContext:
    """Tag values recorded as Parquet key-value metadata."""

    ticker: str
    interval: str
    period1: int
    period2: int


def write_chart_parquet(  # noqa: PLR0913 - keyword-only context fields.
    chart_json_text: str,
    out_path: Path,
    *,
    ticker: str,
    interval: str,
    period1: int,
    period2: int,
) -> dict[str, Any]:
    """Parse a Yahoo chart response and write the OHLCV table as Parquet.

    Args:
        chart_json_text: Raw JSON body returned by Yahoo's ``chart`` endpoint.
        out_path: Destination Parquet file path.
        ticker: Symbol requested (recorded in key-value metadata).
        interval: Chart interval requested (recorded in metadata).
        period1: Epoch-second start period (recorded in metadata).
        period2: Epoch-second end period (recorded in metadata).

    Returns:
        dict[str, Any]: The single-line stdout descriptor for the write.
    """

    pa, pq = _import_pyarrow()
    result = _parse_chart_result(chart_json_text)
    timestamps, indicator_columns = _extract_chart_columns(result)
    context = _ChartContext(
        ticker=ticker, interval=interval, period1=period1, period2=period2
    )
    table = _build_chart_table(timestamps, indicator_columns, result, context, pa)
    _write_table(pq, table, out_path)
    return {
        "format": "parquet",
        "out": str(out_path),
        "command": "chart",
        "ticker": ticker,
        "interval": interval,
        "rows": table.num_rows,
        "bytes": out_path.stat().st_size,
    }


_MISSING_PYARROW_MESSAGE: Final[str] = (
    "--format parquet requires the parquet extra: "
    "pip install 'yoghurt[parquet]' (or uv sync --extra parquet)"
)


def _import_pyarrow() -> tuple[Any, Any]:
    """Lazily import pyarrow + pyarrow.parquet.

    Returns:
        tuple[Any, Any]: ``(pyarrow_module, pyarrow_parquet_module)``.

    Raises:
        ParquetWriterError: If pyarrow is not installed. The error
            message directs the user at the ``[parquet]`` extra.
    """

    try:
        import pyarrow as pa  # noqa: PLC0415 - lazy import keeps JSON path free.
        import pyarrow.parquet as pq  # noqa: PLC0415
    except ImportError as exc:
        raise ParquetWriterError(_MISSING_PYARROW_MESSAGE) from exc
    return pa, pq


def _write_table(
    pq: Any,  # noqa: ANN401 - pyarrow.parquet module.
    table: Any,  # noqa: ANN401 - pyarrow.Table instance.
    out_path: Path,
) -> None:
    """Write ``table`` to ``out_path`` and translate OS errors.

    Raises:
        ParquetWriterError: If writing fails (missing directory, permission
            denied, etc.).
    """

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, out_path)
    except OSError as exc:
        message = f"failed to write Parquet file {out_path}: {exc}"
        raise ParquetWriterError(message) from exc


def _parse_chart_result(chart_json_text: str) -> dict[str, Any]:
    """Decode the chart response and return ``chart.result[0]``.

    Returns:
        dict[str, Any]: The first ``chart.result`` element.

    Raises:
        ParquetWriterError: If the JSON is malformed or the expected path
            is missing.
    """

    try:
        payload = json.loads(chart_json_text)
    except json.JSONDecodeError as exc:
        message = f"chart response is not valid JSON: {exc}"
        raise ParquetWriterError(message) from exc
    try:
        result = payload["chart"]["result"][0]
    except (KeyError, IndexError, TypeError) as exc:
        message = "chart response missing chart.result[0]"
        raise ParquetWriterError(message) from exc
    return result


def _extract_chart_columns(
    result: dict[str, Any],
) -> tuple[list[int], dict[str, list[Any]]]:
    """Return validated timestamp + indicator arrays for the chart writer.

    Returns:
        tuple[list[int], dict[str, list[Any]]]: ``(timestamps,
        {column_name: values})`` keyed by Parquet column name.

    Raises:
        ParquetWriterError: If the timestamp array, indicator block, or any
            indicator array has the wrong shape.
    """

    timestamps = result.get("timestamp") or []
    if not isinstance(timestamps, list):
        message = "chart.result[0].timestamp must be a list"
        raise ParquetWriterError(message)

    indicators = result.get("indicators") or {}
    quote_blocks = indicators.get("quote") or [{}]
    quote = quote_blocks[0] if quote_blocks else {}
    if not isinstance(quote, dict):
        message = "chart.result[0].indicators.quote[0] must be an object"
        raise ParquetWriterError(message)

    adjclose_block = indicators.get("adjclose")
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
            raise ParquetWriterError(message)
        if len(values) != expected:
            message = (
                f"chart indicator {label!r} has length {len(values)} but "
                f"timestamp has length {expected}"
            )
            raise ParquetWriterError(message)
        columns[label] = values
    return list(timestamps), columns


def _build_chart_table(
    timestamps: list[int],
    columns: dict[str, list[Any]],
    result: dict[str, Any],
    context: _ChartContext,
    pa: Any,  # noqa: ANN401 - pyarrow module is intentionally untyped here.
) -> Any:  # noqa: ANN401
    """Construct the chart Parquet ``pa.Table`` with schema metadata.

    Returns:
        Any: A populated ``pyarrow.Table`` instance.
    """

    volume_ints = _coerce_volume_to_int(columns["volume"])
    ts_array = pa.array(
        [int(ts) * 1_000_000_000 for ts in timestamps],
        type=pa.timestamp("ns", tz="UTC"),
    )
    schema = pa.schema(
        [
            pa.field("ts", pa.timestamp("ns", tz="UTC")),
            pa.field("open", pa.float64()),
            pa.field("high", pa.float64()),
            pa.field("low", pa.float64()),
            pa.field("close", pa.float64()),
            pa.field("volume", pa.int64()),
            pa.field("adj_close", pa.float64()),
        ],
        metadata={
            "yoghurt_command": "chart",
            "yoghurt_version": __version__,
            "ticker": context.ticker,
            "interval": context.interval,
            "period1": str(context.period1),
            "period2": str(context.period2),
            "yahoo_response_meta_json": json.dumps(result.get("meta", {})),
        },
    )
    return pa.Table.from_arrays(
        [
            ts_array,
            pa.array(columns["open"], type=pa.float64()),
            pa.array(columns["high"], type=pa.float64()),
            pa.array(columns["low"], type=pa.float64()),
            pa.array(columns["close"], type=pa.float64()),
            pa.array(volume_ints, type=pa.int64()),
            pa.array(columns["adj_close"], type=pa.float64()),
        ],
        schema=schema,
    )


def _coerce_volume_to_int(volumes: list[Any]) -> list[int | None]:
    """Return ``volumes`` as ints, raising if any value is non-integer.

    Returns:
        list[int | None]: Integers (or ``None``) one per input value.

    Raises:
        ParquetWriterError: If any non-null value is not an integer.
    """

    result: list[int | None] = []
    for value in volumes:
        if value is None:
            result.append(None)
            continue
        if isinstance(value, bool):
            message = f"chart volume value must be an integer, got bool: {value!r}"
            raise ParquetWriterError(message)
        if isinstance(value, int):
            result.append(value)
            continue
        if isinstance(value, float):
            if not value.is_integer():
                message = (
                    f"chart volume value must be an integer, got non-integer: {value!r}"
                )
                raise ParquetWriterError(message)
            result.append(int(value))
            continue
        message = (
            f"chart volume value must be an integer, "
            f"got {type(value).__name__}: {value!r}"
        )
        raise ParquetWriterError(message)
    return result


_TABULAR_ROUTE_RECORD_KEY: dict[str, str] = {
    "screener": "records",
    "visualization": "documents",
}


def _records_from_visualization_documents(
    documents_raw: Any,  # noqa: ANN401 - shape comes from json.loads.
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
        ParquetWriterError: If the shape is unexpected.
    """

    if not isinstance(documents_raw, list):
        message = f"{command} response 'documents' must be a list"
        raise ParquetWriterError(message)
    documents: list[Any] = documents_raw
    if not documents:
        return [], None
    first: Any = documents[0]
    if not isinstance(first, dict):
        message = f"{command} response documents[0] is not an object"
        raise ParquetWriterError(message)
    first_dict: dict[str, Any] = first
    columns_obj: Any = first_dict.get("columns")
    rows_obj: Any = first_dict.get("rows")
    if not isinstance(columns_obj, list) or not isinstance(rows_obj, list):
        message = f"{command} response documents[0] must have list 'columns' and 'rows'"
        raise ParquetWriterError(message)
    columns: list[Any] = columns_obj
    rows: list[Any] = rows_obj
    column_ids: list[str] = []
    for index, column in enumerate(columns):
        if not isinstance(column, dict) or "id" not in column:
            message = f"{command} response documents[0].columns[{index}] missing 'id'"
            raise ParquetWriterError(message)
        column_dict: dict[str, Any] = column
        column_ids.append(str(column_dict["id"]))
    records: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, list):
            message = f"{command} response documents[0].rows[{row_index}] is not a list"
            raise ParquetWriterError(message)
        row_list: list[Any] = row
        if len(row_list) != len(column_ids):
            message = (
                f"{command} response documents[0].rows[{row_index}] has "
                f"{len(row_list)} values but columns has {len(column_ids)}"
            )
            raise ParquetWriterError(message)
        record: dict[str, Any] = dict(zip(column_ids, row_list, strict=True))
        records.append(record)
    return records, column_ids


def write_tabular_parquet(  # noqa: PLR0913 - keyword-only metadata.
    response_json_text: str,
    out_path: Path,
    *,
    command: str,
    route: str,
    query: str | None,
    wire_params: dict[str, Any],
) -> dict[str, Any]:
    """Parse a screener / visualization SELECT response and write it as Parquet.

    Args:
        response_json_text: Raw JSON body returned by Yahoo.
        out_path: Destination Parquet file path.
        command: ``"screener"`` or ``"visualization"`` (recorded in metadata).
        route: ``"screener"`` or ``"visualization"`` (drives record-path lookup).
        query: The ``--query`` string if available; ``None`` if the user used
            ``--body-json``. Recorded in metadata and used to seed columns
            when the response is empty.
        wire_params: Actual params the CLI sent to Yahoo. Recorded as
            ``wire_params_json`` in metadata.

    Returns:
        dict[str, Any]: The single-line stdout descriptor for the write.
    """

    pa, pq = _import_pyarrow()
    records, total_rows, schema_hint = _parse_tabular_response(
        response_json_text, command, route
    )
    columns = _resolve_column_order(records, schema_hint)
    column_data = _collect_column_data(records, columns)
    _reject_nested_cells(column_data)
    table = _build_tabular_table(
        column_data,
        columns,
        pa,
        command=command,
        route=route,
        query=query,
        wire_params=wire_params,
        total_rows=total_rows,
    )
    _write_table(pq, table, out_path)
    return {
        "format": "parquet",
        "out": str(out_path),
        "command": command,
        "rows": table.num_rows,
        "columns": list(columns),
        "bytes": out_path.stat().st_size,
    }


def _parse_tabular_response(
    response_json_text: str, command: str, route: str
) -> tuple[list[dict[str, Any]], int, list[str] | None]:
    """Return records, ``total_rows``, and an optional schema hint.

    The schema hint is populated only for visualization responses, where
    ``documents[0].columns`` provides column IDs even when ``rows`` is
    empty. Screener responses carry their schema inline in each record,
    so the hint is ``None``.

    Returns:
        tuple[list[dict[str, Any]], int, list[str] | None]: ``(records,
        total_rows, schema_hint)``.

    Raises:
        ParquetWriterError: If the response JSON is malformed or the
            records path has the wrong type.
    """

    try:
        payload = json.loads(response_json_text)
    except json.JSONDecodeError as exc:
        message = f"{command} response is not valid JSON: {exc}"
        raise ParquetWriterError(message) from exc

    record_key = _TABULAR_ROUTE_RECORD_KEY.get(route)
    if record_key is None:
        message = f"Unsupported route for Parquet output: {route!r}"
        raise ParquetWriterError(message)

    try:
        result = payload["finance"]["result"][0]
    except (KeyError, IndexError, TypeError):
        result = {}

    records_raw = result.get(record_key) if isinstance(result, dict) else None
    if records_raw is None:
        records_raw = []

    schema_hint: list[str] | None = None
    records: list[dict[str, Any]]
    if route == "visualization":
        records, schema_hint = _records_from_visualization_documents(
            records_raw, command
        )
    else:
        if not isinstance(records_raw, list):
            message = f"{command} response {record_key!r} must be a list"
            raise ParquetWriterError(message)
        records = []
        for index, item in enumerate(records_raw):
            if not isinstance(item, dict):
                message = (
                    f"{command} response row {index} is not a JSON object "
                    f"(got {type(item).__name__})"
                )
                raise ParquetWriterError(message)
            records.append(item)

    total_rows = result.get("total") if isinstance(result, dict) else None
    if not isinstance(total_rows, int):
        total_rows = len(records)
    return records, total_rows, schema_hint


def _collect_column_data(
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


def _reject_nested_cells(column_data: dict[str, list[Any]]) -> None:
    """Raise if any cell contains a nested object or list.

    Raises:
        ParquetWriterError: If any cell value is a dict or list.
    """

    for name, values in column_data.items():
        for value in values:
            if isinstance(value, (dict, list)):
                message = (
                    f"column {name!r} contains nested cell; Parquet output "
                    "requires scalar cells. Drop --formatted or switch to "
                    "--format json."
                )
                raise ParquetWriterError(message)


def _build_tabular_table(  # noqa: PLR0913 - keyword-only metadata bundle.
    column_data: dict[str, list[Any]],
    columns: list[str],
    pa: Any,  # noqa: ANN401
    *,
    command: str,
    route: str,
    query: str | None,
    wire_params: dict[str, Any],
    total_rows: int,
) -> Any:  # noqa: ANN401
    """Assemble the tabular Parquet table and attach key-value metadata.

    Returns:
        Any: A populated ``pyarrow.Table`` instance.
    """

    schema_fields: list[Any] = []
    arrays: list[Any] = []
    for name in columns:
        values = column_data[name]
        pa_type = _infer_arrow_type(values, pa)
        schema_fields.append(pa.field(name, pa_type))
        arrays.append(_build_array(values, pa_type, pa))

    metadata = {
        "yoghurt_command": command,
        "yoghurt_version": __version__,
        "query": query if query is not None else "<body-json>",
        "route": route,
        "wire_params_json": json.dumps(wire_params, sort_keys=True),
        "total_rows": str(total_rows),
    }
    schema = pa.schema(schema_fields, metadata=metadata)
    return pa.Table.from_arrays(arrays, schema=schema)


def _resolve_column_order(
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

    for record in records:
        if record:
            return list(record.keys())
    if schema_hint is not None:
        return list(schema_hint)
    return []


def _infer_arrow_type(
    values: list[Any],
    pa: Any,  # noqa: ANN401 - pyarrow module is intentionally untyped here.
) -> Any:  # noqa: ANN401
    """Pick the most specific common Arrow type for ``values``.

    Returns:
        Any: The chosen ``pyarrow`` type. Defaults to ``string`` for empty,
        all-null, or mixed-type columns.
    """

    non_null = [value for value in values if value is not None]
    if not non_null:
        return pa.string()
    if all(isinstance(value, bool) for value in non_null):
        return pa.bool_()
    if all(
        isinstance(value, int) and not isinstance(value, bool) for value in non_null
    ):
        return pa.int64()
    if all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in non_null
    ):
        return pa.float64()
    return pa.string()


def _build_array(
    values: list[Any],
    pa_type: Any,  # noqa: ANN401
    pa: Any,  # noqa: ANN401
) -> Any:  # noqa: ANN401
    """Coerce ``values`` to ``pa_type`` and build an Arrow array.

    Returns:
        Any: A ``pyarrow`` array typed for the resolved column dtype.

    Raises:
        ParquetWriterError: If ``pa_type`` is not one produced by
            :func:`_infer_arrow_type` (string / bool / int64 / float64).
    """

    if pa_type == pa.string():
        coerced = [
            None if value is None else _coerce_to_string(value) for value in values
        ]
        return pa.array(coerced, type=pa.string())
    if pa_type == pa.bool_():
        return pa.array(values, type=pa.bool_())
    if pa_type == pa.int64():
        return pa.array(values, type=pa.int64())
    if pa_type == pa.float64():
        coerced_floats: list[float | None] = [
            None if value is None else float(value) for value in values
        ]
        return pa.array(coerced_floats, type=pa.float64())
    message = f"unsupported inferred Arrow type: {pa_type}"
    raise ParquetWriterError(message)


def _coerce_to_string(
    value: Any,  # noqa: ANN401 - cell values are untyped JSON scalars.
) -> str:
    """Render a scalar cell to a Parquet string value.

    Returns:
        str: The stringified value.
    """

    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
