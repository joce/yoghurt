"""Market-wide calendar query and schema tests."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, cast

import polars as pl
import pytest

import yoghurt._core as core
from yoghurt import api
from yoghurt._market_calendar import (
    build_market_calendar_query,
)
from yoghurt.cli import main
from yoghurt.exceptions import YahooApiError
from yoghurt.frames import Frame
from yoghurt.types import MARKET_CALENDAR_KINDS

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from yoghurt.types import ParamValue

_CORPUS = Path(__file__).parent / "fixtures" / "corpus" / "visualization"
_OFFSET = 2
_ROW_LIMIT = 5
_CASES = {
    "earnings": (
        [
            "symbol",
            "company_name",
            "market_cap",
            "event_name",
            "event_at",
            "timing",
            "eps_estimate",
            "eps_actual",
            "eps_surprise_percent",
        ],
        {"event_at": pl.Datetime("ms", "UTC")},
    ),
    "ipo": (
        [
            "symbol",
            "company_name",
            "exchange",
            "filing_date",
            "event_at",
            "amended_date",
            "price_from",
            "price_to",
            "offer_price",
            "currency",
            "shares",
            "deal_type",
        ],
        {
            "filing_date": pl.Date,
            "event_at": pl.Datetime("ms", "UTC"),
            "amended_date": pl.Date,
        },
    ),
    "economic": (
        [
            "event",
            "region",
            "event_at",
            "period",
            "actual",
            "expected",
            "prior",
            "revised",
        ],
        {"event_at": pl.Datetime("ms", "UTC")},
    ),
    "splits": (
        [
            "symbol",
            "company_name",
            "payable_at",
            "optionable",
            "old_share_worth",
            "new_share_worth",
        ],
        {"payable_at": pl.Datetime("ms", "UTC")},
    ),
}


class _FakeClient:
    def __init__(self, body: str) -> None:
        self.body = body
        self.calls: list[tuple[str, dict[str, ParamValue], dict[str, Any]]] = []

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Satisfy the shared CLI client protocol."""

        del path, params, use_crumb, base_url
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
        del use_crumb, base_url
        self.calls.append((path, params, json_body))
        return self.body

    async def aclose(self) -> None:
        """No-op close."""


def _body(kind: str, *, empty: bool = False) -> str:
    suffix = "_empty" if empty else ""
    return (_CORPUS / f"market_calendar_{kind}{suffix}.json").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("kind", MARKET_CALENDAR_KINDS)
def test_market_calendar_returns_stable_typed_frame(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Every kind normalizes its real visualization response."""

    fake = _FakeClient(_body(kind))
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    result = api.market_calendar(
        kind,  # pyright: ignore[reportArgumentType]
        start_date="2026-07-01",
        end_date="2026-08-15",
        limit=5,
    )
    columns, typed_columns = _CASES[kind]
    assert isinstance(result, Frame)
    assert result.to_polars().height == _ROW_LIMIT
    assert result.to_polars().columns == columns
    for name, dtype in typed_columns.items():
        assert result.to_polars().schema[name] == dtype
    path, params, body = fake.calls[0]
    assert path == "/v1/finance/visualization"
    assert params == {"lang": "en-US", "region": "US"}
    assert body["size"] == _ROW_LIMIT
    assert body["sortField"] == "startdatetime"
    assert body["sortType"] == "ASC"


@pytest.mark.parametrize("kind", MARKET_CALENDAR_KINDS)
def test_market_calendar_empty_response_keeps_schema(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A corpus-backed empty response retains every declared column and type."""

    fake = _FakeClient(_body(kind, empty=True))
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    result = api.market_calendar(
        kind,  # pyright: ignore[reportArgumentType]
        start_date="2100-01-01",
        end_date="2100-01-02",
        limit=5,
    )
    columns, typed_columns = _CASES[kind]
    assert result.to_polars().is_empty()
    assert result.to_polars().columns == columns
    for name, dtype in typed_columns.items():
        assert result.to_polars().schema[name] == dtype


def test_market_calendar_builds_inclusive_window_and_page() -> None:
    """The final public day becomes the exclusive next-day wire boundary."""

    query = build_market_calendar_query(
        "earnings",
        start_date=date(2026, 7, 20),
        end_date=datetime(2026, 7, 25, 23, tzinfo=timezone.utc),
        limit=25,
        offset=50,
    )
    assert "startdatetime >= '2026-07-20'" in query
    assert "startdatetime < '2026-07-26'" in query
    assert query.endswith("LIMIT 25 OFFSET 50")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"kind": "dividends"}, "unsupported market calendar"),
        (
            {
                "kind": "earnings",
                "start_date": "2026-07-26",
                "end_date": "2026-07-25",
            },
            "end_date must be",
        ),
        ({"kind": "earnings", "limit": 101}, "limit must be"),
        ({"kind": "earnings", "offset": -1}, "offset must be"),
    ],
)
def test_market_calendar_rejects_invalid_requests(
    kwargs: dict[str, object], message: str
) -> None:
    """Invalid requests fail before any network call."""

    defaults: dict[str, object] = {
        "start_date": "2026-07-20",
        "end_date": "2026-07-25",
        "limit": 100,
        "offset": 0,
    }
    call = cast("Callable[..., str]", build_market_calendar_query)
    with pytest.raises(ValueError, match=message):
        call(**(defaults | kwargs))


