"""Pin the README ``## Library`` quickstart examples.

Each unit test below mirrors one of the three lines shown in README.md's
``## Library`` section, exercised against the fake client and corpus
fixtures (no network). One additional integration test runs the same three
calls for real against Yahoo, marked so it stays out of the default
``pytest`` run.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import yoghurt
import yoghurt._core as core
from yoghurt.api import Ticker, screener

if TYPE_CHECKING:
    from typing import Any

    from yoghurt.types import ParamValue

_CORPUS_ROOT = Path(__file__).parent / "fixtures" / "corpus"

# Keep in sync with README.md's "## Library" quickstart query string.
_TECH_SCREENER_QUERY = (
    "SELECT ticker, intradaymarketcap FROM EQUITY "
    "WHERE region = 'us' AND sector = 'Technology' "
    "ORDER BY intradaymarketcap DESC LIMIT 25"
)


def _corpus_text(relative_path: str) -> str:
    """Read a corpus fixture body as text.

    Returns:
        str: The raw fixture file contents.
    """

    return (_CORPUS_ROOT / relative_path).read_text(encoding="utf-8")


class _FakeClient:
    """Minimal stand-in for YahooClient that returns a canned body."""

    def __init__(self, body: str) -> None:
        """Store the canned response body."""
        self.body = body

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Return the canned body.

        Returns:
            str: The canned response body.
        """
        del path, params, use_crumb, base_url
        return self.body

    async def post(
        self,
        path: str,
        params: dict[str, ParamValue],
        json_body: dict[str, Any],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Return the canned body.

        Returns:
            str: The canned response body.
        """
        del path, params, json_body, use_crumb, base_url
        return self.body

    async def aclose(self) -> None:
        """No-op close."""


def _install_fake(monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    """Patch the core client seam with a fake that returns ``body``."""

    monkeypatch.setattr(core, "_get_client", lambda: _FakeClient(body))


def test_readme_chart_quickstart(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pins the README chart quickstart: ``Ticker(...).chart(...).to_polars()``."""

    _install_fake(monkeypatch, _corpus_text("chart/AAPL.json"))
    bars = Ticker("AAPL").chart(interval="1d").to_polars()
    assert bars.columns == [
        "ts",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adj_close",
    ]


def test_readme_quote_quickstart(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pins the README quote quickstart: ``Ticker(...).quote()``."""

    _install_fake(monkeypatch, _corpus_text("quote/AAPL_default.json"))
    record = Ticker("AAPL").quote()
    assert record["symbol"] == "AAPL"


def test_readme_screener_quickstart(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pins the README screener quickstart: ``screener(...).to_polars()``."""

    _install_fake(monkeypatch, _corpus_text("screener/equity_us_tech.json"))
    frame = screener(_TECH_SCREENER_QUERY).to_polars()
    assert frame.height > 0
    assert "ticker" in frame.columns


@pytest.mark.integration
@pytest.mark.timeout(60)
def test_readme_quickstart_examples_live() -> None:
    """Runs the README quickstart shapes against live Yahoo endpoints."""

    bars = yoghurt.Ticker("AAPL").chart(interval="1d").to_polars()
    assert bars.height > 0

    quote = yoghurt.Ticker("AAPL").quote()
    assert quote["symbol"] == "AAPL"

    frame = yoghurt.screener(
        "SELECT ticker FROM EQUITY WHERE region = 'us' LIMIT 5"
    ).to_polars()
    assert frame.height > 0
    assert "ticker" in frame.columns
