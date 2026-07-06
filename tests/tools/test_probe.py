"""Tests for the Yahoo probe harness."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from tools.probe import (
    _CROSS_ASSET_SYMBOLS,  # pyright: ignore[reportPrivateUsage]
    _QUARANTINED_EVENT_TYPES,  # pyright: ignore[reportPrivateUsage]
    INVALID_SYMBOL,
    SYMBOLS,
    ProbeCase,
    _contract_cases,  # pyright: ignore[reportPrivateUsage]
    _cross_asset_cases,  # pyright: ignore[reportPrivateUsage]
    _first_contract_symbol,  # pyright: ignore[reportPrivateUsage]
    _invalid_cases,  # pyright: ignore[reportPrivateUsage]
    _run_all,  # pyright: ignore[reportPrivateUsage]
    _run_case,  # pyright: ignore[reportPrivateUsage]
    _timeseries_all_type_cases,  # pyright: ignore[reportPrivateUsage]
    build_cases,
    sanitize,
)
from yoghurt.cli import build_parser
from yoghurt.commands import COMMANDS_BY_NAME
from yoghurt.exceptions import YahooRequestError, YahooUnavailableError
from yoghurt.types import ParamValue

_HTTP_OK = 200
_HTTP_NOT_FOUND = 404


def test_sanitize_maps_symbol_punctuation() -> None:
    """Sanitize replaces filesystem-unsafe punctuation, keeps safe punctuation."""
    assert sanitize("^GSPC") == "_GSPC"
    assert sanitize("ES=F") == "ES_F"
    assert sanitize("EURUSD=X") == "EURUSD_X"
    assert sanitize("RY.TO") == "RY.TO"
    assert sanitize("BAC-PL") == "BAC-PL"
    assert sanitize("0700.HK") == "0700.HK"


def test_every_modeled_command_has_cases() -> None:
    """Every CommandSpec plus the DSL-only routes appears in the probe plan."""
    covered = {case.command for case in build_cases()}
    assert set(COMMANDS_BY_NAME) <= covered
    # DSL routes are CLI-level commands, not CommandSpecs:
    assert {"screener", "visualization"} <= covered


def test_dsl_cases_include_the_splits_entity() -> None:
    """The splits visualization case (agent-skill snippet evidence) stays planned.

    Added 2026-07-05 to back the queries skill domain's ``FROM splits``
    snippet with a real capture; pinned here so a probe-plan refactor
    cannot silently drop it (same traceability the quarantined event
    types get).
    """
    visualization_cases = {
        case.case for case in build_cases() if case.command == "visualization"
    }
    assert "splits" in visualization_cases


def test_symbol_matrix_is_probed_for_quote() -> None:
    """Every baseline symbol and the invalid symbol get a quote case."""
    quote_cases = {c.case for c in build_cases() if c.command == "quote"}
    for symbol in SYMBOLS:
        assert symbol in quote_cases
    assert INVALID_SYMBOL in quote_cases


_EXPECTED_INVALID_SYMBOL_COMMANDS = {
    "quote",
    "quote-summary",
    "quote-type",
    "chart",
    "spark",
    "timeseries",
    "analyst",
    "calendar-events",
    "recommendations-by-symbol",
    "stock-recommender",
    "price-insights",
    "insights",
    "ratings-top",
    "options",
}


def test_invalid_symbol_cases_cover_every_error_prone_command() -> None:
    """Every error-prone command gets an INVALID_SYMBOL case (Part 4 gate).

    Extends the original quote/chart/spark/timeseries/analyst set with the
    seven commands that previously had no captured invalid-symbol shape:
    calendar-events, recommendations-by-symbol, stock-recommender,
    price-insights, insights, ratings-top, options.
    """
    cases = _invalid_cases()
    commands = {c.command for c in cases}
    assert commands == _EXPECTED_INVALID_SYMBOL_COMMANDS
    for case in cases:
        assert case.case == INVALID_SYMBOL


_EXPECTED_CROSS_ASSET_CASE_COUNT = 15


def test_cross_asset_cases_cover_insights_family() -> None:
    """insights/price-insights/recommendations-by-symbol get 5 cross-asset cases each.

    These three endpoints were only probed against EQUITY_SUBSET
    (AAPL/MSFT/RY.TO); live checks during Part 3d found real
    applicability differences across asset classes the corpus never
    captured (see the model docstrings in
    ``yoghurt.models.analysis_insights``). ``_CROSS_ASSET_SYMBOLS`` mirrors
    the AGENTS.md baseline probe's non-equity coverage.
    """
    cases = _cross_asset_cases()
    by_command: dict[str, set[str]] = {}
    for case in cases:
        by_command.setdefault(case.command, set()).add(case.case)
    assert by_command == {
        "insights": set(_CROSS_ASSET_SYMBOLS),
        "price-insights": set(_CROSS_ASSET_SYMBOLS),
        "recommendations-by-symbol": set(_CROSS_ASSET_SYMBOLS),
    }
    assert len(cases) == _EXPECTED_CROSS_ASSET_CASE_COUNT


def test_quarantined_event_types_excluded_from_bulk_chunks() -> None:
    """The three event types never appear in an AAPL_types_NN bulk chunk.

    spEarningsReleaseEvents corrupts Yahoo's JSON response wholesale when
    bundled with any other type; analystRatings and economicEvents are
    individually clean but are quarantined alongside it so the bulk
    fundamentals sweep stays parseable.
    """
    cases = _timeseries_all_type_cases()
    bulk_cases = [c for c in cases if c.case.startswith("AAPL_types_")]
    assert bulk_cases, "expected at least one bulk fundamentals chunk"
    for case in bulk_cases:
        type_index = case.argv.index("--type")
        requested = set(case.argv[type_index + 1].split(","))
        assert requested.isdisjoint(_QUARANTINED_EVENT_TYPES)


def test_quarantined_event_types_each_get_a_dedicated_case() -> None:
    """analystRatings, economicEvents, and spEarnings each get their own case."""
    cases = _timeseries_all_type_cases()
    dedicated_names = {
        "AAPL_analystRatings",
        "AAPL_economicEventsLong",
        "AAPL_spEarnings",
    }
    dedicated = {
        c.case: c.argv[c.argv.index("--type") + 1]
        for c in cases
        if c.case in dedicated_names
    }
    assert dedicated == {
        "AAPL_analystRatings": "analystRatings",
        "AAPL_economicEventsLong": "economicEvents",
        "AAPL_spEarnings": "spEarningsReleaseEvents",
    }


def test_all_case_argv_parse() -> None:
    """Every case's argv parses through the real CLI argument parser."""
    parser = build_parser()
    for case in build_cases():
        try:
            parser.parse_args(list(case.argv))
        except SystemExit:  # noqa: PERF203
            pytest.fail(
                f"argv does not parse for {case.command}/{case.case}: {case.argv}"
            )


