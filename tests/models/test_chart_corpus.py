"""The ChartMeta/ChartEvents corpus coverage gate.

Every valid chart capture's ``meta`` block and every spark response's
``meta`` block must validate as :class:`ChartMeta` with nothing landing on
``model_extra`` anywhere in the model tree (including the nested
``currentTradingPeriod``/``tradingPeriods`` sub-models). Every observed
``events`` block must validate as :class:`ChartEvents` with the same empty-
extras guarantee, exercising the nested-extras walker's dict-traversal path
(``dividends``/``splits`` are ``dict[str, Model]`` fields, not lists). This
file also pins the required-field set to the corpus-measured universal keys
and enforces alphabetical field declaration order for every model added in
this module.
"""

from __future__ import annotations

import datetime
import json
from typing import Any

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import (
    CORPUS_ROOT,
    chart_and_spark_meta_records,
    collect_chart_and_spark_meta_presence,
)
from yoghurt.models.chart import (
    ChartDividend,
    ChartEvents,
    ChartMeta,
    ChartSplit,
    CurrentTradingPeriod,
    TradingPeriod,
)

_CORPUS_CHART_DIR = CORPUS_ROOT / "chart"
_CORPUS_SPARK_DIR = CORPUS_ROOT / "spark"
_INVALID_SYMBOL_STEM = "ZZZZXYZQ"

_EXPECTED_CHART_FILE_COUNT = 25
_EXPECTED_CHART_VALID_META_COUNT = 24
_EXPECTED_SPARK_FILE_COUNT = 24
_EXPECTED_SPARK_META_COUNT = 24
_EXPECTED_COMBINED_META_COUNT = 48
_EXPECTED_REQUIRED_FIELD_COUNT = 21


def _load_json(path: Any) -> dict[str, Any]:  # noqa: ANN401 - corpus JSON is untyped.
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _chart_meta_cases() -> list[tuple[str, dict[str, Any]]]:
    """Every (case-id, meta) pair across valid chart captures."""

    cases: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(_CORPUS_CHART_DIR.glob("*.json")):
        if path.stem == _INVALID_SYMBOL_STEM:
            continue
        payload = _load_json(path)
        results: list[dict[str, Any]] = payload.get("chart", {}).get("result") or []
        if not results:
            continue
        meta = results[0].get("meta")
        if meta:
            cases.append((path.name, meta))
    return cases


def _spark_meta_cases() -> list[tuple[str, dict[str, Any]]]:
    """Every (case-id, meta) pair across spark responses."""

    cases: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(_CORPUS_SPARK_DIR.glob("*.json")):
        if path.stem == _INVALID_SYMBOL_STEM:
            continue
        payload = _load_json(path)
        results: list[dict[str, Any]] = payload.get("spark", {}).get("result") or []
        for index, result in enumerate(results):
            responses: list[dict[str, Any]] = result.get("response") or []
            for response_index, response in enumerate(responses):
                meta = response.get("meta")
                if meta:
                    case_id = f"{path.name}[{index}][{response_index}]"
                    cases.append((case_id, meta))
    return cases


_CHART_CASES = _chart_meta_cases()
_SPARK_CASES = _spark_meta_cases()
_ALL_META_CASES = _CHART_CASES + _SPARK_CASES


def _flatten_extras(nested: dict[str, dict[str, object]]) -> list[str]:
    """Flatten a nested-extras map to sorted ``path.key`` strings."""

    return sorted(
        f"{path}.{key}" if path else key
        for path, extras in nested.items()
        for key in extras
    )


def test_chart_corpus_has_expected_file_and_record_counts() -> None:
    """Sanity check on the fixture set: 25 chart files, 24 with valid meta."""

    chart_files = sorted(_CORPUS_CHART_DIR.glob("*.json"))
    assert len(chart_files) == _EXPECTED_CHART_FILE_COUNT
    assert len(_CHART_CASES) == _EXPECTED_CHART_VALID_META_COUNT


def test_spark_corpus_has_expected_file_and_record_counts() -> None:
    """Sanity check on the fixture set: 24 spark files, 24 meta records."""

    spark_files = sorted(_CORPUS_SPARK_DIR.glob("*.json"))
    assert len(spark_files) == _EXPECTED_SPARK_FILE_COUNT
    assert len(_SPARK_CASES) == _EXPECTED_SPARK_META_COUNT


def test_zzzzxyzq_chart_capture_has_no_result() -> None:
    """The unknown-symbol chart capture must have zero results, not a skip."""

    path = _CORPUS_CHART_DIR / f"{_INVALID_SYMBOL_STEM}.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert (payload.get("chart", {}).get("result") or []) == []


