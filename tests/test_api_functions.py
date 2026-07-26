"""Tests for the public synchronous module-level API functions."""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import yoghurt._core as core
from yoghurt import api
from yoghurt.commands import COMMANDS_BY_NAME
from yoghurt.exceptions import YahooApiError
from yoghurt.frames import Frame, History
from yoghurt.history import HISTORY_REQUEST_BATCH_SIZE
from yoghurt.models import (
    LookupResult,
    MarketInfoResult,
    MarketSummaryQuote,
    MarketTimeResult,
    Quote,
    ScreenerDiscoverResult,
    ScreenerInstrumentFieldsResult,
    ScreenerPredefinedResult,
    SearchResult,
    SectorResult,
    TimeseriesFieldsResult,
    TrendingResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from yoghurt.types import ParamValue

_CORPUS_ROOT = Path(__file__).parent / "fixtures" / "corpus"
_TRENDING_SPEC_REGION = next(
    param.default
    for param in COMMANDS_BY_NAME["trending"].params
    if param.name == "region"
)


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


class _ConcurrencyTrackingClient(_FakeClient):
    """Track peak simultaneous GET calls."""

    def __init__(self, body: str) -> None:
        """Initialize concurrency counters."""

        super().__init__(body)
        self.active = 0
        self.peak_active = 0

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Yield while active so overlapping calls can be counted."""

        self.active += 1
        self.peak_active = max(self.peak_active, self.active)
        try:
            await asyncio.sleep(0)
            return await super().get(
                path,
                params,
                use_crumb=use_crumb,
                base_url=base_url,
            )
        finally:
            self.active -= 1


def _install_fake(monkeypatch: pytest.MonkeyPatch, body: str) -> _FakeClient:
    """Patch the core client seam with a fake that returns ``body``.

    Returns:
        _FakeClient: The installed fake, for call-inspection assertions.
    """

    fake = _FakeClient(body)
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    return fake


def test_quotes_returns_result_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """quotes() returns a typed Quote per quoteResponse.result record."""
    body = _corpus_text("quote/multi.json")
    _install_fake(monkeypatch, body)
    results = api.quotes(["AAPL", "MSFT"])
    expected = json.loads(body)["quoteResponse"]["result"]
    assert len(results) == len(expected)
    assert all(isinstance(result, Quote) for result in results)
    assert [result.symbol for result in results] == [
        record["symbol"] for record in expected
    ]


def test_quotes_joins_symbols_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    """quotes() joins the symbols list into the wire CSV param."""
    fake = _install_fake(monkeypatch, _corpus_text("quote/multi.json"))
    api.quotes(["AAPL", "MSFT"], include_private_companies=False)
    _, params = fake.calls[0]
    assert params["symbols"] == "AAPL,MSFT"
    assert params["enablePrivateCompany"] is False


def test_quotes_empty_list_raises_before_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """quotes([]) raises ValueError without making any client call."""

    def _fail_get_client() -> object:
        message = "must not be called"
        raise AssertionError(message)

    monkeypatch.setattr(core, "_get_client", _fail_get_client)
    with pytest.raises(ValueError, match="symbols must not be empty"):
        api.quotes([])


def test_search_returns_typed_result_and_maps_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """search() validates the whole response and maps readable Python controls."""

    fake = _install_fake(monkeypatch, _corpus_text("search/AAPL_content.json"))
    result = api.search(
        "AAPL",
        quotes_count=3,
        news_count=3,
        lists_count=3,
        recommended_count=3,
        fuzzy=True,
        include_private_companies=False,
        include_navigation_links=True,
        include_research_reports=True,
        include_cultural_assets=True,
        lang="fr-FR",
        region="FR",
    )

    assert isinstance(result, SearchResult)
    assert result.quotes[0].symbol == "AAPL"
    path, params = fake.calls[0]
    assert path == "/v1/finance/search"
    assert params == {
        "q": "AAPL",
        "quotesCount": 3,
        "newsCount": 3,
        "listsCount": 3,
        "recommendedCount": 3,
        "enableFuzzyQuery": True,
        "enableCb": False,
        "enableNavLinks": True,
        "enableResearchReports": True,
        "enableCulturalAssets": True,
        "lang": "fr-FR",
        "region": "FR",
    }


def test_lookup_returns_typed_result_and_empty_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """lookup() preserves an unmatched query as an empty typed page."""

    fake = _install_fake(monkeypatch, _corpus_text("lookup/no_match.json"))
    result = api.lookup(
        "ZZZZXYZQ",
        type="equity",
        start=5,
        count=10,
        formatted=True,
        fetch_pricing_data=False,
        lang="en-CA",
        region="CA",
    )

    assert isinstance(result, LookupResult)
    assert result.documents == []
    path, params = fake.calls[0]
    assert path == "/v1/finance/lookup"
    assert params == {
        "query": "ZZZZXYZQ",
        "type": "equity",
        "start": 5,
        "count": 10,
        "formatted": True,
        "fetchPricingData": False,
        "lang": "en-CA",
        "region": "CA",
    }


@pytest.mark.parametrize(
    "function",
    [
        api.history,
        api.quotes,
        api.search,
        api.lookup,
        api.screener,
        api.visualization,
        api.screener_predefined,
        api.trending,
        api.market_calendar,
        api.sector,
        api.market_summary,
        api.market_info,
        api.market_time,
        api.screener_instrument_fields,
        api.timeseries_fields,
        api.screener_discover,
    ],
)
def test_locale_aware_library_functions_expose_overrides(
    function: Callable[..., object],
) -> None:
    """Every locale-aware module function accepts lang and region overrides."""

    parameters = inspect.signature(function).parameters
    assert "lang" in parameters
    assert "region" in parameters


def test_history_fetches_symbols_concurrently_into_one_long_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """history() preserves input symbol order in one adjusted History table."""

    fake = _install_fake(monkeypatch, _corpus_text("chart/AAPL.json"))
    result = api.history(
        ["AAPL", "MSFT"],
        period="1y",
        lang="en-CA",
        region="CA",
    )

    assert isinstance(result, History)
    symbols = result.to_polars()["symbol"].to_list()
    rows_per_symbol = len(symbols) // 2
    assert symbols == ["AAPL"] * rows_per_symbol + ["MSFT"] * rows_per_symbol
    assert [path for path, _params in fake.calls] == [
        "/v8/finance/chart/AAPL",
        "/v8/finance/chart/MSFT",
    ]
    assert all(params["range"] == "1y" for _path, params in fake.calls)
    assert all(params["lang"] == "en-CA" for _path, params in fake.calls)
    assert all(params["region"] == "CA" for _path, params in fake.calls)


def test_history_bounds_concurrent_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    """history() never has more than one request batch in flight."""

    fake = _ConcurrencyTrackingClient(_corpus_text("chart/AAPL.json"))
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    symbols = [f"SYM{index}" for index in range(HISTORY_REQUEST_BATCH_SIZE + 1)]

    api.history(symbols)

    assert fake.peak_active == HISTORY_REQUEST_BATCH_SIZE
    assert [path.rsplit("/", 1)[-1] for path, _params in fake.calls] == symbols


_SCREENER_QUERY = (
    "SELECT ticker, sector FROM EQUITY WHERE sector = 'Technology' LIMIT 5"
)
_VISUALIZATION_QUERY = (
    "SELECT ticker, transactiondate, shares FROM INSIDER_TRANSACTION "
    "WHERE ticker = 'AAPL' ORDER BY transactiondate DESC LIMIT 5"
)


def test_screener_builds_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    """screener() flattens records into a Frame with the expected row count."""
    body = _corpus_text("screener/equity_us_tech.json")
    fake = _install_fake(monkeypatch, body)
    frame = api.screener(_SCREENER_QUERY, lang="en-CA", region="CA")
    expected_records = json.loads(body)["finance"]["result"][0]["records"]
    assert isinstance(frame, Frame)
    assert frame.to_polars().height == len(expected_records)
    assert "ticker" in frame.to_polars().columns
    path, call = fake.calls[0]
    assert path == "/v1/finance/screener"
    assert isinstance(call, dict)
    params = call["params"]
    assert isinstance(params, dict)
    assert params["lang"] == "en-CA"
    assert params["region"] == "CA"


def test_visualization_builds_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    """visualization() flattens documents into a Frame with the expected row count."""
    body = _corpus_text("visualization/insider_transaction.json")
    fake = _install_fake(monkeypatch, body)
    frame = api.visualization(_VISUALIZATION_QUERY, lang="fr-FR", region="FR")
    expected_rows = json.loads(body)["finance"]["result"][0]["documents"][0]["rows"]
    assert isinstance(frame, Frame)
    assert frame.to_polars().height == len(expected_rows)
    assert "ticker" in frame.to_polars().columns
    path, call = fake.calls[0]
    assert path == "/v1/finance/visualization"
    assert isinstance(call, dict)
    params = call["params"]
    assert isinstance(params, dict)
    assert params["lang"] == "fr-FR"
    assert params["region"] == "FR"


def test_screener_empty_records_returns_empty_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty screener records list yields an empty Frame, not a raised error."""
    payload = json.loads(_corpus_text("screener/equity_us_tech.json"))
    payload["finance"]["result"][0]["records"] = []
    payload["finance"]["result"][0]["total"] = 0
    _install_fake(monkeypatch, json.dumps(payload))
    frame = api.screener(_SCREENER_QUERY)
    assert isinstance(frame, Frame)
    assert frame.to_polars().height == 0


def test_visualization_empty_documents_returns_empty_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty visualization documents list yields an empty Frame."""
    payload = json.loads(_corpus_text("visualization/insider_transaction.json"))
    payload["finance"]["result"][0]["documents"] = []
    payload["finance"]["result"][0]["total"] = 0
    _install_fake(monkeypatch, json.dumps(payload))
    frame = api.visualization(_VISUALIZATION_QUERY)
    assert isinstance(frame, Frame)
    assert frame.to_polars().height == 0


def test_screener_nested_cell_raises_unsupported_response_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nested screener value surfaces as YahooApiError, not TabularShapeError."""
    payload = json.loads(_corpus_text("screener/equity_us_tech.json"))
    payload["finance"]["result"][0]["records"][0]["sector"] = {"nested": "value"}
    _install_fake(monkeypatch, json.dumps(payload))
    with pytest.raises(YahooApiError) as exc_info:
        api.screener(_SCREENER_QUERY)
    assert exc_info.value.code == "unsupported-response-shape"


def test_trending_returns_typed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """trending() returns a typed TrendingResult built from finance.result[0]."""
    body = _corpus_text("trending/default.json")
    fake = _install_fake(monkeypatch, body)
    result = api.trending()
    expected = json.loads(body)["finance"]["result"][0]
    assert isinstance(result, TrendingResult)
    assert result.count == expected["count"]
    assert len(result.quotes) == len(expected["quotes"])
    path, _ = fake.calls[0]
    assert path == f"/v1/finance/trending/{_TRENDING_SPEC_REGION}"


def test_sector_returns_typed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """sector() returns a typed SectorResult built from the data envelope."""
    body = _corpus_text("sector/technology.json")
    fake = _install_fake(monkeypatch, body)
    result = api.sector("technology")
    expected = json.loads(body)["data"]
    assert isinstance(result, SectorResult)
    assert result.key == expected["key"]
    path, _ = fake.calls[0]
    assert path == "/v1/finance/sectors/technology"


def test_sector_slug_maps_to_wire_sector_param(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sector()'s slug parameter still populates the wire 'sector' path value."""
    fake = _install_fake(monkeypatch, _corpus_text("sector/technology.json"))
    api.sector("technology")
    path, _ = fake.calls[0]
    assert path == "/v1/finance/sectors/technology"


def test_market_summary_returns_typed_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """market_summary() returns a typed MarketSummaryQuote per result record."""
    body = _corpus_text("market-summary/default.json")
    fake = _install_fake(monkeypatch, body)
    results = api.market_summary()
    expected = json.loads(body)["marketSummaryResponse"]["result"]
    assert len(results) == len(expected)
    assert all(isinstance(result, MarketSummaryQuote) for result in results)
    assert [result.symbol for result in results] == [
        record["symbol"] for record in expected
    ]
    path, _ = fake.calls[0]
    assert path == "/v6/finance/quote/marketSummary"


def test_market_summary_empty_results_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty market-summary result list is valid data, not an error."""
    payload = json.loads(_corpus_text("market-summary/default.json"))
    payload["marketSummaryResponse"]["result"] = []
    _install_fake(monkeypatch, json.dumps(payload))
    assert api.market_summary() == []


def test_market_info_returns_typed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """market_info() returns a typed MarketInfoResult built from finance.result."""
    body = _corpus_text("market-info/default.json")
    fake = _install_fake(monkeypatch, body)
    result = api.market_info()
    expected = json.loads(body)["finance"]["result"]
    assert isinstance(result, MarketInfoResult)
    assert result.currencies is not None
    assert result.currencies.tickers == expected["currencies"]["tickers"]
    assert result.commodities is not None
    assert result.commodities.tickers == expected["commodities"]["tickers"]
    path, _ = fake.calls[0]
    assert path == "/ws/market-info/v1/finance/markets/ids"


def test_market_time_returns_typed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """market_time() returns a typed MarketTimeResult from the finance envelope."""
    body = _corpus_text("market-time/default.json")
    fake = _install_fake(monkeypatch, body)
    result = api.market_time()
    expected = json.loads(body)["finance"]
    assert isinstance(result, MarketTimeResult)
    assert result.version == expected["version"]
    path, _ = fake.calls[0]
    assert path == "/v6/finance/markettime"


def test_screener_predefined_returns_typed_result_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """screener_predefined() returns one typed record per requested screener id."""
    body = _corpus_text("screener-predefined/MOST_ACTIVES.json")
    fake = _install_fake(monkeypatch, body)
    results = api.screener_predefined(["MOST_ACTIVES"])
    expected = json.loads(body)["finance"]["result"]
    assert len(results) == len(expected)
    assert all(isinstance(result, ScreenerPredefinedResult) for result in results)
    assert results[0].canonical_name == expected[0]["canonicalName"]
    assert results[0].records == expected[0]["records"]
    path, _ = fake.calls[0]
    assert path == "/v1/finance/screener/predefined/saved"


def test_screener_instrument_fields_returns_typed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """screener_instrument_fields() returns a typed ScreenerInstrumentFieldsResult."""
    body = _corpus_text("screener-instrument-fields/equity.json")
    fake = _install_fake(monkeypatch, body)
    result = api.screener_instrument_fields("equity")
    expected = json.loads(body)["finance"]["result"][0]
    assert isinstance(result, ScreenerInstrumentFieldsResult)
    assert set(result.fields) == set(expected["fields"])
    path, _ = fake.calls[0]
    assert path == "/v1/finance/screener/instrument/equity/fields"


def test_timeseries_fields_returns_typed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """timeseries_fields() returns a typed TimeseriesFieldsResult."""
    body = _corpus_text("timeseries-fields/default.json")
    fake = _install_fake(monkeypatch, body)
    result = api.timeseries_fields()
    expected = json.loads(body)["timeseriesfields"]["result"][0]
    assert isinstance(result, TimeseriesFieldsResult)
    assert len(result.time_series_data_class) == len(expected["timeSeriesDataClass"])
    path, _ = fake.calls[0]
    assert path == "/ws/fundamentals-timeseries/v1/finance/timeseriesfields"


def test_screener_discover_returns_typed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """screener_discover() returns a typed ScreenerDiscoverResult."""
    body = _corpus_text("screener-discover/default.json")
    fake = _install_fake(monkeypatch, body)
    result = api.screener_discover()
    expected = json.loads(body)["finance"]["result"]
    assert isinstance(result, ScreenerDiscoverResult)
    assert set(result.quotes) == set(expected["quotes"])
    path, _ = fake.calls[0]
    assert path == "/ws/screeners/v1/finance/screener/discover"


def test_raw_returns_parsed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """raw() parses the body with no envelope lookup and passes the payload through."""
    body = _corpus_text("raw/quote_AAPL.json")
    fake = _install_fake(monkeypatch, body)
    result = api.raw("/v7/finance/quote", {"symbols": "AAPL"})
    assert result == json.loads(body)
    path, params = fake.calls[0]
    assert path == "/v7/finance/quote"
    assert params["symbols"] == "AAPL"


def test_raw_malformed_body_raises_yahoo_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """raw() maps a non-JSON body to YahooApiError with a malformed-response code."""
    _install_fake(monkeypatch, "not json")
    with pytest.raises(YahooApiError) as exc_info:
        api.raw("/v7/finance/quote", {"symbols": "AAPL"})
    assert exc_info.value.code == "malformed-response"
