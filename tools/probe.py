"""Probe every Yahoo endpoint across the symbol matrix; write the corpus.

Run from the repo root:  uv run python -m tools.probe

Writes raw response bodies to tests/fixtures/corpus/<command>/<case>.json and
a manifest.json describing every case (argv, status, timestamp). Re-running
and diffing the corpus is the Yahoo schema-drift detector.
"""

from __future__ import annotations

import asyncio
import io
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Final

from yoghurt.cli import _dispatch_command, build_parser
from yoghurt.client import YahooClient
from yoghurt.commands import COMMANDS_BY_NAME
from yoghurt.exceptions import YahooRequestError, YoghurtError

if TYPE_CHECKING:
    import argparse

    from yoghurt.cli import _YahooClientProtocol

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


def _chunked(values: tuple[str, ...], size: int) -> list[tuple[str, ...]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def _all_quote_summary_modules() -> str:
    """Every quote-summary module: common list, or the full field reference.

    Returns:
        str: A comma-joined module list suitable for --modules.
    """

    qs_spec = COMMANDS_BY_NAME["quote-summary"]
    return ",".join(
        qs_spec.common_modules or tuple(ref.name for ref in qs_spec.field_reference)
    )


def _symbol_cases() -> list[ProbeCase]:
    """Symbol-bound endpoints across the full matrix.

    Returns:
        list[ProbeCase]: One quote/quote-type/quote-summary/chart/spark/
        timeseries/calendar-events case per symbol, plus default-field and
        multi-symbol batch cases.
    """

    quote_fields = ",".join(
        ref.name for ref in COMMANDS_BY_NAME["quote"].field_reference
    )
    qs_modules = _all_quote_summary_modules()
    chart_p1, chart_p2 = _days_ago_iso(5), _yesterday_iso()

    cases: list[ProbeCase] = []
    for sym in SYMBOLS:
        cases += [
            # All known quote fields -> maximum field-applicability evidence.
            ProbeCase("quote", sym, ("quote", sym, "--fields", quote_fields)),
            ProbeCase("quote-type", sym, ("quote-type", sym)),
            # All modules in one request; Yahoo returns the applicable subset.
            ProbeCase(
                "quote-summary",
                sym,
                ("quote-summary", sym, "--modules", qs_modules),
            ),
            ProbeCase(
                "chart",
                sym,
                (
                    "chart",
                    sym,
                    "--period1",
                    chart_p1,
                    "--period2",
                    chart_p2,
                    "--interval",
                    "1d",
                ),
            ),
            ProbeCase("spark", sym, ("spark", sym)),
            ProbeCase("timeseries", sym, ("timeseries", sym)),
            ProbeCase("calendar-events", sym, ("calendar-events", sym)),
        ]
    # Default-field quote and a multi-symbol batch (envelope evidence).
    cases += [
        ProbeCase("quote", "AAPL_default", ("quote", "AAPL")),
        ProbeCase("quote", "multi", ("quote", "AAPL,MSFT,BTC-USD,EURUSD=X")),
        ProbeCase("spark", "multi", ("spark", "AAPL,MSFT")),
    ]
    return cases


def _chart_variant_cases() -> list[ProbeCase]:
    """Interval/eventful variants: meta differs by granularity.

    Returns:
        list[ProbeCase]: An intraday 1m case and a long-window daily case
        with dividend/split/earnings events requested.
    """

    yesterday = _yesterday_iso()
    return [
        # One hour of 1m bars (intraday meta: tradingPeriods, etc.).
        ProbeCase(
            "chart",
            "AAPL_1m",
            (
                "chart",
                "AAPL",
                "--period1",
                f"{yesterday}T15:00:00Z",
                "--period2",
                f"{yesterday}T16:00:00Z",
                "--interval",
                "1m",
            ),
        ),
        # A year of dailies with events (dividends/splits/earnings arrays).
        ProbeCase(
            "chart",
            "MSFT_1y_events",
            (
                "chart",
                "MSFT",
                "--period1",
                _days_ago_iso(366),
                "--period2",
                yesterday,
                "--interval",
                "1d",
                "--events",
                "div,split,earn",
            ),
        ),
    ]


# Yahoo serves stable, systemic malformed JSON for spEarningsReleaseEvents
# (every symbol, every re-probe, even requested alone): a request bundling it
# with any other type fails wholesale at JSON parse. Quarantined out of the
# all-types chunks below; analystRatings and economicEvents are event types
# too but are individually clean, so they get their own dedicated cases
# instead of riding in the bulk fundamentals sweep.
_QUARANTINED_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {"spEarningsReleaseEvents", "analystRatings", "economicEvents"}
)


