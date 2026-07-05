"""Tests for the public synchronous Ticker API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pydantic
import pytest

import yoghurt._core as core
from yoghurt.api import Ticker
from yoghurt.exceptions import SymbolNotFoundError, YahooApiError, YahooRequestError
from yoghurt.frames import Spark, Timeseries
from yoghurt.models import (
    AnalystResult,
    CalendarEventsResult,
    ChartEvents,
    ChartMeta,
    Insights,
    OptionChain,
    PriceInsights,
    Quote,
    QuoteSummary,
    QuoteType,
    QuoteTypeResult,
    RecommendationsResult,
    StockRecommenderResult,
    TopRatingsResult,
)
from yoghurt.tabular import TabularShapeError

if TYPE_CHECKING:
    from typing import Any

    from yoghurt.types import ParamValue

_CORPUS_ROOT = Path(__file__).parent / "fixtures" / "corpus"
_IMG_SIZE = 50


def _corpus_text(relative_path: str) -> str:
    """Read a corpus fixture body as text.

    Returns:
        str: The raw fixture file contents.
    """

    return (_CORPUS_ROOT / relative_path).read_text(encoding="utf-8")


class _FakeClient:
    """Minimal stand-in for YahooClient that records calls and returns a body."""

    def __init__(self, body: str) -> None:
        """Store the canned response body."""
        self.body = body
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Record the call and return the canned body.

        Returns:
            str: The canned response body.
        """
        del use_crumb, base_url
        self.calls.append((path, dict(params)))
        return self.body

    async def post(
        self,
        path: str,
        params: dict[str, ParamValue],
        json_body: dict[str, Any],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Record the call and return the canned body.

        Returns:
            str: The canned response body.
        """
        del use_crumb, base_url
        self.calls.append((path, {"params": dict(params), "body": json_body}))
        return self.body

    async def aclose(self) -> None:
        """No-op close."""


def _install_fake(monkeypatch: pytest.MonkeyPatch, body: str) -> _FakeClient:
    """Patch the core client seam with a fake that returns ``body``.

    Returns:
        _FakeClient: The installed fake, for call-inspection assertions.
    """

    fake = _FakeClient(body)
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    return fake


_HTTP_NOT_FOUND = 404


class _ErrClient(_FakeClient):
    """A fake client whose ``get``/``post`` raise a 404 with ``body``."""

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Raise a 404 YahooRequestError carrying the canned body."""
        del path, params, use_crumb, base_url
        raise YahooRequestError(_HTTP_NOT_FOUND, "https://x", body=self.body)


def _install_fake_error(monkeypatch: pytest.MonkeyPatch, body: str) -> _ErrClient:
    """Patch the core client seam with a fake whose calls raise a 404.

    Returns:
        _ErrClient: The installed fake, for call-inspection assertions.
    """

    fake = _ErrClient(body)
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    return fake


def test_ticker_quote_returns_single_record(monkeypatch: pytest.MonkeyPatch) -> None:
    """quote() unwraps the one-record result list into a typed Quote."""
    _install_fake(monkeypatch, _corpus_text("quote/AAPL_default.json"))
    record = Ticker("AAPL").quote()
    assert isinstance(record, Quote)
    assert record.symbol == "AAPL"
    assert record.quote_type is QuoteType.EQUITY


def test_ticker_quote_empty_result_raises_symbol_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yahoo's 200-with-empty-result shape becomes SymbolNotFoundError."""
    _install_fake(monkeypatch, _corpus_text("quote/ZZZZXYZQ.json"))
    with pytest.raises(SymbolNotFoundError):
        Ticker("ZZZZXYZQ").quote()


def test_ticker_quote_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A record that fails Quote validation surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("quote/AAPL_default.json"))
    payload["quoteResponse"]["result"][0]["regularMarketPrice"] = "abc"
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").quote()
    assert exc_info.value.code == "model-validation"
    assert type(exc_info.value) is YahooApiError
    assert isinstance(exc_info.value.__cause__, pydantic.ValidationError)


