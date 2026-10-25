# Owner-private wiring — frozen V2

No process is armed and no DB/client credential is captured by this package.
Use the same source copy at the approved merged revision in both owner-operated
processes. Keep custody files/socket outside Git and agent access. No fixture,
synthetic environment or test adapter may be used for production.

1. Privately initialize two independent existing-authority Mongo clients, one
per process/event loop, with retryWrites=False. Do not fork or share a Motor
client across processes. Establish the approved earnalism database and nonempty
node set privately; retain only the approved fingerprint in private inputs.
No Railway variable or provider credential is changed.
2. Construct exactly one interlock.Plan with the final revision/deployment,
one-time 32-hex run ID, fixed restore_at, frozen recovery-module hash, database
name and private node fingerprint. Both processes use identical Plan.digest.
Construct Gate(db,client,plan); constructor checks target and retry policy.
3. After authorization only, call Gate.prepare() once. This creates one OPEN
control document in the existing installation-receipt collection; no index or
new collection is provisioned. Retain an uncertain setup without retry/reset.
4. Choose the fixed T0 and restoration deadline once. Start recovery.supervise
in a distinct process/session with its own Gate, installer PID, private socket
path, new private restart-reservation path and exact-target provider adapter.
restore_at = T0+180s; supervisor monotonic deadline must map to this time within
one second. Provider read-only health deadline is T0+300s.
5. Call interlock.require_ready(socket,plan) from the actual installer process
before any traffic stop. It must answer a fresh challenge with the exact plan
and installer PID, different supervisor PID, live OPEN gate and pinned source.
The directory is owner-owned0700, socket0600. An expired/stale socket, copied
response or recovery receipt is insufficient. If not ready, do not stop traffic.
6. Build LiveApproval with exact installer/launcher hashes, private account
selector, private node fingerprint, plan.digest, fixed fence/restoration times
and private baseline/recovery receipt hash. Keep identity_path mode0600 and
account/credential data out of command arguments, output and evidence.
7. After all approved stop/fence gates, call execute_production with explicit
installation_authorized=True and the exact approval, private identity path,
client, db, recovery_receipt, interlock=that Gate and readiness_path=that socket.
The adapter repeats the live handshake, target/source and real provider fence
checks. It never imports server.py, opens credentials or starts a session.
8. At the fixed deadline, the independent supervisor closes that SAME DB gate
and verifies majority-acknowledged CLOSED state before its one reserved restart.
A late installer loses the transaction conflict; an earlier committed cap is
preserved. Failed/uncertain closure means NO restart. Never reopen the gate.

Argument provenance: final revision/deployment come from exact-source CI and
successful Railway deployment; source hashes come from SOURCE-ANNEX.json; private
account/node selectors come only from owner preflight; run ID is newly selected
once and retained; timestamps are fixed before arming. No actual private values
are included here. Source pinning and private preflight remain execution checks,
not reasons to repeat generation, storage or the accepted listening review.
