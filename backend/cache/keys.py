"""Stable current Redis key construction helpers."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def redis_key(prefix: str, *parts: str) -> str:
    cleaned = [re.sub(r"[^a-zA-Z0-9_.:-]", "_", str(part)) for part in parts if str(part)]
    return ":".join([prefix, *cleaned])


def cache_digest_key(prefix: str, namespace: str, key: str) -> str:
    return redis_key(prefix, "cache", namespace, hashlib.sha256(key.encode("utf-8")).hexdigest())


def public_cache_storage_key(prefix: str, generation: int, key: str) -> str:
    return redis_key(prefix, "public-cache", str(generation), hashlib.sha256(key.encode("utf-8")).hexdigest())


def public_cache_key(scope: str, *, truth_gate: str, catalog_truth: str, **params: Any) -> str:
    payload = {"truth_gate": truth_gate, "catalog_truth": catalog_truth, **params}
    return f"{scope}:{json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)}"
