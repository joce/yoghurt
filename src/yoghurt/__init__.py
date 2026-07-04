"""Yahoo Finance data, one call at a time, with no response modeling to fight.

Yoghurt is a synchronous library over Yahoo Finance's undocumented endpoints:
call a method, get back a plain dict or a typed :class:`~yoghurt.frames.Frame`
you can convert to polars, pandas, or Arrow — for example, ``import yoghurt``
then ``bars = yoghurt.Ticker("AAPL").chart(interval="1d").to_polars()``.
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
    from yoghurt.api import (
        Ticker,
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
    from yoghurt.frames import Chart, Frame


def __getattr__(name: str) -> Any:  # noqa: ANN401 - PEP 562 module __getattr__
    """Lazily import heavy public names on first access (PEP 562).

    ``Frame``/``Chart`` and the ``Ticker``/function surface live in
    :mod:`yoghurt.frames` and :mod:`yoghurt.api`, both of which pull in
    polars; deferring the import here keeps that cost off every import of
    the ``yoghurt`` package (including the CLI, which imports the package
    by virtue of ``yoghurt.cli`` being a submodule).

    Returns:
        Any: The resolved attribute, also cached on the module for reuse.

    Raises:
        AttributeError: If ``name`` is not a lazily-exported attribute.
    """

    if name not in __all__ or name == "__version__":
        message = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(message)
    module_name = "yoghurt.frames" if name in {"Chart", "Frame"} else "yoghurt.api"
    module = importlib.import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = [
    "Chart",
    "Frame",
    "SymbolNotFoundError",
    "Ticker",
    "YahooApiError",
    "YahooClient",
    "YahooRequestError",
    "YahooUnavailableError",
    "YoghurtError",
    "__version__",
    "configure",
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
