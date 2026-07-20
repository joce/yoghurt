"""Tests for the YahooModel base: the template every Yahoo model follows."""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from yoghurt.models import YahooModel

# Raw* types are pydantic field annotations resolved at class-creation time,
# so (unlike a plain type-hint import) they must be available at runtime.
from yoghurt.models._base import (  # ruff:ignore[typing-only-first-party-import]
    RawDate,
    RawDateOrNone,
    RawFloat,
    RawFloatOrNone,
    RawInt,
    RawIntOrNone,
)

_MARKET_CAP = 42
_RAW_TOTAL_PAY = 16759518
_RAW_SMALL_INT = 3
_RAW_EPOCH_SECONDS = 1735689600


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


class _RawFmtHolder(YahooModel):
    """Minimal fixture model exercising every Raw* value type."""

    raw_date: RawDate | None = None
    raw_date_or_none: RawDateOrNone = None
    raw_float: RawFloat | None = None
    raw_float_or_none: RawFloatOrNone = None
    raw_int: RawInt | None = None
    raw_int_or_none: RawIntOrNone = None


def test_raw_int_accepts_bare_scalar() -> None:
    """A bare int passes through unchanged."""

    holder = _RawFmtHolder.model_validate({"rawInt": _RAW_SMALL_INT})
    assert holder.raw_int == _RAW_SMALL_INT


def test_raw_float_unwraps_raw_fmt_long_fmt_wrapper() -> None:
    """A {raw, fmt, longFmt} wrapper resolves to its raw value."""

    holder = _RawFmtHolder.model_validate(
        {
            "rawFloat": {
                "raw": _RAW_TOTAL_PAY,
                "fmt": "16.76M",
                "longFmt": "16,759,518",
            }
        }
    )
    assert holder.raw_float == pytest.approx(float(_RAW_TOTAL_PAY))


def test_raw_int_unwraps_raw_fmt_wrapper_without_long_fmt() -> None:
    """A {raw, fmt} wrapper (no longFmt) also unwraps to raw."""

    holder = _RawFmtHolder.model_validate(
        {"rawInt": {"raw": _RAW_SMALL_INT, "fmt": "3"}}
    )
    assert holder.raw_int == _RAW_SMALL_INT


def test_raw_int_unwraps_wrapper_with_null_fmt() -> None:
    """A wrapper with fmt=None (observed in the corpus) still unwraps to raw."""

    holder = _RawFmtHolder.model_validate(
        {"rawInt": {"raw": 0, "fmt": None, "longFmt": "0"}}
    )
    assert holder.raw_int == 0


def test_raw_int_unwraps_raw_only_wrapper() -> None:
    """A wrapper carrying only the raw key (no fmt/longFmt) unwraps cleanly."""

    holder = _RawFmtHolder.model_validate({"rawInt": {"raw": _RAW_SMALL_INT}})
    assert holder.raw_int == _RAW_SMALL_INT


def test_raw_int_rejects_unknown_wrapper_key() -> None:
    """A wrapper key outside {raw, fmt, longFmt} fails validation (drift alarm)."""

    with pytest.raises(ValidationError, match="unexpected keys"):
        _RawFmtHolder.model_validate({"rawInt": {"raw": 1, "surpriseField": "new"}})


def test_raw_int_rejects_empty_dict() -> None:
    """Plain Raw* (not Raw*OrNone) still rejects {} when the field has no default.

    ``{}`` unwraps to ``None`` at the validator level (see
    ``test_raw_int_or_none_unwraps_empty_dict_to_none`` below), but a plain
    ``RawInt`` field (no ``| None`` in its own annotation) still rejects
    that resolved ``None`` at the ``int`` core-validation step — this is
    the documented reason ``Raw*OrNone`` exists as a separate family
    rather than always writing ``Raw* | None``.
    """

    with pytest.raises(ValidationError, match="int_type"):
        _RawFmtHolder.model_validate({"rawInt": {}})


def test_raw_int_or_none_unwraps_empty_dict_to_none() -> None:
    """RawIntOrNone maps an empty-dict wrapper to None (batch c2 evidence)."""

    holder = _RawFmtHolder.model_validate({"rawIntOrNone": {}})
    assert holder.raw_int_or_none is None


def test_raw_float_or_none_unwraps_empty_dict_to_none() -> None:
    """RawFloatOrNone maps an empty-dict wrapper to None (batch c2 evidence)."""

    holder = _RawFmtHolder.model_validate({"rawFloatOrNone": {}})
    assert holder.raw_float_or_none is None


def test_raw_date_or_none_unwraps_empty_dict_to_none() -> None:
    """RawDateOrNone maps an empty-dict wrapper to None."""

    holder = _RawFmtHolder.model_validate({"rawDateOrNone": {}})
    assert holder.raw_date_or_none is None


def test_raw_int_or_none_still_unwraps_populated_wrapper() -> None:
    """RawIntOrNone still resolves a populated wrapper to its raw value."""

    holder = _RawFmtHolder.model_validate(
        {"rawIntOrNone": {"raw": _RAW_SMALL_INT, "fmt": "3", "longFmt": "3"}}
    )
    assert holder.raw_int_or_none == _RAW_SMALL_INT


def test_raw_int_or_none_accepts_bare_none() -> None:
    """RawIntOrNone accepts a bare null the same as any optional field."""

    holder = _RawFmtHolder.model_validate({"rawIntOrNone": None})
    assert holder.raw_int_or_none is None


def test_raw_date_unwraps_epoch_to_calendar_date() -> None:
    """RawDate resolves a wrapped epoch-seconds value to a calendar date."""

    holder = _RawFmtHolder.model_validate(
        {"rawDate": {"raw": _RAW_EPOCH_SECONDS, "fmt": "2025-01-01"}}
    )
    assert holder.raw_date == datetime.date(2025, 1, 1)


def test_raw_date_accepts_bare_epoch() -> None:
    """RawDate also accepts a bare epoch-seconds int, unwrapped or not."""

    holder = _RawFmtHolder.model_validate({"rawDate": _RAW_EPOCH_SECONDS})
    assert holder.raw_date == datetime.date(2025, 1, 1)
