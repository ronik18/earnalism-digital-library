# Earnalism release handoff

This document is a review/release checklist for the execution checkpoint
recorded in [EXECUTION.md](EXECUTION.md). It is not an authorization to merge,
deploy, publish another title, charge a customer, or alter live policy.

## Release candidate scope

| Task | User-visible effect | State |
| --- | --- | --- |
| EXE-003 | Removes stale “purchases are not available” wording from the enabled Account Reading Pass state. | Source complete; local verification complete; not merged/deployed |
| EXE-001 / EXE-009 | Records the exact source/CI/release guard evidence used for review. | Complete |

No title, rights record, cover, canonical text, access allowlist, audio state,
territory, commercial price, payment provider setting, or database record is
part of this candidate.

## Verified before a release decision

- Exact current main at the start: `4bcf50be32c4d8c72057a966e1b9f2a083b74e4c`.
- Current exact-main GitHub CI succeeded: backend container run `37788505783`;
  GO LIVE regression runs `37788505873` and `37789982519`.
- Release-workflow guard tests: 9/9 local PASS.
- Vercel packaging guard tests: 9/9 local PASS.
- Read-only production endpoints on 2026-10-08: public site routes and API
  health returned 200; payment configuration reported live/configured and the
  public pack catalogue returned four offers.
- Current candidate local checks: Account/customer-copy tests 9/9 PASS;
  frontend production build PASS; static SEO verifier 172 snapshots / 3,647
  assertions / 0 failed; release workflow and packaging guards 18/18 PASS;
  `git diff --check` PASS.

These observations do **not** prove an authenticated Reader or checkout
journey and do not authorize a live transaction.

## Required candidate checks

Run after the final candidate commit, not against the starting SHA:

1. `npm ci --prefix frontend --legacy-peer-deps`
2. Run the focused Account/customer-copy test(s).
3. `npm run build --prefix frontend`
4. `python3 -m unittest scripts.test_manual_production_release_workflow scripts.test_verify_vercel_packaging -v`
5. `git diff --check` and focused review of the final diff.
6. Obtain the normal protected PR CI for the exact candidate SHA.

The full backend/runtime suite requires the repository's isolated MongoDB and
Redis harness or hosted CI. A bare local shell with no `MONGODB_URL` is not a
substitute for that environment.

## Remaining release blockers and owners

| Blocker | Minimum action | Owner | Follow-up verification |
| --- | --- | --- | --- |
| Production merge/deploy authorization | Explicitly authorize the exact reviewed PR/SHA. | Founder | Protected merge and normal deployment workflow. |
| Authenticated commercial Reader evidence | Provide a sanctioned, non-destructive India test session/process; do not provide credentials in chat. | Founder / identity provider | Browse preview, page-4 denial, entitled continuation, held-title/foreign denial. |
| Financial path evidence | Choose an approved test procedure (provider sandbox or narrowly authorized live test) and refund/remedy handling. | Founder / Razorpay owner | Order, signature/webhook idempotency, balance credit, denial/retry, refund/remedy results. |
| Direct-route browser evidence | Run browser checks after the exact candidate is available. | Codex | Legal/support routes hydrate and render via direct navigation. |

## Normal deployment sequence after authorization

1. Confirm the PR head equals the reviewed SHA and all required checks pass.
2. Merge through branch protection; do not force-push or manually modify
   production.
3. Let the existing main workflow determine whether a frontend deployment is
   needed. The current workflow deploys frontend changes only after its exact
   main regression gate and its deployment-scope/credential checks pass.
4. Capture the resulting workflow, deployment status, deployed source identity
   if the provider exposes it, and canary outputs.
5. Run public browser smoke: Home, Library, Pricing, Privacy, Terms, Copyright,
   Contact and the Account copy state where a sanctioned session is available.
6. Run the signed-proxy Reader smoke only through the normal frontend path;
   retain an unsigned-backend denial as a separate negative test.

## Rollback approach

- For a copy-only frontend regression, revert the exact merged commit through
  the protected workflow and re-run the same CI/deployment canaries.
- Do not change the title allowlist, entitlement balances, payment settings,
  or rights records to roll back a copy defect.

## Approved work still beyond this checkpoint

EXE-002, EXE-004, EXE-005, EXE-006, EXE-008 and EXE-010 remain visible in the
execution ledger. They require the stated production/authentication evidence;
they are neither declared complete nor silently deferred by this candidate.
