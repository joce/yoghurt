"""Tests for the Yahoo HTTP client."""

from __future__ import annotations

import time
import traceback
from typing import TYPE_CHECKING

import httpx2 as httpx
import pytest

from yoghurt.client import YahooClient
from yoghurt.exceptions import YahooRequestError, YahooUnavailableError
from yoghurt.session_cache import save_session_cache

if TYPE_CHECKING:
    from pathlib import Path

REQUEST_ATTEMPTS = 3
SESSION_ATTEMPTS = 2


@pytest.mark.parametrize(
    "cookie_case", ["empty", "missing", "expired", "wrong-domain", "non-ascii"]
)
@pytest.mark.asyncio
async def test_unusable_cached_cookie_reinitializes_session(
    tmp_path: Path, cookie_case: str
) -> None:
    """A future crumb expiry cannot make an unusable A3 cookie valid."""
    cache = tmp_path / "session.json"
    cookies = httpx.Cookies()
    if cookie_case != "empty":
        name = "OTHER" if cookie_case == "missing" else "A3"
        domain = ".example.com" if cookie_case == "wrong-domain" else ".yahoo.com"
        value = "caf\u00e9" if cookie_case == "non-ascii" else "synthetic"
        cookies.set(name, value, domain=domain, path="/")
        if cookie_case == "expired":
            for cookie in cookies.jar:
                cookie.expires = int(time.time()) - 1
    save_session_cache(cache, cookies, "old", time.time() + 3600)
    requests: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/":
            return httpx.Response(
                200, headers={"set-cookie": "A3=test; Domain=.yahoo.com; Path=/"}
            )
        return httpx.Response(200, text="ok")

    client = YahooClient(
        transport=httpx.MockTransport(handle), session_cache_path=cache
    )
    try:
        assert await client.get("/endpoint", {}) == "ok"
    finally:
        await client.aclose()
    assert requests == ["/", "/v1/test/getcrumb", "/endpoint"]


@pytest.mark.parametrize("description", [[], {}, None, 1])
@pytest.mark.asyncio
async def test_malformed_auth_description_keeps_http_error(description: object) -> None:
    """Unhashable error descriptions cannot escape the request error contract."""
    requests: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/":
            return httpx.Response(
                200, headers={"set-cookie": "A3=test; Domain=.yahoo.com; Path=/"}
            )
        if request.url.path.endswith("getcrumb"):
            return httpx.Response(200, text="synthetic")
        return httpx.Response(
            401, json={"finance": {"error": {"description": description}}}
        )

    client = YahooClient(transport=httpx.MockTransport(handle), use_session_cache=False)
    try:
        with pytest.raises(YahooRequestError, match="HTTP 401"):
            await client.get("/endpoint", {})
    finally:
        await client.aclose()
    assert requests == ["/", "/v1/test/getcrumb", "/endpoint"]


@pytest.mark.parametrize("failure", ["rejected", "transport"])
@pytest.mark.asyncio
async def test_refresh_failure_and_replay_exhaustion(failure: str) -> None:
    """Authentication recovery is bounded even when refresh or replay fails."""
    paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/":
            return httpx.Response(
                200, headers={"set-cookie": "A3=test; Domain=.yahoo.com; Path=/"}
            )
        if request.url.path.endswith("getcrumb"):
            if failure == "transport" and paths.count("/v1/test/getcrumb") > 1:
                message = "synthetic-cookie synthetic-crumb"
                raise httpx.ConnectError(message, request=request)
            return httpx.Response(200, text="synthetic-crumb")
        return httpx.Response(
            401, json={"finance": {"error": {"description": "Invalid Crumb"}}}
        )

    client = YahooClient(transport=httpx.MockTransport(handle), use_session_cache=False)
    try:
        with pytest.raises((YahooRequestError, YahooUnavailableError)) as error:
            await client.post("/endpoint", {}, {})
    finally:
        await client.aclose()
    trace = "".join(traceback.format_exception(error.value))
    assert "synthetic-cookie" not in trace
    assert "synthetic-crumb" not in trace
    expected_requests = 2 if failure == "rejected" else 1
    assert paths.count("/endpoint") == expected_requests
    assert paths.count("/") == SESSION_ATTEMPTS


@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.asyncio
async def test_eu_consent_flow_and_safe_failure(*, valid: bool) -> None:
    """EU consent handles redirects and redacts consent tokens on failure."""
    finance_requests = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal finance_requests
        if request.url.host == "finance.yahoo.com":
            finance_requests += 1
            return httpx.Response(
                302,
                headers={
                    "location": "https://guce.yahoo.com/consent?gcrumb=synthetic-csrf"
                },
            )
        if request.url.host == "guce.yahoo.com":
            return httpx.Response(
                302,
                headers={
                    "location": "https://consent.yahoo.com/collect?sessionId=synthetic-session",
                    "set-cookie": "GUCS=synthetic-cookie; Domain=.yahoo.com; Path=/",
                },
            )
        if request.url.host == "consent.yahoo.com":
            headers: dict[str, str] = {}
            if request.method == "POST" and valid:
                headers["set-cookie"] = "A3=synthetic-a3; Domain=.yahoo.com; Path=/"
            return httpx.Response(200, headers=headers)
        if request.url.path.endswith("getcrumb"):
            return httpx.Response(200, text="synthetic-crumb")
        return httpx.Response(200, text="ok")

    client = YahooClient(transport=httpx.MockTransport(handle), use_session_cache=False)
    try:
        if valid:
            assert await client.get("/endpoint", {}) == "ok"
        else:
            with pytest.raises(YahooRequestError, match="A3 cookie missing") as error:
                await client.get("/endpoint", {})
            trace = "".join(traceback.format_exception(error.value))
            assert "synthetic-session" not in trace
            assert "synthetic-csrf" not in trace
            assert "synthetic-cookie" not in trace
    finally:
        await client.aclose()
    assert finance_requests == SESSION_ATTEMPTS


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