def _timeseries_all_type_cases() -> list[ProbeCase]:
    """All known fundamentals types for AAPL, chunked to keep URLs sane.

    Long window: annual metrics need years of history to return anything.
    The three event types (``spEarningsReleaseEvents``, ``analystRatings``,
    ``economicEvents``) are excluded from these chunks; see
    ``_QUARANTINED_EVENT_TYPES`` and the three dedicated cases below.

    Returns:
        list[ProbeCase]: One case per chunk of --type values.
    """

    ts_spec = COMMANDS_BY_NAME["timeseries"]
    all_types = (
        tuple(ref.name for ref in ts_spec.field_reference) or ts_spec.common_types
    )
    fundamentals_types = tuple(
        name for name in all_types if name not in _QUARANTINED_EVENT_TYPES
    )
    p1, p2 = "2020-01-01", _yesterday_iso()
    return [
        ProbeCase(
            "timeseries",
            f"AAPL_types_{index:02d}",
            (
                "timeseries",
                "AAPL",
                "--type",
                ",".join(chunk),
                "--period1",
                p1,
                "--period2",
                p2,
            ),
        )
        for index, chunk in enumerate(_chunked(fundamentals_types, 40))
    ] + [
        ProbeCase(
            "timeseries",
            "AAPL_analystRatings",
            (
                "timeseries",
                "AAPL",
                "--type",
                "analystRatings",
                "--period1",
                p1,
                "--period2",
                p2,
            ),
        ),
        ProbeCase(
            "timeseries",
            "AAPL_economicEventsLong",
            (
                "timeseries",
                "AAPL",
                "--type",
                "economicEvents",
                "--period1",
                p1,
                "--period2",
                p2,
            ),
        ),
        # Requesting spEarningsReleaseEvents records Yahoo's own JSON
        # corruption as manifest evidence (status "error", no file) on
        # future full runs; that's intentional, not a probe bug.
        ProbeCase(
            "timeseries",
            "AAPL_spEarnings",
            (
                "timeseries",
                "AAPL",
                "--type",
                "spEarningsReleaseEvents",
                "--period1",
                p1,
                "--period2",
                p2,
            ),
        ),
    ]


def _equity_subset_cases() -> list[ProbeCase]:
    """Equity-only analysis endpoints; a small representative set suffices.

    Returns:
        list[ProbeCase]: Analyst/ratings/insights/recommendations/options
        cases across EQUITY_SUBSET and OPTIONABLE, plus a calendar-events
        module sweep on AAPL.
    """

    cases: list[ProbeCase] = []
    for sym in EQUITY_SUBSET:
        cases += [
            ProbeCase("analyst", sym, ("analyst", sym)),
            ProbeCase("ratings-top", sym, ("ratings-top", sym)),
            ProbeCase("price-insights", sym, ("price-insights", sym)),
            ProbeCase("insights", sym, ("insights", sym)),
            ProbeCase(
                "recommendations-by-symbol",
                sym,
                ("recommendations-by-symbol", sym),
            ),
            ProbeCase("stock-recommender", sym, ("stock-recommender", sym)),
        ]
    # README documents index recommendations too; ^GSPC now rides in
    # _cross_asset_cases() instead of a standalone case here (same
    # command/argv, folded in to avoid a duplicate case key).
    for sym in OPTIONABLE:
        cases.append(ProbeCase("options", sym, ("options", sym)))
    # Documented price-insights shape variants: modules=ai drops the
    # news/rating sections; check-anomaly narrows to hasPriceAnomaly only.
    cases += [
        ProbeCase(
            "price-insights",
            "AAPL_ai",
            ("price-insights", "AAPL", "--modules", "ai"),
        ),
        ProbeCase(
            "price-insights",
            "AAPL_anomaly",
            ("price-insights", "AAPL", "--check-anomaly"),
        ),
    ]
    # Calendar module sweep on AAPL (shapes differ per module).
    for module in ("economicEvents", "ipoEvents", "secReports"):
        cases.append(
            ProbeCase(
                "calendar-events",
                f"AAPL_{module}",
                ("calendar-events", "AAPL", "--modules", module),
            )
        )
    return cases


