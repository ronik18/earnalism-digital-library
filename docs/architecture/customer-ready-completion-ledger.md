# CUSTOMER_READY completion ledger

Updated from the released `origin/main` source `ce4f3646e0963e78cf12664c247a14c811f60d45`
(tree `0c63bf4691ca3b108a328482adb560b34b28fd4f`). This is a release-readiness
ledger, not an activation decision: no row below turns an earlier fixture,
route inventory, or CI capture into production-interaction acceptance.

| Required area | Current status | Evidence identity | Remaining work | Next action |
| --- | --- | --- | --- | --- |
| Home, Library, and Reading Passes Quiet Heritage surfaces | Implemented and deployed | Route inventory; prior controlled visual record; released main source | Real mobile Library acceptance remains separately held | Do not credit the held mobile check from static or fixture results |
| Book Detail to Reader handoffs | Implemented but awaiting production interaction evidence | PR #365 merged source `ce4f3646…`; released tree `0c63bf…` | Authenticated protected-chapter interaction is untested | Exercise only with separately authorized non-consuming production access |
| Book Detail to Listener handoff | Implemented and deployed | PR #365 released main and main-push workflow `34186960477` | Visible Listener manifest/unavailable recovery and duplicate explicit authorization guard are not yet implemented | Complete the focused Listener recovery batch and validate with isolated fixtures |
| Reader immersive surface | Implemented but awaiting production interaction evidence | Current V2 route inventory and released main | Existing V2 preference bridge remains intentionally absent; protected access must be observed separately | Preserve legacy Reader preferences and classify the V2 limitation explicitly |
| Listener immersive surface | Confirmed unfinished implementation | Current `ListenerExperienceV2Route` source audit | Failures can collapse into redirects and duplicate explicit authorization can start duplicate requests | Focused recovery-integrity PR; no release authorization implied |
| Auth, Account, and My Library | Implemented and deployed | Current route inventory; released My Library source | Saved library/resume APIs do not exist | Keep the truthful Library-next-read state; do not fabricate progress |
| About, Journal, Journal article, Contact, Micro Story, and 404/removed-route surfaces | Implemented but awaiting production interaction evidence | `editorial-support-route-map.md`; current route inventory | Direct public interaction and responsive observation are not current release evidence | Include representative live paths in the later production observation run |
| Catalogue release truth | Implemented and deployed | PR #364/365 released history and current canonical predicates | Mobile API-backed acceptance is still unavailable | Keep `PUBLIC_API_CORS_INTERMITTENCY_P1` and `MOBILE_ACCEPTANCE_PENDING` open |
| Public API browser readability | Blocked by an observed issue | Headed mobile reload observation; Railway had no matching upstream request | Narrow failure domain remains unproven without the sanctioned browser trace | Obtain and compare the sanitized failed headed-browser HAR or NetLog; no speculative change |
| Reading Pass v2 activation | Unverified | Read-only Railway variable observation: `READING_PASS_V2_ENABLED=false` | Activation, all-title segmentation, and post-activation evidence remain outside this batch | Keep the flag unchanged and activation recommendation on hold |
| Production deployment / rollback | Implemented but awaiting later release observation | PR #365 main-push workflow `34186960477`; verified known-good deployment and prepared rollback procedure | Future batches need their own exact-candidate preflight and postmerge evidence | Revalidate provider source/rollback access before any separately authorized merge |
| Historical worktree preservation | Unverified | Existing recovery report and historical incident record | A clean later worktree does not explain the earlier disappearance | Preserve the incident as unresolved; do not overwrite unrelated worktrees |

## Program state

- `PUBLIC_API_CORS_INTERMITTENCY_P1=OPEN`
- `MOBILE_ACCEPTANCE_PENDING=OPEN`
- `READING_PASS_V2_ENABLED=false` as a read-only configuration observation; this
  is not an activation decision.
- `CUSTOMER_READY=NOT_DECLARED`

The next implementation item is deliberately limited to Listener recovery
integrity. It must preserve public Header exclusion, server-authoritative
authorization, zero public audio preview, and existing Reader preferences.
