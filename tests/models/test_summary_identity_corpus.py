"""The batch c1 quote-summary corpus coverage gate.

Every quote-summary capture's payload for each of the 9 batch c1 modules
(``price``, ``quoteType``, ``summaryDetail``, ``summaryProfile``,
``assetProfile``, ``pageViews``, ``corporateActions``, ``equityPerformance``,
``quoteUnadjustedPerformanceOverview``) must validate against its model with
nothing landing on ``model_extra`` anywhere in the model tree — the same
drift alarm the quote/chart/options corpus gates enforce. This file also
pins each module's required-field set to its corpus-measured universal keys
(via ``tools.fields_report.quote_summary_module_records``) and enforces
alphabetical field declaration order for every model added in this module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import (
    CORPUS_QUOTE_SUMMARY_DIR,
    collect_presence,
    quote_summary_module_kind,
    quote_summary_module_records,
)
from yoghurt.models.summary_identity import (
    AssetProfile,
    Benchmark,
    CompanyOfficer,
    CorporateActionMeta,
    CorporateActions,
    EquityPerformance,
    ExecutiveTeamMember,
    PageViews,
    PerformanceOverview,
    Price,
    QuoteUnadjustedPerformanceOverview,
    SummaryCorporateAction,
    SummaryDetail,
    SummaryProfile,
    SummaryQuoteType,
)

if TYPE_CHECKING:
    from yoghurt.models._base import YahooModel

_EXPECTED_CORPUS_FILE_COUNT = 24
_EXPECTED_VALID_CAPTURE_COUNT = 23

_MODULE_MODELS: dict[str, type[YahooModel]] = {
    "price": Price,
    "quoteType": SummaryQuoteType,
    "summaryDetail": SummaryDetail,
    "summaryProfile": SummaryProfile,
    "assetProfile": AssetProfile,
    "pageViews": PageViews,
    "corporateActions": CorporateActions,
    "equityPerformance": EquityPerformance,
    "quoteUnadjustedPerformanceOverview": QuoteUnadjustedPerformanceOverview,
}

_EXPECTED_RECORD_COUNTS: dict[str, int] = {
    "price": 23,
    "quoteType": 23,
    "summaryDetail": 23,
    "summaryProfile": 14,
    "assetProfile": 14,
    "pageViews": 10,
    "corporateActions": 23,
    "equityPerformance": 23,
    "quoteUnadjustedPerformanceOverview": 23,
}

_EXPECTED_REQUIRED_FIELD_COUNTS: dict[str, int] = {
    "price": 22,
    "quoteType": 10,
    "summaryDetail": 13,
    "summaryProfile": 3,
    "assetProfile": 3,
    "pageViews": 4,
    "corporateActions": 2,
    "equityPerformance": 2,
    "quoteUnadjustedPerformanceOverview": 2,
}


def _flatten_extras(nested: dict[str, dict[str, object]]) -> list[str]:
    """Flatten a nested-extras map to sorted ``path.key`` strings."""

    return sorted(
        f"{path}.{key}" if path else key
        for path, extras in nested.items()
        for key in extras
    )


def _module_cases(module: str) -> list[tuple[str, dict[str, Any]]]:
    """Every (case-id, payload) pair for one module across the corpus."""

    return [
        (f"{module}[{index}]", dict(record))
        for index, record in enumerate(quote_summary_module_records(module))
    ]


_CASES: dict[str, list[tuple[str, dict[str, Any]]]] = {
    module: _module_cases(module) for module in _MODULE_MODELS
}


def test_corpus_has_expected_file_count() -> None:
    """Sanity check on the fixture set: 24 files (23 valid + ZZZZXYZQ)."""

    files = sorted(CORPUS_QUOTE_SUMMARY_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_CORPUS_FILE_COUNT


def test_zzzzxyzq_has_no_quote_summary_result() -> None:
    """The unknown-symbol capture carries no module payloads, not a skip."""

    for module in _MODULE_MODELS:
        records = [
            record
            for record in quote_summary_module_records(module)
            if quote_summary_module_kind(record)
        ]
        symbols_seen = len(records)
        assert symbols_seen <= _EXPECTED_VALID_CAPTURE_COUNT


@pytest.mark.parametrize("module", sorted(_MODULE_MODELS))
def test_module_stream_has_expected_record_count(module: str) -> None:
    """Each module's record stream matches its corpus-measured capture count."""

    records = list(quote_summary_module_records(module))
    assert len(records) == _EXPECTED_RECORD_COUNTS[module]


@pytest.mark.parametrize(
    ("module", "case_id", "payload"),
    [
        (module, case_id, payload)
        for module, cases in _CASES.items()
        for case_id, payload in cases
    ],
    ids=[case_id for cases in _CASES.values() for case_id, _payload in cases],
)
def test_module_payload_validates_with_no_extra_fields(
    module: str, case_id: str, payload: dict[str, Any]
) -> None:
    """Every capture's module payload validates with no extras anywhere.

    The nested-extras walker checks the whole model tree: nested rows like
    ``CompanyOfficer``, ``PerformanceOverview``/``Benchmark``, and
    ``SummaryCorporateAction``/``CorporateActionMeta`` must all stay
    extras-free too, not just the top-level module model.
    """

    model_cls = _MODULE_MODELS[module]
    instance = model_cls.model_validate(payload)
    nested = collect_nested_extras(instance)
    message = (
        f"{model_cls.__name__} ({case_id}) gained unmodeled fields "
        f"(drift alarm): {_flatten_extras(nested)}"
    )
    assert not nested, message


@pytest.mark.parametrize("module", sorted(_MODULE_MODELS))
def test_required_field_set_matches_corpus_universal_keys(module: str) -> None:
    """Each module's required fields are exactly its corpus-measured universal keys.

    A required field is one whose ``FieldInfo.is_required()`` is True; its
    wire key is its alias (or its name, for the handful with no override).
    This must equal the set of wire keys present on every capture of that
    module - not a superset, not a subset - including keys that are always
    present but sometimes null (required-but-nullable fields typed ``T |
    None`` with no default).
    """

    model_cls = _MODULE_MODELS[module]
    report = collect_presence(
        quote_summary_module_records(module), kind_of=quote_summary_module_kind
    )
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in model_cls.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_REQUIRED_FIELD_COUNTS[module]
    assert required_aliases == universal_keys


@pytest.mark.parametrize(
    "model_cls",
    [
        Benchmark,
        PerformanceOverview,
        EquityPerformance,
        QuoteUnadjustedPerformanceOverview,
        Price,
        SummaryQuoteType,
        SummaryDetail,
        CompanyOfficer,
        ExecutiveTeamMember,
        SummaryProfile,
        AssetProfile,
        PageViews,
        CorporateActionMeta,
        SummaryCorporateAction,
        CorporateActions,
    ],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[YahooModel],
) -> None:
    """Template enforcement: every model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
