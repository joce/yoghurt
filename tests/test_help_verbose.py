"""Tests for per-command --help --verbose, which appends reference docs."""

from __future__ import annotations

from importlib.resources import files

import pytest

from yoghurt import cli
from yoghurt.cli import build_parser, main
from yoghurt.commands import COMMANDS_BY_NAME

_DOCS_DIR = "yoghurt.docs"
_DOC_MARKER_LINE = 10

_VERBOSE_HELP_COMMANDS: tuple[tuple[str, str], ...] = (
    ("screener", "QUERY_DSL.md"),
    ("visualization", "QUERY_DSL.md"),
)


@pytest.mark.parametrize(("command", "doc_filename"), _VERBOSE_HELP_COMMANDS)
def test_help_verbose_appends_reference_doc(
    command: str,
    doc_filename: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`<command> --help --verbose` prints standard help followed by the doc."""

    expected_doc = (files(_DOCS_DIR) / doc_filename).read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main([command, "--help", "--verbose"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    # Standard help still present (usage line).
    assert f"usage: yoghurt {command}" in captured.out
    # Doc body appended verbatim.
    assert expected_doc.rstrip() in captured.out


@pytest.mark.parametrize(("command", "_doc_filename"), _VERBOSE_HELP_COMMANDS)
def test_help_mentions_help_verbose(
    command: str,
    _doc_filename: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Standard `--help` for verbose-enabled commands points to --help --verbose."""

    with pytest.raises(SystemExit) as exc_info:
        main([command, "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--help --verbose" in captured.out


@pytest.mark.parametrize(("command", "doc_filename"), _VERBOSE_HELP_COMMANDS)
def test_standard_help_does_not_include_doc_body(
    command: str,
    doc_filename: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Standard `--help` does NOT dump the full reference doc."""

    expected_doc = (files(_DOCS_DIR) / doc_filename).read_text(encoding="utf-8")
    # Pick a marker far enough into the doc that it would not be in a brief
    # mention.
    lines = expected_doc.splitlines()
    marker = lines[_DOC_MARKER_LINE] if len(lines) > _DOC_MARKER_LINE else ""
    if not marker.strip():
        return

    with pytest.raises(SystemExit) as exc_info:
        main([command, "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert marker not in captured.out


@pytest.mark.parametrize("command", ["quote", "timeseries", "quote-summary"])
def test_compact_help_preserves_options_and_reaches_catalog(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Both views share options; verbose appends each metadata reference once."""
    with pytest.raises(SystemExit):
        main([command, "--help"])
    ordinary = capsys.readouterr().out
    with pytest.raises(SystemExit):
        main([command, "--help", "--verbose"])
    verbose = capsys.readouterr().out
    spec = COMMANDS_BY_NAME[command]
    assert verbose.startswith(ordinary)
    assert len(ordinary) < len(verbose) / 2
    for param in spec.params:
        if not param.positional:
            assert param.option in ordinary
    for reference in spec.field_reference:
        assert verbose.count(f"  {reference.name}:") == 1
    for section in spec.reference_sections:
        for reference in section.values:
            assert verbose.count(f"  {reference.name}:") == 1


@pytest.mark.parametrize(
    "flags",
    [
        ["quote", "--help", "--verbose"],
        ["quote", "--verbose", "--help"],
        ["--verbose", "quote", "--help"],
        ["-v", "quote", "-h"],
        ["quote", "-h", "-v"],
        ["quote", "-v", "-h"],
        ["quote", "-hv"],
        ["quote", "-vh"],
    ],
)
def test_help_verbose_order_and_scope(
    flags: list[str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Help bypasses required symbols, client creation, and logging setup."""

    def unexpected(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("Help must not create a client or configure logging")

    monkeypatch.setattr(cli, "YahooClient", unexpected)
    monkeypatch.setattr(cli, "_configure_logging", unexpected)
    with pytest.raises(SystemExit) as result:
        main(flags)
    assert result.value.code == 0
    actual = capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["quote", "--help", "--verbose"])
    assert actual == capsys.readouterr().out
    assert "Quote --fields reference" in actual


@pytest.mark.parametrize("prefix", [[], ["raw"], ["history"], ["skills", "install"]])
def test_help_verbose_without_reference(
    prefix: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """Every parser supports composed help even without a longer reference."""
    with pytest.raises(SystemExit):
        main([*prefix, "--help", "--verbose"])
    verbose = capsys.readouterr().out
    with pytest.raises(SystemExit):
        main([*prefix, "--help"])
    assert verbose == capsys.readouterr().out


@pytest.mark.parametrize(
    "args",
    [
        ["-v", "quote", "AAPL"],
        ["quote", "AAPL", "-v"],
        ["--verbose", "quote", "AAPL"],
        ["quote", "AAPL", "--verbose"],
    ],
)
def test_verbose_normal_execution_parser(args: list[str]) -> None:
    """Debug verbosity survives root and endpoint placement."""
    assert build_parser().parse_args(args).verbose is True


def test_help_verbosity_does_not_leak_or_match_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A previous parse or a value containing the switch does not enable it."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["quote", "--help", "--verbose"])
    capsys.readouterr()
    with pytest.raises(SystemExit):
        parser.parse_args(["quote", "--img-labels=--verbose", "--help"])
    assert "Quote --fields reference" not in capsys.readouterr().out
