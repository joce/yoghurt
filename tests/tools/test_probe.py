"""Tests for the Yahoo probe harness."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from tools.probe import (
    INVALID_SYMBOL,
    SYMBOLS,
    ProbeCase,
    _contract_cases,  # pyright: ignore[reportPrivateUsage]
    _first_contract_symbol,  # pyright: ignore[reportPrivateUsage]
    _run_all,  # pyright: ignore[reportPrivateUsage]
    _run_case,  # pyright: ignore[reportPrivateUsage]
    build_cases,
    sanitize,
)
from yoghurt.cli import build_parser
from yoghurt.commands import COMMANDS_BY_NAME
from yoghurt.exceptions import YahooRequestError, YahooUnavailableError
from yoghurt.types import ParamValue

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


def test_symbol_matrix_is_probed_for_quote() -> None:
    """Every baseline symbol and the invalid symbol get a quote case."""
    quote_cases = {c.case for c in build_cases() if c.command == "quote"}
    for symbol in SYMBOLS:
        assert symbol in quote_cases
    assert INVALID_SYMBOL in quote_cases


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

    def __init__(self, *, error: Exception | None = None) -> None:
        """Store the error to raise, if any, instead of returning a body."""
        self._error = error
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
        return '{"ok": true}'

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
        return '{"ok": true}'

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