# Live windows (found via Yahoo's calendar UI, 2026-07-05) where earnings/
# ipoEvents/secReports actually populate rows: every prior calendar-events
# capture used the default (no --start-date/--end-date) window, which is
# always empty for these three modules. secReports resolves the CLI help's
# "SEC filing events" text as accurate (10-Q/8-K rows observed), not the
# stock-split hypothesis the UI otherwise suggested (split-day symbols like
# BEOB/CATTF/6669.TW captured empty secReports on retest).
_EARNINGS_WINDOW: Final[tuple[str, str]] = ("2026-06-20", "2026-06-27")
_EARNINGS_SYMBOLS: Final[tuple[str, ...]] = ("IVF", "HAWK", "EBF", "POWW")
_EARNINGS_LARGE_CAP_WINDOW: Final[tuple[str, str]] = ("2026-04-26", "2026-05-05")

_IPO_EVENTS_WINDOW: Final[tuple[str, str]] = ("2026-06-29", "2026-07-03")
_IPO_EVENTS_SYMBOLS: Final[tuple[str, ...]] = (
    "COPR",  # NYSE American common-stock pricing
    "GSRVR",  # rights
    "IQMXW",  # warrants
    "MIACU",  # units
    "VCRE",  # ADS
    "SECZ",  # NYSE common-stock pricing, empty currencyName variant
)

_SEC_REPORTS_WINDOW: Final[tuple[str, str]] = ("2026-06-20", "2026-06-27")
_SEC_REPORTS_SYMBOLS: Final[tuple[str, ...]] = ("BOXL", "HAWK")
_SEC_REPORTS_AAPL_WINDOW: Final[tuple[str, str]] = ("2026-04-20", "2026-05-05")
_SEC_REPORTS_MSFT_WINDOW: Final[tuple[str, str]] = ("2026-04-26", "2026-05-05")

# Negative evidence for the split-vs-filings hypothesis: these symbols split
# on 2026-06-22 per Yahoo's UI, so if secReports carried stock splits (the
# competing hypothesis) this window would populate. It does not.
_SEC_REPORTS_SPLIT_WINDOW: Final[tuple[str, str]] = ("2026-06-21", "2026-06-27")
_SEC_REPORTS_SPLIT_SYMBOLS: Final[tuple[str, ...]] = ("BEOB", "CATTF", "6669.TW")


def _calendar_events_case(
    symbol: str, case_suffix: str, module: str, window: tuple[str, str]
) -> ProbeCase:
    """Build one windowed calendar-events probe case for a single module.

    Returns:
        ProbeCase: A ``calendar-events`` case for ``symbol`` requesting
        ``module`` over ``window`` (start, end).
    """

    start, end = window
    return ProbeCase(
        "calendar-events",
        f"{symbol}_{case_suffix}",
        (
            "calendar-events",
            symbol,
            "--modules",
            module,
            "--start-date",
            start,
            "--end-date",
            end,
        ),
    )


def _calendar_events_populated_cases() -> list[ProbeCase]:
    """Live-found windows where earnings/ipoEvents/secReports populate rows.

    Also includes the split-hypothesis negative-evidence cases: three
    split-day symbols probed over the same window, expected to stay empty.

    Returns:
        list[ProbeCase]: 4 earnings cases + 1 large-cap earnings case, 6
        ipoEvents cases, 4 populated secReports cases (2 small/mid-cap +
        AAPL + MSFT), and 3 split-hypothesis secReports cases, each with an
        explicit --start-date/--end-date window.
    """

    cases = [
        _calendar_events_case(sym, "earnings", "earnings", _EARNINGS_WINDOW)
        for sym in _EARNINGS_SYMBOLS
    ]
    cases.append(
        _calendar_events_case(
            "MSFT", "earnings", "earnings", _EARNINGS_LARGE_CAP_WINDOW
        )
    )
    cases.extend(
        _calendar_events_case(sym, "ipoEvents", "ipoEvents", _IPO_EVENTS_WINDOW)
        for sym in _IPO_EVENTS_SYMBOLS
    )
    cases.extend(
        _calendar_events_case(sym, "secReports", "secReports", _SEC_REPORTS_WINDOW)
        for sym in _SEC_REPORTS_SYMBOLS
    )
    cases.extend(
        [
            _calendar_events_case(
                "AAPL", "secReports_filed", "secReports", _SEC_REPORTS_AAPL_WINDOW
            ),
            _calendar_events_case(
                "MSFT", "secReports_filed", "secReports", _SEC_REPORTS_MSFT_WINDOW
            ),
        ]
    )
    cases.extend(
        _calendar_events_case(
            sym, "secReports_split", "secReports", _SEC_REPORTS_SPLIT_WINDOW
        )
        for sym in _SEC_REPORTS_SPLIT_SYMBOLS
    )
    return cases


