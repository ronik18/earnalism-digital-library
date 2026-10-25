# Open Window readiness and installer/recovery interlock

26 October 2026. Local implementation/test only. No production DB access,
supervisor arming, stop/restart, deployment, installation or paid session.

## Minimal change

One control document in the existing `reading_pass_acceptance_installations`
collection and one owner-local Unix socket replace the two missing assurances.
No new service, collection, index, account, key, subscription or audio work.

`open_window_audio_cap_interlock.Plan` binds the exact revision, deployment,
one-time run ID, restoration timestamp, supervisor source hash, database name
and privately approved node fingerprint. Neither private fingerprint nor owner
identity belongs in public evidence. Both independent clients must match the
same DB/plan and disable retryable writes. Existing records are never reopened.

`Gate.prepare()` creates one separately authorized control record as OPEN.
`Gate.claim()` requires an active Mongo transaction and changes OPEN to INSTALLED
inside the **same transaction** as the account budget, installation receipt and
audit. Recovery must change OPEN/INSTALLED to CLOSED with majority acknowledgement
and readback **before** reserving/calling its one restart. Snapshot transactions
and the shared document establish the ordering:

- Close first: stale/new installer claims fail; no budget transaction can commit.
- Install first: closure waits/serializes after that transaction; the installed cap is preserved.
- Abort first: the claim rolls back; closure prevents a later installation.
- Lost commit reply: closure still orders against the actual transaction outcome.
- Lost close reply or failed readback: no restart. Preserve evidence and reconcile read-only.

The gate is never reopened, deleted or reset. No process kill, guessed delay or
statement that a hung installer probably finished is needed. A late/suspended
installer cannot commit behind a verified closed gate. This is DB transaction
ordering, not a guarantee of provider recovery within a fixed time.

## Private readiness and wiring

The owner starts the supervisor in a separate process/session with its own
already-authorized private DB client. Credentials remain owner-only; clients
must not be reused across process/event-loop boundaries. Construction/import
does not connect, create a record or arm any timer.

`supervise(... interlock=gate, readiness_path=...)` binds the same revision and
deployment and checks the wall-clock restoration time against the fixed
monotonic deadline. It creates a fresh socket under an owner-owned mode-0700
directory, mode0600 socket, with source-hash and authenticated OPEN-gate checks.
`require_ready()` sends a fresh random challenge and requires exact plan,
installer PID, different supervisor PID and READY response. A saved JSON receipt,
stale socket, replayed response or shared-process callback is insufficient.

Before traffic stop the operator must perform this handshake. The live installer
performs it again before private account loading/DB installation. The socket
must remain outside the source checkout; stale paths are not reused. At its
fixed deadline the supervisor closes the DB gate, durably reserves one restart,
and restores only the same capped deployment. The challenge is not an auth token;
no credential, account ID or balance is sent through the socket.

## Validation

89 focused tests PASS on authenticated disposable loopback Mongo and dummy
provider adapters. Includes 20 real-Mongo cases in total (13 installer and seven
interlock scenarios), true separate-process readiness and failure after that
process dies, coordinator-exit recovery, closed/stale/wrong-plan/wrong-source
readiness, replay/permissions checks, exact DB/node binding and deadline binding.
Real transaction tests cover both ordering directions, a pre-close stale
snapshot, abort, lost closing/commit responses and no-overwrite setup.

Enforcement policy, Reading Pass service, server and original cap-test hashes
remain unchanged; their prior 129-test evidence is reused. Hosted isolated gates
now include the interlock test module; hosted CI has not run for this revision.
No dependency installation or production credentials were used.

## Successor release scope

The successor approval must explicitly include one temporary control-record
creation, its in-transaction claim and one majority-verified closure. No control
record cleanup is included. It must bind source hashes and require exact-head
CI/review, one merged-main backend deployment, startup/health, private target and
account preflight, and live readiness before any stop. These are execution
preconditions, not claims of tests already performed in production.

Keep the 600-second aggregate/two sequential starts/900-second authority unchanged.
The deployment/install approval itself authorizes no paid start or debit.
Automatic deployments remain OFF. Preserve all earlier freezes, journals,
storage objects, corrected master and operational security closure dispositions.

Next exact prompt: Review the frozen successor source and approve only its
bounded deployment, fence/recovery and one-account installation scope, with paid
sessions still held.
