"""Opt-in ReadingPass-only admission and cancellation-safe session ownership.

No Motor framework monkeypatch. This adapter supports one client/loop, serial
explicit transactions and the inventoried ReadingPass collection/cursor methods.
The original Motor session __aexit__ still runs on the loop; it is not offloaded.
Cancellation returns to the caller while an owned cleanup waits for the original
Motor future before session exit and permit release. ``drain(timeout=...)`` must
be used before closing the raw client. A timeout never frees live permits.
"""
from __future__ import annotations

import asyncio
import contextvars
import math


class ScopedAdmission:
    def __init__(self, client, capacity=8, *, _inert_test_client=False):
        if type(capacity) is not int or capacity != 8:
            raise ValueError("Only reviewed capacity 8 is supported")
        import motor
        import pymongo
        from motor.motor_asyncio import AsyncIOMotorClient

        if motor.version != "3.3.1" or pymongo.version != "4.5.0":
            raise RuntimeError("Unqualified Motor/PyMongo versions")
        if not _inert_test_client:
            if not isinstance(client, AsyncIOMotorClient):
                raise TypeError("An explicitly owned Motor client is required")
            if client.options.pool_options.max_pool_size != capacity:
                raise RuntimeError("Client pool capacity does not match admission")
        self.raw = client
        self.capacity = capacity
        self.loop = None
        self.gate = None
        self.closed = False
        self.sessions = set()
        self.background = set()
        self.errors = []
        self.permits = set()
        self.owner = contextvars.ContextVar("reading_pass_scoped_session", default=None)
        self.activity = None
        self.drain_task = None

    def _loop(self):
        loop = asyncio.get_running_loop()
        if hasattr(self.raw, "get_io_loop") and self.raw.get_io_loop() is not loop:
            raise RuntimeError("Raw client belongs to a different loop")
        if self.loop is None:
            self.loop = loop
            self.gate = asyncio.Semaphore(self.capacity)
            self.activity = asyncio.Event()
        if self.loop is not loop:
            raise RuntimeError("Single owned loop required")
        return loop

    async def _acquire(self):
        self._loop()
        if self.closed:
            raise RuntimeError("Admission is draining")
        await self.gate.acquire()
        if self.closed:
            self.gate.release()
            raise RuntimeError("Admission is draining")
        permit = object()
        self.permits.add(permit)
        return permit

    def _release(self, permit):
        if permit not in self.permits:
            raise RuntimeError("Permit already released")
        self.permits.remove(permit)
        self.gate.release()
        self.activity.set()

    def _background(self, coroutine):
        task = self._loop().create_task(coroutine)
        self.background.add(task)

        def done(future):
            self.background.discard(future)
            if not future.cancelled():
                error = future.exception()
                if error is not None:
                    self.errors.append(error)
            self.activity.set()

        task.add_done_callback(done)
        return task

    async def start_session(self, **kwargs):
        if self.owner.get() is not None:
            raise RuntimeError("Nested/inherited session unsupported")
        permit = await self._acquire()
        future = None
        try:
            # ensure_future returns the exact Motor Future when it is a Future.
            future = asyncio.ensure_future(self.raw.start_session(**kwargs))
            raw_session = await asyncio.shield(future)
            session = ScopedSession(self, raw_session, permit)
            self.sessions.add(session)
            return session
        except asyncio.CancelledError:
            if future is None:
                self._release(permit)
            else:
                async def finish_start():
                    try:
                        raw_session = await asyncio.shield(future)
                        await raw_session.__aexit__(None, None, None)
                    finally:
                        self._release(permit)
                self._background(finish_start())
            raise
        except BaseException:
            self._release(permit)
            raise

    async def call(self, obj, method, *args, **kwargs):
        self._loop()
        session = kwargs.get("session")
        owner = self.owner.get()
        if isinstance(session, ScopedSession):
            if session.admission is not self:
                raise RuntimeError("Foreign session")
            owner = session
            kwargs = {**kwargs, "session": session.raw}
        if owner is not None:
            if (owner.admission is not self or owner.task is not asyncio.current_task()
                    or owner.closing):
                raise RuntimeError("Child/concurrent/closed session unsupported")
            if any(not future.done() for future in owner.pending):
                raise RuntimeError("Parallel session operations unsupported")
            return await owner._call(obj, method, *args, **kwargs)

        permit = await self._acquire()
        future = None
        try:
            future = asyncio.ensure_future(getattr(obj, method)(*args, **kwargs))

            def done(result):
                self._release(permit)
                if not result.cancelled():
                    result.exception()  # Retain original exception for awaiters.

            future.add_done_callback(done)
            return await asyncio.shield(future)
        finally:
            if future is None:
                self._release(permit)

    async def _drain(self):
        # A caller cancellation or timeout of drain must not cancel cleanup.
        while self.permits or self.background:
            self.activity.clear()
            if self.permits or self.background:
                await self.activity.wait()
        if self.errors:
            raise RuntimeError("Deferred admission cleanup failed") from self.errors[0]

    async def drain(self, *, timeout):
        self._loop()
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("A positive bounded drain timeout is required")
        self.closed = True
        if self.drain_task is None:
            self.drain_task = self.loop.create_task(self._drain())
            # Observe failures even when the original drain caller times out.
            self.drain_task.add_done_callback(
                lambda task: None if task.cancelled() else task.exception())
        return await asyncio.wait_for(asyncio.shield(self.drain_task), timeout)

    def snapshot(self):
        """Nonsecret lifecycle counts; no arguments, results or error messages."""
        return {"capacity": self.capacity, "held_permits": len(self.permits),
                "owned_sessions": len(self.sessions),
                "cleanup_tasks": len(self.background),
                "deferred_errors": len(self.errors), "draining": self.closed}

    def database(self, database):
        if database.client is not self.raw:
            raise RuntimeError("Foreign database/client binding")
        return ScopedDatabase(self, database)


