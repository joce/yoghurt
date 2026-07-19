"""Tests for ``yoghurt.parquet_writer``."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import polars as pl
import pytest

from yoghurt import __version__
from yoghurt.exceptions import YoghurtError
from yoghurt.parquet_writer import (
    ParquetWriterError,
    write_chart_parquet,
    write_tabular_parquet,
)

if TYPE_CHECKING:
    from pathlib import Path


_FIVE_BARS_TIMESTAMPS = [
    1_704_067_200,
    1_704_153_600,
    1_704_240_000,
    1_704_326_400,
    1_704_412_800,
]
_SCREENER_HAPPY_PATH_ROWS = 3
_VISUALIZATION_HAPPY_PATH_ROWS = 2


def _chart_body(  # ruff:ignore[too-many-arguments] - keyword-only helper for test fixtures.
    *,
    timestamps: list[int] | None = None,
    opens: list[float | None] | None = None,
    highs: list[float | None] | None = None,
    lows: list[float | None] | None = None,
    closes: list[float | None] | None = None,
    volumes: list[float | None] | None = None,
    adjclose: list[float | None] | object | None = ...,
    meta: dict[str, object] | None = None,
) -> str:
    """Build a minimal Yahoo chart response JSON string for tests."""

    if timestamps is None:
        timestamps = list(_FIVE_BARS_TIMESTAMPS)
    quote_block: dict[str, list[float | None]] = {
        "open": opens if opens is not None else [100.0, 101.0, 102.0, 103.0, 104.0],
        "high": highs if highs is not None else [110.0, 111.0, 112.0, 113.0, 114.0],
        "low": lows if lows is not None else [90.0, 91.0, 92.0, 93.0, 94.0],
        "close": closes if closes is not None else [105.0, 106.0, 107.0, 108.0, 109.0],
        "volume": (
            volumes if volumes is not None else [1000.0, 2000.0, 3000.0, 4000.0, 5000.0]
        ),
    }
    indicators: dict[str, object] = {"quote": [quote_block]}
    if adjclose is not ...:
        # Caller wanted to control adjclose presence.
        if adjclose is None:
            pass  # Skip the key entirely.
        else:
            indicators["adjclose"] = [{"adjclose": adjclose}]
    else:
        indicators["adjclose"] = [{"adjclose": [104.5, 105.5, 106.5, 107.5, 108.5]}]
    result_block = {
        "meta": meta if meta is not None else {"symbol": "AAPL", "currency": "USD"},
        "timestamp": timestamps,
        "indicators": indicators,
    }
    return json.dumps({"chart": {"result": [result_block], "error": None}})


# --- Chart writer ------------------------------------------------------------


def test_chart_writer_happy_path(tmp_path: Path) -> None:
    """Chart writer produces correct schema, rows, and key_value_metadata."""

    out_path = tmp_path / "aapl.parquet"
    descriptor = write_chart_parquet(
        _chart_body(),
        out_path,
        ticker="AAPL",
        interval="1d",
        period1=1_703_980_800,
        period2=1_704_499_200,
    )

    assert descriptor["format"] == "parquet"
    assert descriptor["command"] == "chart"
    assert descriptor["ticker"] == "AAPL"
    assert descriptor["interval"] == "1d"
    assert descriptor["rows"] == len(_FIVE_BARS_TIMESTAMPS)
    assert descriptor["out"] == str(out_path)
    assert isinstance(descriptor["bytes"], int)
    assert descriptor["bytes"] > 0

    df = pl.read_parquet(out_path)
    assert df.height == len(_FIVE_BARS_TIMESTAMPS)
    assert df.columns == ["ts", "open", "high", "low", "close", "volume", "adj_close"]
    assert df.schema["ts"] == pl.Datetime("ns", "UTC")
    assert df.schema["open"] == pl.Float64
    assert df.schema["high"] == pl.Float64
    assert df.schema["low"] == pl.Float64
    assert df.schema["close"] == pl.Float64
    assert df.schema["volume"] == pl.Int64
    assert df.schema["adj_close"] == pl.Float64

    raw_meta = pl.read_parquet_metadata(out_path)
    meta = {k: v for k, v in raw_meta.items() if k != "ARROW:schema"}
    assert meta["yoghurt_command"] == "chart"
    assert meta["yoghurt_version"] == __version__
    assert meta["ticker"] == "AAPL"
    assert meta["interval"] == "1d"
    assert meta["period1"] == "1703980800"
    assert meta["period2"] == "1704499200"
    meta_json = json.loads(meta["yahoo_response_meta_json"])
    assert meta_json["symbol"] == "AAPL"

    # The ``ts`` column round-trips as tz-aware UTC datetimes that match the
    # original epoch-second inputs exactly.
    expected_datetimes = [
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 2, tzinfo=timezone.utc),
        datetime(2024, 1, 3, tzinfo=timezone.utc),
        datetime(2024, 1, 4, tzinfo=timezone.utc),
        datetime(2024, 1, 5, tzinfo=timezone.utc),
    ]
    assert df.get_column("ts").to_list() == expected_datetimes


def test_chart_writer_preserves_nulls(tmp_path: Path) -> None:
    """Yahoo nulls in OHLC and volume are written as Parquet nulls."""

    out_path = tmp_path / "nulls.parquet"
    write_chart_parquet(
        _chart_body(
            opens=[100.0, None, 102.0, None, 104.0],
            volumes=[1000.0, 2000.0, None, 4000.0, 5000.0],
        ),
        out_path,
        ticker="AAPL",
        interval="1d",
        period1=0,
        period2=1,
    )

    df = pl.read_parquet(out_path)
    opens = df.get_column("open").to_list()
    volumes = df.get_column("volume").to_list()
    assert opens == [100.0, None, 102.0, None, 104.0]
    assert volumes == [1000, 2000, None, 4000, 5000]


def test_chart_writer_missing_adjclose(tmp_path: Path) -> None:
    """Missing adjclose block yields an all-null adj_close column with full schema."""

    out_path = tmp_path / "noadj.parquet"
    write_chart_parquet(
        _chart_body(adjclose=None),
        out_path,
        ticker="AAPL",
        interval="1d",
        period1=0,
        period2=1,
    )

    df = pl.read_parquet(out_path)
    assert df.columns[-1] == "adj_close"
    assert df.schema["adj_close"] == pl.Float64
    assert df.get_column("adj_close").to_list() == [None, None, None, None, None]


def test_chart_writer_length_mismatch_raises(tmp_path: Path) -> None:
    """Mismatched indicator length raises a clear error and writes no file."""

    out_path = tmp_path / "bad.parquet"
    with pytest.raises(ParquetWriterError) as exc_info:
        write_chart_parquet(
            _chart_body(opens=[100.0, 101.0]),  # length 2 vs timestamp length 5
            out_path,
            ticker="AAPL",
            interval="1d",
            period1=0,
            period2=1,
        )
    assert "length" in str(exc_info.value).lower()
    assert not out_path.exists()


def test_chart_writer_empty_timestamp(tmp_path: Path) -> None:
    """Empty timestamp array yields a valid empty Parquet with full schema."""

    out_path = tmp_path / "empty.parquet"
    write_chart_parquet(
        _chart_body(
            timestamps=[],
            opens=[],
            highs=[],
            lows=[],
            closes=[],
            volumes=[],
            adjclose=[],
        ),
        out_path,
        ticker="AAPL",
        interval="1d",
        period1=0,
        period2=1,
    )

    df = pl.read_parquet(out_path)
    assert df.height == 0
    assert df.columns == [
        "ts",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adj_close",
    ]


def test_chart_writer_non_integer_volume_raises(tmp_path: Path) -> None:
    """A non-integer volume entry raises rather than truncating."""

    out_path = tmp_path / "badvol.parquet"
    with pytest.raises(ParquetWriterError) as exc_info:
        write_chart_parquet(
            _chart_body(volumes=[1000.0, 2000.5, 3000.0, 4000.0, 5000.0]),
            out_path,
            ticker="AAPL",
            interval="1d",
            period1=0,
            period2=1,
        )
    assert "volume" in str(exc_info.value).lower()
    assert not out_path.exists()


def test_chart_writer_error_inherits_yoghurt_error(tmp_path: Path) -> None:
    """ParquetWriterError is catchable as YoghurtError in the CLI."""

    out_path = tmp_path / "bad.parquet"
    with pytest.raises(YoghurtError):
        write_chart_parquet(
            _chart_body(opens=[100.0]),  # mismatch
            out_path,
            ticker="AAPL",
            interval="1d",
            period1=0,
            period2=1,
        )


# --- Tabular writer ----------------------------------------------------------


def _records_body(records: list[dict[str, object]]) -> str:
    """Build a screener-shaped JSON body with the given records."""

    return json.dumps(
        {
            "finance": {
                "result": [
                    {
                        "records": records,
                        "total": len(records),
                    }
                ],
                "error": None,
            }
        }
    )


def _documents_body(
    columns: list[dict[str, str]],
    rows: list[list[object]],
) -> str:
    """Build a visualization-shaped JSON body.

    The real shape Yahoo's ``/visualization`` returns for SELECT is
    ``finance.result[0].documents[0]`` with ``columns`` (``id``, ``label``,
    ``type``) and ``rows`` (positional arrays). Pinning this
    structure here guards against drift in the writer.
    """

    return json.dumps(
        {
            "finance": {
                "result": [
                    {
                        "documents": [
                            {
                                "entityIdType": "SP_EARNINGS",
                                "columns": columns,
                                "rows": rows,
                            }
                        ],
                        "total": len(rows),
                    }
                ],
                "error": None,
            }
        }
    )


def test_tabular_writer_screener_happy_path(tmp_path: Path) -> None:
    """Mixed int/float/string columns are inferred to the expected dtypes."""

    out_path = tmp_path / "screener.parquet"
    body = _records_body(
        [
            {
                "ticker": "AAPL",
                "marketCap": 3_000_000_000_000,
                "peRatio": 30.5,
                "sector": "Technology",
            },
            {
                "ticker": "MSFT",
                "marketCap": 2_500_000_000_000,
                "peRatio": 28.0,
                "sector": "Technology",
            },
            {
                "ticker": "GOOG",
                "marketCap": 1_800_000_000_000,
                "peRatio": 25.4,
                "sector": "Communication",
            },
        ]
    )

    descriptor = write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query="SELECT ticker, marketCap, peRatio, sector FROM EQUITY LIMIT 3",
        wire_params={
            "lang": "en-US",
            "region": "US",
            "formatted": False,
            "useRecordsResponse": True,
        },
    )

    df = pl.read_parquet(out_path)
    assert df.height == _SCREENER_HAPPY_PATH_ROWS
    assert df.columns == ["ticker", "marketCap", "peRatio", "sector"]
    assert df.schema["ticker"] == pl.Utf8
    assert df.schema["marketCap"] == pl.Int64
    assert df.schema["peRatio"] == pl.Float64
    assert df.schema["sector"] == pl.Utf8

    assert descriptor["format"] == "parquet"
    assert descriptor["command"] == "screener"
    assert descriptor["rows"] == _SCREENER_HAPPY_PATH_ROWS
    assert descriptor["columns"] == ["ticker", "marketCap", "peRatio", "sector"]
    assert isinstance(descriptor["bytes"], int)

    raw_meta = pl.read_parquet_metadata(out_path)
    meta = {k: v for k, v in raw_meta.items() if k != "ARROW:schema"}
    assert meta["yoghurt_command"] == "screener"
    assert meta["yoghurt_version"] == __version__
    assert meta["route"] == "screener"
    assert meta["query"].startswith("SELECT ticker")
    wire_params = json.loads(meta["wire_params_json"])
    assert wire_params["formatted"] is False
    assert wire_params["useRecordsResponse"] is True
    assert meta["total_rows"] == "3"


def test_tabular_writer_null_cells_preserved(tmp_path: Path) -> None:
    """Null cells round-trip as Parquet nulls."""

    out_path = tmp_path / "nulls.parquet"
    body = _records_body(
        [
            {"ticker": "AAPL", "marketCap": 3_000_000_000_000},
            {"ticker": "MSFT", "marketCap": None},
            {"ticker": None, "marketCap": 1_800_000_000_000},
        ]
    )
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query="SELECT ticker, marketCap FROM EQUITY",
        wire_params={"formatted": False, "useRecordsResponse": True},
    )

    df = pl.read_parquet(out_path)
    assert df.get_column("ticker").to_list() == ["AAPL", "MSFT", None]
    assert df.get_column("marketCap").to_list() == [
        3_000_000_000_000,
        None,
        1_800_000_000_000,
    ]


def test_tabular_writer_all_null_column_is_string(tmp_path: Path) -> None:
    """An all-null column defaults to string dtype."""

    out_path = tmp_path / "allnull.parquet"
    body = _records_body(
        [
            {"ticker": "AAPL", "stockStory": None},
            {"ticker": "MSFT", "stockStory": None},
        ]
    )
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query="SELECT ticker, stockStory FROM EQUITY",
        wire_params={"formatted": False, "useRecordsResponse": True},
    )

    df = pl.read_parquet(out_path)
    assert df.schema["stockStory"] == pl.Utf8
    assert df.get_column("stockStory").to_list() == [None, None]


def test_tabular_writer_mixed_type_column_falls_back_to_string(tmp_path: Path) -> None:
    """A column with mixed int and string values is rendered as string."""

    out_path = tmp_path / "mixed.parquet"
    body = _records_body(
        [
            {"ticker": "AAPL", "value": 1},
            {"ticker": "MSFT", "value": "two"},
        ]
    )
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query="SELECT ticker, value FROM EQUITY",
        wire_params={"formatted": False, "useRecordsResponse": True},
    )

    df = pl.read_parquet(out_path)
    assert df.schema["value"] == pl.Utf8
    assert df.get_column("value").to_list() == ["1", "two"]


def test_tabular_writer_empty_records_with_query_is_empty_schema(
    tmp_path: Path,
) -> None:
    """Empty records produce an empty schema even when a query was provided.

    Parquet columns mirror what Yahoo actually returned. The SELECT clause
    does not synthesize a schema — if Yahoo returned no rows, there is no
    response shape to honor.
    """

    out_path = tmp_path / "empty.parquet"
    body = _records_body([])
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query="SELECT ticker, marketCap FROM EQUITY",
        wire_params={"formatted": False, "useRecordsResponse": True},
    )

    df = pl.read_parquet(out_path)
    assert df.height == 0
    assert df.columns == []


def test_tabular_writer_empty_records_no_query_is_empty_schema(tmp_path: Path) -> None:
    """Empty records without a query produce a valid empty Parquet file."""

    out_path = tmp_path / "emptynoq.parquet"
    body = _records_body([])
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query=None,
        wire_params={"formatted": False, "useRecordsResponse": True},
    )

    df = pl.read_parquet(out_path)
    assert df.height == 0
    assert df.columns == []


def test_tabular_writer_rejects_nested_struct_cell(tmp_path: Path) -> None:
    """Nested cells (e.g. formatted=True) are rejected with a clear error."""

    out_path = tmp_path / "nested.parquet"
    body = _records_body(
        [
            {"ticker": "AAPL", "marketCap": {"raw": 3_000_000_000_000, "fmt": "3T"}},
        ]
    )
    with pytest.raises(ParquetWriterError) as exc_info:
        write_tabular_parquet(
            body,
            out_path,
            command="screener",
            route="screener",
            query="SELECT ticker, marketCap FROM EQUITY",
            wire_params={"formatted": True, "useRecordsResponse": True},
        )
    assert "marketCap" in str(exc_info.value)
    assert (
        "nested" in str(exc_info.value).lower()
        or "scalar" in str(exc_info.value).lower()
    )
    assert not out_path.exists()


def test_tabular_writer_visualization_uses_documents(tmp_path: Path) -> None:
    """Visualization SELECT rows come from documents[0].rows keyed by columns[]."""

    out_path = tmp_path / "viz.parquet"
    body = _documents_body(
        columns=[
            {"id": "ticker", "label": "Symbol", "type": "STRING"},
            {"id": "startdatetime", "label": "Event Start Date", "type": "DATE"},
        ],
        rows=[
            ["AAPL", "2026-05-15T21:00:00.000Z"],
            ["MSFT", "2026-05-16T21:00:00.000Z"],
        ],
    )
    descriptor = write_tabular_parquet(
        body,
        out_path,
        command="visualization",
        route="visualization",
        query="SELECT ticker, startdatetime FROM sp_earnings LIMIT 2",
        wire_params={"lang": "en-US", "region": "US"},
    )

    assert descriptor["rows"] == _VISUALIZATION_HAPPY_PATH_ROWS
    df = pl.read_parquet(out_path)
    assert df.height == _VISUALIZATION_HAPPY_PATH_ROWS
    assert df.columns == ["ticker", "startdatetime"]
    assert df.schema["ticker"] == pl.Utf8
    assert df.schema["startdatetime"] == pl.Utf8
    assert df.get_column("ticker").to_list() == ["AAPL", "MSFT"]


def test_tabular_writer_visualization_handles_empty_rows(tmp_path: Path) -> None:
    """An empty rows array still yields a valid Parquet file with query columns."""

    out_path = tmp_path / "empty_viz.parquet"
    body = _documents_body(
        columns=[
            {"id": "ticker", "label": "Symbol", "type": "STRING"},
            {"id": "startdatetime", "label": "Event Start Date", "type": "DATE"},
        ],
        rows=[],
    )
    write_tabular_parquet(
        body,
        out_path,
        command="visualization",
        route="visualization",
        query="SELECT ticker, startdatetime FROM sp_earnings",
        wire_params={"lang": "en-US", "region": "US"},
    )

    df = pl.read_parquet(out_path)
    assert df.height == 0
    assert df.columns == ["ticker", "startdatetime"]


def test_tabular_writer_boolean_column(tmp_path: Path) -> None:
    """All-bool column is inferred to bool."""

    out_path = tmp_path / "bool.parquet"
    body = _records_body(
        [
            {"ticker": "AAPL", "isActive": True},
            {"ticker": "MSFT", "isActive": False},
        ]
    )
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query="SELECT ticker, isActive FROM EQUITY",
        wire_params={"formatted": False, "useRecordsResponse": True},
    )
    df = pl.read_parquet(out_path)
    assert df.schema["isActive"] == pl.Boolean
    assert df.get_column("isActive").to_list() == [True, False]


def test_tabular_writer_preserves_yahoo_column_order(tmp_path: Path) -> None:
    """Without a parseable query, the writer preserves the first record's key order."""

    out_path = tmp_path / "order.parquet"
    body = _records_body(
        [
            {"sector": "Technology", "ticker": "AAPL", "marketCap": 1},
            {"sector": "Technology", "ticker": "MSFT", "marketCap": 2},
        ]
    )
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query=None,
        wire_params={"formatted": False, "useRecordsResponse": True},
    )
    df = pl.read_parquet(out_path)
    assert df.columns == ["sector", "ticker", "marketCap"]


