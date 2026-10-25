# Open Window audio acceptance cap — local implementation, not installed

The proposed authority permits at most 600 aggregate reading seconds and two
sequential successful audio-session starts, for the exact approved Open Window
package. Authority expires 900 server seconds after its creation. This is a
maximum, not an upfront debit or a promise that full playback will succeed.

`backend/audio_acceptance_budget.py` holds the exact title/UUID/package/descriptor
pins and a pure budget-object builder. It performs no database, provider,
credential or installation operation. There is no public budget-provisioning
endpoint and no live installation runner enabled by this change.

The trusted account record uses `reader_acceptance_budget` with schema
`audio-acceptance-budget.v1`. No client request can supply the record. Existing
text acceptance budgets retain their v1 behavior and their separate operator.

Enforcement reuses the existing Reading Pass transactions:

- Start validates account, title, immutable package, expiry and counters. A
  compare-and-set update reserves a start in the same transaction that inserts
  the session and audit record. An abort rolls back the reservation. Starts do
  not debit the balance. Zero-debit completed sessions still consume start slots.
- An existing active or paused session, including an expired but unsettled one,
  blocks the next start. Audio acceptance transfers are rejected; the normal
  explicit settlement path must finish first. No automatic acceptance settlement
  or transfer is performed to make room for a new session.
- Renewal and terminal settlement retain the native server-timestamp billing
  calculation, clamped by lease expiry, authority expiry, remaining balance and
  the same persisted 600-second allowance. Budget, wallet, linked debit records
  and session changes commit together. Counters are not reset on end or restart.
- Both bearer and media-cookie authorization retain their existing checks and
  revalidate the exact selected package for acceptance-bound media access.
  The start route binds the validated exact candidate without relying on the
  rollout cookie, whose path does not include the session-start endpoint.
  Protected media independently retains cohort selection and lease requirements.
- Legacy direct debit refuses accounts carrying any acceptance budget. Missing,
  malformed or changed authority on a bound session fails closed.

The factory is not an installation approval. Before any production use, review
the exact source, qualify a separate protected installer for the privately
confirmed account, require no conflicting budget/session, sufficient existing
balance, exact runtime/package and automatic deployments off. Never overwrite
an existing authority or reset its counters. Retain the record through complete
settlement/reconciliation. Removal or archival and restoring ordinary account
use require their own reviewed cleanup boundary; expiry does not silently erase
the record or reopen paid access.

Local validation used existing dependencies and an authenticated, disposable
loopback MongoDB replica set. The 129-test focused set passed, including actual
concurrent starts, renew/end races, full aggregate exhaustion and transaction
abort rollback. No production database or provider was contacted by those tests.
The new suite is included in `scripts/run_pr_regression_gates.sh` so its real
Mongo cases run in the existing isolated CI environment.

An additional historical `test_audiobook_package_v2_routes.py` run had ten
failures. An untouched-HEAD export reproduced those same ten failures (removed
descriptor helper / obsolete route fixtures). They were not changed or counted
as passing. Current B2 routing and the focused cap/lease suites pass.

No production budget has been installed, no deployment performed, and no paid
session started. This does not establish production playback/accounting PASS,
public activation, or an overall audio QA score.