class ScopedSession:
    def __init__(self, admission, raw, permit):
        self.admission = admission
        self.raw = raw
        self.permit = permit
        self.task = None
        self.token = None
        self.pending = set()
        self.closing = False
        self.cleanup = None

    async def __aenter__(self):
        if self.task is not None or self.admission.owner.get() is not None:
            raise RuntimeError("Session already entered/nested")
        self.task = asyncio.current_task()
        try:
            await self.raw.__aenter__()
        except BaseException as error:
            self._begin_cleanup(type(error), error, error.__traceback__)
            if not isinstance(error, asyncio.CancelledError):
                await asyncio.shield(self.cleanup)
            raise
        self.token = self.admission.owner.set(self)
        return self

    @property
    def in_transaction(self):
        return self.raw.in_transaction

    def start_transaction(self, *args, **kwargs):
        if self.task is not asyncio.current_task() or self.closing:
            raise RuntimeError("Session owner required")
        return self.raw.start_transaction(*args, **kwargs)

    async def _call(self, obj, method, *args, **kwargs):
        future = asyncio.ensure_future(getattr(obj, method)(*args, **kwargs))
        self.pending.add(future)

        def done(result):
            self.pending.discard(result)
            if not result.cancelled():
                result.exception()
            self.admission.activity.set()

        future.add_done_callback(done)
        return await asyncio.shield(future)

    def _assert_current_owner(self):
        if (self.task is not asyncio.current_task()
                or self.admission.owner.get() is not self
                or self.closing or self.token is None
                or self not in self.admission.sessions
                or self.permit not in self.admission.permits):
            raise RuntimeError("This live session must own the current task and permit")

    async def commit_transaction(self):
        self._assert_current_owner()
        return await self.admission.call(self.raw, "commit_transaction")

    async def abort_transaction(self):
        self._assert_current_owner()
        return await self.admission.call(self.raw, "abort_transaction")

    def _begin_cleanup(self, typ, value, traceback):
        if self.closing:
            raise RuntimeError("Session cleanup already started")
        self.closing = True
        if self.token is not None:
            self.admission.owner.reset(self.token)
            self.token = None

        async def cleanup():
            try:
                while self.pending:
                    await asyncio.gather(*(asyncio.shield(future)
                                           for future in tuple(self.pending)),
                                         return_exceptions=True)
                # Preserve the exact original Motor context-exit contract.
                # In the pinned Motor this contains synchronous delegate exit.
                return await self.raw.__aexit__(typ, value, traceback)
            finally:
                self.admission.sessions.discard(self)
                self.admission._release(self.permit)

        self.cleanup = self.admission._background(cleanup())

    async def __aexit__(self, typ, value, traceback):
        if self.task is not asyncio.current_task():
            raise RuntimeError("Session exit owner required")
        self._begin_cleanup(typ, value, traceback)
        if typ is not None and issubclass(typ, asyncio.CancelledError):
            return False
        return await asyncio.shield(self.cleanup)


class ScopedDatabase:
    def __init__(self, admission, raw):
        self.admission, self.raw = admission, raw

    @property
    def client(self):
        return self.admission

    @property
    def name(self):
        return self.raw.name

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return ScopedCollection(self.admission, getattr(self.raw, name))

    def __getitem__(self, name):
        return ScopedCollection(self.admission, self.raw[name])


class ScopedCollection:
    ASYNC = frozenset({"find_one", "find_one_and_update", "update_one", "insert_one",
                       "delete_one", "count_documents", "index_information", "create_index"})

    def __init__(self, admission, raw):
        self.admission, self.raw = admission, raw

    def __getattr__(self, name):
        if name not in self.ASYNC:
            raise AttributeError("Unsupported scoped method: " + name)

        async def call(*args, **kwargs):
            return await self.admission.call(self.raw, name, *args, **kwargs)
        return call

    def find(self, *args, **kwargs):
        session = kwargs.get("session")
        if isinstance(session, ScopedSession):
            session = kwargs["session"]
            if session.admission is not self.admission:
                raise RuntimeError("Foreign cursor session")
            kwargs = {**kwargs, "session": session.raw}
        return ScopedCursor(self.admission, self.raw.find(*args, **kwargs),
                            session if isinstance(session, ScopedSession) else None)


class ScopedCursor:
    def __init__(self, admission, raw, session=None):
        self.admission, self.raw, self.session = admission, raw, session

    def sort(self, *args, **kwargs):
        self.raw = self.raw.sort(*args, **kwargs)
        return self

    def limit(self, *args, **kwargs):
        self.raw = self.raw.limit(*args, **kwargs)
        return self

    async def to_list(self, *args, **kwargs):
        if self.session is not None and self.admission.owner.get() is not self.session:
            raise RuntimeError("Cursor must remain in its owned session context")
        return await self.admission.call(self.raw, "to_list", *args, **kwargs)
