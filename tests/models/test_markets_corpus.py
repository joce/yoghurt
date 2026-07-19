"""Batch 3e-1 corpus gate: trending/market-summary/market-info/market-time/sector.

Every relevant corpus capture must validate against its model with nothing
landing on ``model_extra`` anywhere in the model tree, and each model's
required-field set is pinned to its corpus-measured universal keys via
``tools.fields_report``.

``market-summary`` additionally documents the reuse-decision evidence for
:class:`~yoghurt.models.markets.MarketSummaryQuote`: see
``test_market_summary_rows_have_no_extras_against_quote`` and
``test_market_summary_required_quote_fields_are_not_all_universal`` for the
script-validated finding that :class:`~yoghurt.models.quote.Quote` cannot be
reused (zero extras, but 8 of its 34 required fields are not universal).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import (
    CORPUS_ROOT,
    collect_presence,
    market_info_kind,
    market_info_records,
    market_summary_records,
    market_time_records,
    trending_records,
)
from yoghurt.models.markets import (
    MarketInfoModule,
    MarketInfoResult,
    MarketSummaryQuote,
    MarketTimeResult,
    SectorResult,
    TrendingQuote,
    TrendingResult,
)
from yoghurt.models.quote import Quote

if TYPE_CHECKING:
    from collections.abc import Mapping

    from yoghurt.models._base import YahooModel

_CORPUS_TRENDING_DIR = CORPUS_ROOT / "trending"
_CORPUS_MARKET_SUMMARY_DIR = CORPUS_ROOT / "market-summary"
_CORPUS_MARKET_INFO_DIR = CORPUS_ROOT / "market-info"
_CORPUS_MARKET_TIME_DIR = CORPUS_ROOT / "market-time"
_CORPUS_SECTOR_DIR = CORPUS_ROOT / "sector"

_EXPECTED_TRENDING_FILE_COUNT = 1
_EXPECTED_TRENDING_RECORD_COUNT = 5
_EXPECTED_MARKET_SUMMARY_FILE_COUNT = 1
_EXPECTED_MARKET_SUMMARY_RECORD_COUNT = 15
_EXPECTED_MARKET_INFO_FILE_COUNT = 1
_EXPECTED_MARKET_INFO_RECORD_COUNT = 2
_EXPECTED_MARKET_TIME_FILE_COUNT = 1
_EXPECTED_MARKET_TIME_RECORD_COUNT = 1
_EXPECTED_SECTOR_FILE_COUNT = 4

_EXPECTED_TRENDING_REQUIRED_FIELD_COUNT = 25
_EXPECTED_MARKET_SUMMARY_REQUIRED_FIELD_COUNT = 27
_EXPECTED_MARKET_INFO_REQUIRED_FIELD_COUNT = 3
_QUOTE_REQUIRED_FIELD_COUNT = 34


def _load_json(
    path: Any,  # ruff:ignore[any-type] - corpus JSON is untyped.
) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _flatten_extras(nested: dict[str, dict[str, object]]) -> list[str]:
    """Flatten a nested-extras map to sorted ``path.key`` strings."""

    return sorted(
        f"{path}.{key}" if path else key
        for path, extras in nested.items()
        for key in extras
    )


def _required_aliases(model_cls: type[YahooModel]) -> set[str]:
    return {
        (field_info.alias or name)
        for name, field_info in model_cls.model_fields.items()
        if field_info.is_required()
    }


# ---------------------------------------------------------------------------
# trending
# ---------------------------------------------------------------------------


def test_trending_corpus_has_expected_file_count() -> None:
    """Sanity check: 1 capture (5 mini-quote rows)."""

    files = sorted(_CORPUS_TRENDING_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_TRENDING_FILE_COUNT


def test_trending_stream_has_expected_record_count() -> None:
    """5 mini-quote rows in the single capture."""

    records = list(trending_records())
    assert len(records) == _EXPECTED_TRENDING_RECORD_COUNT


def _trending_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (path.name, _load_json(path)["finance"]["result"][0])
        for path in sorted(_CORPUS_TRENDING_DIR.glob("*.json"))
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _trending_cases(),
    ids=[case_id for case_id, _payload in _trending_cases()],
)
def test_trending_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every trending capture validates as TrendingResult with no extras."""

    del case_id
    result = TrendingResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"TrendingResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def _trending_quote_kind(record: Mapping[str, Any]) -> str:
    return str(record.get("quoteType", ""))


