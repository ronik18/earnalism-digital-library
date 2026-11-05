# Public availability acceptance for any title

Use for a new title, publication-state change or release-contract correction. Resolve all identifiers from current canonical records; Open Window IDs, durations, budgets, voices and package counts are examples from one release, never future defaults.

## Before deployment: verify one complete contract

Trace the title's current supported path: source publication decision → catalogue projection → HTTP response schema → client mapping → public Reader-manifest enrichment → Library/Book presentation → Listener admission. Inspect the actual code and current API shapes; do not assume every future title uses protected package v2 or the same framework.

For the active delivery format, test the actual HTTP boundary and feed its response and the actual public-manifest shape into the customer composition. Preserve safe delivery mode, immutable package identity and measured duration where required; omit private provider/origin/rights/receipt data and preauthorization playable URLs. A pure projection or isolated release helper test cannot prove the composed path.

When protected package delivery intentionally hides its provider, require the repository-supported matching canonical/manifest identity and release contract. Do not revive disabled canonical audio from manifest data. Keep unrelated titles, revoked rights, wrong slug/version/mode and failed QA denied. Preserve legacy formats independently; a fix for one supported format must not globally enable audio.

Test the actual lookup with a dummy database row carrying a stale approved legacy conveyor, through the unmodified finder, canonical merge and HTTP serialization. Valid exact protected package truth must survive; missing/corrupt/revoked bindings and explicit canonical denials must not fall back to old database audio. Preserve legacy-format behavior. Test the observable result: the approved title offers its listening entry; a denied title does not. Metadata must not overwrite a current canonical denial or silently clear a valid canonical package binding. Check the actual Book merge/presentation path, not just authorization in isolation. Include the compiled frontend protected-title allowlist and native static SEO generator/verifier; updating backend JSON alone does not update the deployed frontend. Keep global audio exposure off and deny unrelated titles. A frontend change needs its own exact-source build/candidate; an unchanged backend needs no redeployment.

## After deployment: separate evidence by surface

| Surface | Acceptance evidence |
|---|---|
| Deployment | Exact changed-service merged source, startup/database health; tested candidate and both production aliases. An unchanged service can retain its recorded qualified deployment. |
| Public catalogue / Library | Title discoverable under the intended territory and audiobook filter; correct listening state, correct destination and cover. No inherited private cohort required. |
| Public Book | Fresh normal navigation shows listening entry and truthful release copy. Follow it to the correct Listener without authorizing playback. Verify any Reader/manifest enrichment has settled. |
| Listener | Correct title, complete measured duration, chapters, narrator/disclosure where supported, approved cover and expected sign-in/pass/authorization presentation. Do not click the billable authorization control under no-paid-session scope. |
| Covers | Approved exact front/back versions and full-byte hashes, plus actual customer rendering where the product exposes each side. A URL or thumbnail alone does not prove full-byte identity; bytes alone do not prove rendering. |
| Protected access | Normal guest/expired/no-lease requests receive intended denials. Use trusted normal proxy/provider-supported preview access; never forge territorial or authorization headers. |
| Playback/accounting | Applicable genuine evidence bound to edition/package and runtime dependencies, with exact limits on reuse. No new playback claim from read-only checks. |

Inspect the current supported routes rather than treating all manifest responses alike. In the existing route family, public Reader `/api/reading-pass/books/{slug}/manifest`200 is expected; protected AUDIO `/api/reader/book/{slug}/audiobook/manifest` without a current lease must return the application's intended AUTH_REQUIRED401. Provider login HTML or a provider-level401 does not establish that denial. Record actual expected response bodies/statuses through supported preview access; do not claim an unverified redirect passed.

Public navigation may be anonymous while playback requires existing Earnalism authentication and an authorized Reading Pass session. That is expected; do not introduce a second audiobook login. A visible authorization button is not a started listening session.

If any surface disagrees, record its actual response and visible result, keep LIVE held, locate the earliest broken boundary and fix narrowly. Compare list, detail and public Reader-manifest responses before blaming presentation. Check actual cache namespace/generation and TTL; one bounded check after expiry can distinguish stale data, but persistent disagreement is not automatically a cache problem. For changed projection semantics, update the supported cache contract/version and focused fixtures together; do not broadly flush shared caches or alter customer data as a diagnostic. Do not repeat generation, uploads or unaffected deployments. Preserve an already promoted release unless rollback is actually warranted by impact and existing authority; do not launch repeated promotions as a diagnostic.

## Completion wording

Declare public GO LIVE only when discovery, Book listening entry, Listener availability and approved covers are verified for the intended territory and supported format, and relevant genuine playback/accounting evidence still applies. State when playback evidence was reused and which devices/apps or historical audits remain unverified. Never describe a finite test matrix as all possible billing cases or universal fraud prevention.

At an incomplete gate, name the single current blocker and next supported action. Keep old failures as history, not active prerequisites after their exact correction is qualified. Update an existing monitor/checkpoint so later runs cannot remerge, redeploy or reupload completed work.
