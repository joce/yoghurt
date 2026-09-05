"""Parquet writers for the CLI's tabular commands.

This module is a documented, scoped exception to the ``AGENTS.md`` rule that
yoghurt prints Yahoo bodies to stdout exactly as returned. The exception
applies only when the user opts in to Parquet output on a supported tabular
command. ``history`` and ``market-calendar`` are already derived tables in
both output formats.

Polars is the Parquet engine; the CLI imports this module lazily so the JSON
path never loads it.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
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
    import polars as pl


class ParquetWriterError(YoghurtError):
    """Raised when Parquet writing fails for a user-visible reason."""


@dataclass(frozen=True, slots=True)
class _ChartContext:
    """Tag values recorded as Parquet key-value metadata."""

    ticker: str
    interval: str
    period1: int | None
    period2: int | None
    range: str | None


def write_chart_parquet(  # ruff:ignore[too-many-arguments] - keyword-only context fields.
    chart_json_text: str,
    out_path: Path,
    *,
    ticker: str,
    interval: str,
    period1: int | None,
    period2: int | None,
    range: (  # ruff:ignore[builtin-argument-shadowing] - mirrors Yahoo's wire name
        str | None
    ) = None,
) -> dict[str, Any]:
    """Parse a Yahoo chart response and write the OHLCV table as Parquet.

    Args:
        chart_json_text: Raw JSON body returned by Yahoo's ``chart`` endpoint.
        out_path: Destination Parquet file path.
        ticker: Symbol requested (recorded in key-value metadata).
        interval: Chart interval requested (recorded in metadata).
        period1: Epoch-second start period, if used.
        period2: Epoch-second end period, if used.
        range: Relative Yahoo range, if used.

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
        ticker=ticker,
        interval=interval,
        period1=period1,
        period2=period2,
        range=range,
    )
    metadata = {
        "yoghurt_command": "chart",
        "yoghurt_version": __version__,
        "ticker": context.ticker,
        "interval": context.interval,
        "yahoo_response_meta_json": json.dumps(result.get("meta", {})),
    }
    if context.range is not None:
        metadata["range"] = context.range
    else:
        metadata["period1"] = str(context.period1)
        metadata["period2"] = str(context.period2)
    _write_frame(frame, out_path, metadata)
    descriptor = {
        "format": "parquet",
        "out": str(out_path),
        "command": "chart",
        "ticker": ticker,
        "interval": interval,
        "rows": frame.height,
        "bytes": out_path.stat().st_size,
    }
    if range is not None:
        descriptor["range"] = range
    return descriptor


def write_history_parquet(  # ruff:ignore[too-many-arguments] - keyword-only metadata.
    frame: pl.DataFrame,
    out_path: Path,
    *,
    symbols: list[str],
    period: str | None,
    start: str | None,
    end: str | None,
    interval: str,
) -> dict[str, Any]:
    """Write an adjusted history frame and return its CLI descriptor.

    Returns:
        dict[str, Any]: The single-line stdout descriptor for the write.
    """

    metadata = {
        "yoghurt_command": "history",
        "yoghurt_version": __version__,
        "symbols": ",".join(symbols),
        "interval": interval,
        "adjustment": "adj_close_ratio",
        "repair": "none",
    }
    if period is not None:
        metadata["period"] = period
    if start is not None:
        metadata["start"] = start
    if end is not None:
        metadata["end"] = end
    _write_frame(frame, out_path, metadata)
    return {
        "format": "parquet",
        "out": str(out_path),
        "command": "history",
        "symbols": symbols,
        "interval": interval,
        "rows": frame.height,
        "bytes": out_path.stat().st_size,
    }


def write_market_calendar_parquet(
    frame: pl.DataFrame,
    out_path: Path,
    *,
    kind: str,
    query: str,
) -> dict[str, Any]:
    """Write one normalized market calendar and return its CLI descriptor.

    Returns:
        dict[str, Any]: The single-line stdout descriptor for the write.
    """

    metadata = {
        "yoghurt_command": "market-calendar",
        "yoghurt_version": __version__,
        "kind": kind,
        "query": query,
    }
    _write_frame(frame, out_path, metadata)
    return {
        "format": "parquet",
        "out": str(out_path),
        "command": "market-calendar",
        "kind": kind,
        "rows": frame.height,
        "columns": frame.columns,
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

    try:  # ruff:ignore[too-many-statements-in-try-clause] - translate every filesystem failure.
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            mode = stat.S_IMODE(out_path.stat().st_mode)
        except FileNotFoundError:
            mode = None
        with ExitStack() as cleanup:
            if os.name == "nt":
                # Stage beside the target to retain Windows ACL inheritance.
                with tempfile.NamedTemporaryFile(
                    dir=out_path.parent, delete=False
                ) as stream:
                    temporary = Path(stream.name)
                cleanup.callback(temporary.unlink, missing_ok=True)
            else:
                # A new file respects umask, while the private directory hides
                # partial contents until the atomic replacement.
                directory = cleanup.enter_context(
                    tempfile.TemporaryDirectory(dir=out_path.parent)
                )
                temporary = Path(directory) / "data.parquet"
            frame.write_parquet(temporary, compression="snappy", metadata=metadata)
            if os.name != "nt" and mode is not None:
                temporary.chmod(mode)
            temporary.replace(out_path)
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
