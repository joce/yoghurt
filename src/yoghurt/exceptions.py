"""Yoghurt-specific exception hierarchy."""

from __future__ import annotations


class YoghurtError(Exception):
    """Base exception for all yoghurt errors."""


class YahooRequestError(YoghurtError):
    """Raised when Yahoo rejects an HTTP request."""

    def __init__(
        self,
        status_code: int,
        url: str,
        *,
        reason: str | None = None,
        body: str | None = None,
    ) -> None:
        """Initialize the request error."""

        message = f"Yahoo request rejected with HTTP {status_code} for {url}"
        if reason:
            message = f"{message}: {reason}"
        super().__init__(message)
        self.status_code = status_code
        self.url = url
        self.reason = reason
        self.body = body


class YahooUnavailableError(YoghurtError):
    """Raised when Yahoo cannot be reached due to transport failure."""

    def __init__(self, context: str) -> None:
        """Initialize the transport error."""

        super().__init__(f"Yahoo Finance unavailable while processing {context}")
        self.context = context


class YahooApiError(YoghurtError):
    """Raised when Yahoo reports an application-level error payload."""

    def __init__(
        self,
        *,
        code: str,
        description: str,
        http_status: int | None = None,
    ) -> None:
        """Initialize the API error."""

        super().__init__(f"Yahoo API error {code}: {description}")
        self.code = code
        self.description = description
        self.http_status = http_status


class SymbolNotFoundError(YahooApiError):
    """Raised when Yahoo indicates a symbol does not exist."""

    def __init__(
        self,
        symbol: str,
        *,
        description: str | None = None,
        http_status: int | None = None,
    ) -> None:
        """Initialize the symbol lookup error."""

        super().__init__(
            code="Not Found",
            description=description or f"symbol not found: {symbol}",
            http_status=http_status,
        )
        self.symbol = symbol
