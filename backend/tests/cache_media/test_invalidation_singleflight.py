"""A4 coherence and bounded process-local singleflight coverage."""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_safe_json_cache_migration import _restore_redis, _with_fake_redis

server = importlib.import_module("backend.server")
store_module = importlib.import_module("backend.cache.store")
policy_module = importlib.import_module("backend.cache.policy")
singleflight_module = importlib.import_module("backend.cache.singleflight")


def _store(flight):
    fake, prior = _with_fake_redis()
    server._sync_cache_runtime_from_compat()
    return fake, prior, store_module.RedisCacheStore(
        client_provider=lambda: fake,
        enabled_provider=lambda: True,
        key_builder=lambda policy, identity: server._v2_cache_key(policy.namespace, identity.resource, scope=policy.scope, identity=identity.identity, version=identity.version),
        encoder=lambda raw: server.cache_codec.encode_v2_canonical(raw, compress_min_bytes=1),
        decoder=server.cache_codec.decode_v2,
        canonical_encoder=server.cache_codec.canonical_json_bytes,
        canonical_decoder=server.cache_codec.decoded_canonical_json_bytes,
        stats=server._cache_stats,
        logger=None,
        singleflight=flight,
    )


def _policy():
    registered = policy_module.resolve_active_policy("reader-content")
    return store_module.CachePolicy("reader-content", "resource", 20, registered.metric_namespace, registered)


def test_same_identity_singleflight_runs_one_loader_for_1_5_20_50_callers():
    async def scenario(count):
        flight = singleflight_module.SingleFlight(256)
        fake, prior, store = _store(flight)
        calls = []
        try:
            async def loader():
                calls.append(True)
                await asyncio.sleep(0)
                return {"value": "shared"}
            values = await asyncio.gather(*[store.cache_aside(_policy(), store_module.CacheIdentity("a", "same"), loader) for _ in range(count)])
            assert values == [{"value": "shared"}] * count
            assert len(calls) == 1 and flight.current == 0 and len(fake.entries) == 1
        finally:
            _restore_redis(prior)
    for count in (1, 5, 20, 50):
        asyncio.run(scenario(count))


def test_different_identities_are_not_serialized():
    async def scenario():
        flight = singleflight_module.SingleFlight(256)
        _, prior, store = _store(flight)
        started = []
        gate = asyncio.Event()
        try:
            async def loader(name):
                started.append(name)
                await gate.wait()
                return {"value": name}
            first = asyncio.create_task(store.cache_aside(_policy(), store_module.CacheIdentity("a", "one"), lambda: loader("one")))
            second = asyncio.create_task(store.cache_aside(_policy(), store_module.CacheIdentity("b", "two"), lambda: loader("two")))
            await asyncio.sleep(0.01)
            assert set(started) == {"one", "two"}
            gate.set()
            assert await asyncio.gather(first, second) == [{"value": "one"}, {"value": "two"}]
        finally:
            _restore_redis(prior)
    asyncio.run(scenario())


def test_version_change_during_load_suppresses_stale_write():
    async def scenario():
        flight = singleflight_module.SingleFlight(256)
        fake, prior, store = _store(flight)
        version = ["before"]
        release = asyncio.Event()
        started = asyncio.Event()
        try:
            async def loader():
                started.set()
                await release.wait()
                return {"value": "old"}
            task = asyncio.create_task(store.cache_aside(_policy(), store_module.CacheIdentity("a", "race", "before"), loader, version_resolver=lambda: _version(version)))
            await started.wait()
            version[0] = "after"
            release.set()
            assert await task == {"value": "old"}
            assert server._v2_cache_key("reader-content", "race", identity="a", version="before") not in fake.entries
        finally:
            _restore_redis(prior)
    asyncio.run(scenario())


async def _version(value):
    return value[0]


def test_capacity_bypass_and_waiter_cancellation_do_not_leak_or_cancel_loader():
    async def scenario():
        flight = singleflight_module.SingleFlight(1)
        gate = asyncio.Event()
        calls = []
        async def loader():
            calls.append(True)
            await gate.wait()
            return "ok"
        leader = asyncio.create_task(flight.run("a", loader))
        waiter = asyncio.create_task(flight.run("a", loader))
        await asyncio.sleep(0)
        waiter.cancel()
        try:
            await waiter
        except asyncio.CancelledError:
            pass
        bypass = asyncio.create_task(flight.run("b", lambda: _immediate("bypass")))
        gate.set()
        assert await leader == ("ok", "leader")
        assert await bypass == ("bypass", "capacity_bypass")
        await asyncio.sleep(0)
        assert flight.current == 0 and len(calls) == 1
    asyncio.run(scenario())


async def _immediate(value):
    return value
