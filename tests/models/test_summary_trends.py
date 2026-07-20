"""Round-trip tests for typed batch c3 trend/filing models against real captures.

The corpus coverage gate (``tests/models/test_summary_trends_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes: ``secFilings``' calendar-date epoch vs. its
redundant bare-string sibling, the optional ``downloadUrl`` exhibit field,
``upgradeDowngradeHistory``'s session-anchored epoch and empty-string
``fromGrade``/``priceTargetAction`` values, and the
``indexTrend``/``sectorTrend``/``industryTrend`` shared-model reuse across
both a populated and an always-empty capture.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from yoghurt.models.summary_trends import (
    RecommendationTrend,
    SecFilings,
    TrendEstimateGroup,
    UpgradeDowngradeHistory,
)

_CORPUS_QUOTE_SUMMARY_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote-summary"
)


def _load_module(filename: str, module: str) -> dict[str, Any]:
    payload = json.loads(
        (_CORPUS_QUOTE_SUMMARY_DIR / filename).read_text(encoding="utf-8")
    )
    result: dict[str, Any] = payload["quoteSummary"]["result"][0][module]
    return result


def test_sec_filings_epoch_date_and_date_agree_and_parse_as_calendar_dates() -> None:
    """secFilings.filings[].epochDate/date both resolve to the same calendar date."""

    filings = SecFilings.model_validate(_load_module("AAPL.json", "secFilings"))

    first_filing = filings.filings[0]
    assert first_filing.epoch_date == datetime.date(2026, 5, 28)
    assert first_filing.date == datetime.date(2026, 5, 28)
    assert isinstance(first_filing.epoch_date, datetime.date)
    assert not isinstance(first_filing.epoch_date, datetime.datetime)


def test_sec_filings_exhibit_download_url_is_optional() -> None:
    """SecFilingExhibit.download_url is present only on EXCEL-type exhibits."""

    filings = SecFilings.model_validate(_load_module("AAPL.json", "secFilings"))

    excel_exhibits = [
        exhibit
        for filing in filings.filings
        for exhibit in filing.exhibits
        if exhibit.type == "EXCEL"
    ]
    non_excel_exhibits = [
        exhibit
        for filing in filings.filings
        for exhibit in filing.exhibits
        if exhibit.type != "EXCEL"
    ]

    assert excel_exhibits
    assert all(exhibit.download_url is not None for exhibit in excel_exhibits)
    assert non_excel_exhibits
    assert all(exhibit.download_url is None for exhibit in non_excel_exhibits)


def test_recommendation_trend_rows_are_bare_int_counts() -> None:
    """recommendationTrend.trend[] fields are plain ints, never Raw* wrappers."""

    trend = RecommendationTrend.model_validate(
        _load_module("AAPL.json", "recommendationTrend")
    )

    current = trend.trend[0]
    assert current.period == "0m"
    assert isinstance(current.strong_buy, int)
    assert isinstance(current.buy, int)
    assert isinstance(current.hold, int)
    assert isinstance(current.sell, int)
    assert isinstance(current.strong_sell, int)


def test_upgrade_downgrade_history_epoch_grade_date_is_session_anchored() -> None:
    """The history[].epochGradeDate field is a tier-3 aware-UTC datetime."""

    history = UpgradeDowngradeHistory.model_validate(
        _load_module("AAPL.json", "upgradeDowngradeHistory")
    )

    first_entry = history.history[0]
    assert first_entry.epoch_grade_date.tzinfo is not None
    assert first_entry.epoch_grade_date.time() != datetime.time(0, 0, 0)


def test_upgrade_downgrade_history_empty_strings_are_real_values() -> None:
    """BABA's initiating-coverage rows send '' for fromGrade (no prior grade).

    AAPL separately has 'reit' rows with '' for priceTargetAction (no
    price-target action accompanied the reiteration). Both are genuine
    observed empty-string values, not a stand-in for null - both fields
    stay plain non-nullable str.
    """

    baba_history = UpgradeDowngradeHistory.model_validate(
        _load_module("BABA.json", "upgradeDowngradeHistory")
    )
    init_entries = [entry for entry in baba_history.history if entry.action == "init"]
    assert init_entries
    assert all(not entry.from_grade for entry in init_entries)

    aapl_history = UpgradeDowngradeHistory.model_validate(
        _load_module("AAPL.json", "upgradeDowngradeHistory")
    )
    no_price_target_action_entries = [
        entry for entry in aapl_history.history if not entry.price_target_action
    ]
    assert no_price_target_action_entries


def test_index_trend_and_sector_trend_share_one_model_with_divergent_data() -> None:
    """indexTrend/sectorTrend validate through the same model but hold different data.

    indexTrend is always populated (symbol "SP5", 5 estimates) while
    sectorTrend is always the empty stub (null symbol, no estimates) in
    this corpus - same shape, genuinely different data, mirroring the
    earnings/earningsGaap/earningsNonGaap precedent from batch c2.
    """

    index_trend = TrendEstimateGroup.model_validate(
        _load_module("AAPL.json", "indexTrend")
    )
    sector_trend = TrendEstimateGroup.model_validate(
        _load_module("AAPL.json", "sectorTrend")
    )

    assert type(index_trend) is type(sector_trend)
    assert index_trend.symbol == "SP5"
    # Corpus-observed count.
    assert len(index_trend.estimates) == 5  # ruff:ignore[magic-value-comparison]
    assert sector_trend.symbol is None
    assert sector_trend.estimates == []


def test_index_trend_estimates_carry_bare_float_growth_and_period_label() -> None:
    """indexTrend.estimates[] rows are bare floats/strings, never wrapped."""

    index_trend = TrendEstimateGroup.model_validate(
        _load_module("AAPL.json", "indexTrend")
    )

    first_estimate = index_trend.estimates[0]
    assert first_estimate.period == "0q"
    assert isinstance(first_estimate.growth, float)
