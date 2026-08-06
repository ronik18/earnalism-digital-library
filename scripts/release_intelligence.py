#!/usr/bin/env python3
"""Conservative learning and governance primitives for release repair."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


SAFE_REPAIR_CHECKS = {
    "audio_artifacts",
    "synchronization",
    "checksums",
    "staging",
    "browser",
    "production",
}
MAX_ATTEMPTS = 3


def validate_strategy(check: str, strategy: dict[str, Any]) -> None:
    if check not in SAFE_REPAIR_CHECKS:
        raise ValueError(f"repair scope is not self-healable: {check}")
    if str(strategy.get("failure_class", "")).upper() != "TRANSIENT":
        raise ValueError("only TRANSIENT repair strategies may be retried")
    if int(strategy.get("attempt_limit", MAX_ATTEMPTS)) > MAX_ATTEMPTS:
        raise ValueError("repair attempt limit cannot exceed three")
    if any(strategy.get(field) is True for field in ("changes_rights", "approves_human_gate", "lowers_thresholds")):
        raise ValueError("repair strategy cannot alter rights, approvals, or quality thresholds")


def read_learning_ledger(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def rank_strategies(check: str, strategies: list[dict[str, Any]], ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer verified success, then lower measured cost/latency, stably."""
    stats: dict[str, dict[str, float]] = {}
    for row in ledger:
        if row.get("check") != check:
            continue
        key = str(row.get("strategy") or "")
        current = stats.setdefault(key, {"success": 0, "failure": 0, "cost": 0, "latency": 0})
        if row.get("outcome") == "PASS":
            current["success"] += 1
        else:
            current["failure"] += 1
        current["cost"] += float(row.get("cost_usd") or 0)
        current["latency"] += float(row.get("latency_ms") or 0)

    indexed = list(enumerate(strategies))
    indexed.sort(
        key=lambda pair: (
            -stats.get(str(pair[1].get("id")), {}).get("success", 0),
            stats.get(str(pair[1].get("id")), {}).get("failure", 0),
            stats.get(str(pair[1].get("id")), {}).get("cost", 0),
            stats.get(str(pair[1].get("id")), {}).get("latency", 0),
            pair[0],
        )
    )
    return [strategy for _, strategy in indexed]


def record_learning(path: Path | None, *, check: str, strategy: str, outcome: str, result: dict[str, Any] | None = None) -> None:
    """Persist only operational outcomes, never source text or approval evidence."""
    if path is None:
        return
    row = {
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "check": check,
        "strategy": strategy,
        "outcome": outcome,
        "cost_usd": float((result or {}).get("cost_usd") or 0),
        "latency_ms": float((result or {}).get("latency_ms") or 0),
        "reused_artifacts": bool((result or {}).get("reused_artifacts")),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
