"""Round-trip tests for typed batch 3d-2 models against real captures.

The corpus coverage gate (``tests/models/test_analysis_ratings_corpus.py``)
proves every valid capture validates with no extras; these tests instead
check representative typed attributes: the analyst-service sub-tree reuse,
the ``dir`` keyword/builtin-shadow resolution, and the top-ratings
bucket-vs-row field-name collision.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import pytest

from yoghurt.models.analysis_insights import NewsSummaryBlock, PriceMovement
from yoghurt.models.analysis_ratings import AnalystResult, TopRatingsResult

_MM_ROW_MM_SCORE = 45.526952490124216
_MM_ROW_PT_SCORE = 49.47620419141286
_DIR_ROW_DIR_SCORE = 78.19956282236427

_CORPUS_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "corpus"


def _load(relative_path: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        (_CORPUS_ROOT / relative_path).read_text(encoding="utf-8")
    )
    return payload


def test_analyst_price_movement_validates_as_shared_model() -> None:
    """The analyst price_movement block round-trips as the shared PriceMovement."""

    payload = _load("analyst/AAPL.json")
    result = AnalystResult.model_validate(payload)

    assert isinstance(result.price_movement, PriceMovement)
    assert result.price_movement.ticker == "AAPL"


def test_analyst_news_summary_validates_as_shared_model() -> None:
    """The analyst news_summary block round-trips as the shared NewsSummaryBlock."""

    payload = _load("analyst/AAPL.json")
    result = AnalystResult.model_validate(payload)

    assert isinstance(result.news_summary, NewsSummaryBlock)
    assert result.news_summary.news_summary.id == "AAPL"


def test_analyst_options_analysis_pcr_populated() -> None:
    """options_analysis carries the put/call ratio block."""

    payload = _load("analyst/AAPL.json")
    result = AnalystResult.model_validate(payload)

    assert result.options_analysis.pcr.underlying_symbol == "AAPL"
    assert result.options_analysis.options_data == {}


def test_analyst_earnings_transcripts_fiscal_year_is_a_string() -> None:
    """earnings_transcripts_insights.fiscal_year is a wire string.

    Unlike the financial_insights int fields of the same name.
    """

    payload = _load("analyst/AAPL.json")
    result = AnalystResult.model_validate(payload)

    assert result.earnings_transcripts_insights.fiscal_year == "2026"
    assert isinstance(
        result.financial_insights.latest_earnings_metadata.fiscal_year, int
    )


def test_analyst_key_insights_structured_is_dynamically_keyed() -> None:
    """key_insights_structured has no fixed key vocabulary at either level."""

    payload = _load("analyst/MSFT.json")
    result = AnalystResult.model_validate(payload)

    structured = (
        result.earnings_transcripts_insights.earnings_analysis.key_insights_structured
    )
    assert "Outlook" in structured
    assert isinstance(structured["Outlook"], dict)


def test_analyst_msft_matches_aapl_shape() -> None:
    """MSFT's capture validates with the identical top-level key set as AAPL."""

    payload = _load("analyst/MSFT.json")
    result = AnalystResult.model_validate(payload)

    assert result.symbol_id
    assert result.price_movement.ticker == "MSFT"


def test_ratings_top_row_dir_field_uses_wire_alias() -> None:
    """The dir keyword/builtin-shadow resolves via Field(alias='dir')."""

    payload = _load("ratings-top/AAPL.json")
    result = TopRatingsResult.model_validate(payload)

    row = result.dir
    assert row.analyst == "CLSA"
    assert row.dir == pytest.approx(_DIR_ROW_DIR_SCORE)


def test_ratings_top_bucket_and_row_dir_are_distinct_concepts() -> None:
    """The top-level `dir` bucket and the row's own `dir` score differ in value."""

    payload = _load("ratings-top/AAPL.json")
    result = TopRatingsResult.model_validate(payload)

    bucket_row = result.dir
    assert bucket_row.dir != bucket_row.mm
    assert bucket_row.dir != bucket_row.pt
    assert bucket_row.dir != bucket_row.fin_score


def test_ratings_top_wrapped_scores_unwrap_to_raw_float() -> None:
    """dir/mm/pt/fin_score on the row unwrap {raw, fmt} to the bare float."""

    payload = _load("ratings-top/MSFT.json")
    result = TopRatingsResult.model_validate(payload)

    row = result.mm
    assert row.mm == pytest.approx(_MM_ROW_MM_SCORE)
    assert row.pt == pytest.approx(_MM_ROW_PT_SCORE)


def test_ratings_top_announcement_date_parses_as_date() -> None:
    """announcement_date is a bare YYYY-MM-DD string parsed to datetime.date."""

    payload = _load("ratings-top/AAPL.json")
    result = TopRatingsResult.model_validate(payload)

    assert result.pt.announcement_date == datetime.date(2025, 9, 10)


def test_ratings_top_all_four_buckets_present() -> None:
    """Every capture populates all four dir/mm/pt/fin_score buckets."""

    payload = _load("ratings-top/MSFT.json")
    result = TopRatingsResult.model_validate(payload)

    assert result.dir.ticker == "MSFT"
    assert result.mm.ticker == "MSFT"
    assert result.pt.ticker == "MSFT"
    assert result.fin_score.ticker == "MSFT"
