"""Versioned safe JSON cache-aside store using the shared Redis runtime."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from time import monotonic
from typing import Any, Awaitable, Callable, Optional

from . import metrics as cache_metrics
from .singleflight import DEFAULT_SINGLEFLIGHT, SingleFlight


@dataclass(frozen=True)
class CachePolicy:
    namespace: str
    scope: str
    ttl_seconds: int
    metrics_namespace: Optional[str] = None
    registered: Any = None


@dataclass(frozen=True)
class CacheIdentity:
    identity: str
    resource: str
    version: str = ""


class RedisCacheStore:
    def __init__(self, *, client_provider: Callable[[], Any], enabled_provider: Callable[[], bool], key_builder: Callable[[CachePolicy, CacheIdentity], str], encoder: Callable[[Any], bytes], decoder: Callable[[bytes], Any], stats: dict[str, int], logger: Any, canonical_encoder: Optional[Callable[[Any], bytes]] = None, canonical_decoder: Optional[Callable[[bytes], tuple[Any, bytes]]] = None, singleflight: SingleFlight = DEFAULT_SINGLEFLIGHT):
        self._client_provider, self._enabled_provider = client_provider, enabled_provider
        self._key_builder, self._encoder, self._decoder = key_builder, encoder, decoder
        self._stats, self._logger = stats, logger
        self._canonical_encoder = canonical_encoder
        self._canonical_decoder = canonical_decoder
        self._singleflight = singleflight

    def _increment(self, policy: CachePolicy, suffix: str) -> None:
        namespace = policy.namespace if policy.metrics_namespace is None else policy.metrics_namespace
        if namespace:
            self._stats[f"{namespace}_{suffix}"] += 1

    def _event(self, policy: CachePolicy, operation: str, result: str, *, started: Optional[float] = None, size_bytes: Optional[int] = None, legacy_suffix: Optional[str] = None) -> None:
        if legacy_suffix:
            self._increment(policy, legacy_suffix)
        definition = policy.registered
        cache_metrics.record(
            getattr(definition, "policy_id", policy.namespace), operation, result,
            latency_ms=(monotonic() - started) * 1000 if started is not None else None,
            size_bytes=size_bytes,
        )

    def _log(self, level: str, policy: CachePolicy, operation: str, result: str, *, size_bytes: Optional[int] = None, exc: Optional[BaseException] = None) -> None:
        if self._logger is None:
            return
        event = {"event": "cache_v2", "policy_id": getattr(policy.registered, "policy_id", policy.namespace), "namespace": policy.namespace, "operation": operation, "result": result, "schema_version": "v2"}
        if size_bytes is not None:
            event["size_bucket"] = cache_metrics.bucket(size_bytes, cache_metrics.SIZE_BUCKETS_BYTES)
        if exc is not None:
            event["exception_class"] = exc.__class__.__name__
        try:
            getattr(self._logger, level)("cache_event=%s", event)
        except Exception:
            pass

    def _limits(self, policy: CachePolicy) -> Optional[tuple[int, int]]:
        return policy.registered.effective_limits() if policy.registered is not None else None

    async def _delete_exact(self, policy: CachePolicy, identity: CacheIdentity) -> None:
        try:
            await self._client_provider().delete(self._key_builder(policy, identity))
            self._event(policy, "delete", "exact_key_cleanup", legacy_suffix="exact_key_cleanup")
        except Exception as exc:
            self._event(policy, "delete", "error", legacy_suffix="error")
            self._log("warning", policy, "delete", "error", exc=exc)

    async def get(self, policy: CachePolicy, identity: CacheIdentity) -> Any:
        started = monotonic()
        if not self._enabled_provider():
            self._event(policy, "read", "cache_disabled", started=started, legacy_suffix="miss")
            return None
        redis_key = self._key_builder(policy, identity)
        try:
            blob = await self._client_provider().get(redis_key)
        except Exception as exc:
            self._event(policy, "read", "redis_error", started=started, legacy_suffix="error")
            self._log("warning", policy, "read", "redis_error", exc=exc)
            return None
        if not blob:
            self._event(policy, "read", "miss", started=started, legacy_suffix="miss")
            return None
        limits = self._limits(policy)
        if limits is not None and len(blob) > limits[1]:
            self._event(policy, "read", "oversized_stored", started=started, size_bytes=len(blob), legacy_suffix="error")
            self._log("warning", policy, "read", "oversized_stored", size_bytes=len(blob))
            await self._delete_exact(policy, identity)
            return None
        try:
            if self._canonical_decoder is not None:
                value, canonical = self._canonical_decoder(blob)
            else:
                value, canonical = self._decoder(blob), b""
            if limits is not None and len(canonical) > limits[0]:
                self._event(policy, "read", "oversized_decoded", started=started, size_bytes=len(canonical), legacy_suffix="error")
                self._log("warning", policy, "read", "oversized_decoded", size_bytes=len(canonical))
                await self._delete_exact(policy, identity)
                return None
        except Exception as exc:
            self._event(policy, "read", "decode_error", started=started, legacy_suffix="error")
            self._log("warning", policy, "read", "decode_error", exc=exc)
            await self._delete_exact(policy, identity)
            return None
        self._event(policy, "read", "hit", started=started, size_bytes=len(blob), legacy_suffix="hit")
        return value

    async def set(self, policy: CachePolicy, identity: CacheIdentity, value: Any) -> None:
        started = monotonic()
        if policy.ttl_seconds <= 0 or not self._enabled_provider():
            self._event(policy, "write", "cache_disabled", started=started)
            return
        try:
            canonical = self._canonical_encoder(value) if self._canonical_encoder is not None else b""
        except Exception as exc:
            message = str(exc).lower()
            result = "binary_or_media" if "binary or media" in message else "unsupported_value_type" if "unsupported" in message else "serialization_error"
            self._event(policy, "write", result, started=started)
            self._log("info", policy, "write", result, exc=exc)
            return
        limits = self._limits(policy)
        if limits is not None and len(canonical) > limits[0]:
            self._event(policy, "write", "oversized_uncompressed", started=started, size_bytes=len(canonical))
            self._log("info", policy, "write", "oversized_uncompressed", size_bytes=len(canonical))
            return
        try:
            payload = self._encoder(value) if self._canonical_encoder is None else self._encoder(canonical)
            if limits is not None and len(payload) > limits[1]:
                self._event(policy, "write", "oversized_stored", started=started, size_bytes=len(payload))
                self._log("info", policy, "write", "oversized_stored", size_bytes=len(payload))
                return
            await self._client_provider().setex(self._key_builder(policy, identity), policy.ttl_seconds, payload)
            self._event(policy, "write", "success", started=started, size_bytes=len(payload))
        except Exception as exc:
            self._event(policy, "write", "redis_error", started=started)
            self._log("warning", policy, "write", "redis_error", exc=exc)

    async def delete(self, policy: CachePolicy, identity: CacheIdentity) -> None:
        if not self._enabled_provider():
            return
        try:
            await self._client_provider().delete(self._key_builder(policy, identity))
            self._event(policy, "delete", "exact_key_delete", legacy_suffix="exact_key_delete")
        except Exception as exc:
            self._event(policy, "delete", "error", legacy_suffix="error")
            self._log("warning", policy, "delete", "error", exc=exc)

    async def cache_aside(self, policy: CachePolicy, identity: CacheIdentity, loader: Callable[[], Awaitable[Any]], *, version_resolver: Optional[Callable[[], Awaitable[str]]] = None) -> Any:
        started = monotonic()
        cached = await self.get(policy, identity)
        if cached is not None:
            self._event(policy, "cache_aside", "hit", started=started)
            return cached

        async def coherent_loader() -> Any:
            before = await version_resolver() if version_resolver is not None else identity.version
            try:
                value = await loader()
            except Exception:
                self._event(policy, "cache_aside", "source_loader_error", started=started)
                raise
            after = await version_resolver() if version_resolver is not None else before
            self._event(policy, "cache_aside", "source_loader", started=started)
            if before != after:
                self._event(policy, "cache_aside", "stale_fill_suppressed", started=started)
                self._log("warning", policy, "cache_aside", "stale_fill_suppressed")
                return value
            await self.set(policy, identity, value)
            return value

        internal = hashlib.sha256(
            f"{getattr(policy.registered, 'policy_id', policy.namespace)}:{self._key_builder(policy, identity)}:{identity.version}".encode("utf-8")
        ).hexdigest()
        value, role = await self._singleflight.run(internal, coherent_loader)
        self._event(policy, "coalescing", role, started=started)
        self._event(policy, "cache_aside", "miss", started=started)
        return value
