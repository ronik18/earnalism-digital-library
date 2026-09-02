"""A1 characterization-only legacy pickle codec; never use for active cache I/O."""

from __future__ import annotations

import pickle
import zlib
from typing import Any


def encode(value: Any, *, compress_min_bytes: int) -> bytes:
    blob = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    if len(blob) >= compress_min_bytes:
        return b"z:" + zlib.compress(blob, level=6)
    return b"p:" + blob


def decode(blob: bytes) -> Any:
    if blob.startswith(b"z:"):
        return pickle.loads(zlib.decompress(blob[2:]))
    if blob.startswith(b"p:"):
        return pickle.loads(blob[2:])
    return pickle.loads(blob)
