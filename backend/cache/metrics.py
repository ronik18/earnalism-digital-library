"""Existing in-process cache counters."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict


cache_stats: Dict[str, int] = defaultdict(int)


def snapshot() -> dict[str, int]:
    return dict(cache_stats)
