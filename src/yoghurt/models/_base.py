"""Shared configuration for all Yahoo response models.

Also home to the ``Raw*`` wrapper-tolerant value types (:data:`RawFloat`,
:data:`RawInt`, :data:`RawDate`): some nested Yahoo rows (never top-level
quote-summary module fields) wrap a value as ``{"raw": ..., "fmt": ...,
"longFmt": ...}`` instead of sending the bare scalar directly, for example
``assetProfile.companyOfficers[].totalPay``. The ``Raw*`` types accept
either shape and always resolve to the bare ``raw`` value:

- A bare scalar passes through unchanged.
- A mapping is accepted only when its keys are a subset of ``{"raw",
  "fmt", "longFmt"}``; ``fmt``/``longFmt`` are presentation strings and
  are discarded. Any other key in the mapping fails validation, so wrapper
  drift (an unexpected new key inside the wrapper) surfaces loudly instead
  of silently passing through.
- An empty mapping ``{}`` is *not* special-cased: it has never been
  observed in the corpus (verified across every quote-summary capture as
  of the 2026-07-04 corpus), so it is rejected the same as any other
  mapping whose keys don't resolve a ``raw`` value. If Yahoo is ever
  observed sending ``{}`` for an absent wrapped value, this validator
  should map it to ``None`` and the field made optional at that point —
  not before.

``RawDate`` additionally means the resolved ``raw`` epoch-seconds value is
a calendar date (statement ``endDate``s and similar), per the epoch-typing
tiers in ``AGENTS.md``: it converts straight to :class:`datetime.date`.
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
        object: ``value`` unchanged when it isn't a mapping; otherwise the
        wrapper's ``"raw"`` entry.

    Raises:
        ValueError: If ``value`` is a mapping with a key outside
            ``{"raw", "fmt", "longFmt"}``, or a mapping with no ``"raw"``
            key at all (including ``{}``) — see the module docstring for
            why ``{}`` is not special-cased.
    """

    if not isinstance(value, dict):
        return value

    mapping = cast("dict[str, Any]", value)
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

See the module docstring for the unwrap rule.
"""

RawInt = Annotated[int, BeforeValidator(_unwrap_raw)]
"""An ``int`` that also accepts a ``{raw, fmt, longFmt}`` wrapper.

See the module docstring for the unwrap rule.
"""

RawDate = Annotated[datetime.date, BeforeValidator(_unwrap_raw)]
"""A ``datetime.date`` that also accepts a ``{raw, fmt, longFmt}`` wrapper.

The unwrapped ``raw`` value is epoch-seconds with calendar-date meaning
(for example, a financial statement's ``endDate``); pydantic converts it
to a UTC :class:`datetime.date` after unwrapping. See the module
docstring for the unwrap rule.
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
