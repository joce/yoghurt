"""Shared fixtures and helpers for the yoghurt test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from yoghurt.models import YahooModel

_CORPUS_QUOTE_DIR = Path(__file__).resolve().parent / "fixtures" / "corpus" / "quote"


def collect_nested_extras(model: YahooModel) -> dict[str, dict[str, object]]:
    """Collect every non-empty ``model_extra`` in a validated model tree.

    Walks the model's own ``model_extra`` plus, recursively, every field
    value that is a :class:`YahooModel`, a list/tuple of YahooModels, or a
    dict with YahooModel values (the ``ChartEvents.dividends``/``.splits``
    shape: ``dict[str, ChartDividend | ChartSplit]``). This is the corpus
    drift alarm's eyes below top level: a nested sub-model quietly growing
    unknown keys must fail the coverage gate just as loudly as the root
    model would, whether that sub-model sits in a list or under a dict key.

    Returns:
        dict[str, dict[str, object]]: Dotted path -> that model's extra
        fields, for every model in the tree whose ``model_extra`` is
        non-empty. The root model's path is ``""``; nested paths look
        like ``corporate_actions[0]`` for list items or
        ``dividends['1755783000']`` for dict values.
    """

    found: dict[str, dict[str, object]] = {}

    def _walk(node: YahooModel, path: str) -> None:
        extra = node.model_extra
        if extra:
            found[path] = dict(extra)
        for name in type(node).model_fields:
            value: object = getattr(node, name)
            prefix = f"{path}.{name}" if path else name
            if isinstance(value, YahooModel):
                _walk(value, prefix)
            else:
                for suffix, item in _child_models(value):
                    _walk(item, f"{prefix}{suffix}")

    _walk(model, "")
    return found


def _child_models(value: object) -> list[tuple[str, YahooModel]]:
    """Return ``(path_suffix, model)`` for each YahooModel nested in ``value``.

    Handles the two collection shapes response models use for nested
    sub-models: list/tuple (``corporate_actions``-style) and dict with
    model values (``ChartEvents.dividends``/``.splits``-style).

    Returns:
        list[tuple[str, YahooModel]]: Empty for scalars and collections with
        no model members.
    """

    if isinstance(value, (list, tuple)):
        items = cast("tuple[object, ...]", value)
        return [
            (f"[{index}]", item)
            for index, item in enumerate(items)
            if isinstance(item, YahooModel)
        ]
    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)
        return [
            (f"[{key!r}]", item)
            for key, item in mapping.items()
            if isinstance(item, YahooModel)
        ]
    return []


class _DictHolder(YahooModel):
    """Minimal fixture model with a ``dict[str, YahooModel]`` field.

    Mirrors the shape of :class:`~yoghurt.models.chart.ChartEvents`
    (``dividends``/``splits``), used to prove the nested-extras walker
    traverses dict-valued fields, not just lists/tuples of models.
    """

    items: dict[str, YahooModel] | None = None


def test_nested_extras_walker_traverses_dict_valued_fields() -> None:
    """The walker reports extras inside a dict[str, YahooModel] field's values.

    ``ChartEvents.dividends``/``.splits`` are keyed dict collections, not
    lists, so the walker must handle dict values explicitly (a plain
    list/tuple check would miss them entirely and silently pass drifted
    dict-valued sub-models).
    """

    holder = _DictHolder.model_validate(
        {"items": {"1755783000": {"amount": 0.83, "surpriseField": "new"}}}
    )

    nested = collect_nested_extras(holder)

    assert "items['1755783000']" in nested
    assert nested["items['1755783000']"] == {
        "amount": 0.83,
        "surpriseField": "new",
    }


@pytest.fixture(scope="session")
def quote_corpus_records() -> list[dict[str, object]]:
    """Every quoteResponse.result record across the whole quote corpus.

    The flat record list is the evidence base for quote-model tests: enum
    coverage, field applicability, and (from Part 3b on) model validation
    against real captures all iterate these records.

    Returns:
        list[dict[str, object]]: All records from every quote corpus file,
        in file-then-list order.
    """

    records: list[dict[str, object]] = []
    for path in sorted(_CORPUS_QUOTE_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.extend(payload.get("quoteResponse", {}).get("result", []))
    return records