def test_ticker_quote_passes_new_wire_params(monkeypatch: pytest.MonkeyPatch) -> None:
    """Typed quote kwargs land under their Yahoo wire names and forms."""
    fake = _install_fake(monkeypatch, _corpus_text("quote/AAPL_default.json"))
    Ticker("AAPL").quote(formatted=True, img_labels=["logoUrl"], img_heights=_IMG_SIZE)
    _, params = fake.calls[0]
    assert params["formatted"] is True
    assert params["imgLabels"] == "logoUrl"
    assert params["imgHeights"] == _IMG_SIZE


def test_ticker_quote_type_returns_single_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """quote_type() unwraps the one-record result list into a typed QuoteTypeResult."""
    fake = _install_fake(monkeypatch, _corpus_text("quote-type/AAPL.json"))
    record = Ticker("AAPL").quote_type()
    assert isinstance(record, QuoteTypeResult)
    assert record.symbol == "AAPL"
    path, _ = fake.calls[0]
    assert path == "/v1/finance/quoteType/AAPL"


def test_ticker_quote_type_empty_result_raises_symbol_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yahoo's 200-with-empty-result quoteType shape becomes SymbolNotFoundError."""
    _install_fake(monkeypatch, _corpus_text("quote-type/ZZZZXYZQ.json"))
    with pytest.raises(SymbolNotFoundError):
        Ticker("ZZZZXYZQ").quote_type()


def test_ticker_quote_type_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A record that fails QuoteTypeResult validation surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("quote-type/AAPL.json"))
    del payload["quoteType"]["result"][0]["symbol"]
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").quote_type()
    assert exc_info.value.code == "model-validation"


def test_ticker_chart_builds_typed_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    """chart() returns a Chart whose frame has the fixed schema and typed meta."""
    _install_fake(monkeypatch, _corpus_text("chart/AAPL.json"))
    chart = Ticker("AAPL").chart()
    assert chart.to_polars().columns == [
        "ts",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adj_close",
    ]
    assert isinstance(chart.meta, ChartMeta)
    assert chart.meta.currency == "USD"
    assert chart.events is None


def test_ticker_chart_all_defaults_sends_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An all-defaults chart() call still sends the spec's static interval."""
    fake = _install_fake(monkeypatch, _corpus_text("chart/AAPL.json"))
    Ticker("AAPL").chart()
    _, params = fake.calls[0]
    assert params["interval"] == "1m"


def test_ticker_chart_shape_mismatch_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A truncated timestamp array surfaces as YahooApiError, not TabularShapeError."""
    payload = json.loads(_corpus_text("chart/AAPL.json"))
    result = payload["chart"]["result"][0]
    result["timestamp"] = result["timestamp"][:1]
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").chart()
    assert exc_info.value.code == "malformed-response"
    assert type(exc_info.value) is YahooApiError
    assert isinstance(exc_info.value.__cause__, TabularShapeError)


def test_ticker_chart_meta_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A meta block that fails ChartMeta validation surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("chart/AAPL.json"))
    payload["chart"]["result"][0]["meta"]["regularMarketPrice"] = "abc"
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").chart()
    assert exc_info.value.code == "model-validation"
    assert type(exc_info.value) is YahooApiError
    assert isinstance(exc_info.value.__cause__, pydantic.ValidationError)


def test_ticker_chart_builds_typed_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """chart() returns typed ChartEvents when the response carries an events block."""
    _install_fake(monkeypatch, _corpus_text("chart/MSFT_1y_events.json"))
    chart = Ticker("MSFT").chart(events=["div"])
    assert isinstance(chart.events, ChartEvents)
    assert chart.events.dividends is not None
    assert chart.events.splits is None


_SPARK_AAPL_PREVIOUS_CLOSE = 294.38
_SPARK_AAPL_FIRST_CLOSE = 298.2
_SPARK_AAPL_LAST_CLOSE = 308.63
_SPARK_AAPL_ROW_COUNT = 79


def test_ticker_spark_builds_typed_close_series(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """spark() returns a Spark whose frame has the fixed (ts, close) schema."""
    fake = _install_fake(monkeypatch, _corpus_text("spark/AAPL.json"))
    spark = Ticker("AAPL").spark()
    assert isinstance(spark, Spark)
    path, _ = fake.calls[0]
    assert path == "/v7/finance/spark"
    assert spark.to_polars().columns == ["ts", "close"]
    rows = spark.to_dicts()
    assert len(rows) == _SPARK_AAPL_ROW_COUNT
    assert rows[0]["close"] == pytest.approx(_SPARK_AAPL_FIRST_CLOSE)
    assert rows[-1]["close"] == pytest.approx(_SPARK_AAPL_LAST_CLOSE)
    assert isinstance(spark.meta, ChartMeta)
    assert spark.meta.previous_close == pytest.approx(_SPARK_AAPL_PREVIOUS_CLOSE)


def test_ticker_spark_empty_result_raises_symbol_not_found_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yahoo's 200-with-null-result spark shape becomes SymbolNotFoundError."""
    _install_fake(monkeypatch, _corpus_text("spark/ZZZZXYZQ.json"))
    with pytest.raises(SymbolNotFoundError):
        Ticker("ZZZZXYZQ").spark()


