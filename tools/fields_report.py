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
- ``calendar-events``: finance.result per calendar-events capture; kind is
  fixed (the module-keyed result shape has no quoteType/instrumentType of
  its own).
- ``calendar-events:earnings``/``calendar-events:ipoEvents``/
  ``calendar-events:secReports``: the inner ``records[]`` rows of that
  module's day buckets (``finance.result.<module>[].records[]``), flattened
  across every calendar-events capture; kind is fixed per module.
- ``quote-type``: quoteType.result[0] per valid quote-type capture (skips
  the invalid-symbol probe); kind = the record's own quoteType.
- ``recommendations-by-symbol``: finance.result[0] per capture; kind is
  looked up from the quote-type corpus's symbol -> quoteType map.
- ``stock-recommender``: the bare payload per capture; kind is looked up
  from the quote-type corpus's symbol -> quoteType map via ``fields.id``.
- ``price-insights``: each per-symbol record in finance.result (itself a
  symbol-keyed mapping, not a list); kind is looked up from the quote-type
  corpus's symbol -> quoteType map.
- ``insights``: finance.result[] per capture; kind is looked up from the
  quote-type corpus's symbol -> quoteType map.
- ``analyst``: the bare payload per valid (non-error) capture; kind is
  looked up from the quote-type corpus's symbol -> quoteType map via the
  capture's own ``symbol_id``-adjacent ``price_movement.ticker`` field.
- ``ratings-top``: the bare payload per valid (non-error) capture; kind is
  looked up from the quote-type corpus's symbol -> quoteType map via the
  capture's ``dir.ticker`` field.
- ``trending``: finance.result[0].quotes[] per capture; kind = the row's
  own quoteType.
- ``market-summary``: marketSummaryResponse.result[] per capture; kind =
  the row's own quoteType.
- ``market-info``: each populated module value of finance.result (a
  mapping, not a list) per capture; kind = the module's own key name
  (``"currencies"``/``"commodities"``).
- ``market-time``: finance.marketTimes[].marketTime[] per capture; kind is
  fixed (this symbol-independent endpoint's rows carry no quoteType/
  instrumentType of their own).
- ``sector``: the whole ``data`` payload per capture (a container gate,
  mirroring ``quote-summary`` with no module argument); kind is fixed.
- ``screener-instrument-fields``: finance.result[0].fields values (one per
  field id) per capture; kind = the instrument, read from the capture's
  own filename (this endpoint's payload carries no instrument marker of
  its own).
- ``timeseries-fields``: timeseriesfields.result[0].timeSeriesDataClass
  rows; kind is fixed (single capture, no per-row classification).
- ``screener-discover``: finance.result.quotes values (a symbol-keyed
  mapping, not a list) per capture; kind = the row's own quoteType.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

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