def test_case_keys_are_unique() -> None:
    """No two cases share the same command/case key."""
    keys = [f"{c.command}/{c.case}" for c in build_cases()]
    assert len(keys) == len(set(keys))


def test_case_files_are_unique() -> None:
    """No two cases sanitize to the same command/file path on disk."""
    files = [(c.command, sanitize(c.case)) for c in build_cases()]
    assert len(files) == len(set(files))


class _FakeClient:
    """Minimal stand-in for YahooClient that returns or raises canned results."""

    def __init__(
        self, *, error: Exception | None = None, body: str = '{"ok": true}'
    ) -> None:
        """Store the body to return, or the error to raise instead."""
        self._error = error
        self._body = body
        self.closed = False

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Return a canned body, or raise the configured error.

        Returns:
            str: A trivial JSON body.
        """
        del path, params, use_crumb, base_url
        if self._error is not None:
            raise self._error
        return self._body

    async def post(
        self,
        path: str,
        params: dict[str, ParamValue],
        json_body: dict[str, object],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Return a canned body, or raise the configured error.

        Returns:
            str: A trivial JSON body.
        """
        del path, params, json_body, use_crumb, base_url
        if self._error is not None:
            raise self._error
        return self._body

    async def aclose(self) -> None:
        """Record the close; there is no real connection."""
        self.closed = True


async def test_run_case_writes_body_and_manifest_entry(tmp_path: Path) -> None:
    """A successful case writes its body under the corpus dir and reports ok."""
    parser = build_parser()
    case = ProbeCase("quote", "AAPL", ("quote", "AAPL"))
    entry = await _run_case(parser, _FakeClient(), case, tmp_path)
    assert entry["status"] == "ok"
    assert entry["file"] == "quote/AAPL.json"
    written = (tmp_path / "quote" / "AAPL.json").read_text(encoding="utf-8")
    assert written == '{"ok": true}\n'  # CLI appends the trailing newline


async def test_run_case_records_http_error_body(tmp_path: Path) -> None:
    """An HTTP error still writes Yahoo's error body and records the status."""
    parser = build_parser()
    error = YahooRequestError(_HTTP_NOT_FOUND, "https://x", body='{"finance": null}')
    case = ProbeCase("quote-summary", "ZZZZXYZQ", ("quote-summary", "ZZZZXYZQ"))
    entry = await _run_case(parser, _FakeClient(error=error), case, tmp_path)
    assert entry["status"] == "http_error"
    assert entry["http_status"] == _HTTP_NOT_FOUND
    written = (tmp_path / "quote-summary" / "ZZZZXYZQ.json").read_text(encoding="utf-8")
    assert written == '{"finance": null}'


