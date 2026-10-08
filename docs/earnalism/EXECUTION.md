# Earnalism execution ledger

Last reconciled: 2026-10-08 (Asia/Kolkata)
Integration source: `codex/main-approved-integration` at `4bcf50be32c4d8c72057a966e1b9f2a083b74e4c` (`origin/main` matched; tree `b10798afb3425972eb876e1a4ec0a992ea3317fb`).

## Product outcome and operating boundary

Earnalism is an India-only digital reading service for rights-cleared English
and Bengali editions. Its primary journey is: browse an approved edition →
read pages 1–3 where a preview is available → sign in and obtain/use a
Reading Pass → continue from page 4 under server-authoritative entitlement.
The current release configuration names 52 approved text editions and uses
`COMMERCIAL_ENTITLEMENT`; public audio remains disabled.

This ledger treats the current owner mandate and checked-in release controls as
scope. It does not elevate older ideas into requirements. The historical
ChatGPT share URL was fetched on 2026-10-08, but is a large client-rendered
serialization rather than a locally supplied, reviewable transcript; no local
`earnalism-conversation.md` exists. Therefore this ledger relies on the current
mandate and repository/runtime evidence for decisions.

### Current decisions and exclusions

- Reader territory is `IN`; do not infer worldwide rights or access.
- Audio is separately evidence-gated and remains disabled.
- The 52 configured titles are the current source allowlist; held/pipeline
  titles are not promoted by this work.
- Reading Pass continuation is commercial; public-domain/source status is not
  a reason to provide unlimited free access.
- This checkpoint authorizes reversible source/test/documentation work only.
  It does **not** authorize a production merge, deployment, content promotion,
  billing/policy change, destructive data work, or payment attempt.

## Evidence hierarchy and contradictions

| ID | Observation | Evidence | Consequence |
| --- | --- | --- | --- |
| E-01 | Current exact-main CI is green. | GitHub runs `37788505783` (backend container) and `37788505873`/`37789982519` (GO LIVE regression) all completed successfully for `4bcf50be`. | Strong source/CI evidence; not proof of an authenticated customer journey. |
| E-02 | The controlled launch mirrors 52 India text titles in commercial mode and keeps audio off. | `data/controlled_launch.json`, `backend/data/controlled_launch.json`, and `backend/tests/test_controlled_launch_parity.py`. | Release scope is source-defined and fail-closed. |
| E-03 | The public production payment configuration is live and returns four Reading Pass offers. | Read-only `GET /health`, `/api/payments/config`, `/api/payments/packs`, and `/api/reading-pass/config` on 2026-10-08. | Do not claim payment checkout is unavailable. No purchase, login, or wallet mutation was performed. |
| E-04 | Account source copy said purchases were unavailable while commercial mode is enabled. | `frontend/src/pages/Account.jsx` alongside current `PUBLIC_PAID_COMMERCE_ENABLED = true`; repaired in this candidate with a focused lifecycle assertion. | Source repair is locally verified; it is not yet deployed. |
| E-05 | The public site, Library, Pricing, Privacy, Terms and health endpoints returned HTTP 200 in a read-only check. | `https://theearnalism.com/*`, `https://api.theearnalism.com/health`. | Public reachability is verified only at HTTP level; browser hydration and authenticated flows remain unverified. |

## Task ledger

