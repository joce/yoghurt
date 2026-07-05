"""The batch c3 quote-summary corpus coverage gate: statement-history modules.

Every quote-summary capture's payload for each of the six statement-history
batch c3 modules (``balanceSheetHistory``, ``balanceSheetHistoryQuarterly``,
``cashflowStatementHistory``, ``cashflowStatementHistoryQuarterly``,
``incomeStatementHistory``, ``incomeStatementHistoryQuarterly``) must
validate against its model with nothing landing on ``model_extra`` anywhere
in the model tree — the same drift alarm the earlier corpus gates enforce.
This file also pins each module's required-field set to its corpus-measured
universal keys (via ``tools.fields_report.quote_summary_module_records``),
proves both cadences of each statement type validate through the same
shared row model, and enforces alphabetical field declaration order for
every model added in ``yoghurt.models.summary_statements``. See
``tests/models/test_summary_trends_corpus.py`` for the remaining six batch
c3 (trend/filing) modules.
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
from yoghurt.models.summary_statements import (
    BalanceSheetHistory,
    BalanceSheetHistoryQuarterly,
    BalanceSheetStatement,
    CashflowStatement,
    CashflowStatementHistory,
    CashflowStatementHistoryQuarterly,
    IncomeStatement,
    IncomeStatementHistory,
    IncomeStatementHistoryQuarterly,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from yoghurt.models._base import YahooModel

_EXPECTED_CORPUS_FILE_COUNT = 24

_MODULE_MODELS: dict[str, type[YahooModel]] = {
    "balanceSheetHistory": BalanceSheetHistory,
    "balanceSheetHistoryQuarterly": BalanceSheetHistoryQuarterly,
    "cashflowStatementHistory": CashflowStatementHistory,
    "cashflowStatementHistoryQuarterly": CashflowStatementHistoryQuarterly,
    "incomeStatementHistory": IncomeStatementHistory,
    "incomeStatementHistoryQuarterly": IncomeStatementHistoryQuarterly,
}

_EXPECTED_RECORD_COUNTS: dict[str, int] = {
    "balanceSheetHistory": 9,
    "balanceSheetHistoryQuarterly": 9,
    "cashflowStatementHistory": 9,
    "cashflowStatementHistoryQuarterly": 9,
    "incomeStatementHistory": 9,
    "incomeStatementHistoryQuarterly": 9,
}

_EXPECTED_REQUIRED_FIELD_COUNTS: dict[str, int] = {
    "balanceSheetHistory": 2,
    "balanceSheetHistoryQuarterly": 2,
    "cashflowStatementHistory": 2,
    "cashflowStatementHistoryQuarterly": 2,
    "incomeStatementHistory": 2,
    "incomeStatementHistoryQuarterly": 2,
}

_ROW_LIST_KEYS: dict[str, str] = {
    "balanceSheetHistory": "balanceSheetStatements",
    "balanceSheetHistoryQuarterly": "balanceSheetStatements",
    "cashflowStatementHistory": "cashflowStatements",
    "cashflowStatementHistoryQuarterly": "cashflowStatements",
    "incomeStatementHistory": "incomeStatementHistory",
    "incomeStatementHistoryQuarterly": "incomeStatementHistory",
}

_EXPECTED_ROW_REQUIRED_FIELD_COUNTS: dict[str, int] = {
    "balanceSheetHistory": 2,
    "balanceSheetHistoryQuarterly": 2,
    "cashflowStatementHistory": 3,
    "cashflowStatementHistoryQuarterly": 3,
    "incomeStatementHistory": 24,
    "incomeStatementHistoryQuarterly": 24,
}

_ROW_MODELS: dict[str, type[YahooModel]] = {
    "balanceSheetHistory": BalanceSheetStatement,
    "balanceSheetHistoryQuarterly": BalanceSheetStatement,
    "cashflowStatementHistory": CashflowStatement,
    "cashflowStatementHistoryQuarterly": CashflowStatement,
    "incomeStatementHistory": IncomeStatement,
    "incomeStatementHistoryQuarterly": IncomeStatement,
}

_STATEMENT_TYPES: dict[str, tuple[str, str]] = {
    "balance sheet": ("balanceSheetHistory", "balanceSheetHistoryQuarterly"),
    "cashflow": ("cashflowStatementHistory", "cashflowStatementHistoryQuarterly"),
    "income": ("incomeStatementHistory", "incomeStatementHistoryQuarterly"),
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
    ``BalanceSheetStatement``, ``CashflowStatement``, and ``IncomeStatement``
    must all stay extras-free too, not just the top-level module model. This
    is also the gate that proves the fifteen universal-but-always-``{}``
    ``IncomeStatement`` fields (see the module docstring) unwrap cleanly on
    every corpus row without leaving stray extras behind.
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


@pytest.mark.parametrize("module", sorted(_ROW_MODELS))
def test_row_required_field_set_matches_corpus_universal_keys(module: str) -> None:
    """Each statement's shared row model's required fields match corpus-measured keys.

    Unlike the module-level check above, this walks every individual
    statement row (not the module wrapper) across every capture that
    carries this module, pooling both cadences' rows when the row model is
    shared (``BalanceSheetStatement``/``CashflowStatement``/
    ``IncomeStatement`` each back two modules).
    """

    row_model_cls = _ROW_MODELS[module]
    list_key = _ROW_LIST_KEYS[module]

    def _rows() -> Iterator[Mapping[str, Any]]:
        for record in quote_summary_module_records(module):
            yield from record[list_key]

    report = collect_presence(_rows(), kind_of=lambda _row: "row")
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in row_model_cls.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_ROW_REQUIRED_FIELD_COUNTS[module]
    assert required_aliases == universal_keys


@pytest.mark.parametrize(
    ("statement_type", "annual_module", "quarterly_module"),
    [
        (statement_type, annual, quarterly)
        for statement_type, (annual, quarterly) in _STATEMENT_TYPES.items()
    ],
    ids=list(_STATEMENT_TYPES),
)
def test_annual_and_quarterly_cadences_both_validate_through_shared_row_model(
    statement_type: str, annual_module: str, quarterly_module: str
) -> None:
    """Both cadences of each statement type validate through the same row model.

    Proves the plan's one-row-model-per-statement-type reuse: every annual
    row and every quarterly row for a given statement type validates
    against the identical shared model class (``BalanceSheetStatement``,
    ``CashflowStatement``, or ``IncomeStatement``), not two parallel
    almost-identical models.
    """

    row_model_cls = _ROW_MODELS[annual_module]
    assert _ROW_MODELS[quarterly_module] is row_model_cls

    annual_list_key = _ROW_LIST_KEYS[annual_module]
    quarterly_list_key = _ROW_LIST_KEYS[quarterly_module]

    annual_rows = [
        row
        for record in quote_summary_module_records(annual_module)
        for row in record[annual_list_key]
    ]
    quarterly_rows = [
        row
        for record in quote_summary_module_records(quarterly_module)
        for row in record[quarterly_list_key]
    ]

    assert annual_rows, f"no annual rows found for {statement_type}"
    assert quarterly_rows, f"no quarterly rows found for {statement_type}"

    for row in annual_rows:
        instance = row_model_cls.model_validate(row)
        assert not collect_nested_extras(instance)
    for row in quarterly_rows:
        instance = row_model_cls.model_validate(row)
        assert not collect_nested_extras(instance)


@pytest.mark.parametrize(
    "model_cls",
    [
        BalanceSheetStatement,
        BalanceSheetHistory,
        BalanceSheetHistoryQuarterly,
        CashflowStatement,
        CashflowStatementHistory,
        CashflowStatementHistoryQuarterly,
        IncomeStatement,
        IncomeStatementHistory,
        IncomeStatementHistoryQuarterly,
    ],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[YahooModel],
) -> None:
    """Template enforcement: every model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
