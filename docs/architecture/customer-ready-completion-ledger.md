# CUSTOMER_READY completion ledger

Updated from released `origin/main` source `d626927c11d0d2e9596a097f299dfb13131938ef`
(tree `236727dcde3e81eae7f56e8343b24a0853721d39`). This is a
release-readiness ledger, not an activation decision: no
row below turns an earlier fixture, route inventory, or CI capture into
production-interaction or Quiet Heritage design acceptance.

| Required area | Current status | Evidence identity | Remaining work | Next action |
| --- | --- | --- | --- | --- |
| Home, Library, and Reading Passes Quiet Heritage surfaces | Implemented and deployed | Route inventory; prior controlled visual record; released main source | Real mobile Library acceptance remains separately held | Do not credit the held mobile check from static or fixture results |
| Book Detail to Reader handoffs | Implemented but awaiting production interaction evidence | PR #365 merged source `ce4f3646…`; released tree `0c63bf…` | Authenticated protected-chapter interaction is untested | Await an existing supported production-session procedure and appropriate owner authorization |
| Book Detail to Listener handoff | Implemented and deployed | PR #365 released main; PR #366 merge `5ecd7f68…` | Production listening authorization remains intentionally untested | Retain server authorization, no-playback, and lease boundaries; observe only under a separately authorized procedure |
| Reader immersive surface | Implemented but awaiting production interaction evidence | Current V2 route inventory and released main | Existing V2 preference bridge remains intentionally absent; protected access must be observed separately | Preserve legacy Reader preferences and classify the V2 limitation explicitly |
| Listener immersive surface | Implemented and deployed | PR #366 merge `5ecd7f68…`, tree `dba7e102…`, main-push workflow `34196452256` | Public unavailable/recovery and matching Book Detail navigation are observed; manifest failure and authorized-listener states remain fixture-only, and no successful playback is proven | Preserve the fixture/production distinction and await any authorized non-consuming production-session procedure |
| Auth, Account, and My Library | Implemented and deployed | Current route inventory; released My Library source | Saved library/resume APIs do not exist | Keep the truthful Library-next-read state; do not fabricate progress |
| Journal and Journal article | Implemented and deployed | PR #367 merge `db56bc02…`; tree `d024b0fa…`; main-push workflow `34212751223` | Desktop public Journal → published article → Library was observed; responsive category-control interaction is not verified in the available production browser surface | Retain the fixture/production distinction and obtain supported responsive interaction observation later |
| About and Contact | Implemented and deployed | PR #368 merge `d626927c…`, tree `236727dc…`; main-push workflow `34229025073` passed regression, deployment, and production canary; public navigation-only check reached `/library` and `/contact` from About and rendered the retained Header/Footer and Contact form | Production form submission was intentionally not run; responsive production interaction was not exercised in the available browser context | Preserve the isolated-fixture/production distinction and use an authorized procedure for any form mutation |
| Micro Story and 404/removed-route surfaces | Implemented but awaiting review evidence | Route map; source audit and local before-capture under the current review-only batch | The campaign and direct status documents had not yet reached Quiet Heritage structural acceptance | Complete the scoped Micro Story plus 404/410 recovery implementation, isolated capture, and fingerprint preflight |
| Catalogue release truth | Implemented and deployed | PR #364/365 released history and current canonical predicates | Mobile API-backed acceptance is still unavailable | Keep `PUBLIC_API_CORS_INTERMITTENCY_P1` and `MOBILE_ACCEPTANCE_PENDING` open |
| Public API browser readability | Blocked by an observed issue | Headed mobile reload observation; Railway had no matching upstream request | Narrow failure domain remains unproven without the sanctioned browser trace | Obtain and compare the sanitized failed headed-browser HAR or NetLog; no speculative change |
| Reading Pass v2 activation readiness | Unverified | Read-only Railway observation at `2026-09-08T05:44:57Z`: `READING_PASS_V2_ENABLED=false` | The observed disabled value is configuration state, not activation-readiness evidence; all-title segmentation and post-activation evidence remain outside this batch | Keep the flag unchanged and activation recommendation on hold |
| Production deployment / rollback | Implemented and observed for PR #368 | PR #368 main-push workflow `34229025073`; Vercel deployment `dpl_GFMXg2fJovHrDLXeMppwTHm1X5Tn` served `https://theearnalism.com`; regression, deployment, and production canary all passed | The preceding PR #366 deployment remains the known-good rollback target; a future batch needs its own source-bound preflight | Revalidate provider source/rollback access before any separately authorized merge |
| Historical worktree preservation | Unverified | Existing recovery report and historical incident record | A clean later worktree does not explain the earlier disappearance | Preserve the incident as unresolved; do not overwrite unrelated worktrees |

## Program state

- `PUBLIC_API_CORS_INTERMITTENCY_P1=OPEN`
- `MOBILE_ACCEPTANCE_PENDING=OPEN`
- `READING_PASS_V2_ENABLED=false` observed read-only at `2026-09-08T05:44:57Z`;
  this is configuration state, not verified activation readiness or an
  activation decision.
- `CUSTOMER_READY=NOT_DECLARED`

The current implementation item is deliberately limited to the public Micro
Story plus 404/410 recovery journey. It preserves the campaign Library source
parameter, public Header implementation, existing retired-route rewrites,
HTTP status/noindex behavior, and recovery destinations; it introduces no
authentication, entitlement, payment, or media behavior.
