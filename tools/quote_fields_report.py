"""Report which quote-response fields Yahoo actually sends, and on what.

Run from the repo root:  uv run python -m tools.quote_fields_report

Scans every captured quote-response record in the corpus and reports, per
field key: which quoteTypes it was observed on, how many records had it out
of the total scanned, and whether it is universal (present on every record
regardless of quoteType). This tool is permanent: re-run it after corpus
refreshes to regenerate applicability evidence for the typed quote model.
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


def collect_field_presence(corpus_dir: Path) -> dict[str, FieldPresence]:
    """Compute per-field applicability across every quote corpus record.

    Returns:
        dict[str, FieldPresence]: Field key to its applicability evidence,
        keyed by Yahoo's exact wire spelling.
    """

    records = _iter_quote_records(corpus_dir)
    total = len(records)
    quote_types_by_field: dict[str, set[str]] = {}
    counts: dict[str, int] = {}
    for record in records:
        quote_type = str(record.get("quoteType", ""))
        for key in record:
            quote_types_by_field.setdefault(key, set()).add(quote_type)
            counts[key] = counts.get(key, 0) + 1

    return {
        key: FieldPresence(
            quote_types=tuple(sorted(quote_types_by_field[key])),
            count=counts[key],
            total=total,
            universal=counts[key] == total,
        )
        for key in sorted(counts)
    }


def _print_table(presence: dict[str, FieldPresence]) -> None:
    """Print a human-readable, sorted applicability table to stdout."""

    for key in sorted(presence):
        field = presence[key]
        marker = "universal" if field.universal else ",".join(field.quote_types)
        print(f"{key}\t{field.count}/{field.total}\t{marker}")


def _print_json(presence: dict[str, FieldPresence]) -> None:
    """Print the full applicability report as JSON to stdout."""

    payload = {
        key: {
            "quoteTypes": list(field.quote_types),
            "count": field.count,
            "total": field.total,
            "universal": field.universal,
        }
        for key, field in sorted(presence.items())
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    """Collect and print the quote field applicability report.

    Returns:
        int: Process exit code.
    """

    presence = collect_field_presence(CORPUS_DIR)
    if "--json" in sys.argv[1:]:
        _print_json(presence)
    else:
        _print_table(presence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
