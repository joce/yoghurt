"""Tests for the Yahoo probe harness."""

from pathlib import Path

import pytest

from tools.probe import (
    INVALID_SYMBOL,
    SYMBOLS,
    ProbeCase,
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


class _FakeClient:
    """Minimal stand-in for YahooClient that returns or raises canned results."""

    def __init__(self, *, error: Exception | None = None) -> None:
        """Store the error to raise, if any, instead of returning a body."""
        self._error = error

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
        """Do nothing; no real connection to close."""


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