def test_market_calendar_populated_response_requires_every_source_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing requested field in populated data is response drift."""

    payload = json.loads(_body("splits"))
    document = payload["finance"]["result"][0]["documents"][0]
    document["columns"].pop()
    for row in document["rows"]:
        row.pop()
    fake = _FakeClient(json.dumps(payload))
    monkeypatch.setattr(core, "_get_client", lambda: fake)
    with pytest.raises(YahooApiError) as exc_info:
        api.market_calendar(
            "splits",
            start_date="2026-07-20",
            end_date="2026-08-15",
            limit=5,
        )
    assert exc_info.value.code == "malformed-response"


def test_market_calendar_help_documents_kinds_schemas_and_window(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The derived command is self-documenting from its primary help surface."""

    with pytest.raises(SystemExit) as exc_info:
        main(["market-calendar", "--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    for kind in MARKET_CALENDAR_KINDS:
        assert kind in output
    assert "--start-date" in output
    assert "--end-date" in output
    assert "--limit" in output
    assert "--offset" in output
    assert "--lang" in output
    assert "--region" in output
    assert "--format {json,parquet}" in output
    assert "eps_surprise_percent" in output
    assert "old_share_worth" in output
    assert "inclusive" in output
    assert "use visualization for custom fields and filters" in output
    assert "Calls Yahoo" not in output
    assert "Output:" not in output


def test_market_calendar_cli_normalizes_rows_and_passes_locale() -> None:
    """CLI JSON contains canonical rows while the POST keeps locale controls."""

    fake = _FakeClient(_body("earnings"))
    stdout = StringIO()
    exit_code = main(
        [
            "market-calendar",
            "earnings",
            "--start-date",
            "2026-07-20",
            "--end-date",
            "2026-08-15",
            "--limit",
            "5",
            "--offset",
            "2",
            "--lang",
            "fr-FR",
            "--region",
            "FR",
        ],
        stdout=stdout,
        client=fake,
    )

    assert exit_code == 0
    rows = json.loads(stdout.getvalue())
    assert len(rows) == _ROW_LIMIT
    assert list(rows[0]) == _CASES["earnings"][0]
    path, params, body = fake.calls[0]
    assert path == "/v1/finance/visualization"
    assert params == {"lang": "fr-FR", "region": "FR"}
    assert body["entityIdType"] == "sp_earnings"
    assert body["size"] == _ROW_LIMIT
    assert body["offset"] == _OFFSET


def test_market_calendar_cli_writes_normalized_parquet(tmp_path: Path) -> None:
    """Parquet output preserves the same normalized schema and metadata."""

    out_path = tmp_path / "ipos.parquet"
    fake = _FakeClient(_body("ipo"))
    stdout = StringIO()
    exit_code = main(
        [
            "market-calendar",
            "ipo",
            "--start-date",
            "2026-07-01",
            "--end-date",
            "2026-09-30",
            "--limit",
            "5",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        client=fake,
    )

    assert exit_code == 0
    descriptor = json.loads(stdout.getvalue())
    assert descriptor["command"] == "market-calendar"
    assert descriptor["kind"] == "ipo"
    assert descriptor["rows"] == _ROW_LIMIT
    assert descriptor["columns"] == _CASES["ipo"][0]
    frame = pl.read_parquet(out_path)
    assert frame.schema["filing_date"] == pl.Date
    assert frame.schema["event_at"] == pl.Datetime("ms", "UTC")