def test_tabular_writer_uses_response_keys_not_select_clause(tmp_path: Path) -> None:
    """Screener Parquet columns reflect Yahoo's response keys, not SELECT names.

    Yahoo's screener translates DSL field names to response keys (e.g.
    ``intradaymarketcap`` becomes ``marketCap``) and adds unrequested fields
    like ``logoUrl``. The Parquet file must mirror the response, so users see
    the same columns they would in the JSON output. Regression for the
    ``intradaymarketcap`` all-null column surprise.
    """

    out_path = tmp_path / "screener_response_keys.parquet"
    body = _records_body(
        [
            {
                "ticker": "NVDA",
                "logoUrl": "https://example.invalid/nvda.png",
                "marketCap": 5_400_000_000_000,
            },
            {
                "ticker": "AAPL",
                "logoUrl": "https://example.invalid/aapl.png",
                "marketCap": 4_400_000_000_000,
            },
        ]
    )
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query="SELECT ticker, intradaymarketcap FROM EQUITY LIMIT 2",
        wire_params={"formatted": False, "useRecordsResponse": True},
    )

    df = pl.read_parquet(out_path)
    assert df.columns == ["ticker", "logoUrl", "marketCap"]
    assert "intradaymarketcap" not in df.columns
    assert df.get_column("marketCap").to_list() == [
        5_400_000_000_000,
        4_400_000_000_000,
    ]


