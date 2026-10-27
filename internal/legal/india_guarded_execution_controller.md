# Guarded controller implementation and containment source

Current owner instruction: **no deployment, publication, dispatch, provider
execution or paid sessions**. Default adapter authority is false. There is no
execution CLI or automatic workflow dispatch in this change. The older heartbeat
deployment permission was superseded after verification of the native owner
instruction; source integration and offline qualification continue separately.

## Concrete implementation

`scripts/india_release_provider_adapter.py` implements explicit Vercel Git-source
production staging with domain assignment disabled, exact-candidate promotion,
and Railway exact-clean-checkout deployment command adapters. Commands use
installed documented CLI interfaces; no shell interpolation or token arguments.
Local help/version inspection covered Vercel59.25.4 (`api --method --input --raw
--scope`) and Railway5.71.0 (`up --ci --project --service --environment --json`).
The observer must attest the reviewed exact CLI version before a future write.
They were inspected via local help, not called against providers in these tests.
The controller requires a verified stage receipt before promotion and a verified
frontend promotion before backend release. It checks protected operation/source/
target/config/rollback bindings, approval expiry and fresh provider observations.

A future protected runner must supply the actual provider/source/config/startup
and rollback observer. Missing observer, changed evidence, unknown rollback,
unsigned frontend or failed candidate qualification blocks before any write.
The library's observer interface is not itself genuine observed evidence.
Actual provider adapters are implemented; protected-runner integration and
authentic observation/receipt acquisition are still required before execution.

Every operation persists an exclusive intent before calling its adapter.
The operation identity uses immutable provider targets, action, source SHA and
candidate identity, not local checkout paths. Any unresolved intent blocks all
later writes, including promotion after unknown staging. Timeout, nonzero exit,
process interruption and even process success require actual read-only provider
reconciliation. No provider output/secret is logged. An already attempted same
operation is never automatically repeated. Operator-authorized reconciliation
does not grant permission to retry or roll back.

The protected runner must use one fixed durable journal namespace and one
noncanceling release concurrency group. An exclusive global write barrier closes
the race between concurrent different operations in that journal; it is removed
only after bound read-only reconciliation, while permanent operation receipts
remain. The library does not provision durable/shared storage or a protected
runner automatically.

## Containment source instead of an unsafe old rollback

The historical565 backend lacks the India purchase guard and newer financial
fixes. It is rejected as an approved fallback. The initial guard-only old-runtime
offline proposal is retained only as rejected historical evidence and must not
be used. The accepted **preparation direction** starts from the complete current
backend633caa1a, retaining all Listener, payment-proof, atomic-refund, controlled
balance and entitlement code. Only a fail-closed purchase-initiation branch is
inserted in its actual production middleware; existing middleware and every
other backend file remain unchanged, including file modes.

`scripts/build_india_guarded_rollback.py` creates this source tree outside the
repository with a checksum/mode manifest. It cannot overwrite an existing output,
write into the repo, deploy, import server/startup, or produce provider approval.
Tests execute only the extracted middleware against inert dummy responses:
purchase initiation returns503; verify/refund/webhook paths continue through
unchanged middleware. This does not exercise real payment handlers or prove
generic server-failure recovery. It is a proposed containment artifact, not a
qualified provider rollback.

```sh
python3 -m unittest scripts.test_build_india_guarded_rollback scripts.test_india_release_provider_adapter
python3 scripts/build_india_guarded_rollback.py --output /tmp/a-new-unique-containment-source-directory
```

Remaining actual gates: immutable reviewed containment-source identity; isolated
qualification of that exact artifact; provider-built artifact/config eligibility;
guard-preserving rollback/containment operator approval; protected runner and live
observer wiring; current source-role contract and CI; explicit later deployment
authority. A local tar/manifest hash establishes neither serving nor rollback
eligibility. No engineering dependency is an invitation for an owner waiver.

## Bounded native metadata observer and protected preflight

`scripts/india_release_observer.py` supplies concrete authenticated read commands for fixed Vercel project/candidate GETs and bounded Railway deployment metadata. It never requests variables, account identity, logs or customer data. Unknown shapes/scopes/read failures hold; only allowlisted metadata survives projection, not raw provider output. Local help verified the installed native CLI syntax. Tests inject inert responses; actual native CLI response compatibility is not claimed from those tests.

The preflight uses a fixed journal namespace outside the checkout and does not create it, execute, dispatch or accept approval booleans as authority. Its result always retains the current no-execution prohibition and authentic platform executor/source-role/config/startup holds. A local folder is not proof of durable/shared protected-runner storage. Actual protected platform runner authentication/storage/approval wiring remains incomplete, explicitly rather than modeled as PASS.

Reused read-only Railway observation from 28 October local date: the bounded10-artifact inventory contains no reviewed guarded633/v4 artifact. Current22c88931/e68d70bc is healthy but capability `canRollback` does not prove guard/config qualification. No provider build/deploy is permitted to manufacture the missing evidence. Existing artifact/config eligibility and actual protected executor require further qualification before execution; no owner waiver is requested.