def quote_summary_records(
    corpus_dir: Path = CORPUS_QUOTE_SUMMARY_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield the whole module set from every valid quote-summary capture.

    Unlike :func:`quote_summary_module_records`, which yields one module's
    payload at a time, this yields ``quoteSummary.result[0]`` whole (every
    module the capture carries) — the evidence base for the
    :class:`~yoghurt.models.summary.QuoteSummary` whole-endpoint container
    gate. Skips captures with no ``quoteSummary.result`` (the deliberate
    invalid-symbol probe).

    Args:
        corpus_dir: Directory of quote-summary corpus captures.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = (
            payload.get("quoteSummary", {}).get("result") or []
        )
        if results:
            yield results[0]


CORPUS_CALENDAR_EVENTS_DIR: Final[Path] = CORPUS_ROOT / "calendar-events"
CORPUS_QUOTE_TYPE_DIR: Final[Path] = CORPUS_ROOT / "quote-type"
CORPUS_RECOMMENDATIONS_DIR: Final[Path] = CORPUS_ROOT / "recommendations-by-symbol"
CORPUS_STOCK_RECOMMENDER_DIR: Final[Path] = CORPUS_ROOT / "stock-recommender"
CORPUS_PRICE_INSIGHTS_DIR: Final[Path] = CORPUS_ROOT / "price-insights"
CORPUS_INSIGHTS_DIR: Final[Path] = CORPUS_ROOT / "insights"


def calendar_events_records(
    corpus_dir: Path = CORPUS_CALENDAR_EVENTS_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield each calendar-events capture's ``finance.result``.

    Kind is fixed (``"calendar-events"``): the result's module-keyed shape
    (``earnings``/``economicEvents``/``ipoEvents``/``secReports``) has no
    quoteType or instrumentType of its own to key applicability by.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        result: dict[str, Any] | None = payload.get("finance", {}).get("result")
        if result:
            yield result


def _calendar_events_module_rows(
    module: str, corpus_dir: Path = CORPUS_CALENDAR_EVENTS_DIR
) -> Iterator[dict[str, Any]]:
    """Yield every inner ``records[]`` row for one calendar-events module.

    Walks ``finance.result.<module>[].records[]`` across every capture:
    the module key is a list of day buckets, each carrying its own
    ``records`` list of the actual event rows. Kind is fixed, same as
    :func:`calendar_events_records`.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        result: dict[str, Any] = payload.get("finance", {}).get("result") or {}
        days: list[dict[str, Any]] = result.get(module) or []
        for day in days:
            rows: list[dict[str, Any]] = day.get("records") or []
            yield from rows


def earnings_records(
    corpus_dir: Path = CORPUS_CALENDAR_EVENTS_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield every ``earnings[].records[]`` row across the calendar-events corpus."""

    yield from _calendar_events_module_rows("earnings", corpus_dir)


def ipo_events_records(
    corpus_dir: Path = CORPUS_CALENDAR_EVENTS_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield every ``ipoEvents[].records[]`` row across the calendar-events corpus."""

    yield from _calendar_events_module_rows("ipoEvents", corpus_dir)


def sec_reports_records(
    corpus_dir: Path = CORPUS_CALENDAR_EVENTS_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield every ``secReports[].records[]`` row across the calendar-events corpus."""

    yield from _calendar_events_module_rows("secReports", corpus_dir)


def _quote_type_symbol_map(
    corpus_dir: Path = CORPUS_QUOTE_TYPE_DIR,
) -> dict[str, str]:
    """Build a symbol -> quoteType map from every valid quote-type capture.

    Returns:
        dict[str, str]: Symbol to quoteType, for every corpus record that
        carries both fields.
    """

    mapping: dict[str, str] = {}
    for path in sorted(corpus_dir.glob("*.json")):
        if path.stem == _INVALID_SYMBOL_STEM:
            continue
        payload = _load_json(path)
        records: list[dict[str, Any]] = payload.get("quoteType", {}).get("result") or []
        for record in records:
            symbol = record.get("symbol")
            quote_type = record.get("quoteType")
            if isinstance(symbol, str) and isinstance(quote_type, str):
                mapping[symbol] = quote_type
    return mapping


def quote_type_records(
    corpus_dir: Path = CORPUS_QUOTE_TYPE_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield each valid quote-type capture's single result record.

    Skips the deliberate invalid-symbol probe (``ZZZZXYZQ``, empty
    ``result: []``). Kind is the record's own ``quoteType`` field.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        if path.stem == _INVALID_SYMBOL_STEM:
            continue
        payload = _load_json(path)
        results: list[dict[str, Any]] = payload.get("quoteType", {}).get("result") or []
        if results:
            yield results[0]


def recommendations_records(
    corpus_dir: Path = CORPUS_RECOMMENDATIONS_DIR,
) -> Iterator[_KindTagged]:
    """Yield each recommendations-by-symbol capture's single result record.

    Kind is looked up from the quote-type corpus's symbol -> quoteType map,
    since this endpoint's own payload carries no type field.
    """

    symbol_kinds = _quote_type_symbol_map()
    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        records: list[dict[str, Any]] = payload.get("finance", {}).get("result") or []
        for record in records:
            symbol = record.get("symbol")
            kind = symbol_kinds.get(symbol, "") if isinstance(symbol, str) else ""
            yield _KindTagged(record, kind)


def stock_recommender_records(
    corpus_dir: Path = CORPUS_STOCK_RECOMMENDER_DIR,
) -> Iterator[_KindTagged]:
    """Yield each stock-recommender capture's bare (non-enveloped) payload.

    Skips the deliberate invalid-symbol probe (``ZZZZXYZQ``): unlike every
    other endpoint in this batch, its 404 body is a bare, differently-shaped
    error payload (``{"message": "Not Found"}``, no ``fields``/``id``/
    ``pathId``) rather than data this model could ever validate — the 404
    is truly unmappable (see ``yoghurt.api.Ticker.stock_recommender``'s
    docstring), so it is not a "record" at all.

    Kind is looked up from the quote-type corpus's symbol -> quoteType map
    via ``fields.id`` (wire-spelled ``"ticker:<symbol>"``).
    """

    symbol_kinds = _quote_type_symbol_map()
    for path in sorted(corpus_dir.glob("*.json")):
        if path.stem == _INVALID_SYMBOL_STEM:
            continue
        payload = _load_json(path)
        entity_id = str(payload.get("fields", {}).get("id", ""))
        symbol = entity_id.removeprefix("ticker:")
        kind = symbol_kinds.get(symbol, "")
        yield _KindTagged(payload, kind)


def price_insights_records(
    corpus_dir: Path = CORPUS_PRICE_INSIGHTS_DIR,
) -> Iterator[_KindTagged]:
    """Yield each price-insights capture's per-symbol record(s).

    ``finance.result`` is itself a symbol-keyed mapping (not a list); this
    yields each symbol's record in turn. Kind is looked up from the
    quote-type corpus's symbol -> quoteType map.
    """

    symbol_kinds = _quote_type_symbol_map()
    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        result: dict[str, Any] = payload.get("finance", {}).get("result") or {}
        for symbol, record in result.items():
            kind = symbol_kinds.get(symbol, "")
            yield _KindTagged(record, kind)


def insights_records(
    corpus_dir: Path = CORPUS_INSIGHTS_DIR,
) -> Iterator[_KindTagged]:
    """Yield each insights capture's result record(s).

    Kind is looked up from the quote-type corpus's symbol -> quoteType map.
    """

    symbol_kinds = _quote_type_symbol_map()
    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        records: list[dict[str, Any]] = payload.get("finance", {}).get("result") or []
        for record in records:
            symbol = record.get("symbol")
            kind = symbol_kinds.get(symbol, "") if isinstance(symbol, str) else ""
            yield _KindTagged(record, kind)


CORPUS_ANALYST_DIR: Final[Path] = CORPUS_ROOT / "analyst"
CORPUS_RATINGS_TOP_DIR: Final[Path] = CORPUS_ROOT / "ratings-top"


def analyst_records(
    corpus_dir: Path = CORPUS_ANALYST_DIR,
) -> Iterator[_KindTagged]:
    """Yield each valid (non-error) analyst capture's bare payload.

    Skips error-shaped captures (``{"detail": ...}``, no ``symbol_id``
    key — both the deliberate invalid-symbol probe and, in this corpus,
    the thin-coverage ``RY.TO`` probe). Kind is looked up from the
    quote-type corpus's symbol -> quoteType map via ``price_movement.ticker``.
    """

    symbol_kinds = _quote_type_symbol_map()
    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        if "symbol_id" not in payload:
            continue
        symbol = str(payload.get("price_movement", {}).get("ticker", ""))
        kind = symbol_kinds.get(symbol, "")
        yield _KindTagged(payload, kind)


def ratings_top_records(
    corpus_dir: Path = CORPUS_RATINGS_TOP_DIR,
) -> Iterator[_KindTagged]:
    """Yield each valid (non-error) ratings-top capture's bare payload.

    Skips error-shaped captures (``{"detail": ...}``, no ``dir`` key — the
    corpus's ``RY.TO`` not-found probe). Kind is looked up from the
    quote-type corpus's symbol -> quoteType map via ``dir.ticker``.
    """

    symbol_kinds = _quote_type_symbol_map()
    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        if "dir" not in payload:
            continue
        symbol = str(payload.get("dir", {}).get("ticker", ""))
        kind = symbol_kinds.get(symbol, "")
        yield _KindTagged(payload, kind)


def quote_type_lookup_kind(record: Mapping[str, Any]) -> str:
    """Read the quoteType kind off a record tagged via the quote-type symbol map.

    Shared by ``recommendations-by-symbol``, ``stock-recommender``,
    ``price-insights``, and ``insights`` streams, none of which self-report
    a quoteType/instrumentType field of their own.

    Returns:
        str: The looked-up quoteType (for example ``"EQUITY"``), or ``"?"``
        for an untagged record.
    """

    return record.kind if isinstance(record, _KindTagged) else "?"


CORPUS_TRENDING_DIR: Final[Path] = CORPUS_ROOT / "trending"
CORPUS_MARKET_SUMMARY_DIR: Final[Path] = CORPUS_ROOT / "market-summary"
CORPUS_MARKET_INFO_DIR: Final[Path] = CORPUS_ROOT / "market-info"
CORPUS_MARKET_TIME_DIR: Final[Path] = CORPUS_ROOT / "market-time"
CORPUS_SECTOR_DIR: Final[Path] = CORPUS_ROOT / "sector"


def trending_records(
    corpus_dir: Path = CORPUS_TRENDING_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield each trending capture's ``finance.result[0].quotes`` rows.

    Kind is each row's own ``quoteType`` field.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = payload.get("finance", {}).get("result") or []
        for result in results:
            quotes: list[dict[str, Any]] = result.get("quotes") or []
            yield from quotes


def market_summary_records(
    corpus_dir: Path = CORPUS_MARKET_SUMMARY_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield each market-summary capture's ``marketSummaryResponse.result`` rows.

    Kind is each row's own ``quoteType`` field.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = (
            payload.get("marketSummaryResponse", {}).get("result") or []
        )
        yield from results


def market_info_records(
    corpus_dir: Path = CORPUS_MARKET_INFO_DIR,
) -> Iterator[_KindTagged]:
    """Yield each market-info capture's populated module tiles.

    ``finance.result`` is a mapping (``currencies``/``commodities`` keys),
    not a list; each populated module value is tagged with its own key name
    (``"currencies"``/``"commodities"``) as its kind, since that is the
    natural applicability grouping for this endpoint's fixed, small module
    set.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        result: dict[str, Any] = payload.get("finance", {}).get("result") or {}
        for module_name, module_payload in result.items():
            if isinstance(module_payload, dict):
                tagged = cast("dict[str, Any]", module_payload)
                yield _KindTagged(tagged, module_name)


def market_info_kind(record: Mapping[str, Any]) -> str:
    """Read the module-name kind off a record from ``market_info_records``.

    Returns:
        str: ``"currencies"``/``"commodities"``, or ``"?"`` for an
        untagged record.
    """

    return record.kind if isinstance(record, _KindTagged) else "?"


def market_time_records(
    corpus_dir: Path = CORPUS_MARKET_TIME_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield each market-time capture's ``finance.marketTimes[].marketTime[]`` rows.

    Kind is fixed (``"market-time"``): this endpoint is symbol-independent
    and its rows carry no quoteType/instrumentType of their own.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        groups: list[dict[str, Any]] = (
            payload.get("finance", {}).get("marketTimes") or []
        )
        for group in groups:
            entries: list[dict[str, Any]] = group.get("marketTime") or []
            yield from entries


def sector_records(corpus_dir: Path = CORPUS_SECTOR_DIR) -> Iterator[dict[str, Any]]:
    """Yield each sector capture's ``data`` payload whole.

    Kind is fixed (``"sector"``): the whole-endpoint container gate mirrors
    :func:`quote_summary_records`, not a per-row applicability stream (this
    endpoint's sub-blocks are evidenced individually via direct corpus
    reads in ``tests/models/test_markets_corpus.py`` instead).
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        data: dict[str, Any] | None = payload.get("data")
        if data:
            yield data


CORPUS_SCREENER_INSTRUMENT_FIELDS_DIR: Final[Path] = (
    CORPUS_ROOT / "screener-instrument-fields"
)
CORPUS_TIMESERIES_FIELDS_DIR: Final[Path] = CORPUS_ROOT / "timeseries-fields"
CORPUS_SCREENER_DISCOVER_DIR: Final[Path] = CORPUS_ROOT / "screener-discover"


def screener_instrument_fields_records(
    corpus_dir: Path = CORPUS_SCREENER_INSTRUMENT_FIELDS_DIR,
) -> Iterator[_KindTagged]:
    """Yield each capture's ``finance.result[0].fields`` values.

    Each field spec is tagged with its instrument, read from the capture's
    own filename (for example ``equity.json`` -> ``"equity"``): this
    endpoint's payload carries no instrument marker of its own.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = payload.get("finance", {}).get("result") or []
        if not results:
            continue
        fields: dict[str, Any] = results[0].get("fields") or {}
        for spec in fields.values():
            if isinstance(spec, dict):
                yield _KindTagged(cast("dict[str, Any]", spec), path.stem)


def screener_instrument_fields_kind(record: Mapping[str, Any]) -> str:
    """Read the instrument kind tagged by ``screener_instrument_fields_records``.

    Returns:
        str: The instrument name (for example ``"equity"``), or ``"?"``
        for an untagged record.
    """

    return record.kind if isinstance(record, _KindTagged) else "?"


def timeseries_fields_records(
    corpus_dir: Path = CORPUS_TIMESERIES_FIELDS_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield each capture's ``timeseriesfields.result[0].timeSeriesDataClass`` rows.

    Kind is fixed (``"timeseries-fields"``): a single, thin capture with no
    per-row classification.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        results: list[dict[str, Any]] = (
            payload.get("timeseriesfields", {}).get("result") or []
        )
        for result in results:
            rows: list[dict[str, Any]] = result.get("timeSeriesDataClass") or []
            yield from rows


def screener_discover_records(
    corpus_dir: Path = CORPUS_SCREENER_DISCOVER_DIR,
) -> Iterator[dict[str, Any]]:
    """Yield each capture's ``finance.result.quotes`` values.

    ``quotes`` is a symbol-keyed mapping, not a list. Kind is each row's
    own ``quoteType`` field.
    """

    for path in sorted(corpus_dir.glob("*.json")):
        payload = _load_json(path)
        result: dict[str, Any] = payload.get("finance", {}).get("result") or {}
        quotes: dict[str, Any] = result.get("quotes") or {}
        for quote in quotes.values():
            if isinstance(quote, dict):
                yield cast("dict[str, Any]", quote)


_STREAMS: Final[dict[str, Callable[[], Iterator[Mapping[str, Any]]]]] = {
    "quote": quote_records,
    "chart-meta": chart_meta_records,
    "spark-meta": spark_meta_records,
    "chart-and-spark-meta": chart_and_spark_meta_records,
    "option-contracts": option_contract_records,
    "option-chains": option_chain_records,
    "calendar-events": calendar_events_records,
    "calendar-events:earnings": earnings_records,
    "calendar-events:ipoEvents": ipo_events_records,
    "calendar-events:secReports": sec_reports_records,
    "quote-type": quote_type_records,
    "recommendations-by-symbol": recommendations_records,
    "stock-recommender": stock_recommender_records,
    "price-insights": price_insights_records,
    "insights": insights_records,
    "analyst": analyst_records,
    "ratings-top": ratings_top_records,
    "trending": trending_records,
    "market-summary": market_summary_records,
    "market-info": market_info_records,
    "market-time": market_time_records,
    "sector": sector_records,
    "screener-instrument-fields": screener_instrument_fields_records,
    "timeseries-fields": timeseries_fields_records,
    "screener-discover": screener_discover_records,
}

_KIND_OF: Final[dict[str, Callable[[Mapping[str, Any]], str]]] = {
    "quote": _quote_kind,
    "chart-meta": _instrument_kind,
    "spark-meta": _instrument_kind,
    "chart-and-spark-meta": _instrument_kind,
    "option-contracts": contract_kind,
    "option-chains": lambda _record: "chain",
    "calendar-events": lambda _record: "calendar-events",
    "calendar-events:earnings": lambda _record: "earnings",
    "calendar-events:ipoEvents": lambda _record: "ipoEvents",
    "calendar-events:secReports": lambda _record: "secReports",
    "quote-type": _quote_kind,
    "recommendations-by-symbol": quote_type_lookup_kind,
    "stock-recommender": quote_type_lookup_kind,
    "price-insights": quote_type_lookup_kind,
    "insights": quote_type_lookup_kind,
    "analyst": quote_type_lookup_kind,
    "ratings-top": quote_type_lookup_kind,
    "trending": _quote_kind,
    "market-summary": _quote_kind,
    "market-info": market_info_kind,
    "market-time": lambda _record: "market-time",
    "sector": lambda _record: "sector",
    "screener-instrument-fields": screener_instrument_fields_kind,
    "timeseries-fields": lambda _record: "timeseries-fields",
    "screener-discover": _quote_kind,
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
