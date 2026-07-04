"""Tests for the Yahoo HTTP client."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx2 as httpx
import pytest

from yoghurt.client import YahooClient
from yoghurt.exceptions import YahooRequestError
from yoghurt.session_cache import save_session_cache

if TYPE_CHECKING:
    from pathlib import Path

REQUEST_ATTEMPTS = 3


class Httpx2Mock:
    """Queue expected httpx2 responses and record outgoing requests."""

    def __init__(self) -> None:
        """Initialize an httpx2 mock transport."""

        self.requests: list[httpx.Request] = []
        self._responses: list[tuple[str, httpx.URL, httpx.Response]] = []
        self._next_response_index = 0
        self.transport = httpx.MockTransport(self._handle)

    def add(self, method: str, url: str, response: httpx.Response) -> None:
        """Add an expected request and response."""

        self._responses.append((method, httpx.URL(url), response))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        has_response = self._next_response_index < len(self._responses)
        assert has_response, f"Unexpected request: {request.method} {request.url}"
        method, url, response = self._responses[self._next_response_index]
        self._next_response_index += 1
        assert request.method == method
        assert request.url == url
        return response


@pytest.mark.asyncio
async def test_get_redacts_crumb_from_request_error(
    tmp_path: Path,
) -> None:
    """Failed API requests do not expose Yahoo crumbs in user-facing errors."""

    cache_path = tmp_path / "session.json"
    cookies = httpx.Cookies()
    cookies.set("A3", "token", domain=".yahoo.com", path="/")
    save_session_cache(cache_path, cookies, "secret-crumb", time.time() + 3600)
    httpx_mock = Httpx2Mock()
    httpx_mock.add(
        "GET",
        "https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL&crumb=secret-crumb",
        httpx.Response(404, json={"finance": {"error": {"code": "Not Found"}}}),
    )
    client = YahooClient(
        session_cache_path=cache_path,
        transport=httpx_mock.transport,
    )

    try:
        with pytest.raises(YahooRequestError) as exc_info:
            await client.get("/v7/finance/quote", {"symbols": "AAPL"})
    finally:
        await client.aclose()

    assert "secret-crumb" not in str(exc_info.value)
    assert "crumb=" not in str(exc_info.value)
    assert "symbols=AAPL" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_request_error_includes_response_body(
    tmp_path: Path,
) -> None:
    """A failed API request carries the Yahoo response body on the error."""

    cache_path = tmp_path / "session.json"
    cookies = httpx.Cookies()
    cookies.set("A3", "token", domain=".yahoo.com", path="/")
    save_session_cache(cache_path, cookies, "crumb-token", time.time() + 3600)
    error_body = '{"finance": {"error": {"code": "Not Found"}}}'
    httpx_mock = Httpx2Mock()
    httpx_mock.add(
        "GET",
        "https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL&crumb=crumb-token",
        httpx.Response(404, text=error_body),
    )
    client = YahooClient(
        session_cache_path=cache_path,
        transport=httpx_mock.transport,
    )

    try:
        with pytest.raises(YahooRequestError) as exc_info:
            await client.get("/v7/finance/quote", {"symbols": "AAPL"})
    finally:
        await client.aclose()

    assert exc_info.value.body == error_body


@pytest.mark.asyncio
async def test_get_retries_retryable_status_codes(
    tmp_path: Path,
) -> None:
    """Retryable GET failures are retried before surfacing the final response."""

    cache_path = tmp_path / "session.json"
    cookies = httpx.Cookies()
    cookies.set("A3", "token", domain=".yahoo.com", path="/")
    save_session_cache(cache_path, cookies, "crumb-token", time.time() + 3600)
    url = (
        "https://query1.finance.yahoo.com/v7/finance/quote?"
        "symbols=AAPL&crumb=crumb-token"
    )
    httpx_mock = Httpx2Mock()
    httpx_mock.add("GET", url, httpx.Response(503))
    httpx_mock.add("GET", url, httpx.Response(503))
    httpx_mock.add("GET", url, httpx.Response(200, text='{"ok":true}'))
    client = YahooClient(
        session_cache_path=cache_path,
        transport=httpx_mock.transport,
    )

    try:
        body = await client.get("/v7/finance/quote", {"symbols": "AAPL"})
    finally:
        await client.aclose()

    assert body == '{"ok":true}'
    assert len(httpx_mock.requests) == REQUEST_ATTEMPTS


@pytest.mark.asyncio
async def test_get_uses_cached_session_without_refreshing(
    tmp_path: Path,
) -> None:
    """A valid cached cookie and crumb are enough for a one-shot API call."""

    cache_path = tmp_path / "session.json"
    cookies = httpx.Cookies()
    cookies.set("A3", "token", domain=".yahoo.com", path="/")
    save_session_cache(cache_path, cookies, "crumb-token", time.time() + 3600)
    httpx_mock = Httpx2Mock()
    httpx_mock.add(
        "GET",
        (
            "https://query1.finance.yahoo.com/v7/finance/quote?"
            "symbols=AAPL&crumb=crumb-token"
        ),
        httpx.Response(200, text='{"ok":true}'),
    )
    client = YahooClient(
        session_cache_path=cache_path,
        transport=httpx_mock.transport,
    )

    try:
        body = await client.get("/v7/finance/quote", {"symbols": "AAPL"})
    finally:
        await client.aclose()

    assert body == '{"ok":true}'
    assert [request.url.host for request in httpx_mock.requests] == [
        "query1.finance.yahoo.com"
    ]
