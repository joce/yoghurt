"""Immutable tabular results with one conversion vocabulary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    import pandas as pd  # pyright: ignore[reportMissingImports, reportMissingTypeStubs]
    import polars as pl
    import pyarrow as pa  # pyright: ignore[reportMissingImports, reportMissingTypeStubs]


@dataclass(frozen=True, slots=True)
class Frame:
    """A fetched tabular result wrapping a polars DataFrame."""

    df: pl.DataFrame
    fetched_at: datetime

    def to_polars(self) -> pl.DataFrame:
        """Return the underlying polars DataFrame.

        Returns:
            pl.DataFrame: The result table.
        """

        return self.df

    def to_pandas(  # pyright: ignore[reportUnknownParameterType]
        self,
    ) -> pd.DataFrame:  # pyright: ignore[reportUnknownMemberType]
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
        return self.df.to_pandas()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    def to_arrow(  # pyright: ignore[reportUnknownParameterType]
        self,
    ) -> pa.Table:  # pyright: ignore[reportUnknownMemberType]
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
        return self.df.to_arrow()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

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
    """OHLCV bars plus the chart response's meta block.

    ``meta`` is required (no default) because a defaulted field on a
    slotted dataclass subclass confuses pyright's field-type inference
    (the field itself is correctly typed at use sites; only the
    declaration line mis-infers). Callers always have a meta block to
    pass, since it comes straight from the chart response.
    """

    meta: dict[str, Any]
