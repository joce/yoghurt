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
    value that is a :class:`YahooModel` or a list/tuple of YahooModels.
    This is the corpus drift alarm's eyes below top level: a nested
    sub-model quietly growing unknown keys must fail the coverage gate
    just as loudly as the root model would.

    Returns:
        dict[str, dict[str, object]]: Dotted path -> that model's extra
        fields, for every model in the tree whose ``model_extra`` is
        non-empty. The root model's path is ``""``; nested paths look
        like ``corporate_actions[0]``.
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
            elif isinstance(value, (list, tuple)):
                items = cast("tuple[object, ...]", value)
                for index, item in enumerate(items):
                    if isinstance(item, YahooModel):
                        _walk(item, f"{prefix}[{index}]")

    _walk(model, "")
    return found


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
