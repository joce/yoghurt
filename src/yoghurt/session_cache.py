"""Persist Yahoo session data between one-shot CLI calls."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from http.cookiejar import Cookie
from pathlib import Path
from typing import Any, Final

import httpx


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
        return bool(self.crumb) and self.expiry - time.time() >= one_minute


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


def load_session_cache(path: Path) -> CachedSession | None:
    """Load cached Yahoo session state if present and well formed.

    Returns:
        CachedSession | None: Cached session data, or None when unavailable.
    """

    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cookies = httpx.Cookies()
        for cookie_payload in payload.get("cookies", []):
            cookies.jar.set_cookie(_cookie_from_payload(cookie_payload))
        crumb = str(payload.get("crumb", ""))
        expiry = float(payload.get("expiry", 0.0))
    except (OSError, TypeError, ValueError, json.JSONDecodeError, KeyError):
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
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
