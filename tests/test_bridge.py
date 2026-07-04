"""Tests for the background-loop sync bridge."""

import asyncio
import concurrent.futures
import time

import pytest

from yoghurt._bridge import run

_DOUBLED = 42
_SHORT_TIMEOUT_SECONDS = 0.1
_LONG_SLEEP_SECONDS = 5.0
_WELL_UNDER_A_SECOND = 1.0


async def _double(value: int) -> int:
    await asyncio.sleep(0)
    return value * 2


def test_run_executes_coroutine_from_sync_context() -> None:
    """Plain sync callers get the coroutine result."""
    assert run(_double(21)) == _DOUBLED


async def test_run_works_inside_a_running_event_loop() -> None:  # noqa: RUF029
    """The Jupyter case: a loop is already running; asyncio.run would raise."""
    assert run(_double(21)) == _DOUBLED


def test_run_propagates_exceptions() -> None:
    """Exceptions cross the thread boundary intact."""

    async def _boom() -> None:  # noqa: RUF029
        msg = "boom"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="boom"):
        run(_boom())


def test_run_with_timeout_returns_fast_result() -> None:
    """A bounded wait does not disturb a coroutine that finishes in time."""
    assert run(_double(21), timeout=_SHORT_TIMEOUT_SECONDS) == _DOUBLED


def test_run_with_timeout_raises_instead_of_hanging() -> None:
    """A slow coroutine raises the timeout error promptly; the wait is bounded."""
    started = time.monotonic()
    with pytest.raises(concurrent.futures.TimeoutError):
        run(asyncio.sleep(_LONG_SLEEP_SECONDS), timeout=_SHORT_TIMEOUT_SECONDS)
    assert time.monotonic() - started < _WELL_UNDER_A_SECOND
