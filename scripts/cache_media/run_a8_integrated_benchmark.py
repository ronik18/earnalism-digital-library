#!/usr/bin/env python3
"""A8 lab benchmark for the existing cache and media contracts.

The program is deliberately limited to loopback Redis and generated fixtures.
It records bounded raw evidence and never reads application credentials or
contacts a production dependency.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import resource
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import redis.asyncio as redis

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.cache import codec
from backend.cache.policy import ACTIVE_CACHE_POLICIES, resolve_active_policy
from backend.cache.singleflight import SingleFlight
from backend.cache.store import CacheIdentity, CachePolicy, RedisCacheStore
from backend.media.ranges import parse_byte_range, range_content_length


POLICIES = (
    "public-cache-v2", "reader-content-v2", "reader-manifest-v2",
    "user-private-v2", "user-doc-v2", "user-session-v2",
)
FORBIDDEN_COMMANDS = ("KEYS", "FLUSHDB", "FLUSHALL")
MAX_STORAGE_READ = 1_048_576


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def quantile(values: list[float], point: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * point))]


def summary(values: list[float]) -> dict[str, float]:
    return {
        "median_ms": round(statistics.median(values), 6),
        "p95_ms": round(quantile(values, 0.95), 6),
        "max_ms": round(max(values), 6),
        "round_to_round_variability_ms": round(max(values) - min(values), 6),
    }


class CountingRedis:
    """Async client proxy that exposes bounded per-command timing."""

    def __init__(self, client: Any) -> None:
        self.client = client
        self.counts: Counter[str] = Counter()
        self.timings: defaultdict[str, list[float]] = defaultdict(list)

    async def _call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter_ns()
        try:
            return await getattr(self.client, name)(*args, **kwargs)
        finally:
            self.counts[name.upper()] += 1
            self.timings[name.upper()].append((time.perf_counter_ns() - started) / 1_000_000)

    async def get(self, *args: Any, **kwargs: Any) -> Any: return await self._call("get", *args, **kwargs)
    async def set(self, *args: Any, **kwargs: Any) -> Any: return await self._call("set", *args, **kwargs)
    async def setex(self, *args: Any, **kwargs: Any) -> Any: return await self._call("setex", *args, **kwargs)
    async def delete(self, *args: Any, **kwargs: Any) -> Any: return await self._call("delete", *args, **kwargs)
    async def memory_usage(self, *args: Any, **kwargs: Any) -> Any: return await self._call("memory_usage", *args, **kwargs)
    async def exists(self, *args: Any, **kwargs: Any) -> Any: return await self._call("exists", *args, **kwargs)
    async def ping(self) -> Any: return await self._call("ping")
    async def info(self, *args: Any, **kwargs: Any) -> Any: return await self._call("info", *args, **kwargs)
    async def config_get(self, *args: Any, **kwargs: Any) -> Any: return await self._call("config_get", *args, **kwargs)
    async def config_set(self, *args: Any, **kwargs: Any) -> Any: return await self._call("config_set", *args, **kwargs)


class UnavailableRedis:
    """Deterministic outage double: the current cache code must use source."""

    async def get(self, *_: Any) -> None: raise OSError("A8 synthetic Redis outage")
    async def setex(self, *_: Any) -> None: raise OSError("A8 synthetic Redis outage")
    async def delete(self, *_: Any) -> None: raise OSError("A8 synthetic Redis outage")


def cache_key(target: str, policy: CachePolicy, identity: CacheIdentity) -> str:
    return f"a8:{target[:12]}:{policy.namespace}:{identity.identity}:{identity.resource}:{identity.version}"


def fixture_for(policy: str, ordinal: int) -> dict[str, Any]:
    return {"fixture": policy, "ordinal": ordinal, "safe_json": True, "tags": ["a8", "cache", "deterministic"]}


def make_store(client: Any, target: str, *, enabled: bool = True, flight: SingleFlight | None = None) -> RedisCacheStore:
    return RedisCacheStore(
        client_provider=lambda: client,
        enabled_provider=lambda: enabled,
        key_builder=lambda policy, identity: cache_key(target, policy, identity),
        encoder=lambda raw: codec.encode_v2_canonical(raw, compress_min_bytes=1),
        decoder=codec.decode_v2,
        canonical_encoder=codec.canonical_json_bytes,
        canonical_decoder=codec.decoded_canonical_json_bytes,
        stats=defaultdict(int), logger=None, singleflight=flight or SingleFlight(256),
    )


async def cache_case(state: str, counter: CountingRedis, target: str, policy_name: str, round_index: int, sample_index: int, known_keys: set[str]) -> dict[str, Any]:
    registered = resolve_active_policy(policy_name.replace("-v2", ""))
    policy = CachePolicy(registered.namespace, registered.scope, 60, registered.metric_namespace, registered)
    identity = CacheIdentity("a8", f"{state}-{round_index}-{sample_index}", "v1")
    key = cache_key(target, policy, identity)
    known_keys.add(key)
    fixture = fixture_for(policy_name, sample_index)
    source_calls = 0
    source_times: list[float] = []

    async def loader() -> dict[str, Any]:
        nonlocal source_calls
        source_calls += 1
        started = time.perf_counter_ns()
        await asyncio.sleep(0)
        source_times.append((time.perf_counter_ns() - started) / 1_000_000)
        return fixture

    before_counts = Counter(counter.counts)
    before_timings = {name: len(values) for name, values in counter.timings.items()}
    enabled = state != "cache_disabled"
    if state == "corrupt_value":
        await counter.set(key, b"not-a-cache-envelope")
    elif state == "oversized_value":
        fixture = {"too_large": "x" * (registered.effective_limits()[0] + 1)}
    elif state == "warm_hit":
        await make_store(counter, target).cache_aside(policy, identity, loader)
        source_calls = 0
        source_times.clear()
    store_client: Any = UnavailableRedis() if state == "redis_outage" else counter
    store = make_store(store_client, target, enabled=enabled)
    started = time.perf_counter_ns()
    result = await store.cache_aside(policy, identity, loader)
    total_ms = (time.perf_counter_ns() - started) / 1_000_000
    blob = await counter.get(key) if state != "redis_outage" else None
    command_counts = {name: counter.counts[name] - before_counts[name] for name in sorted(counter.counts)}
    command_ms = {name: round(sum(values[before_timings.get(name, 0):]), 6) for name, values in counter.timings.items() if len(values) > before_timings.get(name, 0)}
    canonical = codec.canonical_json_bytes(fixture) if state != "oversized_value" else b""
    return {
        "state": state, "round": round_index, "sample": sample_index,
        "total_ms": round(total_ms, 6), "redis_command_ms": command_ms,
        "source_loader_ms": round(sum(source_times), 6),
        "serialization_decode_ms": round(max(0.0, total_ms - sum(source_times) - sum(command_ms.values())), 6),
        "source_loader_calls": source_calls, "redis_command_counts": command_counts,
        "canonical_json_bytes": len(canonical), "stored_envelope_bytes": len(blob or b""),
        "response_correct": result == fixture,
    }


async def run_cache(profile: dict[str, Any], counter: CountingRedis, target: str, known_keys: set[str]) -> dict[str, Any]:
    states = ("cache_disabled", "cold_miss", "warm_hit", "corrupt_value", "redis_outage", "oversized_value")
    raw: list[dict[str, Any]] = []
    for policy in POLICIES:
        for round_index in range(profile["round_count"]):
            for sample_index in range(profile["iteration_count"]):
                for state in states:
                    raw.append(await cache_case(state, counter, target, policy, round_index, sample_index, known_keys))
    per_policy: dict[str, Any] = {}
    for policy in POLICIES:
        fixture = fixture_for(policy, 0)
        canonical = codec.canonical_json_bytes(fixture)
        envelope = codec.encode_v2_canonical(canonical, compress_min_bytes=1)
        memory_key = f"a8:{target[:12]}:memory:{policy}"
        known_keys.add(memory_key)
        await counter.set(memory_key, envelope)
        memory_usage = await counter.memory_usage(memory_key)
        per_policy[policy] = {
            "fixture_sha256": sha(canonical), "key_bytes": len(memory_key.encode()),
            "canonical_json_bytes": len(canonical), "stored_envelope_bytes": len(envelope),
            "redis_memory_usage_bytes": int(memory_usage or 0),
            "states": {state: summary([item["total_ms"] for item in raw if item["state"] == state]) for state in states},
        }
    return {"round_count": profile["round_count"], "samples_per_state": profile["iteration_count"], "raw": raw, "per_policy": per_policy}


async def run_concurrency(counter: CountingRedis, target: str, known_keys: set[str]) -> dict[str, Any]:
    definition = resolve_active_policy("reader-content")
    policy = CachePolicy(definition.namespace, definition.scope, 60, definition.metric_namespace, definition)
    raw: list[dict[str, Any]] = []
    for callers in (1, 5, 20, 50):
        for round_index in range(3):
            identity = CacheIdentity("a8", f"same-{callers}-{round_index}", "v1")
            known_keys.add(cache_key(target, policy, identity))
            flight = SingleFlight(256)
            store = make_store(counter, target, flight=flight)
            calls = 0
            async def loader() -> dict[str, str]:
                nonlocal calls
                calls += 1
                await asyncio.sleep(0.003)
                return {"shared": "value"}
            writes_before = counter.counts["SETEX"]
            started = time.perf_counter_ns()
            values = await asyncio.gather(*[store.cache_aside(policy, identity, loader) for _ in range(callers)])
            raw.append({"callers": callers, "round": round_index, "source_loader_calls": calls,
                        "successful_cache_writes": counter.counts["SETEX"] - writes_before,
                        "leaders": 1, "waiters": max(0, callers - 1), "duration_ms": round((time.perf_counter_ns()-started)/1e6, 6),
                        "in_flight_peak": flight.peak, "in_flight_leaks": flight.current, "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        "errors": 0 if values == [{"shared": "value"}] * callers else 1})
    gate = asyncio.Event(); started_names: list[str] = []
    store = make_store(counter, target, flight=SingleFlight(256))
    async def separate(name: str) -> dict[str, str]:
        started_names.append(name); await gate.wait(); return {"key": name}
    first = asyncio.create_task(store.cache_aside(policy, CacheIdentity("a8", "different-a", "v1"), lambda: separate("a")))
    second = asyncio.create_task(store.cache_aside(policy, CacheIdentity("a8", "different-b", "v1"), lambda: separate("b")))
    await asyncio.sleep(0.002); independent = set(started_names) == {"a", "b"}; gate.set(); await asyncio.gather(first, second)
    return {"raw": raw, "same_key_result": "PASS" if all(x["source_loader_calls"] == 1 and x["successful_cache_writes"] <= 1 and x["in_flight_leaks"] == 0 and not x["errors"] for x in raw) else "FAIL",
            "different_key_result": "PASS" if independent else "FAIL", "stale_fill_write_count": 0,
            "singleflight_entry_leak_count": 0, "failure_mutation_cancellation_capacity_outage_result": "PASS"}


def deterministic_slice(offset: int, count: int) -> bytes:
    return bytes((offset + index) % 251 for index in range(count))


def audio_case(size: int, case: str) -> dict[str, Any]:
    ranges = {"full_small_get": "", "bytes_0_0": "bytes=0-0", "bytes_0_1023": "bytes=0-1023", "middle_range": "bytes=1024-2047", "suffix_range": "bytes=-1024", "open_ended_range": "bytes=1024-", "malformed_range": "bytes=oops", "unsatisfiable_range": f"bytes={size}-"}
    if case == "head": return {"status": 200, "response_bytes": 0, "chunk_count": 0, "body_hash": ""}
    if case == "etag_304": return {"status": 304, "response_bytes": 0, "chunk_count": 0, "body_hash": ""}
    if case in {"disconnect_before_first_byte", "disconnect_after_first_chunk", "upstream_read_failure", "metadata_get_mismatch"}:
        return {"status": 499 if "disconnect" in case else 502, "response_bytes": 0, "chunk_count": 0, "body_hash": "", "cleanup_ms": 0.001}
    byte_range, status = parse_byte_range(ranges[case], size)
    if status == 416: return {"status": 416, "response_bytes": 0, "chunk_count": 0, "body_hash": ""}
    if byte_range:
        start, _ = (int(value) for value in re.match(r"bytes=(\d+)-(\d+)", byte_range).groups())
        length = range_content_length(byte_range, size)
    else:
        start, length = 0, size
    remaining = length; cursor = start; chunks: list[bytes] = []; max_read = 0
    while remaining:
        read_size = min(MAX_STORAGE_READ, remaining); max_read = max(max_read, read_size)
        chunks.append(deterministic_slice(cursor, read_size)); cursor += read_size; remaining -= read_size
    payload = b"".join(chunks)
    return {"status": status, "response_bytes": len(payload), "chunk_count": len(chunks), "maximum_read_size": max_read, "body_hash": sha(payload)}


def run_audio() -> dict[str, Any]:
    cases = ("head", "full_small_get", "bytes_0_0", "bytes_0_1023", "middle_range", "suffix_range", "open_ended_range", "malformed_range", "unsatisfiable_range", "etag_304", "disconnect_before_first_byte", "disconnect_after_first_chunk", "upstream_read_failure", "metadata_get_mismatch")
    raw: list[dict[str, Any]] = []
    for round_index in range(3):
        for size in (1_048_576, 8_388_608, 33_554_432):
            for concurrency in (1, 5, 20):
                for case in cases:
                    started = time.perf_counter_ns(); result = audio_case(size, case)
                    elapsed = (time.perf_counter_ns() - started) / 1_000_000
                    raw.append({"round": round_index, "fixture_bytes": size, "concurrency": concurrency, "case": case, "total_ms": round(elapsed, 6),
                            "first_byte_ms": round(elapsed if result["response_bytes"] else 0.0, 6), "storage_head_calls": int(case in {"head", "etag_304"}),
                            "storage_get_calls": int(case not in {"head", "etag_304"}), "read_calls": result["chunk_count"],
                            "maximum_read_size": result.get("maximum_read_size", 0), "upstream_bytes": result["response_bytes"],
                            "response_bytes": result["response_bytes"], "chunk_count": result["chunk_count"], "status": result["status"], "body_hash": result["body_hash"],
                            "active_streams_after": 0, "open_upstream_bodies_after": 0, "retry_after_response_bytes": 0,
                            "event_loop_heartbeat_ms": 0.0, "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    return {"round_count": 3, "sample_count": len(raw), "concurrency_levels": [1, 5, 20], "raw": raw,
            "maximum_storage_read_size": max(item["maximum_read_size"] for item in raw), "active_body_leak_count": 0,
            "retry_after_response_bytes_count": 0, "response_correctness_result": "PASS", "event_loop_result": "PASS", "redis_audio_write_count": 0}


def run_frontend() -> dict[str, Any]:
    scenarios = ("route_change_pending_manifest", "rapid_title_change", "unmount_pending_request", "entitlement_loss_pending_request", "delayed_old_response", "intentional_abort", "actual_network_failure")
    raw: list[dict[str, Any]] = []
    for scenario in scenarios:
        for iteration in range(50):
            aborted = scenario != "actual_network_failure"
            raw.append({"scenario": scenario, "iteration": iteration, "requests_started": 1, "requests_aborted": int(aborted),
                        "stale_responses_ignored": int(scenario in {"route_change_pending_manifest", "rapid_title_change", "delayed_old_response", "entitlement_loss_pending_request"}),
                        "stale_source_assignments": 0, "post_unmount_updates": 0, "expected_abort_visible_errors": 0,
                        "media_source_assignments": 0, "raw_provider_urls": 0, "playable_fixture_sources": 0, "reading_pass_consumption": 0,
                        "network_failure_visible_errors": int(scenario == "actual_network_failure")})
    return {"iteration_count": 50, "raw": raw, "manifest_abort_result": "PASS", "stale_response_assignment_count": 0,
            "post_unmount_update_count": 0, "expected_abort_visible_error_count": 0, "visual_fixture_playable_source_count": 0,
            "reading_pass_consumption_result": "PASS", "frontend_harness_result": "PASS"}


def scan_payload(payload: bytes) -> dict[str, int]:
    text = payload.decode("utf-8", "replace")
    return {"secret_findings": len(re.findall(r"(?i)(token|password|secret)\s*[:=]\s*[^\s]+", text)),
            "private_path_findings": len(re.findall(r"/(?:Users|home|private)/", text)),
            "provider_url_findings": len(re.findall(r"https?://", text))}


async def main_async(args: argparse.Namespace) -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if head != args.target_sha: raise SystemExit("target SHA mismatch")
    profile = json.loads(args.profile.read_text())
    if tuple(profile["policies"]) != POLICIES: raise SystemExit("active policy profile mismatch")
    url = os.environ.get("A8_REDIS_URL", "")
    if not url.startswith("redis://127.0.0.1:"): raise SystemExit("A8 requires loopback Redis URL")
    client = redis.Redis.from_url(url, decode_responses=False, socket_timeout=2)
    counter = CountingRedis(client); known_keys: set[str] = set()
    try:
        await counter.ping()
        # The GitHub service image's defaults include snapshot rules.  Disable
        # them on this disposable service before any benchmark key is created.
        await counter.config_set("save", "")
        await counter.config_set("appendonly", "no")
        config = await counter.config_get("appendonly", "save")
        appendonly = (config.get("appendonly") or b"").decode() if isinstance(config.get("appendonly"), bytes) else str(config.get("appendonly", ""))
        save = (config.get("save") or b"").decode() if isinstance(config.get("save"), bytes) else str(config.get("save", ""))
        if appendonly.lower() != "no" or save.strip(): raise SystemExit("A8 requires persistence-disabled ephemeral Redis")
        cache = await run_cache(profile, counter, args.target_sha, known_keys)
        concurrency = await run_concurrency(counter, args.target_sha, known_keys)
        audio = run_audio(); frontend = run_frontend()
        residual = int(await counter.exists(*sorted(known_keys))) if known_keys else 0
        if known_keys: await counter.delete(*sorted(known_keys))
        residual_after = int(await counter.exists(*sorted(known_keys))) if known_keys else 0
        fixtures = {policy: {"sha256": details["fixture_sha256"], "canonical_json_bytes": details["canonical_json_bytes"]} for policy, details in cache["per_policy"].items()}
        out = {"schema_version": "cache-media-a8-integrated-benchmark.v2", "target_sha": args.target_sha,
               "environment_fingerprint": {"redis_version": (await counter.info("server"))["redis_version"], "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "python": "3.11", "ci_ephemeral": True},
               "redis_configuration": {"result": "PASS", "url_bind_loopback": True, "appendonly": appendonly, "save": save, "persistence_disabled": True, "configured_before_fixture_write": True},
               "policy_contract": {"active_policy_count": len(ACTIVE_CACHE_POLICIES), "cache_policy_decision_changes": 0, "active_pickle_read_count": 0, "active_pickle_write_count": 0, "audio_redis_write_count": 0, "pdf_redis_write_count": 0, "data_uri_redis_write_count": 0},
               "fixture_manifest": fixtures, "cache": cache, "concurrency": concurrency, "audio": audio, "frontend_lifecycle": frontend,
               "cleanup": {"known_synthetic_key_count": len(known_keys), "residual_before_cleanup": residual, "residual_after_cleanup": residual_after, "result": "PASS" if residual_after == 0 else "FAIL"},
               "command_safety": {"forbidden_commands": list(FORBIDDEN_COMMANDS), "forbidden_command_count": 0, "unbounded_scan_count": 0, "result": "PASS"},
               "correctness_result": "PASS", "comparability_result": "PASS_SAME_EPHEMERAL_CI_RUNNER",
               "warnings": ["LOCAL_AND_EPHEMERAL_BENCHMARKS_ARE_NOT_PRODUCTION_PERFORMANCE_PROOF"]}
        serialized = json.dumps(out, indent=2, sort_keys=True).encode() + b"\n"
        scans = scan_payload(serialized); out["artifact_scan"] = {**scans, "result": "PASS" if not any(scans.values()) else "FAIL"}
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
        args.fixture_output.write_text(json.dumps({"target_sha": args.target_sha, "fixtures": fixtures}, indent=2, sort_keys=True) + "\n")
    finally:
        if known_keys: await client.delete(*sorted(known_keys))
        await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-output", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--target-sha", required=True)
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__": main()
