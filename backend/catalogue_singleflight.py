"""Generation-fenced public catalogue fill; never caches authorization decisions."""
import asyncio
import time
import uuid

from redis.exceptions import RedisError


RELEASE = """if redis.call('GET', KEYS[1]) == ARGV[1] then
return redis.call('DEL', KEYS[1]) end return 0"""
PUBLISH = """if (redis.call('GET', KEYS[1]) or '0') ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
redis.call('SETEX', KEYS[3], ARGV[3], ARGV[4]) return 1"""


def _decode_or_miss(blob, decode):
    if not blob:
        return None
    try:
        return decode(blob)
    except (ValueError, TypeError, UnicodeError, OSError):
        return None  # Corruption is a miss, never an alternative rights decision.


async def cached_catalogue(client, generation_key, storage_key, build, encode, decode,
                           ttl, *, lock_seconds=10, wait_seconds=12):
    """One Redis owner per key/generation, with bounded wait and owner-safe release.

    Outages and exhausted contention fall back to uncached authoritative builds.
    A changed generation discards the old fill; it cannot poison the new cache.
    Cancellation releases ownership, and worker death is recovered through TTL.
    """
    deadline = time.monotonic() + wait_seconds
    delay = .01
    while time.monotonic() < deadline:
        try:
            generation = await client.get(generation_key) or b'0'
            if isinstance(generation, bytes):
                generation = generation.decode('ascii')
            key = storage_key(int(generation))
            blob = await client.get(key)
            cached = _decode_or_miss(blob, decode)
            if cached is not None:
                return cached
            lock_key = key + ':fill-lock'
            owner = uuid.uuid4().hex
            acquired = await client.set(lock_key, owner, nx=True, ex=lock_seconds)
        except RedisError:
            return await build()
        if not acquired:
            await asyncio.sleep(delay)
            delay = min(.1, delay * 2)
            continue
        try:
            # Another owner can finish between our miss and lock acquisition.
            try:
                blob = await client.get(key)
            except RedisError:
                return await build()
            cached = _decode_or_miss(blob, decode)
            if cached is not None:
                return cached
            value = await build()
            payload = encode(value)
            try:
                if payload is not None:
                    published = await client.eval(PUBLISH, 3, generation_key, lock_key,
                                                  key, generation, owner, ttl, payload)
                    if published:
                        return value
                else:
                    current = await client.get(generation_key) or b'0'
                    if str(current.decode() if isinstance(current, bytes) else current) == generation:
                        return value
            except RedisError:
                return value
            # Generation changed or ownership expired: never publish stale data.
        finally:
            try:
                await client.eval(RELEASE, 1, lock_key, owner)
            except RedisError:
                pass  # Expiry remains the recovery mechanism during an outage.
    return await build()
