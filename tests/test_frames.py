"""Tests for Frame/Chart/Spark conversion vocabulary."""

# The optional pandas/pyarrow deps are absent in the base dev env, so their
# types are Unknown to pyright here; the positive-path tests below skip at
# runtime via importorskip. Relax only the Unknown-type checks, file-wide.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import builtins
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from yoghurt.frames import Chart, Frame, Spark, Timeseries
from yoghurt.models.chart import ChartMeta

_EXPECTED_ROW_COUNT = 2
_CORPUS_CHART_DIR = Path(__file__).resolve().parent / "fixtures" / "corpus" / "chart"


def _aapl_chart_meta() -> ChartMeta:
    payload = json.loads((_CORPUS_CHART_DIR / "AAPL.json").read_text(encoding="utf-8"))
    meta: dict[str, object] = payload["chart"]["result"][0]["meta"]
    return ChartMeta.model_validate(meta)


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

    def _no_pandas(
        name: str,
        *args: Any,  # ruff:ignore[any-type]
        **kwargs: Any,  # ruff:ignore[any-type]
    ) -> Any:  # ruff:ignore[any-type]
        if name == "pandas":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_pandas)
    with pytest.raises(ImportError, match=r"yoghurt\[pandas\]"):
        _frame().to_pandas()


def test_to_arrow_without_pyarrow_raises_helpful_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """to_arrow() raises an ImportError mentioning pyarrow."""

    real_import = builtins.__import__

    def _no_pyarrow(
        name: str,
        *args: Any,  # ruff:ignore[any-type]
        **kwargs: Any,  # ruff:ignore[any-type]
    ) -> Any:  # ruff:ignore[any-type]
        if name == "pyarrow":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_pyarrow)
    with pytest.raises(ImportError, match=r"pyarrow"):
        _frame().to_arrow()


def test_to_pandas_returns_a_pandas_dataframe() -> None:
    """to_pandas() converts to pandas when the extra is installed."""

    pytest.importorskip("pandas")
    result: Any = _frame().to_pandas()
    columns: Any = result.columns
    assert list(columns) == ["a", "b"]


def test_to_arrow_returns_a_pyarrow_table() -> None:
    """to_arrow() converts to pyarrow when installed."""

    pytest.importorskip("pyarrow")
    result: Any = _frame().to_arrow()
    rows: Any = result.num_rows
    assert rows == _EXPECTED_ROW_COUNT


def test_chart_is_a_frame_with_typed_meta() -> None:
    """Chart carries the typed meta block alongside Frame behavior."""

    chart = Chart(
        df=pl.DataFrame({"ts": [1]}),
        fetched_at=datetime(2026, 7, 4, tzinfo=timezone.utc),
        meta=_aapl_chart_meta(),
        events=None,
    )
    assert chart.meta.currency == "USD"
    assert chart.events is None
    assert chart.to_dicts() == [{"ts": 1}]


def test_spark_is_a_frame_with_typed_meta() -> None:
    """Spark carries the typed meta block alongside Frame behavior."""

    spark = Spark(
        df=pl.DataFrame({"ts": [1], "close": [1.5]}),
        fetched_at=datetime(2026, 7, 4, tzinfo=timezone.utc),
        meta=_aapl_chart_meta(),
    )
    assert spark.meta.currency == "USD"
    assert spark.to_dicts() == [{"ts": 1, "close": 1.5}]


def test_timeseries_holds_four_frames_and_bookkeeping() -> None:
    """Timeseries aggregates four Frames plus the type-name tuples."""

    fetched_at = datetime(2026, 7, 4, tzinfo=timezone.utc)
    empty = Frame(df=pl.DataFrame(), fetched_at=fetched_at)
    ts = Timeseries(
        fundamentals=_frame(),
        geographic_segments=empty,
        economic_events=empty,
        analyst_ratings=empty,
        empty_types=("spEarningsReleaseEvents",),
        unrecognized_types=(),
        fetched_at=fetched_at,
    )
    assert ts.fundamentals.to_polars().shape == (2, 2)
    assert ts.economic_events.to_polars().is_empty()
    assert ts.empty_types == ("spEarningsReleaseEvents",)
    assert ts.unrecognized_types == ()
    assert ts.fetched_at is fetched_at
    with pytest.raises(AttributeError):
        ts.fundamentals = empty  # pyright: ignore[reportAttributeAccessIssue]
