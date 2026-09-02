"""Versioned safe JSON cache-aside store using the shared Redis runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional


@dataclass(frozen=True)
class CachePolicy:
    namespace: str
    scope: str
    ttl_seconds: int
    metrics_namespace: Optional[str] = None


@dataclass(frozen=True)
class CacheIdentity:
    identity: str
    resource: str
    version: str = ""


class RedisCacheStore:
    def __init__(self, *, client_provider: Callable[[], Any], enabled_provider: Callable[[], bool], key_builder: Callable[[CachePolicy, CacheIdentity], str], encoder: Callable[[Any], bytes], decoder: Callable[[bytes], Any], stats: dict[str, int], logger: Any):
        self._client_provider, self._enabled_provider = client_provider, enabled_provider
        self._key_builder, self._encoder, self._decoder = key_builder, encoder, decoder
        self._stats, self._logger = stats, logger

    def _increment(self, policy: CachePolicy, suffix: str) -> None:
        namespace = policy.namespace if policy.metrics_namespace is None else policy.metrics_namespace
        if namespace:
            self._stats[f"{namespace}_{suffix}"] += 1

    async def get(self, policy: CachePolicy, identity: CacheIdentity) -> Any:
        if not self._enabled_provider():
            self._increment(policy, "miss")
            return None
        redis_key = self._key_builder(policy, identity)
        try:
            blob = await self._client_provider().get(redis_key)
        except Exception:
            self._increment(policy, "error")
            return None
        if not blob:
            self._increment(policy, "miss")
            return None
        try:
            value = self._decoder(blob)
        except Exception:
            self._increment(policy, "error")
            try:
                await self._client_provider().delete(redis_key)
            except Exception:
                pass
            return None
        self._increment(policy, "hit")
        return value

    async def set(self, policy: CachePolicy, identity: CacheIdentity, value: Any) -> None:
        if policy.ttl_seconds <= 0 or not self._enabled_provider():
            return
        try:
            payload = self._encoder(value)
            await self._client_provider().setex(self._key_builder(policy, identity), policy.ttl_seconds, payload)
        except Exception:
            self._increment(policy, "error")

    async def delete(self, policy: CachePolicy, identity: CacheIdentity) -> None:
        if not self._enabled_provider():
            return
        try:
            await self._client_provider().delete(self._key_builder(policy, identity))
        except Exception:
            self._increment(policy, "error")

    async def cache_aside(self, policy: CachePolicy, identity: CacheIdentity, loader: Callable[[], Awaitable[Any]]) -> Any:
        cached = await self.get(policy, identity)
        if cached is not None:
            return cached
        value = await loader()
        await self.set(policy, identity, value)
        return value
