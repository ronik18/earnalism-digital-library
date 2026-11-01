# Guarded Custom API scaling controller — isolated source preparation

This is a standalone, unwired application factory in
`scripts/guarded_scaling_controller.py`. It is not registered in the customer
backend, has no CLI/listener, does not load credentials or environment variables,
and has no real Railway adapter. Execution defaults OFF and provider access
uses DisabledProvider unless explicitly injected. Tests use only dummy provider
objects, in-process ASGI and private temporary SQLite files. Nothing here enables
Redis, changes a controller setting, scales a service or deploys an application.

## Supported API and enforced boundary

Judoscale documents authenticated `GET /services` and `PATCH /services/:id`
with JSON `{ "scale": integer }` for its Custom API integration. The factory
implements those routes. An explicit bearer context is required; comparison is
constant-time and duplicate authorization fields are rejected. The scale body
allows no target, source, approval, capacity or readiness fields. Duplicate JSON
keys, booleans/non-integer scales, out-of-range values, extra fields, oversized
bodies and slow bodies are rejected before provider mutation. Responses do not
cache or include credentials/provider exception text.

The scale handler itself invokes admission before its only provider mutation
call. It checks exact native UUID target, expected backend source digest,
fresh/stable running and configured counts, no pending work, exact Atlas
project/cluster identity, exclusive control,
shared-state admission, downscale drain proof and strict per-node Atlas budget.
An authenticated caller cannot submit those proofs in its request. Observation
and receipt are trusted adapter outputs; a JSON field labelled true is not
runtime evidence. A future adapter must derive these from real native metadata,
all active/draining deployment/source/worker inventories and reviewed evidence.

The current native Judoscale integration bypasses this new app. Its direct
provider writer must not remain active beside an admitted bridge. Routing the
controller to Custom API is a separately authorized provider-settings change;
no such change is performed or implied. Matching service names or a metrics URL
cannot establish native mapping or exclusivity.

## At-most-once local intent barrier

A private same-owner SQLite journal uses synchronous FULL commits and a verified
unique partial index. One unresolved intent per exact native target is allowed.
The intent is committed before the provider call. Two readers racing before
claim cannot create two unresolved intents. A second fresh observation after
claim must match the original source/revision/config/proofs before submission.
The provider contract requires compare-and-set with that revision; a real
adapter cannot emulate atomic CAS with an unprotected read followed by write.
If Railway's actual API/control arrangement cannot supply that condition, leave
execution disabled rather than claiming this protocol proves native CAS.

Success requires a settled, matching operation receipt. Lost reply, timeout,
cancellation or uncertain result leaves UNKNOWN (or crash-persistent PENDING)
and blocks subsequent writes, even after restart. There is no automatic expiry,
mutation retry, force-clear or count-only recovery. An operator-only library
method performs read-only receipt lookup; receipt target, operation, desired
count and ORIGINAL recorded source must match. New policy/source cannot rebind
an old uncertain intent. Reconciliation is not an HTTP endpoint. A proven
post-submit rejection without a supported terminal receipt remains held; do not
manually delete the intent to get a green result.

At-most-once scope is exactly one admitted shared local journal. Pointing a
second host/path at a new database would bypass its history. A future deployment
must bind canonical journal identity, singleton/shared ownership, persistence,
off-device retention and restore/reconciliation. Local SQLite tests do not
qualify multi-host coordination, off-device durability or a provider outage.

## Atlas client and rollout bounds

Use the existing `connection_envelope` implementation, not bare replica×pool
arithmetic. Required inputs include maximum current and replacement cohorts,
workers/client factories per process, pool+monitor sockets per node, all separate
background consumers, other-client bound, quota and explicit reserve. One
observed replica cannot replace the maximum current cohort. Null/missing counts
remain unknown and prevent provider mutation. The controller also rejects a
snapshot whose observed replica count or policy range differs from its inputs.

The source inventory at base68f4dcea finds one web factory sharing its client,
eight manual production-tool factories and six isolated-UAT factory calls.
The eight manual tools are prepared with explicit maxPoolSize8/minPoolSize0/
maxConnecting2; driver tests evaluate their actual constructor expressions with
connect=False and prove that URI unlimited/oversized options cannot override
these keyword bounds. Business operations are not run against a database. Seven previously unclosed
manual clients now have deterministic ownership/cleanup; the eighth already
closed in finally (database selection is now inside that protected block). Repair helpers transfer a live collection to the caller and
close only on helper failure or after caller use. Dummy lifecycle tests cover
early returns, errors, BaseException and report/write failures. This does not
retrospectively close clients in older already-running processes.

This bounds one newly invoked manual client to at most8pool+2monitor sockets
per node with the pinned driver. Eight script TYPES is not eight concurrent
processes. Already-running older tools, other projects/software/accounts and
simultaneous manual invocations still need a bounded inventory/control source.
Current low connection telemetry cannot establish that bound or an approved
reserve. No finite operational maximum is approved from dummy values.

Railway's documented configurable overlap duration is not a hard cap of two
simultaneous cohorts. The two-full-cohort calculation is a planning scenario,
not a provider guarantee. A future real adapter must inventory all active and
draining cohorts and reject pending/concurrent rollout activity; other deployment
and manual scaling writers are bypasses unless separately controlled. Current
maximum overlap and aggregate other-client allowance therefore remain held.

## Tests and integration

`python3.11 -m unittest scripts.test_guarded_scaling_controller scripts.test_manual_mongo_pool_bounds scripts.test_manual_mongo_client_lifecycle scripts.test_check_scaling_readiness`

Before adoption, review the exact source head and run required CI in the serial
Integration Lane against then-current main. Preserve the audiobook lane and its
package changes. No integration, publication, credentials, settings or compute
allocation is authorized by this preparation document.

Future runtime dependencies: native adapter with actual CAS/receipt semantics;
exclusive controller/deployment ownership; verified shared state/ACL/memory and
drain; all client/rollout/reserve evidence; fixed durable journal and off-device
recovery; separate authority for settings/deployment/scaling validation. Do not
present dummy provider tests as those proofs.

Sources:
- https://judoscale.com/docs/custom-platform-getting-started
- https://judoscale.com/docs/railway-getting-started
- https://docs.railway.com/deployments/deployment-teardown
- https://www.mongodb.com/docs/atlas/reference/atlas-limits/
- https://pymongo.readthedocs.io/en/4.5.0/faq.html
