"""Tests for the background-loop sync bridge."""

import asyncio

import pytest

from yoghurt._bridge import run  # pyright: ignore[reportPrivateUsage]

_DOUBLED = 42


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
