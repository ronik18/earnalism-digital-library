"""Bounded streaming-body iterators with cancellation-safe cleanup telemetry."""

from __future__ import annotations

import asyncio
from collections import Counter
from threading import Lock
from typing import Any, AsyncIterator

CHUNK_SIZE = 1024 * 1024


class _StreamDiagnostics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()

    def record(self, name: str) -> None:
        with self._lock:
            self._counters[name] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            opened = self._counters["opened"]
            closed = self._counters["closed"]
            return {
                "active_streams": max(opened - closed, 0),
                "opened": opened,
                "closed": closed,
                "cancelled": self._counters["cancelled"],
                "read_errors": self._counters["read_errors"],
                "close_errors": self._counters["close_errors"],
                "request_results": {
                    key.removeprefix("request:"): value
                    for key, value in sorted(self._counters.items())
                    if key.startswith("request:")
                },
                "storage_operations": {
                    key.removeprefix("storage:"): value
                    for key, value in sorted(self._counters.items())
                    if key.startswith("storage:")
                },
                "consistency": {
                    key.removeprefix("consistency:"): value
                    for key, value in sorted(self._counters.items())
                    if key.startswith("consistency:")
                },
            }


_diagnostics = _StreamDiagnostics()


def streaming_metrics_snapshot() -> dict[str, Any]:
    """Return aggregate-only diagnostics; no URLs, keys, users, or secrets."""
    return _diagnostics.snapshot()


def record_request(method: str, range_class: str, status_code: int) -> None:
    """Record a bounded request tuple without resource or user labels."""
    safe_method = method if method in {"GET", "HEAD"} else "OTHER"
    safe_range = range_class if range_class in {
        "full", "fixed", "suffix", "open_ended", "conditional", "invalid"
    } else "other"
    status_class = str(status_code) if status_code in {200, 206, 304, 401, 403, 404, 416} else "5xx"
    _diagnostics.record(f"request:{safe_method}:{safe_range}:{status_class}")


def record_storage(operation: str, result: str) -> None:
    """Record a bounded storage operation/result pair."""
    safe_operation = operation if operation in {"head", "get"} else "other"
    safe_result = result if result in {"ok", "error"} else "other"
    _diagnostics.record(f"storage:{safe_operation}:{safe_result}")


def record_consistency(result: str) -> None:
    safe_result = result if result in {"retry", "failure"} else "other"
    _diagnostics.record(f"consistency:{safe_result}")


def streaming_body_iterator(body):
    try:
        while True:
            chunk = body.read(CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
    finally:
        close = getattr(body, "close", None)
        if callable(close):
            close()


class AsyncStreamingBody(AsyncIterator[bytes]):
    """One B2 body with idempotent async cleanup, including pre-first-byte exit."""

    def __init__(self, body: Any) -> None:
        self._body = body
        self._closed = False
        self._close_lock = asyncio.Lock()
        _diagnostics.record("opened")

    def __aiter__(self) -> "AsyncStreamingBody":
        return self

    async def __anext__(self) -> bytes:
        if self._closed:
            raise StopAsyncIteration
        try:
            chunk = await asyncio.to_thread(self._body.read, CHUNK_SIZE)
        except asyncio.CancelledError:
            _diagnostics.record("cancelled")
            await self._close()
            raise
        except BaseException:
            _diagnostics.record("read_errors")
            await self._close()
            raise
        if not chunk:
            await self._close()
            raise StopAsyncIteration
        return chunk

    async def aclose(self) -> None:
        if not self._closed:
            _diagnostics.record("cancelled")
        await self._close()

    async def _close(self) -> None:
        async with self._close_lock:
            if self._closed:
                return
            self._closed = True
            try:
                close = getattr(self._body, "close", None)
                if callable(close):
                    await asyncio.to_thread(close)
            except BaseException:
                _diagnostics.record("close_errors")
            finally:
                _diagnostics.record("closed")


def async_streaming_body_iterator(body: Any) -> AsyncStreamingBody:
    """Return a cancellation-safe async body iterator without prefetching."""
    return AsyncStreamingBody(body)
