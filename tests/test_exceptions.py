"""Tests for the yoghurt exception hierarchy."""

from __future__ import annotations

from yoghurt.exceptions import SymbolNotFoundError, YahooApiError, YahooRequestError

_HTTP_BAD_REQUEST = 400


def test_yahoo_request_error_carries_body() -> None:
    """The response body is stored verbatim when provided."""

    exc = YahooRequestError(404, "https://x", reason="nope", body='{"e": 1}')

    assert exc.body == '{"e": 1}'


def test_yahoo_request_error_body_defaults_to_none() -> None:
    """The response body defaults to None when not provided."""

    assert YahooRequestError(500, "https://x").body is None


def test_yahoo_api_error_carries_code_and_description() -> None:
    """The code, description, and http_status are stored verbatim."""
    exc = YahooApiError(
        code="Bad Request", description="invalid crumb", http_status=_HTTP_BAD_REQUEST
    )
    assert exc.code == "Bad Request"
    assert exc.description == "invalid crumb"
    assert exc.http_status == _HTTP_BAD_REQUEST
    assert "Bad Request" in str(exc)
    assert "invalid crumb" in str(exc)


def test_symbol_not_found_is_a_yahoo_api_error() -> None:
    """SymbolNotFoundError subclasses YahooApiError and carries the symbol."""
    exc = SymbolNotFoundError("ZZZZXYZQ")
    assert isinstance(exc, YahooApiError)
    assert exc.symbol == "ZZZZXYZQ"
    assert "ZZZZXYZQ" in str(exc)
