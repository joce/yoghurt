"""Shared type aliases."""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

ParamValue: TypeAlias = str | int | float | bool
"""Scalar query parameter value accepted by Yahoo endpoints."""

MarketCalendarKind: TypeAlias = Literal["earnings", "ipo", "economic", "splits"]
"""Supported market-wide event calendar."""

MARKET_CALENDAR_KINDS: Final[tuple[MarketCalendarKind, ...]] = (
    "earnings",
    "ipo",
    "economic",
    "splits",
)
