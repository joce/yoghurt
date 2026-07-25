"""Tests for the derived financial-analysis library and CLI surfaces."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, fields
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import yoghurt._core as core
from yoghurt.api import Ticker
from yoghurt.cli import main
from yoghurt.financial_analysis import (
    FINANCIAL_ANALYSIS_QUOTE_SUMMARY_MODULES,
    FINANCIAL_ANALYSIS_TIMESERIES_TYPES,
    FinancialAnalysis,
)

if TYPE_CHECKING:
    from typing import Any

    from yoghurt.types import ParamValue

_CORPUS_ROOT = Path(__file__).parent / "fixtures" / "corpus"
_NOW_EPOCH = 1_777_903_200
_SOURCE_REQUEST_COUNT = 2
_FUNDAMENTALS_COLUMNS = [
    "type",
    "as_of_date",
    "period_type",
    "currency_code",
    "value",
]
_EXPECTED_COLUMNS = {
    "income_statement": _FUNDAMENTALS_COLUMNS,
    "balance_sheet": _FUNDAMENTALS_COLUMNS,
    "cash_flow": _FUNDAMENTALS_COLUMNS,
    "valuation_history": _FUNDAMENTALS_COLUMNS,
    "earnings_estimates": [
        "period",
        "end_date",
        "currency",
        "avg",
        "low",
        "high",
        "year_ago_eps",
        "growth",
        "number_of_analysts",
    ],
    "revenue_estimates": [
        "period",
        "end_date",
        "currency",
        "avg",
        "low",
        "high",
        "year_ago_revenue",
        "growth",
        "number_of_analysts",
    ],
    "earnings_history": [
        "period",
        "quarter",
        "currency",
        "eps_estimate",
        "eps_actual",
        "eps_difference",
        "surprise_percent",
    ],
    "eps_trends": [
        "period",
        "end_date",
        "currency",
        "current",
        "seven_days_ago",
        "thirty_days_ago",
        "sixty_days_ago",
        "ninety_days_ago",
    ],
    "eps_revisions": [
        "period",
        "end_date",
        "currency",
        "up_last_7_days",
        "up_last_30_days",
        "down_last_7_days",
        "down_last_30_days",
        "down_last_90_days",
    ],
    "analyst_price_targets": [
        "currency",
        "current_price",
        "target_low_price",
        "target_mean_price",
        "target_median_price",
        "target_high_price",
        "number_of_analyst_opinions",
        "recommendation_key",
        "recommendation_mean",
    ],
    "growth_comparison": ["source", "symbol", "period", "end_date", "growth"],
    "major_holders_breakdown": [
        "insiders_percent_held",
        "institutions_count",
        "institutions_float_percent_held",
        "institutions_percent_held",
    ],
    "institutional_ownership": [
        "organization",
        "report_date",
        "pct_held",
        "pct_change",
        "position",
        "value",
    ],
    "fund_ownership": [
        "organization",
        "report_date",
        "pct_held",
        "pct_change",
        "position",
        "value",
    ],
    "insider_roster": [
        "name",
        "relation",
        "latest_transaction_date",
        "transaction_description",
        "position_direct",
        "position_direct_date",
        "position_indirect",
        "position_indirect_date",
        "position_summary",
        "position_summary_date",
    ],
    "insider_transactions": [
        "filer_name",
        "filer_relation",
        "start_date",
        "ownership",
        "shares",
        "value",
        "transaction_text",
    ],
    "insider_purchase_activity": [
        "period",
        "buy_info_count",
        "buy_info_shares",
        "buy_percent_insider_shares",
        "sell_info_count",
        "sell_info_shares",
        "sell_percent_insider_shares",
        "net_info_count",
        "net_info_shares",
        "net_percent_insider_shares",
        "total_insider_shares",
        "net_inst_shares_buying",
        "net_inst_buying_percent",
    ],
}


def _corpus_text(relative_path: str) -> str:
    return (_CORPUS_ROOT / relative_path).read_text(encoding="utf-8")


def _financial_timeseries_body() -> str:
    """Combine the three valid all-types corpus batches into one response."""

    results: list[dict[str, Any]] = []
    for filename in (
        "AAPL_types_01.json",
        "AAPL_types_02.json",
        "AAPL_types_03.json",
    ):
        payload = json.loads(_corpus_text(f"timeseries/{filename}"))
        results.extend(payload["timeseries"]["result"])
    return json.dumps({"timeseries": {"result": results, "error": None}})


class _FakeClient:
    """Route the two financial-analysis source requests to corpus captures."""

    def __init__(
        self,
        *,
        timeseries_body: str | None = None,
        quote_summary_fixture: str = "AAPL.json",
    ) -> None:
        self.calls: list[tuple[str, dict[str, ParamValue], bool]] = []
        self.closed = False
        self.timeseries_body = timeseries_body or _financial_timeseries_body()
        self.quote_summary_fixture = quote_summary_fixture
        self.returned_quote_summary_modules: set[str] = set()

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        del base_url
        self.calls.append((path, dict(params), use_crumb))
        if path.startswith("/ws/fundamentals-timeseries/"):
            return self.timeseries_body
        payload = json.loads(
            _corpus_text(f"quote-summary/{self.quote_summary_fixture}")
        )
        requested = params["modules"]
        if not isinstance(requested, str):
            message = "quote-summary modules must be a CSV string"
            raise TypeError(message)
        record = payload["quoteSummary"]["result"][0]
        filtered = {
            module: record[module]
            for module in requested.split(",")
            if module in record
        }
        self.returned_quote_summary_modules = set(filtered)
        if not filtered:
            payload["quoteSummary"] = {
                "result": None,
                "error": {
                    "code": "Not Found",
                    "description": "No fundamentals data found",
                },
            }
        else:
            payload["quoteSummary"]["result"] = [filtered]
        return json.dumps(payload)

    async def post(  # ruff:ignore[no-self-use] - protocol method must be present
        self,
        path: str,
        params: dict[str, ParamValue],
        json_body: dict[str, Any],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        del path, params, json_body, use_crumb, base_url
        message = "financial-analysis does not use POST"
        raise AssertionError(message)

    async def aclose(self) -> None:
        self.closed = True


def test_ticker_financial_analysis_uses_existing_retrievals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ticker orchestrates the two public retrieval paths into typed tables."""

    fake = _FakeClient()
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    monkeypatch.setattr("yoghurt.params.time.time", lambda: 1777903200.9)

    result = Ticker("AAPL").financial_analysis()

    assert isinstance(result, FinancialAnalysis)
    with pytest.raises(FrozenInstanceError):
        result.cash_flow = (  # pyright: ignore[reportAttributeAccessIssue]
            result.balance_sheet
        )
    assert {
        field.name: getattr(result, field.name).to_polars().columns
        for field in fields(result)
    } == _EXPECTED_COLUMNS
    assert result.income_statement.to_polars().height > 0
    assert result.balance_sheet.to_polars().height > 0
    assert result.cash_flow.to_polars().height > 0
    assert set(result.cash_flow.to_polars()["type"]) <= {
        type_name
        for type_name in FINANCIAL_ANALYSIS_TIMESERIES_TYPES
        if type_name.startswith("annual")
    }
    estimates = result.earnings_estimates.to_dicts()
    assert estimates[0]["currency"] == "USD"
    assert estimates[0]["end_date"].isoformat() == "2026-06-30"
    assert not result.earnings_history.to_polars().is_empty()
    growth = result.growth_comparison.to_polars()
    assert set(growth["source"]) == {"stock", "index"}
    assert growth["growth"].null_count() == 0
    assert not result.institutional_ownership.to_polars().is_empty()
    assert not result.insider_transactions.to_polars().is_empty()
    assert len(fake.calls) == _SOURCE_REQUEST_COUNT
    timeseries_path, timeseries_params, _ = fake.calls[0]
    assert timeseries_path.endswith("/AAPL")
    assert timeseries_params["period1"] == 0
    assert timeseries_params["period2"] == _NOW_EPOCH
    assert timeseries_params["type"] == ",".join(FINANCIAL_ANALYSIS_TIMESERIES_TYPES)
    assert {
        "annualOperatingCashFlow",
        "annualTotalAssets",
        "annualTotalRevenue",
        "quarterlyPeRatio",
    } <= set(FINANCIAL_ANALYSIS_TIMESERIES_TYPES)
    summary_path, summary_params, _ = fake.calls[1]
    assert summary_path == "/v10/finance/quoteSummary/AAPL"
    assert summary_params["modules"] == ",".join(
        FINANCIAL_ANALYSIS_QUOTE_SUMMARY_MODULES
    )
    assert "quoteType" in fake.returned_quote_summary_modules


