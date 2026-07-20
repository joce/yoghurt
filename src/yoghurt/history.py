"""Analysis-ready historical prices derived from Yahoo chart responses."""

# Polars' expression stubs intentionally admit Unknown values for general
# expressions. This module constructs only fixed, locally-known columns.
# pyright: reportUnknownMemberType=false

from __future__ import annotations

from datetime import date, datetime
from time import time
from typing import Any, Final

import polars as pl

from yoghurt.params import CHART_RANGES, HISTORY_INTERVALS
from yoghurt.tabular import TabularShapeError, build_chart_frame, extract_chart_columns

DateLike = int | str | date | datetime
HISTORY_REQUEST_BATCH_SIZE: Final[int] = 8


def request_values(
    *,
    period: str | None,
    start: DateLike | None,
    end: DateLike | None,
    interval: str,
    include_pre_post: bool,
) -> dict[str, object]:
    """Build chart-command values for one history request.

    Returns:
        dict[str, object]: Values accepted by the shared chart command.

    Raises:
        ValueError: If period/date or interval arguments are invalid.
    """

    if period is not None and (start is not None or end is not None):
        message = "period cannot be combined with start or end"
        raise ValueError(message)
    if end is not None and start is None:
        message = "end cannot be provided without start"
        raise ValueError(message)
    selected_period = period
    if selected_period is None and start is None:
        selected_period = "1mo"
    if selected_period is not None and selected_period not in CHART_RANGES:
        expected = ", ".join(CHART_RANGES)
        message = f"unsupported period {selected_period!r}; expected one of: {expected}"
        raise ValueError(message)
    if interval not in HISTORY_INTERVALS:
        expected = ", ".join(HISTORY_INTERVALS)
        message = f"unsupported interval {interval!r}; expected one of: {expected}"
        raise ValueError(message)

    values: dict[str, object] = {
        "interval": interval,
        "includePrePost": include_pre_post,
    }
    if selected_period is not None:
        values["range"] = selected_period
    else:
        values["period1"] = start
        values["period2"] = end if end is not None else int(time())
    return values


def frame_from_chart_result(result: dict[str, Any], symbol: str) -> pl.DataFrame:
    """Return corporate-action-adjusted OHLCV rows for one symbol.

    Yahoo's adjusted close supplies the scale factor applied to open, high,
    low, and close. Volume is unchanged. A price-bearing row without a usable
    adjustment factor makes the response invalid; empty responses stay empty.

    Returns:
        pl.DataFrame: Long-form adjusted history with a leading symbol column.

    Raises:
        TabularShapeError: If a price-bearing row has no usable adjustment
            factor.
    """

    timestamps, columns = extract_chart_columns(result)
    chart = build_chart_frame(timestamps, columns)
    usable_factor = (
        pl.col("close").is_not_null()
        & (pl.col("close") != 0)
        & pl.col("adj_close").is_not_null()
    )
    price_bearing = pl.any_horizontal(
        pl.col("open").is_not_null(),
        pl.col("high").is_not_null(),
        pl.col("low").is_not_null(),
        pl.col("close").is_not_null(),
        pl.col("adj_close").is_not_null(),
    )
    if chart.filter(price_bearing & ~usable_factor).height:
        message = (
            f"{symbol}: history response has price rows without usable adjusted close"
        )
        raise TabularShapeError(message)
    factor = pl.col("adj_close") / pl.col("close")
    # ponytail: no heuristic price repair. Add it only after corpus-backed
    # Yahoo defects demonstrate which anomalies are safe to change.
    return chart.select(
        pl.lit(symbol).alias("symbol"),
        "ts",
        (pl.col("open") * factor).alias("open"),
        (pl.col("high") * factor).alias("high"),
        (pl.col("low") * factor).alias("low"),
        pl.col("adj_close").alias("close"),
        "volume",
    )


def concat_frames(frames: list[pl.DataFrame]) -> pl.DataFrame:
    """Concatenate per-symbol history frames in caller-supplied symbol order.

    Returns:
        pl.DataFrame: One stable long-form history table.
    """

    return pl.concat(frames)
