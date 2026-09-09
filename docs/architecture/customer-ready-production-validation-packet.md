# CUSTOMER_READY production-validation packet

Corrected from read-only provider and source evidence at `2026-09-09T04:59:27Z`.
This packet requests no execution. It is the
minimum concrete plan for production-only evidence that cannot truthfully be
replaced by fixtures, local UAT, or desktop probes.

## Current source and configuration observations

- Frontend: `ab24caddf0b51210acc15e6957cbcaf4e9a4c210`, tree
  `a7b44064c800d239ae14c2df7a56292e82891920`; GitHub main-push run
  `34274857117` completed regression, deployment, and canary successfully.
- Backend: Railway deployment `136e2460-f9d7-43b9-94a5-6235d12c5e2f`, source
  `b47ae96916adbd31f5baed182af76bde64980530`, with two running instances.
  A read-only Git comparison of `b47ae969…` through released main `ab24cadd…`
  found no changes below `backend/`; that establishes backend-tree equivalence
  for the isolated UAT source, not that Railway has deployed current main.
- Effective public config at `2026-09-09T04:30:52Z`: V2 disabled, three public
  text pages, zero public-audio seconds. This observation is not authorization
  to activate V2.

## Required activation source decision

Any future activation must name the exact then-current merged-main SHA and
compare its `backend/` tree with Railway's reported deployment SHA before any
configuration change. The current comparison is clean, but the envelope still
requires a normal Railway source deployment followed by provider proof that
the resulting backend deployment reports that exact intended SHA. A branch
name, ancestry, or an unchanged frontend deployment is insufficient.

`railway redeploy --from-source` in the installed Railway CLI `5.41.0` has no
commit-pinning option. It is therefore **not an executable activation command
yet**: an operator must first verify that Railway's configured source resolves
to the approved SHA, then capture the new deployment ID, source SHA, image,
effective flag value, and the absence of other environment-variable changes.
If any of those prerequisites is unavailable, activation stops.

## Production actions that require separate owner authorization

| Validation | Preconditions | Actions and expected observation | Mutation/consumption | Cleanup and stop condition |
| --- | --- | --- | --- | --- |
| Headed mobile-capable Library acceptance | A headed mobile-capable browser context with cache disabled and browser-network visibility | Directly load and Header-navigate to `/library?language=bn&availability=reader-ready`; wait for `/api/books`; verify API-backed Reference Library, Reader-only eligibility, unfiltered Bengali `Coming soon`/`Notify me`, reload, filter, Back, and compact resize | None intended | Stop on a missing/failed browser request; retain timestamp, request outcome, and browser-visible headers. Do not inspect hidden fallback DOM |
| Text protected-page authorization | Explicit V2 activation decision; a specially provisioned non-customer test account; a reader-approved title with current canonical page 4; verified current manifest/release identity; an actually provisioned limited balance | Record wallet/session state, sign in, explicitly choose the chapter continuation, verify only the exact authorized page renders, then end the session | Starts a metered session immediately and writes session/audit/possibly position records. The application has no independent owner-cap control; the usable limit is only the balance actually provisioned to the test account | `POST /reading-pass/sessions/end`, record post-state, and stop on any unexpected debit, wrong title/page, or denied response |
| Entitlement-denial behavior | A separately provisioned zero-balance or content-denied test account and the same approved test procedure | Request page 4 through the normal UI; expect the server-defined denial with no protected text | Authentication/audit records may be written; no access should be granted | Sign out; stop immediately if protected content, a lease, or balance change appears |
| Session locking, duplicate requests, and termination | Two approved isolated production test-device contexts, explicit balance cap, and owner approval for metering | Start one text session; issue an explicit second-device attempt and duplicate user action; verify server-defined lock/transfer semantics and final termination | Session and ledger mutation; metering can occur | End/revoke according to the documented API; stop on duplicate debit, concurrent grant, or failed cleanup |
| Authorized Listener/audio | Explicit V2 activation and a released-audio title, plus a specially approved test account and bounded observation window | Verify unauthenticated audio remains unavailable; only after explicit authorization, verify server-authorized media handling and termination | Starting audio can create a consuming lease and audit/position state; zero public audio must remain true | End session and stop on any public byte, cross-account media access, or unexpected playback |
| Position/cache isolation | Explicit test-account authority and a procedure that permits position writes | Verify the per-content position API restores only the same account/content and cannot expose another user's protected content. Do not expect a saved-shelf/listing API or a My Library resume experience: neither is implemented | Position records and cache entries may be written | Preserve the test record as audit evidence unless a separately approved cleanup path exists; stop on cross-account/cache leakage |

