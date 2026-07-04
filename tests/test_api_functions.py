"""Tests for the public synchronous module-level API functions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

import pytest

import yoghurt._core as core
from yoghurt import api
from yoghurt.commands import COMMANDS_BY_NAME
from yoghurt.exceptions import YahooApiError
from yoghurt.frames import Frame

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from yoghurt.types import ParamValue

_Invoke: TypeAlias = "Callable[[], object]"

_CORPUS_ROOT = Path(__file__).parent / "fixtures" / "corpus"
_TRENDING_SPEC_REGION = next(
    param.default
    for param in COMMANDS_BY_NAME["trending"].params
    if param.name == "region"
)


def _corpus_text(relative_path: str) -> str:
    """Read a corpus fixture body as text.

    Returns:
        str: The raw fixture file contents.
    """

    return (_CORPUS_ROOT / relative_path).read_text(encoding="utf-8")


class _FakeClient:
    """Minimal stand-in for YahooClient that records calls and returns a body."""

    def __init__(self, body: str) -> None:
        """Store the canned response body."""
        self.body = body
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Record the call and return the canned body.

        Returns:
            str: The canned response body.
        """
        del use_crumb, base_url
        self.calls.append((path, dict(params)))
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
        """Record the call and return the canned body.

        Returns:
            str: The canned response body.
        """
        del use_crumb, base_url
        self.calls.append((path, {"params": dict(params), "body": json_body}))
        return self.body

    async def aclose(self) -> None:
        """No-op close."""


def _install_fake(monkeypatch: pytest.MonkeyPatch, body: str) -> _FakeClient:
    """Patch the core client seam with a fake that returns ``body``.

    Returns:
        _FakeClient: The installed fake, for call-inspection assertions.
    """

    fake = _FakeClient(body)
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    return fake


def test_quotes_returns_result_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """quotes() returns quoteResponse.result as-is."""
    body = _corpus_text("quote/multi.json")
    _install_fake(monkeypatch, body)
    results = api.quotes(["AAPL", "MSFT"])
    expected = json.loads(body)["quoteResponse"]["result"]
    assert len(results) == len(expected)


def test_quotes_joins_symbols_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    """quotes() joins the symbols list into the wire CSV param."""
    fake = _install_fake(monkeypatch, _corpus_text("quote/multi.json"))
    api.quotes(["AAPL", "MSFT"])
    _, params = fake.calls[0]
    assert params["symbols"] == "AAPL,MSFT"


def test_quotes_empty_list_raises_before_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """quotes([]) raises ValueError without making any client call."""

    def _fail_get_client() -> object:
        message = "must not be called"
        raise AssertionError(message)

    monkeypatch.setattr(core, "_get_client", _fail_get_client)
    with pytest.raises(ValueError, match="symbols must not be empty"):
        api.quotes([])


_SCREENER_QUERY = (
    "SELECT ticker, sector FROM EQUITY WHERE sector = 'Technology' LIMIT 5"
)
_VISUALIZATION_QUERY = (
    "SELECT ticker, transactiondate, shares FROM INSIDER_TRANSACTION "
    "WHERE ticker = 'AAPL' ORDER BY transactiondate DESC LIMIT 5"
)


def test_screener_builds_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    """screener() flattens records into a Frame with the expected row count."""
    body = _corpus_text("screener/equity_us_tech.json")
    fake = _install_fake(monkeypatch, body)
    frame = api.screener(_SCREENER_QUERY)
    expected_records = json.loads(body)["finance"]["result"][0]["records"]
    assert isinstance(frame, Frame)
    assert frame.to_polars().height == len(expected_records)
    assert "ticker" in frame.to_polars().columns
    path, _ = fake.calls[0]
    assert path == "/v1/finance/screener"


def test_visualization_builds_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    """visualization() flattens documents into a Frame with the expected row count."""
    body = _corpus_text("visualization/insider_transaction.json")
    fake = _install_fake(monkeypatch, body)
    frame = api.visualization(_VISUALIZATION_QUERY)
    expected_rows = json.loads(body)["finance"]["result"][0]["documents"][0]["rows"]
    assert isinstance(frame, Frame)
    assert frame.to_polars().height == len(expected_rows)
    assert "ticker" in frame.to_polars().columns
    path, _ = fake.calls[0]
    assert path == "/v1/finance/visualization"


