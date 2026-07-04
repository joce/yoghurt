"""Tests for Frame/Chart conversion vocabulary."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import polars as pl
import pytest

from yoghurt.frames import Chart, Frame

if TYPE_CHECKING:
    from pathlib import Path

_EXPECTED_ROW_COUNT = 2


def _frame() -> Frame:
    """Build a small two-column Frame for reuse across tests.

    Returns:
        Frame: A frame wrapping a two-row, two-column DataFrame.
    """

    df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    return Frame(df=df, fetched_at=datetime(2026, 7, 4, tzinfo=timezone.utc))


def test_to_polars_returns_the_dataframe() -> None:
    """to_polars() returns the wrapped DataFrame unchanged."""

    assert _frame().to_polars().shape == (2, 2)


def test_to_dicts_round_trips_rows() -> None:
    """to_dicts() returns one plain dict per row."""

    assert _frame().to_dicts() == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]


def test_save_parquet_writes_readable_file(tmp_path: Path) -> None:
    """save_parquet() writes a file that polars can read back."""

    target = tmp_path / "out.parquet"
    _frame().save_parquet(target)
    assert pl.read_parquet(target).shape == (2, 2)


def test_to_pandas_without_pandas_raises_helpful_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """to_pandas() raises an ImportError naming the yoghurt[pandas] extra."""

    real_import = builtins.__import__

    def _no_pandas(name: str, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        if name == "pandas":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_pandas)
    with pytest.raises(ImportError, match=r"yoghurt\[pandas\]"):
        _frame().to_pandas()  # pyright: ignore[reportUnknownMemberType]


def test_to_arrow_without_pyarrow_raises_helpful_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """to_arrow() raises an ImportError mentioning pyarrow."""

    real_import = builtins.__import__

    def _no_pyarrow(name: str, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        if name == "pyarrow":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_pyarrow)
    with pytest.raises(ImportError, match=r"pyarrow"):
        _frame().to_arrow()  # pyright: ignore[reportUnknownMemberType]


def test_to_pandas_returns_a_pandas_dataframe() -> None:
    """to_pandas() converts to pandas when the extra is installed."""

    pytest.importorskip("pandas")
    result: Any = _frame().to_pandas()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    assert list(result.columns) == ["a", "b"]  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]


def test_to_arrow_returns_a_pyarrow_table() -> None:
    """to_arrow() converts to pyarrow when installed."""

    pytest.importorskip("pyarrow")
    result: Any = _frame().to_arrow()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    assert result.num_rows == _EXPECTED_ROW_COUNT  # pyright: ignore[reportUnknownMemberType]


def test_chart_is_a_frame_with_meta() -> None:
    """Chart carries the response meta block alongside Frame behavior."""

    chart = Chart(
        df=pl.DataFrame({"ts": [1]}),
        fetched_at=datetime(2026, 7, 4, tzinfo=timezone.utc),
        meta={"currency": "USD"},
    )
    assert chart.meta["currency"] == "USD"
    assert chart.to_dicts() == [{"ts": 1}]