## Nonproduction payment evidence

Sandbox/test payment and settlement behavior belongs to isolated evidence, not
to a proposed production transaction. The completed disposable UAT covers the
existing provider test path and idempotent ledger behavior. No real payment is
planned or required by this packet.

## Recovery boundaries and read-only-verified targets

Do not rehearse either recovery. A deployment rollback changes deployed code
or routing only. It does **not** reverse session, position, audit, payment, or
balance records. Those mutations require their own supported session
termination or provider/ledger reconciliation procedure and explicit approval.

### Frontend — Vercel

Read-only inspection confirms the retained frontend target
`https://earnalism-h6imjrup3-sales-8498s-projects.vercel.app` is deployment
`dpl_5HoT7GUgV9bsbakRKcqEfHXwXQLS`, `READY`, production-targeted, and aliased
to `theearnalism.com`. In the verified project/team context, the prepared
commands are:

```sh
vercel inspect https://earnalism-h6imjrup3-sales-8498s-projects.vercel.app --json
vercel rollback https://earnalism-h6imjrup3-sales-8498s-projects.vercel.app
vercel rollback status earnalism
```

After a threshold-triggered rollback, verify the resulting production-domain
pinning, source-bound deployment identity, `/`, `/library`, the affected
recovery route, and normal frontend canary probes. Restoring automatic
promotion needs a later deliberate release.

### Backend — Railway

The current active backend is `136e2460-f9d7-43b9-94a5-6235d12c5e2f` at
`b47ae969…`. The historical D0/D1/D2 anchor source is `ef7292a…`, but its
recorded deployments `817e76ce…`, `08dea9e4…`, and `94888291…` are currently
`REMOVED`; they are evidence of a past rehearsal, not an executable rollback
target. Railway CLI `5.41.0` exposes deployment list, upload, and redeploy,
but no deployment-ID rollback command. A backend fallback target and operator
method are therefore currently unavailable and must be read-only verified
before activation.

The merged envelope's sequence remains mandatory: set only
`READING_PASS_V2_ENABLED=false`, trigger a normal Railway source redeploy,
verify the intended source SHA/configuration/health, and only if that
configuration rollback fails restore a **retained** previous backend through
the provider-supported mechanism. Do not use an unpinned `--from-source`
redeploy as a substitute for source verification.

The prepared read-only probes after any authorized backend operation are:

```sh
curl -fsS https://api.theearnalism.com/healthz
curl -fsS https://api.theearnalism.com/api/reading-pass/config
```

The second probe must confirm the false baseline, three public text pages, and
zero public-audio seconds. It does not validate or reconcile account data.

## Consolidated approval needed next

Before any consuming production test, the owner must separately authorize:

1. the exact merged backend SHA, a provider source comparison, and a verified
   retained Railway fallback/operator method;
2. V2 activation and the merged envelope's false-baseline rollback sequence;
3. named, non-customer test-account provisioning with an actually provisioned
   limited balance (no unsupported cap mechanism is assumed);
4. the exact current reader/audio title, release/manifest identity, and
   bounded observation duration;
5. session, audit, position, provider-test, and cleanup mutations; and
6. rollback thresholds and the operators responsible for Vercel and Railway.

Until then, `PUBLIC_API_CORS_INTERMITTENCY_P1` and
`MOBILE_ACCEPTANCE_PENDING` remain open, and `CUSTOMER_READY` remains
`NOT_DECLARED`.
