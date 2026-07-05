"""Shared configuration for all Yahoo response models.

Also home to the ``Raw*`` wrapper-tolerant value types (:data:`RawFloat`,
:data:`RawInt`, :data:`RawDate`, and their nullable counterparts
:data:`RawFloatOrNone`, :data:`RawIntOrNone`, :data:`RawDateOrNone`): some
nested Yahoo rows (never top-level quote-summary module fields) wrap a
value as ``{"raw": ..., "fmt": ..., "longFmt": ...}`` instead of sending
the bare scalar directly, for example
``assetProfile.companyOfficers[].totalPay``. The ``Raw*`` types accept
either shape and always resolve to the bare ``raw`` value:

- A bare scalar passes through unchanged.
- A mapping is accepted only when its keys are a subset of ``{"raw",
  "fmt", "longFmt"}``; ``fmt``/``longFmt`` are presentation strings and
  are discarded. Any other key in the mapping fails validation, so wrapper
  drift (an unexpected new key inside the wrapper) surfaces loudly instead
  of silently passing through.
- An empty mapping ``{}`` resolves to ``None``: batch c2's
  ``earningsTrend.trend[].earningsEstimate``/``.epsTrend``/
  ``.epsRevisions`` (and the row-level ``growth``) send ``{}`` in place of
  every wrapped field when Yahoo has no analyst estimate to report (for
  example ``BAC-PL``, ``7203.T`` — see
  ``tests/fixtures/corpus/quote-summary/``), confirming the scenario the
  batch c1 docstring flagged as unobserved-so-far.

  Any field that can observe ``{}`` on the wire MUST use the
  ``Raw*OrNone`` variant, never plain ``Raw* | None``: pydantic applies a
  ``BeforeValidator`` *inside* the annotation it decorates, so
  ``Annotated[float, BeforeValidator(_unwrap_raw)] | None`` still routes a
  validator-returned ``None`` back into the ``float`` branch of the union
  and fails, instead of falling through to the ``None`` branch. The
  ``Raw*OrNone`` aliases below apply the validator to the whole ``T |
  None`` annotation instead, so a resolved ``None`` (bare ``null``, or an
  unwrapped ``{}``) validates correctly. Use plain ``Raw*`` (optionally
  with `` | None = None`` for a merely-absent-not-``{}`` field) only where
  the corpus has never shown ``{}`` for that exact field.

``RawDate``/``RawDateOrNone`` additionally mean the resolved ``raw``
epoch-seconds value is a calendar date (statement ``endDate``s and
similar), per the epoch-typing tiers in ``AGENTS.md``: it converts
straight to :class:`datetime.date`.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Annotated, TypeVar, cast

import pydantic
from pydantic import BaseModel, BeforeValidator, ConfigDict
from pydantic.alias_generators import to_camel

from yoghurt.exceptions import YahooApiError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

_WRAPPER_KEYS = frozenset({"raw", "fmt", "longFmt"})


def _unwrap_raw(value: object) -> object:
    """Resolve a bare scalar or a ``{raw, fmt, longFmt}`` wrapper to ``raw``.

    Returns:
        object: ``value`` unchanged when it isn't a mapping; ``None`` for
        an empty mapping ``{}`` (Yahoo's spelling for an absent wrapped
        value, per the module docstring); otherwise the wrapper's
        ``"raw"`` entry.

    Raises:
        ValueError: If ``value`` is a non-empty mapping with a key outside
            ``{"raw", "fmt", "longFmt"}``, or a non-empty mapping with no
            ``"raw"`` key at all.
    """

    if not isinstance(value, dict):
        return value

    mapping = cast("dict[str, Any]", value)
    if not mapping:
        return None
    unknown_keys = set(mapping) - _WRAPPER_KEYS
    if unknown_keys:
        message = f"unexpected keys in raw/fmt wrapper: {sorted(unknown_keys)}"
        raise ValueError(message)
    if "raw" not in mapping:
        message = f"raw/fmt wrapper missing 'raw' key: {mapping!r}"
        raise ValueError(message)
    return mapping["raw"]


RawFloat = Annotated[float, BeforeValidator(_unwrap_raw)]
"""A ``float`` that also accepts a ``{raw, fmt, longFmt}`` wrapper.