| Task | Outcome | Source / evidence | Status | Dependencies / areas | Acceptance criteria | Effort / risk | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EXE-001 | Preserve one authoritative integration baseline. | Clean `codex/main-approved-integration`, exact `origin/main`, no open PR. | VERIFIED_COMPLETE | Git/GitHub. | Clean checkout and exact SHA recorded. | Low / release-state drift. | Codex |
| EXE-002 | Keep the India Reader fail closed outside the approved commercial title set. | Mirrored launch JSON; parity tests; current launch jurisdiction `IN`. | IMPLEMENTED_UNVERIFIED | Backend release proxy, frontend launch mirror. | Authenticated India allow/foreign denial/held-title denial on production. | Medium / production auth. | Codex + founder-authorized test session |
| EXE-003 | Present truthful Reading Pass availability to a signed-in customer. | E-03/E-04; focused Account tests and production build below. | IMPLEMENTED_UNVERIFIED | `Account.jsx`, its focused tests. | With commerce enabled, Account never says purchases are unavailable; an actual availability failure remains distinguishable. | Low / copy regression. | Codex |
| EXE-004 | Protect payment, credit and entitlement accounting. | Production config is live; source has signed verification/webhook/idempotency paths. | IMPLEMENTED_UNVERIFIED | Razorpay, backend transactions, account/Reader. | Controlled end-to-end payment, duplicate webhook and refund/remedy checks in an approved non-production or explicitly authorized production procedure. | High / financial mutation. | Founder + external provider + Codex |
| EXE-005 | Deliver pages 1–3 preview and page 4+ only with a valid entitlement. | `ReaderExperienceV2Route`, reading-pass service, source contracts, exact-head CI. | IMPLEMENTED_UNVERIFIED | Reader, signed proxy, entitlement service. | Browser test of preview, denial, entitled continuation, reload and deep-link denial with no bypass. | Medium / authenticated session. | Codex + founder-authorized test session |
| EXE-006 | Maintain evidence-backed 52-title India catalogue. | Controlled publication packages, rights registry, parity tests. | IMPLEMENTED_UNVERIFIED | Catalogue manifests, rights decisions, canonical pages. | Per-title production readback of title, cover, metadata, chapter availability and India admission. | High / live data/runtime. | Codex + founder-authorized read-only session |
| EXE-007 | Keep public audio unavailable. | `public_audio_exposure_enabled=false`; empty audio allowlist; zero-preview tests. | VERIFIED_COMPLETE (source/CI) | Backend, frontend, controlled launch. | No audio control or endpoint is publicly admitted for the commercial release. | Low / regression. | Codex |
| EXE-008 | Preserve the legal/support surface. | `/privacy`, `/terms`, `/copyright`, `/contact` routes in `App.js`; public HTTP checks for Privacy/Terms. | PARTIAL | Frontend legal pages and direct-route hosting. | Browser direct-navigation and rendered-content check of all legal/support routes. | Low / browser-only verification. | Codex |
| EXE-009 | Preserve release safety. | `regression.yml`, `scripts/test_manual_production_release_workflow.py` (9/9 local pass). | VERIFIED_COMPLETE | GitHub Actions/Vercel deployment boundary. | Exact-main workflow dispatch rejects stale/dirty source and requires explicit confirmation. | Low / workflow change. | Codex |
| EXE-010 | Confirm normal Reader opening and page turns are not obscured by a full-screen turn loader. | `reader_opening_review_20261004.md`; current later Reader changes. | IMPLEMENTED_UNVERIFIED | Reader V2 and browser fixture. | Exact-current-head browser test for cold open, forward/back, rapid navigation and reduced motion. | Medium / runtime UX. | Codex |
| EXE-011 | Expand scope only through a reviewed title/access decision. | Existing held/pipeline records. | EXPLICITLY_DEFERRED | Rights, assets, territory, audio. | Separate accepted decision packet and release procedure. | Varies / rights. | Founder + Codex |

## Shortest safe sequence

1. **EXE-003:** complete its focused source repair and test. This is
   deterministic from current live configuration and changes no pricing,
   entitlement, or access policy.
2. Review the exact diff, commit it as one candidate, then prepare an
   unmerged PR with this ledger, release handoff, and
   the focused copy repair. Do not merge or deploy under this mandate.
3. After an explicit merge/deploy authorization, execute the release sequence
   in `docs/earnalism/RELEASE.md`; only then perform browser/authenticated
   customer and payment-safety verification.

## Current checkpoint

- **Branch / base:** `codex/main-approved-integration` / `4bcf50be32c4d8c72057a966e1b9f2a083b74e4c`.
- **Initial worktree state:** clean and aligned with `origin/main`.
- **Local checks:** Account/customer-copy tests 9/9 PASS; frontend production
  build PASS; static SEO verifier 172 snapshots / 3,647 assertions / 0 failed;
  release workflow and Vercel packaging guards 18/18 PASS; `git diff --check`
  PASS. The backend contract suite cannot run in this shell because
  `MONGODB_URL` is absent; this is an environment limitation, not a passing
  result. Exact-head hosted CI is green (E-01).
- **Candidate state:** PR [#524](https://github.com/ronik18/earnalism-digital-library/pull/524)
  is open from the canonical integration branch; its required checks are
  pending at this checkpoint. No merge or deployment was requested or made.
- **Next exact safe action:** wait for terminal checks on the exact PR head.
  If they pass, retain the PR for explicit merge/deployment authorization;
  otherwise classify and repair only an evidenced candidate defect.
