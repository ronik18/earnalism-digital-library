# Open Window protected entry, audit and fence/recovery qualification

Successor: `open_window_audio_cap_interlock_local.md` closes the local readiness
and installer-quiescence implementation gaps below. The 66-test evidence in this
document is historical; the successor passed 89 focused tests. Production
execution remains separately authorized and has not occurred.

26 October 2026. Local preparation only; no source publication, deployment,
installation, paid session or provider mutation performed.

## Implemented candidate

`backend/open_window_audio_cap_live.py` is an owner-operated callable, with no
CLI, API route, startup hook, credential acquisition or automatic invocation.
The installer entry remains disabled unless its explicit installation-authority
argument is exactly true. That argument is an operator confirmation, not an
authentication credential or substitute for approval.

The adapter runs outside the stopped service. It never imports `server.py` or
loads a configuration/secret file. It accepts an already-authenticated private
owner DB client; requires the exact `earnalism` database, identical client,
nonempty nodes matching an approved private fingerprint, owner-only account
input and reviewed source hashes. It checks a clean local source export/checkout
at the actual approved Git revision. No existing account identity, balance,
credential, node list or selector is included in output.

Railway reads bind the exact project/environment/service/deployment/revision.
They reject another/latest pending deployment, staged changes, auto-deploy on,
missing instance evidence or any running replica. Refreshes retain the original
outage deadline, never extend it, and require at least 30 seconds remaining.
The three direct/proxied health/config paths must positively return 502/503;
timeouts, redirects, 401 and 404 are not evidence of stopped traffic. Reads are
repeated before DB access, around the transaction and through committed readback.
This covers the selected serving deployment only. External DB writers must be
separately excluded; an owner-supplied Boolean alone is not independent proof.

The transaction uses snapshot reads, majority write concern and a 5-second
commit time limit. Readback now checks the exact audit event as well as budget
and installation receipt. Missing/changed audit stops with an uncertain outcome;
it never repairs or reinstalls. Existing maximum 600 seconds, two sequential
starts and original 15-minute authority remain unchanged.

`backend/open_window_audio_cap_recovery.py` prepares a separate-process deadline
supervisor. It durably reserves one restart with exclusive creation and fsync
before the provider call. Reservation/response uncertainty consumes the attempt;
there is no retry/reset. The adapter can restart only the exact pinned deployment
and read health; it has no rebuild, redeploy, rollback, secret/config write or DB
operation. It preserves the capped image and installed/uncertain authority.
Recovery health polling is read-only and bounded. Importing/constructing these
objects does not arm a supervisor or contact a provider.

The private recovery receipt binds source/deployment, restoration time, baseline
guard/health/Reading Pass status and writer exclusions. Hash/shape validation
does not prove a supervisor is alive. Before any execution the separately
reviewed operator must verify that the independent supervisor is armed and will
survive coordinator loss. A JSON assertion is insufficient. The local callable
is a reviewed candidate, not a claim that operational qualification is complete.

## Evidence and limits

66 focused tests PASS, including 13 authenticated disposable real-Mongo installer
scenarios, missing/changed audit, exact-target guards, recovery uncertainty,
durable no-overwrite restart reservation and an actual detached dummy supervisor
that completes after its coordinator exits. All provider interactions in tests
are synthetic. The earlier 129 cap tests are retained evidence; enforcement
policy/service/server and cap-test hashes are unchanged. The hosted regression
script now includes installer/live tests; hosted CI has not run for this revision.

Fresh read-only Railway CLI checks found the sole backend deployment
33023e20-5af4-460c-9e65-726a62ad2f62 SUCCESS, one RUNNING replica, source
f5ff5ddc4cc6132c32963e6bd7cc4d42c8da585b, no staged patch, auto-deploy OFF and
no newer deployment. Schema introspection confirms deploymentStop and
deploymentRestart each accept an exact deployment ID. The connector required
reauthentication; existing CLI authentication supplied the read-only fallback.
No provider variable values or credentials were requested.

The retained 23 October rehearsal stopped an earlier deployment and restored
health at 111.1 seconds. It is historical capability evidence only, not this
candidate's installation/fence test. Railway's deployment actions/reference
document restart of the selected deployment/process; they do not guarantee a
300-second recovery SLA:

- https://docs.railway.com/deployments/deployment-actions
- https://docs.railway.com/deployments/reference

## Execution holds

No production outage was authorized for this turn, so current-revision stop,
all-writer exclusion, live supervisor readiness and end-to-end restoration are
NOT DIRECTLY TESTED. The existing live revision does not contain cap enforcement.
Before execution: freeze reviewed source and exact merged revision; pass hosted
gates; qualify the protected private client/account and supervisor wiring; agree
the interruption/recovery procedure and installation timing. A bounded rehearsal
would require separate explicit operational authorization. No hard wall-clock
recovery guarantee is inferred from dummy tests or the historical rehearsal.

No paid start, public activation, storage/key work, automatic deployment or
cleanup is authorized by these files. Preserve capped enforcement after a
committed/uncertain installation; reconcile read-only rather than restoring
uncapped code. Preserve parked work and route all release decisions through the
single Integration Lane.

Next preparation prompt: Review and freeze the protected entry/source annex and
the owner-private supervisor/client wiring; prepare the exact bounded deployment,
fence/recovery and installation approval without executing it.
