# Optional public metadata Redis cache

This is a source qualification runbook, not permission to enable Redis. The
public metadata flag and both broader shared-state flags remain unchanged.
Reading/listening, payment verification, refunds, balances and entitlements must
never acquire a Redis dependency through this cache.

## Correctness contract

The public cache uses a durable MongoDB control record and fixed Redis slots.
Before trusting a Redis payload, readers check the control record on the primary
with bounded linearizable read concern. Control writes require majority and
journal acknowledgement. The extra Mongo request is a deliberate correctness
cost; one Redis command does not mean one total network round trip.

A metadata writer must fence before its first visible source mutation. An
unavailable, malformed, already fenced or ambiguous control record prevents that
mutation from starting. A known successful operation can release only its own
token into a fresh generation. Exceptions, cancellation and uncertain outcomes
leave the fence intact. No timeout automatically unlocks it and no source write
is replayed to repair invalidation. Direct and offline writers must use the same
protocol or refuse to write while shared metadata caching is admitted.

Startup and re-enable require fresh generation admission; retaining an old Redis
epoch with `SETNX` is insufficient. Malformed or fenced state is never reset to
green. Redis loss or recovery cannot override the durable control record.
Mixed legacy writers/readers must be drained before future activation.
Payload keys also bind the measured local runtime source, so a different
deployment cannot populate this source's cache entries. An unavailable source
binding bypasses the shared cache rather than inventing an identity.

The default-OFF and legacy shared-state modes preserve their existing handler
behavior. They are not certified as concurrent writers beside newly enabled
public-only readers. Enabling shared public caching requires admitting every
writer on the reviewed mode and draining older/OFF writers first.
Evidence intake preserves any existing durable control even when the public
flag is OFF: an absent record stays absent, an ACTIVE record uses the same-task
fenced server path, and unresolved/malformed/unavailable control remains held.
This avoids stranding the supported intake path after rollback without admitting
unfenced legacy CLI writers or changing financial handlers.
The internal authorized Reader-bootstrap helper is fenced too, including its
startup/background caller. Startup database maintenance must remain OFF when
admitting public-only Redis: its mixed metadata/financial migrations cannot run
behind shared readers or acquire a cache dependency. The incompatible
configuration is rejected before Redis is contacted.

## Bounded failure behavior

Public-only cache connection, startup and read failures fall back to authoritative
metadata without making optional Redis a backend startup requirement. Broader
shared-state behavior retains its own explicit admission rules. No cache miss
authorizes protected data or changes customer accounting.

Public payloads use bounded JSON rather than pickle or compressed payloads.
Fixed slots bound namespace cardinality across generations. Payload, structure,
nesting and serialization limits are application limits, not a claim about the
provider's global memory or eviction policy. No `CONFIG SET`, `FLUSH`, key scan,
arbitrary deletion or policy change is part of this feature.

The candidate uses 64 slots with at most 128 KiB of encoded body per slot:
8 MiB of body capacity plus bounded identifiers and Redis object overhead. The
slot budget is shared across generations; old generations cannot add more keys.
This does not remove pre-existing legacy cache keys or set a global memory cap.
Admission must account for those retained keys and other users of the service.

## Future activation evidence

After source tests and exact-head CI/review pass, prepare one exact activation
decision with the serving source, existing destination, private-path latency,
script/key-prefix permissions, effective resource limits, writer/reader drain,
canary thresholds and rollback artifact. Local Redis/Mongo fixtures do not prove
provider ACLs, runtime performance, customer billing or production playback.
Keep broader cache and multi-replica flags false for a public-only decision.

## Rollback

With separate authority, turn only public metadata caching off and drain/restart
every cache reader on the qualified source. Fresh processes rebuild local caches
from authoritative metadata. Check public response identity and protected
guest/no-pass denials without starting a paid session. Preserve live audiobook,
cover, rights and Reader entitlement bindings.

Do not flush Redis or alter global policy. Preserve unresolved mutation/fence
records. Disabling caching is not evidence that an uncertain mutation was
unapplied; reconcile its authoritative outcome without rerunning the handler.
Do not re-enable until the repaired startup admission and reader/writer drain
have been qualified again. Retained entries may expire normally.

## Evidence boundaries

Report actual test counts, source hashes, fixture cleanup and exact CI/review
results. Keep source qualification, provider qualification, activation and public
acceptance separate. No production setting, deployment or paid session is
authorized by this runbook.

The purchase-guard source successor keeps the historical owner receipt and exact
original OPEN/CLOSED hashes. It adds an exact Git binding for this application
candidate, derives its guarded source and checks that the purchase, territorial,
financial and lease handlers remain unchanged. This is source qualification;
it does not pause purchases, deploy a recovery image or reuse an old rollout
receipt as authority for a new provider operation.

MongoDB's consistency and timeout requirements are documented in the official
[linearizable read concern reference](https://www.mongodb.com/docs/manual/reference/read-concern-linearizable/).
