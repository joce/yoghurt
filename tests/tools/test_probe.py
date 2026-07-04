"""Tests for the Yahoo probe harness."""

from tools.probe import sanitize


def test_sanitize_maps_symbol_punctuation() -> None:
    """Sanitize replaces filesystem-unsafe punctuation, keeps safe punctuation."""
    assert sanitize("^GSPC") == "_GSPC"
    assert sanitize("ES=F") == "ES_F"
    assert sanitize("EURUSD=X") == "EURUSD_X"
    assert sanitize("RY.TO") == "RY.TO"
    assert sanitize("BAC-PL") == "BAC-PL"
    assert sanitize("0700.HK") == "0700.HK"
