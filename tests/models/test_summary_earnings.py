"""Round-trip tests for typed batch c2 earnings-family models against real captures.

The corpus coverage gate (``tests/models/test_summary_earnings_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes: the ``earnings``/``earningsGaap``/
``earningsNonGaap`` shared-shape-divergent-data relationship, RawDate/
RawFloat unwrapping in ``earningsHistory``, the ``{}``-means-``None``
extension on ``earningsTrend`` (``BAC-PL``'s no-analyst-coverage rows),
and the not-yet-reported quarter's outright-absent fields (``OKLO``).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from yoghurt.models.summary_earnings import (
    EarningsCallTranscripts,
    EarningsHistory,
    EarningsModule,
    EarningsTrend,
)

_CORPUS_QUOTE_SUMMARY_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote-summary"
)

_AAPL_EPS_ACTUAL = 1.57
_AAPL_EPS_ESTIMATE = 1.42572


def _load_module(filename: str, module: str) -> dict[str, Any]:
    payload = json.loads(
        (_CORPUS_QUOTE_SUMMARY_DIR / filename).read_text(encoding="utf-8")
    )
    result: dict[str, Any] = payload["quoteSummary"]["result"][0][module]
    return result


def test_earnings_and_earnings_gaap_share_shape_but_diverge_in_data() -> None:
    """AAPL's earnings mirrors earningsGaap (its defaultMethodology) exactly.

    earningsNonGaap uses the same EarningsModule shape but carries
    different EPS estimate figures (non-GAAP adjustments), proving the
    "same shape, different data" relationship documented in the module
    docstring.
    """

    earnings = EarningsModule.model_validate(_load_module("AAPL.json", "earnings"))
    earnings_gaap = EarningsModule.model_validate(
        _load_module("AAPL.json", "earningsGaap")
    )
    earnings_non_gaap = EarningsModule.model_validate(
        _load_module("AAPL.json", "earningsNonGaap")
    )

    assert earnings.default_methodology == "gaap"
    assert earnings.earnings_chart == earnings_gaap.earnings_chart
    assert earnings.earnings_chart != earnings_non_gaap.earnings_chart


def test_earnings_chart_quarter_period_end_date_is_calendar_date() -> None:
    """earningsChart.quarterly[].periodEndDate is a tier-1 UTC calendar date."""

    earnings = EarningsModule.model_validate(_load_module("AAPL.json", "earnings"))

    first_quarter = earnings.earnings_chart.quarterly[0]
    assert first_quarter.period_end_date == datetime.date(2025, 6, 30)
    assert isinstance(first_quarter.period_end_date, datetime.date)
    assert not isinstance(first_quarter.period_end_date, datetime.datetime)


def test_earnings_chart_quarter_reported_date_is_session_anchored_datetime() -> None:
    """earningsChart.quarterly[].reportedDate is a tier-3 aware-UTC datetime."""

    earnings = EarningsModule.model_validate(_load_module("AAPL.json", "earnings"))

    first_quarter = earnings.earnings_chart.quarterly[0]
    assert first_quarter.reported_date is not None
    assert first_quarter.reported_date.tzinfo is not None
    assert first_quarter.reported_date.time() != datetime.time(0, 0, 0)


def test_earnings_chart_quarter_missing_actual_for_unreported_quarter() -> None:
    """OKLO's forward quarter omits actual/difference/reportedDate/surprisePct."""

    earnings = EarningsModule.model_validate(_load_module("OKLO.json", "earnings"))

    forward_quarter = earnings.earnings_chart.quarterly[-1]
    assert forward_quarter.actual is None
    assert forward_quarter.difference is None
    assert forward_quarter.reported_date is None
    assert forward_quarter.surprise_pct is None
    assert forward_quarter.estimate is not None