def test_ticker_spark_empty_response_list_raises_symbol_not_found_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A result entry with an empty response list also becomes SymbolNotFoundError."""
    payload = json.loads(_corpus_text("spark/AAPL.json"))
    payload["spark"]["result"][0]["response"] = []
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(SymbolNotFoundError):
        Ticker("AAPL").spark()


def test_ticker_spark_shape_mismatch_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A truncated timestamp array surfaces as YahooApiError, not TabularShapeError."""
    payload = json.loads(_corpus_text("spark/AAPL.json"))
    response = payload["spark"]["result"][0]["response"][0]
    response["timestamp"] = response["timestamp"][:1]
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").spark()
    assert exc_info.value.code == "malformed-response"
    assert type(exc_info.value) is YahooApiError
    assert isinstance(exc_info.value.__cause__, TabularShapeError)


def test_ticker_spark_meta_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A meta block that fails ChartMeta validation surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("spark/AAPL.json"))
    response = payload["spark"]["result"][0]["response"][0]
    response["meta"]["regularMarketPrice"] = "abc"
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").spark()
    assert exc_info.value.code == "model-validation"
    assert type(exc_info.value) is YahooApiError
    assert isinstance(exc_info.value.__cause__, pydantic.ValidationError)


def test_ticker_spark_passes_wire_params(monkeypatch: pytest.MonkeyPatch) -> None:
    """Typed spark kwargs land under their Yahoo wire names."""
    fake = _install_fake(monkeypatch, _corpus_text("spark/AAPL.json"))
    Ticker("AAPL").spark(range="1d", interval="5m", include_timestamps=True)
    _, params = fake.calls[0]
    assert params["range"] == "1d"
    assert params["interval"] == "5m"
    assert params["includeTimestamps"] is True


def test_ticker_options_returns_typed_option_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """options() unwraps the one-record result list into a typed OptionChain."""
    fake = _install_fake(monkeypatch, _corpus_text("options/AAPL.json"))
    chain = Ticker("AAPL").options()
    assert isinstance(chain, OptionChain)
    assert chain.underlying_symbol == "AAPL"
    assert chain.quote.symbol == "AAPL"
    path, _ = fake.calls[0]
    assert path == "/v7/finance/options/AAPL"


def test_ticker_options_empty_result_raises_symbol_not_found_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yahoo's 200-with-empty-result options shape becomes SymbolNotFoundError."""
    payload = json.loads(_corpus_text("options/AAPL.json"))
    payload["optionChain"]["result"] = []
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(SymbolNotFoundError):
        Ticker("AAPL").options()


def test_ticker_options_invalid_symbol_raises_symbol_not_found_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deliberate ZZZZXYZQ probe hits the same empty-result path, live-confirmed.

    Corpus-confirmed live 2026-07-05 (P4-1): HTTP 200 with
    ``{"optionChain": {"result": [], "error": None}}`` — the exact
    synthetic shape the sibling test above already exercised, now backed
    by a real capture instead of a hand-edited payload.
    """
    _install_fake(monkeypatch, _corpus_text("options/ZZZZXYZQ.json"))
    with pytest.raises(SymbolNotFoundError) as exc_info:
        Ticker("ZZZZXYZQ").options()
    assert exc_info.value.symbol == "ZZZZXYZQ"


def test_ticker_options_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A record that fails OptionChain validation surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("options/AAPL.json"))
    payload["optionChain"]["result"][0]["underlyingSymbol"] = 123
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").options()
    assert exc_info.value.code == "model-validation"
    assert type(exc_info.value) is YahooApiError
    assert isinstance(exc_info.value.__cause__, pydantic.ValidationError)


def test_ticker_options_passes_new_wire_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Typed options kwargs land under their Yahoo wire names."""
    fake = _install_fake(monkeypatch, _corpus_text("options/AAPL.json"))
    Ticker("AAPL").options(date="2026-07-06", straddle=True)
    _, params = fake.calls[0]
    assert params["straddle"] is True


