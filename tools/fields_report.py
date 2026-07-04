"""Report which response fields Yahoo actually sends, and on what.

Run from the repo root:  uv run python -m tools.fields_report <stream>

Scans a corpus record stream and reports, per field key: which kinds it
was observed on, how many records had it out of the total scanned (overall
and per kind), and whether it is universal (present on every record
regardless of kind). Per-kind counts matter because the corpus is skewed
(a couple of CRYPTOCURRENCY records vs many EQUITY records): a field can be
universal within its own kind while looking rare overall. This tool is
permanent: re-run it after corpus refreshes to regenerate applicability
evidence for the typed response models.

Streams:

- ``quote``: quoteResponse.result records; kind = quoteType.
- ``chart-meta``: chart.result[0].meta per valid chart capture; kind =
  instrumentType.
- ``spark-meta``: spark.result[].response[].meta records; kind =
  instrumentType.
- ``chart-and-spark-meta``: chart-meta and spark-meta combined (Task 3
  needs universality evidence across both meta shapes at once).
- ``option-contracts``: calls+puts across every options capture; kind =
  "call"/"put".
- ``option-chains``: optionChain.result[0] records; kind = "chain".
- ``quote-summary:<module>``: that module's payload per valid quote-summary
  capture (for example ``quote-summary:price``); kind = the same capture's
  own ``quoteType`` module payload (``quoteType.quoteType``), so applicability
  never depends on filename conventions.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
CORPUS_ROOT: Final[Path] = REPO_ROOT / "tests" / "fixtures" / "corpus"
CORPUS_DIR: Final[Path] = CORPUS_ROOT / "quote"
_INVALID_SYMBOL_STEM: Final[str] = "ZZZZXYZQ"


@dataclass(frozen=True, slots=True)
class FieldPresence:
    """Applicability evidence for one response field key."""

    quote_types: tuple[str, ...]  # sorted, distinct kinds bearing this key
    count: int  # records containing the key
    total: int  # all records scanned
    universal: bool  # present in 100% of ALL records
    type_counts: tuple[tuple[str, int], ...]  # per kind: records with key


@dataclass(frozen=True, slots=True)
class PresenceReport:
    """Full applicability report: per-field evidence plus per-kind totals."""

    fields: dict[str, FieldPresence]  # field key -> its applicability evidence
    records_per_kind: dict[str, int]  # kind -> records of that kind

    def universal_for(self, key: str, quote_type: str) -> bool:
        """Whether ``key`` is present on every scanned record of ``quote_type``.

        Returns:
            bool: True when every record of that kind carries the key;
            False when any record lacks it, the key was never observed, or
            no records of that kind were scanned.
        """

        total = self.records_per_kind.get(quote_type, 0)
        field = self.fields.get(key)
        if total == 0 or field is None:
            return False
        return dict(field.type_counts).get(quote_type, 0) == total


class _KindTagged(Mapping[str, Any]):
    """A record wrapper carrying a kind that isn't derivable from itself.

    Option contracts don't self-report "call" vs "put"; the corpus walker
    knows which list it read the record from, so it tags the record here
    instead of forcing ``collect_presence`` to special-case that stream.
    """

    __slots__ = ("_record", "kind")

    def __init__(self, record: Mapping[str, Any], kind: str) -> None:
        self._record = record
        self.kind = kind

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401 - Mapping value type
        return self._record[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._record)

    def __len__(self) -> int:
        return len(self._record)


def collect_presence(
    records: Iterable[Mapping[str, Any]],
    *,
    kind_of: Callable[[Mapping[str, Any]], str],
) -> PresenceReport:
    """Compute per-field applicability across a stream of records.

    ``kind_of`` groups records into applicability buckets (quoteType,
    instrumentType, call/put, ...); records where it raises or returns a
    falsy value group under ``"?"``.

    Returns:
        PresenceReport: Per-field evidence keyed by Yahoo's exact wire
        spelling, plus how many records of each kind were scanned.
    """

    total = 0
    records_per_kind: dict[str, int] = {}
    type_counts: dict[str, dict[str, int]] = {}
    counts: dict[str, int] = {}
    for record in records:
        total += 1
        try:
            kind = kind_of(record) or "?"
        except Exception:  # noqa: BLE001 - any failure to classify is "?"
            kind = "?"
        records_per_kind[kind] = records_per_kind.get(kind, 0) + 1
        for key in record:
            per_type = type_counts.setdefault(key, {})
            per_type[kind] = per_type.get(kind, 0) + 1
            counts[key] = counts.get(key, 0) + 1

    fields = {
        key: FieldPresence(
            quote_types=tuple(sorted(type_counts[key])),
            count=counts[key],
            total=total,
            universal=counts[key] == total,
            type_counts=tuple(sorted(type_counts[key].items())),
        )
        for key in sorted(counts)
    }
    return PresenceReport(
        fields=fields,
        records_per_kind=dict(sorted(records_per_kind.items())),
    )


def _quote_kind(record: Mapping[str, Any]) -> str:
    return str(record.get("quoteType", ""))


def quote_records(corpus_dir: Path = CORPUS_DIR) -> Iterator[dict[str, Any]]:
    """Yield every quoteResponse.result record from every quote corpus file."""

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = (
            payload.get("quoteResponse", {}).get("result") or []
        )
        yield from results


def collect_field_presence(corpus_dir: Path = CORPUS_DIR) -> PresenceReport:
    """Compute per-field applicability across every quote corpus record.

    Returns:
        PresenceReport: Per-field evidence keyed by Yahoo's exact wire
        spelling, plus how many records of each quoteType were scanned.
    """

    return collect_presence(quote_records(corpus_dir), kind_of=_quote_kind)


def _instrument_kind(record: Mapping[str, Any]) -> str:
    return str(record.get("instrumentType", ""))


def _load_json(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def chart_meta_records() -> Iterator[dict[str, Any]]:
    """Yield each valid chart capture's ``chart.result[0].meta``.

    Skips the deliberate invalid-symbol probe and any capture with no
    chart result (an enveloped error, no meta to report on).
    """

    corpus_dir = CORPUS_ROOT / "chart"
    for path in sorted(corpus_dir.glob("*.json")):
        if path.stem == _INVALID_SYMBOL_STEM:
            continue
        payload = _load_json(path)
        results: list[dict[str, Any]] = payload.get("chart", {}).get("result") or []
        if not results:
            continue
        meta: dict[str, Any] | None = results[0].get("meta")
        if meta:
            yield meta


def spark_meta_records() -> Iterator[dict[str, Any]]:
    """Yield every ``spark.result[].response[].meta`` record."""

    corpus_dir = CORPUS_ROOT / "spark"
    for path in sorted(corpus_dir.glob("*.json")):
        if path.stem == _INVALID_SYMBOL_STEM:
            continue
        payload = _load_json(path)
        results: list[dict[str, Any]] = payload.get("spark", {}).get("result") or []
        for result in results:
            responses: list[dict[str, Any]] = result.get("response") or []
            for response in responses:
                meta: dict[str, Any] | None = response.get("meta")
                if meta:
                    yield meta


def chart_and_spark_meta_records() -> Iterator[dict[str, Any]]:
    """Yield chart-meta records followed by spark-meta records."""

    yield from chart_meta_records()
    yield from spark_meta_records()


def collect_chart_and_spark_meta_presence() -> PresenceReport:
    """Compute per-field applicability across the combined chart+spark meta stream.

    This is the evidence base for :class:`~yoghurt.models.chart.ChartMeta`'s
    requiredness (see ``tests/models/test_chart_corpus.py``), mirroring
    :func:`collect_field_presence`'s role for the quote model.

    Returns:
        PresenceReport: Per-field evidence keyed by Yahoo's exact wire
        spelling, plus how many records of each instrumentType were scanned.
    """

    return collect_presence(chart_and_spark_meta_records(), kind_of=_instrument_kind)


def option_contract_records() -> Iterator[_KindTagged]:
    """Yield every call/put contract across every options capture.

    Each yielded record is tagged with its kind ("call" or "put") via
    :class:`_KindTagged`, since that distinction comes from which list the
    walker read the contract from, not from any field on the contract
    itself.
    """

    corpus_dir = CORPUS_ROOT / "options"
    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = (
            payload.get("optionChain", {}).get("result") or []
        )
        for result in results:
            options: list[dict[str, Any]] = result.get("options") or []
            for option in options:
                calls: list[dict[str, Any]] = option.get("calls") or []
                for call in calls:
                    yield _KindTagged(call, "call")
                puts: list[dict[str, Any]] = option.get("puts") or []
                for put in puts:
                    yield _KindTagged(put, "put")


def contract_kind(record: Mapping[str, Any]) -> str:
    """Read the call/put kind off a record produced by ``option_contract_records``.

    Returns:
        str: ``"call"`` or ``"put"``, or ``"?"`` for an untagged record.
    """

    return record.kind if isinstance(record, _KindTagged) else "?"


def option_chain_records() -> Iterator[dict[str, Any]]:
    """Yield each options capture's ``optionChain.result[0]``."""

    corpus_dir = CORPUS_ROOT / "options"
    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = (
            payload.get("optionChain", {}).get("result") or []
        )
        if results:
            yield results[0]


