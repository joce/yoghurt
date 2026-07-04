"""Run library coroutines on a dedicated background event loop.

The public sync API is a thin facade over async core functions. Those
coroutines run on one lazily-started daemon thread, which keeps the sync
surface usable inside environments that already run an event loop
(notebooks, agent runtimes) where a naive asyncio.run() would raise.
"""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any

_T = TypeVar("_T")

_lock = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop  # noqa: PLW0603 - module-level singleton by design
    with _lock:
        if _loop is not None and not _loop.is_closed():
            return _loop
        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target=loop.run_forever, name="yoghurt-bridge", daemon=True
        )
        thread.start()
        _loop = loop
    return loop


def run(coro: Coroutine[Any, Any, _T]) -> _T:
    """Execute ``coro`` on the bridge loop and return its result.

    Returns:
        _T: Whatever the coroutine returns.
    """

    return asyncio.run_coroutine_threadsafe(coro, _ensure_loop()).result()
