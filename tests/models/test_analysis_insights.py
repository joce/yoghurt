"""Round-trip tests for typed batch 3d-1 insights models against real captures.

The corpus coverage gate (``tests/models/test_analysis_insights_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes: the price-insights tri-variant shape and
the insights thin-vs-rich capture divergence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yoghurt.models.analysis_insights import AiAnalysisData, Insights, PriceInsights

_CORPUS_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "corpus"


def _load(relative_path: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        (_CORPUS_ROOT / relative_path).read_text(encoding="utf-8")
    )
    return payload


def test_price_insights_default_variant_has_every_block() -> None:
    """The default AAPL capture populates every top-level block."""

    payload = _load("price-insights/AAPL.json")
    record = payload["finance"]["result"]["AAPL"]
    result = PriceInsights.model_validate(record)

    assert result.has_price_anomaly is True
    assert result.news_first_party is not None
    assert result.news_third_party is not None
    assert result.news_third_party.news
    assert result.ai_analysis is not None
    assert isinstance(result.ai_analysis.data, AiAnalysisData)
    assert result.analyst_rating is not None
    assert result.analyst_rating.history == []


def test_price_insights_thin_symbol_has_empty_ai_data() -> None:
    """RY.TO's aiAnalysis.data is an empty dict, not the full AiAnalysisData shape."""

    payload = _load("price-insights/RY.TO.json")
    record = payload["finance"]["result"]["RY.TO"]
    result = PriceInsights.model_validate(record)

    assert result.ai_analysis is not None
    assert result.ai_analysis.data == {}
    assert result.news_first_party is not None
    assert result.news_first_party.news == []


def test_price_insights_ai_only_variant_omits_news_and_rating() -> None:
    """The AI-only capture has aiAnalysis but no news blocks or analyst rating."""

    payload = _load("price-insights/AAPL_ai.json")
    record = payload["finance"]["result"]["AAPL"]
    result = PriceInsights.model_validate(record)

    assert result.has_price_anomaly is True
    assert result.ai_analysis is not None
    assert result.news_first_party is None
    assert result.news_third_party is None
    assert result.analyst_rating is None


def test_price_insights_anomaly_only_variant_omits_everything_else() -> None:
    """The anomaly-only capture has only has_price_anomaly populated."""

    payload = _load("price-insights/AAPL_anomaly.json")
    record = payload["finance"]["result"]["AAPL"]
    result = PriceInsights.model_validate(record)

    assert result.has_price_anomaly is False
    assert result.ai_analysis is None
    assert result.news_first_party is None
    assert result.news_third_party is None
    assert result.analyst_rating is None


def test_price_insights_price_movement_observations_is_a_dynamic_dict() -> None:
    """price_movement.explanation.observations keys are AI-generated headlines."""

    payload = _load("price-insights/AAPL.json")
    record = payload["finance"]["result"]["AAPL"]
    result = PriceInsights.model_validate(record)

    assert result.ai_analysis is not None
    data = result.ai_analysis.data
    assert isinstance(data, AiAnalysisData)
    observations = data.price_movement.explanation.observations
    assert "Market context" in observations
    assert isinstance(observations["Market context"], str)


def test_insights_rich_capture_has_every_optional_block() -> None:
    """AAPL's insights capture populates every optional block."""

    payload = _load("insights/AAPL.json")
    result = Insights.model_validate(payload["finance"]["result"][0])

    assert result.symbol == "AAPL"
    assert result.company_snapshot is not None
    assert result.events is not None
    assert result.instrument_info is not None
    assert result.reports is not None
    assert result.sec_reports is not None
    assert result.upsell_search_d_d is not None
    assert result.instrument_info.valuation.relative_value == "Premium"


def test_insights_thin_capture_omits_every_optional_block() -> None:
    """RY.TO's insights capture only populates the four universal fields."""

    payload = _load("insights/RY.TO.json")
    result = Insights.model_validate(payload["finance"]["result"][0])

    assert result.symbol == "RY.TO"
    assert result.company_snapshot is None
    assert result.events is None
    assert result.instrument_info is None
    assert result.reports is None
    assert result.sec_reports is None
    assert result.upsell_search_d_d is None
    assert result.recommendation.rating == "BUY"


def test_insights_valuation_relative_value_absent_on_msft() -> None:
    """MSFT's valuation block omits relative_value (present only on AAPL)."""

    payload = _load("insights/MSFT.json")
    result = Insights.model_validate(payload["finance"]["result"][0])

    assert result.instrument_info is not None
    assert result.instrument_info.valuation.relative_value is None


def test_insights_analyst_report_row_carries_target_price() -> None:
    """The one Analyst-Report-type row carries target_price/investment_rating."""

    payload = _load("insights/AAPL.json")
    result = Insights.model_validate(payload["finance"]["result"][0])

    assert result.reports is not None
    analyst_rows = [row for row in result.reports if row.target_price is not None]
    assert len(analyst_rows) == 1
    assert analyst_rows[0].investment_rating is not None


def test_insights_sec_report_exhibit_download_url_is_optional() -> None:
    """Most exhibits have no download_url; a few EXCEL-type ones do."""

    payload = _load("insights/AAPL.json")
    result = Insights.model_validate(payload["finance"]["result"][0])

    assert result.sec_reports is not None
    exhibits = [exhibit for report in result.sec_reports for exhibit in report.exhibits]
    with_download = [e for e in exhibits if e.download_url is not None]
    without_download = [e for e in exhibits if e.download_url is None]
    assert with_download
    assert without_download
