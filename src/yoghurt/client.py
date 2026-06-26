"""Async Yahoo Finance client that returns raw response bodies."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Final, Literal

import httpx2 as httpx

from yoghurt.exceptions import YahooRequestError, YahooUnavailableError
from yoghurt.session_cache import (
    default_cache_path,
    load_session_cache,
    save_session_cache,
)

if TYPE_CHECKING:
    from http.cookiejar import Cookie
    from pathlib import Path

    from yoghurt.types import ParamValue


class YahooClient:
    """Async Yahoo Finance API client."""

    _YAHOO_FINANCE_URL: Final[str] = "https://finance.yahoo.com"
    _YAHOO_FINANCE_QUERY_URL: Final[str] = "https://query1.finance.yahoo.com"
    _CRUMB_URL: Final[str] = _YAHOO_FINANCE_QUERY_URL + "/v1/test/getcrumb"
    _ACCEPT_MIME_TYPES: Final[str] = (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.7"
    )
    _USER_AGENT: Final[str] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.3240.64"
    )
    _YAHOO_FINANCE_HEADERS: Final[dict[str, str]] = {
        "authority": "finance.yahoo.com",
        "accept": _ACCEPT_MIME_TYPES,
        "accept-language": "en-US,en;q=0.9",
        "upgrade-insecure-requests": "1",
        "user-agent": _USER_AGENT,
    }
    _REQUEST_ATTEMPTS: Final[int] = 3
    _RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({429, 502, 503, 504})
    _RETRY_DELAY_SECONDS: Final[float] = 0.25

    def __init__(
        self,
        *,
        timeout: httpx.Timeout | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        use_session_cache: bool = True,
        refresh_session: bool = False,
        session_cache_path: Path | None = None,
    ) -> None:
        """Initialize the Yahoo client."""

        self._timeout = timeout or httpx.Timeout(connect=5, read=15, write=5, pool=5)
        self._client = httpx.AsyncClient(
            headers={
                "authority": "query1.finance.yahoo.com",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "origin": self._YAHOO_FINANCE_URL,
                "user-agent": self._USER_AGENT,
            },
            timeout=self._timeout,
            transport=transport,
        )
        self._expiry = 0.0
        self._crumb = ""
        self._use_session_cache = use_session_cache
        self._refresh_session = refresh_session
        self._session_cache_path = session_cache_path or default_cache_path()
        self._logger = logging.getLogger(__name__)
        self._refresh_lock = asyncio.Lock()
        self._load_cached_session()

    def _load_cached_session(self) -> None:
        if not self._use_session_cache or self._refresh_session:
            return
        cached_session = load_session_cache(self._session_cache_path)
        if cached_session is None or not cached_session.is_valid:
            return
        self._client.cookies.update(cached_session.cookies)
        self._crumb = cached_session.crumb
        self._expiry = cached_session.expiry

    def _save_cached_session(self) -> None:
        if not self._use_session_cache or not self._crumb:
            return
        try:
            save_session_cache(
                self._session_cache_path,
                self._client.cookies,
                self._crumb,
                self._expiry,
            )
        except OSError:
            self._logger.warning("Could not save Yahoo session cache")

    @staticmethod
    def _redact_url(url: httpx.URL) -> str:
        params = [
            (name, value) for name, value in url.params.multi_items() if name != "crumb"
        ]
        return str(url.copy_with(params=params))

    async def _request_or_raise(
        self,
        method: Literal["GET", "POST"],
        url: str,
        *,
        context: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> httpx.Response:
        request = self._client.get if method == "GET" else self._client.post
        attempt = 1
        while True:
            try:
                response = await request(url, **kwargs)
                if response.is_error:
                    response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # noqa: PERF203
                status_code = exc.response.status_code if exc.response else -1
                if (
                    method == "GET"
                    and status_code in self._RETRYABLE_STATUS_CODES
                    and attempt < self._REQUEST_ATTEMPTS
                ):
                    await asyncio.sleep(self._RETRY_DELAY_SECONDS * attempt)
                    attempt += 1
                    continue
                url_str = self._redact_url(exc.request.url)
                raise YahooRequestError(status_code, url_str) from exc
            except httpx.TransportError as exc:
                if method == "GET" and attempt < self._REQUEST_ATTEMPTS:
                    await asyncio.sleep(self._RETRY_DELAY_SECONDS * attempt)
                    attempt += 1
                    continue
                raise YahooUnavailableError(context) from exc
            else:
                return response

    async def _refresh_cookies(self) -> None:
        def _is_eu_consent_redirect(response: httpx.Response) -> bool:
            return (
                "guce.yahoo.com" in response.headers.get("Location", "")
                and response.is_redirect
            )

        self._client.cookies.clear()
        response = await self._request_or_raise(
            "GET",
            self._YAHOO_FINANCE_URL,
            context="login",
            headers=self._YAHOO_FINANCE_HEADERS,
            follow_redirects=False,
        )
        cookies = response.cookies
        if _is_eu_consent_redirect(response):
            cookies = await self._get_cookies_eu()
        if not any(cookie == "A3" for cookie in cookies):
            raise YahooRequestError(
                response.status_code,
                str(response.url),
                reason="A3 cookie missing after login",
            )
        self._client.cookies.update(cookies)
        self._refresh_expiry(cookies)

    def _refresh_expiry(self, cookies: httpx.Cookies) -> None:
        ten_years = 60 * 60 * 24 * 365 * 10
        expiry = time.time() + ten_years
        cookie: Cookie
        for cookie in cookies.jar:
            if cookie.domain != ".yahoo.com" or cookie.expires is None:
                continue
            cookie_expiry: float = cookie.expires
            expiry = min(expiry, cookie_expiry)
        self._expiry = expiry
        self._crumb = ""

    @staticmethod
    def _extract_session_id(response: httpx.Response) -> str:
        session_id = response.url.params.get("sessionId", "")
        if not session_id:
            raise YahooRequestError(
                response.status_code,
                str(response.url),
                reason="Session identifier missing in consent redirect",
            )
        return session_id

    @staticmethod
    def _extract_csrf_token(response: httpx.Response) -> str:
        guce_url = httpx.URL("")
        for history_response in response.history:
            if history_response.url.host == "guce.yahoo.com":
                guce_url = history_response.url
                break
        csrf_token = guce_url.params.get("gcrumb", "")
        if not csrf_token:
            raise YahooRequestError(
                response.status_code,
                str(response.url),
                reason="CSRF token missing in consent redirect history",
            )
        return csrf_token

    @staticmethod
    def _extract_gucs_cookie(response: httpx.Response) -> httpx.Cookies:
        gucs_cookie = httpx.Cookies()
        for history_response in response.history:
            if history_response.cookies.get("GUCS") is not None:
                gucs_cookie = history_response.cookies
                break
        if len(gucs_cookie) == 0:
            raise YahooRequestError(
                response.status_code,
                str(response.url),
                reason="GUCS cookie missing in consent redirect history",
            )
        return gucs_cookie

    async def _get_cookies_eu(self) -> httpx.Cookies:
        response = await self._request_or_raise(
            "GET",
            self._YAHOO_FINANCE_URL,
            context="EU consent initial request",
            headers=self._YAHOO_FINANCE_HEADERS,
            follow_redirects=True,
        )
        session_id = self._extract_session_id(response)
        csrf_token = self._extract_csrf_token(response)
        gucs_cookie = self._extract_gucs_cookie(response)
        referrer_url = (
            "https://consent.yahoo.com/v2/collectConsent?sessionId=" + session_id
        )
        consent_headers = {
            "origin": "https://consent.yahoo.com",
            "host": "consent.yahoo.com",
            "content-type": "application/x-www-form-urlencoded",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.5",
            "accept-encoding": "gzip, deflate, br",
            "dnt": "1",
            "referer": referrer_url,
            "user-agent": self._USER_AGENT,
        }
        data = {
            "csrfToken": csrf_token,
            "sessionId": session_id,
            "namespace": "yahoo",
            "agree": "agree",
        }
        self._client.cookies.update(gucs_cookie)
        response = await self._request_or_raise(
            "POST",
            referrer_url,
            context="EU consent posting",
            headers=consent_headers,
            data=data,
            follow_redirects=True,
        )
        for history_response in [*list(response.history), response]:
            if history_response.cookies.get("A3") is not None:
                return history_response.cookies
        raise YahooRequestError(
            response.status_code,
            str(response.url),
            reason="A3 cookie missing after consent POST",
        )

    async def _refresh_crumb(self) -> None:
        self._crumb = ""
        response = await self._request_or_raise(
            "GET",
            self._CRUMB_URL,
            context="fetching crumb",
        )
        self._crumb = response.text
        if not self._crumb:
            raise YahooRequestError(
                response.status_code,
                str(response.url),
                reason="Crumb response empty",
            )

    async def _ensure_ready(self) -> None:
        async with self._refresh_lock:
            one_minute = 60.0
            if self._expiry - time.time() < one_minute:
                await self._refresh_cookies()
            if not self._crumb:
                await self._refresh_crumb()
            self._save_cached_session()

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Call a Yahoo Finance endpoint.

        Returns:
            str: Raw Yahoo response body.
        """

        await self._ensure_ready()
        request_params = dict(params)
        if use_crumb and self._crumb:
            request_params["crumb"] = self._crumb
        host = base_url or self._YAHOO_FINANCE_QUERY_URL
        response = await self._request_or_raise(
            "GET",
            host + path,
            context=f"api call: {path}",
            params=request_params,
        )
        return response.text

    async def post(
        self,
        path: str,
        params: dict[str, ParamValue],
        json_body: dict[str, Any],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Call a Yahoo Finance POST endpoint with a JSON body.

        Returns:
            str: Raw Yahoo response body.
        """

        await self._ensure_ready()
        request_params = dict(params)
        if use_crumb and self._crumb:
            request_params["crumb"] = self._crumb
        host = base_url or self._YAHOO_FINANCE_QUERY_URL
        response = await self._request_or_raise(
            "POST",
            host + path,
            context=f"api call: {path}",
            params=request_params,
            json=json_body,
        )
        return response.text

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""

        await self._client.aclose()
