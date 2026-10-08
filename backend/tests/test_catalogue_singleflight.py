"""Isolated Redis ownership tests; no production or application DB access."""
import asyncio
import json
import os
import uuid

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from backend.catalogue_singleflight import cached_catalogue, RELEASE


def run(coroutine):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


def test_outage_uses_authoritative_uncached_build():
    class Outage:
        async def get(self, key):
            raise ConnectionError('isolated failure')
    async def exercise():
        async def build():
            return {'approved': False}
        assert await cached_catalogue(Outage(), 'g', str, build, json.dumps, json.loads, 60) == {'approved': False}
    run(exercise())


@pytest.fixture
def redis_fixture():
    if os.environ.get('PERF_REDIS_SINGLEFLIGHT_TEST') != '1':
        pytest.skip('Requires explicitly enabled disposable Redis on loopback 27019')
    return 'performance-singleflight:' + uuid.uuid4().hex


@pytest.mark.parametrize('concurrency', [2, 4, 8, 16, 32])
def test_one_rebuild_per_cold_generation(redis_fixture, concurrency):
    async def exercise():
        client = Redis(host='127.0.0.1', port=27019, db=15)
        prefix = redis_fixture
        count = 0
        async def build():
            nonlocal count
            count += 1
            await asyncio.sleep(.025)
            return {'generation': count}
        try:
            for generation in [0, 1]:
                await client.set(prefix + ':generation', generation)
                values = await asyncio.gather(*(cached_catalogue(client, prefix + ':generation',
                    lambda g: prefix + ':' + str(g), build, json.dumps, json.loads, 60) for _ in range(concurrency)))
                assert count == generation + 1
                assert all(value == {'generation': generation + 1} for value in values)
                assert not await client.exists(prefix + ':' + str(generation) + ':fill-lock')
        finally:
            keys = [key async for key in client.scan_iter(prefix + '*')]
            if keys:
                await client.delete(*keys)
            await client.aclose()
    run(exercise())


def test_generation_change_discards_old_build(redis_fixture):
    async def exercise():
        client = Redis(host='127.0.0.1', port=27019, db=15)
        prefix = redis_fixture
        count = 0
        async def build():
            nonlocal count
            count += 1
            if count == 1:
                await client.set(prefix + ':generation', 1)
            return {'version': count}
        try:
            result = await cached_catalogue(client, prefix + ':generation', lambda g: prefix + ':' + str(g),
                build, json.dumps, json.loads, 60)
            assert result == {'version': 2}
            assert not await client.exists(prefix + ':0')
            assert json.loads(await client.get(prefix + ':1')) == result
        finally:
            keys = [key async for key in client.scan_iter(prefix + '*')]
            if keys:
                await client.delete(*keys)
            await client.aclose()
    run(exercise())


def test_owner_safe_release_exception_and_expiry_recovery(redis_fixture):
    async def exercise():
        client = Redis(host='127.0.0.1', port=27019, db=15)
        prefix = redis_fixture
        lock = prefix + ':0:fill-lock'
        async def broken():
            raise ValueError('builder failure')
        async def build():
            return {'valid': True}
        async def fill(builder):
            return await cached_catalogue(client, prefix + ':generation', lambda g: prefix + ':' + str(g),
                builder, json.dumps, json.loads, 60)
        try:
            with pytest.raises(ValueError, match='builder failure'):
                await fill(broken)
            assert not await client.exists(lock)
            await client.set(lock, 'replacement-owner', px=100)
            assert await client.eval(RELEASE, 1, lock, 'old-owner') == 0
            assert await client.get(lock) == b'replacement-owner'
            assert await fill(build) == {'valid': True}
        finally:
            keys = [key async for key in client.scan_iter(prefix + '*')]
            if keys:
                await client.delete(*keys)
            await client.aclose()
    run(exercise())


def test_cancelled_builder_releases_lock(redis_fixture):
    async def exercise():
        client = Redis(host='127.0.0.1', port=27019, db=15)
        prefix = redis_fixture
        entered = asyncio.Event()
        async def build():
            entered.set()
            await asyncio.sleep(60)
        try:
            task = asyncio.create_task(cached_catalogue(client, prefix + ':generation',
                lambda g: prefix + ':' + str(g), build, json.dumps, json.loads, 60))
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not await client.exists(prefix + ':0:fill-lock')
        finally:
            await client.aclose()
    run(exercise())
