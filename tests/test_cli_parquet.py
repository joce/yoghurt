"""Tests for CLI behavior around ``--format parquet`` / ``--out``."""

from __future__ import annotations

import asyncio
import json
from io import StringIO
from typing import TYPE_CHECKING, Any

import polars as pl
import pytest

from yoghurt.cli import main
from yoghurt.history import HISTORY_REQUEST_BATCH_SIZE

from .test_cli import StubClient, assert_formatted_default_false

if TYPE_CHECKING:
    from pathlib import Path

    from yoghurt.types import ParamValue

ARGPARSE_ERROR = 2
EXPECTED_ROW_COUNT = 3


class _ConcurrencyTrackingStubClient(StubClient):
    """Track peak simultaneous CLI GET calls."""

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


def _chart_body_json() -> str:
    return json.dumps(
        {
            "chart": {
                "result": [
                    {
                        "meta": {"symbol": "AAPL", "currency": "USD"},
                        "timestamp": [1_704_067_200, 1_704_153_600, 1_704_240_000],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [100.0, 101.0, 102.0],
                                    "high": [110.0, 111.0, 112.0],
                                    "low": [90.0, 91.0, 92.0],
                                    "close": [105.0, 106.0, 107.0],
                                    "volume": [1000, 2000, 3000],
                                }
                            ],
                            "adjclose": [{"adjclose": [104.5, 105.5, 106.5]}],
                        },
                    }
                ],
                "error": None,
            }
        }
    )


def _screener_body_json() -> str:
    return json.dumps(
        {
            "finance": {
                "result": [
                    {
                        "records": [
                            {"ticker": "AAPL"},
                            {"ticker": "MSFT"},
                            {"ticker": "GOOG"},
                        ],
                        "total": 3,
                    }
                ],
                "error": None,
            }
        }
    )


def _visualization_body_json() -> str:
    return json.dumps(
        {
            "finance": {
                "result": [
                    {
                        "documents": [
                            {
                                "entityIdType": "SP_EARNINGS",
                                "columns": [
                                    {
                                        "id": "ticker",
                                        "label": "Symbol",
                                        "type": "STRING",
                                    },
                                    {
                                        "id": "startdatetime",
                                        "label": "Event Start Date",
                                        "type": "DATE",
                                    },
                                ],
                                "rows": [
                                    ["AAPL", "2026-05-15T21:00:00.000Z"],
                                    ["MSFT", "2026-05-16T21:00:00.000Z"],
                                    ["GOOG", "2026-05-17T21:00:00.000Z"],
                                ],
                            }
                        ],
                        "total": 3,
                    }
                ],
                "error": None,
            }
        }
    )


# --- Chart -------------------------------------------------------------------


def test_chart_parquet_writes_file_and_prints_descriptor(tmp_path: Path) -> None:
    """Chart parquet path writes the file and prints a one-line descriptor."""

    out_path = tmp_path / "aapl.parquet"
    client = StubClient(body=_chart_body_json())
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "chart",
            "AAPL",
            "--period1",
            "1703980800",
            "--period2",
            "1704499200",
            "--interval",
            "1d",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        stderr=stderr,
        client=client,
    )

    assert exit_code == 0
    assert not stderr.getvalue()
    assert out_path.exists()

    descriptor = json.loads(stdout.getvalue().rstrip("\n"))
    assert descriptor["format"] == "parquet"
    assert descriptor["command"] == "chart"
    assert descriptor["ticker"] == "AAPL"
    assert descriptor["interval"] == "1d"
    assert descriptor["rows"] == EXPECTED_ROW_COUNT
    assert descriptor["out"] == str(out_path)

    df = pl.read_parquet(out_path)
    assert df.height == EXPECTED_ROW_COUNT
    assert "ts" in df.columns