def _market_cases() -> list[ProbeCase]:
    """Symbol-free and market-wide endpoints.

    Returns:
        list[ProbeCase]: Market summary/info/time/trending/discovery cases,
        a sector sweep, an instrument-fields sweep, and a predefined
        screener sweep.
    """

    # Every documented instrument: asset classes, event entities, and
    # premium-locked entities (whose schemas are still readable). If this
    # metadata ever empties out, the completeness gate test fails loudly.
    sif_spec = COMMANDS_BY_NAME["screener-instrument-fields"]
    instruments = tuple(
        ref.name for section in sif_spec.reference_sections for ref in section.values
    )
    screener_ids = (
        "MOST_ACTIVES",  # equities
        "TOP_MUTUAL_FUNDS",  # funds
        "MOST_ACTIVES_CRYPTOCURRENCIES",  # crypto
        "52_WEEK_GAINERS_PRIVATE_COMPANY",  # private companies
        "TOP_OPTIONS_OPEN_INTEREST",  # options
    )
    cases = [
        ProbeCase("market-summary", "default", ("market-summary",)),
        ProbeCase("market-info", "default", ("market-info",)),
        ProbeCase("market-time", "default", ("market-time",)),
        ProbeCase("trending", "default", ("trending",)),
        ProbeCase("screener-discover", "default", ("screener-discover",)),
        ProbeCase("timeseries-fields", "default", ("timeseries-fields",)),
        ProbeCase("sector", "technology", ("sector", "technology")),
        ProbeCase("sector", "energy", ("sector", "energy")),
        ProbeCase("sector", "real-estate", ("sector", "real-estate")),
        # --with-returns adds return data to the sector performance section.
        ProbeCase(
            "sector",
            "technology_returns",
            ("sector", "technology", "--with-returns"),
        ),
    ]
    cases += [
        ProbeCase(
            "screener-instrument-fields", inst, ("screener-instrument-fields", inst)
        )
        for inst in instruments
    ]
    cases += [
        ProbeCase("screener-predefined", sid, ("screener-predefined", sid))
        for sid in screener_ids
    ]
    return cases


def _dsl_cases() -> list[ProbeCase]:
    """Screener and visualization DSL envelopes (columns are dynamic).

    Returns:
        list[ProbeCase]: A handful of representative screener and
        visualization DSL queries covering different entity types.
    """

    # These build yoghurt's SQL-flavored DSL query strings sent to Yahoo's
    # visualization/screener endpoints, not SQL against a real database;
    # there is no injection surface here.
    week_ago, yesterday = _days_ago_iso(8), _yesterday_iso()
    screener_queries = {
        "equity_us_tech": (
            "SELECT ticker, intradaymarketcap, sector FROM EQUITY "
            "WHERE region = 'us' AND sector = 'Technology' "
            "ORDER BY intradaymarketcap DESC LIMIT 5"
        ),
        "etf": (
            "SELECT ticker, fundnetassets FROM ETF "
            "WHERE region = 'us' ORDER BY fundnetassets DESC LIMIT 5"
        ),
        "mutualfund": (
            "SELECT ticker, fundnetassets FROM MUTUALFUND "
            "WHERE region = 'us' ORDER BY fundnetassets DESC LIMIT 5"
        ),
    }
    viz_queries = {
        "insider_transaction": (
            "SELECT ticker, transactiondate, shares FROM INSIDER_TRANSACTION "
            "WHERE ticker = 'AAPL' ORDER BY transactiondate DESC LIMIT 5"
        ),
        "sp_earnings": (
            "SELECT ticker, startdatetime FROM sp_earnings "  # ruff:ignore[hardcoded-sql-expression]
            f"WHERE region = 'us' AND startdatetime BETWEEN '{week_ago}' "
            f"AND '{yesterday}' LIMIT 5"
        ),
        "splits": (
            "SELECT ticker, startdatetime FROM splits "
            "WHERE startdatetime BETWEEN '2026-05-09' AND '2026-05-16' LIMIT 25"
        ),
    }
    return [
        ProbeCase("screener", name, ("screener", "--query", query))
        for name, query in screener_queries.items()
    ] + [
        ProbeCase("visualization", name, ("visualization", "--query", query))
        for name, query in viz_queries.items()
    ]


