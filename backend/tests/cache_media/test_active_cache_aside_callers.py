"""A4.1 active policy-family adoption of the central cache-aside adapter."""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_invalidation_singleflight import _store
from test_safe_json_cache_migration import _restore_redis

server = importlib.import_module("backend.server")
singleflight_module = importlib.import_module("backend.cache.singleflight")


FAMILIES = (
    ("public-cache", "public", "public-catalog", "home", True),
    ("reader-content", "resource", "book:dracula", "chapter:1", True),
    ("reader-manifest", "resource", "book:dracula", "manifest", True),
    ("user-private", "user", "user-a", "wallet-transactions", False),
    ("user-doc", "user", "user-a", "profile", False),
    ("user-session", "session", "session-a", "session", False),
)


@pytest.mark.parametrize("policy_id, entrypoint", (
    ("public-cache-v2", "_public_cache_aside"),
    ("reader-content-v2", "_reader_book_access_doc"),
    ("reader-manifest-v2", "_reader_book_manifest_doc"),
    ("user-private-v2", "user_my_transactions"),
    ("user-doc-v2", "_cached_user_doc"),
    ("user-session-v2", "_cached_user_session"),
))
def test_active_runtime_callers_adopt_the_central_adapter(policy_id, entrypoint):
    source = Path(server.__file__).read_text(encoding="utf-8")
    start = source.index(f"async def {entrypoint}")
    next_definition = source.find("\nasync def ", start + 1)
    body = source[start:next_definition if next_definition >= 0 else None]
    assert "_redis_cache_aside(" in body or "_public_cache_aside(" in body, policy_id


def _adapter(monkeypatch):
    fake, prior, store = _store(singleflight_module.SingleFlight(256))
    monkeypatch.setattr(server, "_v2_cache_store", lambda: store)
    return fake, prior, store


@pytest.mark.parametrize("namespace,scope,identity,resource,mutable", FAMILIES)
def test_active_cache_aside_family_contract(
    monkeypatch, namespace, scope, identity, resource, mutable,
):
    """Cold/warm/outage/disabled/corrupt/concurrent/mutation paths stay coherent."""
    async def scenario():
        fake, prior, store = _adapter(monkeypatch)
        version = ["before"]

        async def resolve_version():
            return version[0]

        async def invoke(loader):
            return await server._redis_cache_aside(
                namespace, resource, 20, loader, scope=scope, identity=identity,
                version=version[0] if mutable else "", version_resolver=resolve_version if mutable else None,
            )

        try:
            # Cold miss and warm hit preserve the loader's plain business value.
            calls = []
            async def cold_loader():
                calls.append("cold")
                return {"family": namespace, "value": "source"}
            expected = await invoke(cold_loader)
            assert calls == ["cold"]
            assert await invoke(lambda: _unexpected_loader()) == expected

            # A corrupt v2 value is deleted exactly and replaced from source.
            fake.entries.clear()
            corrupt_key = server._v2_cache_key(namespace, resource, scope=scope, identity=identity, version=version[0] if mutable else "")
            fake.entries[corrupt_key] = (20, b"not-json-v2")
            assert await invoke(cold_loader) == expected
            assert corrupt_key in fake.deleted

            # Redis outage and cache-disabled modes return the source result.
            fake.entries.clear()
            fake.fail = True
            assert await invoke(cold_loader) == expected
            fake.fail = False
            server._redis_available = False
            assert await invoke(cold_loader) == expected
            server._redis_available = True

            # Twenty same-identity misses have one leader/source and no leak.
            fake.entries.clear()
            calls.clear()
            async def concurrent_loader():
                calls.append("concurrent")
                await asyncio.sleep(0)
                return {"family": namespace, "value": "concurrent"}
            values = await asyncio.gather(*(invoke(concurrent_loader) for _ in range(20)))
            assert values == [{"family": namespace, "value": "concurrent"}] * 20
            assert calls == ["concurrent"] and store._singleflight.current == 0

            # Different identities remain independent (no global serialization).
            fake.entries.clear()
            started, release = set(), asyncio.Event()
            async def named(name):
                started.add(name)
                await release.wait()
                return {"name": name}
            first = asyncio.create_task(invoke(lambda: named("first")))
            second = asyncio.create_task(server._redis_cache_aside(
                namespace, resource + "-other", 20, lambda: named("second"), scope=scope,
                identity=identity + "-other", version=version[0] if mutable else "",
                version_resolver=resolve_version if mutable else None,
            ))
            await asyncio.sleep(0.01)
            assert started == {"first", "second"}
            release.set()
            assert (await first)["name"] == "first" and (await second)["name"] == "second"

            # Mutable generations suppress stale fills. Immutable user/session
            # identities retain the existing exact-delete invalidation strategy.
            if mutable:
                fake.entries.clear()
                begun, release = asyncio.Event(), asyncio.Event()
                async def stale_loader():
                    begun.set()
                    await release.wait()
                    return {"value": "old"}
                stale = asyncio.create_task(invoke(stale_loader))
                await begun.wait()
                version[0] = "after"
                release.set()
                assert await stale == {"value": "old"}
                stale_key = server._v2_cache_key(namespace, resource, scope=scope, identity=identity, version="before")
                assert stale_key not in fake.entries
        finally:
            _restore_redis(prior)

    asyncio.run(scenario())


async def _unexpected_loader():
    raise AssertionError("warm cache hit invoked the source loader")