def test_financials_chart_yearly_date_is_bare_year_int() -> None:
    """financialsChart.yearly[].date is a bare year int, unlike quarterly's label."""

    earnings = EarningsModule.model_validate(_load_module("AAPL.json", "earnings"))

    first_year = earnings.financials_chart.yearly[0]
    assert isinstance(first_year.date, int)
    assert first_year.date == 2022  # noqa: PLR2004 - the corpus's first observed year


def test_earnings_history_unwraps_raw_fmt_wrapper_from_real_capture() -> None:
    """earningsHistory.history[] unwraps {raw, fmt} for EPS and quarter fields."""

    history = EarningsHistory.model_validate(
        _load_module("AAPL.json", "earningsHistory")
    )

    first_entry = history.history[0]
    assert first_entry.eps_actual == _AAPL_EPS_ACTUAL
    assert isinstance(first_entry.eps_actual, float)
    assert first_entry.eps_estimate == _AAPL_EPS_ESTIMATE
    assert first_entry.quarter == datetime.date(2025, 6, 30)
    assert isinstance(first_entry.quarter, datetime.date)


def test_earnings_history_missing_actual_for_unreported_quarter() -> None:
    """OKLO's forward entry omits epsActual/epsDifference/surprisePercent."""

    history = EarningsHistory.model_validate(
        _load_module("OKLO.json", "earningsHistory")
    )

    forward_entry = history.history[-1]
    assert forward_entry.eps_actual is None
    assert forward_entry.eps_difference is None
    assert forward_entry.surprise_percent is None
    assert forward_entry.eps_estimate is not None


def test_earnings_trend_end_date_parses_bare_iso_string() -> None:
    """earningsTrend.trend[].endDate is a bare ISO date string, not epoch-based."""

    trend = EarningsTrend.model_validate(_load_module("AAPL.json", "earningsTrend"))

    first_entry = trend.trend[0]
    assert first_entry.period == "0q"
    assert first_entry.end_date == datetime.date(2026, 6, 30)


def test_earnings_trend_eps_revisions_down_last_90_days_is_always_none() -> None:
    """epsRevisions.downLast90days unwraps {} to None on every AAPL trend row."""

    trend = EarningsTrend.model_validate(_load_module("AAPL.json", "earningsTrend"))

    assert all(entry.eps_revisions.down_last_90_days is None for entry in trend.trend)


def test_earnings_trend_empty_wrappers_unwrap_to_none_for_no_coverage_symbol() -> None:
    """BAC-PL's no-analyst-coverage rows unwrap every {} wrapper to None.

    This is the corpus's proving ground for the {}-means-None extension to
    the Raw* unwrap rule: growth, earningsEstimate, epsTrend, and
    epsRevisions are all sent as {} rather than omitted or populated.
    """

    trend = EarningsTrend.model_validate(_load_module("BAC-PL.json", "earningsTrend"))

    first_entry = trend.trend[0]
    assert first_entry.growth is None
    assert first_entry.earnings_estimate.avg is None
    assert first_entry.earnings_estimate.number_of_analysts is None
    assert first_entry.earnings_estimate.earnings_currency is None
    assert first_entry.eps_trend.current is None
    assert first_entry.eps_trend.eps_trend_currency is None
    assert first_entry.eps_revisions.up_last_7_days is None
    assert first_entry.eps_revisions.eps_revisions_currency is None
    # revenueEstimate has real analyst coverage even when EPS doesn't.
    assert first_entry.revenue_estimate.avg is not None


def test_earnings_call_transcripts_dates_are_session_anchored_datetimes() -> None:
    """earningsCallTranscripts.transcripts[].date/.updated are tier-3 datetimes."""

    transcripts = EarningsCallTranscripts.model_validate(
        _load_module("AAPL.json", "earningsCallTranscripts")
    )

    first_transcript = transcripts.transcripts[0]
    assert first_transcript.date.tzinfo is not None
    assert first_transcript.updated.tzinfo is not None
    assert first_transcript.date.time() != datetime.time(0, 0, 0)
