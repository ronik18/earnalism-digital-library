"""One process-shared Redis client with current startup semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class RedisRuntime:
    client: Any = None
    available: bool = False
    config_status: dict[str, Any] = field(default_factory=dict)
    initialize_calls: int = 0
    close_calls: int = 0


runtime = RedisRuntime()


def active_client() -> Any:
    return runtime.client



def is_available() -> bool:
    return bool(runtime.available and runtime.client is not None)


async def configure_cache_policy(*, configure_on_startup: bool, maxmemory: str, maxmemory_policy: str, logger: Any) -> None:
    status = runtime.config_status
    status.clear()
    status.update({"attempted": False, "applied": {}, "errors": {}})
    if not configure_on_startup or runtime.client is None:
        return
    status["attempted"] = True
    pairs: dict[str, str] = {}
    if maxmemory:
        pairs["maxmemory"] = maxmemory
    if maxmemory_policy:
        pairs["maxmemory-policy"] = maxmemory_policy
    for name, value in pairs.items():
        try:
            await runtime.client.config_set(name, value)
            status["applied"][name] = value
        except Exception as exc:
            status["errors"][name] = str(exc)[:240]
            logger.warning("Redis CONFIG SET %s failed; continuing with provider defaults.", name, exc_info=True)


async def initialize(*, enabled: bool, multi_replica_enabled: bool, redis_url: str, fail_fast: bool, connect_timeout: float, socket_timeout: float, configure_on_startup: bool, maxmemory: str, maxmemory_policy: str, logger: Any, redis_factory: Optional[Callable[..., Any]] = None) -> None:
    if runtime.client is not None and runtime.available:
        return
    runtime.initialize_calls += 1
    if not enabled and not multi_replica_enabled:
        logger.info("Redis cache/state disabled; using per-process local cache and rate-limit state.")
        return
    if not redis_url:
        message = "REDIS_URL is required for shared Redis cache/state."
        if fail_fast or multi_replica_enabled:
            raise RuntimeError(message)
        logger.warning("%s Continuing without Redis.", message)
        return
    if redis_factory is None:
        try:
            import redis.asyncio as redis  # type: ignore
            redis_factory = redis.from_url
        except Exception as exc:
            message = "Redis cache/state requires the redis Python package."
            if fail_fast or multi_replica_enabled:
                raise RuntimeError(message) from exc
            logger.warning("%s Continuing without Redis.", message)
            return
    runtime.client = redis_factory(redis_url, socket_connect_timeout=connect_timeout, socket_timeout=socket_timeout, retry_on_timeout=True)
    try:
        await runtime.client.ping()
    except Exception as exc:
        runtime.client = None
        message = f"Redis cache/state ping failed: {exc}"
        if fail_fast or multi_replica_enabled:
            raise RuntimeError(message) from exc
        logger.warning("%s Continuing without Redis.", message)
        return
    runtime.available = True
    await configure_cache_policy(configure_on_startup=configure_on_startup, maxmemory=maxmemory, maxmemory_policy=maxmemory_policy, logger=logger)
    logger.info("Redis-backed cache/state is enabled.")


async def close() -> None:
    if runtime.client is not None:
        runtime.close_calls += 1
        await runtime.client.aclose()
    runtime.available = False


async def cache_get(*, namespace: str, logical_key: str, redis_key: str, decoder: Callable[[bytes], Any], stats: dict[str, int], logger: Any) -> Any:
    if not is_available():
        stats[f"{namespace}_miss"] += 1
        return None
    try:
        blob = await runtime.client.get(redis_key)
    except Exception:
        logger.warning("Redis cache get failed for namespace=%s", namespace, exc_info=True)
        stats[f"{namespace}_error"] += 1
        return None
    if not blob:
        stats[f"{namespace}_miss"] += 1
        return None
    try:
        value = decoder(blob)
    except Exception:
        logger.warning("Failed to decode Redis cache entry namespace=%s key=%s", namespace, logical_key)
        stats[f"{namespace}_error"] += 1
        return None
    stats[f"{namespace}_hit"] += 1
    return value


async def cache_set(*, namespace: str, redis_key: str, payload: Optional[bytes], ttl_seconds: int, stats: dict[str, int], logger: Any) -> None:
    if ttl_seconds <= 0 or not is_available() or payload is None:
        return
    try:
        await runtime.client.setex(redis_key, ttl_seconds, payload)
    except Exception:
        logger.warning("Redis cache set failed for namespace=%s", namespace, exc_info=True)
        stats[f"{namespace}_error"] += 1


async def cache_delete(*, namespace: str, redis_keys: tuple[str, ...], stats: dict[str, int], logger: Any) -> None:
    if not redis_keys or not is_available():
        return
    try:
        await runtime.client.delete(*redis_keys)
    except Exception:
        logger.warning("Redis cache key delete failed", exc_info=True)
        stats[f"{namespace}_error"] += 1
