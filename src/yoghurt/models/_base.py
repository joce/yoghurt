"""Shared configuration for all Yahoo response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


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
