# CUSTOMER_READY completion ledger

Updated from released `origin/main` source `5ecd7f689ccabc7da4c8289b7fed6ed452e993c4`
(tree `dba7e1023743dfec3c60dc36028a8cba18900d4a`). This is a
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
| Journal and Journal article | Implemented locally but awaiting review-only CI | Focused Journal → article → Library fixture journey; current review-only source batch | Exact-head CI, visual package validation, and later public interaction observation remain pending | Complete the current review-only Journal batch; do not relabel fixture evidence as production acceptance |
| About, Contact, Micro Story, and 404/removed-route surfaces | Confirmed unfinished design acceptance | `editorial-support-route-map.md`; current route inventory | Existing routes and historical captures are not complete Quiet Heritage acceptance | Address one support/editorial journey in the next focused batch after Journal review |
| Catalogue release truth | Implemented and deployed | PR #364/365 released history and current canonical predicates | Mobile API-backed acceptance is still unavailable | Keep `PUBLIC_API_CORS_INTERMITTENCY_P1` and `MOBILE_ACCEPTANCE_PENDING` open |
| Public API browser readability | Blocked by an observed issue | Headed mobile reload observation; Railway had no matching upstream request | Narrow failure domain remains unproven without the sanctioned browser trace | Obtain and compare the sanitized failed headed-browser HAR or NetLog; no speculative change |
| Reading Pass v2 activation readiness | Unverified | Read-only Railway observation at `2026-09-08T05:44:57Z`: `READING_PASS_V2_ENABLED=false` | The observed disabled value is configuration state, not activation-readiness evidence; all-title segmentation and post-activation evidence remain outside this batch | Keep the flag unchanged and activation recommendation on hold |
| Production deployment / rollback | Implemented and observed for PR #366 | PR #366 main-push workflow `34196452256`; Vercel deployment `dpl_dTDU5bVt79ogYd3aAYqfZw5fmbSm` served alias `https://theearnalism.com`; known-good rollback target remains recorded separately | A later batch needs its own exact-candidate preflight and postmerge evidence | Revalidate provider source/rollback access before any separately authorized merge |
| Historical worktree preservation | Unverified | Existing recovery report and historical incident record | A clean later worktree does not explain the earlier disappearance | Preserve the incident as unresolved; do not overwrite unrelated worktrees |

## Program state

- `PUBLIC_API_CORS_INTERMITTENCY_P1=OPEN`
- `MOBILE_ACCEPTANCE_PENDING=OPEN`
- `READING_PASS_V2_ENABLED=false` observed read-only at `2026-09-08T05:44:57Z`;
  this is configuration state, not verified activation readiness or an
  activation decision.
- `CUSTOMER_READY=NOT_DECLARED`

The current implementation item is deliberately limited to the public Journal
→ article → Library discovery journey. It preserves public Header exclusion,
the real `/blog` data contract, and the existing Library route; it introduces
no authentication, entitlement, payment, or media behavior.
