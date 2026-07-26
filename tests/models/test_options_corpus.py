"""The OptionChain/OptionExpiration/OptionContract corpus coverage gate.

Every options capture's ``optionChain.result[0]`` must validate as
:class:`OptionChain` with nothing landing on ``model_extra`` anywhere in the
model tree. This is the deepest nesting exercised so far: the walker must
reach through ``OptionChain.options`` (a list of ``OptionExpiration``), each
expiration's ``calls``/``puts`` (lists of ``OptionContract``), and the
embedded ``quote`` (a full :class:`~yoghurt.models.quote.Quote` — the first
cross-model reuse in this package). This file also pins the required-field
sets for ``OptionContract`` (from the option-contracts stream) and
``OptionChain`` (from the option-chains stream) to their corpus-measured
universal keys, and enforces alphabetical field declaration order for every
model added in this module.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import collect_nested_extras
from tools.fields_report import (
    CORPUS_ROOT,
    collect_presence,
    contract_kind,
    option_chain_records,
    option_contract_records,
)
from yoghurt.models.options import OptionChain, OptionContract, OptionExpiration

_CORPUS_OPTIONS_DIR = CORPUS_ROOT / "options"

_EXPECTED_CORPUS_FILE_COUNT = 4  # +1: ZZZZXYZQ invalid-symbol probe (P4-1)
_EXPECTED_CONTRACT_COUNT = 365
_EXPECTED_CHAIN_COUNT = 3
_EXPECTED_CONTRACT_REQUIRED_FIELD_COUNT = 14
_EXPECTED_CHAIN_REQUIRED_FIELD_COUNT = 6


def _load_json(
    path: Any,  # ruff:ignore[any-type] - corpus JSON is untyped.
) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _chain_cases() -> list[tuple[str, dict[str, Any]]]:
    """Every (case-id, optionChain.result[0]) pair across options captures."""

    cases: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(_CORPUS_OPTIONS_DIR.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = (
            payload.get("optionChain", {}).get("result") or []
        )
        if results:
            cases.append((path.name, results[0]))
    return cases


_CHAIN_CASES = _chain_cases()


def _flatten_extras(nested: dict[str, dict[str, object]]) -> list[str]:
    """Flatten a nested-extras map to sorted ``path.key`` strings."""

    return sorted(
        f"{path}.{key}" if path else key
        for path, extras in nested.items()
        for key in extras
    )


def test_options_corpus_has_expected_file_count() -> None:
    """Sanity check on the fixture set: 3 chains (AAPL/MSFT/SPY) + ZZZZXYZQ (empty)."""

    files = sorted(_CORPUS_OPTIONS_DIR.glob("*.json"))
    assert len(files) == _EXPECTED_CORPUS_FILE_COUNT
    # ZZZZXYZQ's optionChain.result is [] (valid-empty, not a chain to
    # validate) so it is excluded from _CHAIN_CASES; see
    # test_options_invalid_symbol_capture_is_a_valid_empty_result below.
    assert len(_CHAIN_CASES) == _EXPECTED_CHAIN_COUNT


def test_options_invalid_symbol_capture_is_a_valid_empty_result() -> None:
    """The ZZZZXYZQ probe (P4-1) is HTTP 200 with an empty optionChain.result.

    Corpus-confirmed live 2026-07-05: not an error payload. This is exactly
    the empty-``result``-list shape ``yoghurt.api.Ticker.options`` already
    raises ``SymbolNotFoundError`` for (pre-existing behavior, now backed
    by a real capture instead of only the shape being assumed).
    """

    payload = _load_json(_CORPUS_OPTIONS_DIR / "ZZZZXYZQ.json")
    assert payload == {"optionChain": {"result": [], "error": None}}


def test_contract_stream_has_expected_record_count() -> None:
    """365 call+put contracts across the 3 captures (evidence base for requiredness)."""

    contracts = list(option_contract_records())
    assert len(contracts) == _EXPECTED_CONTRACT_COUNT


def test_chain_stream_has_expected_record_count() -> None:
    """3 chain-level records, one per options capture."""

    chains = list(option_chain_records())
    assert len(chains) == _EXPECTED_CHAIN_COUNT


@pytest.mark.parametrize(
    "chain_record",
    [record for _case_id, record in _CHAIN_CASES],
    ids=[case_id for case_id, _record in _CHAIN_CASES],
)
def test_chain_validates_with_no_extra_fields(
    chain_record: dict[str, object],
) -> None:
    """Every options capture validates as OptionChain with no extras anywhere.

    The nested-extras walker checks the whole model tree: OptionChain's
    ``options`` (a list of ``OptionExpiration``), each expiration's ``calls``
    and ``puts`` (lists of ``OptionContract``), and the embedded ``quote``
    (a full ``Quote``) — the deepest nesting and the first cross-model reuse
    exercised by any corpus gate in this package.
    """

    chain = OptionChain.model_validate(chain_record)
    nested = collect_nested_extras(chain)
    message = (
        f"OptionChain gained unmodeled fields (drift alarm): {_flatten_extras(nested)}"
    )
    assert not nested, message


def test_contract_required_field_set_matches_corpus_universal_keys() -> None:
    """Live evidence loosens bid below the corpus-universal required set.

    ``volume`` is corpus-optional; ``bid`` was live-observed absent on a
    ``fr-FR``/``FR`` contract despite being corpus-universal.
    """

    report = collect_presence(option_contract_records(), kind_of=contract_kind)
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in OptionContract.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_CONTRACT_REQUIRED_FIELD_COUNT
    assert required_aliases < universal_keys
    assert universal_keys - required_aliases == {"bid"}
    assert {"bid", "volume"}.isdisjoint(required_aliases)


def test_chain_required_field_set_matches_corpus_universal_keys() -> None:
    """OptionChain's required fields are exactly the corpus-measured universal keys."""

    report = collect_presence(option_chain_records(), kind_of=lambda _r: "chain")
    universal_keys = {key for key, field in report.fields.items() if field.universal}

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in OptionChain.model_fields.items()
        if field_info.is_required()
    }

    assert len(universal_keys) == _EXPECTED_CHAIN_REQUIRED_FIELD_COUNT
    assert required_aliases == universal_keys


def test_expiration_fields_are_all_present_in_every_capture() -> None:
    """OptionExpiration's four keys are universal across every options[] entry.

    There is no separate fields_report stream for the expiration level (only
    one entry per capture in this corpus), so this directly checks the raw
    JSON instead of going through PresenceReport.
    """

    for path in sorted(_CORPUS_OPTIONS_DIR.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = (
            payload.get("optionChain", {}).get("result") or []
        )
        for result in results:
            options: list[dict[str, Any]] = result.get("options") or []
            for option in options:
                assert set(option.keys()) == {
                    "calls",
                    "expirationDate",
                    "hasMiniOptions",
                    "puts",
                }

    required_aliases = {
        (field_info.alias or name)
        for name, field_info in OptionExpiration.model_fields.items()
        if field_info.is_required()
    }
    assert required_aliases == {
        "calls",
        "expirationDate",
        "hasMiniOptions",
        "puts",
    }


@pytest.mark.parametrize(
    "model_cls",
    [OptionContract, OptionExpiration, OptionChain],
    ids=lambda cls: cls.__name__,
)
def test_model_fields_are_declared_in_alphabetical_order(
    model_cls: type[OptionContract],
) -> None:
    """Template enforcement: every new model here declares fields alphabetically."""

    names = list(model_cls.model_fields)
    assert names == sorted(names)
