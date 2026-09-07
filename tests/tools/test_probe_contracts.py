"""Offline corpus regressions for opt-in public contract reports."""

from __future__ import annotations

# Tests exercise the developer tool and its internal invariant checks.
# pyright: reportPrivateUsage=false
import json
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from tests.test_financial_analysis import _FakeClient
from tools import probe
from yoghurt import _core
from yoghurt.exceptions import YahooApiError, YahooRequestError, YahooUnavailableError

if TYPE_CHECKING:
    from yoghurt.types import ParamValue

_ARGPARSE_ERROR = 2
_CONTRACT_CASE_COUNT = 54
CORPUS = Path(__file__).parents[1] / "fixtures/corpus"


class ContractClient(_FakeClient):
    """Replay source responses through the real public API."""

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Return recorded quote/chart or financial responses."""
        if path.endswith("/quote"):
            return (CORPUS / "quote" / f"{params['symbols']}.json").read_text(
                encoding="utf-8"
            )
        if "/chart/" in path:
            return (CORPUS / "chart" / f"{path.rsplit('/', 1)[-1]}.json").read_text(
                encoding="utf-8"
            )
        return await super().get(path, params, use_crumb=use_crumb, base_url=base_url)

    async def post(  # ruff: ignore[no-self-use] - transport protocol method
        self,
        path: str,
        params: dict[str, ParamValue],
        json_body: dict[str, Any],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Return a legitimate empty calendar capture."""
        del path, params, json_body, use_crumb, base_url
        return (CORPUS / "visualization/market_calendar_earnings_empty.json").read_text(
            encoding="utf-8"
        )


