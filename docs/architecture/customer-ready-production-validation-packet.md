# CUSTOMER_READY production-validation packet

Prepared `2026-09-09T04:30:52Z`. This packet requests no execution. It is the
minimum concrete plan for production-only evidence that cannot truthfully be
replaced by fixtures, local UAT, or desktop probes.

## Current source and configuration observations

- Frontend: `ab24caddf0b51210acc15e6957cbcaf4e9a4c210`, tree
  `a7b44064c800d239ae14c2df7a56292e82891920`; GitHub main-push run
  `34274857117` completed regression, deployment, and canary successfully.
- Backend: Railway deployment `136e2460-f9d7-43b9-94a5-6235d12c5e2f`, source
  `b47ae96916adbd31f5baed182af76bde64980530`, with two running instances.
  This is a separate backend deployment, not evidence that it matches the
  frontend source.
- Effective public config at `2026-09-09T04:30:52Z`: V2 disabled, three public
  text pages, zero public-audio seconds. This observation is not authorization
  to activate V2.

## Production actions that require separate owner authorization

| Validation | Preconditions | Actions and expected observation | Mutation/consumption | Cleanup and stop condition |
| --- | --- | --- | --- | --- |
| Headed real-mobile Library acceptance | A real mobile-capable headed browser, cache disabled, and a reproducible browser network capture capability | Directly load and Header-navigate to `/library?language=bn&availability=reader-ready`; wait for `/api/books`; verify API-backed Reference Library, Reader-only eligibility, unfiltered Bengali `Coming soon`/`Notify me`, reload, filter, Back, and compact resize | None intended | Stop on a missing/failed browser request; retain timestamp, request outcome, and browser-visible headers. Do not inspect hidden fallback DOM |
| Text protected-page authorization | Explicit V2 activation decision; a specially provisioned non-customer test account; a reader-ready title with canonical page 4; an owner-defined balance cap | Record wallet/session state, sign in, explicitly choose the chapter continuation, verify only the exact authorized page renders, then end the session | Starts a metered session immediately and writes session/audit/possibly position records. The application cannot enforce an owner-defined spending cap by itself | `POST /reading-pass/sessions/end`, record post-state, and stop on any unexpected debit, wrong title/page, or denied response |
| Entitlement-denial behavior | A separately provisioned zero-balance or content-denied test account and the same approved test procedure | Request page 4 through the normal UI; expect the server-defined denial with no protected text | Authentication/audit records may be written; no access should be granted | Sign out; stop immediately if protected content, a lease, or balance change appears |
| Session locking, duplicate requests, and termination | Two approved isolated production test-device contexts, explicit balance cap, and owner approval for metering | Start one text session; issue an explicit second-device attempt and duplicate user action; verify server-defined lock/transfer semantics and final termination | Session and ledger mutation; metering can occur | End/revoke according to the documented API; stop on duplicate debit, concurrent grant, or failed cleanup |
| Payment/settlement | An existing provider-supported non-production payment procedure; no real customer payment | Exercise only the provider's approved sandbox/test path and verify idempotent settlement | Payment intents/ledger records may be created | Follow the provider test cleanup procedure. Do not substitute a real payment |
| Authorized Listener/audio | Explicit V2 activation and a released-audio title, plus a specially approved test account and bounded observation window | Verify unauthenticated audio remains unavailable; only after explicit authorization, verify server-authorized media handling and termination | Starting audio can create a consuming lease and audit/position state; zero public audio must remain true | End session and stop on any public byte, cross-account media access, or unexpected playback |
| Position/cache isolation | Explicit test-account authority and a procedure that permits position writes | Verify per-content position is restored only for the same account/content and cannot expose another user's protected content | Position records and cache entries may be written; this is not a saved-shelf API | Preserve the test record as audit evidence unless a separately approved cleanup path exists; stop on cross-account/cache leakage |

## Existing rollback procedure

Do not rehearse rollback. If an established release threshold is met, use the
verified Vercel recovery target
`https://earnalism-h6imjrup3-sales-8498s-projects.vercel.app` in the verified
project/team context:

```sh
vercel rollback https://earnalism-h6imjrup3-sales-8498s-projects.vercel.app
```

Then verify the resulting production-domain pinning, the source-bound
deployment identity, `/`, `/library`, the relevant recovery route, and the
normal health/canary probes. Rollback is not authorized merely to collect
evidence, and restoring automatic promotion needs a later deliberate release.

## Consolidated approval needed next

Before any consuming production test, the owner must separately authorize:

1. V2 activation or a valid existing test equivalent, if required;
2. named, non-customer test-account provisioning and an enforceable budget or
   balance cap;
3. the exact reader/audio title and bounded duration;
4. session, audit, position, provider-test, and cleanup mutations; and
5. rollback thresholds and the operator responsible for executing them.

Until then, `PUBLIC_API_CORS_INTERMITTENCY_P1` and
`MOBILE_ACCEPTANCE_PENDING` remain open, and `CUSTOMER_READY` remains
`NOT_DECLARED`.
