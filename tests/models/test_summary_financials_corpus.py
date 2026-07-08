"""The batch c2 quote-summary corpus coverage gate: financial-snapshot modules.

Every quote-summary capture's payload for each of the four financial-snapshot
batch c2 modules (``financialData``, ``defaultKeyStatistics``,
``calendarEvents``, ``financialsTemplate``) must validate against its model
with nothing landing on ``model_extra`` anywhere in the model tree — the
same drift alarm the earlier corpus gates enforce. This file also pins each
module's required-field set to its corpus-measured universal keys (via
``tools.fields_report.quote_summary_module_records``) and enforces
alphabetical field declaration order for every model added in
``yoghurt.models.summary_financials``. See
``tests/models/test_summary_earnings_corpus.py`` for the remaining six
batch c2 (earnings-family) modules.

Live divergence (2026-07-07, see the module docstring in
``yoghurt.models.summary_financials``): ``financialData.returnOnAssets``/
``.returnOnEquity`` (absent on LHX/SPCX/YSS) and
``calendarEvents.earnings.isEarningsDateEstimate`` (absent on SPCX) are
corpus-universal but loosened to Optional on live evidence; the exact
difference is pinned here so a future corpus refresh cannot silently
reintroduce the required-ness. A second 2026-07-07 sweep (mining/materials
universe) added ``financialData.operatingCashflow`` (TECK, U-UN.TO),
``.totalCash``/``.totalCashPerShare``/``.totalDebt`` (U-UN.TO), and the
nested ``calendarEvents.earnings.revenueAverage``/``.revenueLow``/
``.revenueHigh`` (WDO.TO, OR, NGEX.TO, NXE, DNN, U-UN.TO) to the loosened
set; ``financialData.financialCurrency`` stays required but became
nullable (present-but-null on U-UN.TO).
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
from yoghurt.models.summary_financials import (
    CalendarEvents,
    DefaultKeyStatistics,
    Earnings,
    FinancialData,
    FinancialsTemplate,
)

if TYPE_CHECKING:
    from yoghurt.models._base import YahooModel

_EXPECTED_CORPUS_FILE_COUNT = 24

_MODULE_MODELS: dict[str, type[YahooModel]] = {
    "financialData": FinancialData,
    "defaultKeyStatistics": DefaultKeyStatistics,
    "calendarEvents": CalendarEvents,
    "financialsTemplate": FinancialsTemplate,
}

_EXPECTED_RECORD_COUNTS: dict[str, int] = {
    "financialData": 9,
    "defaultKeyStatistics": 18,
    "calendarEvents": 9,
    "financialsTemplate": 9,
}

_EXPECTED_UNIVERSAL_KEY_COUNTS: dict[str, int] = {
    "financialData": 14,
    "defaultKeyStatistics": 8,
    "calendarEvents": 2,
    "financialsTemplate": 2,
}

# Corpus-universal keys loosened to Optional on live evidence (2026-07-07;
# see the field docstrings). Pinned exactly: a corpus refresh that starts
# backing the loosening shrinks the universal set and must prune this map.
_LIVE_LOOSENED_UNIVERSAL_KEYS: dict[str, set[str]] = {
    "financialData": {
        "operatingCashflow",
        "returnOnAssets",
        "returnOnEquity",
        "totalCash",
        "totalCashPerShare",
        "totalDebt",
    },
    "defaultKeyStatistics": set(),
    "calendarEvents": set(),
    "financialsTemplate": set(),
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

    The nested-extras walker checks the whole model tree: ``calendarEvents``'s
    nested ``Earnings`` block must stay extras-free too, not just the
    top-level module model.
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
    """Each module's required fields are its corpus-measured universal keys.

    A required field is one whose ``FieldInfo.is_required()`` is True; its
    wire key is its alias (or its name, for the handful with no override).
    This must equal the set of wire keys present on every capture of that
    module — including keys that are always present but sometimes null
    (required-but-nullable fields typed ``T | None`` with no default) —
    minus exactly the live-evidence loosened keys pinned in
    ``_LIVE_LOOSENED_UNIVERSAL_KEYS``: not a superset, not any other subset.
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

    loosened = _LIVE_LOOSENED_UNIVERSAL_KEYS[module]
    assert len(universal_keys) == _EXPECTED_UNIVERSAL_KEY_COUNTS[module]
    assert loosened <= universal_keys
    assert required_aliases == universal_keys - loosened
    if loosened:
        assert required_aliases < universal_keys


