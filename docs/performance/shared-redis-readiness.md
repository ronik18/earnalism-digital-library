# Shared Redis source readiness

This change does not enable Redis, change database indexes, or authorize deployment.
Use actual running replica status as runtime evidence. A configured replica count is
not proof that the instances are running.

## Atomic request admission

The shared limiter uses Redis TIME and one Lua operation for prune/count/admit/expiry.
Local-only limiting retains its existing monotonic clock. The helper's internal UUID
is reused by the SDK's transport retry: a retained UUID returns its original admission
without consuming another slot. A new helper invocation generates a new UUID. The
shared client's existing retry policy is unchanged.

New counters use `rate-limit-v2-server-time`. Old monotonic-clock counters are not
reset or reinterpreted: a retained legacy TTL denies admission; persistent or invalid
legacy state fails closed. No old/new shared-limiter writers may be mixed during
activation. The two-key script requires standalone Redis or demonstrated same-slot
placement and the appropriate existing script/command ACL. Redis Cluster compatibility
is not implied. Outages continue to fail closed through the existing error path;
this is not a promise of graceful availability.

Retry deduplication is finite. Qualify the effective request/transport deadline and
SDK retry policy against the retained key lifetime before activation. With the current
default 60-second window, keys expire after 120 seconds. Arbitrarily long pauses or
future timeout increases are not covered by that horizon. Do not raise timeouts or
reset counters merely to obtain a passing test.

## Configuration side effects and rollback

Enabling either shared-state flag can initialize Redis. If
`REDIS_CONFIGURE_ON_STARTUP=true`, startup can also issue global `CONFIG SET` commands.
A source-only merge must not activate flags or change memory/eviction policy. Any later
activation proposal must explicitly account for existing Redis roles, persistence,
memory limits, ACL, failure behavior, cost bounds and retained state. Setting startup
configuration to false avoids those implicit policy changes, but does not qualify the
remaining runtime behavior by itself.

Never label a return to multiple local-only limiter processes a safe rollback. Retain
exact source/configuration, drain and containment evidence. Provider changes, index
builds and release operations require their own authority and qualification.

## Offline metadata checks

Both tools below read only supplied JSON files; they do not connect to providers or
create, drop or alter indexes.

```
python3 scripts/check_index_readiness.py --declared DECLARED.json --actual ACTUAL.json --output RESULT.json
python3 scripts/check_scaling_readiness.py --config CONFIG.json --replicas RUNNING_COUNT --limits LIMITS.json --output RESULT.json
python3 -m unittest scripts.test_check_index_readiness scripts.test_check_scaling_readiness
```

Index declarations are an array (or an object with an `indexes` array) containing
`collection`, ordered `key` pairs and `options`. Metadata has a `collections` object
mapping each inspected collection to its actual index specifications. An empty array
means the namespace was inspected and absent/empty; a missing entry means unknown.
Compare unique, sparse, partial-filter, collation and TTL semantics as well as key order. A
matching name alone is insufficient. Prefix redundancy is a review candidate, never
automatic drop authority. Index declarations and matching metadata do not prove an
optimal query plan or spare build resources. Do not run broad startup maintenance as
an index-repair shortcut: it may migrate or seed customer-facing data.

Scaling input uses explicit `MULTI_REPLICA_ENABLED`, `REDIS_CACHE_ENABLED`, worker and
pool values. The optional limits file supplies autoscaler min/max/cooldown, database
connection quota and Redis memory/client/eviction limits. Missing or malformed limits
remain UNKNOWN. A metadata match does not certify capacity, actual cache correctness
or failover. Treat exit 2 as HOLD and exit 3 as UNQUALIFIED, not a test-run failure or
permission to mutate provider settings.
