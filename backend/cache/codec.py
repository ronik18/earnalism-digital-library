"""Current pickle/zlib cache codec preserved verbatim for A1.1 parity."""

from __future__ import annotations

import io
import pickle
import re
import zlib
from typing import Any, Iterable, Optional


MEDIA_DATA_URI_RE = re.compile(
    r"data:(?:image|audio|video|application/octet-stream|application/pdf)/",
    re.IGNORECASE,
)


def redis_cache_payload_is_media(value: Any, *, response_types: Iterable[type] = (), _seen: int = 0) -> bool:
    if _seen > 800:
        return False
    if isinstance(value, (bytes, bytearray, memoryview, io.IOBase, *tuple(response_types))):
        return True
    if isinstance(value, str):
        return bool(MEDIA_DATA_URI_RE.search(value))
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key).lower()
            if isinstance(nested, (bytes, bytearray, memoryview, io.IOBase)):
                return True
            if isinstance(nested, str) and key_text in {"body", "blob", "bytes", "binary", "file", "stream", "content"} and MEDIA_DATA_URI_RE.search(nested):
                return True
            if redis_cache_payload_is_media(nested, response_types=response_types, _seen=_seen + 1):
                return True
        return False
    if isinstance(value, (list, tuple, set)):
        return any(redis_cache_payload_is_media(item, response_types=response_types, _seen=_seen + 1) for item in value)
    return False


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


def encode_for_redis(namespace: str, value: Any, *, compress_min_bytes: int, response_types: Iterable[type] = ()) -> Optional[bytes]:
    if redis_cache_payload_is_media(value, response_types=response_types):
        return None
    return encode(value, compress_min_bytes=compress_min_bytes)
