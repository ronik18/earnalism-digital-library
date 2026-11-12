"""Synthetic storage only: exercise real sharing, cancellation and admission."""
import asyncio
import threading

import pytest

from backend.audiobook_preview import PreviewClipCache, PreviewCapacityError


def blocked_producer(loop, started, release, calls):
    def produce():
        calls.append(1)
        loop.call_soon_threadsafe(started.set)
        if not release.wait(2):
            raise AssertionError('Fixture producer was not released')
        return b'clipped', 100
    return produce


def test_overlapping_range_and_head_reads_share_one_cold_producer():
    async def scenario():
        cache = PreviewClipCache()
        started, release, calls = asyncio.Event(), threading.Event(), []
        producer = blocked_producer(asyncio.get_running_loop(), started, release, calls)
        tasks = [asyncio.create_task(cache.get('same-immutable-clip', producer)) for _ in range(12)]
        try:
            await asyncio.wait_for(started.wait(), 1)
            assert len(calls) == len(cache._jobs) == 1
        finally:
            release.set()
        assert await asyncio.gather(*tasks) == [(b'clipped', 100)] * 12
        assert not cache._jobs and cache._waiters == 0
    asyncio.run(scenario())


def test_cached_range_is_served_while_next_clip_is_being_prepared():
    async def scenario():
        cache = PreviewClipCache()
        await cache.get('current', lambda: (b'current', 100))
        started, release, calls = asyncio.Event(), threading.Event(), []
        next_clip = asyncio.create_task(cache.get('next', blocked_producer(asyncio.get_running_loop(), started, release, calls)))
        try:
            await asyncio.wait_for(started.wait(), 1)
            def forbidden():
                raise AssertionError('Cached clip must not refetch storage')
            assert await asyncio.wait_for(cache.get('current', forbidden), .1) == (b'current', 100)
        finally:
            release.set()
        await next_clip
    asyncio.run(scenario())


def test_cancelling_http_waiter_does_not_release_or_restart_producer():
    async def scenario():
        cache = PreviewClipCache()
        started, release, calls = asyncio.Event(), threading.Event(), []
        producer = blocked_producer(asyncio.get_running_loop(), started, release, calls)
        first = asyncio.create_task(cache.get('clip', producer))
        await asyncio.wait_for(started.wait(), 1)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert len(cache._jobs) == len(calls) == 1
        second = asyncio.create_task(cache.get('clip', producer))
        release.set()
        assert await second == (b'clipped', 100)
        assert len(calls) == 1
    asyncio.run(scenario())


def test_pending_jobs_and_waiters_are_finite_and_storage_stays_serial():
    async def scenario():
        cache = PreviewClipCache(max_jobs=2, max_waiters=2)
        started, release, calls = asyncio.Event(), threading.Event(), []
        first = asyncio.create_task(cache.get('first', blocked_producer(asyncio.get_running_loop(), started, release, calls)))
        await asyncio.wait_for(started.wait(), 1)
        second_calls = []
        def second_producer():
            second_calls.append(1)
            assert release.is_set(), 'Physical producers must not overlap'
            return b'second', 100
        second = asyncio.create_task(cache.get('second', second_producer))
        await asyncio.sleep(0)
        try:
            with pytest.raises(PreviewCapacityError):
                await cache.get('third', lambda: (b'forbidden', 100))
            assert len(cache._jobs) == 2 and not second_calls
        finally:
            release.set()
        await asyncio.gather(first, second)
        assert second_calls == [1]
        assert cache._waiters == 0 and not cache._jobs
    asyncio.run(scenario())


def test_timeout_keeps_shared_job_alive_and_cache_is_still_two_entries():
    async def scenario():
        cache = PreviewClipCache(wait_seconds=.02)
        started, release, calls = asyncio.Event(), threading.Event(), []
        producer = blocked_producer(asyncio.get_running_loop(), started, release, calls)
        try:
            with pytest.raises(PreviewCapacityError):
                await cache.get('clip', producer)
            assert len(cache._jobs) == 1 and calls == [1]
            task = cache._jobs['clip']
        finally:
            release.set()
        await task
        await cache.get('clip', lambda: (_ for _ in ()).throw(AssertionError('No refetch')))
        await cache.get('next', lambda: (b'next', 100))
        await cache.get('third', lambda: (b'third', 100))
        assert len(cache._cache) == 2 and 'clip' not in cache._cache
    asyncio.run(scenario())


def test_failed_storage_is_not_cached_or_automatically_retried():
    async def scenario():
        cache, calls = PreviewClipCache(), []
        def failing():
            calls.append(1)
            raise ValueError('Synthetic immutable storage failure')
        results = await asyncio.gather(cache.get('bad', failing), cache.get('bad', failing), return_exceptions=True)
        assert all(isinstance(r, ValueError) for r in results)
        assert calls == [1] and not cache._cache and not cache._jobs and cache._waiters == 0
        assert await cache.get('different', lambda: (b'ok', 100)) == (b'ok', 100)
    asyncio.run(scenario())


def test_distinct_job_limit_does_not_refuse_a_join_to_an_existing_clip():
    async def scenario():
        cache = PreviewClipCache(max_jobs=1, max_waiters=8)
        started, release, calls = asyncio.Event(), threading.Event(), []
        producer = blocked_producer(asyncio.get_running_loop(), started, release, calls)
        first = asyncio.create_task(cache.get('same', producer))
        await asyncio.wait_for(started.wait(), 1)
        try:
            with pytest.raises(PreviewCapacityError):
                await cache.get('different', lambda: (b'not-admitted', 100))
            joined = asyncio.create_task(cache.get('same', producer))
        finally:
            release.set()
        assert await asyncio.gather(first, joined) == [(b'clipped', 100)] * 2
        assert calls == [1]
    asyncio.run(scenario())