CORPUS_QUOTE_SUMMARY_DIR: Final[Path] = CORPUS_ROOT / "quote-summary"


class _KindTaggedModule(Mapping[str, Any]):
    """A quote-summary module payload tagged with its capture's quoteType.

    A module payload (``price``, ``assetProfile``, and so on) doesn't
    self-report the capture's quoteType; the sibling ``quoteType`` module
    in the same capture does, so :func:`quote_summary_module_records` reads
    it once per capture and tags every module payload from that capture
    with it.
    """

    __slots__ = ("_record", "kind")

    def __init__(self, record: Mapping[str, Any], kind: str) -> None:
        self._record = record
        self.kind = kind

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401 - Mapping value type
        return self._record[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._record)

    def __len__(self) -> int:
        return len(self._record)


def quote_summary_module_records(
    module: str, corpus_dir: Path = CORPUS_QUOTE_SUMMARY_DIR
) -> Iterator[_KindTaggedModule]:
    """Yield ``module``'s payload from every valid quote-summary capture.

    Skips captures with no ``quoteSummary.result`` (the deliberate
    invalid-symbol probe) and captures where ``module`` itself is absent
    (module availability varies by quoteType). Each yielded payload is
    tagged with the capture's own quoteType, read from that same capture's
    sibling ``quoteType`` module payload (``quoteType.quoteType``) rather
    than any filename or cross-corpus mapping, so tagging stays correct
    even if captures are renamed.

    Args:
        module: The quote-summary module name, wire-spelled (for example
            ``"price"``, ``"assetProfile"``).
        corpus_dir: Directory of quote-summary corpus captures.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = (
            payload.get("quoteSummary", {}).get("result") or []
        )
        if not results:
            continue
        modules = results[0]
        module_payload = modules.get(module)
        if module_payload is None:
            continue
        kind = str(modules.get("quoteType", {}).get("quoteType", ""))
        yield _KindTaggedModule(module_payload, kind)


def quote_summary_module_kind(record: Mapping[str, Any]) -> str:
    """Read the quoteType kind off a record from ``quote_summary_module_records``.

    Returns:
        str: The capture's quoteType (for example ``"EQUITY"``), or ``"?"``
        for an untagged record.
    """

    return record.kind if isinstance(record, _KindTaggedModule) else "?"


_STREAMS: Final[dict[str, Callable[[], Iterator[Mapping[str, Any]]]]] = {
    "quote": quote_records,
    "chart-meta": chart_meta_records,
    "spark-meta": spark_meta_records,
    "chart-and-spark-meta": chart_and_spark_meta_records,
    "option-contracts": option_contract_records,
    "option-chains": option_chain_records,
}

_KIND_OF: Final[dict[str, Callable[[Mapping[str, Any]], str]]] = {
    "quote": _quote_kind,
    "chart-meta": _instrument_kind,
    "spark-meta": _instrument_kind,
    "chart-and-spark-meta": _instrument_kind,
    "option-contracts": contract_kind,
    "option-chains": lambda _record: "chain",
}

_QUOTE_SUMMARY_PREFIX: Final[str] = "quote-summary:"


def _print_table(report: PresenceReport) -> None:
    """Print a human-readable, sorted applicability table to stdout."""

    for key in sorted(report.fields):
        field = report.fields[key]
        marker = "universal" if field.universal else ",".join(field.quote_types)
        print(f"{key}\t{field.count}/{field.total}\t{marker}")


def _print_json(report: PresenceReport) -> None:
    """Print the full applicability report as JSON to stdout."""

    payload = {
        "recordsPerKind": report.records_per_kind,
        "fields": {
            key: {
                "kinds": list(field.quote_types),
                "kindCounts": dict(field.type_counts),
                "count": field.count,
                "total": field.total,
                "universal": field.universal,
            }
            for key, field in sorted(report.fields.items())
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    """Collect and print the applicability report for the requested stream.

    Returns:
        int: Process exit code.
    """

    args = sys.argv[1:]
    as_json = "--json" in args
    positional = [arg for arg in args if arg != "--json"]
    stream = positional[0] if positional else "quote"

    if stream.startswith(_QUOTE_SUMMARY_PREFIX):
        module = stream[len(_QUOTE_SUMMARY_PREFIX) :]
        if not module:
            print("quote-summary: stream requires a module name", file=sys.stderr)
            return 2
        report = collect_presence(
            quote_summary_module_records(module), kind_of=quote_summary_module_kind
        )
    elif stream in _STREAMS:
        report = collect_presence(_STREAMS[stream](), kind_of=_KIND_OF[stream])
    else:
        choices = [*sorted(_STREAMS), f"{_QUOTE_SUMMARY_PREFIX}<module>"]
        print(
            f"unknown stream {stream!r}; choose from: {', '.join(choices)}",
            file=sys.stderr,
        )
        return 2

    if as_json:
        _print_json(report)
    else:
        _print_table(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
