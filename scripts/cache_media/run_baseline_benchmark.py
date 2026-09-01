#!/usr/bin/env python3
"""Local-only baseline benchmark for current range parsing and streaming helpers.

No network, credentials, object-storage client, or production endpoint is used.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_benchmark")
os.environ.setdefault("JWT_SECRET", "local-cache-media-benchmark-only")

from backend import server  # noqa: E402


def percentile(samples: list[float], fraction: float) -> float:
    ordered = sorted(samples)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def rss_bytes() -> int | None:
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value * (1 if sys.platform == "darwin" else 1024))
    except Exception:
        return None


def stream_fixture(size: int, requested_range: str) -> dict:
    blob = b"a" * size
    started = time.perf_counter_ns()
    byte_range, status = server._parse_byte_range(requested_range, size)
    if status == 416:
        body_bytes = 0
    else:
        start, end = (0, size - 1)
        if byte_range:
            start, end = (int(part) for part in byte_range.removeprefix("bytes=").split("-"))
        body = io.BytesIO(blob[start : end + 1])
        body_bytes = sum(len(chunk) for chunk in server._streaming_body_iterator(body))
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return {"status": status, "response_bytes": body_bytes, "latency_ms": elapsed_ms}


def run_case(size: int, requested_range: str, concurrency: int) -> dict:
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(lambda _: stream_fixture(size, requested_range), range(concurrency)))
    latencies = [entry["latency_ms"] for entry in results]
    return {
        "fixture_bytes": size,
        "request": requested_range or "full",
        "concurrency": concurrency,
        "status_codes": sorted({entry["status"] for entry in results}),
        "response_bytes": results[0]["response_bytes"],
        "latency_ms": {"p50": percentile(latencies, 0.5), "p95": percentile(latencies, 0.95), "max": max(latencies)},
        "application_bytes_buffered": min(size, 1024 * 1024),
        "upstream_bytes_read": results[0]["response_bytes"],
        "cancellation_behavior": "NOT_EXERCISED_BY_SYNTHETIC_ITERATOR",
        "event_loop_indicator": "NOT_MEASURED: helper is synchronous generator used by StreamingResponse",
    }


def markdown(payload: dict) -> str:
    lines = ["# Cache and Media Local Baseline Benchmark", "", "Local synthetic evidence only; it is not production traffic or a performance-improvement claim.", "", "| Fixture | Request | Concurrency | Status | p50 ms | p95 ms | Max ms | Response bytes |", "|---|---|---:|---|---:|---:|---:|---:|"]
    for result in payload["audio_cases"]:
        metrics = result["latency_ms"]
        lines.append(f"| {result['fixture_bytes']} | {result['request']} | {result['concurrency']} | {','.join(map(str, result['status_codes']))} | {metrics['p50']:.3f} | {metrics['p95']:.3f} | {metrics['max']:.3f} | {result['response_bytes']} |")
    lines.extend(["", "## Scope", "", "- Current helpers: `backend/server.py:_parse_byte_range` and `_streaming_body_iterator`.", "- Fixtures: in-memory 4 KiB and 8 MiB deterministic byte objects.", "- No B2, Redis, Railway, network, credentials, or production HTTP was invoked.", "- RSS values are process high-water marks, not a per-request allocation profile.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    before = rss_bytes()
    cases = []
    for size in (4 * 1024, 8 * 1024 * 1024):
        for request in ("", "bytes=0-1023", "bytes=4194304-4195327", "bytes=999999999-"):
            for concurrency in (1, 5, 20):
                cases.append(run_case(size, request, concurrency))
    payload = {
        "schema_version": "cache-media-local-baseline.v1",
        "classification": "LOCAL_SYNTHETIC_BASELINE_ONLY",
        "audio_cases": cases,
        "redis_cache": {"status": "NOT_BENCHMARKED", "reason": "No local Redis service or production Redis access was used."},
        "pdf": {"status": "NOT_APPLICABLE", "reason": "No active customer PDF delivery route discovered."},
        "rss_bytes": {"before": before, "peak_or_after": rss_bytes(), "note": "platform high-water mark when available"},
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.write_text(markdown(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
