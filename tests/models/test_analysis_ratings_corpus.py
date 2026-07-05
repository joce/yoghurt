"""Batch 3d-2 corpus gate: analyst/ratings-top.

Every relevant corpus capture must validate against its model with nothing
landing on ``model_extra`` anywhere in the model tree, and each model's
required-field set is pinned to its corpus-measured universal keys via
``tools.fields_report``. See ``tests/models/test_analysis_events_corpus.py``/
``test_analysis_insights_corpus.py`` for the batch 3d-1 endpoints.

Both endpoints in this batch rest on an unusually thin evidence base: only
2 populated captures each (``AAPL``/``MSFT``). ``analyst``'s corpus has no
thin-but-valid capture at all — the plan's expected ``RY.TO`` "thin"
capture turned out, on inspection, to be a genuine 404 error body
(``{"detail": "Symbol not found for RY.TO"}``), same as the deliberate
``ZZZZXYZQ`` probe. ``ratings-top``'s ``RY.TO`` capture is also a genuine
404 (``{"detail": "No top ratings found for symbol: RY.TO"}``). This
module's required-field gates are therefore pinned to a 2-record universal
set for both endpoints; a future corpus refresh with a genuinely thin or
wider-instrument-type capture is the real test of these requiredness
assumptions.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import (
    CORPUS_ROOT,
    analyst_records,
    collect_presence,
    quote_type_lookup_kind,
    ratings_top_records,
)
from yoghurt.models.analysis_insights import NewsSummaryBlock, PriceMovement
from yoghurt.models.analysis_ratings import AnalystResult, TopRatingsResult

if TYPE_CHECKING:
    from yoghurt.models._base import YahooModel

_CORPUS_ANALYST_DIR = CORPUS_ROOT / "analyst"
_CORPUS_RATINGS_TOP_DIR = CORPUS_ROOT / "ratings-top"

_EXPECTED_ANALYST_FILE_COUNT = 4  # AAPL, MSFT, RY.TO (404), ZZZZXYZQ (404)
_EXPECTED_ANALYST_RECORD_COUNT = 2  # AAPL, MSFT only; both error bodies skipped
_EXPECTED_RATINGS_TOP_FILE_COUNT = 3  # AAPL, MSFT, RY.TO (404)
_EXPECTED_RATINGS_TOP_RECORD_COUNT = 2  # AAPL, MSFT only; error body skipped

_EXPECTED_ANALYST_REQUIRED_FIELD_COUNT = 9
_EXPECTED_RATINGS_TOP_REQUIRED_FIELD_COUNT = 4


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
# analyst
# ---------------------------------------------------------------------------


def test_analyst_corpus_has_expected_file_count() -> None:
    """Sanity check: 4 captures (2 valid + RY.TO/ZZZZXYZQ 404 bodies)."""

    files = sorted(_CORPUS_ANALYST_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_ANALYST_FILE_COUNT


def test_analyst_stream_has_expected_record_count() -> None:
    """2 valid records (both error-shaped captures are skipped)."""

    records = list(analyst_records())
    assert len(records) == _EXPECTED_ANALYST_RECORD_COUNT


def test_analyst_ry_to_capture_is_a_404_error_body() -> None:
    """RY.TO is a genuine not-found error, not a thin-but-valid capture.

    The plan anticipated a thin-but-valid RY.TO record; the actual capture
    is an error body identical in shape to the deliberate ZZZZXYZQ probe.
    """

    payload = _load_json(_CORPUS_ANALYST_DIR / "RY.TO.json")
    assert set(payload.keys()) == {"detail"}
    assert "not found" in payload["detail"].lower()


def test_analyst_zzzzxyzq_capture_is_a_404_error_body() -> None:
    """The deliberate invalid-symbol probe is a not-found error body."""

    payload = _load_json(_CORPUS_ANALYST_DIR / "ZZZZXYZQ.json")
    assert set(payload.keys()) == {"detail"}
    assert "not found" in payload["detail"].lower()


def _analyst_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"analyst[{index}]", dict(record))
        for index, record in enumerate(analyst_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _analyst_cases(),
    ids=[case_id for case_id, _payload in _analyst_cases()],
)
def test_analyst_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every valid analyst capture validates with no extras anywhere."""

    del case_id
    result = AnalystResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"AnalystResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_analyst_required_field_set_matches_corpus_universal_keys() -> None:
    """AnalystResult's required fields match the corpus-measured universal keys.

    Thin evidence: only 2 records back this gate (see the module
    docstring); a future corpus refresh with a genuinely thin capture is
    the real requiredness test.
    """

    report = collect_presence(analyst_records(), kind_of=quote_type_lookup_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in AnalystResult.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_ANALYST_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


def test_analyst_price_movement_reuses_analysis_insights_model() -> None:
    """AnalystResult.price_movement is the shared PriceMovement model."""

    assert AnalystResult.model_fields["price_movement"].annotation is PriceMovement


def test_analyst_news_summary_reuses_analysis_insights_model() -> None:
    """AnalystResult.news_summary is the shared NewsSummaryBlock model."""

    assert AnalystResult.model_fields["news_summary"].annotation is NewsSummaryBlock


# ---------------------------------------------------------------------------
# ratings-top
# ---------------------------------------------------------------------------


def test_ratings_top_corpus_has_expected_file_count() -> None:
    """Sanity check: 3 captures (2 valid + RY.TO 404 body)."""

    files = sorted(_CORPUS_RATINGS_TOP_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_RATINGS_TOP_FILE_COUNT


def test_ratings_top_stream_has_expected_record_count() -> None:
    """2 valid records (the RY.TO error-shaped capture is skipped)."""

    records = list(ratings_top_records())
    assert len(records) == _EXPECTED_RATINGS_TOP_RECORD_COUNT


def test_ratings_top_ry_to_capture_is_a_404_error_body() -> None:
    """RY.TO is a 404, but its wording does NOT trip _core's "not found" check.

    ``"No top ratings found for symbol: RY.TO"`` contains "ratings found",
    not the literal substring "not found" that
    ``yoghurt._core.map_http_error`` matches case-insensitively — so this
    body maps to plain ``YahooApiError``, not ``SymbolNotFoundError``,
    despite the endpoint being unambiguously a symbol-lookup miss. See
    ``tests/test_api_ticker.py::test_ticker_ratings_top_not_found_raises_yahoo_api_error``
    for the confirming behavioral test.
    """

    payload = _load_json(_CORPUS_RATINGS_TOP_DIR / "RY.TO.json")
    assert set(payload.keys()) == {"detail"}
    assert "not found" not in payload["detail"].lower()
    assert "no top ratings found" in payload["detail"].lower()


def _ratings_top_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"ratings-top[{index}]", dict(record))
        for index, record in enumerate(ratings_top_records())
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _ratings_top_cases(),
    ids=[case_id for case_id, _payload in _ratings_top_cases()],
)
def test_ratings_top_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every valid ratings-top capture validates with no extras anywhere."""

    del case_id
    result = TopRatingsResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"TopRatingsResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_ratings_top_required_field_set_matches_corpus_universal_keys() -> None:
    """TopRatingsResult's required fields match the corpus-measured universal keys.

    Thin evidence: only 2 records back this gate (see the module
    docstring).
    """

    report = collect_presence(ratings_top_records(), kind_of=quote_type_lookup_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in TopRatingsResult.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_RATINGS_TOP_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys
    assert required_aliases == {"dir", "fin_score", "mm", "pt"}


# ---------------------------------------------------------------------------
# alphabetical field order (template enforcement)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_cls",
    [AnalystResult, TopRatingsResult],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[YahooModel],
) -> None:
    """Template enforcement: every model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
