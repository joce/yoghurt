"""Typed Yahoo response models and quote enums.

Every model here is a frozen pydantic model built on :class:`YahooModel`:
snake_case fields, camelCase wire aliases, unknown fields preserved rather
than dropped. See :mod:`yoghurt.models._base` for the full template. The
package also carries the corpus-verified quote enums (:class:`QuoteType`,
:class:`MarketState`, :class:`OptionType`, :class:`PriceAlertConfidence`).
"""

from __future__ import annotations

from yoghurt.models._base import YahooModel
from yoghurt.models.enums import (
    MarketState,
    OptionType,
    PriceAlertConfidence,
    QuoteType,
)

__all__ = [
    "MarketState",
    "OptionType",
    "PriceAlertConfidence",
    "QuoteType",
    "YahooModel",
]
