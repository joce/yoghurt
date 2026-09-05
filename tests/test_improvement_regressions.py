"""Regression checks for response contracts and failure-safe replacement."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import time
import traceback
from pathlib import Path
from typing import Any

import httpx2 as httpx
import polars as pl
import pytest

from tests.conftest import collect_nested_extras
from yoghurt import api
from yoghurt._core import interpret_body
from yoghurt.client import YahooClient
from yoghurt.exceptions import YahooApiError, YahooRequestError
from yoghurt.models.options import OptionChain, OptionExpiration, OptionStraddle
from yoghurt.parquet_writer import (
    ParquetWriterError,
    _write_frame,  # pyright: ignore[reportPrivateUsage]
)
from yoghurt.query import QueryError, parse
from yoghurt.session_cache import load_session_cache, save_session_cache
from yoghurt.skills import _install
from yoghurt.tabular import (
    TabularShapeError,
    build_chart_frame,
    build_tabular_frame,
    collect_column_data,
    extract_chart_columns,
    parse_tabular_payload,
    resolve_column_order,
)

CORPUS = Path(__file__).parent / "fixtures" / "corpus"


@pytest.mark.parametrize(
    "path", sorted((CORPUS / "options" / "variants").glob("*.json"))
)
def test_straddle_capture_has_no_unmodeled_data(path: Path) -> None:
    """Real paired responses validate, including absent call and put legs."""
    record = json.loads(path.read_text(encoding="utf-8"))["optionChain"]["result"][0]
    chain = OptionChain.model_validate(record)
    assert not collect_nested_extras(chain)
    expiration = chain.options[0]
    assert expiration.calls is None
    assert expiration.puts is None
    assert expiration.straddles
    assert any(pair.call is None for pair in expiration.straddles)
    assert any(pair.put is None for pair in expiration.straddles)
    assert {
        name
        for name, field in OptionStraddle.model_fields.items()
        if field.is_required()
    } == {"strike"}


@pytest.mark.parametrize(
    "collections", [{}, {"calls": []}, {"straddles": [], "puts": []}]
)
def test_options_reject_missing_or_mixed_collections(
    collections: dict[str, Any],
) -> None:
    """Optional collections do not make malformed expiration objects valid."""
    with pytest.raises(ValueError, match="expiration must contain"):
        OptionExpiration.model_validate(
            {"expirationDate": 1783123200, "hasMiniOptions": False, **collections}
        )


def test_typed_quote_has_no_projection_or_formatting_parameters() -> None:
    """Removed arguments cannot silently undermine the full-model contract."""
    for function in (api.Ticker.quote, api.quotes):
        assert (
            not {"fields", "formatted"} & inspect.signature(function).parameters.keys()
        )
    for name, function in inspect.getmembers(api, inspect.isfunction):
        if not name.startswith("_"):
            assert "formatted" not in inspect.signature(function).parameters
    for name, function in inspect.getmembers(api.Ticker, inspect.isfunction):
        if not name.startswith("_"):
            assert "formatted" not in inspect.signature(function).parameters


@pytest.mark.parametrize(
    "suffix",
    [
        "LIMIT -1",
        "LIMIT 0",
        "LIMIT 1.5",
        "LIMIT 1e2",
        "LIMIT 2 OFFSET -1",
        "LIMIT 2 OFFSET 1.5",
        "WHERE price = 1e",
        "WHERE price = 1e999",
    ],
)
def test_bad_query_numbers_have_positional_errors(suffix: str) -> None:
    """Invalid pagination and scalar numbers fail at the DSL boundary."""
    with pytest.raises(QueryError, match="position"):
        parse(
            f"SELECT symbol FROM equity {suffix}",  # ruff: ignore[hardcoded-sql-expression]
        )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"quoteResponse": []},
        {"quoteResponse": {}},
        {"quoteResponse": {"result": [None]}},
    ],
)
def test_missing_quote_envelopes_are_api_errors(payload: dict[str, Any]) -> None:
    """Malformed containers cannot leak KeyError or pass as empty data."""
    with pytest.raises(YahooApiError, match="malformed-response"):
        interpret_body("quote", json.dumps(payload))


def test_screener_columns_preserve_later_records_in_frame_and_parquet(
    tmp_path: Path,
) -> None:
    """Heterogeneous rows retain every returned key in first-seen order."""
    records = [{"symbol": "A"}, {"symbol": "B", "price": 2}]
    columns = resolve_column_order(records, None)
    frame = build_tabular_frame(collect_column_data(records, columns), columns)
    assert frame.columns == ["symbol", "price"]
    assert frame["price"].to_list() == [None, 2]
    output = tmp_path / "rows.parquet"
    _write_frame(frame, output, {})
    assert pl.read_parquet(output).to_dicts() == frame.to_dicts()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"finance": []},
        {"finance": {"result": None}},
        {"finance": {"result": [{}]}},
    ],  # pyright: ignore[reportUnknownArgumentType]
)
def test_bad_query_envelopes_are_not_empty_frames(payload: dict[str, Any]) -> None:
    """Only an actual empty result collection counts as an empty query."""
    with pytest.raises(TabularShapeError):
        parse_tabular_payload(payload, "screener", "screener")
    assert parse_tabular_payload(
        {"finance": {"result": []}}, "screener", "screener"
    ) == ([], 0, None)


@pytest.mark.parametrize("value", [[], "bad", 1])
def test_chart_rejects_wrong_indicator_containers(value: object) -> None:
    """Wrong nested container types have a shared tabular error."""
    with pytest.raises(TabularShapeError):
        extract_chart_columns({"indicators": value})


def test_chart_bad_timestamp_conversion_is_tabular_error() -> None:
    """Conversion errors do not escape as built-in or polars exceptions."""
    columns = {
        name: [1] for name in ("open", "high", "low", "close", "volume", "adj_close")
    }
    with pytest.raises(TabularShapeError):
        build_chart_frame(["bad"], columns)  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    "payload",
    [
        [],
        None,
        "bad",
        {"crumb": 4},
        {"crumb": "test", "cookies": [None]},
        {"crumb": "test", "cookies": [], "expiry": "nan"},
    ],
)
def test_malformed_session_cache_is_a_miss(tmp_path: Path, payload: object) -> None:
    """Malformed JSON structures never crash session initialization."""
    path = tmp_path / "session.json"
    path.write_text(json.dumps(payload))
    assert load_session_cache(path) is None


def test_cache_replacement_failure_preserves_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An interrupted replacement keeps the prior cache and cleans its temporary."""
    path = tmp_path / "session.json"
    path.write_text("old")

    def fail_replace(self: Path, target: Path) -> Path:
        del self, target
        message = "replacement failed"
        raise OSError(message)

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="replacement failed"):
        save_session_cache(path, httpx.Cookies(), "synthetic", time.time() + 3600)
    assert path.read_text() == "old"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits")
