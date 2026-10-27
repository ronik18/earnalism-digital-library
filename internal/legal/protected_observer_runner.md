# Protected observer runner integration

This successor integrates the #576 metadata observer with a concrete manual
GitHub Actions workflow and a read-only runner entry point. It cannot stage,
promote, deploy, roll back or dispatch another workflow. Current authority
continues to prohibit deployment, publication and paid sessions.

The workflow uses the existing `reader-frontend-production` environment and
noncanceling release concurrency group. It accepts only the exact dispatch
commit on this repository's `main` branch. The runner rechecks repository,
event, ref, controller SHA, clean checkout and the repository-bound application
contract trees before provider reads. Inputs cannot supply an approval receipt,
arbitrary source ref, command, journal directory or provider target. Actions are
pinned; credentials are scoped only to the observation step and never passed in
argv or retained in artifacts. The workflow uses a GitHub-hosted Ubuntu runner
for observation; it does not require a new persistent host. Pinned observation
tools are prepared before, and without, the provider-credential step. Railway's
official Linux archive is SHA256-pinned; Vercel's exact CLI version is pinned.
Existing production deployment workflows and
their approval pins are unchanged.

The observer now checks the reviewed Vercel59.25.4/Railway5.71.0 CLI versions
before fixed read commands. A timeout is a bounded HOLD with no retry. Reports
retain only allowlisted metadata; failure reports omit provider output and
exception messages. The only workflow artifact is that sanitized report.

The existing journal namespace remains fixed at
`/Users/ronikbasak/.codex/earnalism-release-journal/india-production`. The runner
does not create, clear, migrate or declare that directory durable. It rejects
symlinked, permissive, wrong-owner and workspace/temporary journal locations.
Unknown intents continue to block execution. Host persistence and protected
executor provisioning are external facts, not consequences of passing tests.

## Actual observations and remaining gates

Read-only GitHub inspection on28October2026 found the existing environment's
required-reviewer rule (one reviewer) and deployment branch restriction `main`.
It found zero repository self-hosted runners. That fact is retained, but is not
a blocker for nonmutating observation: the workflow now uses the existing
GitHub-hosted runner platform. No environment or runner registration was changed.

The actual local Vercel project JSON passed the new transport's scope checks.
The subsequent Railway CLI deployment-list call timed out at60seconds. No
retry was performed. The separate working Railway connector observation remains
metadata evidence only; it does not prove native CLI compatibility. The fixed
transport therefore remains operationally unverified until a separately
authorized protected read can complete. Offline command/schema/fault tests are
not a substitute for that read.

The bounded connector list still shows the historical565 backend as latest and
no new guarded containment artifact. Its `canRollback` flag cannot establish
source/config compatibility. Reuse #574's20 focused tests,12 selector tests and
v4 containment inventory within their original scope.

Remaining production-execution HOLDs are: an authentic protected write executor
and genuinely durable journal (the current file-journal design needs a qualified
persistent host); successful actual native transport observation; current reviewed
source-role/config/startup contract; a provider-built guarded artifact with
verified configuration/eligibility; and the existing protected rollback/release
approvals. Building/deploying that missing artifact is outside current scope.
The absence of a persistent write executor must not block read-only collection
or be presented as an unavoidable requirement to provision a new host. Hosted
observation leaves all write-executor and journal HOLDs intact and never creates
or clears a write intent. This workflow is code-ready for review, not
platform-executed or release-ready.
No workflow was dispatched and no provider/customer/financial state was changed.

The next Integration Lane action is to review this exact successor and reconcile
it into #576, then run required exact-head CI. Keep operational holds explicit;
do not dispatch or manufacture approval to clear them.