def test_trending_quote_required_field_set_matches_corpus_universal_keys() -> None:
    """TrendingQuote's required fields match the corpus-measured universal keys."""

    report = collect_presence(trending_records(), kind_of=_trending_quote_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = _required_aliases(TrendingQuote)

    assert len(universal_keys) == _EXPECTED_TRENDING_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


# ---------------------------------------------------------------------------
# market-summary
# ---------------------------------------------------------------------------


def test_market_summary_corpus_has_expected_file_count() -> None:
    """Sanity check: 1 capture (15 rows across INDEX/FUTURE/CURRENCY/CRYPTOCURRENCY)."""

    files = sorted(_CORPUS_MARKET_SUMMARY_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_MARKET_SUMMARY_FILE_COUNT


def test_market_summary_stream_has_expected_record_count() -> None:
    """15 rows in the single capture."""

    records = list(market_summary_records())
    assert len(records) == _EXPECTED_MARKET_SUMMARY_RECORD_COUNT


def _market_summary_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"market-summary[{index}]", dict(record))
        for index, record in enumerate(market_summary_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _market_summary_cases(),
    ids=[case_id for case_id, _payload in _market_summary_cases()],
)
def test_market_summary_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every market-summary row validates as MarketSummaryQuote with no extras."""

    del case_id
    result = MarketSummaryQuote.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"MarketSummaryQuote gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_market_summary_required_field_set_matches_corpus_universal_keys() -> None:
    """MarketSummaryQuote's required fields match the corpus-measured universal keys."""

    report = collect_presence(market_summary_records(), kind_of=_trending_quote_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = _required_aliases(MarketSummaryQuote)

    assert len(universal_keys) == _EXPECTED_MARKET_SUMMARY_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


def test_market_summary_rows_have_no_extras_against_quote() -> None:
    """Reuse-decision evidence: every row's wire keys are known to ``Quote``.

    None would land on ``model_extra``. Checked by wire-key membership
    rather than ``Quote.model_validate`` directly: a full validate would
    also enforce ``Quote``'s requiredness, which is the *other* half of
    the plan's decision procedure this row fails (see
    ``test_market_summary_required_quote_fields_are_not_all_universal``)
    and would raise before ``model_extra`` could even be inspected.
    """

    quote_aliases = {(f.alias or n) for n, f in Quote.model_fields.items()}
    for record in market_summary_records():
        unknown_keys = set(record) - quote_aliases
        assert not unknown_keys, (record.get("symbol"), unknown_keys)


def test_market_summary_required_quote_fields_are_not_all_universal() -> None:
    """Reuse-decision evidence: 8 of Quote's required fields aren't universal.

    ``currency``, ``priceHint``, and all six required ``fiftyTwoWeek*``
    fields are not universal across the market-summary corpus, which is why
    :class:`~yoghurt.models.markets.MarketSummaryQuote` is a distinct model
    rather than a reuse of :class:`~yoghurt.models.quote.Quote`. (The
    seventh family member, ``fiftyTwoWeekLowChangePercent``, is equally
    absent on these rows but optional on ``Quote`` since the 2026-07-05
    live loosening, so it no longer appears in this pin.)
    """

    quote_required_aliases = _required_aliases(Quote)
    assert len(quote_required_aliases) == _QUOTE_REQUIRED_FIELD_COUNT

    report = collect_presence(market_summary_records(), kind_of=_trending_quote_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    missing_from_universal = quote_required_aliases - universal_keys
    assert missing_from_universal == {
        "currency",
        "priceHint",
        "fiftyTwoWeekHigh",
        "fiftyTwoWeekHighChange",
        "fiftyTwoWeekHighChangePercent",
        "fiftyTwoWeekLow",
        "fiftyTwoWeekLowChange",
        "fiftyTwoWeekRange",
    }


# ---------------------------------------------------------------------------
# market-info
# ---------------------------------------------------------------------------


def test_market_info_corpus_has_expected_file_count() -> None:
    """Sanity check: 1 capture (both currencies and commodities modules)."""

    files = sorted(_CORPUS_MARKET_INFO_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_MARKET_INFO_FILE_COUNT


def test_market_info_stream_has_expected_record_count() -> None:
    """2 populated module tiles (currencies, commodities) in the single capture."""

    records = list(market_info_records())
    assert len(records) == _EXPECTED_MARKET_INFO_RECORD_COUNT


def _market_info_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (path.name, _load_json(path)["finance"]["result"])
        for path in sorted(_CORPUS_MARKET_INFO_DIR.glob("*.json"))
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _market_info_cases(),
    ids=[case_id for case_id, _payload in _market_info_cases()],
)
def test_market_info_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every market-info capture validates as MarketInfoResult with no extras."""

    del case_id
    result = MarketInfoResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"MarketInfoResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_market_info_module_required_field_set_matches_corpus_universal_keys() -> None:
    """MarketInfoModule's required fields match the corpus-measured universal keys."""

    report = collect_presence(market_info_records(), kind_of=market_info_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = _required_aliases(MarketInfoModule)

    assert len(universal_keys) == _EXPECTED_MARKET_INFO_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


# ---------------------------------------------------------------------------
# market-time
# ---------------------------------------------------------------------------


def test_market_time_corpus_has_expected_file_count() -> None:
    """Sanity check: 1 thin capture (single market group, single entry)."""

    files = sorted(_CORPUS_MARKET_TIME_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_MARKET_TIME_FILE_COUNT


def test_market_time_stream_has_expected_record_count() -> None:
    """1 market-time entry in the single capture."""

    records = list(market_time_records())
    assert len(records) == _EXPECTED_MARKET_TIME_RECORD_COUNT


def _market_time_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (path.name, _load_json(path)["finance"])
        for path in sorted(_CORPUS_MARKET_TIME_DIR.glob("*.json"))
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _market_time_cases(),
    ids=[case_id for case_id, _payload in _market_time_cases()],
)
def test_market_time_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every market-time capture validates as MarketTimeResult with no extras."""

    del case_id
    result = MarketTimeResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"MarketTimeResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


# ---------------------------------------------------------------------------
# sector
# ---------------------------------------------------------------------------


def test_sector_corpus_has_expected_file_count() -> None:
    """Sanity check: 4 captures (energy, real-estate, technology x2)."""

    files = sorted(_CORPUS_SECTOR_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_SECTOR_FILE_COUNT


def _sector_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (path.name, _load_json(path)["data"])
        for path in sorted(_CORPUS_SECTOR_DIR.glob("*.json"))
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _sector_cases(),
    ids=[case_id for case_id, _payload in _sector_cases()],
)
def test_sector_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every sector capture validates as SectorResult with no extras anywhere."""

    del case_id
    result = SectorResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"SectorResult gained unmodeled fields (drift alarm): {_flatten_extras(nested)}"
    )
    assert not nested, message


def test_sector_technology_with_returns_variant_matches_plain_shape() -> None:
    """The --with-returns capture is shape-identical to the plain capture.

    Every key set matches at every nesting level (values/ordering differ);
    see the model module's docstring for the full diff evidence.
    """

    plain = _load_json(_CORPUS_SECTOR_DIR / "technology.json")["data"]
    with_returns = _load_json(_CORPUS_SECTOR_DIR / "technology_returns.json")["data"]
    assert set(plain.keys()) == set(with_returns.keys())


def test_sector_industries_key_and_symbol_absent_only_on_aggregate_row() -> None:
    """SectorIndustry.key/.symbol are absent only on the "All Industries" row."""

    for path in sorted(_CORPUS_SECTOR_DIR.glob("*.json")):
        data = _load_json(path)["data"]
        industries = data["industries"]
        assert "key" not in industries[0]
        assert "symbol" not in industries[0]
        for row in industries[1:]:
            assert "key" in row
            assert "symbol" in row


# ---------------------------------------------------------------------------
# alphabetical field order (template enforcement)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_cls",
    [
        TrendingResult,
        MarketSummaryQuote,
        MarketInfoResult,
        MarketTimeResult,
        SectorResult,
    ],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[YahooModel],
) -> None:
    """Template enforcement: every model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
