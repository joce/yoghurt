"""Batch 3d-1 corpus gate: calendar-events/quote-type/recommendations/stock-recommender.

Every relevant corpus capture must validate against its model with nothing
landing on ``model_extra`` anywhere in the model tree, and each model's
required-field set is pinned to its corpus-measured universal keys via
``tools.fields_report``. See ``tests/models/test_analysis_insights_corpus.py``
for the remaining two (deeper) batch 3d-1 endpoints.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import (
    CORPUS_ROOT,
    collect_presence,
    earnings_records,
    ipo_events_records,
    quote_type_lookup_kind,
    quote_type_records,
    recommendations_records,
    sec_reports_records,
    stock_recommender_records,
)
from yoghurt.models.analysis_events import (
    CalendarEventsResult,
    EarningsEvent,
    EarningsEventDay,
    EconomicEvent,
    EconomicEventDay,
    IpoEvent,
    IpoEventDay,
    QuoteTypeResult,
    RecommendationsResult,
    SecReport,
    SecReportDay,
    SecReportExhibit,
    StockRecommenderResult,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from yoghurt.models._base import YahooModel

_CORPUS_CALENDAR_EVENTS_DIR = CORPUS_ROOT / "calendar-events"
_CORPUS_QUOTE_TYPE_DIR = CORPUS_ROOT / "quote-type"
_CORPUS_RECOMMENDATIONS_DIR = CORPUS_ROOT / "recommendations-by-symbol"
_CORPUS_STOCK_RECOMMENDER_DIR = CORPUS_ROOT / "stock-recommender"

_EXPECTED_CALENDAR_EVENTS_FILE_COUNT = (
    44  # +15 populated windows +3 split-hypothesis negative evidence
)
_EXPECTED_QUOTE_TYPE_FILE_COUNT = 24  # 23 valid + ZZZZXYZQ
_EXPECTED_QUOTE_TYPE_RECORD_COUNT = 23
_EXPECTED_RECOMMENDATIONS_FILE_COUNT = (
    9  # +5: SPY/BTC-USD/EURUSD=X/ES=F/ZZZZXYZQ (P4-1)
)
_EXPECTED_STOCK_RECOMMENDER_FILE_COUNT = 4  # +1: ZZZZXYZQ (P4-1, unmappable 404 body)

_EXPECTED_QUOTE_TYPE_REQUIRED_FIELD_COUNT = 11
_EXPECTED_RECOMMENDATIONS_REQUIRED_FIELD_COUNT = 2
_EXPECTED_STOCK_RECOMMENDER_REQUIRED_FIELD_COUNT = 3
_EXPECTED_EARNINGS_RECORD_COUNT = 5
_EXPECTED_EARNINGS_REQUIRED_FIELD_COUNT = 13
_EXPECTED_IPO_EVENTS_RECORD_COUNT = 6
_EXPECTED_IPO_EVENTS_REQUIRED_FIELD_COUNT = 8
_EXPECTED_SEC_REPORTS_RECORD_COUNT = 9
_EXPECTED_SEC_REPORTS_REQUIRED_FIELD_COUNT = 10


def _load_json(path: Any) -> dict[str, Any]:  # noqa: ANN401 - corpus JSON is untyped.
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _flatten_extras(nested: dict[str, dict[str, object]]) -> list[str]:
    """Flatten a nested-extras map to sorted ``path.key`` strings."""

    return sorted(
        f"{path}.{key}" if path else key
        for path, extras in nested.items()
        for key in extras
    )


# ---------------------------------------------------------------------------
# calendar-events
# ---------------------------------------------------------------------------


def test_calendar_events_corpus_has_expected_file_count() -> None:
    """Sanity check: 44 (26 original + 15 populated windows + 3 split negatives)."""

    files = sorted(_CORPUS_CALENDAR_EVENTS_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_CALENDAR_EVENTS_FILE_COUNT


def _calendar_events_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (path.name, _load_json(path)["finance"]["result"])
        for path in sorted(_CORPUS_CALENDAR_EVENTS_DIR.glob("*.json"))
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _calendar_events_cases(),
    ids=[case_id for case_id, _payload in _calendar_events_cases()],
)
def test_calendar_events_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every calendar-events capture validates with no extras anywhere.

    Covers the default (``earnings``-only) shape and the three isolated
    ``--modules`` probes (``economicEvents``/``ipoEvents``/``secReports``).
    """

    del case_id
    result = CalendarEventsResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"CalendarEventsResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_calendar_events_every_field_is_optional() -> None:
    """No capture ever populates more than one module key at once.

    See the model module's docstring: the default request returns only
    ``earnings``, and each ``--modules`` probe returns only that module.
    """

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in CalendarEventsResult.model_fields.items()
        if field_info.is_required()
    }
    assert required_aliases == set()


