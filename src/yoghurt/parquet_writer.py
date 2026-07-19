"""Parquet writers for the ``chart``, ``screener``, and ``visualization`` commands.

This module is a documented, scoped exception to the ``AGENTS.md`` rule that
yoghurt prints Yahoo bodies to stdout exactly as returned. The exception
applies only when the user opts in to Parquet output on one of the three
tabular commands.

Polars is the Parquet engine; the CLI imports this module lazily so the JSON
path never loads it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from yoghurt import __version__
from yoghurt.exceptions import YoghurtError
from yoghurt.tabular import (
    TabularShapeError,
    build_chart_frame,
    build_tabular_frame,
    collect_column_data,
    extract_chart_columns,
    parse_chart_result,
    parse_tabular_response,
    reject_nested_cells,
    resolve_column_order,
)

if TYPE_CHECKING:
    from pathlib import Path

    import polars as pl


class ParquetWriterError(YoghurtError):
    """Raised when Parquet writing fails for a user-visible reason."""


@dataclass(frozen=True, slots=True)
class _ChartContext:
    """Tag values recorded as Parquet key-value metadata."""

    ticker: str
    interval: str
    period1: int
    period2: int


def write_chart_parquet(  # ruff:ignore[too-many-arguments] - keyword-only context fields.
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

    Raises:
        ParquetWriterError: If the chart response cannot be flattened or
            the Parquet file cannot be written.
    """

    try:
        result = parse_chart_result(chart_json_text)
        timestamps, indicator_columns = extract_chart_columns(result)
        frame = build_chart_frame(timestamps, indicator_columns)
    except TabularShapeError as exc:
        raise ParquetWriterError(str(exc)) from exc
    context = _ChartContext(
        ticker=ticker, interval=interval, period1=period1, period2=period2
    )
    metadata = {
        "yoghurt_command": "chart",
        "yoghurt_version": __version__,
        "ticker": context.ticker,
        "interval": context.interval,
        "period1": str(context.period1),
        "period2": str(context.period2),
        "yahoo_response_meta_json": json.dumps(result.get("meta", {})),
    }
    _write_frame(frame, out_path, metadata)
    return {
        "format": "parquet",
        "out": str(out_path),
        "command": "chart",
        "ticker": ticker,
        "interval": interval,
        "rows": frame.height,
        "bytes": out_path.stat().st_size,
    }


def _write_frame(
    frame: pl.DataFrame,
    out_path: Path,
    metadata: dict[str, str],
) -> None:
    """Write ``frame`` to ``out_path`` and translate OS errors.

    Raises:
        ParquetWriterError: If writing fails (missing directory, permission
            denied, etc.).
    """

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        frame.write_parquet(out_path, compression="snappy", metadata=metadata)
    except OSError as exc:
        message = f"failed to write Parquet file {out_path}: {exc}"
        raise ParquetWriterError(message) from exc


def write_tabular_parquet(  # ruff:ignore[too-many-arguments] - keyword-only metadata.
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

    Raises:
        ParquetWriterError: If the response cannot be flattened or the
            Parquet file cannot be written.
    """

    try:
        records, total_rows, schema_hint = parse_tabular_response(
            response_json_text, command, route
        )
        columns = resolve_column_order(records, schema_hint)
        column_data = collect_column_data(records, columns)
        reject_nested_cells(column_data)
        frame = build_tabular_frame(column_data, columns)
    except TabularShapeError as exc:
        raise ParquetWriterError(str(exc)) from exc
    metadata = {
        "yoghurt_command": command,
        "yoghurt_version": __version__,
        "query": query if query is not None else "<body-json>",
        "route": route,
        "wire_params_json": json.dumps(wire_params, sort_keys=True),
        "total_rows": str(total_rows),
    }
    _write_frame(frame, out_path, metadata)
    return {
        "format": "parquet",
        "out": str(out_path),
        "command": command,
        "rows": frame.height,
        "columns": list(columns),
        "bytes": out_path.stat().st_size,
    }
