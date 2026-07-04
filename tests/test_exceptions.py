"""Tests for the yoghurt exception hierarchy."""

from __future__ import annotations

from yoghurt.exceptions import YahooRequestError


def test_yahoo_request_error_carries_body() -> None:
    """The response body is stored verbatim when provided."""

    exc = YahooRequestError(404, "https://x", reason="nope", body='{"e": 1}')

    assert exc.body == '{"e": 1}'


def test_yahoo_request_error_body_defaults_to_none() -> None:
    """The response body defaults to None when not provided."""

    assert YahooRequestError(500, "https://x").body is None
