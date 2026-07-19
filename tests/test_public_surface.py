"""The public import surface is explicit and importable."""

from __future__ import annotations

import subprocess  # ruff:ignore[suspicious-subprocess-import] - building the wheel is a fixed, trusted argv
import sys
import zipfile
from pathlib import Path

import pytest

import yoghurt


def test_all_names_are_importable() -> None:
    """Every __all__ entry resolves to a real attribute."""

    for name in yoghurt.__all__:
        assert getattr(yoghurt, name, None) is not None, name


def test_expected_surface() -> None:
    """The documented public names are all exported."""

    expected = {
        "Chart",
        "Frame",
        "Quote",
        "QuoteType",
        "Spark",
        "Ticker",
        "Timeseries",
        "YahooClient",
        "SymbolNotFoundError",
        "YahooApiError",
        "YahooRequestError",
        "YahooUnavailableError",
        "YoghurtError",
        "configure",
        "quotes",
        "raw",
        "screener",
        "visualization",
        "screener_predefined",
        "screener_discover",
        "screener_instrument_fields",
        "timeseries_fields",
        "trending",
        "sector",
        "market_summary",
        "market_info",
        "market_time",
        "__version__",
    }
    assert expected <= set(yoghurt.__all__)


def test_all_is_sorted_and_unique() -> None:
    """__all__ stays sorted (plain ASCII order, matching ruff's RUF022), no dupes."""

    names = list(yoghurt.__all__)
    assert len(names) == len(set(names))
    assert names == sorted(names)


def test_dir_hides_internal_imports() -> None:
    """dir() surfaces the public API and dunders, not internal module imports."""

    names = dir(yoghurt)
    assert "importlib" not in names
    assert "TYPE_CHECKING" not in names
    assert set(yoghurt.__all__) <= set(names)


@pytest.mark.timeout(60)
def test_py_typed_ships_in_wheel(tmp_path: Path) -> None:
    """PEP 561 marker must reach the wheel."""

    subprocess.run(  # ruff:ignore[subprocess-without-shell-equals-true] - fixed argv, no untrusted input
        [sys.executable, "-m", "uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        check=True,
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
    )
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        assert "yoghurt/py.typed" in wheel.namelist()