_TIMESERIES_DEFAULT_ECONOMIC_ROWS = 2


def test_ticker_timeseries_returns_typed_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """timeseries() flattens the payload into a typed Timeseries container."""
    fake = _install_fake(monkeypatch, _corpus_text("timeseries/AAPL.json"))
    result = Ticker("AAPL").timeseries()
    assert isinstance(result, Timeseries)
    path, _ = fake.calls[0]
    assert path == "/ws/fundamentals-timeseries/v1/finance/timeseries/AAPL"
    economic = result.economic_events.to_polars()
    assert economic.height == _TIMESERIES_DEFAULT_ECONOMIC_ROWS
    assert economic["country_code"].to_list() == ["US", "US"]
    assert result.empty_types == ("spEarningsReleaseEvents", "analystRatings")
    assert result.unrecognized_types == ()
    assert result.fundamentals.to_polars().is_empty()
    assert result.fundamentals.fetched_at == result.fetched_at


def test_ticker_timeseries_invalid_symbol_yields_all_empty_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ZZZZXYZQ capture (meta-only entries) yields an all-empty container."""
    _install_fake(monkeypatch, _corpus_text("timeseries/ZZZZXYZQ.json"))
    result = Ticker("ZZZZXYZQ").timeseries()
    assert result.empty_types == (
        "economicEvents",
        "spEarningsReleaseEvents",
        "analystRatings",
    )
    assert result.unrecognized_types == ()
    for frame in (
        result.fundamentals,
        result.geographic_segments,
        result.economic_events,
        result.analyst_ratings,
    ):
        df = frame.to_polars()
        assert df.height == 0
        assert df.columns  # the declared schema survives empty results


def test_ticker_timeseries_shape_mismatch_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed result shape surfaces as YahooApiError, not TabularShapeError."""
    _install_fake(monkeypatch, json.dumps({"timeseries": {"result": [1]}}))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").timeseries()
    assert exc_info.value.code == "malformed-response"
    assert type(exc_info.value) is YahooApiError
    assert isinstance(exc_info.value.__cause__, TabularShapeError)


def test_ticker_timeseries_passes_wire_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Typed timeseries kwargs land under their Yahoo wire names."""
    fake = _install_fake(monkeypatch, _corpus_text("timeseries/AAPL.json"))
    Ticker("AAPL").timeseries(
        type=["annualTotalRevenue", "economicEvents"],
        merge=False,
        pad_time_series=True,
    )
    _, params = fake.calls[0]
    assert params["type"] == "annualTotalRevenue,economicEvents"
    assert params["merge"] is False
    assert params["padTimeSeries"] is True


def test_ticker_quote_summary_passes_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Modules list serializes to the CSV wire form."""
    fake = _install_fake(monkeypatch, _corpus_text("quote-summary/AAPL.json"))
    Ticker("AAPL").quote_summary(modules=["price", "summaryDetail"])
    _, params = fake.calls[0]
    assert params["modules"] == "price,summaryDetail"


