"""Tests for the generic endpoint call machinery."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, cast

import pytest
from typing_extensions import override

import yoghurt._core as core
from yoghurt.cli import build_parser
from yoghurt.exceptions import SymbolNotFoundError, YahooRequestError

if TYPE_CHECKING:
    from yoghurt.types import ParamValue

_HTTP_NOT_FOUND = 404
_CHART_PERIOD1_EPOCH_SECONDS = 1767225600


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


async def test_call_endpoint_builds_path_params_and_unwraps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Typed values reach the wire in CLI-identical form."""
    body = json.dumps({"quoteSummary": {"result": [{}], "error": None}})
    fake = _FakeClient(body)
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    payload = await core.call_endpoint(
        "quote-summary",
        symbol="AAPL",
        values={"symbol": "AAPL", "modules": ["price", "summaryDetail"]},
    )
    assert payload["quoteSummary"]["result"] == [{}]
    path, params = fake.calls[0]
    assert path == "/v10/finance/quoteSummary/AAPL"
    assert params["modules"] == "price,summaryDetail"


async def test_call_endpoint_serializes_dates_and_bools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """datetime/date/bool typed kwargs serialize like CLI strings."""
    body = json.dumps({"chart": {"result": [{}], "error": None}})
    fake = _FakeClient(body)
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    await core.call_endpoint(
        "chart",
        symbol="AAPL",
        values={
            "symbol": "AAPL",
            "period1": date(2026, 1, 1),
            "period2": datetime(2026, 1, 5, tzinfo=timezone.utc),
            "interval": "1d",
        },
    )
    _, params = fake.calls[0]
    assert params["period1"] == _CHART_PERIOD1_EPOCH_SECONDS
    assert isinstance(params["period2"], int)


async def test_call_endpoint_maps_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 404 with an enveloped error surfaces as SymbolNotFoundError."""
    error_body = json.dumps(
        {
            "quoteSummary": {
                "result": None,
                "error": {"code": "Not Found", "description": "x"},
            }
        }
    )

    class _ErrClient(_FakeClient):
        @override
        async def get(
            self,
            path: str,
            params: dict[str, ParamValue],
            *,
            use_crumb: bool = True,
            base_url: str | None = None,
        ) -> str:
            del path, params, use_crumb, base_url
            raise YahooRequestError(_HTTP_NOT_FOUND, "https://x", body=error_body)

    monkeypatch.setattr(core, "_get_client", lambda: _ErrClient(""))
    with pytest.raises(SymbolNotFoundError):
        await core.call_endpoint(
            "quote-summary", symbol="ZZZZXYZQ", values={"symbol": "ZZZZXYZQ"}
        )


async def test_call_query_screener_posts_body_and_wire_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The screener route posts the parsed statement body and its wire params."""
    body = json.dumps({"finance": {"result": [{}], "error": None}})
    fake = _FakeClient(body)
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    await core.call_query(
        "screener",
        "SELECT ticker FROM EQUITY LIMIT 1",
        lang="en-CA",
        region="CA",
    )
    path, call = fake.calls[0]
    assert path == "/v1/finance/screener"
    assert isinstance(call, dict)
    params = call["params"]
    assert isinstance(params, dict)
    assert params["lang"] == "en-CA"
    assert params["region"] == "CA"
    assert params["formatted"] is False
    assert params["useRecordsResponse"] is True
    assert call["body"] == {
        "query": {"operator": "and", "operands": []},
        "topOperator": "AND",
        "includeFields": ["ticker"],
        "quoteType": "EQUITY",
        "size": 1,
    }


async def test_call_query_visualization_params_are_lang_region_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The visualization route sends only lang/region wire params."""
    body = json.dumps({"finance": {"result": [{}], "error": None}})
    fake = _FakeClient(body)
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    await core.call_query("visualization", "SELECT ticker FROM sp_earnings LIMIT 1")
    path, call = fake.calls[0]
    assert path == "/v1/finance/visualization"
    assert isinstance(call, dict)
    params = cast("dict[str, object]", call["params"])
    assert isinstance(params, dict)
    assert set(params.keys()) == {"lang", "region"}


def test_configure_after_first_use_raises() -> None:
    """configure() is a before-first-use knob; late calls fail loudly."""
    core._reset_for_tests()  # pyright: ignore[reportPrivateUsage]
    core.configure(use_session_cache=False)
    core._get_client()  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(RuntimeError, match="configure"):
        core.configure(refresh_session=True)
    core._reset_for_tests()  # pyright: ignore[reportPrivateUsage]


def test_query_defaults_match_cli_parser() -> None:
    """Library DSL wire params equal the CLI parser's defaults."""
    parser = build_parser()
    namespace = parser.parse_args(
        ["screener", "--query", "SELECT ticker FROM EQUITY LIMIT 1"]
    )
    assert namespace.lang == core._QUERY_LANG  # pyright: ignore[reportPrivateUsage]
    assert namespace.region == core._QUERY_REGION  # pyright: ignore[reportPrivateUsage]
    assert namespace.formatted is False
    assert namespace.useRecordsResponse is True
