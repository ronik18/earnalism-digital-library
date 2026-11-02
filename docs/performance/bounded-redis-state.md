# Bounded Redis state: source preparation, activation held

This patch is not a deployment, numeric memory budget, controller implementation,
or 5,000-user capacity qualification. Keep the 2.5-second renewal deadline and all
existing stop/financial/rights/territory gates. Existing local/Redis-off behavior
remains separate from protected shared-state activation.

Multi-replica mode requires explicit REDIS_LIMITER_SLOTS (1..4096), a separately
admitted 32-hex REDIS_LIMITER_GENERATION, window 1..120 seconds, and the nine fixed
scope limits (each 1..30000). These are structural upper bounds, not recommended
operating values. Defaults do not activate the policy. Policy copies are frozen.

For the first bounded shared-state profile, PUBLIC_CACHE_ENABLED, REDIS_CACHE_ENABLED,
REDIS_PUBLIC_METADATA_ENABLED, READER_RUM_ENABLED and
ENABLE_STARTUP_DB_MAINTENANCE must be false. Optional cache helpers no longer follow
MULTI_REPLICA_ENABLED. The Redis constructor requests at most 16 connections per process; bounded
multi-replica startup additionally verifies the effective parsed pool is a strict
integer in 1..16 before ping, because URL options override constructor keywords.
An override or missing/invalid bound denies with cleanup; lower caps stay unchanged. This
does not bound all replicas, other clients, buffers or provider RSS. Local public
caches are disabled too: per-process generations cannot invalidate a different
replica after a catalogue mutation. Do not substitute a local-cache fallback for
shared invalidation; authoritative uncached reads remain subject to DB headroom gates.

The v3 limiter hashes identity/scope into a finite slot set. A slot holds a
persistent policy/generation header, one owner and at most twice its declared
scope limit of fixed-format UUID/time records. Key count is at most 9*S+1;
member count at most S*sum(2*limit+2). Legacy keys and retained generations are
NOT included in that bound until separately reconciled. Slot collisions deny a
new owner until all previous-owner replay history expires (2W), even if the
ordinary W rate window has expired. This deliberate conservative availability
tradeoff must be accepted in the exact activation packet and qualified; it is
not a claim of equivalent throughput or campaign readiness.

Slots and policy must be initialized under separate, explicit migration/access
execution authority after ALL old writers are frozen and ALL old state is
reconciled/drained. Application startup and requests never initialize or repair
them. Slots and policy remain persistent; missing/expiring/mismatched state denies.
Startup verifies policy presence/persistence only; this does NOT prove all-slot
initialization. Actual preflight must verify every admitted slot and namespace,
exclusive writers, generation/recovery custody and actual finite memory policy.
Do not re-create a lost manifest or slots as a recovery shortcut.

Lua verifies policy/argument binding, persistent slot shape and bounded members
before mutation. A transport retry uses the original internal UUID and does not
refresh history. Old v1/v2 incoming-identity keys block admission, but checking
one identity is NOT proof of a drained old namespace. Only logically expired
records are pruned. Lua isolation does not roll back errors: a failed final write
may strand a slot, which must remain held for reconciliation rather than reset.

The validator may scan up to 60002 members for the maximum scope setting. This
finite bound does NOT establish compliance with the 2.5-second deadline. No load
or benchmark is included. Actual Redis 8.2 runtime/ACL/clock/OOM/loss/drain and
memory/COW/buffer/HA behavior remain release gates. The local functional fixture
uses a disposable Unix socket, TCP disabled, synthetic keys, no provider secrets,
and verified teardown; it cannot establish production readiness.

Canonical application must await explicit serial writer handoff, rebase/reconcile
against newly merged source, fresh guard/runtime inventory bindings, independent
exact-head review and required CI. No concurrent audiobook edits may be replaced.
Rollback must bind immutable image AND custom-variable/secret-version identities;
OPEN source is not CLOSED purchase containment. Mongo global custody and the real
exclusive controller adapter/authority/journal are still absent. No source JSON
boolean, per-tool pool or provider canRollback flag closes those gaps.