def test_ticker_quote_summary_passes_boolean_wire_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boolean kwargs pass their values through to matching wire names."""
    fake = _install_fake(monkeypatch, _corpus_text("quote-summary/AAPL.json"))
    Ticker("AAPL").quote_summary(
        enable_qsp_expanded_earnings=False, overnight_price=False
    )
    _, params = fake.calls[0]
    assert params["enableQSPExpandedEarnings"] is False
    assert params["overnightPrice"] is False


def test_ticker_quote_summary_returns_typed_quote_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """quote_summary() unwraps the one-record result list into a typed QuoteSummary."""
    _install_fake(monkeypatch, _corpus_text("quote-summary/AAPL.json"))
    summary = Ticker("AAPL").quote_summary()
    assert isinstance(summary, QuoteSummary)
    assert summary.price is not None
    assert summary.price.symbol == "AAPL"
    assert summary.quote_type is not None
    assert summary.quote_type.symbol == "AAPL"


def test_ticker_quote_summary_unrequested_modules_are_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modules absent from an EQUITY capture (fund-only modules) validate as None."""
    _install_fake(monkeypatch, _corpus_text("quote-summary/AAPL.json"))
    summary = Ticker("AAPL").quote_summary(modules=["price", "summaryDetail"])
    assert summary.price is not None
    assert summary.summary_detail is not None
    assert summary.fund_profile is None
    assert summary.fund_performance is None
    assert summary.top_holdings is None


def test_ticker_quote_summary_empty_result_raises_symbol_not_found_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yahoo's 200-with-empty-result quoteSummary shape becomes SymbolNotFoundError."""
    payload = json.loads(_corpus_text("quote-summary/AAPL.json"))
    payload["quoteSummary"]["result"] = []
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(SymbolNotFoundError):
        Ticker("AAPL").quote_summary()


def test_ticker_quote_summary_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A record that fails QuoteSummary validation surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("quote-summary/AAPL.json"))
    payload["quoteSummary"]["result"][0]["price"]["regularMarketPrice"] = "abc"
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").quote_summary()
    assert exc_info.value.code == "model-validation"
    assert type(exc_info.value) is YahooApiError
    assert isinstance(exc_info.value.__cause__, pydantic.ValidationError)


def test_ticker_repr() -> None:
    """repr() shows the bound symbol."""
    assert repr(Ticker(" AAPL ")) == "Ticker('AAPL')"


def test_ticker_strips_symbol_whitespace() -> None:
    """The constructor strips surrounding whitespace from the symbol."""
    assert Ticker(" AAPL ").symbol == "AAPL"


def test_ticker_analyst_returns_typed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """analyst() returns a typed AnalystResult and hits the expected path."""
    fake = _install_fake(monkeypatch, _corpus_text("analyst/AAPL.json"))
    result = Ticker("AAPL").analyst()
    assert isinstance(result, AnalystResult)
    assert result.price_movement.ticker == "AAPL"
    path, _ = fake.calls[0]
    assert path == "/ws/mad/v2/analyst/symbol/AAPL"


def test_ticker_analyst_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed analyst payload surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("analyst/AAPL.json"))
    del payload["symbol_id"]
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").analyst()
    assert exc_info.value.code == "model-validation"


def test_ticker_analyst_not_found_raises_symbol_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yahoo's 404 not-found body for analyst becomes SymbolNotFoundError."""
    _install_fake_error(monkeypatch, _corpus_text("analyst/ZZZZXYZQ.json"))
    with pytest.raises(SymbolNotFoundError):
        Ticker("ZZZZXYZQ").analyst()


def test_ticker_ratings_top_returns_typed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ratings_top() returns a typed TopRatingsResult and hits the expected path."""
    fake = _install_fake(monkeypatch, _corpus_text("ratings-top/AAPL.json"))
    result = Ticker("AAPL").ratings_top()
    assert isinstance(result, TopRatingsResult)
    assert result.dir.ticker == "AAPL"
    path, _ = fake.calls[0]
    assert path == "/v2/ratings/top/AAPL"


def test_ticker_ratings_top_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed ratings-top payload surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("ratings-top/AAPL.json"))
    del payload["dir"]
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").ratings_top()
    assert exc_info.value.code == "model-validation"


def test_ticker_ratings_top_not_found_raises_symbol_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yahoo's ratings-top 404 body surfaces as SymbolNotFoundError.

    A 404 with a bare ``{"detail": ...}`` body on a symbol-bound call is a
    per-endpoint lookup miss regardless of Yahoo's wording — the AI-service
    endpoints report unknown symbols and no-coverage-for-symbol identically
    (``"No top ratings found for symbol: RY.TO"`` here vs analyst's
    ``"Symbol not found for RY.TO"`` for the same miss), so
    ``yoghurt._core.map_http_error`` maps by status + shape, not wording.
    """
    _install_fake_error(monkeypatch, _corpus_text("ratings-top/RY.TO.json"))
    with pytest.raises(SymbolNotFoundError) as exc_info:
        Ticker("RY.TO").ratings_top()
    assert exc_info.value.symbol == "RY.TO"
    assert "No top ratings found" in (exc_info.value.description or "")


