"""Batch 3e-2 corpus gate: screener-instrument-fields/timeseries-fields/discover.

Every relevant corpus capture must validate against its model with nothing
landing on ``model_extra`` anywhere in the model tree, and each model's
required-field set is pinned to its corpus-measured universal keys via
``tools.fields_report``.

``screener-discover`` additionally documents the reuse-decision evidence for
:class:`~yoghurt.models.screener_meta.ScreenerDiscoverQuote`: see
``test_screener_discover_quotes_fail_validation_against_quote`` for the
script-validated finding that :class:`~yoghurt.models.quote.Quote` cannot be
reused (validation itself fails: 8 of ``Quote``'s required fields are
missing outright on every row).

``screener-predefined`` is intentionally NOT gated here: per the module
docstring's "screener-predefined" section, its ``records`` field is a
deliberately untyped ``list[dict[str, object]]`` (an open-ended,
screener-id-specific field subset), so there is no fixed row model to
corpus-gate. Its envelope-level fields (``ScreenerPredefinedResult``,
``ScreenerCriteriaMeta``, ``ScreenerCriteriaMetaFilter``) are still
covered below.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import (
    CORPUS_ROOT,
    collect_presence,
    screener_discover_records,
    screener_instrument_fields_kind,
    screener_instrument_fields_records,
    timeseries_fields_records,
)
from yoghurt.models.quote import Quote
from yoghurt.models.screener_meta import (
    ScreenerDiscoverQuote,
    ScreenerDiscoverResult,
    ScreenerField,
    ScreenerInstrumentFieldsResult,
    ScreenerPredefinedResult,
    TimeseriesFieldsResult,
)

if TYPE_CHECKING:
    from yoghurt.models._base import YahooModel

_CORPUS_SCREENER_INSTRUMENT_FIELDS_DIR = CORPUS_ROOT / "screener-instrument-fields"
_CORPUS_TIMESERIES_FIELDS_DIR = CORPUS_ROOT / "timeseries-fields"
_CORPUS_SCREENER_DISCOVER_DIR = CORPUS_ROOT / "screener-discover"
_CORPUS_SCREENER_PREDEFINED_DIR = CORPUS_ROOT / "screener-predefined"

_EXPECTED_SCREENER_INSTRUMENT_FIELDS_FILE_COUNT = 21
_EXPECTED_SCREENER_INSTRUMENT_FIELDS_RECORD_COUNT = 1666
_EXPECTED_TIMESERIES_FIELDS_FILE_COUNT = 1
_EXPECTED_TIMESERIES_FIELDS_RECORD_COUNT = 13
_EXPECTED_SCREENER_DISCOVER_FILE_COUNT = 1
_EXPECTED_SCREENER_DISCOVER_QUOTE_COUNT = 44
_EXPECTED_SCREENER_PREDEFINED_FILE_COUNT = 5

_EXPECTED_SCREENER_FIELD_REQUIRED_FIELD_COUNT = 9
_EXPECTED_SCREENER_DISCOVER_QUOTE_REQUIRED_FIELD_COUNT = 29
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
# screener-instrument-fields
# ---------------------------------------------------------------------------


def test_screener_instrument_fields_corpus_has_expected_file_count() -> None:
    """Sanity check: 21 instrument captures."""

    files = sorted(_CORPUS_SCREENER_INSTRUMENT_FIELDS_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_SCREENER_INSTRUMENT_FIELDS_FILE_COUNT


def test_screener_instrument_fields_stream_has_expected_record_count() -> None:
    """1666 field specs across all 21 instrument captures."""

    records = list(screener_instrument_fields_records())
    assert len(records) == _EXPECTED_SCREENER_INSTRUMENT_FIELDS_RECORD_COUNT


def _screener_instrument_fields_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (path.name, _load_json(path)["finance"]["result"][0])
        for path in sorted(_CORPUS_SCREENER_INSTRUMENT_FIELDS_DIR.glob("*.json"))
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _screener_instrument_fields_cases(),
    ids=[case_id for case_id, _payload in _screener_instrument_fields_cases()],
)
def test_screener_instrument_fields_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every instrument capture validates with no extras anywhere in the tree."""

    del case_id
    result = ScreenerInstrumentFieldsResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        "ScreenerInstrumentFieldsResult gained unmodeled fields "
        f"(drift alarm): {_flatten_extras(nested)}"
    )
    assert not nested, message


