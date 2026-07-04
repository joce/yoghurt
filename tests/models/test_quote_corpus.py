"""The Quote corpus coverage gate: the template test for every Yahoo model.

Every quote corpus record must validate as a :class:`Quote` with nothing
landing on ``model_extra`` — a non-empty ``model_extra`` means Yahoo has
started sending a field this model doesn't know about, and that should
fail loudly rather than silently pass through. This file also pins the
required-field set to the corpus-measured universal keys and checks that
the enum fields round-trip to real enum members, not bare strings.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.quote_fields_report import CORPUS_DIR, collect_field_presence
from yoghurt.models import MarketState, QuoteType
from yoghurt.models.quote import Quote

_CORPUS_QUOTE_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote"
)
_CORPUS_FILES = sorted(_CORPUS_QUOTE_DIR.glob("*.json"))

_EXPECTED_CORPUS_FILE_COUNT = 26
_EXPECTED_CORPUS_RECORD_COUNT = 28
_EXPECTED_MULTI_JSON_RECORD_COUNT = 4


def _records_in(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    results: list[dict[str, object]] = payload.get("quoteResponse", {}).get(
        "result", []
    )
    return results


def _all_corpus_records() -> list[tuple[str, dict[str, object]]]:
    """Every (case-id, record) pair across the whole quote corpus."""

    cases: list[tuple[str, dict[str, object]]] = []
    for path in _CORPUS_FILES:
        for index, record in enumerate(_records_in(path)):
            cases.append((f"{path.name}[{index}]", record))
    return cases


_CASES = _all_corpus_records()


def test_zzzzxyzq_has_zero_records() -> None:
    """The unknown-symbol capture must have exactly zero records, not a skip.

    A silently-skipped empty file would hide the difference between "no
    records to check" and "the parametrization missed this file".
    """

    path = _CORPUS_QUOTE_DIR / "ZZZZXYZQ.json"
    assert path in _CORPUS_FILES
    assert _records_in(path) == []


def test_multi_json_has_four_records() -> None:
    """multi.json is the multi-symbol capture; it must carry all 4 records."""

    records = _records_in(_CORPUS_QUOTE_DIR / "multi.json")
    assert len(records) == _EXPECTED_MULTI_JSON_RECORD_COUNT


def test_corpus_has_expected_record_count() -> None:
    """Sanity check on the fixture set itself: 26 files, 28 total records."""

    assert len(_CORPUS_FILES) == _EXPECTED_CORPUS_FILE_COUNT
    assert len(_CASES) == _EXPECTED_CORPUS_RECORD_COUNT


@pytest.mark.parametrize(
    "record", [record for _case_id, record in _CASES], ids=[c for c, _r in _CASES]
)
def test_record_validates_with_no_extra_fields(record: dict[str, object]) -> None:
    """Every corpus record validates as Quote with model_extra empty.

    A non-empty model_extra is the drift alarm: it means Yahoo sent a
    field this model doesn't know about, and the assertion message lists
    exactly which keys so the alarm is actionable.
    """

    quote = Quote.model_validate(record)
    extra = quote.model_extra
    message = f"Quote gained unmodeled fields (drift alarm): {sorted(extra or {})}"
    assert not extra, message


def test_required_field_set_matches_corpus_universal_keys() -> None:
    """Quote's required fields are exactly the corpus-measured universal keys.

    A required field is one whose ``FieldInfo.is_required()`` is True; its
    wire key is its alias (or its name, for the handful with no override).
    This must equal the set of wire keys present on all 28 corpus records,
    exactly - not a superset, not a subset.
    """

    report = collect_field_presence(CORPUS_DIR)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in Quote.model_fields.items()
        if field_info.is_required()
    }

    assert required_aliases == universal_keys


def test_enum_fields_round_trip_to_enum_members() -> None:
    """quote_type and market_state validate to real enum members, not str."""

    record = _records_in(_CORPUS_QUOTE_DIR / "AAPL.json")[0]
    quote = Quote.model_validate(record)

    assert isinstance(quote.quote_type, QuoteType)
    assert isinstance(quote.market_state, MarketState)
