"""Deterministic ownership of a blocking upstream streaming body.

Cleanup has its own bounded worker limiter so saturated body-read workers do not
prevent close from starting. It is shielded from response cancellation, not a
hard deadline for arbitrary upstream close/socket implementations.
"""
import asyncio
import logging
import threading
from weakref import WeakKeyDictionary

import anyio
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)
_limiters = WeakKeyDictionary()
_limiter_lock = threading.Lock()


def _cleanup_limiter():
    loop = asyncio.get_running_loop()
    with _limiter_lock:
        if loop not in _limiters:
            _limiters[loop] = anyio.CapacityLimiter(4)
        return _limiters[loop]


class _BodyOwner:
    def __init__(self, body):
        self.body = body
        self._lock = threading.Lock()
        self._claimed = False
        self._done = threading.Event()
        self.error_type = None

    def read(self, size):
        return self.body.read(size)

    def close(self):
        with self._lock:
            claimed = self._claimed
            self._claimed = True
        if claimed:
            # Wait only on the cleanup/read worker, never on the event loop.
            self._done.wait()
            return
        try:
            close = getattr(self.body, 'close', None)
            if not callable(close):
                self.error_type = 'MissingCloseMethod'
            else:
                close()
        except Exception as exc:
            # Do not replace an upstream read/send exception with cleanup noise,
            # or report an attempted close as a verified successful close.
            self.error_type = type(exc).__name__
        finally:
            self._done.set()


class OwnedStreamingResponse(StreamingResponse):
    def __init__(self, content, *, owner, **kwargs):
        super().__init__(content, **kwargs)
        self._body_owner = owner
        self._close_error_logged = False

    async def _close_upstream(self):
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(self._body_owner.close, limiter=_cleanup_limiter())
        if self._body_owner.error_type and not self._close_error_logged:
            self._close_error_logged = True
            logger.warning('Upstream body close did not verify: %s', self._body_owner.error_type)

    async def __call__(self, scope, receive, send):
        async def owned_receive():
            try:
                message = await receive()
            except BaseException:
                await self._close_upstream()
                raise
            if message.get('type') == 'http.disconnect':
                # Close before StreamingResponse waits for its shielded read.
                await self._close_upstream()
            return message

        async def owned_send(message):
            try:
                await send(message)
            except BaseException:
                await self._close_upstream()
                raise

        try:
            return await super().__call__(scope, owned_receive, owned_send)
        finally:
            await self._close_upstream()


async def owned_streaming_response(body, iterator_factory, **kwargs):
    owner = _BodyOwner(body)
    try:
        return OwnedStreamingResponse(iterator_factory(owner), owner=owner, **kwargs)
    except BaseException:
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(owner.close, limiter=_cleanup_limiter())
        raise
