"""Real response lifecycle with synthetic blocking bodies; no network/provider."""
import asyncio
import logging
import threading
import time

import anyio
import pytest

from backend.tests.test_audio_stream_chunking import iterator
from backend.utils.owned_stream_response import _BodyOwner, owned_streaming_response


class Body:
    def __init__(self, chunks=4):
        self.remaining=chunks;self.closed=False;self.close_count=0;self.requests=[]
    def read(self,size):
        self.requests.append(size)
        if self.closed or not self.remaining:return b''
        self.remaining-=1
        return b'x'*size
    def close(self):
        self.close_count+=1;self.closed=True


def flatten(error):
    children=getattr(error,'exceptions',None)
    return [leaf for child in children for leaf in flatten(child)] if children else [error]


@pytest.mark.parametrize('case',['normal','disconnect','send-error','receive-error','read-error','cancel','range-disconnect'])
def test_response_closes_exactly_once_without_gc(case):
    async def scenario():
        body=Body();first=asyncio.Event();messages=[]
        if case=='read-error':
            def broken(size):raise OSError('original synthetic read failure')
            body.read=broken
        async def receive():
            if case=='receive-error':raise OSError('original synthetic receive failure')
            await first.wait()
            if 'disconnect' in case:return {'type':'http.disconnect'}
            await asyncio.Event().wait()
        async def send(message):
            messages.append(message)
            if message['type']=='http.response.body' and message.get('body'):
                first.set()
                if case=='send-error':raise OSError('original synthetic send failure')
                if case=='cancel':
                    asyncio.current_task().cancel();await asyncio.sleep(0)
                if 'disconnect' in case:await asyncio.sleep(.02)
        response=await owned_streaming_response(body,iterator(),status_code=206 if case=='range-disconnect' else 200,
                    headers={'Cache-Control':'private, no-store','Accept-Ranges':'bytes'})
        error=None
        try:await asyncio.wait_for(response({'type':'http','asgi':{'spec_version':'2.3'}},receive,send),2)
        except BaseException as exc:error=exc
        # Retain response and iterator references: no del/gc as cleanup evidence.
        assert body.closed and body.close_count==1
        assert response.headers['cache-control']=='private, no-store'
        if case=='normal':
            assert error is None
            assert sum(len(m.get('body',b'')) for m in messages)==4*65536
        elif case.endswith('error'):
            assert error is not None and any(isinstance(e,OSError) for e in flatten(error))
        elif case=='cancel':
            # Starlette's task group may consume child cancellation. Cleanup
            # and terminating the body, rather than propagation, are the contract.
            assert sum(len(m.get('body',b'')) for m in messages)==65536
        else:assert error is None
        assert all(n==65536 for n in body.requests)
    asyncio.run(scenario())


def test_disconnect_closes_before_shielded_blocking_read_finishes():
    async def scenario():
        entered=threading.Event();released=threading.Event()
        class Blocked(Body):
            def read(self,size):
                self.requests.append(size);entered.set()
                if not released.wait(1):raise TimeoutError('fixture release ceiling')
                return b''
            def close(self):super().close();released.set()
        body=Blocked();response=await owned_streaming_response(body,iterator())
        async def receive():
            for _ in range(100):
                if entered.is_set():return {'type':'http.disconnect'}
                await asyncio.sleep(.002)
            raise TimeoutError('fixture read did not begin')
        async def send(_):pass
        started=time.monotonic()
        try:await asyncio.wait_for(response({'type':'http','asgi':{'spec_version':'2.3'}},receive,send),2)
        finally:released.set()
        assert body.closed and body.close_count==1
        assert time.monotonic()-started<.5
    asyncio.run(scenario())


def test_slow_close_does_not_block_loop_and_concurrent_closers_wait():
    async def scenario():
        entered=threading.Event();released=threading.Event()
        class Slow(Body):
            def close(self):
                self.close_count+=1;entered.set()
                if not released.wait(1):raise TimeoutError('fixture close ceiling')
                self.closed=True
        body=Slow();owner=_BodyOwner(body)
        first=asyncio.create_task(asyncio.to_thread(owner.close))
        try:
            for _ in range(100):
                if entered.is_set():break
                await asyncio.sleep(.002)
            assert entered.is_set()
            second=asyncio.create_task(asyncio.to_thread(owner.close))
            begun=time.monotonic();await asyncio.sleep(.02)
            assert time.monotonic()-begun<.3
            assert not first.done() and not second.done() and not body.closed
            assert body.close_count==1
        finally:released.set()
        await asyncio.wait_for(asyncio.gather(first,second),2)
        assert body.closed and body.close_count==1
    asyncio.run(scenario())


def test_cleanup_has_capacity_when_default_read_pool_is_saturated():
    async def scenario():
        default=anyio.to_thread.current_default_thread_limiter();old=default.total_tokens
        entered=threading.Event();release=threading.Event();default.total_tokens=1
        def blocked():entered.set();release.wait(2)
        blocker=asyncio.create_task(anyio.to_thread.run_sync(blocked))
        try:
            for _ in range(100):
                if entered.is_set():break
                await asyncio.sleep(.002)
            assert entered.is_set()
            body=Body();response=await owned_streaming_response(body,iterator())
            started=time.monotonic();await asyncio.wait_for(response._close_upstream(),1)
            assert body.closed and body.close_count==1
            assert not release.is_set() and not blocker.done()
            assert time.monotonic()-started<.5
        finally:
            release.set();await blocker;default.total_tokens=old
    asyncio.run(scenario())


def test_close_failure_is_logged_without_masking_read_failure(caplog):
    async def scenario():
        class Broken(Body):
            def read(self,size):raise OSError('original synthetic read failure')
            def close(self):self.close_count+=1;raise ValueError('private fixture detail must not be logged')
        body=Broken();response=await owned_streaming_response(body,iterator())
        async def receive():await asyncio.Event().wait()
        async def send(_):pass
        error=None
        try:await response({'type':'http','asgi':{'spec_version':'2.3'}},receive,send)
        except BaseException as exc:error=exc
        assert error is not None
        assert any(isinstance(e,OSError) and str(e)=='original synthetic read failure' for e in flatten(error))
        assert body.close_count==1 and not body.closed
        assert response._body_owner.error_type=='ValueError'
    with caplog.at_level(logging.WARNING):asyncio.run(scenario())
    assert 'ValueError' in caplog.text
    assert 'private fixture detail' not in caplog.text
