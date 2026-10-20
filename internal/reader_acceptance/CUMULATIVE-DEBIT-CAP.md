# Cumulative acceptance debit cap

Disabled by default: this change provisions no account or budget, creates no
entitlement, and adds no client-facing enable/reset endpoint. Normal accounts
keep their existing behavior. A provisioned account is restricted to the exact
text/audio title and immutable manifest/segmentation identity in its budget.

The server-only `users.reader_acceptance_budget` record has these fields:
`schema: reader-acceptance-budget.v1`, exact `user_id`, `content_type`,
`content_id`, `test_id`, `manifest_version`, `segmentation_version`, integer
`maximum_seconds`, integer `consumed_seconds`, BSON UTC `expires_at`, and
`status: enabled`. No request supplies these values. Sessions retain the test
identity; missing/changed records fail closed. Consumption survives process,
session and device changes. Expiry/exhaustion denies new leases and protected
reads. Leases cannot outlast expiry or remaining seconds. Preparation grants no
extra budget and cannot revive exhaustion.

Both V2 heartbeat and terminal settlement (end/reaper/transfer/revocation) update
budget consumption and both wallet counters in one account CAS, inside the
existing transaction with the ledger and session transition. Concurrent updates
conflict or fail closed. Ledger/session replay rules remain unchanged. Late
settlement charges only the previously granted interval before expiry, bounded
by remaining budget. The legacy debit helper rejects provisioned accounts and
also excludes the budget field atomically from its debit filter. This is an
acceptance consumption limit, not a restriction on separately privileged
administrative financial operations.

## Smallest deployment and enable transaction — not executed

1. Keep this Draft PR unmerged until a specific backend deployment is authorized;
   production Railway follows main. Do not merge payment540 or Listener544 as a
   side effect. No frontend release is needed.
2. After exact-head CI/review, authorize only this backend source and its isolated
   deployment/rollback transaction; verify the actual served revision before use.
3. Bind one existing authenticated normal account by its authoritative internal
   ID (no wallet lookup or guessed identity). Retain normal entitlements and
   Reading Pass V2 enforcement. Establish no existing active V2/legacy session.
4. With separate scoped data/spending authority, insert the reviewed budget once
   using an authorized transaction: exact user ID/role and absence of the budget
   field, no upsert, unchanged balance fields. Pin the actual served edition.
   If any prerequisite/CAS fails, STOP. Never replace an existing budget, increase
   its maximum, zero consumption, or remove it to resume the same acceptance.
5. Verify only the inserted budget metadata through the approved protected
   mechanism. An active-session race is fail-closed by session/test binding;
   stop rather than adapt a legacy session. No synthetic credit or payment.
6. Complete the four-page journey under the one budget; retain actual responses,
   rendered source order, navigation/seek/persistence evidence and final settled
   consumption. On error/exhaustion stop, do not renew authority or top up.
7. Close/settle the session and retain the exhausted/expired budget. Do not delete
   the record as cleanup. Backend rollback must first close acceptance sessions
   and leave this account unavailable for metered acceptance until cap enforcement
   is restored; never run the test against a pre-cap backend.

## Proposed Désirée’s Baby acceptance — not a spending grant

Propose **180 cumulative wallet seconds maximum**, one normal-account test,
`content_type=text`, `content_id=dsires-baby`, exact serving manifest and
segmentation version verified by the existing authenticated caller. Four pages;
no inference of a source defect from differing pagination. Budget expiry:
15 minutes after the authorized enable commit, lease maximum unchanged (20s).
No transfer/restart resets, automatic retry, top-up, reward claim, payment,
entitlement override or frontend deployment. Use an existing legitimate
entitlement instead if it establishes a nonbillable route without modification.

The exact account ID and enable-time expiry are intentionally unfilled: no
customer identity/wallet was retrieved for this implementation. The remaining
protected actions are the explicitly authorized backend deployment, narrowly
scoped budget provisioning, and ONE account-bound capped-debit approval before
starting the paid journey. Do not represent this proposal as an enabled cap or
completed real-book acceptance.

## Protected operator and startup containment

`backend/reader_acceptance_operator.py` is the protected-runtime caller; it adds
no HTTP endpoint. The current acceptance selector is pinned by SHA256 (raw ID
remains in the task-owned verified selector receipt). Other selectors stop
before a database read. The caller fixes the title/test/canonical revision,
180-second total and900-second expiry. It projects no wallet fields, never
credits/grants access, and never resets/replaces an existing budget.

Use only an explicitly authorized existing Railway SSH identity via
`--via-railway --identity-file <approved-existing-path>` or an already approved
in-runtime administrative session. No key scan/registration or credential
acquisition is implemented. Exact project/environment/service/source identity
is required. Each mutation commits once; uncertain commit/remote timeout stops
and requires the status action, never a mutation retry. A retained disabled
budget still denies metered acceptance; no automatic account unlock/reset.

For this bounded deployment only, prepare the exact nonsecret variable
`READER_ACCEPTANCE_RELEASE_MODE=cap-only-v1` with `skipDeploys=true` before the
separately approved source deployment. Do not execute that setting now. The
mode suppresses both existing canonical bootstrap and general startup database
maintenance; normal absent-mode behavior is unchanged, unknown values stop
startup. This is not a claim that all normal operational startup effects stop.

The preflight action also qualifies rollback to the unchanged old backend:
original general maintenance must already be disabled, required canonical
indexes must exist, and every entry in the exact existing bootstrap plan must
already reach its preserve-pointer/active-version branch. It only reads these
metadata; no index creation, page generation, pointer activation or repair.
A missing prerequisite stops before production. Recheck immediately before
conditional rollback and exclude concurrent publication changes. No catalogue,
source or rights audit is introduced.

Enable requires absence of active V2/legacy sessions and the exact current
edition. Disable requires no unsettled session and an observed consumption CAS.
The separate `rollback-guard` action additionally blocks only the pinned
acceptance account before restoring a pre-cap backend; that availability change
must be in the eventual exact approval. It does not change wallet/entitlement
fields or automatically unblock. Unknown outcome requires scoped status-only
reconciliation. Retain all budget/session/ledger evidence.
