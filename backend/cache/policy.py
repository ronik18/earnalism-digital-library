"""Current cache configuration and TTL policy; no A2 policy changes here."""

from __future__ import annotations

import os
import secrets


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float, minimum: float = 0.1) -> float:
    try:
        return max(minimum, float(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


MULTI_REPLICA_ENABLED = _env_bool("MULTI_REPLICA_ENABLED", False)
REDIS_URL = os.environ.get("REDIS_URL", "").strip()
REDIS_KEY_PREFIX = os.environ.get("REDIS_KEY_PREFIX", "earnalism").strip() or "earnalism"
REDIS_CACHE_ENABLED = _env_bool("REDIS_CACHE_ENABLED", bool(REDIS_URL) or MULTI_REPLICA_ENABLED)
REDIS_CACHE_FAIL_FAST = _env_bool("REDIS_CACHE_FAIL_FAST", MULTI_REPLICA_ENABLED)
REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS = _env_float("REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS", 2.0)
REDIS_SOCKET_TIMEOUT_SECONDS = _env_float("REDIS_SOCKET_TIMEOUT_SECONDS", 2.0)
REDIS_CACHE_COMPRESS_MIN_BYTES = _env_int("REDIS_CACHE_COMPRESS_MIN_BYTES", 4096)
REDIS_CACHE_TTL_JITTER_SECONDS = _env_int("REDIS_CACHE_TTL_JITTER_SECONDS", 30, minimum=0)
REDIS_CONFIGURE_ON_STARTUP = _env_bool("REDIS_CONFIGURE_ON_STARTUP", False)
REDIS_MAXMEMORY = os.environ.get("REDIS_MAXMEMORY", "").strip()
REDIS_MAXMEMORY_POLICY = os.environ.get("REDIS_MAXMEMORY_POLICY", "volatile-lfu").strip()
USER_AUTH_CACHE_TTL_SECONDS = _env_int("USER_AUTH_CACHE_TTL_SECONDS", 20)
USER_SESSION_CACHE_TTL_SECONDS = _env_int("USER_SESSION_CACHE_TTL_SECONDS", 20)
USER_WALLET_CACHE_TTL_SECONDS = _env_int("USER_WALLET_CACHE_TTL_SECONDS", 8)
USER_TRANSACTIONS_CACHE_TTL_SECONDS = _env_int("USER_TRANSACTIONS_CACHE_TTL_SECONDS", 20)
USER_PAYMENT_INTENTS_CACHE_TTL_SECONDS = _env_int("USER_PAYMENT_INTENTS_CACHE_TTL_SECONDS", 15)
READER_MANIFEST_CACHE_TTL_SECONDS = _env_int("READER_MANIFEST_CACHE_TTL_SECONDS", 1800)
READER_BOOK_CACHE_TTL_SECONDS = _env_int("READER_BOOK_CACHE_TTL_SECONDS", 900)
READER_CHAPTER_CACHE_TTL_SECONDS = _env_int("READER_CHAPTER_CACHE_TTL_SECONDS", 3600)

REDIS_CACHE_ALLOWED_PAYLOADS = (
    "metadata", "reader_manifests", "chapter_text", "short_lived_user_state",
    "session_state", "payment_state", "rate_limit_state", "reader_rum_aggregates",
)
REDIS_CACHE_EXCLUDED_PAYLOADS = (
    "book_cover_image_binaries", "audiobook_binaries", "video_binaries",
    "file_upload_streams", "response_objects", "inline_media_data_uris",
)


def ttl_with_jitter(ttl_seconds: int, *, jitter_seconds: int = REDIS_CACHE_TTL_JITTER_SECONDS) -> int:
    ttl = int(ttl_seconds or 0)
    if ttl <= 0:
        return ttl
    jitter = min(max(0, jitter_seconds), max(0, ttl // 5))
    if jitter <= 0:
        return ttl
    return ttl + secrets.randbelow(jitter + 1)
