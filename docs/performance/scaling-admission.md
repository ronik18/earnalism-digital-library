# Source-only connection budget and controller diagnosis

This extends the existing offline `scripts/check_scaling_readiness.py`, not an
external controller and not a provider-write executor. No credentials, settings,
load, API mutations or Redis access are needed. The tool never reports production
runtime admission: overall status remains HOLD or UNQUALIFIED and exit is2or3.

`limits.database_connection_quota` is a positive per-node quota. Supply the
following `limits.database_connection_budget` object only from bounded actual
inventory plus an explicit maximum rollout scenario:

```
{
  "nodes": 3,
  "observed_running_replicas": 1,
  "max_current_web_replicas": 10,
  "max_replacement_replicas": 10,
  "other_connections_per_node": 20,
  "reserve_connections_per_node": 50,
  "cohorts": [
    {"role":"current_web","replicas":10,"workers_per_replica":1,
     "clients_per_worker":1,"pool_per_client_per_node":8,
     "monitoring_sockets_per_client_per_node":2},
    {"role":"replacement_web","replicas":10,"workers_per_replica":1,
     "clients_per_worker":1,"pool_per_client_per_node":8,
     "monitoring_sockets_per_client_per_node":2}
  ],
  "additional_replica": {"workers_per_replica":1,"clients_per_worker":1,
    "pool_per_client_per_node":8,"monitoring_sockets_per_client_per_node":2}
}
```

These numbers are a dummy example, NOT Earnalism's observed other-client bound or
approved reserve. Do not copy them into production admission. `current_web` and
`replacement_web` are both explicit; known zero replacement still needs a
zero-replica cohort. Additional `background` cohorts include known job processes.
Unknown external/admin clients must remain missing/null, never assigned zero.
`other_connections_per_node` includes remaining client categories not already in
cohorts; do not double-count the application's current10connection dashboard
snapshot. Missing surge/current maximum, a current maximum below observed replicas or configured autoscaler maximum, or mismatch between the actual replicas argument and observed inventory remains UNKNOWN. The current cohort represents the maximum old cohort, not merely the idle observed count: actual1 with targetmax10 and replacement10 still bounds20processes/200connections per node. Present
WEB_CONCURRENCY/MONGODB_MAX_POOL_SIZE must match every web cohort; mixed worker or
pool versions need explicit resolution rather than silently assuming defaults.

Application per-node bound is the sum over cohorts of replicas × workers ×
clients × (pool + monitoring). Other connections and reserved headroom are added
per node. The all-node sum is reporting only and is never compared with one
node's quota. With the dummy values above, bound200 + other20 + reserve50 =270
per node; conditional headroom230 permits23 *additional* one-worker replicas in
arithmetic only. `maxAdditionalReplicas` does not mean an approved autoscaler
maximum, process inventory certainty, capacity, cost authority or throughput.
No finite maximum is emitted when required bounds are unknown. Quota saturation
is allowed only at the explicitly reserved headroom boundary, never without a
positive reserve. Existing current runtime inputs still lack these actual bounds.

`limits.controller` accepts `mode`, `expected_target`, `observed_target`. Each
target has exactly `project_id`, `environment_id`, `service_id` UUID fields.
Only UUID equality can report supplied target MATCH. Names, metrics token,
`enforcementVerified:true` or another caller-provided boolean never attest a
write boundary. Native Judoscale mode always returns
UNMEDIATED_NATIVE_CONTROLLER/HOLD: no call of this offline script can veto the
external Railway write. A target mismatch independently holds.

The supported alternative documented by Judoscale is a Custom API integration
with GET /services and PATCH /services/:id. A guarded implementation could reject
PATCH before calling Railway when source, inventory, budget or rollback proof
is missing. This source does not create that API, choose a credential, configure
it, replace the native integration or claim it is now in the provider path.
`guarded_custom_api` returns GUARDED_IMPLEMENTATION_AND_RUNTIME_BINDING_REQUIRED,
never enforcement PASS. Switching the live control boundary requires separate
provider settings authority and actual audited executor implementation, durable
intent/result reconciliation and current native target binding; current user
prohibits those settings changes. The native autoscaler must not remain a bypass
beside any future guard.

Tests cover actual per-node arithmetic, old/new worker overlap, monitor sockets (at least two per node for the pinned PyMongo driver),
unknown other clients/surge, observed-count/config drift, boolean/negative input,
quota+reserve boundary, no total-node comparison, native UUID mismatch and forged
boolean enforcement. Existing mandatory unittest module is extended so the new
checks cannot be skipped by omitting a new test hook.

Official references:
- https://judoscale.com/docs/custom-platform-getting-started
- https://judoscale.com/docs/railway-getting-started
- https://www.mongodb.com/docs/atlas/reference/atlas-limits/
- https://pymongo.readthedocs.io/en/4.5.0/faq.html