Never observed as ``{}`` in the corpus for the fields that use this
variant; use :data:`RawFloatOrNone` instead where ``{}`` has been
observed. See the module docstring for the unwrap rule.
"""

RawInt = Annotated[int, BeforeValidator(_unwrap_raw)]
"""An ``int`` that also accepts a ``{raw, fmt, longFmt}`` wrapper.

Never observed as ``{}`` in the corpus for the fields that use this
variant; use :data:`RawIntOrNone` instead where ``{}`` has been observed.
See the module docstring for the unwrap rule.
"""

RawDate = Annotated[datetime.date, BeforeValidator(_unwrap_raw)]
"""A ``datetime.date`` that also accepts a ``{raw, fmt, longFmt}`` wrapper.

The unwrapped ``raw`` value is epoch-seconds with calendar-date meaning
(for example, a financial statement's ``endDate``); pydantic converts it
to a UTC :class:`datetime.date` after unwrapping. Never observed as
``{}`` in the corpus for the fields that use this variant; use
:data:`RawDateOrNone` instead where ``{}`` has been observed. See the
module docstring for the unwrap rule.
"""

RawFloatOrNone = Annotated[float | None, BeforeValidator(_unwrap_raw)]
"""A nullable ``float`` that also accepts a ``{raw, fmt, longFmt}``
wrapper or an empty-mapping ``{}`` (both resolve to ``None``).

Required (no default) where the wire key is universal but its value can
resolve to ``None``; add `` = None`` at the field site where the key
itself is only sometimes present. See the module docstring for why this
must be used (instead of plain ``RawFloat | None``) whenever ``{}`` has
been observed for a field.
"""

RawIntOrNone = Annotated[int | None, BeforeValidator(_unwrap_raw)]
"""A nullable ``int`` that also accepts a ``{raw, fmt, longFmt}`` wrapper
or an empty-mapping ``{}`` (both resolve to ``None``).

See :data:`RawFloatOrNone` for the requiredness convention and the module
docstring for why this must be used (instead of plain ``RawInt | None``)
whenever ``{}`` has been observed for a field.
"""

RawDateOrNone = Annotated[datetime.date | None, BeforeValidator(_unwrap_raw)]
"""A nullable ``datetime.date`` that also accepts a ``{raw, fmt,
longFmt}`` wrapper or an empty-mapping ``{}`` (both resolve to ``None``).

See :data:`RawFloatOrNone` for the requiredness convention and the module
docstring for why this must be used (instead of plain ``RawDate | None``)
whenever ``{}`` has been observed for a field.
"""


class YahooModel(BaseModel):
    """Base for typed Yahoo response models.

    Conventions (the template for every model in yoghurt):

    - ``frozen=True``: response models are immutable records.
    - ``alias_generator=to_camel`` + ``populate_by_name=True``: fields are
      snake_case in Python, camelCase on the wire; irregular Yahoo spellings
      (``forwardPE``, ``...URL``) get explicit ``Field(alias=...)`` overrides.
    - ``extra="allow"``: unknown fields are preserved on ``model_extra``,
      never dropped — and the corpus coverage gate asserts ``model_extra``
      is EMPTY for every corpus capture, so any Yahoo drift fails loudly.
    - ``str_strip_whitespace=True``: Yahoo pads some string fields. This is
      a quote-informed default carried into the shared base — future
      endpoint families must confirm, not assume, that it holds.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="allow",
        str_strip_whitespace=True,
    )


_M = TypeVar("_M", bound=YahooModel)


def validate_model(model_cls: type[_M], payload: Mapping[str, Any]) -> _M:
    """Validate a Yahoo payload into a model, folding failures into the error contract.

    Returns:
        _M: The validated model instance.

    Raises:
        YahooApiError: If the payload does not satisfy the model (code
            ``"model-validation"``).
    """

    try:
        return model_cls.model_validate(payload)
    except pydantic.ValidationError as exc:
        message = f"{model_cls.__name__}: {exc}"
        raise YahooApiError(code="model-validation", description=message) from exc
