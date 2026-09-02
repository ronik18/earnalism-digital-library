"""A1.1 parity vectors for the existing cache contract."""

from __future__ import annotations

import hashlib
import importlib
import asyncio
import os
import secrets
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_cache_media_a11")
os.environ.setdefault("JWT_SECRET", "cache-media-a11-synthetic")
server = importlib.import_module("backend.server")
try:
    cache_client = importlib.import_module("backend.cache.client")
    cache_keys = importlib.import_module("backend.cache.keys")
    legacy_pickle = importlib.import_module("backend.cache.legacy_pickle")
    cache_metrics = importlib.import_module("backend.cache.metrics")
except ModuleNotFoundError:
    # The same vectors deliberately run against the server-only baseline after
    # `git revert <A1_1_EXTRACTION_COMMIT>`.
    cache_client = None
    cache_keys = None
    legacy_pickle = None
    cache_metrics = None


def test_key_vectors_remain_exact():
    assert server._public_cache_key("books", category="all", q="") == (
        'books:{"catalog_truth": "controlled-covers-v1", "category": "all", "q": "", "truth_gate": "audio-contract-v16"}'
    )
    assert server._public_cache_key("home_payload", books_limit=8, books_offset=0) == (
        'home_payload:{"books_limit": 8, "books_offset": 0, "catalog_truth": "controlled-covers-v1", "truth_gate": "audio-contract-v16"}'
    )
    assert server._public_cache_key("book_detail", slug="synthetic-book").endswith('"truth_gate": "audio-contract-v16"}')
    assert server._public_cache_key("book_chapter", slug="synthetic-book", chapter_id="chapter-001") == (
        'book_chapter:{"catalog_truth": "controlled-covers-v1", "chapter_id": "chapter-001", '
        '"slug": "synthetic-book", "truth_gate": "audio-contract-v16"}'
    )
    assert server._user_cache_key("synthetic-user").startswith("earnalism:cache:v2:user-doc:user:")
    assert server._user_session_cache_key("synthetic-session").startswith("earnalism:cache:v2:user-session:session:")
    assert server._user_wallet_cache_key("synthetic-user") == "earnalism:user-wallet:synthetic-user"
    assert server._redis_key("public-cache", "generation") == "earnalism:public-cache:generation"
    assert server._redis_key("reader-content-cache", "generation") == "earnalism:reader-content-cache:generation"
    assert cache_keys is not None
    assert cache_keys.cache_digest_key(server.REDIS_KEY_PREFIX, "reader-manifest", "synthetic-listener-manifest") == (
        "earnalism:cache:reader-manifest:08e9b65028a3c6decd5390194b339834e7b50b352e3c60d991c09c0723c1a922"
    )


@pytest.mark.parametrize(
    ("value", "marker", "length", "digest"),
    [
        ({"value": "x"}, b"p:", 29, "edf72472ef5381207fca0b7f3b4f473e2429ff4690613d48d6d8ee18cd722c1d"),
        ({"value": "x" * 5000}, b"z:", 65, "561d1ca531e2ec0cf11313700cf6d92a141f569dd7cb9135d6a60c2e362f6302"),
    ],
)
def test_codec_vectors_keep_current_pickle_bytes(value, marker, length, digest):
    assert legacy_pickle is not None
    encoded = legacy_pickle.encode(value, compress_min_bytes=server.REDIS_CACHE_COMPRESS_MIN_BYTES)
    assert encoded.startswith(marker)
    assert len(encoded) == length
    assert hashlib.sha256(encoded).hexdigest() == digest
    assert legacy_pickle.decode(encoded) == value


def test_ttl_jitter_vectors_use_current_random_bounds(monkeypatch):
    monkeypatch.setattr(secrets, "randbelow", lambda upper: upper - 1)
    assert {ttl: server._ttl_with_jitter(ttl) for ttl in (0, 1, 8, 20, 300, 1800)} == {
        0: 0, 1: 1, 8: 9, 20: 24, 300: 330, 1800: 1830,
    }


def test_codec_and_media_rejection_vectors_are_fail_closed():
    assert server._redis_cache_payload_is_media({"audio": b"ID3"}) is True
    assert server._redis_cache_payload_is_media({"cover": "data:image/png;base64,AAAA"}) is True
    assert server._redis_cache_payload_is_media({"audio_url": "https://example.test/audio.mp3"}) is False