def test_chart_parquet_without_out_is_argparse_error() -> None:
    """``--format parquet`` requires ``--out``."""

    client = StubClient(body=_chart_body_json())
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "chart",
                "AAPL",
                "--format",
                "parquet",
            ],
            stderr=stderr,
            client=client,
        )
    assert exc_info.value.code == ARGPARSE_ERROR


def test_chart_range_parquet_records_relative_window(tmp_path: Path) -> None:
    """Chart Parquet supports relative ranges without fake epoch metadata."""

    out_path = tmp_path / "aapl-range.parquet"
    client = StubClient(body=_chart_body_json())
    stdout = StringIO()

    exit_code = main(
        [
            "chart",
            "AAPL",
            "--range",
            "1mo",
            "--interval",
            "1d",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        client=client,
    )

    assert exit_code == 0
    descriptor = json.loads(stdout.getvalue())
    assert descriptor["range"] == "1mo"
    metadata = pl.read_parquet_metadata(out_path)
    assert metadata["range"] == "1mo"
    assert "period1" not in metadata
    assert "period2" not in metadata


# --- History -----------------------------------------------------------------


def test_history_json_adjusts_and_combines_symbols() -> None:
    """History JSON is one adjusted long-form table for all requested symbols."""

    client = StubClient(body=_chart_body_json())
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "history",
            "AAPL,MSFT",
            "--period",
            "1y",
            "--lang",
            "en-CA",
            "--region",
            "CA",
        ],
        stdout=stdout,
        stderr=stderr,
        client=client,
    )

    assert exit_code == 0
    assert not stderr.getvalue()
    rows = json.loads(stdout.getvalue())
    assert len(rows) == 2 * EXPECTED_ROW_COUNT
    assert [row["symbol"] for row in rows] == ["AAPL"] * 3 + ["MSFT"] * 3
    assert rows[0]["open"] == pytest.approx(100.0 * 104.5 / 105.0)
    assert rows[0]["close"] == pytest.approx(104.5)
    assert [call[0] for call in client.calls] == [
        "/v8/finance/chart/AAPL",
        "/v8/finance/chart/MSFT",
    ]
    assert all(call[1]["range"] == "1y" for call in client.calls)
    assert all(call[1]["interval"] == "1d" for call in client.calls)
    assert all(call[1]["lang"] == "en-CA" for call in client.calls)
    assert all(call[1]["region"] == "CA" for call in client.calls)


def test_history_cli_bounds_concurrent_requests() -> None:
    """The history CLI never has more than one request batch in flight."""

    client = _ConcurrencyTrackingStubClient(_chart_body_json())
    symbols = [f"SYM{index}" for index in range(HISTORY_REQUEST_BATCH_SIZE + 1)]

    exit_code = main(["history", ",".join(symbols)], client=client)

    assert exit_code == 0
    assert client.peak_active == HISTORY_REQUEST_BATCH_SIZE
    assert [call[0].rsplit("/", 1)[-1] for call in client.calls] == symbols


def test_history_parquet_writes_adjustment_contract(tmp_path: Path) -> None:
    """History Parquet records adjusted/no-repair semantics in metadata."""

    out_path = tmp_path / "history.parquet"
    client = StubClient(body=_chart_body_json())
    stdout = StringIO()

    exit_code = main(
        [
            "history",
            "AAPL,MSFT",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        client=client,
    )

    assert exit_code == 0
    descriptor = json.loads(stdout.getvalue())
    assert descriptor["command"] == "history"
    assert descriptor["symbols"] == ["AAPL", "MSFT"]
    assert descriptor["rows"] == 2 * EXPECTED_ROW_COUNT
    frame = pl.read_parquet(out_path)
    assert frame.columns == [
        "symbol",
        "ts",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    metadata = pl.read_parquet_metadata(out_path)
    assert metadata["adjustment"] == "adj_close_ratio"
    assert metadata["repair"] == "none"
    assert metadata["period"] == "1mo"


def test_chart_out_without_parquet_is_argparse_error(tmp_path: Path) -> None:
    """--out is rejected on the JSON path."""

    out_path = tmp_path / "aapl.parquet"
    client = StubClient(body=_chart_body_json())
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "chart",
                "AAPL",
                "--out",
                str(out_path),
            ],
            stderr=stderr,
            client=client,
        )
    assert exc_info.value.code == ARGPARSE_ERROR