def test_ticker_ratings_top_invalid_symbol_raises_symbol_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deliberate ZZZZXYZQ probe gets the identical 404 shape as RY.TO.

    Corpus-confirmed live 2026-07-05 (P4-1). See
    ``yoghurt.api.Ticker.ratings_top``'s docstring.
    """
    _install_fake_error(monkeypatch, _corpus_text("ratings-top/ZZZZXYZQ.json"))
    with pytest.raises(SymbolNotFoundError) as exc_info:
        Ticker("ZZZZXYZQ").ratings_top()
    assert exc_info.value.symbol == "ZZZZXYZQ"


def test_ticker_calendar_events_returns_typed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """calendar_events() returns a typed CalendarEventsResult."""
    fake = _install_fake(monkeypatch, _corpus_text("calendar-events/AAPL.json"))
    result = Ticker("AAPL").calendar_events()
    assert isinstance(result, CalendarEventsResult)
    assert result.earnings == []
    path, _ = fake.calls[0]
    assert path == "/ws/screeners/v1/finance/calendar-events"


def test_ticker_calendar_events_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed calendar-events payload surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("calendar-events/AAPL.json"))
    payload["finance"]["result"]["earnings"] = "not-a-list"
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").calendar_events()
    assert exc_info.value.code == "model-validation"


def test_ticker_calendar_events_invalid_symbol_returns_valid_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unrecognized symbol is not an error: Yahoo sends a valid-empty result.

    Corpus-confirmed live 2026-07-05 (P4-1): ``{"earnings": []}``,
    byte-for-byte the same shape as a recognized symbol with no scheduled
    events. See ``yoghurt.api.Ticker.calendar_events``'s docstring.
    """
    _install_fake(monkeypatch, _corpus_text("calendar-events/ZZZZXYZQ.json"))
    result = Ticker("ZZZZXYZQ").calendar_events()
    assert isinstance(result, CalendarEventsResult)
    assert result.earnings == []
    assert result.economic_events is None


def test_ticker_price_insights_returns_typed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """price_insights() unwraps this symbol's record into a typed PriceInsights."""
    fake = _install_fake(monkeypatch, _corpus_text("price-insights/AAPL.json"))
    result = Ticker("AAPL").price_insights()
    assert isinstance(result, PriceInsights)
    assert result.has_price_anomaly is True
    path, _ = fake.calls[0]
    assert path == "/ws/company-fundamentals/v1/finance/price-insights"


def test_ticker_price_insights_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A symbol missing from the result map surfaces as YahooApiError."""
    _install_fake(monkeypatch, _corpus_text("price-insights/AAPL.json"))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("ZZZZXYZQ").price_insights()
    assert exc_info.value.code == "model-validation"


def test_ticker_price_insights_invalid_symbol_returns_valid_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unrecognized symbol is not an error: Yahoo sends a fully-shaped record.

    Corpus-confirmed live 2026-07-05 (P4-1): HTTP 200 with every top-level
    block present and ``has_price_anomaly=True``, not a 404 or an empty
    result. See ``yoghurt.api.Ticker.price_insights``'s docstring.
    """
    _install_fake(monkeypatch, _corpus_text("price-insights/ZZZZXYZQ.json"))
    result = Ticker("ZZZZXYZQ").price_insights()
    assert isinstance(result, PriceInsights)
    assert result.has_price_anomaly is True


def test_ticker_insights_returns_typed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """insights() unwraps the one-record result list into a typed Insights."""
    fake = _install_fake(monkeypatch, _corpus_text("insights/AAPL.json"))
    result = Ticker("AAPL").insights()
    assert isinstance(result, Insights)
    assert result.symbol == "AAPL"
    path, _ = fake.calls[0]
    assert path == "/ws/insights/v3/finance/insights"


def test_ticker_insights_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty insights result list surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("insights/AAPL.json"))
    payload["finance"]["result"] = []
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").insights()
    assert exc_info.value.code == "model-validation"


