"""Persist Yahoo session data between one-shot CLI calls."""

from __future__ import annotations

import json
import math
import tempfile
import time
from dataclasses import dataclass
from http.cookiejar import Cookie
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from typing import Any, Final, cast

import httpx2 as httpx

from yoghurt._urls import YAHOO_FINANCE_QUERY_URL


@dataclass(frozen=True, slots=True)
class CachedSession:
    """Cookie and crumb data loaded from disk."""

    cookies: httpx.Cookies
    crumb: str
    expiry: float

    @property
    def is_valid(self) -> bool:
        """Whether the cache is still usable."""

        one_minute: Final[float] = 60.0
        if not self.crumb or self.expiry - time.time() < one_minute:
            return False
        try:
            request = httpx.Request("GET", YAHOO_FINANCE_QUERY_URL)
            self.cookies.set_cookie_header(request)
            applicable = SimpleCookie(request.headers.get("cookie", ""))
        except (CookieError, ValueError):
            return False
        a3 = applicable.get("A3")
        return a3 is not None and bool(a3.value)


def default_cache_path() -> Path:
    """Return yoghurt's default Yahoo session cache path."""

    return Path.home() / ".cache" / "yoghurt" / "yahoo-session.json"


def _cookie_to_payload(cookie: Cookie) -> dict[str, Any]:
    return {
        "name": cookie.name,
        "value": cookie.value,
        "domain": cookie.domain,
        "path": cookie.path,
        "expires": cookie.expires,
        "secure": cookie.secure,
    }


def _cookie_from_payload(payload: dict[str, Any]) -> Cookie:
    return Cookie(
        version=0,
        name=str(payload["name"]),
        value=str(payload["value"]),
        port=None,
        port_specified=False,
        domain=str(payload["domain"]),
        domain_specified=True,
        domain_initial_dot=str(payload["domain"]).startswith("."),
        path=str(payload.get("path", "/")),
        path_specified=True,
        secure=bool(payload.get("secure")),
        expires=int(payload["expires"]) if payload.get("expires") is not None else None,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
    )


def load_session_cache(  # ruff:ignore[too-many-return-statements] - malformed cache shapes each return a miss
    path: Path,
) -> CachedSession | None:
    """Load cached Yahoo session state if present and well formed.

    Returns:
        CachedSession | None: Cached session data, or None when unavailable.
    """

    try:  # ruff:ignore[too-many-statements-in-try-clause] - malformed cache is always a miss
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        payload = cast("dict[str, Any]", payload)
        cookie_payloads = payload.get("cookies")
        if not isinstance(payload.get("crumb"), str) or not isinstance(
            cookie_payloads, list
        ):
            return None
        cookies = httpx.Cookies()
        for cookie_payload in cast("list[Any]", cookie_payloads):
            if not isinstance(cookie_payload, dict):
                return None
            cookie_record = cast("dict[str, Any]", cookie_payload)
            if any(
                not isinstance(cookie_record.get(key), str)
                for key in ("name", "value", "domain")
            ):
                return None
            cookies.jar.set_cookie(_cookie_from_payload(cookie_record))
        crumb = str(payload.get("crumb", ""))
        expiry = float(payload.get("expiry", 0.0))
        if not math.isfinite(expiry):
            return None
    except (OSError, TypeError, ValueError, OverflowError, KeyError):
        return None
    return CachedSession(cookies=cookies, crumb=crumb, expiry=expiry)


def save_session_cache(
    path: Path, cookies: httpx.Cookies, crumb: str, expiry: float
) -> None:
    """Save Yahoo session state for reuse by later CLI invocations."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "crumb": crumb,
        "expiry": expiry,
        "cookies": [_cookie_to_payload(cookie) for cookie in cookies.jar],
    }
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, separators=(",", ":"))
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
