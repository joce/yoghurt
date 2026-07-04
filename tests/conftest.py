"""Shared fixtures for the yoghurt test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_CORPUS_QUOTE_DIR = Path(__file__).resolve().parent / "fixtures" / "corpus" / "quote"


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
