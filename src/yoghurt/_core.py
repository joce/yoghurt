"""Async endpoint core: envelopes, error mapping, default client, calls."""

from __future__ import annotations

import json
from typing import Any, Final, cast

from yoghurt.exceptions import (
    SymbolNotFoundError,
    YahooApiError,
    YahooRequestError,
)

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


def interpret_body(
    command: str, body: str, *, symbol: str | None = None
) -> dict[str, Any]:
    """Parse a Yahoo response body and enforce the error contract.

    Returns:
        dict[str, Any]: The full parsed payload (envelope included).

    Raises:
        YahooApiError: If the body is not valid JSON or carries an error.
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        # Observed in the wild: HTTP 200 with a broken JSON body
        # (corpus: timeseries/AAPL_types_00.json).
        message = f"Yahoo response is not valid JSON: {exc}"
        raise YahooApiError(code="malformed-response", description=message) from exc
    error = _envelope_error(command, payload)
    if error is not None:
        _raise_for_envelope_error(error, symbol=symbol, http_status=None)
    payload_dict = _as_object_dict(payload)
    if payload_dict is None:
        message = "Yahoo response is not a JSON object"
        raise YahooApiError(code="malformed-response", description=message)
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