# --- Visualization document-shape validation --------------------------------


def _viz_payload(documents: object) -> str:
    """Build a finance.result[0].documents payload with no extra validation."""

    return json.dumps(
        {"finance": {"result": [{"documents": documents}], "error": None}}
    )


def test_visualization_rejects_documents_not_a_list(tmp_path: Path) -> None:
    """``documents`` must be a list — anything else is a writer error."""

    out_path = tmp_path / "bad.parquet"
    body = _viz_payload({"oops": "not a list"})
    with pytest.raises(ParquetWriterError) as exc_info:
        write_tabular_parquet(
            body,
            out_path,
            command="visualization",
            route="visualization",
            query=None,
            wire_params={},
        )
    assert "documents" in str(exc_info.value).lower()
    assert not out_path.exists()


def test_visualization_rejects_documents_zero_not_a_dict(tmp_path: Path) -> None:
    """``documents[0]`` must be an object — a stray scalar is rejected."""

    out_path = tmp_path / "bad.parquet"
    body = _viz_payload(["not an object"])
    with pytest.raises(ParquetWriterError) as exc_info:
        write_tabular_parquet(
            body,
            out_path,
            command="visualization",
            route="visualization",
            query=None,
            wire_params={},
        )
    assert "documents[0]" in str(exc_info.value)
    assert not out_path.exists()