async def test_run_case_records_corrupt_ok_body_as_error(tmp_path: Path) -> None:
    r"""An HTTP-200 body that is not valid JSON records an error and no file.

    Yahoo's spEarningsReleaseEvents corruption arrives as an HTTP 200 whose
    body carries an invalid ``\'`` escape; the manifest must not call such
    a capture "ok" (a 2026-07-05 retest session mistook exactly that for a
    fixed feed).
    """
    parser = build_parser()
    case = ProbeCase("quote", "AAPL", ("quote", "AAPL"))
    corrupt = r"""{"note": "it\'s corrupt"}"""
    entry = await _run_case(parser, _FakeClient(body=corrupt), case, tmp_path)
    assert entry["status"] == "error"
    assert entry["http_status"] == _HTTP_OK  # the transport really returned 200
    assert "not valid JSON" in str(entry["detail"])
    assert "file" not in entry
    assert not (tmp_path / "quote" / "AAPL.json").exists()


async def test_run_case_records_transport_error_without_file(
    tmp_path: Path,
) -> None:
    """A transport error records status=error and writes no file."""
    parser = build_parser()
    case = ProbeCase("quote", "AAPL", ("quote", "AAPL"))
    entry = await _run_case(
        parser,
        _FakeClient(error=YahooUnavailableError("api call")),
        case,
        tmp_path,
    )
    assert entry["status"] == "error"
    assert "file" not in entry


async def test_run_all_writes_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A full run writes every body file plus the manifest and closes the client."""
    fake = _FakeClient()
    monkeypatch.setattr("tools.probe.YahooClient", lambda: fake)
    monkeypatch.setattr("tools.probe.POLITENESS_DELAY_SECONDS", 0.0)
    cases = [
        ProbeCase("quote", "AAPL", ("quote", "AAPL")),
        ProbeCase("quote-type", "AAPL", ("quote-type", "AAPL")),
    ]
    await _run_all(cases, tmp_path)
    assert fake.closed
    manifest_text = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    assert manifest_text.endswith("\n")
    manifest = json.loads(manifest_text)
    assert set(manifest) == {"quote/AAPL", "quote-type/AAPL", "_meta"}
    meta = manifest["_meta"]
    assert meta["case_count"] == len(cases)
    assert isinstance(datetime.fromisoformat(meta["fetched_at"]), datetime)
    assert (tmp_path / "quote" / "AAPL.json").is_file()
    assert (tmp_path / "quote-type" / "AAPL.json").is_file()


async def test_run_all_records_validation_error_in_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A case failing dispatch-time validation becomes an error entry, not a crash."""
    fake = _FakeClient()
    monkeypatch.setattr("tools.probe.YahooClient", lambda: fake)
    monkeypatch.setattr("tools.probe.POLITENESS_DELAY_SECONDS", 0.0)
    # Reversed date window: parses fine, then validate_params
    # raises ValueError (not a YoghurtError) at dispatch time.
    bad = ProbeCase(
        "chart",
        "AAPL_reversed",
        (
            "chart",
            "AAPL",
            "--period1",
            "2026-01-02",
            "--period2",
            "2026-01-01",
            "--interval",
            "1d",
        ),
    )
    await _run_all([bad], tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["chart/AAPL_reversed"]
    assert entry["status"] == "error"
    assert entry["http_status"] is None
    assert "file" not in entry


_OPTIONS_BODY = {
    "optionChain": {
        "result": [
            {
                "underlyingSymbol": "AAPL",
                "options": [{"calls": [{"contractSymbol": "AAPL260117C00200000"}]}],
            }
        ],
        "error": None,
    }
}


def test_first_contract_symbol_extracts_call(tmp_path: Path) -> None:
    """The first call contract symbol is pulled from a saved options response."""
    path = tmp_path / "AAPL.json"
    path.write_text(json.dumps(_OPTIONS_BODY), encoding="utf-8")
    assert _first_contract_symbol(path) == "AAPL260117C00200000"


def test_first_contract_symbol_handles_missing_file(tmp_path: Path) -> None:
    """A missing options file resolves to None instead of raising."""
    assert _first_contract_symbol(tmp_path / "nope.json") is None


def test_contract_cases_cover_quote_endpoints() -> None:
    """The contract follow-up cases cover quote, quote-type, and quote-summary."""
    cases = _contract_cases("AAPL260117C00200000")
    assert {c.command for c in cases} == {"quote", "quote-type", "quote-summary"}
    for case in cases:
        assert case.case == "OPTION_CONTRACT"
        assert "AAPL260117C00200000" in case.argv
