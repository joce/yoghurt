"""Fully-typed Yahoo Finance data, one call at a time.

Yoghurt is a synchronous library over Yahoo Finance's undocumented endpoints:
call a method, get back a corpus-verified pydantic model (see
:mod:`yoghurt.models`) or a typed :class:`~yoghurt.frames.Frame` you can
convert to polars, pandas, or Arrow — for example, ``import yoghurt`` then
``bars = yoghurt.Ticker("AAPL").chart(interval="1d").to_polars()`` or
``price = yoghurt.Ticker("AAPL").quote().regular_market_price``.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from yoghurt._core import configure

# __version__ is derived from the git tag by hatch-vcs and written to
# _version.py at build/install time (see pyproject.toml [tool.hatch.version]).
from yoghurt._version import __version__
from yoghurt.client import YahooClient
from yoghurt.exceptions import (
    SymbolNotFoundError,
    YahooApiError,
    YahooRequestError,
    YahooUnavailableError,
    YoghurtError,
)

if TYPE_CHECKING:
    # Real imports for type checkers only; at runtime these names resolve
    # lazily via __getattr__ below so importing the yoghurt package does not
    # pay polars' import cost just to run the CLI (which imports the package
    # by virtue of yoghurt.cli being a submodule).
    # Keep this block in manual parity with __all__ and __getattr__'s routing:
    # a name in one but not the other diverges pyright's view from runtime
    # (test_all_names_are_importable is the runtime drift gate).
    from yoghurt.api import (
        Ticker,
        history,
        market_info,
        market_summary,
        market_time,
        quotes,
        raw,
        screener,
        screener_discover,
        screener_instrument_fields,
        screener_predefined,
        sector,
        timeseries_fields,
        trending,
        visualization,
    )
    from yoghurt.frames import Chart, Frame, History, Spark, Timeseries
    from yoghurt.models import Quote, QuoteType


def __getattr__(name: str) -> Any:  # noqa: ANN401 - PEP 562 module __getattr__
    """Lazily import heavy public names on first access (PEP 562).

    ``Frame``/``Chart`` and the ``Ticker``/function surface live in
    :mod:`yoghurt.frames` and :mod:`yoghurt.api`, both of which pull in
    polars; ``Quote``/``QuoteType`` live in :mod:`yoghurt.models` (pydantic).
    Deferring the import here keeps that cost off every import of the
    ``yoghurt`` package (including the CLI, which imports the package by
    virtue of ``yoghurt.cli`` being a submodule).

    Returns:
        Any: The resolved attribute, also cached on the module for reuse.

    Raises:
        AttributeError: If ``name`` is not a lazily-exported attribute.
    """

    frames_names = {"Chart", "Frame", "History", "Spark", "Timeseries"}
    models_names = {"Quote", "QuoteType"}
    lazy_names = set(__all__) - {"__version__"} - set(globals())
    if name in frames_names:
        module_name = "yoghurt.frames"
    elif name in models_names:
        module_name = "yoghurt.models"
    elif name in lazy_names:
        module_name = "yoghurt.api"
    else:
        message = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(message)
    module = importlib.import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """List the public surface plus module dunders, hiding internal imports.

    Module-level helpers such as ``importlib`` and ``TYPE_CHECKING`` live in
    ``globals()`` too, but they are implementation details, not public API;
    only ``__all__`` and the module's own dunder attributes are surfaced for
    ``dir()`` and tab completion.

    Returns:
        list[str]: Sorted module attributes for ``dir()`` and tab completion.
    """

    return sorted(set(__all__) | {name for name in globals() if name.startswith("__")})


__all__ = [
    "Chart",
    "Frame",
    "History",
    "Quote",
    "QuoteType",
    "Spark",
    "SymbolNotFoundError",
    "Ticker",
    "Timeseries",
    "YahooApiError",
    "YahooClient",
    "YahooRequestError",
    "YahooUnavailableError",
    "YoghurtError",
    "__version__",
    "configure",
    "history",
    "market_info",
    "market_summary",
    "market_time",
    "quotes",
    "raw",
    "screener",
    "screener_discover",
    "screener_instrument_fields",
    "screener_predefined",
    "sector",
    "timeseries_fields",
    "trending",
    "visualization",
]