def test_visualization_rejects_missing_columns_or_rows(tmp_path: Path) -> None:
    """``documents[0]`` must carry both ``columns`` and ``rows`` lists."""

    out_path = tmp_path / "bad.parquet"
    body = _viz_payload([{"entityIdType": "SP_EARNINGS"}])
    with pytest.raises(ParquetWriterError) as exc_info:
        write_tabular_parquet(
            body,
            out_path,
            command="visualization",
            route="visualization",
            query=None,
            wire_params={},
        )
    assert "columns" in str(exc_info.value)
    assert "rows" in str(exc_info.value)
    assert not out_path.exists()


def test_visualization_rejects_column_missing_id(tmp_path: Path) -> None:
    """Each entry in ``columns`` must have an ``id`` key."""

    out_path = tmp_path / "bad.parquet"
    body = _viz_payload(
        [
            {
                "columns": [{"label": "Symbol", "type": "STRING"}],
                "rows": [["AAPL"]],
            }
        ]
    )
    with pytest.raises(ParquetWriterError) as exc_info:
        write_tabular_parquet(
            body,
            out_path,
            command="visualization",
            route="visualization",
            query=None,
            wire_params={},
        )
    assert "columns[0]" in str(exc_info.value)
    assert "id" in str(exc_info.value)
    assert not out_path.exists()


