# India-only source preflight and staged release preparation

This is preparation only. It neither dispatches a workflow nor authorizes a
deployment, publication, paid session, provider change or customer-data operation.
The legacy frontend production workflow and its protected approval values stay
unchanged. Do not dispatch it with substituted source pins for this release.

## Immutable application and controller roles

`india_release_source_contract.json` selects merged application12ad6209 and
backend artifactaf7571ae, whose backend subtree is identical. Frontend source is
the application commit. These commits genuinely have the required ancestry.
Reviewed squash heads are linked by full-root equality and successful exact-head
checks, rather than a false assertion that the squash source is its ancestor.
The controller may change tooling only: its backend/frontend subtrees must still
equal the selected application. Source qualification does not qualify that new
controller's own CI or imply its approval.

After committing the reviewed preparation source, from a clean checkout:

```sh
python3 -m unittest scripts.test_india_release_source_preflight
python3 scripts/india_release_source_preflight.py --output /tmp/india-source-preflight.json
```

The script reads Git objects and GitHub check results only. Its successful result
is always `SOURCE_QUALIFIED_EXECUTION_HOLD`. No source-supplied receipt can turn
this into provider or deployment acceptance. Review and required exact-head CI of
the preparation PR remain necessary before selecting its merged controller SHA.

## Provider preparation and future execution boundaries

1. Keep Vercel automatic Git deployment disabled and Railway deployment triggers
   disabled. Read current scoped project/service metadata; no secret values,
   `.env` export, customer queries, financial events or startup/server imports.
2. Independently observe actual Railway serving Git SHA/deployment identity and
   compare its source to the selected new backend. A healthy older release does
   not qualify the new backend. Existing startup checks are metadata-dependent;
   reuse historical evidence only within scope, not as a fresh database clearance.
3. Record both currently serving rollback artifacts, exact configs, immutable
   hashes, provider eligibility and the authorized rollback operator. Provider
   `canRollback:true` is capability evidence, not a rollback approval or drill.
   Do not execute a rollback to test it. Refresh time-limited checks at execution.
4. Verify effective proxy-secret presence and compatibility using an approved
   non-disclosing mechanism. A variable name proves neither its value/length nor
   equality across providers. Never invent or transmit country assertions from
   a client to obtain admission. Retain IN-only method/path/country signatures.
5. Do not assume backend-first deployment is compatible. The currently retained
   frontendaf4f9d0f does not sign `/api/payments/topup`; new backendaf7571ae
   rejects it. A separately reviewed frontend-first compatibility transition is
   required before backend enforcement, or another reviewed fail-closed staged
   transition. Verify actual source, startup/database health and config; stage a
   Git-source Vercel **production** candidate with domain assignment disabled.
   Verify that exact candidate's public health/book and real guest manifest401,
   then promote that tested candidate once only under separate authority.
6. Qualification must cover India admission, non-India denial, preserved payment
   verify/refund/webhook paths, three-page preview plus intentional free Reader
   entitlements, no free audiobook, and protected listener behavior without
   starting a paid session. Existing tests are evidence, not new production proof.
7. Retained backende68d70bc does not enforce the new India purchase guard. Its
   provider rollback eligibility is not India-only rollback qualification.
   Rolling the frontend back alone after the new backend also breaks purchase
   signing. Require a separately qualified compatible rollback or reviewed
   fail-closed containment plan before execution; never loosen territory guards.

The execution controller remains unimplemented/unapproved by this source-only
preflight. Its future PR must enforce the above protected config/rollback gates,
bounded polling, persisted write intent, read-only reconciliation after unknown
outcomes and actual serving canaries. No approvals are minted by this document.

## Owner facts versus engineering work

Account/team access denied by a provider may require its account administrator.
Actual mailbox/contact queue monitoring, deletion/backups/expiry operations and
India accountant classification/invoice/retention instructions are business
facts if absent from retained evidence. Source selection, CI, controller code,
provider receipt collection and diagnostic work belong to the Integration Lane.
Do not re-request the accepted named operator role or assumed US/video clearance.
