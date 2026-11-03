# Sredni stable-account source authority v2 — design only

Status: PREPARED_FOR_ROOT_REVIEW; NOT_IMPLEMENTED. Integration alone owns canonical source. This packet does not assert merged, deployed, startup-qualified, granted, or playable state.

The authentic owner receipt is 43000292c34c7398e35425e4486796d0e16f617d8e155abc0ad147acc15cfeb3. Root reports the approved read-only snapshot completed with explicit abort, no retained cap, and zero scoped metadata/session/ledger records. Those are Root-reported actual facts, not this lane's inspection of private rows. Root also observed the same account UID with a changed normal SSO SID. Neither private identity file nor Mongo profile was opened by this lane.

## Source authority interface

Replace only the dedicated source allowlist schema with:

    {"schema":"earnalism.sredni_initial_review_authority.v2","accepted":[
      {"owner_receipt_sha256":"<exact owner receipt SHA>",
       "member_account_sha256":"<Root-selected stable account SHA>"}
    ]}

The placeholders above describe field types; they are not an authority file or usable values. No positive account digest is supplied by this design.

Add member_account_binding(user_id), using the existing digest() canonical JSON implementation (sorted keys, compact separators, UTF-8, ensure_ascii=False, allow_nan=False):

    digest({"schema":"earnalism.sredni_initial_review_member_account_binding.v1",
            "user_id":user_id})

Require a nonempty string UID. Root computes the genuine account digest privately from the already approved intended account and externally selects its actual receipt/hash. No raw UID, SID, or private identity receipt content enters Git. A stable account digest remains internal pseudonymous evidence and must not enter public API metadata.

load_authority() accepts v2 only; top-level and row key sets remain exact, SHA formats and pair uniqueness remain strict. Preserve the prior v1 EMPTY file and its frozen receipts as history. Do not fall back to v1, accept mixed schemas, rename an old identity_binding_sha256 value, or reinterpret either historical SID digest as account trust.

authority_allows(grant_or_admission) first recomputes the unchanged full identity_binding(user_id, auth_session_id), requires exact equality to identity_binding_sha256, and then matches the owner receipt plus recomputed member_account_binding(user_id) against the v2 source pair. A supplied member_account_sha256 on a request or grant is never trusted. The source pair grants no access by itself: existing fresh private owner/current normal-API evidence, runtime/startup/recovery/IN rights qualification, and typed grant resolution remain mandatory.

## Unchanged runtime identity and financial contract

No grant, workflow, operation, session, or typed budget schema migration is needed. Existing immutable UID, SID and full identity digest comparisons stay exact. member_budget continues to query the exact current SID; resolve still validates the actual active user_session and user's active_user_session_id, auth deadlines, grant state/epoch, workflow revision and original expiry. A re-login does not rewrite a grant or workflow. The source allowlist expresses which approved account may be considered; the grant still authorizes only its one actual SID.

Keep the deterministic workflow ID exactly as implemented: owner receipt + UID + exact slug/descriptor/package, excluding SID. Keep 60,000,000 cumulative eligible microseconds AND 60 cumulative posted credit seconds (stricter remaining), three atomic starts, and one original window no longer than 900 seconds. Normal wallet, ledger, carry, BSON precision, settlement and transaction behavior stay unchanged. No ReadingPassService, server, Listener, original two-title120, global cap, or ordinary-path change is proposed.

## One-grant provision guard

The current private operator has a same-window regrant branch. Actual owner approval permits maximum_grant_provisions=1. Narrow provision to a first grant only: before inserting or updating anything, require workflow absent, no retained grant of any state/malformed linkage, and no retained same-owner/account operation or dedicated session/ledger/transaction workflow reference under the existing strict history guard. A retained workflow alone is enough to deny new provision. Remove the regrant branch; do not reset, migrate, extend, or recreate counters. Namespace preparation/initial observation do not insert a workflow/grant operation row and remain separate existing actions.

Perform these checks inside the existing transaction. Concurrent first provisions contend on the same deterministic workflow _id; only one may commit, and the loser is not retried. Unknown commit remains status-only through the existing permanent local attempt, never a new provision. Do not turn any retained-history denial into an ordinary uncapped fallback.

## Re-login behavior

1. Before any grant: same UID plus a fresh current SID may pass the source account pair, but still requires genuine fresh private identity/execution admission and complete empty-history qualification. No grant/access is implied by the source pair.
2. After first grant: another SID cannot select/use the old grant and cannot create a new workflow/window/grant. Existing counters, original expiry and full identity are preserved, even after settled close.
3. Another UID: denied even if it supplies the accepted account digest or recomputes its own valid full SID digest.
4. Historic settlement retains the existing bounded terminal-accrual rules; source account trust does not change the old grant's cutoff or financial history.

Known limitation: the existing close path requires the original full admission identity and current member association. A SID rotation after provision can leave close HOLD. This proposal does not authorize changing close identity, moving a grant, reopening access, or introducing a migration framework. Read-only status of the original immutable attempt may still use the existing non-current-auth status path. No grant exists in Root's actual initial snapshot, so this design needs no existing-record migration.

## Finite implementation and verification scope

Expected production paths after Root's design acceptance: backend/sredni_initial_review_scope.py (helper/parser/matcher), backend/data/sredni_initial_review_authority.json (explicit v2; actual pair only through Root-selected proof), backend/sredni_initial_review_operator.py (strict one-grant branch). Update only directly affected synthetic authority fixtures/tests. The parser in sredni_initial_review_authority.py should need no behavior/schema change because it already calls authority_allows with full UID/SID evidence; verify this rather than broadening it. Reuse unchanged service/API/old120 evidence by exact hashes.

Required focused cases:

- v2 EMPTY denies before private profile/client; absent, v1, mixed-row, extra-key, duplicate, invalid-SHA and renamed old SID-hash rows deny.
- Accepted owner + exact account UID succeeds at source eligibility for each of two genuine-shaped synthetic SIDs only when each full UID/SID digest is recomputed correctly; malformed/copied full identity denies.
- Other owner/UID denies, including copied accepted hash and a separately valid full identity digest. No caller-supplied account hash can override recomputation.
- Typed member access still requires the exact grant SID and current active DB SID; guest, expired/revoked/wrong SID remain denied.
- Same UID re-login after one grant: no new provision/write/window/counter reset; old grant access denied for new SID. CLOSED, REVOKED, malformed grant, missing workflow plus surviving operation/reference, and workflow-only history all deny new provision.
- Same SID re-provision also denies; actual one-grant authority is not weakened to same-window regrant.
- Two first-provision transactions cannot both commit; loser/unknown commit uses existing status-only recovery, not replay. Retain meaningful real-Mongo concurrency coverage in the existing harness; supplied but unexecuted tests are not a Mongo PASS.
- Original workflow original expiry, all usage/start counters and normal fractional carry/posted debit remain byte/value conserved on all denies. Existing 60/3/900 and original120/ordinary compatibility tests stay passing.
- Settled close and original immutable status continue on the original SID when permitted; rotated-SID close remains an explicit HOLD.

No live proof, source compile, test execution, source mutation, authority population, grant or new allowance is performed by this packet. Next action: Root accepts/revises this finite design, then assigns Integration the three production paths and affected tests against its actual current dirty/source state; do not overwrite whole files from this private predecessor.
