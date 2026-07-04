"""Corpus-driven tests for envelope parsing and error mapping."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from yoghurt._core import ENVELOPES, interpret_body, map_http_error
from yoghurt.exceptions import SymbolNotFoundError, YahooApiError, YahooRequestError

CORPUS = Path(__file__).parent / "fixtures" / "corpus"
_HTTP_NOT_FOUND = 404
_HTTP_BAD_GATEWAY = 502


def _corpus_text(rel: str) -> str:
    return (CORPUS / rel).read_text(encoding="utf-8")


def test_ok_body_returns_parsed_payload() -> None:
    """A healthy quote body parses and passes through whole."""
    payload = interpret_body("quote", _corpus_text("quote/AAPL.json"), symbol="AAPL")
    assert payload["quoteResponse"]["result"][0]["symbol"] == "AAPL"


def test_enveloped_error_with_200_raises_api_error() -> None:
    """A 200 body whose envelope carries an error raises YahooApiError."""
    body = json.dumps(
        {
            "quoteSummary": {
                "result": None,
                "error": {"code": "Bad Request", "description": "nope"},
            }
        }
    )
    with pytest.raises(YahooApiError) as exc_info:
        interpret_body("quote-summary", body, symbol="AAPL")
    assert exc_info.value.code == "Bad Request"


def test_malformed_json_raises_api_error() -> None:
    """Yahoo can send HTTP 200 with broken JSON (corpus: timeseries AAPL_types_00)."""
    with pytest.raises(YahooApiError, match="not valid JSON"):
        interpret_body(
            "timeseries", _corpus_text("timeseries/AAPL_types_00.json"), symbol="AAPL"
        )


def test_http_404_enveloped_not_found_maps_to_symbol_error() -> None:
    """quote-summary 404 for a bad symbol becomes SymbolNotFoundError."""
    request_error = YahooRequestError(
        _HTTP_NOT_FOUND, "https://x", body=_corpus_text("quote-summary/ZZZZXYZQ.json")
    )
    with pytest.raises(SymbolNotFoundError) as exc_info:
        map_http_error("quote-summary", request_error, symbol="ZZZZXYZQ")
    assert exc_info.value.symbol == "ZZZZXYZQ"
    assert exc_info.value.http_status == _HTTP_NOT_FOUND


def test_http_404_bare_detail_maps_to_symbol_error() -> None:
    """Analyst 404 body {"detail": "..."} becomes SymbolNotFoundError."""
    request_error = YahooRequestError(
        _HTTP_NOT_FOUND, "https://x", body=_corpus_text("analyst/ZZZZXYZQ.json")
    )
    with pytest.raises(SymbolNotFoundError):
        map_http_error("analyst", request_error, symbol="ZZZZXYZQ")


def test_http_error_without_usable_body_reraises_original() -> None:
    """No parseable Yahoo payload -> the transport-level error stands."""
    request_error = YahooRequestError(
        _HTTP_BAD_GATEWAY, "https://x", body="<html>gateway</html>"
    )
    with pytest.raises(YahooRequestError):
        map_http_error("quote", request_error, symbol="AAPL")


@pytest.mark.parametrize(
    "rel",
    ["chart/ZZZZXYZQ.json", "spark/ZZZZXYZQ.json"],
)
def test_all_enveloped_404_corpora_map_to_symbol_error(rel: str) -> None:
    """Every enveloped 404 error shape in the corpus maps to SymbolNotFoundError."""
    command = rel.split("/", maxsplit=1)[0]
    request_error = YahooRequestError(
        _HTTP_NOT_FOUND, "https://x", body=_corpus_text(rel)
    )
    with pytest.raises(SymbolNotFoundError):
        map_http_error(command, request_error, symbol="ZZZZXYZQ")


# Manifest-"ok" captures kept byte-for-byte as evidence of Yahoo-side
# corruption; they do not parse as JSON (see tests/fixtures/corpus/README.md).
_KNOWN_MALFORMED = frozenset({"timeseries/AAPL_types_00.json"})


def _first_ok_corpus_file(command: str) -> str | None:
    """Return the first alphabetical ok-status corpus file, minus known-bad ones."""
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    candidates = sorted(
        entry["file"]
        for key, entry in manifest.items()
        if key.startswith(f"{command}/")
        and entry.get("status") == "ok"
        and entry["file"] not in _KNOWN_MALFORMED
    )
    return candidates[0] if candidates else None


_ENVELOPED_COMMANDS = sorted(
    command for command, key in ENVELOPES.items() if key is not None
)


@pytest.mark.parametrize("command", _ENVELOPED_COMMANDS)
def test_envelope_map_pins_root_key_to_corpus_reality(command: str) -> None:
    """Every enveloped command's mapped root key appears in an ok corpus file."""
    corpus_file = _first_ok_corpus_file(command)
    assert corpus_file is not None, f"no ok corpus file found for {command}"
    payload = interpret_body(command, _corpus_text(corpus_file))
    assert ENVELOPES[command] in payload
