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

Merged #621 removes global CONFIG SET from protected startup. Broad shared-state
startup now requires configure-on-startup=false, verified noeviction and finite
positive maxmemory above observed used_memory. This is a source gate, not proof
of actual provider ACL, peak headroom, persistence or mixed-writer safety. Older
serving/recovery sources may still mutate policy and must not be treated as
Redis-enabled rollback artifacts merely because #621 merged.

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

## Public metadata only (default off)

`REDIS_PUBLIC_METADATA_ENABLED=false` is a separate opt-in. With the existing
`REDIS_CACHE_ENABLED=false` and `MULTI_REPLICA_ENABLED=false`, a later explicit
public-only activation initializes the connection and public generation marker,
but does not enable auth/session/wallet/reader/limiter Redis state or apply
`CONFIG SET`, even if the legacy startup-policy flag is true. No environment
variable or provider setting is changed by this PR. A broad shared-state flag
still retains its existing meaning and must be qualified separately.

Public cache reads use one `EVAL_RO` command, atomically reading a strict lowercase
32-hex epoch and its payload. This is a new `public-cache-v2` namespace: old integer
or generation-zero entries cannot be reused. Startup initializes a missing marker
with `SET NX` and a fresh random epoch. A missing, malformed or wrong-type marker
subsequently causes a miss, never a fallback to zero or stale local data. No
automatic repair of a corrupt marker is performed on reads. A later explicit
invalidation reads the current epoch after the source mutation, then atomically
compares and rotates it in Lua. A delayed transport replay cannot rewind to an
earlier epoch; an intervening invalidation safely supersedes it. This deliberately
uses two commands for invalidation, while cache reads use one.

A miss records a bounded copy-on-write task-local fill ticket. The fill script
compares that captured epoch and writes the TTL payload atomically. If an
invalidation occurred while the route computed its response, the old fill is
rejected. Concurrent requests cannot overwrite each other's tickets. Unpaired
writers skip caching; warmers obtain tickets before reading source data. Local
cache fills are fenced against local generation changes too. Cache reads may
linearize just before an invalidation; this does not promise cancellation of an
already returned/in-flight response. Legacy and new writers must not be mixed
when shared caching is activated.

Metadata read/write failures bypass caching and rebuild through the existing
route. They do not use stale local fallback or alter live rights, auth, leases,
financial decisions or binary-media exclusions. Invalidation failures remain
visible errors rather than fabricated success. Existing Redis client deadlines
and retry behavior are retained; no new API-latency or outage-availability promise
is made. No database or production performance gain is certified by dummy tests.

The script derives a payload key from the epoch inside Redis. Qualification is
standalone-only; Redis Cluster/same-slot compatibility is not implied. Before
activation, verify the actual backend-selected endpoint, `EVAL_RO`/script command
ACL, private-network latency, memory/persistence roles, complete route behavior,
writer drain/rollback and resource budget. Local Redis 8.10.1 and CI Redis 8.2.1
fixtures are not proof of execution on the provider's Redis 8.2.9.

The mandatory isolated Redis gate now includes
`backend/tests/test_public_metadata_redis.py`. It uses only an explicitly admitted
loopback fixture, random private test prefixes and exact-key cleanup. It covers
one-command hits, marker loss/corruption, delayed and concurrent fills,
invalidation, media rejection, public-only startup isolation, and the real ASGI
public categories route/middleware with dummy catalogue and simulated outage.
No customer/provider credentials, paid sessions, broad scans, FLUSH or CONFIG are
used by the tests.

The separate public-only opt-in uses a positive metadata-scope allowlist. Legacy
Reader preview/chapter bodies, blog bodies and unknown future scopes remain local;
the intentional free Reader entitlements do not change. Broader existing shared
flags keep their previous scope and require their own qualification.

## Streaming drain and controller admission successor

HTTP lifetime accounting now wraps the user ASGI middleware stack and awaits
its complete downstream application, including streaming body and background
cleanup. It forwards receive/send without buffering media or changing range
headers. Cancellation, disconnect and send/iterator failures release accounting
exactly once. New non-health requests retain the existing draining503 response.
Framework ServerErrorMiddleware remains outside user middleware; this is not
proof of every framework-generated error send or process termination behavior.

The existing lifespan15second bound and Uvicorn default10second graceful period
are unchanged. Source tests do not certify the provider termination grace,
routing withdrawal, client recovery or actual Redis-enabled up/down behavior.
General health OK remains liveness, not stream-drain/Redis-readiness approval.

The existing offline checker now computes explicit per-node old/new/process
budgets and diagnoses controller target/enforcement gaps. See
[scaling admission](scaling-admission.md). Unknown other clients, reserve or
maximum overlap never becomes zero. Current idle replica counts cannot replace
maximum old+replacement cohorts. No supplied boolean can certify the external
controller's write path. Native Judoscale remains unmediated by this script;
a supported guarded Custom API boundary requires a separately reviewed actual
implementation and authorized provider routing change, neither performed here.
