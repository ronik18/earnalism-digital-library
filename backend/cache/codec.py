"""Deterministic, versioned JSON codec for active application-cache values."""

from __future__ import annotations

import io
import datetime as dt
import json
import math
import re
import uuid
import zlib
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Optional


MEDIA_DATA_URI_RE = re.compile(
    r"data:(?:image|audio|video|application/octet-stream|application/pdf)/",
    re.IGNORECASE,
)
JSON_V2_PREFIX = b"json-v2:"
ZLIB_JSON_V2_PREFIX = b"zlib-json-v2:"
A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES = 1048576
A2_CODEC_MAX_NESTING = 64


class CacheCodecError(ValueError):
    pass


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


def _normalize(value: Any, depth: int = 0) -> Any:
    if depth > A2_CODEC_MAX_NESTING:
        raise CacheCodecError("cache value nesting exceeds the A2 safety ceiling")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CacheCodecError("cache JSON does not allow non-finite floats")
        return value
    if isinstance(value, dt.datetime):
        return {"$cache_type": "datetime", "value": value.isoformat()}
    if isinstance(value, dt.date):
        return {"$cache_type": "date", "value": value.isoformat()}
    if isinstance(value, uuid.UUID):
        return {"$cache_type": "uuid", "value": str(value)}
    if isinstance(value, Decimal):
        return {"$cache_type": "decimal", "value": str(value)}
    if value.__class__.__name__ == "ObjectId" and value.__class__.__module__ == "bson.objectid":
        return {"$cache_type": "objectid", "value": str(value)}
    if isinstance(value, Enum):
        raise CacheCodecError("enum cache values require a namespace adapter")
    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="json"), depth + 1)
    if hasattr(value, "dict") and value.__class__.__module__.startswith("pydantic"):
        return _normalize(value.dict(), depth + 1)
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise CacheCodecError("cache dictionaries require string keys")
        return {key: _normalize(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item, depth + 1) for item in value]
    raise CacheCodecError(f"unsupported cache value type: {type(value).__name__}")


def _restore(value: Any, depth: int = 0) -> Any:
    if depth > A2_CODEC_MAX_NESTING:
        raise CacheCodecError("cache value nesting exceeds the A2 safety ceiling")
    if isinstance(value, list):
        return [_restore(item, depth + 1) for item in value]
    if not isinstance(value, dict):
        return value
    type_tag = value.get("$cache_type")
    if type_tag is not None:
        if set(value) != {"$cache_type", "value"} or not isinstance(value["value"], str):
            raise CacheCodecError("invalid typed cache envelope")
        raw = value["value"]
        if type_tag == "datetime":
            return dt.datetime.fromisoformat(raw)
        if type_tag == "date":
            return dt.date.fromisoformat(raw)
        if type_tag == "uuid":
            return uuid.UUID(raw)
        if type_tag == "decimal":
            return Decimal(raw)
        if type_tag == "objectid":
            try:
                from bson.objectid import ObjectId
                return ObjectId(raw)
            except Exception as exc:
                raise CacheCodecError("invalid ObjectId cache envelope") from exc
        raise CacheCodecError("unsupported cache type tag")
    return {key: _restore(item, depth + 1) for key, item in value.items()}


def encode_v2(value: Any, *, compress_min_bytes: int) -> bytes:
    if redis_cache_payload_is_media(value):
        raise CacheCodecError("binary or media value is not cacheable")
    raw = canonical_json_bytes(value)
    return encode_v2_canonical(raw, compress_min_bytes=compress_min_bytes)


def canonical_json_bytes(value: Any) -> bytes:
    """Encode a validated logical cache value without an envelope."""
    if redis_cache_payload_is_media(value):
        raise CacheCodecError("binary or media value is not cacheable")
    normalized = _normalize(value)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def encode_v2_canonical(raw: bytes, *, compress_min_bytes: int) -> bytes:
    """Envelope already canonical JSON bytes after policy measurement."""
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CacheCodecError("invalid canonical JSON cache payload") from exc
    if not isinstance(parsed, (dict, list, str, int, float, bool)) and parsed is not None:
        raise CacheCodecError("unexpected cache top-level type")
    if len(raw) >= compress_min_bytes:
        return ZLIB_JSON_V2_PREFIX + zlib.compress(raw, level=6)
    return JSON_V2_PREFIX + raw


def _decompress_limited(payload: bytes) -> bytes:
    try:
        decompressor = zlib.decompressobj()
        raw = decompressor.decompress(payload, A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES + 1)
        if len(raw) > A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES or decompressor.unconsumed_tail:
            raise CacheCodecError("cache payload exceeds the A2 decode safety ceiling")
        raw += decompressor.flush(A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES + 1 - len(raw))
    except zlib.error as exc:
        raise CacheCodecError("invalid compressed cache payload") from exc
    if len(raw) > A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES or decompressor.unused_data or not decompressor.eof:
        raise CacheCodecError("invalid or trailing compressed cache payload")
    return raw


def decode_v2(blob: bytes) -> Any:
    if blob.startswith(JSON_V2_PREFIX):
        raw = blob[len(JSON_V2_PREFIX):]
    elif blob.startswith(ZLIB_JSON_V2_PREFIX):
        raw = _decompress_limited(blob[len(ZLIB_JSON_V2_PREFIX):])
    else:
        raise CacheCodecError("unknown cache envelope")
    if len(raw) > A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES:
        raise CacheCodecError("cache payload exceeds the A2 decode safety ceiling")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CacheCodecError("invalid JSON cache payload") from exc
    if not isinstance(parsed, (dict, list, str, int, float, bool)) and parsed is not None:
        raise CacheCodecError("unexpected cache top-level type")
    return _restore(parsed)


def decoded_canonical_json_bytes(blob: bytes) -> tuple[Any, bytes]:
    """Return decoded value and its canonical bytes for A3 read enforcement."""
    value = decode_v2(blob)
    return value, canonical_json_bytes(value)


def encode_for_redis(namespace: str, value: Any, *, compress_min_bytes: int, response_types: Iterable[type] = ()) -> Optional[bytes]:
    if redis_cache_payload_is_media(value, response_types=response_types):
        return None
    return encode_v2(value, compress_min_bytes=compress_min_bytes)
