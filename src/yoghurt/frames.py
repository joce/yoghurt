"""Immutable tabular results with one conversion vocabulary."""

# pandas/pyarrow are optional (the yoghurt[pandas] extra) and absent from the
# base dev environment, so pyright sees their types as Unknown in this module.
# Relax only the Unknown-type checks here; the ImportError probes below keep
# runtime behavior honest, and all polars-side typing remains fully checked
# elsewhere.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    import pandas as pd  # pyright: ignore[reportMissingImports, reportMissingTypeStubs]
    import polars as pl
    import pyarrow as pa  # pyright: ignore[reportMissingImports, reportMissingTypeStubs]

    from yoghurt.models.chart import ChartEvents, ChartMeta


@dataclass(frozen=True, slots=True)
class Frame:
    """A fetched tabular result wrapping a polars DataFrame."""

    df: pl.DataFrame
    fetched_at: datetime

    def to_polars(self) -> pl.DataFrame:
        """Return the underlying polars DataFrame.

        The frame is returned directly, not copied; polars operations
        produce new frames, so aliasing is safe.

        Returns:
            pl.DataFrame: The result table.
        """

        return self.df

    def to_pandas(self) -> pd.DataFrame:
        """Convert to pandas (requires the yoghurt[pandas] extra).

        Returns:
            pd.DataFrame: The result table as pandas.

        Raises:
            ImportError: If pandas is not installed.
        """

        try:
            import pandas as pd  # noqa: F401, PLC0415 - optional dependency probe  # pyright: ignore[reportMissingImports, reportMissingTypeStubs, reportUnusedImport]
        except ImportError as exc:
            message = (
                "to_pandas() requires the optional extra: pip install yoghurt[pandas]"
            )
            raise ImportError(message) from exc
        return self.df.to_pandas()

    def to_arrow(self) -> pa.Table:
        """Convert to a pyarrow Table (requires pyarrow, in yoghurt[pandas]).

        Returns:
            pa.Table: The result table as Arrow.

        Raises:
            ImportError: If pyarrow is not installed.
        """

        try:
            import pyarrow as pa  # noqa: F401, PLC0415 - optional dependency probe  # pyright: ignore[reportMissingImports, reportMissingTypeStubs, reportUnusedImport]
        except ImportError as exc:
            message = "to_arrow() requires pyarrow: pip install yoghurt[pandas]"
            raise ImportError(message) from exc
        return self.df.to_arrow()

    def to_dicts(self) -> list[dict[str, Any]]:
        """Return rows as plain dicts.

        Returns:
            list[dict[str, Any]]: One mapping per row.
        """

        return self.df.to_dicts()

    def save_parquet(self, path: Path | str) -> None:
        """Write the table to a Parquet file (snappy)."""

        self.df.write_parquet(path, compression="snappy")


@dataclass(frozen=True, slots=True)
class Chart(Frame):
    """OHLCV bars plus the chart response's typed meta and events blocks.

    ``meta`` and ``events`` are both required (no defaults) because a
    defaulted field on a slotted dataclass subclass confuses pyright's
    field-type inference (the field itself is correctly typed at use
    sites; only the declaration line mis-infers). Callers always have a
    meta block to pass, since it comes straight from the chart response;
    ``events`` is ``None`` at call sites that did not request an
    ``events`` block (Yahoo omits the key entirely in that case).
    """

    meta: ChartMeta
    events: ChartEvents | None


@dataclass(frozen=True, slots=True)
class History(Frame):
    """Corporate-action-adjusted OHLCV history for one or more symbols.

    Rows always use the long-form ``symbol, ts, open, high, low, close,
    volume`` schema. Open, high, low, and close are scaled from Yahoo's
    adjusted close; volume is unchanged. Rows without a usable adjustment
    factor retain Yahoo's raw prices. No heuristic price repair is applied.
    """


@dataclass(frozen=True, slots=True)
class Spark(Frame):
    """A single-column close-price series plus the spark response's meta block.

    Spark's ``indicators.quote[0]`` carries only ``close`` (no open/high/
    low/volume), unlike chart's seven-column OHLCV shape, so this is a
    distinct Frame subclass rather than a reuse of :class:`Chart`.
    """

    meta: ChartMeta


@dataclass(frozen=True, slots=True)
class Timeseries:
    """Typed fundamentals-timeseries result: four frames plus bookkeeping.

    Each known row family gets its own typed frame. ``fundamentals`` is
    long format (one row per type/date); ``geographic_segments`` carries
    the per-region breakdowns some fundamentals rows attach (supplementing
    the flat frame, not replacing it); ``economic_events`` and
    ``analyst_ratings`` are the two event-type tables. Every frame keeps
    its declared schema even when empty, so callers can rely on columns.

    ``empty_types`` lists requested types Yahoo answered with a meta-only
    entry (or only null rows); ``unrecognized_types`` lists types whose
    rows matched no known family — unexpected data surfaces by name
    instead of being silently eaten.
    """

    # ponytail: no unmodeled-dict field here. The only known-unreachable
    # family is spEarningsReleaseEvents, which fails upstream at JSON parse
    # (Yahoo serves invalid JSON for that type), so nothing survives to
    # store. If Yahoo ever fixes that feed, add a dedicated frame for it.
    fundamentals: Frame
    geographic_segments: Frame
    economic_events: Frame
    analyst_ratings: Frame
    empty_types: tuple[str, ...]
    unrecognized_types: tuple[str, ...]
    fetched_at: datetime
