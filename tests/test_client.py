"""Tests for the Yahoo HTTP client."""

from __future__ import annotations

import asyncio
import time
import traceback
from datetime import datetime, timezone
from email.utils import format_datetime
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
TOO_MANY_REQUESTS = 429


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


@pytest.mark.asyncio
async def test_cold_public_chart_skips_session_bootstrap() -> None:
    """A healthy public chart request does not depend on Yahoo's homepage."""

    requests: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        assert request.url.path == "/v8/finance/chart/AAPL"
        return httpx.Response(200, text='{"chart":true}')

    client = YahooClient(transport=httpx.MockTransport(handle), use_session_cache=False)
    try:
        body = await client.get("/v8/finance/chart/AAPL", {}, use_crumb=False)
    finally:
        await client.aclose()

    assert body == '{"chart":true}'
    assert requests == ["/v8/finance/chart/AAPL"]


@pytest.mark.asyncio
async def test_public_chart_uses_cached_cookie_without_refreshing(
    tmp_path: Path,
) -> None:
    """A cached session remains available to a direct public chart call."""

    cache_path = tmp_path / "session.json"
    cookies = httpx.Cookies()
    cookies.set("A3", "token", domain=".yahoo.com", path="/")
    save_session_cache(cache_path, cookies, "crumb-token", time.time() + 3600)
    requests: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        assert "A3=token" in request.headers.get("Cookie", "")
        return httpx.Response(200, text="ok")

    client = YahooClient(
        session_cache_path=cache_path, transport=httpx.MockTransport(handle)
    )
    try:
        assert await client.get("/v8/finance/chart/AAPL", {}, use_crumb=False) == "ok"
    finally:
        await client.aclose()

    assert requests == ["/v8/finance/chart/AAPL"]


@pytest.mark.asyncio
async def test_public_chart_refresh_switch_still_bootstraps_session() -> None:
    """Explicit refresh keeps its documented session-refresh behavior."""

    requests: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/":
            return httpx.Response(
                200, headers={"set-cookie": "A3=test; Domain=.yahoo.com; Path=/"}
            )
        return httpx.Response(200, text="ok")

    client = YahooClient(
        transport=httpx.MockTransport(handle),
        use_session_cache=False,
        refresh_session=True,
    )
    try:
        assert await client.get("/v8/finance/chart/AAPL", {}, use_crumb=False) == "ok"
    finally:
        await client.aclose()

    assert requests == ["/", "/v8/finance/chart/AAPL"]


@pytest.mark.asyncio
async def test_public_chart_auth_rejection_bootstraps_and_retries() -> None:
    """A direct chart auth rejection gets one authenticated fallback."""

    requests: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if requests == ["/v8/finance/chart/AAPL"]:
            return httpx.Response(401)
        if request.url.path == "/":
            return httpx.Response(
                200, headers={"set-cookie": "A3=test; Domain=.yahoo.com; Path=/"}
            )
        return httpx.Response(200, text="ok")

    client = YahooClient(transport=httpx.MockTransport(handle), use_session_cache=False)
    try:
        assert await client.get("/v8/finance/chart/AAPL", {}, use_crumb=False) == "ok"
    finally:
        await client.aclose()

    assert requests == ["/v8/finance/chart/AAPL", "/", "/v8/finance/chart/AAPL"]


@pytest.mark.asyncio
async def test_concurrent_public_chart_auth_fallback_refreshes_once() -> None:
    """Concurrent direct failures share the existing session refresh lock."""

    homepage_requests = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal homepage_requests
        if request.url.path == "/":
            homepage_requests += 1
            return httpx.Response(
                200, headers={"set-cookie": "A3=test; Domain=.yahoo.com; Path=/"}
            )
        if "A3=test" not in request.headers.get("Cookie", ""):
            return httpx.Response(401)
        return httpx.Response(200, text="ok")

    client = YahooClient(transport=httpx.MockTransport(handle), use_session_cache=False)
    try:
        results = await asyncio.gather(
            client.get("/v8/finance/chart/AAPL", {}, use_crumb=False),
            client.get("/v8/finance/chart/MSFT", {}, use_crumb=False),
        )
    finally:
        await client.aclose()

    assert results == ["ok", "ok"]
    assert homepage_requests == 1