def test_earnings_required_field_set_is_a_subset_of_nested_universal_keys() -> None:
    """The nested Earnings block's required fields: universal keys minus four.

    ``calendarEvents.earnings`` is nested, so the module-level gate above
    never sees its keys; this pins the same invariant one level down.
    ``isEarningsDateEstimate`` is present on every corpus capture's
    ``earnings`` block, but a 2026-07-07 live pull observed it absent on a
    newly listed EQUITY whose ``earningsDate`` is an empty list (SPCX);
    ``revenueAverage``/``revenueLow``/``revenueHigh`` are likewise
    corpus-universal but absent (always together) on low-analyst-coverage
    2026-07-07 live pulls (WDO.TO, OR, NGEX.TO, NXE, DNN, U-UN.TO). All
    four loosened to Optional, with the difference pinned here exactly.
    """

    earnings_records = [
        dict(record["earnings"])
        for record in quote_summary_module_records("calendarEvents")
    ]
    assert earnings_records, "expected calendarEvents captures with earnings blocks"
    report = collect_presence(earnings_records, kind_of=lambda _record: "EQUITY")
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in Earnings.model_fields.items()
        if field_info.is_required()
    }

    assert required_aliases < universal_keys
    assert universal_keys - required_aliases == {
        "isEarningsDateEstimate",
        "revenueAverage",
        "revenueHigh",
        "revenueLow",
    }


def test_financial_data_validates_without_return_metrics() -> None:
    """Live-shape regression (LHX/SPCX/YSS, 2026-07-07).

    Replays the observed divergence on a corpus capture: Yahoo omitting
    ``returnOnAssets``/``returnOnEquity`` (always together) must validate,
    with both fields None.
    """

    record = dict(next(iter(quote_summary_module_records("financialData"))))
    del record["returnOnAssets"]
    del record["returnOnEquity"]

    financial_data = FinancialData.model_validate(record)

    assert financial_data.return_on_assets is None
    assert financial_data.return_on_equity is None


def test_calendar_events_validates_without_is_earnings_date_estimate() -> None:
    """Live-shape regression (SPCX, 2026-07-07).

    Replays the observed divergence on a corpus capture: a nested
    ``earnings`` block missing ``isEarningsDateEstimate`` (as Yahoo sends
    for a newly listed symbol with no scheduled earnings date) must
    validate, with the field None.
    """

    record = dict(next(iter(quote_summary_module_records("calendarEvents"))))
    earnings = dict(record["earnings"])
    del earnings["isEarningsDateEstimate"]
    record["earnings"] = earnings

    calendar_events = CalendarEvents.model_validate(record)

    assert calendar_events.earnings.is_earnings_date_estimate is None


def test_financial_data_validates_without_operating_cashflow() -> None:
    """Live-shape regression (TECK, 2026-07-07).

    Replays the observed divergence on a corpus capture: Yahoo omitting
    ``operatingCashflow`` alone must validate, with the field None.
    """

    record = dict(next(iter(quote_summary_module_records("financialData"))))
    del record["operatingCashflow"]

    financial_data = FinancialData.model_validate(record)

    assert financial_data.operating_cashflow is None


def test_financial_data_validates_fund_like_sparse_payload() -> None:
    """Live-shape regression (U-UN.TO, 2026-07-07).

    Replays the sparsest observed ``financialData`` shape — a physical
    commodity trust: ``operatingCashflow``/``totalCash``/
    ``totalCashPerShare``/``totalDebt`` all absent and
    ``financialCurrency`` present but null — which must validate with the
    absent fields None and the nullable field None.
    """

    record = dict(next(iter(quote_summary_module_records("financialData"))))
    del record["operatingCashflow"]
    del record["totalCash"]
    del record["totalCashPerShare"]
    del record["totalDebt"]
    record["financialCurrency"] = None

    financial_data = FinancialData.model_validate(record)

    assert financial_data.operating_cashflow is None
    assert financial_data.total_cash is None
    assert financial_data.total_cash_per_share is None
    assert financial_data.total_debt is None
    assert financial_data.financial_currency is None


def test_earnings_validates_without_revenue_estimates() -> None:
    """Live-shape regression (WDO.TO/OR/NGEX.TO/NXE/DNN/U-UN.TO, 2026-07-07).

    Replays the observed divergence on a corpus capture: a nested
    ``earnings`` block missing ``revenueAverage``/``revenueLow``/
    ``revenueHigh`` (as Yahoo sends for low-analyst-coverage symbols) must
    validate, with all three fields None.
    """

    record = dict(next(iter(quote_summary_module_records("calendarEvents"))))
    earnings = dict(record["earnings"])
    del earnings["revenueAverage"]
    del earnings["revenueHigh"]
    del earnings["revenueLow"]
    record["earnings"] = earnings

    calendar_events = CalendarEvents.model_validate(record)

    assert calendar_events.earnings.revenue_average is None
    assert calendar_events.earnings.revenue_high is None
    assert calendar_events.earnings.revenue_low is None


@pytest.mark.parametrize(
    "model_cls",
    [
        Earnings,
        CalendarEvents,
        FinancialsTemplate,
        FinancialData,
        DefaultKeyStatistics,
    ],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[YahooModel],
) -> None:
    """Template enforcement: every model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