def test_visualization_rejects_row_not_a_list(tmp_path: Path) -> None:
    """Each entry in ``rows`` must be a list (positional values)."""

    out_path = tmp_path / "bad.parquet"
    body = _viz_payload(
        [
            {
                "columns": [{"id": "ticker", "label": "Symbol", "type": "STRING"}],
                "rows": ["AAPL"],  # Should be [["AAPL"]] — scalar is invalid.
            }
        ]
    )
    with pytest.raises(ParquetWriterError) as exc_info:
        write_tabular_parquet(
            body,
            out_path,
            command="visualization",
            route="visualization",
            query=None,
            wire_params={},
        )
    assert "rows[0]" in str(exc_info.value)
    assert not out_path.exists()


def test_visualization_rejects_row_column_length_mismatch(tmp_path: Path) -> None:
    """A row whose length differs from columns[] raises rather than truncating.

    Regression for Issue #4 — ``zip(strict=False)`` silently discarded the
    extra values.
    """

    out_path = tmp_path / "bad.parquet"
    body = _viz_payload(
        [
            {
                "columns": [
                    {"id": "ticker", "label": "Symbol", "type": "STRING"},
                    {"id": "startdatetime", "label": "Date", "type": "DATE"},
                ],
                "rows": [["AAPL"]],
            }
        ]
    )
    with pytest.raises(ParquetWriterError) as exc_info:
        write_tabular_parquet(
            body,
            out_path,
            command="visualization",
            route="visualization",
            query=None,
            wire_params={},
        )
    msg = str(exc_info.value)
    assert "rows[0]" in msg
    assert "1 value" in msg or "1 values" in msg
    assert "columns" in msg
    assert "2" in msg
    assert not out_path.exists()


