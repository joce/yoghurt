"""Round-trip tests for typed batch 3e-2 models against real captures.

The corpus coverage gate (``tests/models/test_screener_meta_corpus.py``)
proves every valid capture validates with no extras; these tests instead
check representative typed attributes: the nested field-category/criteria
shape, the closed-vocabulary enums, and the screener-discover quote reuse
decision.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yoghurt.models.screener_meta import (
    ScreenerCriteriaOperator,
    ScreenerDiscoverResult,
    ScreenerFieldType,
    ScreenerInstrumentFieldsResult,
    ScreenerPredefinedResult,
    TimeseriesFieldsResult,
)

_CORPUS_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "corpus"


def _load(relative_path: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        (_CORPUS_ROOT / relative_path).read_text(encoding="utf-8")
    )
    return payload


def test_screener_field_beta_carries_nested_category_and_criteria() -> None:
    """The 'beta' equity field nests category and quick-pick criteria chips."""

    payload = _load("screener-instrument-fields/equity.json")
    result = ScreenerInstrumentFieldsResult.model_validate(
        payload["finance"]["result"][0]
    )
    beta = result.fields["beta"]

    assert beta.type is ScreenerFieldType.NUMBER
    assert beta.category.category_id == "keystats"
    assert beta.labels[0].criteria.operator is ScreenerCriteriaOperator.LT
    assert beta.labels[0].criteria.operands == ["beta", -0.2]


def test_screener_field_dependent_pair_links_sector_and_industry() -> None:
    """analyst_ratings' sector/industry fields cross-reference each other."""

    payload = _load("screener-instrument-fields/analyst_ratings.json")
    result = ScreenerInstrumentFieldsResult.model_validate(
        payload["finance"]["result"][0]
    )

    assert result.fields["sector"].depend_for == ["industry"]
    assert result.fields["industry"].dependent_field == "sector"


def test_timeseries_fields_result_lists_field_classes() -> None:
    """TimeSeriesDataClass rows expose displayName/dataType pairs."""

    payload = _load("timeseries-fields/default.json")
    result = TimeseriesFieldsResult.model_validate(
        payload["timeseriesfields"]["result"][0]
    )

    corporate_deals = next(
        row
        for row in result.time_series_data_class
        if row.data_type == "sigdev_corporate_deals"
    )
    assert corporate_deals.display_name == "Corporate Deals"


def test_screener_discover_quotes_are_typed_screener_discover_quote_rows() -> None:
    """The discover endpoint's quotes dict validates as ScreenerDiscoverQuote."""

    payload = _load("screener-discover/default.json")
    result = ScreenerDiscoverResult.model_validate(payload["finance"]["result"])

    msft = result.quotes["MSFT"]
    assert msft.symbol == "MSFT"
    assert msft.average_analyst_rating == "1.3 - Strong Buy"


def test_screener_discover_accepts_live_observed_missing_quote_fields() -> None:
    """French-region warrants may omit first-trade time and short name."""

    payload = _load("screener-discover/default.json")
    quote = payload["finance"]["result"]["quotes"]["MSFT"]
    del quote["firstTradeDateMilliseconds"]
    del quote["shortName"]

    result = ScreenerDiscoverResult.model_validate(payload["finance"]["result"])

    msft = result.quotes["MSFT"]
    assert msft.first_trade_date_milliseconds is None
    assert msft.short_name is None


def test_screener_discover_idea_sections_expose_canonical_names() -> None:
    """ScreenersList rows carry stable canonicalName identifiers."""

    payload = _load("screener-discover/default.json")
    result = ScreenerDiscoverResult.model_validate(payload["finance"]["result"])

    names = {
        section.canonical_name
        for section in result.sections.neo_investment_ideas.screeners_list
    }
    assert "MOST_ACTIVES" in names
    assert "DAY_GAINERS" in names


def test_screener_predefined_result_types_criteria_meta_and_leaves_records_raw() -> (
    None
):
    """ScreenerPredefinedResult types criteriaMeta but leaves records as dicts."""

    payload = _load("screener-predefined/MOST_ACTIVES.json")
    result = ScreenerPredefinedResult.model_validate(payload["finance"]["result"][0])

    assert result.canonical_name == "MOST_ACTIVES"
    assert result.criteria_meta.quote_type == "EQUITY"
    assert result.criteria_meta.sort_field == "dayvolume"
    assert isinstance(result.records, list)
    assert isinstance(result.records[0], dict)
    assert result.records[0]["ticker"] == "AAL"
