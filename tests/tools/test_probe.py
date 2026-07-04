"""Tests for the Yahoo probe harness."""

import pytest

from tools.probe import INVALID_SYMBOL, SYMBOLS, build_cases, sanitize
from yoghurt.cli import build_parser
from yoghurt.commands import COMMANDS_BY_NAME


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