def test_tabular_writer_creates_missing_parent_dir(tmp_path: Path) -> None:
    """Writer auto-creates parent directories that don't exist yet."""

    out_path = tmp_path / "new" / "nested" / "tech.parquet"
    body = _records_body([{"ticker": "AAPL"}])
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query=None,
        wire_params={"formatted": False, "useRecordsResponse": True},
    )
    assert out_path.exists()


def test_tabular_writer_wraps_oserror_on_write(
    tmp_path: Path,
) -> None:
    """A write failure to an unwritable path raises ParquetWriterError.

    Regression for Issue #5 — pq.write_table failures previously escaped as
    unhandled OSError tracebacks. Uses a file-as-parent to produce an OS error
    that mkdir cannot resolve.
    """

    # Create a file where the parent directory would need to be — mkdir will fail.
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    out_path = blocker / "tech.parquet"
    body = _records_body([{"ticker": "AAPL"}])
    with pytest.raises(ParquetWriterError) as exc_info:
        write_tabular_parquet(
            body,
            out_path,
            command="screener",
            route="screener",
            query=None,
            wire_params={"formatted": False, "useRecordsResponse": True},
        )
    assert "failed to write parquet" in str(exc_info.value).lower()


def test_chart_writer_wraps_oserror_on_write(tmp_path: Path) -> None:
    """The chart writer also wraps OS errors as ParquetWriterError."""

    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    out_path = blocker / "chart.parquet"
    with pytest.raises(ParquetWriterError) as exc_info:
        write_chart_parquet(
            _chart_body(),
            out_path,
            ticker="AAPL",
            interval="1d",
            period1=0,
            period2=1,
        )
    assert "failed to write parquet" in str(exc_info.value).lower()