def test_zzzzxyzq_spark_capture_has_no_result() -> None:
    """The unknown-symbol spark capture must have zero results, not a skip."""

    path = _CORPUS_SPARK_DIR / f"{_INVALID_SYMBOL_STEM}.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert (payload.get("spark", {}).get("result") or None) is None


@pytest.mark.parametrize(
    "meta",
    [meta for _case_id, meta in _ALL_META_CASES],
    ids=[case_id for case_id, _meta in _ALL_META_CASES],
)
def test_meta_validates_with_no_extra_fields(meta: dict[str, object]) -> None:
    """Every chart/spark meta record validates as ChartMeta with no extras anywhere.

    The nested-extras walker checks the whole model tree, including
    ``currentTradingPeriod`` (three nested ``TradingPeriod`` sub-models) and
    ``tradingPeriods`` (a list of lists of ``TradingPeriod``), not just the
    top level.
    """

    chart_meta = ChartMeta.model_validate(meta)
    nested = collect_nested_extras(chart_meta)
    message = (
        f"ChartMeta gained unmodeled fields (drift alarm): {_flatten_extras(nested)}"
    )
    assert not nested, message


def test_combined_meta_stream_has_expected_record_count() -> None:
    """The chart+spark meta stream used for requiredness evidence has 48 records."""

    assert len(_ALL_META_CASES) == _EXPECTED_COMBINED_META_COUNT
    assert len(list(chart_and_spark_meta_records())) == _EXPECTED_COMBINED_META_COUNT


def test_required_field_set_matches_combined_stream_universal_keys() -> None:
    """ChartMeta's required fields are exactly the combined-stream universal keys.

    The combined chart+spark meta stream (not chart alone) is the evidence
    base, since both endpoints share the same meta shape and spark adds
    fields (``previousClose``, ``scale``, ``tradingPeriods``) that chart
    only leaks in one intraday capture.
    """

    report = collect_chart_and_spark_meta_presence()
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in ChartMeta.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


@pytest.mark.parametrize(
    "model_cls",
    [
        ChartMeta,
        TradingPeriod,
        CurrentTradingPeriod,
        ChartDividend,
        ChartSplit,
        ChartEvents,
    ],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[ChartMeta],
) -> None:
    """Template enforcement: every new model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)


def _events_cases() -> list[tuple[str, dict[str, Any]]]:
    """Every (case-id, events) pair across chart captures that carry events."""

    cases: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(_CORPUS_CHART_DIR.glob("*.json")):
        if path.stem == _INVALID_SYMBOL_STEM:
            continue
        payload = _load_json(path)
        results: list[dict[str, Any]] = payload.get("chart", {}).get("result") or []
        if not results:
            continue
        events = results[0].get("events")
        if events:
            cases.append((path.name, events))
    return cases


_EVENTS_CASES = _events_cases()
_EXPECTED_EVENTS_CASE_COUNT = 2


def test_events_corpus_has_expected_case_count() -> None:
    """Only MSFT_1y_events.json and BAC-PL.json carry an events block."""

    assert len(_EVENTS_CASES) == _EXPECTED_EVENTS_CASE_COUNT
    assert {case_id for case_id, _events in _EVENTS_CASES} == {
        "BAC-PL.json",
        "MSFT_1y_events.json",
    }


@pytest.mark.parametrize(
    "events",
    [events for _case_id, events in _EVENTS_CASES],
    ids=[case_id for case_id, _events in _EVENTS_CASES],
)
def test_events_validates_with_no_extra_fields(events: dict[str, object]) -> None:
    """Every observed events block validates as ChartEvents with no extras.

    This exercises the nested-extras walker's dict-traversal path: the
    ``dividends`` field is a ``dict[str, ChartDividend]``, keyed by an
    epoch-second string, not a list.
    """

    chart_events = ChartEvents.model_validate(events)
    nested = collect_nested_extras(chart_events)
    assert not nested, f"ChartEvents gained unmodeled fields: {nested}"
    assert chart_events.dividends


def test_events_dividends_are_keyed_by_epoch_string() -> None:
    """MSFT_1y_events.json's dividends dict validates each entry's shape."""

    path = _CORPUS_CHART_DIR / "MSFT_1y_events.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    events = payload["chart"]["result"][0]["events"]

    chart_events = ChartEvents.model_validate(events)

    assert chart_events.dividends is not None
    assert chart_events.splits is None
    for key, dividend in chart_events.dividends.items():
        assert key.isdigit()
        assert dividend.date == datetime.datetime.fromtimestamp(
            int(key), tz=datetime.timezone.utc
        )
        assert dividend.date.tzinfo is not None
        assert isinstance(dividend.amount, float)
