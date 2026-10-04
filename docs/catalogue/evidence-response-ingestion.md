# Catalogue evidence response intake

This is a narrow authenticated evidence-intake feature. It does not approve a
rights-registry entry, change an allowlist, activate a title, issue an entitlement,
modify payments, or launch acquisition. No real catalogue evidence was processed
in local validation.

## API contract

`POST /api/admin/catalogue/evidence-responses` uses the existing `require_admin`
authorization dependency, including current server-side active-admin validation.
An operator string or a supplied role claim is not authentication. The endpoint
becomes available to legitimate administrators when deployed; it does not enable
production ingestion or a worker automatically.

Required fields: decision_id, idempotency_key, edition_id, source_sha256,
package_sha256, authority_id, authorized_scope, decision, evidence. The only scope
is `INDIA_TEXT_READER_ONLY`. Decisions are APPROVED, REJECTED and
NEEDS_MORE_INFORMATION. Evidence should contain durable internal references and
requested evidence fields, never credentials. Optional supersedes_decision_id must
identify the exact currently active decision, with a new decision/idempotency ID.

The persisted edition must contain the exact source/package SHA-256 bindings and
an explicit allowed evidence-authority list. Intake cannot create those facts.
Ambiguous edition identifiers are denied. Validation runs again against the actual
Mongo edition inside the write transaction. An edition write fence forces package
or authority changes to cause transaction retry and fresh validation.

Responses: 200 accepted/replayed; 409 stale hash, unknown/ambiguous edition,
idempotency conflict, conflicting decision or invalid supersession; 422 malformed,
unsupported, unauthorized-authority or unsupported-scope evidence; 503 unavailable
transactional storage. Authentication uses the existing 401/403 behavior.

## Durability, conflict and replay

MongoDB replica-set transactions are required. A unique partial index permits
exactly one active decision per edition; decision IDs and idempotency keys are
also unique. Decision, reference-only audit and edition reassessment outbox commit
atomically. Startup does not silently delete historical conflicting records to
create an index: such preexisting data requires controlled reconciliation.

Exact replay creates no second transition/audit/outbox entry. Current package and
authority validation still precedes replay: an old approval cannot authorize changed
bytes. Conflicting valid decisions freeze the active decision with conflict_pending
and hold outstanding reassessment. An explicit bound supersession resolves that
hold; it never bypasses current source, authority or scope validation.

The audit stores edition, hashes, authority, scope, decision, evidence reference,
actor, server UTC timestamp, idempotency identifier and conflict reason. It does
not copy the evidence body into operational logs/audit. Invalid authority/scope
requests never become canonical decisions.

## One-edition reassessment and worker boundary

`catalogue_evidence_requeue` is a transactional Mongo outbox, not Redis delivery or
a publication job. APPROVED queues one exact edition/decision for reassessment;
REJECTED and NEEDS_MORE_INFORMATION persist HELD records with no retry churn.
Other editions are untouched. Replaying never increments the queue count.

There is currently **no consumer of this outbox in current main**. Intake therefore
creates no worker claim or activation attempt. Claim/lease/crash recovery for a
consumer cannot truthfully be asserted by this producer's tests. A future scoped
consumer must reuse the existing worker's lease/fencing mechanism, recheck current
package/source hashes, active decision and conflict_pending, and then run every
existing publication/rights gate. Never interpret evidence APPROVED as runtime
publication authority. Redis availability is not a dependency for this durable
producer.

## Local validation (not production)

- Python 3.11.15; pytest 9.0.3; PyMongo 4.5.0; Motor 3.3.1; Redis client 5.0.8;
  FastAPI 0.110.1; Starlette 0.37.2; installed Click 8.3.3.
- MongoDB 8.2.7 replica set at loopback 27282; Redis 8.10.1 at loopback 26582,
  isolated Redis database 9. Unique `response_ingestion_disposable_*` Mongo
  databases contain generated fixture books/admin only and are removed after tests.
- 46 focused ingestion/catalogue-truth tests; 151 broader auth/rights/catalogue
  tests (overlapping selection, not additive totals).
- 15 real Mongo/HTTP integration tests: three actual backend process restarts,
  eight concurrent identical submissions (one new result, seven replays), conflicting
  decisions (one 200, one 409, reassessment held), package change, package/authority
  mutation after transactional read, invalid authority/scope concurrent arrival,
  one-edition requeue, injected mid-transition failure with full rollback,
  ambiguous identity, unauthenticated denial, Redis-independent persistence and
  explicit conflict supersession.
- 22 existing Mongo admission/promotion tests passed with canonical ENVIRONMENT=uat;
  an earlier invocation omitted this setting and correctly hit the production
  fail-closed entitlement gate. No application assertion was weakened.
- 3 fresh-process Redis policy tests passed. No Redis job serialization is introduced.

Reproduce focused real-Mongo verification with disposable services only:

```sh
CATALOGUE_EVIDENCE_MONGO_INTEGRATION=1 \
RESPONSE_TEST_MONGO='mongodb://127.0.0.1:27282/?replicaSet=response-uat' \
RESPONSE_TEST_REDIS='redis://127.0.0.1:26582/9' \
/tmp/earnalism-main-approved-integration/.venv-uat/bin/python -m pytest \
  backend/tests/test_evidence_response_mongo_integration.py -v
```

## Dependency resolution

Current main and feature both retain `click==8.3.3`. Both successfully downloaded
that wheel and ran `python -m pip install --dry-run --ignore-installed click==8.3.3`
using the same default package index. The reported install failure no longer
reproduces; its original cause cannot be inferred from these successful attempts.
Dependency files were not changed. The existing UAT virtualenv is the environment
managed by `scripts/start_local_uat.sh`, which installs backend/requirements.txt.
CI regression uses an explicit smaller dependency list; some catalogue jobs use
backend/requirements.txt. No alternate CI package index was found in the workflow
configuration. Global/system Python was not modified.