def test_earnings_stream_has_expected_record_count() -> None:
    """5 earnings rows: IVF/HAWK/EBF/POWW (2026-06-22) + MSFT (2026-04-29)."""

    records = list(earnings_records())
    assert len(records) == _EXPECTED_EARNINGS_RECORD_COUNT


def _earnings_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"earnings[{index}]", dict(record))
        for index, record in enumerate(earnings_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _earnings_cases(),
    ids=[case_id for case_id, _payload in _earnings_cases()],
)
def test_earnings_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every earnings row validates as EarningsEvent with no extras."""

    del case_id
    result = EarningsEvent.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"EarningsEvent gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_earnings_required_field_set_matches_corpus_universal_keys() -> None:
    """EarningsEvent's required fields match the corpus-measured universal keys."""

    report = collect_presence(earnings_records(), kind_of=lambda _r: "earnings")
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in EarningsEvent.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_EARNINGS_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


def test_ipo_events_stream_has_expected_record_count() -> None:
    """6 ipoEvents rows: COPR/GSRVR/IQMXW/MIACU/VCRE/SECZ (2026-07-02)."""

    records = list(ipo_events_records())
    assert len(records) == _EXPECTED_IPO_EVENTS_RECORD_COUNT


def _ipo_events_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"ipoEvents[{index}]", dict(record))
        for index, record in enumerate(ipo_events_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _ipo_events_cases(),
    ids=[case_id for case_id, _payload in _ipo_events_cases()],
)
def test_ipo_events_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every ipoEvents row validates as IpoEvent with no extras."""

    del case_id
    result = IpoEvent.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"IpoEvent gained unmodeled fields (drift alarm): {_flatten_extras(nested)}"
    )
    assert not nested, message


def test_ipo_events_required_field_set_matches_corpus_universal_keys() -> None:
    """IpoEvent's required fields match the corpus-measured universal keys."""

    report = collect_presence(ipo_events_records(), kind_of=lambda _r: "ipoEvents")
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in IpoEvent.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_IPO_EVENTS_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


def test_sec_reports_stream_has_expected_record_count() -> None:
    """9 secReports rows: BOXL x2 + HAWK x2 + AAPL x3 + MSFT x2."""

    records = list(sec_reports_records())
    assert len(records) == _EXPECTED_SEC_REPORTS_RECORD_COUNT


def _sec_reports_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"secReports[{index}]", dict(record))
        for index, record in enumerate(sec_reports_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _sec_reports_cases(),
    ids=[case_id for case_id, _payload in _sec_reports_cases()],
)
def test_sec_reports_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every secReports row validates as SecReport with no extras."""

    del case_id
    result = SecReport.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"SecReport gained unmodeled fields (drift alarm): {_flatten_extras(nested)}"
    )
    assert not nested, message


def test_sec_reports_required_field_set_matches_corpus_universal_keys() -> None:
    """SecReport's required fields match the corpus-measured universal keys."""

    report = collect_presence(sec_reports_records(), kind_of=lambda _r: "secReports")
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in SecReport.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_SEC_REPORTS_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


# ---------------------------------------------------------------------------
# quote-type
# ---------------------------------------------------------------------------


