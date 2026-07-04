"""Tests for the public synchronous Ticker API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

import pydantic
import pytest

import yoghurt._core as core
from yoghurt.api import Ticker
from yoghurt.exceptions import SymbolNotFoundError, YahooApiError
from yoghurt.models import Quote, QuoteType
from yoghurt.tabular import TabularShapeError

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from yoghurt.types import ParamValue

_Invoke: TypeAlias = "Callable[[Ticker], object]"

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
    """quote_type() unwraps the one-record result list."""
    fake = _install_fake(monkeypatch, _corpus_text("quote-type/AAPL.json"))
    record = Ticker("AAPL").quote_type()
    assert record["symbol"] == "AAPL"
    path, _ = fake.calls[0]
    assert path == "/v1/finance/quoteType/AAPL"


def test_ticker_quote_type_empty_result_raises_symbol_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yahoo's 200-with-empty-result quoteType shape becomes SymbolNotFoundError."""
    _install_fake(monkeypatch, _corpus_text("quote-type/ZZZZXYZQ.json"))
    with pytest.raises(SymbolNotFoundError):
        Ticker("ZZZZXYZQ").quote_type()


def test_ticker_chart_builds_typed_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    """chart() returns a Chart whose frame has the fixed schema."""
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
    assert chart.meta["currency"] == "USD"


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


def test_ticker_repr() -> None:
    """repr() shows the bound symbol."""
    assert repr(Ticker(" AAPL ")) == "Ticker('AAPL')"


def test_ticker_strips_symbol_whitespace() -> None:
    """The constructor strips surrounding whitespace from the symbol."""
    assert Ticker(" AAPL ").symbol == "AAPL"


def _invoke_spark(ticker: Ticker) -> object:
    return ticker.spark()


def _invoke_options(ticker: Ticker) -> object:
    return ticker.options()


def _invoke_timeseries(ticker: Ticker) -> object:
    return ticker.timeseries()


def _invoke_calendar_events(ticker: Ticker) -> object:
    return ticker.calendar_events()


def _invoke_analyst(ticker: Ticker) -> object:
    return ticker.analyst()


def _invoke_ratings_top(ticker: Ticker) -> object:
    return ticker.ratings_top()


def _invoke_price_insights(ticker: Ticker) -> object:
    return ticker.price_insights()


def _invoke_insights(ticker: Ticker) -> object:
    return ticker.insights()


def _invoke_recommendations(ticker: Ticker) -> object:
    return ticker.recommendations()


def _invoke_stock_recommender(ticker: Ticker) -> object:
    return ticker.stock_recommender()


_METHOD_CASES = (
    pytest.param(_invoke_spark, "spark/AAPL.json", "/v7/finance/spark", id="spark"),
    pytest.param(
        _invoke_options,
        "options/AAPL.json",
        "/v7/finance/options/AAPL",
        id="options",
    ),
    pytest.param(
        _invoke_timeseries,
        "timeseries/AAPL.json",
        "/ws/fundamentals-timeseries/v1/finance/timeseries/AAPL",
        id="timeseries",
    ),
    pytest.param(
        _invoke_calendar_events,
        "calendar-events/AAPL.json",
        "/ws/screeners/v1/finance/calendar-events",
        id="calendar_events",
    ),
    pytest.param(
        _invoke_analyst,
        "analyst/AAPL.json",
        "/ws/mad/v2/analyst/symbol/AAPL",
        id="analyst",
    ),
    pytest.param(
        _invoke_ratings_top,
        "ratings-top/AAPL.json",
        "/v2/ratings/top/AAPL",
        id="ratings_top",
    ),
    pytest.param(
        _invoke_price_insights,
        "price-insights/AAPL.json",
        "/ws/company-fundamentals/v1/finance/price-insights",
        id="price_insights",
    ),
    pytest.param(
        _invoke_insights,
        "insights/AAPL.json",
        "/ws/insights/v3/finance/insights",
        id="insights",
    ),
    pytest.param(
        _invoke_recommendations,
        "recommendations-by-symbol/AAPL.json",
        "/v6/finance/recommendationsbysymbol/AAPL",
        id="recommendations",
    ),
    pytest.param(
        _invoke_stock_recommender,
        "stock-recommender/AAPL.json",
        "/xhr/stock-recommender",
        id="stock_recommender",
    ),
)


@pytest.mark.parametrize(("invoke", "corpus_file", "expected_path"), _METHOD_CASES)
def test_ticker_method_calls_expected_path_and_returns_payload(
    monkeypatch: pytest.MonkeyPatch,
    invoke: _Invoke,
    corpus_file: str,
    expected_path: str,
) -> None:
    """Each Ticker method hits its command's path and passes the payload through."""
    body = _corpus_text(corpus_file)
    fake = _install_fake(monkeypatch, body)
    result = invoke(Ticker("AAPL"))
    path, _ = fake.calls[0]
    assert path == expected_path
    assert result == json.loads(body)
