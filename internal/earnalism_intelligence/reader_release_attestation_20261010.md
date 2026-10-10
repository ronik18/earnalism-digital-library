# PR528 attestation and separated frontend release qualification

Previous exact head: `4e8285caca684f0b697bbde9ca5cc27e1c06436a`.
Base remains `a8ecbacf2310e917071ef2b2c0b6063204814039`.
Owner authorized minimal additive runtime attestation, verification tooling,
workflow correction, tests, commit/push and fresh CI only. No merge/deployment,
provider configuration change or production Reader session is authorized.

## Serving identity

Existing production Railway deployment `0b00cce3-2f44-4721-87d9-8d3e620fc713`
is SUCCESS with one RUNNING instance, but no provider commitHash. Its CLI label
and a successful health response do not establish serving source. GitHub
production-deployment records inspected did not supply the missing linkage.
Therefore `/healthz` and `/api/healthz` add only `deployment` provenance:
status, provider Git SHA, deployment/project/service/environment UUIDs.
Missing or malformed provider values become null/UNAVAILABLE; no workflow,
local checkout, label, expected-SHA or timestamp fallback. Existing status and
replica fields, liveness and `/health` DB-ping behavior are preserved.
Attestation is no-store and makes no DB call. No new admin flow or secrets.
Provider variable documentation: https://docs.railway.com/variables/reference

The verifier independently GETs the approved HTTPS health/schema origin and
reads Railway production deployment metadata using the existing CLI credential.
It requires HTTP/provider revision, deployment and identities to match, SUCCESS,
running instance, no stopped deployment, no-store and the preparation schema.
Redirects and unavailable/malformed/stale/unhealthy evidence fail closed. It
does not attest its input. Credential errors are redacted. New attestation is
NOT yet serving production and positive live verification is NOT claimed.

## Production preflight read-only observation

At `2026-10-10T17:20:05.868086+00:00`, bounded metadata preflight returned PASS:
five required indexes present; 52 planned titles; no preparation/bootstrap
candidate; Agentic AI generation1 / 211 segments / manifest
`2d6e081a92bbeac0e5364cf2`; state digest
`ed619a46c84fac9c945bb9a142519eb3e578a8b0b3dfe59ed429302c2bf44010` unchanged.
The moved CI preflight enforces that baseline digest as well as individual
flags/index/content conditions. It reads metadata only, never imports startup,
creates indexes or changes publications. This is not a whole-business activity
freeze or a future production clearance. No balance/customer data read.

## Vercel effective suppression evidence

Provider project `prj_kxPN55TOJ23lDgoXIXrvqHtzy607`, configured root `frontend`,
linked repo `ronik18/earnalism-digital-library`, production branch `main`.
The effective config path is `frontend/vercel.json`; current protected main
contains `git.deploymentEnabled=false`, unchanged since commit
`39ddcb62a50e9a33df2584cb982bb5aab431c3d7` (2026-10-01).
Provider Git connection remains enabled; that does not negate the project's
file-based suppression. No deploy hooks. Latest50 provider deployments are all
CLI-origin, including30 production records spanning multiple main releases.
Latest production `dpl_Gq7ids4YRT8EowEjBgvj1Fugu97Q` is CLI-origin and binds base
a8ec. Repository deploy-route review finds only moved production CLI release;
packaging uses dry manifests; Railway deployment canary is read-only.
No alternate automatic production trigger observed in those inspected routes.
https://vercel.com/docs/project-configuration/git-configuration documents that
false suppresses all Git deployments even while the repository stays linked.

CONFIG_DECLARED=YES; CONFIG_APPLIES_TO_PROJECT=YES (provider root/main binding);
AUTOMATIC_PRODUCTION_TRIGGER_ABSENT=YES within inspected config/history/routes;
LIVE_SUPPRESSION_TESTED=NO new controlled push/deployment experiment.
No Git disconnection, root change, secret or provider setting change performed.

## Release graph and qualification

Main-push regression now contains only regression, checks and artifacts; no
deployment or environment hold. Railway source checkSuites remains true,
branchmain, backend root; provider staged changes null. Separate manual-only
workflow uses a dedicated noncanceling concurrency group; exact current main,
GITHUB_SHA and clean checkout gates precede credential use. Actual backend
identity/schema and read-only startup verification precede the owner-held
frontend job. Explicit bash/pipefail prevents tee from masking failure.
The protected job rechecks serving backend after owner approval and exact main
before build. Existing build/packaging/prebuilt deployment/canaries moved;
actual deployment project/READY/source metadata is checked after deploy.
Owner environment readback: ronik18 reviewer; main-only; self-review prevention
off under owner policy; administrator bypass disabled. Settings not changed.
Live manual hold execution remains UNVERIFIED until a later authorized release.
Vercel CLI is pinned63.1.2 in the moved workflow, not unbounded latest.

Newly executed local: workflow/identity/startup negative tests24 PASS; health,
preparation accounting and admin summary tests25 PASS; static SEO canary unit
tests28 PASS; YAML parse and shell-gate execution PASS; diff check PASS.
Inherited unchanged implementation: frontend101, backend115 (including26 real
Mongo concurrency), mixed-version and browser390/768/1440 qualification.
These historical runs are not claimed to test new health/workflow code.
Frontend production fingerprint recomputed with the existing generator:
`a7aa3f53b33024d70137b49ad1161292ed3b60e81f5860dc8925aee49422fd3b`, unchanged.
No fingerprint manually edited. Fresh head CI is required after publication.

No Reader/accounting/rights/content/publication/audio/territory behavior changes.
No title history decision is reopened. #525 remains parked. Owner acceptance
of the resulting exact head is required before merge; environment approval is
a separate later decision after actual backend verification.

Next action: publish only this successor to existing PR528, collect terminal
exact-head CI and prepare fresh owner acceptance; do not merge/deploy/accept.

## Exact-head CI import repair

Candidate c31fdf98 regression38071685406 failed isolated UAT health with500.
Reproduction without server startup or DB calls proved ModuleNotFoundError for
the container-only `utils` import under native `backend.server:app` packaging.
Added actual-handler ASGI package/container regression: 1 FAIL /3 PASS before
fix. Minimal import fallback supports both deployment layouts; 4 PASS after.
No liveness assertion weakened. Fresh head CI replaces the failed candidate;
original commit and its evidence remain preserved. No production change.

Candidate d5201ac5 regression38072219562 passed isolated UAT opening but failed
one stale static assertion expecting production-canary settings in regression.yml.
The authorized split moved those settings to reader-frontend-production.yml.
Updated the assertion to require the same production frontend/API targets there,
backend verification dependency and owner environment hold, and no hold in the
main-push regression workflow. All 64 static module tests newly pass locally;
the focused test also passes. Fresh successor CI is still required. No runtime,
production, Reader, rights or accounting changes were made for this correction.