@pytest.mark.asyncio
async def test_chart_cookie_refresh_replenishes_crumb_for_authenticated_replay(
    tmp_path: Path,
) -> None:
    """A chart refresh cannot leave an in-flight authenticated replay crumb-free."""

    cache_path = tmp_path / "session.json"
    cookies = httpx.Cookies()
    cookies.set("A3", "old-cookie", domain=".yahoo.com", path="/")
    save_session_cache(cache_path, cookies, "old-crumb", time.time() + 3600)
    quote_started = asyncio.Event()
    chart_finished = asyncio.Event()
    paths: list[str] = []
    chart_attempts = 0
    quote_attempts = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal chart_attempts, quote_attempts
        paths.append(request.url.path)
        if request.url.path == "/v7/finance/quote":
            quote_attempts += 1
            if quote_attempts == 1:
                assert request.url.params["crumb"] == "old-crumb"
                quote_started.set()
                await chart_finished.wait()
                return httpx.Response(
                    401,
                    json={"finance": {"error": {"description": "Invalid Crumb"}}},
                )
            assert request.url.params["crumb"] == "new-crumb"
            return httpx.Response(200, text="quote-ok")
        if request.url.path == "/v8/finance/chart/AAPL":
            chart_attempts += 1
            if chart_attempts == 1:
                await quote_started.wait()
                return httpx.Response(401)
            chart_finished.set()
            return httpx.Response(200, text="chart-ok")
        if request.url.path == "/":
            return httpx.Response(
                200,
                headers={"set-cookie": "A3=new-cookie; Domain=.yahoo.com; Path=/"},
            )
        if request.url.path == "/v1/test/getcrumb":
            return httpx.Response(200, text="new-crumb")
        raise AssertionError(request.url.path)

    client = YahooClient(
        session_cache_path=cache_path, transport=httpx.MockTransport(handle)
    )
    try:
        quote, chart = await asyncio.gather(
            client.get("/v7/finance/quote", {}),
            client.get("/v8/finance/chart/AAPL", {}, use_crumb=False),
        )
    finally:
        await client.aclose()

    assert (quote, chart) == ("quote-ok", "chart-ok")
    assert paths == [
        "/v7/finance/quote",
        "/v8/finance/chart/AAPL",
        "/",
        "/v8/finance/chart/AAPL",
        "/v1/test/getcrumb",
        "/v7/finance/quote",
    ]


@pytest.mark.parametrize(
    ("header", "expected_delay"),
    [
        ("2", 2.0),
        (format_datetime(datetime.fromtimestamp(1003, timezone.utc), usegmt=True), 3.0),
        ("not-a-delay", 0.25),
        ("NaN", 0.25),
        ("-2", 0.0),
    ],
)
@pytest.mark.asyncio
async def test_retry_after_controls_retry_delay(
    monkeypatch: pytest.MonkeyPatch, header: str, expected_delay: float
) -> None:
    """Numeric/date delays are honored; malformed and past values stay safe."""

    sleeps: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay: float) -> None:
        await real_sleep(0)
        sleeps.append(delay)

    responses = iter(
        [httpx.Response(503, headers={"Retry-After": header}), httpx.Response(200)]
    )
    monkeypatch.setattr("yoghurt.client.time.time", lambda: 1000.0)
    monkeypatch.setattr("yoghurt.client.asyncio.sleep", fake_sleep)
    client = YahooClient(
        transport=httpx.MockTransport(lambda _request: next(responses)),
        use_session_cache=False,
    )
    try:
        await client.get("/v8/finance/chart/AAPL", {}, use_crumb=False)
    finally:
        await client.aclose()

    assert sleeps == [expected_delay]


@pytest.mark.asyncio
async def test_retry_after_beyond_bound_surfaces_without_early_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A server delay beyond the wait budget is not clamped into an early replay."""

    requests = 0
    real_sleep = asyncio.sleep

    def handle(_request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(TOO_MANY_REQUESTS, headers={"Retry-After": "120"})

    async def fail_sleep(_delay: float) -> None:
        await real_sleep(0)
        message = "must not sleep or replay"
        raise AssertionError(message)

    monkeypatch.setattr("yoghurt.client.asyncio.sleep", fail_sleep)
    client = YahooClient(transport=httpx.MockTransport(handle), use_session_cache=False)
    try:
        with pytest.raises(YahooRequestError) as exc_info:
            await client.get("/v8/finance/chart/AAPL", {}, use_crumb=False)
    finally:
        await client.aclose()

    assert exc_info.value.status_code == TOO_MANY_REQUESTS
    assert requests == 1