def _invalid_cases() -> list[ProbeCase]:
    """Deliberately bad symbol: captures every error-payload shape.

    Returns:
        list[ProbeCase]: One INVALID_SYMBOL case per error-prone command.
    """

    chart_p1, chart_p2 = _days_ago_iso(5), _yesterday_iso()
    argvs: dict[str, tuple[str, ...]] = {
        "quote": ("quote", INVALID_SYMBOL),
        "quote-summary": ("quote-summary", INVALID_SYMBOL),
        "quote-type": ("quote-type", INVALID_SYMBOL),
        "chart": (
            "chart",
            INVALID_SYMBOL,
            "--period1",
            chart_p1,
            "--period2",
            chart_p2,
            "--interval",
            "1d",
        ),
        "spark": ("spark", INVALID_SYMBOL),
        "timeseries": ("timeseries", INVALID_SYMBOL),
        "analyst": ("analyst", INVALID_SYMBOL),
        "calendar-events": ("calendar-events", INVALID_SYMBOL),
        "recommendations-by-symbol": ("recommendations-by-symbol", INVALID_SYMBOL),
        "stock-recommender": ("stock-recommender", INVALID_SYMBOL),
        "price-insights": ("price-insights", INVALID_SYMBOL),
        "insights": ("insights", INVALID_SYMBOL),
        "ratings-top": ("ratings-top", INVALID_SYMBOL),
        "options": ("options", INVALID_SYMBOL),
    }
    return [ProbeCase(command, INVALID_SYMBOL, argv) for command, argv in argvs.items()]


# Cross-asset cases (the Part-4 chip item): insights/price-insights/
# recommendations-by-symbol were only probed against EQUITY_SUBSET
# (AAPL/MSFT/RY.TO); live checks during Part 3d found real applicability
# differences across asset classes that the corpus itself never captured.
# These five symbols mirror the AGENTS.md baseline probe's non-equity
# coverage (ETF, index, crypto, forex, futures) so the corpus can finally
# back those live-only findings with real evidence.
_CROSS_ASSET_SYMBOLS: Final[tuple[str, ...]] = (
    "SPY",
    "^GSPC",
    "BTC-USD",
    "EURUSD=X",
    "ES=F",
)


def _cross_asset_cases() -> list[ProbeCase]:
    """Cross-asset-class cases for insights/price-insights/recommendations.

    Returns:
        list[ProbeCase]: One case per command per ``_CROSS_ASSET_SYMBOLS``
        entry (15 cases).
    """

    cases: list[ProbeCase] = []
    for sym in _CROSS_ASSET_SYMBOLS:
        cases += [
            ProbeCase("insights", sym, ("insights", sym)),
            ProbeCase("price-insights", sym, ("price-insights", sym)),
            ProbeCase(
                "recommendations-by-symbol",
                sym,
                ("recommendations-by-symbol", sym),
            ),
        ]
    return cases


def _raw_case() -> list[ProbeCase]:
    """One raw-command envelope so the completeness gate covers `raw` too.

    Returns:
        list[ProbeCase]: A single raw quote request.
    """

    return [
        ProbeCase(
            "raw",
            "quote_AAPL",
            ("raw", "/v7/finance/quote", "--param", "symbols=AAPL"),
        )
    ]


def _first_contract_symbol(options_file: Path) -> str | None:
    """Pull the first call contract symbol from a saved options response.

    Returns:
        str | None: A live option contract symbol, or None if unavailable.
    """

    try:
        payload = json.loads(options_file.read_text(encoding="utf-8"))
        result = payload["optionChain"]["result"][0]
        return str(result["options"][0]["calls"][0]["contractSymbol"])
    except (OSError, ValueError, LookupError, TypeError):
        return None


def _contract_cases(contract: str) -> list[ProbeCase]:
    """Follow-up quote endpoints for a live option-contract symbol.

    Returns:
        list[ProbeCase]: quote/quote-type/quote-summary cases for the
        contract, mirroring the symbol matrix's field/module coverage.
    """

    qs_modules = _all_quote_summary_modules()
    return [
        ProbeCase("quote", "OPTION_CONTRACT", ("quote", contract)),
        ProbeCase("quote-type", "OPTION_CONTRACT", ("quote-type", contract)),
        ProbeCase(
            "quote-summary",
            "OPTION_CONTRACT",
            ("quote-summary", contract, "--modules", qs_modules),
        ),
    ]