def test_screener_field_required_fields_are_universal() -> None:
    """ScreenerField's required set matches the corpus-universal keys."""

    required_aliases = _required_aliases(ScreenerField)
    assert len(required_aliases) == _EXPECTED_SCREENER_FIELD_REQUIRED_FIELD_COUNT

    report = collect_presence(
        screener_instrument_fields_records(), kind_of=screener_instrument_fields_kind
    )
    universal_keys = {key for key, field in report.fields.items() if field.universal}
    assert required_aliases <= universal_keys


def test_screener_instrument_fields_optional_keys_are_rare_and_multi_instrument() -> (
    None
):
    """enableSearch/searchSource/dependFor/dependentField are genuinely rare.

    Spread across several instruments each, not concentrated on a single
    one (correcting an earlier draft of this module's docstring, which
    over-claimed a single-instrument concentration).
    """

    report = collect_presence(
        screener_instrument_fields_records(), kind_of=screener_instrument_fields_kind
    )
    for key, expected_instrument_count in (
        ("enableSearch", 12),
        ("searchSource", 12),
        ("dependFor", 7),
        ("dependentField", 5),
    ):
        field = report.fields[key]
        assert not field.universal
        assert len(field.quote_types) == expected_instrument_count


# ---------------------------------------------------------------------------
# timeseries-fields
# ---------------------------------------------------------------------------


