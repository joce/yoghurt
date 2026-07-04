"""Tests for the YahooModel base: the template every Yahoo model follows."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from yoghurt.models import YahooModel

_MARKET_CAP = 42


class _Quote(YahooModel):
    """Minimal fixture model mirroring a slice of a real Yahoo quote."""

    market_cap: int | None = None
    display_name: str = ""


def test_frozen_assignment_raises() -> None:
    """Response models are immutable: attribute assignment raises."""

    quote = _Quote.model_validate({"marketCap": 1})
    with pytest.raises(ValidationError):
        quote.market_cap = 2


def test_camel_case_wire_field_validates() -> None:
    """A camelCase wire key populates the snake_case Python field."""

    quote = _Quote.model_validate({"marketCap": 1})
    assert quote.market_cap == 1


def test_unknown_key_lands_in_model_extra() -> None:
    """Unknown wire fields are preserved on model_extra, never dropped."""

    quote = _Quote.model_validate({"marketCap": 1, "someNewYahooField": "surprise"})
    assert quote.model_extra is not None
    assert quote.model_extra["someNewYahooField"] == "surprise"


def test_populate_by_name_allows_construction_by_field_name() -> None:
    """Construction by the Python (snake_case) field name also works."""

    quote = _Quote(market_cap=_MARKET_CAP)
    assert quote.market_cap == _MARKET_CAP


def test_whitespace_is_stripped_on_str_fields() -> None:
    """Yahoo pads some string fields; str_strip_whitespace strips them."""

    quote = _Quote.model_validate({"displayName": "  Apple Inc.  "})
    assert quote.display_name == "Apple Inc."
