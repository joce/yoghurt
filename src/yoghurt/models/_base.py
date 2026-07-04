"""Shared configuration for all Yahoo response models."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import pydantic
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from yoghurt.exceptions import YahooApiError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any


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