def test_client_construction_lifecycle_and_server_identity(monkeypatch):
    if cache_client is None:
        pytest.skip("A1.1 extracted client is absent in the rollback baseline")
    class FakeRedis:
        def __init__(self):
            self.pings = 0
            self.closed = 0

        async def ping(self):
            self.pings += 1

        async def aclose(self):
            self.closed += 1

    created = []
    previous_client = cache_client.runtime.client
    previous_available = cache_client.runtime.available
    previous_calls = cache_client.runtime.initialize_calls
    previous_close_calls = cache_client.runtime.close_calls
    try:
        cache_client.runtime.client = None
        cache_client.runtime.available = False

        def factory(url, **kwargs):
            created.append((url, kwargs))
            return FakeRedis()

        asyncio.run(cache_client.initialize(
            enabled=True, multi_replica_enabled=False, redis_url="redis://synthetic.invalid/0",
            fail_fast=False, connect_timeout=2.0, socket_timeout=2.0,
            configure_on_startup=False, maxmemory="", maxmemory_policy="volatile-lfu",
            logger=server.logger, redis_factory=factory,
        ))
        assert created == [("redis://synthetic.invalid/0", {
            "socket_connect_timeout": 2.0, "socket_timeout": 2.0, "retry_on_timeout": True,
        })]
        active = cache_client.active_client()
        assert active is not None and active.pings == 1

        asyncio.run(cache_client.initialize(
            enabled=True, multi_replica_enabled=False, redis_url="redis://synthetic.invalid/0",
            fail_fast=False, connect_timeout=2.0, socket_timeout=2.0,
            configure_on_startup=False, maxmemory="", maxmemory_policy="volatile-lfu",
            logger=server.logger, redis_factory=factory,
        ))
        assert len(created) == 1

        async def already_initialized(**_kwargs):
            return None

        monkeypatch.setattr(cache_client, "initialize", already_initialized)
        asyncio.run(server.initialize_replica_state_backends())
        assert server._redis_client is cache_client.active_client()
        assert server._redis_available is cache_client.is_available()
        asyncio.run(cache_client.close())
        assert active.closed == 1
    finally:
        cache_client.runtime.client = previous_client
        cache_client.runtime.available = previous_available
        cache_client.runtime.initialize_calls = previous_calls
        cache_client.runtime.close_calls = previous_close_calls
        server._redis_client = previous_client
        server._redis_available = previous_available
        asyncio.set_event_loop(asyncio.new_event_loop())


def test_cache_modules_have_no_import_time_redis_connection():
    if cache_client is None:
        pytest.skip("A1.1 extracted client is absent in the rollback baseline")
    reloaded = importlib.reload(cache_client)
    assert reloaded.active_client() is None
    assert reloaded.is_available() is False


def test_metrics_and_admin_status_schema_remain_compatible():
    if cache_metrics is not None:
        assert server._cache_stats is cache_metrics.cache_stats
        cache_metrics.cache_stats["synthetic_hit"] += 1
    else:
        server._cache_stats["synthetic_hit"] += 1
    response = asyncio.run(server.admin_cache_status())
    assert {"enabled", "available", "key_prefix", "timeouts_seconds", "ttl_seconds", "compression", "stats", "policy", "redis"} <= set(response)
    assert response["stats"]["synthetic_hit"] >= 1
    asyncio.set_event_loop(asyncio.new_event_loop())


def test_redis_cache_facade_preserves_shared_client_and_outage_fallback():
    class FakeRedis:
        def __init__(self):
            self.entries = {}
            self.fail = False

        async def setex(self, key, ttl, value):
            if self.fail:
                raise RuntimeError("synthetic outage")
            self.entries[key] = (ttl, value)

        async def get(self, key):
            if self.fail:
                raise RuntimeError("synthetic outage")
            item = self.entries.get(key)
            return item[1] if item else None

        async def delete(self, key):
            self.entries.pop(key, None)

    fake = FakeRedis()
    previous_client = server._redis_client
    previous_available = server._redis_available
    try:
        server._redis_client = fake
        server._redis_available = True
        asyncio.run(server._redis_cache_set("synthetic", "key", {"value": "x"}, 20))
        if cache_client is not None:
            assert cache_client.active_client() is fake
        assert fake.entries[server._v2_cache_key("synthetic", "key")][0] in range(20, 25)
        assert asyncio.run(server._redis_cache_get("synthetic", "key")) == {"value": "x"}
        fake.entries[server._v2_cache_key("synthetic", "malformed")] = (20, b"malformed")
        assert asyncio.run(server._redis_cache_get("synthetic", "malformed")) is None
        fake.fail = True
        assert asyncio.run(server._redis_cache_get("synthetic", "key")) is None
        server._redis_available = False
        assert asyncio.run(server._redis_cache_get("synthetic", "missing")) is None
    finally:
        server._redis_client = previous_client
        server._redis_available = previous_available
        if cache_client is not None:
            cache_client.runtime.client = previous_client
            cache_client.runtime.available = previous_available
        asyncio.set_event_loop(asyncio.new_event_loop())


def test_multi_replica_without_redis_url_still_fails_fast():
    if cache_client is None:
        pytest.skip("A1.1 extracted client is absent in the rollback baseline")
    with pytest.raises(RuntimeError, match="REDIS_URL is required"):
        asyncio.run(cache_client.initialize(
            enabled=True, multi_replica_enabled=True, redis_url="", fail_fast=True,
            connect_timeout=2.0, socket_timeout=2.0, configure_on_startup=False,
            maxmemory="", maxmemory_policy="volatile-lfu", logger=server.logger,
        ))
    asyncio.set_event_loop(asyncio.new_event_loop())