def test_chart_default_path_unchanged() -> None:
    """Without --format, chart writes raw JSON to stdout, no file."""

    client = StubClient(body=_chart_body_json())
    stdout = StringIO()
    exit_code = main(
        ["chart", "AAPL"],
        stdout=stdout,
        client=client,
    )
    assert exit_code == 0
    assert stdout.getvalue().startswith("{")
    # The JSON body is printed verbatim (plus a trailing newline).
    assert (
        json.loads(stdout.getvalue())["chart"]["result"][0]["meta"]["symbol"] == "AAPL"
    )


# --- Screener ----------------------------------------------------------------


def test_screener_parquet_happy_path_uses_formatted_false(tmp_path: Path) -> None:
    """--format parquet writes the file and wire params keep formatted=False."""

    out_path = tmp_path / "screen.parquet"
    client = StubClient(body=_screener_body_json())
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "screener",
            "--query",
            "SELECT ticker FROM EQUITY LIMIT 3",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        stderr=stderr,
        client=client,
    )

    assert exit_code == 0, stderr.getvalue()
    assert out_path.exists()
    assert len(client.post_calls) == 1
    params = client.post_calls[0][1]
    assert params["formatted"] is False
    assert params["useRecordsResponse"] is True

    descriptor = json.loads(stdout.getvalue().rstrip("\n"))
    assert descriptor["command"] == "screener"
    assert descriptor["rows"] == EXPECTED_ROW_COUNT
    assert descriptor["columns"] == ["ticker"]


def test_screener_parquet_with_formatted_is_rejected(tmp_path: Path) -> None:
    """--format parquet + --formatted is rejected at parse time with exit 2."""

    out_path = tmp_path / "screen.parquet"
    client = StubClient(body=_screener_body_json())
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "screener",
                "--query",
                "SELECT ticker FROM EQUITY LIMIT 3",
                "--format",
                "parquet",
                "--formatted",
                "--out",
                str(out_path),
            ],
            stderr=stderr,
            client=client,
        )
    assert exc_info.value.code == ARGPARSE_ERROR
    err = stderr.getvalue().lower()
    assert "parquet" in err
    assert "scalar" in err or "formatted" in err
    assert not out_path.exists()
    assert not client.post_calls


_EXPECTED_MARKET_CAP = 3_000_000_000_000


def test_screener_json_with_formatted_keeps_request_formatted_true() -> None:
    """JSON path: --formatted toggles the wire param and preserves wrapped structs."""

    body = json.dumps(
        {
            "finance": {
                "result": [
                    {
                        "records": [
                            {
                                "ticker": "AAPL",
                                "marketCap": {
                                    "raw": _EXPECTED_MARKET_CAP,
                                    "fmt": "3T",
                                    "longFmt": "3,000,000,000,000",
                                },
                            }
                        ]
                    }
                ],
                "error": None,
            }
        }
    )
    client = StubClient(body=body)
    stdout = StringIO()
    exit_code = main(
        [
            "screener",
            "--query",
            "SELECT ticker, marketCap FROM EQUITY LIMIT 1",
            "--formatted",
        ],
        stdout=stdout,
        client=client,
    )
    assert exit_code == 0
    params = client.post_calls[0][1]
    assert params["formatted"] is True
    # Raw response body is printed verbatim — the wrapped struct survives end-to-end.
    out_text = stdout.getvalue().rstrip("\n")
    assert out_text == body
    payload = json.loads(out_text)
    record = payload["finance"]["result"][0]["records"][0]
    assert isinstance(record["marketCap"], dict)
    assert record["marketCap"]["raw"] == _EXPECTED_MARKET_CAP
    assert record["marketCap"]["fmt"] == "3T"
    assert record["marketCap"]["longFmt"] == "3,000,000,000,000"