def build_cases() -> list[ProbeCase]:
    """Full declarative probe plan.

    Returns:
        list[ProbeCase]: Every case, in execution order.
    """

    return (
        _symbol_cases()
        + _chart_variant_cases()
        + _timeseries_all_type_cases()
        + _equity_subset_cases()
        + _cross_asset_cases()
        + _calendar_events_populated_cases()
        + _market_cases()
        + _dsl_cases()
        + _invalid_cases()
        + _raw_case()
    )


async def _run_case(
    parser: argparse.ArgumentParser,
    client: _YahooClientProtocol,
    case: ProbeCase,
    corpus_dir: Path,
) -> dict[str, object]:
    """Execute one case through the CLI pipeline; write its body if any.

    Returns:
        dict[str, object]: The manifest entry for this case.
    """

    entry: dict[str, object] = {
        "argv": list(case.argv),
        "status": "ok",
        "http_status": 200,
    }
    body = ""
    try:
        namespace = parser.parse_args(list(case.argv))
        out = io.StringIO()
        await _dispatch_command(namespace, out, client)
        body = out.getvalue()
    except YahooRequestError as exc:
        entry["status"] = "http_error"
        entry["http_status"] = exc.status_code
        entry["detail"] = str(exc)
        body = exc.body or ""
    except (YoghurtError, ValueError) as exc:
        # ValueError covers the CLI's dispatch-time validation (bad chart
        # intervals, reversed date windows); a typo'd probe case should
        # become a manifest entry, not a crash.
        entry["status"] = "error"
        entry["http_status"] = None
        entry["detail"] = str(exc)
    if body and entry["status"] == "ok":
        try:
            json.loads(body)
        except ValueError as exc:
            # An HTTP-200 body that does not parse as JSON is Yahoo-side
            # corruption (see _QUARANTINED_EVENT_TYPES): record it as an
            # error with no corpus file, so a manifest "ok" always means
            # the capture parses. Judging feed health by HTTP status or
            # manifest "ok" alone has already produced one false
            # "Yahoo fixed the feed" alarm (2026-07-05).
            entry["status"] = "error"
            entry["detail"] = f"Yahoo response is not valid JSON: {exc}"
            return entry
    if body:
        relative = f"{case.command}/{sanitize(case.case)}.json"
        target = corpus_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        entry["file"] = relative
    return entry


def _write_manifest(
    manifest: dict[str, object], case_count: int, corpus_dir: Path
) -> None:
    """Attach the run metadata and write manifest.json to the corpus dir."""

    manifest["_meta"] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "case_count": case_count,
    }
    corpus_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = corpus_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


async def _run_all(cases: list[ProbeCase], corpus_dir: Path) -> None:
    """Run every case sequentially and write the corpus plus manifest.json."""

    parser = build_parser()
    client = YahooClient()
    manifest: dict[str, object] = {}
    try:
        # ponytail: sequential with a fixed delay; parallelize only if a full
        # run ever becomes painfully slow (politeness beats speed here).
        for index, case in enumerate(cases, start=1):
            key = f"{case.command}/{case.case}"
            print(f"[{index}/{len(cases)}] {key}", file=sys.stderr)
            manifest[key] = await _run_case(parser, client, case, corpus_dir)
            await asyncio.sleep(POLITENESS_DELAY_SECONDS)

        # A live option-contract symbol can only be resolved from the AAPL
        # options-chain response fetched earlier in this same run.
        contract = _first_contract_symbol(corpus_dir / "options" / "AAPL.json")
        if contract is None:
            print("no option contract resolved; skipping", file=sys.stderr)
        else:
            for case in _contract_cases(contract):
                key = f"{case.command}/{case.case}"
                print(key, file=sys.stderr)
                manifest[key] = await _run_case(parser, client, case, corpus_dir)
                await asyncio.sleep(POLITENESS_DELAY_SECONDS)
    finally:
        # Persist partial progress even if a case raises something
        # unexpected: hours of politely rate-limited evidence should
        # survive a crash on the last case.
        await client.aclose()
        # Actual manifest entries, not len(cases): the dynamically-resolved
        # option-contract follow-up cases add entries the static plan
        # doesn't know about ahead of time.
        _write_manifest(manifest, len(manifest), corpus_dir)


def main() -> int:
    """Run the full probe.

    Returns:
        int: Process exit code.
    """

    asyncio.run(_run_all(build_cases(), CORPUS_DIR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