def test_quote_type_corpus_has_expected_file_count() -> None:
    """Sanity check: 24 files (23 valid + the ZZZZXYZQ invalid-symbol probe)."""

    files = sorted(_CORPUS_QUOTE_TYPE_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_QUOTE_TYPE_FILE_COUNT


def test_quote_type_stream_has_expected_record_count() -> None:
    """23 valid quote-type records (ZZZZXYZQ's empty result is skipped)."""

    records = list(quote_type_records())
    assert len(records) == _EXPECTED_QUOTE_TYPE_RECORD_COUNT


def _quote_type_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"quote-type[{index}]", dict(record))
        for index, record in enumerate(quote_type_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _quote_type_cases(),
    ids=[case_id for case_id, _payload in _quote_type_cases()],
)
def test_quote_type_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every quote-type capture validates as QuoteTypeResult with no extras."""

    del case_id
    result = QuoteTypeResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"QuoteTypeResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def _quote_type_kind(record: Mapping[str, Any]) -> str:
    return str(record.get("quoteType", ""))


def test_quote_type_required_field_set_matches_corpus_universal_keys() -> None:
    """QuoteTypeResult's required fields match the corpus-measured universal keys."""

    report = collect_presence(quote_type_records(), kind_of=_quote_type_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in QuoteTypeResult.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_QUOTE_TYPE_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


# ---------------------------------------------------------------------------
# recommendations-by-symbol
# ---------------------------------------------------------------------------


def test_recommendations_corpus_has_expected_file_count() -> None:
    """Sanity check: 9 captures (AAPL/MSFT/RY.TO/^GSPC + 5 P4-1 additions)."""

    files = sorted(_CORPUS_RECOMMENDATIONS_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_RECOMMENDATIONS_FILE_COUNT


def _recommendations_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"recommendations[{index}]", dict(record))
        for index, record in enumerate(recommendations_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _recommendations_cases(),
    ids=[case_id for case_id, _payload in _recommendations_cases()],
)
def test_recommendations_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every recommendations-by-symbol capture validates with no extras anywhere."""

    del case_id
    result = RecommendationsResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"RecommendationsResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_recommendations_required_field_set_matches_corpus_universal_keys() -> None:
    """RecommendationsResult's required fields match the corpus's universal keys."""

    report = collect_presence(recommendations_records(), kind_of=quote_type_lookup_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in RecommendationsResult.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_RECOMMENDATIONS_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


# ---------------------------------------------------------------------------
# stock-recommender
# ---------------------------------------------------------------------------


def test_stock_recommender_corpus_has_expected_file_count() -> None:
    """Sanity check: 4 captures (AAPL, MSFT, RY.TO, ZZZZXYZQ 404 body)."""

    files = sorted(_CORPUS_STOCK_RECOMMENDER_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_STOCK_RECOMMENDER_FILE_COUNT


def _stock_recommender_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"stock-recommender[{index}]", dict(record))
        for index, record in enumerate(stock_recommender_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _stock_recommender_cases(),
    ids=[case_id for case_id, _payload in _stock_recommender_cases()],
)
def test_stock_recommender_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every stock-recommender capture validates with no extras anywhere."""

    del case_id
    result = StockRecommenderResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"StockRecommenderResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_stock_recommender_required_field_set_matches_corpus_universal_keys() -> None:
    """StockRecommenderResult's required fields match the corpus's universal keys."""

    report = collect_presence(
        stock_recommender_records(), kind_of=quote_type_lookup_kind
    )
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in StockRecommenderResult.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_STOCK_RECOMMENDER_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


# ---------------------------------------------------------------------------
# alphabetical field order (template enforcement)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_cls",
    [
        CalendarEventsResult,
        EarningsEvent,
        EarningsEventDay,
        EconomicEvent,
        EconomicEventDay,
        IpoEvent,
        IpoEventDay,
        QuoteTypeResult,
        RecommendationsResult,
        SecReport,
        SecReportDay,
        SecReportExhibit,
        StockRecommenderResult,
    ],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[YahooModel],
) -> None:
    """Template enforcement: every model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