def test_screener_json_default_requests_scalar_cells() -> None:
    """JSON path default sends formatted=False to Yahoo."""

    body = '{"finance":{"result":[{"records":[{"ticker":"AAPL"}]}]}}'
    client = StubClient(body=body)
    stdout = StringIO()
    exit_code = main(
        [
            "screener",
            "--query",
            "SELECT ticker FROM EQUITY LIMIT 1",
        ],
        stdout=stdout,
        client=client,
    )
    assert exit_code == 0
    params = client.post_calls[0][1]
    assert params["formatted"] is False
    assert params["useRecordsResponse"] is True


# --- Visualization -----------------------------------------------------------


def test_visualization_parquet_happy_path(tmp_path: Path) -> None:
    """Visualization SELECT path writes Parquet from documents[]."""

    out_path = tmp_path / "earn.parquet"
    client = StubClient(body=_visualization_body_json())
    stdout = StringIO()
    stderr = StringIO()
    exit_code = main(
        [
            "visualization",
            "--query",
            "SELECT ticker, startdatetime FROM sp_earnings LIMIT 3",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        stderr=stderr,
        client=client,
    )
    assert exit_code == 0, stderr.getvalue()
    assert out_path.exists()
    descriptor = json.loads(stdout.getvalue().rstrip("\n"))
    assert descriptor["command"] == "visualization"
    assert descriptor["rows"] == EXPECTED_ROW_COUNT


def test_visualization_aggregate_parquet_is_rejected(tmp_path: Path) -> None:
    """AGGREGATE queries cannot be written to Parquet; user is directed to JSON."""

    out_path = tmp_path / "agg.parquet"
    client = StubClient(body='{"finance":{"result":[{}]}}')
    stderr = StringIO()
    exit_code = main(
        [
            "visualization",
            "--query",
            "AGGREGATE date_hist(startdatetime, '1d') FROM sp_earnings",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stderr=stderr,
        client=client,
    )
    assert exit_code != 0
    err = stderr.getvalue().lower()
    assert "aggregate" in err
    assert "--format json" in err
    assert not out_path.exists()
    assert not client.post_calls


# --- Regression tests for reviewer feedback ---------------------------------


def test_chart_parquet_accepts_iso_date_periods(tmp_path: Path) -> None:
    """ISO ``YYYY-MM-DD`` ``--period1`` / ``--period2`` reach Parquet metadata as ints.

    Regression for the crash where ``int(namespace.period1)`` ran on the
    raw string ``"2024-01-01"`` (Issue #1).
    """

    out_path = tmp_path / "iso.parquet"
    client = StubClient(body=_chart_body_json())
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "chart",
            "AAPL",
            "--period1",
            "2024-01-01",
            "--period2",
            "2024-01-05",
            "--interval",
            "1d",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        stderr=stderr,
        client=client,
    )

    assert exit_code == 0, stderr.getvalue()
    assert out_path.exists()
    # 2024-01-01 UTC = epoch 1_704_067_200; 2024-01-05 UTC = 1_704_412_800.
    expected_period1 = 1_704_067_200
    expected_period2 = 1_704_412_800
    raw_meta = pl.read_parquet_metadata(out_path)
    meta = {k: v for k, v in raw_meta.items() if k != "ARROW:schema"}
    assert meta["period1"] == str(expected_period1)
    assert meta["period2"] == str(expected_period2)
    # The wire call to Yahoo also used integer seconds.
    assert client.calls[0][1]["period1"] == expected_period1
    assert client.calls[0][1]["period2"] == expected_period2


def test_chart_parquet_default_periods_match_wire_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Default period1/period2 stamped in Parquet metadata equal the wire values."""

    monkeypatch.setattr("yoghurt.params.time.time", lambda: 1_777_903_200.9)
    out_path = tmp_path / "default.parquet"
    client = StubClient(body=_chart_body_json())
    stdout = StringIO()

    exit_code = main(
        ["chart", "AAPL", "--format", "parquet", "--out", str(out_path)],
        stdout=stdout,
        client=client,
    )

    assert exit_code == 0
    expected_period2 = 1_777_903_200
    expected_period1 = expected_period2 - 3 * 24 * 60 * 60
    assert client.calls[0][1]["period1"] == expected_period1
    assert client.calls[0][1]["period2"] == expected_period2
    raw_meta = pl.read_parquet_metadata(out_path)
    meta = {k: v for k, v in raw_meta.items() if k != "ARROW:schema"}
    assert meta["period1"] == str(expected_period1)
    assert meta["period2"] == str(expected_period2)


def test_visualization_aggregate_body_json_is_rejected(
    tmp_path: Path,
) -> None:
    """A ``--body-json`` payload with a top-level ``aggregation`` is rejected.

    Regression for Issue #2: the AGGREGATE rejection only fired when
    ``--query`` was used.
    """

    out_path = tmp_path / "agg.parquet"
    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "query": {"operator": "and", "operands": []},
                "aggregation": {
                    "operator": "date_hist",
                    "operands": [
                        {"operator": "eq", "operands": ["field", "startdatetime"]},
                        {"operator": "eq", "operands": ["interval", "1d"]},
                    ],
                },
                "entityIdType": "sp_earnings",
            }
        ),
        encoding="utf-8",
    )
    client = StubClient(body='{"finance":{"result":[{}]}}')
    stderr = StringIO()

    exit_code = main(
        [
            "visualization",
            "--body-json",
            f"@{body_path}",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stderr=stderr,
        client=client,
    )

    assert exit_code != 0
    err = stderr.getvalue().lower()
    assert "aggregate" in err
    assert "--format json" in err
    assert not out_path.exists()
    assert not client.post_calls


def test_visualization_body_json_select_writes_parquet_with_response_columns(
    tmp_path: Path,
) -> None:
    """``--body-json`` SELECT-style call writes Parquet using response column order.

    Regression for Issue #13 — the writer's fallback to first-record key
    order is exercised end-to-end through the CLI.
    """

    out_path = tmp_path / "viz.parquet"
    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "query": {"operator": "and", "operands": []},
                "includeFields": ["ticker", "startdatetime"],
                "entityIdType": "sp_earnings",
                "size": 2,
            }
        ),
        encoding="utf-8",
    )
    client = StubClient(body=_visualization_body_json())
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "visualization",
            "--body-json",
            f"@{body_path}",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        stderr=stderr,
        client=client,
    )

    assert exit_code == 0, stderr.getvalue()
    df = pl.read_parquet(out_path)
    assert df.columns == ["ticker", "startdatetime"]
    raw_meta = pl.read_parquet_metadata(out_path)
    meta = {k: v for k, v in raw_meta.items() if k != "ARROW:schema"}
    assert meta["query"] == "<body-json>"


def test_chart_parquet_creates_missing_parent_dir(tmp_path: Path) -> None:
    """Writer auto-creates parent directories that don't exist yet."""

    out_path = tmp_path / "new" / "nested" / "chart.parquet"
    client = StubClient(body=_chart_body_json())
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "chart",
            "AAPL",
            "--period1",
            "1703980800",
            "--period2",
            "1704499200",
            "--interval",
            "1d",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        stderr=stderr,
        client=client,
    )
    assert exit_code == 0
    assert out_path.exists()


