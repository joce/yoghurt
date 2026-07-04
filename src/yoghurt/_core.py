"""Async endpoint core: envelopes, error mapping, default client, calls."""

from __future__ import annotations

import atexit
import concurrent.futures
import contextlib
import json
import threading
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Final, cast

from yoghurt._bridge import run
from yoghurt.client import YahooClient
from yoghurt.commands import COMMANDS_BY_NAME
from yoghurt.exceptions import (
    SymbolNotFoundError,
    YahooApiError,
    YahooRequestError,
)
from yoghurt.params import build_params, build_path, validate_params
from yoghurt.query import parse as parse_query

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    import httpx2 as httpx

    from yoghurt.types import ParamValue

_FINANCE: Final[str] = "finance"
ENVELOPES: Final[dict[str, str | None]] = {
    "analyst": None,
    "calendar-events": _FINANCE,
    "chart": "chart",
    "insights": _FINANCE,
    "market-info": _FINANCE,
    "market-summary": "marketSummaryResponse",
    "market-time": _FINANCE,
    "options": "optionChain",
    "price-insights": _FINANCE,
    "quote": "quoteResponse",
    "quote-summary": "quoteSummary",
    "quote-type": "quoteType",
    "ratings-top": None,
    "recommendations-by-symbol": _FINANCE,
    "screener": _FINANCE,
    "screener-discover": _FINANCE,
    "screener-instrument-fields": _FINANCE,
    "screener-predefined": _FINANCE,
    "sector": "data",
    "spark": "spark",
    "stock-recommender": None,
    "timeseries": "timeseries",
    "timeseries-fields": "timeseriesfields",
    "trending": _FINANCE,
    "visualization": _FINANCE,
}
_NOT_FOUND_CODE: Final[str] = "Not Found"  # Yahoo's verbatim wire value (see corpus)


def _as_object_dict(value: object) -> dict[str, Any] | None:
    """Narrow an arbitrary JSON value to a string-keyed dict, if it is one.

    Returns:
        dict[str, Any] | None: The value, re-typed, or None if not a dict.
    """
    if not isinstance(value, dict):
        return None
    return cast("dict[str, Any]", value)


def _envelope_error(command: str, payload: object) -> dict[str, Any] | None:
    """Extract the envelope's error object, if the command uses an envelope.

    Returns:
        dict[str, Any] | None: The error object, or None if absent/not applicable.
    """
    envelope_key = ENVELOPES.get(command)
    payload_dict = _as_object_dict(payload)
    if envelope_key is None or payload_dict is None:
        return None
    envelope = _as_object_dict(payload_dict.get(envelope_key))
    if envelope is None:
        return None
    return _as_object_dict(envelope.get("error"))


def _raise_for_envelope_error(
    error: dict[str, Any],
    *,
    symbol: str | None,
    http_status: int | None,
    cause: BaseException | None = None,
) -> None:
    """Raise the appropriate exception for an enveloped Yahoo error object.

    Raises:
        SymbolNotFoundError: If the error code indicates a symbol lookup miss.
        YahooApiError: For any other enveloped error.
    """
    code = str(error.get("code", "unknown"))
    description = str(error.get("description", ""))
    if symbol is not None and code == _NOT_FOUND_CODE:
        raise SymbolNotFoundError(
            symbol, description=description, http_status=http_status
        ) from cause
    raise YahooApiError(
        code=code, description=description, http_status=http_status
    ) from cause