def test_tabular_writer_screener_total_rows_from_result(tmp_path: Path) -> None:
    """Screener: ``total_rows`` metadata reads ``finance.result[0].total``.

    Yahoo records ``count``/``total`` at the ``result[0]`` level. Pinning
    that path here documents what the writer expects and would fail loudly
    if it ever started pulling from ``records`` length instead.
    """

    out_path = tmp_path / "scr.parquet"
    body = json.dumps(
        {
            "finance": {
                "result": [
                    {
                        "start": 0,
                        "count": 2,
                        "total": 5000,
                        "records": [{"ticker": "AAPL"}, {"ticker": "MSFT"}],
                    }
                ],
                "error": None,
            }
        }
    )
    write_tabular_parquet(
        body,
        out_path,
        command="screener",
        route="screener",
        query=None,
        wire_params={"formatted": False, "useRecordsResponse": True},
    )
    raw_meta = pl.read_parquet_metadata(out_path)
    meta = {k: v for k, v in raw_meta.items() if k != "ARROW:schema"}
    assert meta["total_rows"] == "5000"


def test_tabular_writer_visualization_total_rows_from_result(tmp_path: Path) -> None:
    """Visualization: ``total_rows`` metadata reads ``finance.result[0].total``.

    Yahoo's visualization endpoint reports the full match count at
    ``result[0].total`` even though the per-row payload lives in
    ``documents[0].rows`` — confirmed via live probe. Pin the path.
    """

    out_path = tmp_path / "viz.parquet"
    body = json.dumps(
        {
            "finance": {
                "result": [
                    {
                        "total": 742,
                        "documents": [
                            {
                                "columns": [
                                    {
                                        "id": "ticker",
                                        "label": "Symbol",
                                        "type": "STRING",
                                    }
                                ],
                                "rows": [["AAPL"], ["MSFT"]],
                            }
                        ],
                    }
                ],
                "error": None,
            }
        }
    )
    write_tabular_parquet(
        body,
        out_path,
        command="visualization",
        route="visualization",
        query=None,
        wire_params={},
    )
    raw_meta = pl.read_parquet_metadata(out_path)
    meta = {k: v for k, v in raw_meta.items() if k != "ARROW:schema"}
    assert meta["total_rows"] == "742"
