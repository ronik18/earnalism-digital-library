# CUSTOMER_READY completion ledger

Reconciled at `2026-09-09T04:30:52Z`. The released frontend source is main
`ab24caddf0b51210acc15e6957cbcaf4e9a4c210` (tree
`a7b44064c800d239ae14c2df7a56292e82891920`). This ledger separates released
implementation, isolated evidence, and real production interaction; it does
not promote a route inventory or fixture capture into production acceptance.

| Area | Implemented/deployed | Isolated or fixture evidence | Production evidence | Remaining work / status |
| --- | --- | --- | --- | --- |
| Home, Library, Reading Passes | Yes | Responsive and CTA fixtures; current candidate System UAT | Main-push deployment/canary passed for the released source | `MOBILE_ACCEPTANCE_PENDING`; real mobile API-backed Library acceptance remains open |
| Book Detail → Reader | Yes | Canonical chapter mapping, protected-entry, denied, reload, Back, and keyboard journeys | No authenticated protected-page interaction | Requires an explicitly authorized consuming production session procedure |
| Book Detail → Listener / Listener | Yes | Navigation, unavailable/recovery, authorization-state, and manifest fixtures | Public recovery/navigation only; no successful authorized playback | Audio/session acceptance requires a separate authorization and released-audio precondition |
| Reader | Yes | Public pages 1–3, page-4 denial/authorized local flow, positions, duplicate/session-transfer and cache tests | No protected production session | V2 is currently disabled; protected production behavior is untested |
| Authentication, Account, My Library | Yes | Isolated routing/form/state tests | No production form or authenticated flow exercise | Product limitation: no saved-shelf/resume API. Positions are per account/content; reader preferences remain separate device-local settings |
| Journal → article → Library | Yes | Desktop/tablet/mobile fixture and keyboard/category tests | Published desktop route/navigation observed | Responsive production interaction remains unavailable in the permitted browser |
| About → Contact / Library | Yes | Responsive/contact-fixture validation | Public render/navigation observed; no contact submission | A production form mutation is intentionally untested |
| Micro Story, 404, retired 410, Journal missing article | Yes | Direct-status, font, recovery, noindex, keyboard, and campaign-query fixtures | Released PR #369 main-push canary covers removed-route/static SEO; public campaign check observed | Responsive/font-face production observation is limited to supported browser capability |
| Public Header, Footer, legacy reader/listener routes | Preserved by design | Regression and route checks | Header/footer public render observed where stated above | The released Bengali Reader-only query/classification repair is not an open defect. Header redesign remains excluded |
| Reading Pass authorization, settlement, audio, positions, cache | Service/contracts deployed; V2 disabled | Current candidate System UAT passed all 14 gates: 45-title isolated preflight, 51 backend-core tests, 34 V2-contract tests, 9 policy tests, 330 frontend tests, build, contracts, hydration, responsive, Chromium/Firefox/WebKit journeys, and contrast | No production authorization, payment, playback, or position mutation was run | Candidate evidence must be rerun against exact merged main after its test-only repair lands; production mutation tests need explicit owner authorization |
| Current frontend deployment | Yes | N/A | GitHub main-push run `34274857117` bound to `ab24cadd…` succeeded: regression job `102225239735`, Vercel deploy `102227024220`, and canary `102227604487` | Vercel’s deployed source identity is evidenced through this workflow binding; provider inspection does not independently expose a Git SHA |
| Current backend deployment | N/A—separate backend service | N/A | Railway production deployment `136e2460-f9d7-43b9-94a5-6235d12c5e2f`, source `b47ae96916adbd31f5baed182af76bde64980530`, two running instances observed | Backend is intentionally a separately deployed source; no equality with frontend main is inferred |
| Reading Pass V2 effective configuration | N/A | Local UAT enabled only in disposable services | `GET /api/reading-pass/config` at `2026-09-09T04:30:52Z` reported `enabled=false`, three public text pages, and zero public audio seconds | Configuration observation is not activation-readiness evidence or an activation decision |
| Public API browser readability | N/A | Local/API fixture coverage only | The headed Pixel reload interruption remains unresolved; Railway had no matching upstream request for the reported failure | `PUBLIC_API_CORS_INTERMITTENCY_P1=OPEN`; do not make a speculative CORS change |
| Mobile Library acceptance | N/A | Isolated mobile fixtures passed | Not completed in a headed real mobile context | `MOBILE_ACCEPTANCE_PENDING=OPEN`; direct API probes and hidden fallback DOM do not close it |
| Historical worktree preservation | N/A | Recovery records retained | N/A | Earlier disappearance cause remains unresolved; a later clean worktree is not explanatory evidence |

## Current review candidate

`4ed7523849f8a9159100dbbfe57a1246bcfccc95` (tree
`51884759e7fb7afab4a80ab95a264b8a45df0672`) contains only the demonstrated
UAT assertion repairs: the Journal 44px contract is now read from its CSS
authority, and all desktop/mobile Listening CTA assertions use the released
accessible name, `Discover listening`. The final attached-candidate System
UAT report `run-20260909T042900Z-88412` is `PASSED`; its SHA-256 report digest
is `841215edb34d810f5cd50c68851c67093248b97fd13653bebcb77672f50ff651`.
This is isolated review evidence, not exact-main or production evidence.
All later PR #370 changes are documentation-only, so the executable source at
the current review head remains the source tested at `4ed752384…`.

## Program state

- `PUBLIC_API_CORS_INTERMITTENCY_P1=OPEN`
- `MOBILE_ACCEPTANCE_PENDING=OPEN`
- `READING_PASS_V2_ENABLED=false` observed at `2026-09-09T04:30:52Z`; activation readiness is unverified.
- `CUSTOMER_READY=NOT_DECLARED`
