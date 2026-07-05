"""The batch c4 quote-summary corpus coverage gate: fund-internals modules.

Every quote-summary capture's payload for each of the three fund-internals
batch c4 modules (``fundProfile``, ``fundPerformance``, ``topHoldings``)
must validate against its model with nothing landing on ``model_extra``
anywhere in the model tree — the same drift alarm the earlier corpus gates
enforce. This file also pins each module's required-field set to its
corpus-measured universal keys (via
``tools.fields_report.quote_summary_module_records``) and enforces
alphabetical field declaration order for every model added in
``yoghurt.models.summary_funds``. See
``tests/models/test_summary_holders_corpus.py`` for the remaining seven
batch c4 (holder/ownership) modules.

Unlike every earlier corpus gate, this file's evidence base is only 4
captures (``QQQ``, ``SPY``, ``VT``, ``VTSAX`` — see the model module's
docstring for the thin-evidence caveat this implies), and several nested
blocks are genuinely dynamic-keyed bags (``dict[str, float]``) rather than
fixed-field models, so this file does not attempt a row-level
required-field gate the way the statement/holder corpus gates do — a
``dict[str, float]`` has no ``model_fields`` to check requiredness against.
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
from yoghurt.models.summary_funds import (
    AnnualReturn,
    AnnualTotalReturns,
    FundFees,
    FundFeesCat,
    FundManagementInfo,
    FundPerformance,
    FundPerformanceOverview,
    FundPerformanceOverviewCat,
    FundProfile,
    Holding,
    LoadAdjustedReturns,
    PastQuarterlyReturns,
    QuarterlyReturn,
    RankInCategory,
    RiskOverviewStatistics,
    RiskOverviewStatisticsCat,
    RiskStatisticsCatEntry,
    RiskStatisticsEntry,
    TopHoldings,
    TrailingReturns,
    TrailingReturnsCat,
    TrailingReturnsNav,
)

if TYPE_CHECKING:
    from yoghurt.models._base import YahooModel

_EXPECTED_CORPUS_FILE_COUNT = 24

_MODULE_MODELS: dict[str, type[YahooModel]] = {
    "fundProfile": FundProfile,
    "fundPerformance": FundPerformance,
    "topHoldings": TopHoldings,
}

_EXPECTED_RECORD_COUNTS: dict[str, int] = {
    "fundProfile": 4,
    "fundPerformance": 4,
    "topHoldings": 4,
}

_EXPECTED_REQUIRED_FIELD_COUNTS: dict[str, int] = {
    "fundProfile": 9,
    "fundPerformance": 11,
    "topHoldings": 12,
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
    """Each module's record stream matches its corpus-measured capture count.

    Only 4 captures total (3 ETF, 1 MUTUALFUND); see the module docstring
    for the thin-evidence caveat this implies.
    """

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

    The nested-extras walker checks the whole model tree: nested blocks
    like ``FundFees``, ``FundPerformanceOverview``, and ``Holding`` must
    all stay extras-free too, not just the top-level module model. Dynamic
    ``dict[str, float]`` bags (``projectionValues``, ``equityHoldings``,
    ``bondRatings``, and so on) accept whatever keys a given capture sends
    without needing a model of their own, so they cannot gain "extras" in
    the ``model_extra`` sense this walker checks.
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


def test_fund_profile_fee_blocks_diverge_by_quote_type() -> None:
    """fundProfile.feesExpensesInvestment shape genuinely differs ETF vs MUTUALFUND.

    Documents the corpus-wide divergence noted in the module docstring:
    ETF captures carry annualHoldingsTurnover/totalNetAssets; the sole
    MUTUALFUND capture instead carries netExpRatio/grossExpRatio.
    """

    etf_seen = False
    mutualfund_seen = False
    for record in quote_summary_module_records("fundProfile"):
        fees = record["feesExpensesInvestment"]
        if record.kind == "ETF":
            assert "annualHoldingsTurnover" in fees
            assert "netExpRatio" not in fees
            etf_seen = True
        elif record.kind == "MUTUALFUND":
            assert "netExpRatio" in fees
            assert "annualHoldingsTurnover" not in fees
            mutualfund_seen = True
    assert etf_seen
    assert mutualfund_seen


_ETF_EQUITY_HOLDINGS_KEY_COUNT = 4
_MUTUALFUND_EQUITY_HOLDINGS_KEY_COUNT = 12


def test_top_holdings_equity_holdings_diverges_by_quote_type() -> None:
    """topHoldings.equityHoldings has 4 keys on ETF, 12 on the MUTUALFUND capture."""

    for record in quote_summary_module_records("topHoldings"):
        equity_holdings = record["equityHoldings"]
        if record.kind == "ETF":
            assert len(equity_holdings) == _ETF_EQUITY_HOLDINGS_KEY_COUNT
        elif record.kind == "MUTUALFUND":
            assert len(equity_holdings) == _MUTUALFUND_EQUITY_HOLDINGS_KEY_COUNT


def test_top_holdings_bond_ratings_and_sector_weightings_are_dynamic_dicts() -> None:
    """bondRatings/sectorWeightings entries are single-key dicts with varying keys."""

    for record in quote_summary_module_records("topHoldings"):
        for entry in record["bondRatings"]:
            assert len(entry) == 1
        for entry in record["sectorWeightings"]:
            assert len(entry) == 1


@pytest.mark.parametrize(
    "model_cls",
    [
        FundManagementInfo,
        FundFees,
        FundFeesCat,
        FundProfile,
        FundPerformanceOverview,
        FundPerformanceOverviewCat,
        TrailingReturns,
        TrailingReturnsCat,
        TrailingReturnsNav,
        RiskStatisticsEntry,
        RiskStatisticsCatEntry,
        RiskOverviewStatistics,
        RiskOverviewStatisticsCat,
        AnnualReturn,
        AnnualTotalReturns,
        QuarterlyReturn,
        PastQuarterlyReturns,
        LoadAdjustedReturns,
        RankInCategory,
        FundPerformance,
        Holding,
        TopHoldings,
    ],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[YahooModel],
) -> None:
    """Template enforcement: every model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
