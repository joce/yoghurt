"""Batch 3d-1 corpus gate: price-insights/insights.

Every relevant corpus capture must validate against its model with nothing
landing on ``model_extra`` anywhere in the model tree, and each model's
required-field set is pinned to its corpus-measured universal keys via
``tools.fields_report``. See ``tests/models/test_analysis_events_corpus.py``
for the remaining (smaller, flatter) four batch 3d-1 endpoints.

``PriceInsights`` is the tri-variant model (see the model module's
docstring): this file's parametrized validation cases span all three
captured shapes (default, AI-only, anomaly-only), proving one model
validates every variant.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import (
    CORPUS_ROOT,
    collect_presence,
    insights_records,
    price_insights_records,
    quote_type_lookup_kind,
)
from yoghurt.models.analysis_insights import Insights, PriceInsights

if TYPE_CHECKING:
    from yoghurt.models._base import YahooModel

_CORPUS_PRICE_INSIGHTS_DIR = CORPUS_ROOT / "price-insights"
_CORPUS_INSIGHTS_DIR = CORPUS_ROOT / "insights"

_EXPECTED_PRICE_INSIGHTS_FILE_COUNT = 11  # +6: cross-asset (P4-1)
_EXPECTED_PRICE_INSIGHTS_RECORD_COUNT = 11
_EXPECTED_INSIGHTS_FILE_COUNT = 9  # +6: cross-asset (P4-1)
_EXPECTED_INSIGHTS_RECORD_COUNT = 9

_EXPECTED_PRICE_INSIGHTS_REQUIRED_FIELD_COUNT = 1
_EXPECTED_INSIGHTS_REQUIRED_FIELD_COUNT = (
    2  # was 4; widened corpus thins to sigDevs/symbol
)


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
# price-insights
# ---------------------------------------------------------------------------


def test_price_insights_corpus_has_expected_file_count() -> None:
    """Sanity check: 11 captures (default x3, AI-only, anomaly-only, +6 cross-asset)."""

    files = sorted(_CORPUS_PRICE_INSIGHTS_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_PRICE_INSIGHTS_FILE_COUNT


def test_price_insights_stream_has_expected_record_count() -> None:
    """11 per-symbol records (one per capture; each capture is single-symbol)."""

    records = list(price_insights_records())
    assert len(records) == _EXPECTED_PRICE_INSIGHTS_RECORD_COUNT


def _price_insights_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"price-insights[{index}]", dict(record))
        for index, record in enumerate(price_insights_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _price_insights_cases(),
    ids=[case_id for case_id, _payload in _price_insights_cases()],
)
def test_price_insights_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every price-insights capture validates with no extras anywhere.

    Covers all three captured shape variants: default (every field
    populated), AI-only (``aiAnalysis``/``hasPriceAnomaly`` only), and
    anomaly-only (``hasPriceAnomaly`` alone) — see the model module's
    docstring.
    """

    del case_id
    result = PriceInsights.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"PriceInsights gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_price_insights_required_field_set_matches_corpus_universal_keys() -> None:
    """Only has_price_anomaly is required; every other field is absent-able."""

    report = collect_presence(price_insights_records(), kind_of=quote_type_lookup_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in PriceInsights.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_PRICE_INSIGHTS_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys
    assert required_aliases == {"hasPriceAnomaly"}


def test_price_insights_anomaly_only_variant_has_only_has_price_anomaly() -> None:
    """The anomaly-only capture omits every field except has_price_anomaly."""

    payload = _load_json(_CORPUS_PRICE_INSIGHTS_DIR / "AAPL_anomaly.json")
    record = payload["finance"]["result"]["AAPL"]
    assert set(record.keys()) == {"hasPriceAnomaly"}


def test_price_insights_ai_only_variant_omits_news_and_analyst_rating() -> None:
    """The AI-only capture omits newsFirstParty/newsThirdParty/analystRating."""

    payload = _load_json(_CORPUS_PRICE_INSIGHTS_DIR / "AAPL_ai.json")
    record = payload["finance"]["result"]["AAPL"]
    assert set(record.keys()) == {"aiAnalysis", "hasPriceAnomaly"}


# ---------------------------------------------------------------------------
# insights
# ---------------------------------------------------------------------------


def test_insights_corpus_has_expected_file_count() -> None:
    """Sanity check: 9 captures (AAPL, MSFT, RY.TO, +6 cross-asset/invalid-symbol)."""

    files = sorted(_CORPUS_INSIGHTS_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_INSIGHTS_FILE_COUNT


def test_insights_stream_has_expected_record_count() -> None:
    """9 result records, one per capture."""

    records = list(insights_records())
    assert len(records) == _EXPECTED_INSIGHTS_RECORD_COUNT


def _insights_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"insights[{index}]", dict(record))
        for index, record in enumerate(insights_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _insights_cases(),
    ids=[case_id for case_id, _payload in _insights_cases()],
)
def test_insights_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every insights capture validates with no extras anywhere.

    Covers the two rich EQUITY captures (AAPL/MSFT), the non-EQUITY rich
    ``SPY`` capture (events/instrumentInfo/secReports/sigDevs/symbol), and
    the thin captures: RY.TO (recommendation/sigDevs/symbol/upsell) plus
    the 2026-07-05 cross-asset/invalid-symbol widening
    (^GSPC/BTC-USD/EURUSD=X/ES=F/ZZZZXYZQ, all sigDevs/symbol only).
    """

    del case_id
    result = Insights.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"Insights gained unmodeled fields (drift alarm): {_flatten_extras(nested)}"
    )
    assert not nested, message


def test_insights_required_field_set_matches_corpus_universal_keys() -> None:
    """Only sig_devs/symbol are required, now matching the corpus's own universal set.

    Originally (3-capture, EQUITY-only corpus: AAPL/MSFT/RY.TO) the
    corpus's universal-key set also included ``recommendation``/``upsell``,
    making the model's required set a strict subset rather than an exact
    match — those two fields were known EQUITY-only only from live
    cross-asset-class checks during development, not yet backed by a
    corpus capture. The 2026-07-05 cross-asset widening
    (``^GSPC``/``BTC-USD``/``EURUSD=X``/``ES=F``/``ZZZZXYZQ``, all thinner
    than RY.TO) now corpus-confirms that finding: the corpus's own
    universal set collapses to exactly ``sigDevs``/``symbol``, matching
    the model exactly like every other model in this batch.
    """

    report = collect_presence(insights_records(), kind_of=quote_type_lookup_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in Insights.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_INSIGHTS_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys
    assert required_aliases == {"sigDevs", "symbol"}


def test_insights_thin_ry_to_capture_omits_optional_blocks() -> None:
    """RY.TO omits every optional block: companySnapshot/events/instrumentInfo/..."""

    payload = _load_json(_CORPUS_INSIGHTS_DIR / "RY.TO.json")
    record = payload["finance"]["result"][0]
    assert set(record.keys()) == {"recommendation", "sigDevs", "symbol", "upsell"}


def test_insights_report_with_analyst_fields_validates() -> None:
    """The one 'Analyst Report'-type row carries targetPrice/investmentRating."""

    payload = _load_json(_CORPUS_INSIGHTS_DIR / "AAPL.json")
    record = payload["finance"]["result"][0]
    analyst_reports = [r for r in record["reports"] if "targetPrice" in r]
    assert len(analyst_reports) == 1


def test_insights_sec_report_exhibit_with_download_url_validates() -> None:
    """Some Excel-type exhibits carry a downloadUrl not present on every exhibit."""

    payload = _load_json(_CORPUS_INSIGHTS_DIR / "AAPL.json")
    record = payload["finance"]["result"][0]
    exhibits_with_download = [
        exhibit
        for sec_report in record["secReports"]
        for exhibit in sec_report["exhibits"]
        if "downloadUrl" in exhibit
    ]
    assert exhibits_with_download


# ---------------------------------------------------------------------------
# alphabetical field order (template enforcement)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_cls",
    [PriceInsights, Insights],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[YahooModel],
) -> None:
    """Template enforcement: every model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