@pytest.mark.parametrize(
    "kind",
    [
        "quote",
        "chart",
        "history",
        "financial",
        "unknown_quote",
        "unknown_chart",
        "calendar",
    ],
)
def test_public_contracts_replay_corpus(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Actual public parsers, models and derived frames meet the report contracts."""
    body = (CORPUS / "quarterly_2026-09-07/timeseries/AAPL.json").read_text(
        encoding="utf-8"
    )
    client = ContractClient(timeseries_body=body)
    monkeypatch.setattr(_core, "_get_client", lambda: client)
    symbol = "AAPL"
    if kind == "calendar":
        symbol = "earnings"
    elif kind.startswith("unknown_"):
        symbol = probe.INVALID_SYMBOL
    parameters = (
        {"start_date": "2100-01-01", "end_date": "2100-01-02", "limit": 5, "offset": 0}
        if kind == "calendar"
        else {}
    )
    assert probe._public_contract(kind, symbol, parameters)["status"] == "pass"


@pytest.mark.parametrize(
    ("error", "status", "classification"),
    [
        (YahooUnavailableError("sensitive"), "blocked", "transport"),
        (
            YahooRequestError(429, "secret-url", body="secret-body"),
            "blocked",
            "throttled",
        ),
        (YahooRequestError(403, "secret-url"), "blocked", "access_restricted"),
        (
            YahooApiError(code="oops", description="secret", http_status=503),
            "blocked",
            "upstream_unavailable",
        ),
        (
            YahooApiError(code="model-validation", description="secret"),
            "failure",
            "contract_violation",
        ),
        (
            YahooApiError(code="malformed-response", description="secret"),
            "failure",
            "contract_violation",
        ),
    ],
)
def test_contract_error_classification_is_safe(
    error: Exception, status: str, classification: str
) -> None:
    """Transport and upstream restrictions are incomplete verification, not success."""
    result = probe._contract_error(error)
    assert result["status"] == status
    assert result["classification"] == classification
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize(
    ("status", "exit_code"), [("pass", 0), ("failure", 1), ("blocked", 2)]
)
def test_report_only_exit_and_cache_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str, exit_code: int
) -> None:
    """No cache or corpus writes; blocked checks never become an all-passed run."""
    client = ContractClient()
    options: dict[str, Any] = {}

    def configure(*, use_session_cache: bool) -> None:
        options["use_session_cache"] = use_session_cache

    def result(*_args: object) -> dict[str, str]:
        return {"status": status, "classification": "example"}

    plan: list[tuple[str, str, dict[str, object], str]] = [
        ("quote", "AAPL", {}, "typed quote")
    ]
    monkeypatch.setattr(_core, "configure", configure)
    monkeypatch.setattr(_core, "_get_client", lambda: client)
    monkeypatch.setattr(probe, "_contract_plan", lambda: plan)
    monkeypatch.setattr(
        probe,
        "_public_contract",
        result,
    )
    monkeypatch.setattr(probe, "POLITENESS_DELAY_SECONDS", 0)
    report = tmp_path / "report.json"
    monkeypatch.setattr("sys.argv", ["probe", "--contracts", "--report", str(report)])
    assert probe.main() == exit_code
    assert options == {"use_session_cache": False}
    assert client.closed
    assert list(tmp_path.iterdir()) == [report]
    assert json.loads(report.read_text())["all_passed"] == (status == "pass")


def test_contract_report_rejects_corpus_before_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsafe destination validation runs before any network configuration."""
    monkeypatch.setattr(
        "sys.argv", ["probe", "--contracts", "--report", str(CORPUS / "overwrite.json")]
    )
    with pytest.raises(SystemExit) as result:
        probe.main()
    assert result.value.code == _ARGPARSE_ERROR


def test_contract_matrix_is_bounded_and_keeps_baseline() -> None:
    """All baseline symbols and required edge contracts stay in the fixed matrix."""
    plan = probe._contract_plan()
    assert len(plan) == _CONTRACT_CASE_COUNT
    assert {symbol for kind, symbol, _, _ in plan if kind == "quote"} == set(
        probe.SYMBOLS[:17]
    )
    assert next(params for kind, _, params, _ in plan if kind == "unknown_chart") == {
        "period1": probe._CONTRACT_START,
        "period2": probe._CONTRACT_END,
    }


def test_contract_missing_bundle_row_is_a_real_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Comparing the intersection would conceal an omitted quarterly observation."""
    body = (CORPUS / "quarterly_2026-09-07/timeseries/AAPL.json").read_text(
        encoding="utf-8"
    )
    client = ContractClient(timeseries_body=body)
    monkeypatch.setattr(_core, "_get_client", lambda: client)
    bundle = probe.api.Ticker("AAPL").financial_analysis()
    rows = bundle.balance_sheet.to_polars()
    removed = rows.filter(  # pyright: ignore[reportUnknownMemberType]
        ~(
            (rows["type"] == "quarterlyTotalAssets")
            & (rows["as_of_date"].cast(str) == "2026-03-31")
        )
    )
    changed = replace(bundle, balance_sheet=replace(bundle.balance_sheet, df=removed))

    def financial_analysis(_self: probe.api.Ticker) -> probe.api.FinancialAnalysis:
        return changed

    monkeypatch.setattr(probe.api.Ticker, "financial_analysis", financial_analysis)
    with pytest.raises(probe._ContractError, match="financial_source_agreement"):
        probe._public_contract("financial", "AAPL", {})


def test_history_contract_accepts_all_price_null_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A wholly missing price row is a supported public history value."""
    payload = json.loads((CORPUS / "chart/AAPL.json").read_text(encoding="utf-8"))
    indicators = payload["chart"]["result"][0]["indicators"]
    for name in ("open", "high", "low", "close"):
        indicators["quote"][0][name][0] = None
    indicators["adjclose"][0]["adjclose"][0] = None

    async def get(  # ruff: ignore[unused-async] - transport protocol
        *_args: object, **_kwargs: object
    ) -> str:

        return json.dumps(payload)

    client = ContractClient()
    monkeypatch.setattr(client, "get", get)
    monkeypatch.setattr(_core, "_get_client", lambda: client)
    assert probe._public_contract("history", "AAPL", {})["status"] == "pass"
    indicators["quote"][0]["close"] = "invalid"
    with pytest.raises(YahooApiError):
        probe._public_contract("history", "AAPL", {})


def test_empty_fundamentals_contract_replays_real_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ETF absence remains a valid empty Frame rather than an unknown symbol."""
    client = ContractClient(
        timeseries_body=(CORPUS / "quarterly_2026-09-07/timeseries/SPY.json").read_text(
            encoding="utf-8"
        )
    )
    monkeypatch.setattr(_core, "_get_client", lambda: client)
    assert probe._public_contract("empty", "SPY", {})["classification"] == "valid_empty"


@pytest.mark.parametrize("kind", ["earnings", "ipo", "economic", "splits"])
def test_populated_calendar_contract_uses_each_public_date_column(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Populated calendars use their actual schema, including splits payable_at."""
    body = (CORPUS / f"visualization/market_calendar_{kind}.json").read_text(
        encoding="utf-8"
    )

    async def post(  # ruff: ignore[unused-async] - transport protocol
        *_args: object,
        **_kwargs: object,
    ) -> str:
        return body

    client = ContractClient()
    monkeypatch.setattr(client, "post", post)
    monkeypatch.setattr(_core, "_get_client", lambda: client)
    parameters = {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "limit": 5,
        "offset": 0,
    }
    assert probe._public_contract("calendar", kind, parameters)["status"] == "pass"


def test_financial_contract_preserves_nullable_source_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identical nullable values and currencies are source agreement, not failure."""
    payload = json.loads(
        (CORPUS / "quarterly_2026-09-07/timeseries/AAPL.json").read_text(
            encoding="utf-8"
        )
    )
    for series in payload["timeseries"]["result"]:
        for row in series.get("quarterlyTotalAssets", []):
            if row and row["asOfDate"] == "2026-03-31":
                row["reportedValue"]["raw"] = None
                row["currencyCode"] = None
    client = ContractClient(timeseries_body=json.dumps(payload))
    monkeypatch.setattr(_core, "_get_client", lambda: client)
    assert probe._public_contract("financial", "AAPL", {})["status"] == "pass"


def test_nested_calendar_scalar_is_contract_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public scalar-only query rejection is a failure, not upstream unavailability."""
    payload = json.loads(
        (CORPUS / "visualization/market_calendar_earnings.json").read_text(
            encoding="utf-8"
        )
    )
    payload["finance"]["result"][0]["documents"][0]["rows"][0][1] = {
        "unexpected": "nested"
    }

    async def post(  # ruff: ignore[unused-async] - transport protocol
        *_args: object,
        **_kwargs: object,
    ) -> str:
        return json.dumps(payload)

    client = ContractClient()
    monkeypatch.setattr(client, "post", post)
    monkeypatch.setattr(_core, "_get_client", lambda: client)
    parameters = {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "limit": 5,
        "offset": 0,
    }
    with pytest.raises(YahooApiError) as caught:
        probe._public_contract("calendar", "earnings", parameters)
    assert caught.value.code == "unsupported-response-shape"
    assert probe._contract_error(caught.value)["status"] == "failure"


@pytest.mark.parametrize("after_end", [False, True])
def test_history_window_accepts_exact_end_but_rejects_later(
    monkeypatch: pytest.MonkeyPatch,
    *,
    after_end: bool,
) -> None:
    """Live crypto evidence allows equality, never arbitrary rows on the end day."""
    payload = json.loads(
        (CORPUS / "history_contract_2026-09-07/BTC-USD.json").read_text(
            encoding="utf-8"
        )
    )
    if after_end:
        payload["chart"]["result"][0]["timestamp"][-1] += 1

    async def get(  # ruff: ignore[unused-async] - transport protocol
        *_args: object,
        **_kwargs: object,
    ) -> str:
        return json.dumps(payload)

    client = ContractClient()
    monkeypatch.setattr(client, "get", get)
    monkeypatch.setattr(_core, "_get_client", lambda: client)
    if after_end:
        with pytest.raises(probe._ContractError, match="history_window"):
            probe._public_contract("history", "BTC-USD", {})
    else:
        assert probe._public_contract("history", "BTC-USD", {})["status"] == "pass"
