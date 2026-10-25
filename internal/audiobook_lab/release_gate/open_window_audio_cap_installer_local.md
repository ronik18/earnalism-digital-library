# Open Window cap installer candidate — local preparation only

`backend/open_window_audio_cap_installer.py` is a protected installer candidate,
not a public/admin API, CLI, startup hook, deployed feature or installation
approval. `execute_production()` stops by default with
`PRODUCTION_ENTRY_NOT_ENABLED`; the prepared explicit-owner entry is described in
`open_window_audio_cap_live_local.md`. No reviewed enforcement commit has yet been
published or deployed. The existing live backend does not contain this cap.

The enabled test adapter accepts only an authenticated disposable loopback
replica set and the registered synthetic namespace. It rejects other targets
before a database command. All tests use synthetic account identities. No
production connection, read, installation, provider event or earlier one-shot
authority has been exercised by this preparation.

The runtime predicate checks exact project/environment/service/deployment and
the separately approved enforcement revision, rejects the known pre-cap base,
and matches the three existing enforcement source hashes plus the reviewed
installer hash. It requires the cap-capable Reading Pass service. The account
ID is supplied through an owner-owned, mode0600, regular non-symlink JSON file
with only `user_id`; it must match a privately held approved selector. No
customer identity, selector, balance or credential belongs in a handoff/report.
The module neither acquires credentials nor opens connections.

Installation requires a separately qualified external traffic fence, held from
preflight through committed readback. Its proof must be fresh and bound to the
same revision/deployment, with automatic deployments off. Validating the proof
shape does **not** prove that provider traffic is stopped. A caller-supplied
Boolean alone is insufficient authority. The future protected launcher must
verify actual provider quiescence and read the actual runtime environment; no
such live launcher is enabled here. This fence is needed because ordinary
uncapped starts do not necessarily write the account row and cannot safely be
assumed to serialize with an installer transaction.

The transaction refuses an existing budget of any kind, a legacy active-session
marker, active/unknown/unsettled sessions, insufficient existing balance or a
balance-mirror mismatch. It never settles a session, creates a session, grants
balance, changes entitlement or creates/repairs indexes. The only initial
account change is a no-overwrite CAS that adds the exact 600-second/two-start
authority; its receipt and audit event commit atomically. There is one commit
attempt and no automatic mutation retry. An uncertain commit or committed-but-
unverified readback stops with a sanitized unknown outcome; no repair, reset,
reinstallation or old-state restoration follows.

An already matching receipt is a read-only idempotent observation, preserving
advanced counters and original expiry. Conflicting receipts, missing authority
or changed scope stop. Sanitized readback contains only limits, counters and
expiry. Authority remains retained through terminal settlement and accounting
reconciliation. Cleanup/archive and restoring ordinary account use are separate
protected boundaries and are not implemented by this installer.

The new installer delta passed29 focused tests, including11 authenticated real
MongoDB scenarios for idempotency, no-overwrite, active/unsettled refusal,
duplicate installation, rollback on fence loss, ambiguous commit and failed
readback. All six existing source pins still match the accepted129-test report;
those tests and the known historical baseline failures were reused, not rerun
or modified in that historical run. The current successor includes explicit
audit readback and isolated hosted gate wiring; its focused local evidence is in
`open_window_audio_cap_live_local.md`. Hosted execution/publication is pending.

Remaining production gates: freeze a reviewed enforcement/installer revision;
qualify its protected live launcher and actual traffic-fence procedure; privately
bind the owner account and verify absence of conflicting authority; obtain exact
deployment/installation/interruption approval; then qualify sanitized readback.
No installation, paid playback, flags, source publication, merge, deployment or
public activation is authorized by this preparation.
