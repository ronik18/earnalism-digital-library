"""A3 bounded-policy and low-cardinality observability coverage."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_safe_json_cache_migration import _restore_redis, _with_fake_redis


server = importlib.import_module("backend.server")
policy = importlib.import_module("backend.cache.policy")
metrics = importlib.import_module("backend.cache.metrics")


def test_every_active_v2_namespace_has_one_finite_registered_policy():
    assert set(policy.ACTIVE_CACHE_POLICIES) == {
        "public-cache", "reader-content", "reader-manifest", "user-private", "user-doc", "user-session",
    }
    assert len({item.policy_id for item in policy.ACTIVE_CACHE_POLICIES.values()}) == 6
    for item in policy.ACTIVE_CACHE_POLICIES.values():
        raw, stored = item.effective_limits()
        assert 0 < raw <= policy.A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES
        assert 0 < stored <= policy.A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES
        assert item.binary_media_prohibited is True
    try:
        policy.resolve_active_policy("untrusted-request-namespace")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown dynamic namespace was accepted")


def test_safe_configuration_bounds_reject_invalid_and_over_ceiling(monkeypatch):
    maximum = policy.A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES
    monkeypatch.setenv("A3_TEST_LIMIT", "not-an-int")
    assert policy._bounded_env_int("A3_TEST_LIMIT", 100, maximum=maximum) == 100
    monkeypatch.setenv("A3_TEST_LIMIT", "0")
    assert policy._bounded_env_int("A3_TEST_LIMIT", 100, maximum=maximum) == 100
    monkeypatch.setenv("A3_TEST_LIMIT", str(maximum + 1))
    assert policy._bounded_env_int("A3_TEST_LIMIT", 100, maximum=maximum) == 100


def test_write_limits_are_inclusive_and_large_compressible_values_bypass_without_set():
    fake, prior = _with_fake_redis()
    definition = policy.resolve_active_policy("reader-content")
    try:
        exact = "x" * (definition.effective_limits()[0] - 2)
        asyncio.run(server._redis_cache_set("reader-content", "exact", exact, 20))
        exact_key = server._v2_cache_key("reader-content", "exact")
        assert exact_key in fake.entries
        asyncio.run(server._redis_cache_set("reader-content", "oversized", exact + "x", 20))
        assert server._v2_cache_key("reader-content", "oversized") not in fake.entries
    finally:
        _restore_redis(prior)


def test_read_policy_limit_deletes_only_the_oversized_current_v2_key():
    fake, prior = _with_fake_redis()
    definition = policy.resolve_active_policy("reader-content")
    try:
        oversized = "x" * definition.effective_limits()[0]
        oversized_key = server._v2_cache_key("reader-content", "oversized-read")
        untouched_key = server._v2_cache_key("reader-content", "unrelated")
        fake.entries[oversized_key] = (20, server.cache_codec.encode_v2(oversized, compress_min_bytes=1))
        fake.entries[untouched_key] = (20, server.cache_codec.encode_v2("ok", compress_min_bytes=1))
        assert asyncio.run(server._redis_cache_get("reader-content", "oversized-read")) is None
        assert oversized_key in fake.deleted and untouched_key not in fake.deleted
        assert untouched_key in fake.entries
    finally:
        _restore_redis(prior)


def test_metrics_are_bounded_and_binary_bypass_does_not_write():
    fake, prior = _with_fake_redis()
    try:
        asyncio.run(server._redis_cache_set("reader-content", "binary", {"audio": b"ID3"}, 20))
        assert server._v2_cache_key("reader-content", "binary") not in fake.entries
        snapshot = metrics.snapshot_v2()
        assert snapshot["scope"] == "process_local"
        assert any(event["policy_id"] == "reader-content-v2" for event in snapshot["events"])
    finally:
        _restore_redis(prior)


def test_admin_status_is_additive_and_redacts_cache_identity_and_values():
    previous_available = server._redis_available
    previous_client = server._redis_client
    try:
        server._redis_available = False
        status = asyncio.run(server.admin_cache_status())
        assert "cache_v2" in status and "audio_delivery" in status and "stats" in status and "redis" in status
        rendered = repr(status)
        assert "untrusted-request-namespace" not in rendered
        assert "redis://" not in rendered
        assert status["cache_v2"]["active_policy_count"] == 6
        assert status["audio_delivery"]["process_local"] is True
        assert status["audio_delivery"]["metadata_cache"]["activated"] is False
    finally:
        server._redis_available, server._redis_client = previous_available, previous_client
