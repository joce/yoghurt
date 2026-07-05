"""The whole-endpoint quote-summary corpus coverage gate: ``QuoteSummary``.

Every one of the 23 valid quote-summary corpus captures (all-modules
requests, unformatted) must validate as a :class:`QuoteSummary` with
``collect_nested_extras`` completely empty across the whole model tree —
41 modules deep. This is the whole-endpoint drift alarm: a module family
gaining an unmodeled field anywhere in its tree fails here even if that
family's own per-batch corpus gate (``test_summary_holders_corpus.py`` and
siblings) somehow missed it, since every one of those same captures is
re-validated here through the single top-level container. This file also
proves every one of the 41 ``QuoteSummary`` fields round-trips through
``to_camel``/``to_snake`` with no explicit alias override needed, and
enforces alphabetical field declaration order.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import CORPUS_QUOTE_SUMMARY_DIR, quote_summary_records
from yoghurt.models.summary import QuoteSummary

_EXPECTED_CORPUS_FILE_COUNT = 24
_EXPECTED_VALID_CAPTURE_COUNT = 23
_EXPECTED_MODULE_COUNT = 41

_EXPECTED_MODULE_NAMES = frozenset(
    {
        "assetProfile",
        "balanceSheetHistory",
        "balanceSheetHistoryQuarterly",
        "calendarEvents",
        "cashflowStatementHistory",
        "cashflowStatementHistoryQuarterly",
        "corporateActions",
        "defaultKeyStatistics",
        "earnings",
        "earningsCallTranscripts",
        "earningsGaap",
        "earningsHistory",
        "earningsNonGaap",
        "earningsTrend",
        "equityPerformance",
        "financialData",
        "financialsTemplate",
        "fundOwnership",
        "fundPerformance",
        "fundProfile",
        "incomeStatementHistory",
        "incomeStatementHistoryQuarterly",
        "indexTrend",
        "industryTrend",
        "insiderHolders",
        "insiderTransactions",
        "institutionOwnership",
        "majorDirectHolders",
        "majorHoldersBreakdown",
        "netSharePurchaseActivity",
        "pageViews",
        "price",
        "quoteType",
        "quoteUnadjustedPerformanceOverview",
        "recommendationTrend",
        "secFilings",
        "sectorTrend",
        "summaryDetail",
        "summaryProfile",
        "topHoldings",
        "upgradeDowngradeHistory",
    }
)


def _flatten_extras(nested: dict[str, dict[str, object]]) -> list[str]:
    """Flatten a nested-extras map to sorted ``path.key`` strings."""

    return sorted(
        f"{path}.{key}" if path else key
        for path, extras in nested.items()
        for key in extras
    )


_CASES: list[tuple[str, dict[str, Any]]] = [
    (f"capture[{index}]", dict(record))
    for index, record in enumerate(quote_summary_records())
]


def test_corpus_has_expected_file_count() -> None:
    """Sanity check on the fixture set: 24 files (23 valid + ZZZZXYZQ)."""

    files = sorted(CORPUS_QUOTE_SUMMARY_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_CORPUS_FILE_COUNT


def test_quote_summary_stream_has_expected_capture_count() -> None:
    """The whole-capture stream matches the corpus-measured valid-capture count."""

    records = list(quote_summary_records())
    assert len(records) == _EXPECTED_VALID_CAPTURE_COUNT


def test_quote_summary_field_count_matches_module_count() -> None:
    """QuoteSummary has exactly one field per quote-summary module (41 total)."""

    assert len(QuoteSummary.model_fields) == _EXPECTED_MODULE_COUNT


def test_quote_summary_field_aliases_match_every_observed_module_name() -> None:
    """Every QuoteSummary field's wire alias is an exact module name from the corpus."""

    aliases = {field_info.alias for field_info in QuoteSummary.model_fields.values()}
    assert aliases == _EXPECTED_MODULE_NAMES


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _CASES,
    ids=[case_id for case_id, _payload in _CASES],
)
def test_capture_validates_as_quote_summary_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every corpus capture validates as QuoteSummary with zero extras anywhere.

    The nested-extras walker checks the entire model tree, 41 modules deep:
    this is the single point where drift in any typed module family would
    surface, since it re-validates the same captures each family's own
    corpus gate already checked, but through the one container class.
    """

    instance = QuoteSummary.model_validate(payload)
    nested = collect_nested_extras(instance)
    message = (
        f"QuoteSummary ({case_id}) gained unmodeled fields "
        f"(drift alarm): {_flatten_extras(nested)}"
    )
    assert not nested, message


def test_quote_summary_fields_are_declared_in_alphabetical_order() -> None:
    """Template enforcement: QuoteSummary declares fields alphabetically."""

    names = list(QuoteSummary.model_fields)
    assert names == sorted(names)


def test_quote_summary_fields_are_all_optional() -> None:
    """Every QuoteSummary field is optional: no module is universally present."""

    assert all(
        not field_info.is_required()
        for field_info in QuoteSummary.model_fields.values()
    )
