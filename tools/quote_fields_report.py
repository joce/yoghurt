"""Report which quote-response fields Yahoo actually sends, and on what.

Run from the repo root:  uv run python -m tools.quote_fields_report

Scans every captured quote-response record in the corpus and reports, per
field key: which quoteTypes it was observed on, how many records had it out
of the total scanned (overall and per quoteType), and whether it is
universal (present on every record regardless of quoteType). Per-type
counts matter because the corpus is skewed (a couple of CRYPTOCURRENCY
records vs many EQUITY records): a field can be universal within its own
quoteType while looking rare overall. This tool is permanent: re-run it
after corpus refreshes to regenerate applicability evidence for the typed
quote model.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
CORPUS_DIR: Final[Path] = REPO_ROOT / "tests" / "fixtures" / "corpus" / "quote"


@dataclass(frozen=True, slots=True)
class FieldPresence:
    """Applicability evidence for one quote-response field key."""

    quote_types: tuple[str, ...]  # sorted, distinct quoteTypes bearing this key
    count: int  # records containing the key
    total: int  # all records scanned
    universal: bool  # present in 100% of ALL records
    type_counts: tuple[tuple[str, int], ...]  # per quoteType: records with key


@dataclass(frozen=True, slots=True)
class PresenceReport:
    """Full applicability report: per-field evidence plus per-type totals."""

    fields: dict[str, FieldPresence]  # field key -> its applicability evidence
    records_per_type: dict[str, int]  # quoteType -> records of that type

    def universal_for(self, key: str, quote_type: str) -> bool:
        """Whether ``key`` is present on every scanned record of ``quote_type``.

        Returns:
            bool: True when every record of that quoteType carries the key;
            False when any record lacks it, the key was never observed, or
            no records of that quoteType were scanned.
        """

        total = self.records_per_type.get(quote_type, 0)
        field = self.fields.get(key)
        if total == 0 or field is None:
            return False
        return dict(field.type_counts).get(quote_type, 0) == total


def _iter_quote_records(corpus_dir: Path) -> list[dict[str, object]]:
    """Load every quoteResponse.result record from every corpus file.

    Returns:
        list[dict[str, object]]: All records across every quote corpus file,
        in file-then-list order.
    """

    records: list[dict[str, object]] = []
    for path in sorted(corpus_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        results = payload.get("quoteResponse", {}).get("result", [])
        records.extend(results)
    return records


def collect_field_presence(corpus_dir: Path) -> PresenceReport:
    """Compute per-field applicability across every quote corpus record.

    Returns:
        PresenceReport: Per-field evidence keyed by Yahoo's exact wire
        spelling, plus how many records of each quoteType were scanned.
    """

    records = _iter_quote_records(corpus_dir)
    total = len(records)
    records_per_type: dict[str, int] = {}
    type_counts: dict[str, dict[str, int]] = {}
    counts: dict[str, int] = {}
    for record in records:
        quote_type = str(record.get("quoteType", ""))
        records_per_type[quote_type] = records_per_type.get(quote_type, 0) + 1
        for key in record:
            per_type = type_counts.setdefault(key, {})
            per_type[quote_type] = per_type.get(quote_type, 0) + 1
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
        records_per_type=dict(sorted(records_per_type.items())),
    )


def _print_table(report: PresenceReport) -> None:
    """Print a human-readable, sorted applicability table to stdout."""

    for key in sorted(report.fields):
        field = report.fields[key]
        marker = "universal" if field.universal else ",".join(field.quote_types)
        print(f"{key}\t{field.count}/{field.total}\t{marker}")


def _print_json(report: PresenceReport) -> None:
    """Print the full applicability report as JSON to stdout."""

    payload = {
        "recordsPerType": report.records_per_type,
        "fields": {
            key: {
                "quoteTypes": list(field.quote_types),
                "typeCounts": dict(field.type_counts),
                "count": field.count,
                "total": field.total,
                "universal": field.universal,
            }
            for key, field in sorted(report.fields.items())
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    """Collect and print the quote field applicability report.

    Returns:
        int: Process exit code.
    """

    report = collect_field_presence(CORPUS_DIR)
    if "--json" in sys.argv[1:]:
        _print_json(report)
    else:
        _print_table(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
