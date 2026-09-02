"""A2 security and migration coverage for the active versioned cache path."""

from __future__ import annotations

import asyncio
import datetime as dt
import importlib
import os
import pickle
import sys
import uuid
import zlib
from decimal import Decimal
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_cache_media_a2")
os.environ.setdefault("JWT_SECRET", "cache-media-a2-synthetic")
server = importlib.import_module("backend.server")
codec = importlib.import_module("backend.cache.codec")
cache_store = importlib.import_module("backend.cache.store")
cache_keys = importlib.import_module("backend.cache.keys")
legacy_pickle = importlib.import_module("backend.cache.legacy_pickle")


class FakeRedis:
    def __init__(self):
        self.entries = {}
        self.deleted = []
        self.fail = False

    async def get(self, key):
        if self.fail:
            raise TimeoutError("synthetic timeout")
        item = self.entries.get(key)
        return item[1] if item else None

    async def setex(self, key, ttl, value):
        if self.fail:
            raise TimeoutError("synthetic timeout")
        self.entries[key] = (ttl, value)

    async def delete(self, key):
        self.deleted.append(key)
        self.entries.pop(key, None)


def _with_fake_redis():
    fake = FakeRedis()
    prior = (
        server._redis_client, server._redis_available,
        server.cache_client.runtime.client, server.cache_client.runtime.available,
    )
    server._redis_client, server._redis_available = fake, True
    return fake, prior


def _restore_redis(prior):
    server._redis_client, server._redis_available, server.cache_client.runtime.client, server.cache_client.runtime.available = prior
    asyncio.set_event_loop(asyncio.new_event_loop())


def test_v2_key_vectors_are_deterministic_isolated_and_non_sensitive():
    first = server._v2_cache_key("user-doc", "profile", scope="user", identity="user-a", version="1")
    assert first == server._v2_cache_key("user-doc", "profile", scope="user", identity="user-a", version="1")
    assert first != server._v2_cache_key("user-doc", "profile", scope="user", identity="user-b", version="1")
    assert first != server._v2_cache_key("user-session", "profile", scope="session", identity="user-a", version="1")
    assert first != server._v2_cache_key("user-doc", "other", scope="user", identity="user-a", version="1")
    assert first != server._v2_cache_key("user-doc", "profile", scope="user", identity="user-a", version="2")
    assert first.startswith("earnalism:cache:v2:user-doc:user:")
    assert "user-a" not in first and "profile" not in first


def test_v2_codec_is_deterministic_and_round_trips_explicit_types():
    value = {
        "decimal": Decimal("12.30"), "date": dt.date(2026, 9, 2),
        "datetime": dt.datetime(2026, 9, 2, 12, 30, tzinfo=dt.timezone.utc),
        "uuid": uuid.UUID("12345678-1234-5678-1234-567812345678"), "nested": {"a": [None, True, 2]},
    }
    encoded = codec.encode_v2(value, compress_min_bytes=99_999)
    assert encoded.startswith(codec.JSON_V2_PREFIX)
    assert encoded == codec.encode_v2(dict(reversed(list(value.items()))), compress_min_bytes=99_999)
    assert codec.decode_v2(encoded) == value


@pytest.mark.parametrize("blob", [
    b"pickle:", b"json-v2:\xff", b"json-v2:{", b"json-v2:{\"$cache_type\":\"unknown\",\"value\":\"x\"}",
    b"zlib-json-v2:not-zlib", b"zlib-json-v2:" + zlib.compress(b"{}") + b"trailing",
])
def test_v2_codec_rejects_invalid_envelopes(blob):
    with pytest.raises(codec.CacheCodecError):
        codec.decode_v2(blob)


