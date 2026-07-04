"""Probe every Yahoo endpoint across the symbol matrix; write the corpus.

Run from the repo root:  uv run python -m tools.probe

Writes raw response bodies to tests/fixtures/corpus/<command>/<case>.json and
a manifest.json describing every case (argv, status, timestamp). Re-running
and diffing the corpus is the Yahoo schema-drift detector.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
CORPUS_DIR: Final[Path] = REPO_ROOT / "tests" / "fixtures" / "corpus"
POLITENESS_DELAY_SECONDS: Final[float] = 0.4

SYMBOLS: Final[tuple[str, ...]] = (
    # US stocks, high profile and smaller
    "AAPL",
    "MSFT",
    "OKLO",
    # ETFs
    "SPY",
    "QQQ",
    "VT",
    # Futures and commodities
    "ES=F",
    "CL=F",
    # Forex
    "EURUSD=X",
    # Indices
    "^GSPC",
    "^DJI",
    "^IXIC",
    # Crypto
    "BTC-USD",
    # Foreign listings
    "RY.TO",
    "0700.HK",
    "7203.T",
    "SHEL.L",
    # Mutual fund
    "VTSAX",
    # Treasury yields
    "^TNX",
    "^IRX",
    # ADR
    "BABA",
    # Preferred share
    "BAC-PL",
)
INVALID_SYMBOL: Final[str] = "ZZZZXYZQ"
EQUITY_SUBSET: Final[tuple[str, ...]] = ("AAPL", "MSFT", "RY.TO")
OPTIONABLE: Final[tuple[str, ...]] = ("AAPL", "MSFT", "SPY")


@dataclass(frozen=True, slots=True)
class ProbeCase:
    """One probe: a CLI-shaped invocation whose output lands in the corpus."""

    command: str  # corpus subdirectory (CLI command name)
    case: str  # file stem before sanitization
    argv: tuple[str, ...]  # exactly what would follow `yoghurt ` on a shell


def sanitize(name: str) -> str:
    """Make a case name filesystem-safe on every platform.

    Returns:
        str: The name with unsafe characters replaced by underscores.
    """
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def _utc_today() -> datetime:
    return datetime.now(timezone.utc)


def _yesterday_iso() -> str:
    return (_utc_today() - timedelta(days=1)).date().isoformat()


def _days_ago_iso(days: int) -> str:
    return (_utc_today() - timedelta(days=days)).date().isoformat()