def test_chart_parquet_unwritable_path_is_user_facing_error(
    tmp_path: Path,
) -> None:
    """OS write failures surface as a YoghurtError, not a raw traceback.

    Regression for Issue #5. Uses a file-as-parent to produce an OS error
    that mkdir cannot resolve.
    """

    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    out_path = blocker / "chart.parquet"
    client = StubClient(body=_chart_body_json())
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "chart",
            "AAPL",
            "--period1",
            "1703980800",
            "--period2",
            "1704499200",
            "--interval",
            "1d",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        stderr=stderr,
        client=client,
    )
    assert exit_code != 0
    err = stderr.getvalue().lower()
    assert "failed to write parquet" in err or "parquet" in err
    assert not out_path.exists()


# --- Negative guards ---------------------------------------------------------


def test_quote_rejects_format_parquet(tmp_path: Path) -> None:
    """Quote rejects --format parquet with a message naming the supported commands."""

    out_path = tmp_path / "q.parquet"
    client = StubClient()
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "quote",
                "AAPL",
                "--format",
                "parquet",
                "--out",
                str(out_path),
            ],
            stderr=stderr,
            client=client,
        )
    assert exc_info.value.code == ARGPARSE_ERROR
    err = stderr.getvalue().lower()
    assert "parquet" in err
    assert "chart" in err
    assert "screener" in err
    assert "visualization" in err