def test_v2_codec_rejects_decompression_bomb_excessive_nesting_and_binary():
    bomb = codec.ZLIB_JSON_V2_PREFIX + zlib.compress(b'"' + (b"x" * (codec.A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES + 1)) + b'"')
    with pytest.raises(codec.CacheCodecError):
        codec.decode_v2(bomb)
    deep = value = {}
    for _ in range(codec.A2_CODEC_MAX_NESTING + 2):
        next_value = {}
        value["next"] = next_value
        value = next_value
    with pytest.raises(codec.CacheCodecError):
        codec.encode_v2(deep, compress_min_bytes=1)
    for binary in (b"ID3", bytearray(b"ID3"), memoryview(b"ID3")):
        with pytest.raises(codec.CacheCodecError):
            codec.encode_v2(binary, compress_min_bytes=1)


def test_v2_miss_ignores_legacy_pickle_and_writes_only_v2_key():
    fake, prior = _with_fake_redis()
    try:
        legacy_key = cache_keys.cache_digest_key(server.REDIS_KEY_PREFIX, "reader-content", "resource")
        legacy_blob = legacy_pickle.encode({"legacy": True}, compress_min_bytes=server.REDIS_CACHE_COMPRESS_MIN_BYTES)
        fake.entries[legacy_key] = (20, legacy_blob)
        assert asyncio.run(server._redis_cache_get("reader-content", "resource")) is None
        asyncio.run(server._redis_cache_set("reader-content", "resource", {"fresh": True}, 20))
        v2_key = server._v2_cache_key("reader-content", "resource")
        assert legacy_key in fake.entries and fake.entries[legacy_key][1] == legacy_blob
        assert v2_key in fake.entries and fake.entries[v2_key][1].startswith(codec.JSON_V2_PREFIX)
        assert asyncio.run(server._redis_cache_get("reader-content", "resource")) == {"fresh": True}
    finally:
        _restore_redis(prior)


def test_corrupt_v2_exact_key_cleanup_and_cache_aside_source_fallback(tmp_path):
    fake, prior = _with_fake_redis()
    marker = tmp_path / "pickle-executed"

    class Malicious:
        def __reduce__(self):
            return Path.touch, (marker,)

    try:
        server._sync_cache_runtime_from_compat()
        legacy_key = cache_keys.cache_digest_key(server.REDIS_KEY_PREFIX, "synthetic", "unsafe")
        v2_key = server._v2_cache_key("synthetic", "unsafe")
        fake.entries[legacy_key] = (20, pickle.dumps(Malicious()))
        fake.entries[v2_key] = (20, b"invalid-v2-marker")
        store = server._v2_cache_store()
        calls = []

        async def loader():
            calls.append(True)
            return {"source": "truth"}

        result = asyncio.run(store.cache_aside(
            cache_store.CachePolicy("synthetic", "resource", 20),
            cache_store.CacheIdentity("unsafe", "unsafe"), loader,
        ))
        assert result == {"source": "truth"} and calls == [True]
        assert not marker.exists()
        assert legacy_key in fake.entries
        assert v2_key in fake.deleted
        assert fake.entries[v2_key][1].startswith(codec.JSON_V2_PREFIX)
    finally:
        _restore_redis(prior)


def test_store_outage_disabled_and_media_are_nonfatal():
    fake, prior = _with_fake_redis()
    try:
        fake.fail = True
        assert asyncio.run(server._redis_cache_get("reader-content", "outage")) is None
        asyncio.run(server._redis_cache_set("reader-content", "outage", {"source": True}, 20))
        fake.fail = False
        asyncio.run(server._redis_cache_set("reader-content", "audio", {"audio": b"ID3"}, 20))
        assert server._v2_cache_key("reader-content", "audio") not in fake.entries
        server._redis_available = False
        assert asyncio.run(server._redis_cache_get("reader-content", "disabled")) is None
    finally:
        _restore_redis(prior)


def test_public_generation_and_protected_isolation_vectors():
    assert server._v2_cache_key("public-cache", "home", scope="public", identity="public-catalog", version="1") != server._v2_cache_key("public-cache", "home", scope="public", identity="public-catalog", version="2")
    assert server._v2_cache_key("user-doc", "u", scope="user", identity="a") != server._v2_cache_key("user-doc", "u", scope="user", identity="b")
    assert server._v2_cache_key("user-session", "s", scope="session", identity="session-a") != server._v2_cache_key("user-session", "s", scope="session", identity="session-b")