def test_cache_file_is_private(tmp_path: Path) -> None:
    """The replacement file grants no group or world permissions."""
    path = tmp_path / "cache.json"
    save_session_cache(path, httpx.Cookies(), "synthetic", time.time() + 3600)
    assert path.stat().st_mode & 0o077 == 0


def test_parquet_failure_preserves_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed writer cannot truncate the user's existing Parquet output."""
    path = tmp_path / "rows.parquet"
    path.write_bytes(b"old")

    def fail_write(self: pl.DataFrame, output: Path, **kwargs: object) -> None:
        del self, kwargs
        output.write_bytes(b"partial")
        message = "write failed"
        raise OSError(message)

    monkeypatch.setattr(pl.DataFrame, "write_parquet", fail_write)
    with pytest.raises(ParquetWriterError):
        _write_frame(pl.DataFrame({"x": [1]}), path, {})
    assert path.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [path]


def test_skill_failed_replacement_restores_previous_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A staged update failure restores the owned skill directory."""
    _install.install([tmp_path])
    marker = tmp_path / "yoghurt" / "previous.txt"
    marker.write_text("previous")
    rename = Path.rename

    def fail_stage(self: Path, target: Path) -> Path:
        if self.name == "new":
            message = "replacement failed"
            raise OSError(message)
        return rename(self, target)

    monkeypatch.setattr(Path, "rename", fail_stage)
    with pytest.raises(OSError, match="replacement failed"):
        _install.install([tmp_path])
    assert marker.read_text() == "previous"
    assert list(tmp_path.iterdir()) == [tmp_path / "yoghurt"]


@pytest.mark.parametrize("refreshed_crumb", ["old", "new"])
@pytest.mark.asyncio
async def test_session_refresh_is_once_for_concurrent_stale_requests(
    tmp_path: Path,
    refreshed_crumb: str,
) -> None:
    """Concurrent stale replies share one refresh and each replay once."""
    calls: list[str] = []
    old_requests = 0
    concurrent_requests = 2
    both_started = asyncio.Event()

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal old_requests
        calls.append(request.url.path)
        if request.url.path == "/":
            return httpx.Response(
                200,
                headers={
                    "set-cookie": "A3=synthetic-cookie; Domain=.yahoo.com; Path=/"
                },
            )
        if request.url.path.endswith("getcrumb"):
            return httpx.Response(200, text=refreshed_crumb)
        if (
            request.url.params.get("crumb") == "old"
            and old_requests < concurrent_requests
        ):
            old_requests += 1
            if old_requests == concurrent_requests:
                both_started.set()
            await both_started.wait()
            return httpx.Response(
                401,
                json={
                    "finance": {
                        "error": {
                            "code": "Unauthorized",
                            "description": "Invalid Crumb",
                        }
                    }
                },
            )
        return httpx.Response(200, text="ok")

    cache = tmp_path / "session.json"
    cookies = httpx.Cookies()
    cookies.set("A3", "synthetic-cookie", domain=".yahoo.com")
    save_session_cache(cache, cookies, "old", time.time() + 3600)
    client = YahooClient(
        transport=httpx.MockTransport(handle), session_cache_path=cache
    )
    try:
        assert await asyncio.gather(
            client.get("/test", {}), client.get("/test", {})
        ) == ["ok", "ok"]
    finally:
        await client.aclose()
    assert calls.count("/") == 1
    assert calls.count("/v1/test/getcrumb") == 1


def test_tabular_conversion_failure_is_a_library_error() -> None:
    """An integer outside Polars bounds cannot leak the internal shape exception."""
    payload = {"finance": {"result": [{"records": [{"value": 10**100}]}]}}
    with pytest.raises(YahooApiError, match="malformed-response"):
        api._tabular_frame(payload, "screener")  # pyright: ignore[reportPrivateUsage]


def test_frame_is_only_shallowly_frozen() -> None:
    """The documented wrapper semantics preserve the existing mutable frame."""
    payload = {"finance": {"result": [{"records": [{"value": 1}]}]}}
    frame = api._tabular_frame(  # pyright: ignore[reportPrivateUsage]
        payload,
        "screener",
    )
    frame.to_polars().replace_column(0, pl.Series("value", [2]))
    assert frame.to_dicts() == [{"value": 2}]


@pytest.mark.asyncio
async def test_crumb_free_start_does_not_fetch_crumb() -> None:
    """Cookie initialization remains, while crumb-free calls skip getcrumb."""
    calls: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/":
            return httpx.Response(
                200, headers={"set-cookie": "A3=synthetic; Domain=.yahoo.com; Path=/"}
            )
        assert "crumb" not in request.url.params
        return httpx.Response(200, text="ok")

    client = YahooClient(transport=httpx.MockTransport(handle), use_session_cache=False)
    try:
        assert await client.get("/test", {}, use_crumb=False) == "ok"
    finally:
        await client.aclose()
    assert calls == ["/", "/test"]


@pytest.mark.parametrize("expires_in", [-1, 3600])
@pytest.mark.asyncio
async def test_cached_session_expiry_and_write_frequency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, expires_in: int
) -> None:
    """Fresh caches avoid both initialization and writes; expired ones refresh once."""
    path = tmp_path / "session.json"
    cookies = httpx.Cookies()
    cookies.set("A3", "synthetic", domain=".yahoo.com")
    save_session_cache(path, cookies, "synthetic", time.time() + expires_in)
    writes: list[Path] = []
    calls: list[str] = []

    def record_save(
        destination: Path, cookies: httpx.Cookies, crumb: str, expiry: float
    ) -> None:
        del cookies, crumb, expiry
        writes.append(destination)

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/":
            return httpx.Response(
                200, headers={"set-cookie": "A3=synthetic; Domain=.yahoo.com; Path=/"}
            )
        return httpx.Response(200, text="ok")

    monkeypatch.setattr("yoghurt.client.save_session_cache", record_save)
    client = YahooClient(transport=httpx.MockTransport(handle), session_cache_path=path)
    try:
        await client.get("/test", {})
        await client.get("/test", {})
    finally:
        await client.aclose()
    if expires_in < 0:
        assert calls == ["/", "/v1/test/getcrumb", "/test", "/test"]
        assert writes == [path]
    else:
        assert calls == ["/test", "/test"]
        assert writes == []


@pytest.mark.asyncio
async def test_credentials_absent_from_logs_and_full_traceback(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Upstream URL and protocol logging cannot disclose synthetic credentials."""
    cache = tmp_path / "session.json"
    cookies = httpx.Cookies()
    cookies.set("A3", "synthetic-cookie", domain=".yahoo.com")
    save_session_cache(cache, cookies, "synthetic-crumb", time.time() + 3600)
    original = cache.read_bytes()

    def handle(request: httpx.Request) -> httpx.Response:
        del request
        logging.getLogger("httpcore2.http11").debug("headers synthetic-cookie")
        return httpx.Response(
            403, json={"finance": {"error": {"description": "Not entitled"}}}
        )

    client = YahooClient(
        transport=httpx.MockTransport(handle), session_cache_path=cache
    )
    caplog.set_level(logging.DEBUG)
    try:
        with pytest.raises(YahooRequestError) as error:
            await client.get("/test", {})
    finally:
        await client.aclose()
    text = caplog.text + "".join(traceback.format_exception(error.value))
    assert "synthetic-crumb" not in text
    assert "synthetic-cookie" not in text
    assert "/test" in text
    assert "403" in text
    assert cache.read_bytes() == original
