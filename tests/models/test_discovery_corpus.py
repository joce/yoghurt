"""Corpus gates for search and lookup models."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import (
    CORPUS_LOOKUP_DIR,
    CORPUS_SEARCH_DIR,
    collect_presence,
    lookup_document_records,
    search_records,
)
from yoghurt.models.discovery import (
    LookupDocument,
    LookupResult,
    LookupTotals,
    SearchList,
    SearchNavigation,
    SearchNews,
    SearchQuote,
    SearchResearchReport,
    SearchResult,
    SearchThumbnail,
    SearchThumbnailResolution,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path
    from typing import Any

    from yoghurt.models._base import YahooModel

_EXPECTED_SEARCH_FILE_COUNT = 6
_EXPECTED_LOOKUP_FILE_COUNT = 11
_EXPECTED_SEARCH_ROW_COUNTS = {
    "lists": 6,
    "nav": 3,
    "news": 22,
    "quotes": 29,
    "researchReports": 6,
}
_EXPECTED_LOOKUP_DOCUMENT_COUNT = 45
_EXPECTED_SEARCH_RESULT_REQUIRED_FIELD_COUNT = 19
_EXPECTED_LOOKUP_DOCUMENT_REQUIRED_FIELD_COUNT = 4
_EXPECTED_LOOKUP_RESULT_REQUIRED_FIELD_COUNT = 5
_EXPECTED_LOOKUP_TOTALS_REQUIRED_FIELD_COUNT = 9


def _load_json(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _required_aliases(model_cls: type[YahooModel]) -> set[str]:
    return {
        field.alias or name
        for name, field in model_cls.model_fields.items()
        if field.is_required()
    }


def _universal_keys(records: Iterable[Mapping[str, Any]]) -> set[str]:
    report = collect_presence(records, kind_of=lambda _record: "all")
    return {key for key, field in report.fields.items() if field.universal}


def _search_payloads() -> list[dict[str, Any]]:
    return [_load_json(path) for path in sorted(CORPUS_SEARCH_DIR.glob("*.json"))]


def _lookup_results() -> list[dict[str, Any]]:
    return [
        _load_json(path)["finance"]["result"][0]
        for path in sorted(CORPUS_LOOKUP_DIR.glob("*.json"))
    ]


def test_corpus_has_expected_file_counts() -> None:
    """The evidence set covers six search and eleven lookup variants."""

    assert len(list(CORPUS_SEARCH_DIR.glob("*.json"))) == _EXPECTED_SEARCH_FILE_COUNT
    assert len(list(CORPUS_LOOKUP_DIR.glob("*.json"))) == _EXPECTED_LOOKUP_FILE_COUNT


@pytest.mark.parametrize(
    ("category", "expected_count"),
    _EXPECTED_SEARCH_ROW_COUNTS.items(),
)
def test_search_category_has_expected_row_count(
    category: str, expected_count: int
) -> None:
    """Each modeled search result family keeps its captured evidence."""

    assert len(list(search_records(category))) == expected_count


def test_lookup_has_expected_document_count() -> None:
    """The lookup corpus spans 45 documents across all observed asset types."""

    assert len(list(lookup_document_records())) == _EXPECTED_LOOKUP_DOCUMENT_COUNT


@pytest.mark.parametrize("payload", _search_payloads())
def test_search_corpus_validates_without_extras(payload: dict[str, Any]) -> None:
    """Every full search response validates with no unmodeled nested fields."""

    assert not collect_nested_extras(SearchResult.model_validate(payload))


@pytest.mark.parametrize("payload", _lookup_results())
def test_lookup_corpus_validates_without_extras(payload: dict[str, Any]) -> None:
    """Every lookup result page validates with no unmodeled nested fields."""

    assert not collect_nested_extras(LookupResult.model_validate(payload))


@pytest.mark.parametrize(
    ("model_cls", "category", "expected_required_count"),
    [
        (SearchQuote, "quotes", 2),
        (SearchNews, "news", 7),
        (SearchNavigation, "nav", 0),
        (SearchList, "lists", 4),
        (SearchResearchReport, "researchReports", 4),
    ],
)
def test_search_row_required_fields_match_corpus(
    model_cls: type[YahooModel],
    category: str,
    expected_required_count: int,
) -> None:
    """Each search row model requires exactly its universal corpus keys."""

    universal_keys = _universal_keys(search_records(category))
    assert len(universal_keys) == expected_required_count
    assert _required_aliases(model_cls) == universal_keys


def test_search_result_required_fields_match_corpus() -> None:
    """SearchResult requires exactly the top-level universal keys."""

    universal_keys = _universal_keys(_search_payloads())
    assert len(universal_keys) == _EXPECTED_SEARCH_RESULT_REQUIRED_FIELD_COUNT
    assert _required_aliases(SearchResult) == universal_keys


def test_lookup_document_required_fields_match_corpus() -> None:
    """LookupDocument requires exactly the document-universal keys."""

    universal_keys = _universal_keys(lookup_document_records())
    assert len(universal_keys) == _EXPECTED_LOOKUP_DOCUMENT_REQUIRED_FIELD_COUNT
    assert _required_aliases(LookupDocument) == universal_keys


def test_lookup_result_required_fields_match_corpus() -> None:
    """LookupResult requires exactly the result-page universal keys."""

    universal_keys = _universal_keys(_lookup_results())
    assert len(universal_keys) == _EXPECTED_LOOKUP_RESULT_REQUIRED_FIELD_COUNT
    assert _required_aliases(LookupResult) == universal_keys


def test_lookup_totals_required_fields_match_corpus() -> None:
    """LookupTotals requires exactly the lookupTotals universal keys."""

    totals = [result["lookupTotals"] for result in _lookup_results()]
    universal_keys = _universal_keys(totals)
    assert len(universal_keys) == _EXPECTED_LOOKUP_TOTALS_REQUIRED_FIELD_COUNT
    assert _required_aliases(LookupTotals) == universal_keys


_MODELS = (
    LookupDocument,
    LookupResult,
    LookupTotals,
    SearchList,
    SearchNavigation,
    SearchNews,
    SearchQuote,
    SearchResearchReport,
    SearchResult,
    SearchThumbnail,
    SearchThumbnailResolution,
)


@pytest.mark.parametrize("model_cls", _MODELS)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[YahooModel],
) -> None:
    """Every discovery model declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
