"""Bounded process-local request coalescing for cache-aside misses."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


class SingleFlight:
    def __init__(self, maximum_entries: int = 256) -> None:
        self.maximum_entries = maximum_entries
        self._lock = asyncio.Lock()
        self._flights: dict[str, asyncio.Task[Any]] = {}
        self.peak = 0

    @property
    def current(self) -> int:
        return len(self._flights)

    async def run(self, identity: str, loader: Callable[[], Awaitable[Any]]) -> tuple[Any, str]:
        """Share a loader task without letting caller cancellation cancel it."""
        async with self._lock:
            task = self._flights.get(identity)
            if task is not None:
                role = "waiter"
            elif len(self._flights) >= self.maximum_entries:
                task = None
                role = "capacity_bypass"
            else:
                task = asyncio.create_task(loader())
                self._flights[identity] = task
                self.peak = max(self.peak, len(self._flights))
                role = "leader"
                task.add_done_callback(lambda _: self._flights.pop(identity, None))
        if task is None:
            return await loader(), role
        return await asyncio.shield(task), role


DEFAULT_SINGLEFLIGHT = SingleFlight()