def test_ticker_insights_invalid_symbol_returns_thin_valid_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unrecognized symbol gets the same thin shape as no-coverage symbols.

    Corpus-confirmed live 2026-07-05 (P4-1): ``{"sigDevs": [], "symbol":
    "ZZZZXYZQ"}``. See ``yoghurt.api.Ticker.insights``'s docstring.
    """
    _install_fake(monkeypatch, _corpus_text("insights/ZZZZXYZQ.json"))
    result = Ticker("ZZZZXYZQ").insights()
    assert isinstance(result, Insights)
    assert result.symbol == "ZZZZXYZQ"
    assert result.sig_devs == []
    assert result.recommendation is None


def test_ticker_recommendations_returns_typed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """recommendations() unwraps the one-record result list into a typed model."""
    fake = _install_fake(
        monkeypatch, _corpus_text("recommendations-by-symbol/AAPL.json")
    )
    result = Ticker("AAPL").recommendations()
    assert isinstance(result, RecommendationsResult)
    assert result.symbol == "AAPL"
    path, _ = fake.calls[0]
    assert path == "/v6/finance/recommendationsbysymbol/AAPL"


def test_ticker_recommendations_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty recommendations result list surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("recommendations-by-symbol/AAPL.json"))
    payload["finance"]["result"] = []
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").recommendations()
    assert exc_info.value.code == "model-validation"


def test_ticker_recommendations_invalid_symbol_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unrecognized symbol surfaces as a model-validation failure, not a 404.

    Corpus-confirmed live 2026-07-05 (P4-1): Yahoo returns HTTP 200 with
    ``{"result": []}``, the same valid-but-empty shape it uses for
    instrument types with nothing to recommend (see the FUTURE-symbol test
    below). See ``yoghurt.api.Ticker.recommendations``'s docstring.
    """
    _install_fake(monkeypatch, _corpus_text("recommendations-by-symbol/ZZZZXYZQ.json"))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("ZZZZXYZQ").recommendations()
    assert exc_info.value.code == "model-validation"


def test_ticker_recommendations_future_symbol_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A FUTURE symbol with no recommendations gets the identical empty shape.

    Corpus-confirmed live 2026-07-05 (P4-1, ``ES=F``): not an error from
    Yahoo's side, but surfaces the same as an invalid symbol because
    ``RecommendationsResult`` requires ``recommended_symbols``/``symbol``.
    """
    _install_fake(monkeypatch, _corpus_text("recommendations-by-symbol/ES_F.json"))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("ES=F").recommendations()
    assert exc_info.value.code == "model-validation"


def test_ticker_stock_recommender_returns_typed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stock_recommender() returns a typed StockRecommenderResult."""
    fake = _install_fake(monkeypatch, _corpus_text("stock-recommender/AAPL.json"))
    result = Ticker("AAPL").stock_recommender()
    assert isinstance(result, StockRecommenderResult)
    assert result.fields.entity_type == "ticker"
    path, _ = fake.calls[0]
    assert path == "/xhr/stock-recommender"


def test_ticker_stock_recommender_model_violation_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed stock-recommender payload surfaces as YahooApiError."""
    payload = json.loads(_corpus_text("stock-recommender/AAPL.json"))
    del payload["fields"]
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        Ticker("AAPL").stock_recommender()
    assert exc_info.value.code == "model-validation"


def test_ticker_stock_recommender_not_found_raises_bare_yahoo_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unrecognized symbol's 404 is truly unmappable: a bare YahooRequestError.

    Corpus-confirmed live 2026-07-05 (P4-1): the 404 body is
    ``{"message": "Not Found"}`` — no ``detail`` key, unlike every other
    endpoint in this batch — so ``yoghurt._core.map_http_error`` cannot map
    it to ``SymbolNotFoundError`` or ``YahooApiError``. See
    ``yoghurt.api.Ticker.stock_recommender``'s docstring.
    """
    _install_fake_error(monkeypatch, _corpus_text("stock-recommender/ZZZZXYZQ.json"))
    with pytest.raises(YahooRequestError):
        Ticker("ZZZZXYZQ").stock_recommender()