def _parse_json_object(body: str) -> dict[str, Any]:
    """Parse a response body into a JSON object, per the malformed-response contract.

    Returns:
        dict[str, Any]: The parsed payload.

    Raises:
        YahooApiError: If the body is not valid JSON or not a JSON object.
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        # Observed in the wild: HTTP 200 with a broken JSON body
        # (corpus: timeseries/AAPL_types_00.json).
        message = f"Yahoo response is not valid JSON: {exc}"
        raise YahooApiError(code="malformed-response", description=message) from exc
    payload_dict = _as_object_dict(payload)
    if payload_dict is None:
        message = "Yahoo response is not a JSON object"
        raise YahooApiError(code="malformed-response", description=message)
    return payload_dict


def interpret_body(
    command: str, body: str, *, symbol: str | None = None
) -> dict[str, Any]:
    """Parse a Yahoo response body and enforce the error contract.

    When ``symbol`` is given and the envelope reports a not-found error, the
    error raised is ``SymbolNotFoundError``, a ``YahooApiError`` subclass.
    Malformed-JSON bodies raise via :func:`_parse_json_object`; enveloped
    errors raise via :func:`_raise_for_envelope_error`.

    Returns:
        dict[str, Any]: The full parsed payload (envelope included).
    """
    payload_dict = _parse_json_object(body)
    error = _envelope_error(command, payload_dict)
    if error is not None:
        _raise_for_envelope_error(error, symbol=symbol, http_status=None)
    return payload_dict


def map_http_error(
    command: str, exc: YahooRequestError, *, symbol: str | None = None
) -> None:
    """Translate an HTTP-level rejection into the library error contract.

    Always raises; never returns.

    Raises:
        SymbolNotFoundError: For symbol-lookup 404 shapes.
        YahooApiError: For other Yahoo-reported error payloads.
    """
    if exc.body:
        try:
            payload: object = json.loads(exc.body)
        except json.JSONDecodeError:
            payload = None
        error = _envelope_error(command, payload)
        if error is not None:
            _raise_for_envelope_error(
                error, symbol=symbol, http_status=exc.status_code, cause=exc
            )
        payload_dict = _as_object_dict(payload)
        detail = payload_dict.get("detail") if payload_dict is not None else None
        if isinstance(detail, str):
            if symbol is not None and "not found" in detail.lower():
                raise SymbolNotFoundError(
                    symbol, description=detail, http_status=exc.status_code
                ) from exc
            raise YahooApiError(
                code=str(exc.status_code),
                description=detail,
                http_status=exc.status_code,
            ) from exc
    raise exc


_client: YahooClient | None = None
_client_options: dict[str, Any] = {}
_client_lock = threading.Lock()


def configure(
    *,
    timeout: httpx.Timeout | None = None,
    use_session_cache: bool = True,
    refresh_session: bool = False,
    session_cache_path: Path | None = None,
) -> None:
    """Set options for the library's shared Yahoo client.

    Must be called before the first data call; raises RuntimeError after.

    Raises:
        RuntimeError: If the shared client has already been created.
    """

    with _client_lock:
        if _client is not None:
            message = "configure() must be called before the first yoghurt call"
            raise RuntimeError(message)
        _client_options.update(
            timeout=timeout,
            use_session_cache=use_session_cache,
            refresh_session=refresh_session,
            session_cache_path=session_cache_path,
        )


def _get_client() -> YahooClient:
    global _client  # noqa: PLW0603 - module singleton by design
    with _client_lock:
        if _client is None:
            _client = YahooClient(**_client_options)
    return _client


def _reset_for_tests() -> None:  # pyright: ignore[reportUnusedFunction]
    """Drop the shared client so tests can reconfigure. Test-only."""
    global _client  # noqa: PLW0603 - module singleton by design
    with _client_lock:
        if _client is not None:
            with contextlib.suppress(Exception):
                run(_client.aclose())
        _client = None
        _client_options.clear()


_CLOSE_TIMEOUT_SECONDS: Final[float] = 2.0


def _close_default_client() -> None:
    """Best-effort aclose of the shared client at interpreter exit.

    The wait is bounded: at interpreter exit the bridge's daemon loop
    thread may already be dead, and an unbounded ``future.result()`` would
    hang forever. ``concurrent.futures.TimeoutError`` is suppressed
    explicitly — it subclasses ``Exception`` on all supported versions
    (a distinct ``Exception`` subclass on 3.10; an alias of the builtin
    ``TimeoutError`` on 3.11+), but spelling it out guarantees the exit
    path can never raise or hang regardless of interpreter version.
    """
    if _client is not None:
        with contextlib.suppress(Exception, concurrent.futures.TimeoutError):
            run(_client.aclose(), timeout=_CLOSE_TIMEOUT_SECONDS)


atexit.register(_close_default_client)


def _serialize(value: object) -> object:
    """Render a typed Python value exactly as a CLI user would spell it.

    Returns:
        object: The CLI-equivalent representation of ``value``.

    Raises:
        TypeError: If the value's type has no CLI-string equivalent.
    """

    if isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, list | tuple):
        items = cast("list[object] | tuple[object, ...]", value)
        return ",".join(str(item) for item in items)
    message = f"unsupported parameter value type: {type(value).__name__}"
    raise TypeError(message)


async def call_endpoint(
    command_name: str,
    *,
    values: Mapping[str, object],
    symbol: str | None = None,
) -> dict[str, Any]:
    """Call one modeled Yahoo endpoint with typed values.

    Yahoo-reported errors are translated per the library error contract (see
    :func:`map_http_error`); this only documents the fallback re-raise.

    Returns:
        dict[str, Any]: The full parsed response payload.

    Raises:
        YahooRequestError: If the HTTP failure carries no mappable payload.
    """

    command = COMMANDS_BY_NAME[command_name]
    wire_values = {name: _serialize(value) for name, value in values.items()}
    params = build_params(command, wire_values)
    validate_params(command, params)
    path = build_path(command, wire_values)
    client = _get_client()
    try:
        body = await client.get(
            path, params, use_crumb=command.use_crumb, base_url=command.base_url
        )
    except YahooRequestError as exc:
        map_http_error(command_name, exc, symbol=symbol)
        raise  # unreachable; map_http_error always raises
    return interpret_body(command_name, body, symbol=symbol)


_QUERY_ROUTE_PATHS: Final[dict[str, str]] = {
    "screener": "/v1/finance/screener",
    "visualization": "/v1/finance/visualization",
}
_QUERY_LANG: Final[str] = "en-US"
_QUERY_REGION: Final[str] = "US"


async def call_query(route: str, query: str) -> dict[str, Any]:
    """Run a DSL query against a data-platform route.

    Yahoo-reported errors are translated per the library error contract (see
    :func:`map_http_error`); this only documents the DSL parse failure and
    the fallback re-raise. ``query`` is parsed with
    :func:`yoghurt.query.parse`, which raises ``QueryError`` (a
    ``ValueError`` subclass) on malformed input; that propagates unchanged.

    Returns:
        dict[str, Any]: The full parsed response payload.

    Raises:
        YahooRequestError: If the HTTP failure carries no mappable payload.
    """

    statement = parse_query(query)
    params: dict[str, ParamValue] = {"lang": _QUERY_LANG, "region": _QUERY_REGION}
    if route == "screener":
        params["formatted"] = False
        params["useRecordsResponse"] = True
    client = _get_client()
    try:
        body = await client.post(_QUERY_ROUTE_PATHS[route], params, statement.to_body())
    except YahooRequestError as exc:
        map_http_error(route, exc)
        raise
    return interpret_body(route, body)


async def call_raw(
    path: str, params: Mapping[str, ParamValue] | None, *, use_crumb: bool
) -> dict[str, Any]:
    """Call an arbitrary Yahoo path with pre-serialized wire params.

    Unlike :func:`call_endpoint`, this bypasses ``COMMANDS_BY_NAME`` entirely:
    no path template, no param coercion or validation, and no envelope
    lookup. The body is parsed with the same malformed-response contract as
    every other call.

    Returns:
        dict[str, Any]: The parsed response payload, exactly as Yahoo sent it.

    Raises:
        YahooRequestError: If the HTTP failure carries no mappable payload.
    """

    client = _get_client()
    try:
        body = await client.get(path, dict(params or {}), use_crumb=use_crumb)
    except YahooRequestError as exc:
        map_http_error("raw", exc)
        raise
    return _parse_json_object(body)