def test_quote_rejects_out_alone(tmp_path: Path) -> None:
    """Quote rejects --out with a directed message naming the supported commands."""

    out_path = tmp_path / "q.parquet"
    client = StubClient()
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "quote",
                "AAPL",
                "--out",
                str(out_path),
            ],
            stderr=stderr,
            client=client,
        )
    assert exc_info.value.code == ARGPARSE_ERROR
    err = stderr.getvalue().lower()
    assert "chart" in err
    assert "screener" in err
    assert "visualization" in err


# --- Help pins ---------------------------------------------------------------


def test_chart_help_documents_format_and_out(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Chart --help shows --format / --out and notes --out is required for parquet."""

    with pytest.raises(SystemExit) as exc_info:
        main(["chart", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--format {json,parquet}" in out
    assert "--out PATH" in out
    assert "Required when --format parquet" in out


def test_screener_help_documents_format_and_out_and_formatted_default_false(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Screener --help shows the parquet flags and the new --formatted default."""

    with pytest.raises(SystemExit) as exc_info:
        main(["screener", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--format {json,parquet}" in out
    assert "--out PATH" in out
    assert_formatted_default_false(out)


def test_visualization_help_documents_format_and_out(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Visualization --help shows the parquet flags."""

    with pytest.raises(SystemExit) as exc_info:
        main(["visualization", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--format {json,parquet}" in out
    assert "--out PATH" in out


def test_quote_help_does_not_show_parquet(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Other commands must not mention --format parquet."""

    with pytest.raises(SystemExit) as exc_info:
        main(["quote", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--format {json,parquet}" not in out
    assert "--out PATH" not in out
    assert "parquet" not in out.lower()


def test_options_help_does_not_show_parquet(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Options command help must not advertise the parquet path."""

    with pytest.raises(SystemExit) as exc_info:
        main(["options", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--format {json,parquet}" not in out
    assert "parquet" not in out.lower()


def test_descriptor_for_chart_includes_size_and_path(tmp_path: Path) -> None:
    """The chart descriptor is a parseable single-line JSON object."""

    out_path = tmp_path / "ch.parquet"
    client = StubClient(body=_chart_body_json())
    stdout = StringIO()
    exit_code = main(
        [
            "chart",
            "AAPL",
            "--period1",
            "1703980800",
            "--period2",
            "1704499200",
            "--interval",
            "1d",
            "--format",
            "parquet",
            "--out",
            str(out_path),
        ],
        stdout=stdout,
        client=client,
    )
    assert exit_code == 0
    line = stdout.getvalue().rstrip("\n")
    assert "\n" not in line
    payload: dict[str, Any] = json.loads(line)
    assert payload["out"] == str(out_path)
    assert payload["bytes"] > 0
