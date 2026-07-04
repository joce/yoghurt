"""Typed Yahoo response models and quote enums.

Every model here is a frozen pydantic model built on :class:`YahooModel`:
snake_case fields, camelCase wire aliases, unknown fields preserved rather
than dropped. See :mod:`yoghurt.models._base` for the full template. The
package also carries the quote enums (:class:`QuoteType`,
:class:`MarketState`, :class:`OptionsType`, :class:`PriceAlertConfidence`),
whose members are corpus-verified except where an enum's docstring notes a
value known only from prior use.
"""

from __future__ import annotations

from yoghurt.models._base import YahooModel
from yoghurt.models.enums import (
    MarketState,
    OptionsType,
    PriceAlertConfidence,
    QuoteType,
)
from yoghurt.models.quote import CorporateAction, Quote

__all__ = [
    "CorporateAction",
    "MarketState",
    "OptionsType",
    "PriceAlertConfidence",
    "Quote",
    "QuoteType",
    "YahooModel",
]
