"""Bounded process-local cache metrics; never a cluster-global claim."""

from __future__ import annotations

from collections import Counter, defaultdict
from time import monotonic
from typing import Dict


cache_stats: Dict[str, int] = defaultdict(int)
LATENCY_BUCKETS_MS = (1, 5, 20, 100, 500, 2_000)
SIZE_BUCKETS_BYTES = (256, 1_024, 4_096, 16_384, 65_536, 262_144)
_v2_events: Counter[tuple[str, str, str, str]] = Counter()
_v2_started_at = monotonic()


def bucket(value: float, boundaries: tuple[int, ...]) -> str:
    for boundary in boundaries:
        if value <= boundary:
            return f"le_{boundary}"
    return "gt_max"


def record(policy_id: str, operation: str, result: str, *, latency_ms: float | None = None, size_bytes: int | None = None) -> None:
    """Best-effort fixed-cardinality metric recording that cannot affect requests."""
    try:
        _v2_events[(policy_id, operation, result, "count")] += 1
        if latency_ms is not None:
            _v2_events[(policy_id, operation, "latency", bucket(latency_ms, LATENCY_BUCKETS_MS))] += 1
        if size_bytes is not None:
            _v2_events[(policy_id, operation, "size", bucket(size_bytes, SIZE_BUCKETS_BYTES))] += 1
    except Exception:
        pass


def snapshot() -> dict[str, int]:
    return dict(cache_stats)


def snapshot_v2() -> dict:
    return {
        "scope": "process_local",
        "started_monotonic_seconds": round(_v2_started_at, 3),
        "latency_buckets_ms": list(LATENCY_BUCKETS_MS),
        "size_buckets_bytes": list(SIZE_BUCKETS_BYTES),
        "events": [
            {"policy_id": policy_id, "operation": operation, "result": result, "bucket": bucket_name, "count": count}
            for (policy_id, operation, result, bucket_name), count in sorted(_v2_events.items())
        ],
    }