def test_ticker_financial_analysis_keeps_empty_schemas_for_an_etf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inapplicable equity-only modules become empty, schema-bearing Frames."""

    fake = _FakeClient(
        timeseries_body=_corpus_text("timeseries/SPY.json"),
        quote_summary_fixture="SPY.json",
    )
    monkeypatch.setattr(core, "_get_client", lambda: fake)

    result = Ticker("SPY").financial_analysis()

    assert fake.returned_quote_summary_modules == {"quoteType"}
    for field in fields(result):
        table = getattr(result, field.name).to_polars()
        assert table.is_empty(), field.name
        assert table.columns, field.name


def test_ticker_financial_analysis_omits_empty_analyst_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Revenue coverage does not manufacture unavailable analysis rows."""

    fake = _FakeClient(quote_summary_fixture="BAC-PL.json")
    monkeypatch.setattr(core, "_get_client", lambda: fake)

    result = Ticker("BAC-PL").financial_analysis()

    assert not result.revenue_estimates.to_polars().is_empty()
    assert result.earnings_estimates.to_polars().is_empty()
    assert result.eps_trends.to_polars().is_empty()
    assert result.eps_revisions.to_polars().is_empty()
    assert result.analyst_price_targets.to_polars().is_empty()
    growth = result.growth_comparison.to_polars()
    assert set(growth["source"]) == {"index"}
    assert growth["growth"].null_count() == 0