def test_screener_empty_records_returns_empty_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty screener records list yields an empty Frame, not a raised error."""
    payload = json.loads(_corpus_text("screener/equity_us_tech.json"))
    payload["finance"]["result"][0]["records"] = []
    payload["finance"]["result"][0]["total"] = 0
    _install_fake(monkeypatch, json.dumps(payload))
    frame = api.screener(_SCREENER_QUERY)
    assert isinstance(frame, Frame)
    assert frame.to_polars().height == 0


def test_visualization_empty_documents_returns_empty_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty visualization documents list yields an empty Frame."""
    payload = json.loads(_corpus_text("visualization/insider_transaction.json"))
    payload["finance"]["result"][0]["documents"] = []
    payload["finance"]["result"][0]["total"] = 0
    _install_fake(monkeypatch, json.dumps(payload))
    frame = api.visualization(_VISUALIZATION_QUERY)
    assert isinstance(frame, Frame)
    assert frame.to_polars().height == 0


def _invoke_screener_predefined() -> object:
    return api.screener_predefined(["MOST_ACTIVES"])


def _invoke_trending() -> object:
    return api.trending()


def _invoke_sector() -> object:
    return api.sector("technology")


def _invoke_market_summary() -> object:
    return api.market_summary()


def _invoke_market_info() -> object:
    return api.market_info()


def _invoke_market_time() -> object:
    return api.market_time()


def _invoke_screener_instrument_fields() -> object:
    return api.screener_instrument_fields("equity")


def _invoke_timeseries_fields() -> object:
    return api.timeseries_fields()


def _invoke_screener_discover() -> object:
    return api.screener_discover()


_METHOD_CASES = (
    pytest.param(
        _invoke_screener_predefined,
        "screener-predefined/MOST_ACTIVES.json",
        "/v1/finance/screener/predefined/saved",
        id="screener_predefined",
    ),
    pytest.param(
        _invoke_trending,
        "trending/default.json",
        f"/v1/finance/trending/{_TRENDING_SPEC_REGION}",
        id="trending",
    ),
    pytest.param(
        _invoke_sector,
        "sector/technology.json",
        "/v1/finance/sectors/technology",
        id="sector",
    ),
    pytest.param(
        _invoke_market_summary,
        "market-summary/default.json",
        "/v6/finance/quote/marketSummary",
        id="market_summary",
    ),
    pytest.param(
        _invoke_market_info,
        "market-info/default.json",
        "/ws/market-info/v1/finance/markets/ids",
        id="market_info",
    ),
    pytest.param(
        _invoke_market_time,
        "market-time/default.json",
        "/v6/finance/markettime",
        id="market_time",
    ),
    pytest.param(
        _invoke_screener_instrument_fields,
        "screener-instrument-fields/equity.json",
        "/v1/finance/screener/instrument/equity/fields",
        id="screener_instrument_fields",
    ),
    pytest.param(
        _invoke_timeseries_fields,
        "timeseries-fields/default.json",
        "/ws/fundamentals-timeseries/v1/finance/timeseriesfields",
        id="timeseries_fields",
    ),
    pytest.param(
        _invoke_screener_discover,
        "screener-discover/default.json",
        "/ws/screeners/v1/finance/screener/discover",
        id="screener_discover",
    ),
)


@pytest.mark.parametrize(("invoke", "corpus_file", "expected_path"), _METHOD_CASES)
def test_dict_function_calls_expected_path_and_returns_payload(
    monkeypatch: pytest.MonkeyPatch,
    invoke: _Invoke,
    corpus_file: str,
    expected_path: str,
) -> None:
    """Each dict function hits its command's path and passes the payload through."""
    body = _corpus_text(corpus_file)
    fake = _install_fake(monkeypatch, body)
    result = invoke()
    path, _ = fake.calls[0]
    assert path == expected_path
    assert result == json.loads(body)


def test_raw_returns_parsed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """raw() parses the body with no envelope lookup and passes the payload through."""
    body = _corpus_text("raw/quote_AAPL.json")
    fake = _install_fake(monkeypatch, body)
    result = api.raw("/v7/finance/quote", {"symbols": "AAPL"})
    assert result == json.loads(body)
    path, params = fake.calls[0]
    assert path == "/v7/finance/quote"
    assert params["symbols"] == "AAPL"


def test_raw_malformed_body_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """raw() maps a non-JSON body to YahooApiError with a malformed-response code."""
    _install_fake(monkeypatch, "not json")
    with pytest.raises(YahooApiError) as exc_info:
        api.raw("/v7/finance/quote", {"symbols": "AAPL"})
    assert exc_info.value.code == "malformed-response"
