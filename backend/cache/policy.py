"""Current cache configuration and TTL policy; no A2 policy changes here."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Dict, Tuple


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


def _bounded_env_int(name: str, default: int, *, maximum: int) -> int:
    """Return a finite non-secret override, or the safe default on invalid input."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if 0 < value <= maximum else default


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
# A2's codec ceiling remains the hard safety ceiling.  A3 uses lower defaults
# derived from the largest synthetic A2 value (3,006 bytes), with room for
# current reader content without making Redis values unbounded.
A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES = 1_048_576
GLOBAL_MAX_UNCOMPRESSED_CACHE_BYTES = _bounded_env_int(
    "REDIS_CACHE_MAX_UNCOMPRESSED_BYTES", 262_144,
    maximum=A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES,
)
GLOBAL_MAX_STORED_CACHE_BYTES = _bounded_env_int(
    "REDIS_CACHE_MAX_STORED_BYTES", 270_336,
    maximum=A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES,
)
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


@dataclass(frozen=True)
class RegisteredCachePolicy:
    """One bounded policy for an active A2 v2 application-cache namespace."""

    policy_id: str
    namespace: str
    scope: str
    ttl_authority: str
    max_uncompressed_bytes: int
    max_stored_bytes: int
    authorization: str
    invalidation: str
    source_fallback: str
    metric_namespace: str
    negative_cache: bool = False
    compression: bool = True
    binary_media_prohibited: bool = True
    log_sampling: str = "errors_and_bypasses"

    def effective_limits(self) -> Tuple[int, int]:
        return (
            min(self.max_uncompressed_bytes, GLOBAL_MAX_UNCOMPRESSED_CACHE_BYTES),
            min(self.max_stored_bytes, GLOBAL_MAX_STORED_CACHE_BYTES),
        )


_POLICIES = (
    RegisteredCachePolicy("public-cache-v2", "public-cache", "public", "PUBLIC_CACHE_TTL_SECONDS", 131_072, 135_168, "public", "public generation", "source or in-process cache", "public-cache"),
    RegisteredCachePolicy("reader-content-v2", "reader-content", "resource", "READER_BOOK_CACHE_TTL_SECONDS/READER_CHAPTER_CACHE_TTL_SECONDS", 262_144, 270_336, "authorization before cache where protected", "reader generation", "source", "reader-content"),
    RegisteredCachePolicy("reader-manifest-v2", "reader-manifest", "resource", "READER_MANIFEST_CACHE_TTL_SECONDS", 131_072, 135_168, "authorization before cache", "resource/generation", "source", "reader-manifest"),
    RegisteredCachePolicy("user-private-v2", "user-private", "user", "USER_TRANSACTIONS_CACHE_TTL_SECONDS/USER_PAYMENT_INTENTS_CACHE_TTL_SECONDS", 65_536, 67_584, "authorization before cache", "targeted user invalidation", "database", "user-private"),
    RegisteredCachePolicy("user-doc-v2", "user-doc", "user", "USER_AUTH_CACHE_TTL_SECONDS", 16_384, 16_896, "caller-owned authenticated lookup", "targeted user invalidation", "database", "user_doc"),
    RegisteredCachePolicy("user-session-v2", "user-session", "session", "USER_SESSION_CACHE_TTL_SECONDS", 16_384, 16_896, "caller-owned session lookup", "targeted session invalidation", "database", "user_session"),
)
ACTIVE_CACHE_POLICIES: Dict[str, RegisteredCachePolicy] = {item.namespace: item for item in _POLICIES}
if len(ACTIVE_CACHE_POLICIES) != len(_POLICIES) or len({item.policy_id for item in _POLICIES}) != len(_POLICIES):
    raise RuntimeError("A3 cache policy registry contains duplicate namespace or policy ID")
for _policy in _POLICIES:
    _raw_limit, _stored_limit = _policy.effective_limits()
    if _raw_limit <= 0 or _stored_limit <= 0 or max(_raw_limit, _stored_limit) > A2_CODEC_ABSOLUTE_DECODE_LIMIT_BYTES:
        raise RuntimeError("A3 cache policy registry contains an invalid bounded limit")
    if not _policy.binary_media_prohibited:
        raise RuntimeError("A3 cache policy cannot allow binary/media values")


def resolve_active_policy(namespace: str) -> RegisteredCachePolicy:
    try:
        return ACTIVE_CACHE_POLICIES[namespace]
    except KeyError as exc:
        raise ValueError("unknown active cache namespace") from exc


def active_policy_status() -> dict:
    return {
        "schema_version": "v2",
        "process_scope": "process_local",
        "active_policy_count": len(_POLICIES),
        "global_limits": {
            "max_uncompressed_bytes": GLOBAL_MAX_UNCOMPRESSED_CACHE_BYTES,
            "max_stored_bytes": GLOBAL_MAX_STORED_CACHE_BYTES,
        },
        "policies": [
            {
                "id": item.policy_id,
                "namespace": item.namespace,
                "scope": item.scope,
                "max_uncompressed_bytes": item.effective_limits()[0],
                "max_stored_bytes": item.effective_limits()[1],
                "ttl_authority": item.ttl_authority,
            }
            for item in _POLICIES
        ],
    }


def ttl_with_jitter(ttl_seconds: int, *, jitter_seconds: int = REDIS_CACHE_TTL_JITTER_SECONDS) -> int:
    ttl = int(ttl_seconds or 0)
    if ttl <= 0:
        return ttl
    jitter = min(max(0, jitter_seconds), max(0, ttl // 5))
    if jitter <= 0:
        return ttl
    return ttl + secrets.randbelow(jitter + 1)