def test_financial_analysis_cli_emits_one_json_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The derived CLI emits table names mapped to row arrays, JSON only."""

    fake = _FakeClient()
    stdout = StringIO()
    monkeypatch.setattr("yoghurt.params.time.time", lambda: 1777903200.9)

    exit_code = main(["financial-analysis", "AAPL"], stdout=stdout, client=fake)

    assert exit_code == 0
    assert fake.closed
    assert len(fake.calls) == _SOURCE_REQUEST_COUNT
    payload = json.loads(stdout.getvalue())
    assert list(payload) == list(_EXPECTED_COLUMNS)
    assert payload["earnings_estimates"][0]["end_date"] == "2026-06-30"
    assert payload["valuation_history"] == []


def test_financial_analysis_help_is_derived_json_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Help identifies the two-source derived command and its fixed output."""

    with pytest.raises(SystemExit) as exc_info:
        main(["financial-analysis", "--help"])

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    assert "SYMBOL" in help_text
    assert "derived command combines" in help_text
    assert "Output is JSON only" in help_text
    assert "income_statement:" in help_text
    assert "insider_purchase_activity:" in help_text
    assert "--format" not in help_text
    assert "Yahoo endpoint:" not in help_text


def test_financial_analysis_help_order(capsys: pytest.CaptureFixture[str]) -> None:
    """The derived bundle follows its source timeseries command in root help."""

    with pytest.raises(SystemExit):
        main(["--help"])

    help_text = capsys.readouterr().out
    assert (
        help_text.index("\n    timeseries ")
        < help_text.index("\n    financial-analysis ")
        < help_text.index("\n    calendar-events ")
    )