def test_timeseries_fields_corpus_has_expected_file_count() -> None:
    """Sanity check: 1 thin capture."""

    files = sorted(_CORPUS_TIMESERIES_FIELDS_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_TIMESERIES_FIELDS_FILE_COUNT


def test_timeseries_fields_stream_has_expected_record_count() -> None:
    """13 field-class rows in the single capture."""

    records = list(timeseries_fields_records())
    assert len(records) == _EXPECTED_TIMESERIES_FIELDS_RECORD_COUNT


def test_timeseries_fields_validates_with_no_extra_fields() -> None:
    """The single capture validates as TimeseriesFieldsResult with no extras."""

    payload = _load_json(_CORPUS_TIMESERIES_FIELDS_DIR / "default.json")
    result = TimeseriesFieldsResult.model_validate(
        payload["timeseriesfields"]["result"][0]
    )
    nested = collect_nested_extras(result)
    message = (
        f"TimeseriesFieldsResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


# ---------------------------------------------------------------------------
# screener-discover
# ---------------------------------------------------------------------------


def test_screener_discover_corpus_has_expected_file_count() -> None:
    """Sanity check: 1 capture (9 idea modules, 44 quote rows)."""

    files = sorted(_CORPUS_SCREENER_DISCOVER_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_SCREENER_DISCOVER_FILE_COUNT


def test_screener_discover_stream_has_expected_record_count() -> None:
    """44 quote rows in the single capture."""

    records = list(screener_discover_records())
    assert len(records) == _EXPECTED_SCREENER_DISCOVER_QUOTE_COUNT


def test_screener_discover_validates_with_no_extra_fields() -> None:
    """The single capture validates as ScreenerDiscoverResult with no extras."""

    payload = _load_json(_CORPUS_SCREENER_DISCOVER_DIR / "default.json")
    result = ScreenerDiscoverResult.model_validate(payload["finance"]["result"])
    nested = collect_nested_extras(result)
    message = (
        f"ScreenerDiscoverResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_screener_discover_quotes_fail_validation_against_quote() -> None:
    """Reuse-decision evidence: Quote validation fails outright on these rows.

    Unlike ``MarketSummaryQuote`` (whose rows are zero-extras but fail on
    requiredness), every screener-discover quote row is missing 7 of
    ``Quote``'s required fields outright, so ``Quote.model_validate``
    raises rather than merely landing extras. (``fiftyTwoWeekLowChangePercent``
    is equally absent but optional on ``Quote`` since the 2026-07-05 live
    loosening, so it no longer appears in this pin.)
    """

    quote_required_aliases = _required_aliases(Quote)
    assert len(quote_required_aliases) == _QUOTE_REQUIRED_FIELD_COUNT

    report = collect_presence(
        screener_discover_records(),
        kind_of=lambda record: str(record.get("quoteType", "")),
    )
    universal_keys = {key for key, field in report.fields.items() if field.universal}
    missing_from_universal = quote_required_aliases - universal_keys
    assert missing_from_universal == {
        "currency",
        "fiftyTwoWeekHigh",
        "fiftyTwoWeekHighChange",
        "fiftyTwoWeekHighChangePercent",
        "fiftyTwoWeekLow",
        "fiftyTwoWeekLowChange",
        "fiftyTwoWeekRange",
    }

    for record in screener_discover_records():
        with pytest.raises(Exception, match="validation error"):
            Quote.model_validate(record)


def test_screener_discover_quote_required_fields_are_universal() -> None:
    """ScreenerDiscoverQuote's required set matches the corpus-universal keys."""

    required_aliases = _required_aliases(ScreenerDiscoverQuote)
    assert (
        len(required_aliases) == _EXPECTED_SCREENER_DISCOVER_QUOTE_REQUIRED_FIELD_COUNT
    )

    report = collect_presence(
        screener_discover_records(),
        kind_of=lambda record: str(record.get("quoteType", "")),
    )
    universal_keys = {key for key, field in report.fields.items() if field.universal}
    assert required_aliases <= universal_keys


def test_screener_discover_idea_section_records_stay_untyped() -> None:
    """Each idea module's records union to only a shared ticker field.

    Confirms the module docstring's evidence for leaving
    ``ScreenerDiscoverIdeaSection.records`` as ``list[dict[str, object]]``.
    """

    payload = _load_json(_CORPUS_SCREENER_DISCOVER_DIR / "default.json")
    result = ScreenerDiscoverResult.model_validate(payload["finance"]["result"])
    key_sets: list[set[str]] = [
        {key for record in section.records for key in record}
        for section in result.sections.neo_investment_ideas.screeners_list
    ]
    common = set[str].intersection(*key_sets)
    assert common == {"ticker"}


# ---------------------------------------------------------------------------
# screener-predefined (envelope-level only)
# ---------------------------------------------------------------------------


def test_screener_predefined_corpus_has_expected_file_count() -> None:
    """Sanity check: 5 predefined-screener captures."""

    files = sorted(_CORPUS_SCREENER_PREDEFINED_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_SCREENER_PREDEFINED_FILE_COUNT


def _screener_predefined_cases() -> list[tuple[str, dict[str, Any]]]:
    return [
        (path.name, _load_json(path)["finance"]["result"][0])
        for path in sorted(_CORPUS_SCREENER_PREDEFINED_DIR.glob("*.json"))
    ]


@pytest.mark.parametrize(
    ("case_id", "payload"),
    _screener_predefined_cases(),
    ids=[case_id for case_id, _payload in _screener_predefined_cases()],
)
def test_screener_predefined_envelope_validates_with_no_extra_fields(
    case_id: str, payload: dict[str, Any]
) -> None:
    """Every capture's envelope fields validate with no extras anywhere.

    ``records`` is deliberately untyped (``list[dict[str, object]]``), so
    this only proves the envelope-level fields around it are fully typed;
    see the module docstring's "screener-predefined" section.
    """

    del case_id
    result = ScreenerPredefinedResult.model_validate(payload)
    nested = collect_nested_extras(result)
    message = (
        f"ScreenerPredefinedResult gained unmodeled fields (drift alarm): "
        f"{_flatten_extras(nested)}"
    )
    assert not nested, message


def test_screener_predefined_records_share_only_five_common_fields() -> None:
    """The 5 screener ids' records union to only 5 shared fields.

    Confirms the module docstring's evidence for leaving
    ``ScreenerPredefinedResult.records`` as ``list[dict[str, object]]``
    rather than a fixed row model.
    """

    key_sets: list[set[str]] = []
    for _case_id, payload in _screener_predefined_cases():
        key_sets.append({key for record in payload["records"] for key in record})
    common = set[str].intersection(*key_sets)
    assert common == {
        "companyName",
        "regularMarketChange",
        "regularMarketChangePercent",
        "regularMarketPrice",
        "ticker",
    }
