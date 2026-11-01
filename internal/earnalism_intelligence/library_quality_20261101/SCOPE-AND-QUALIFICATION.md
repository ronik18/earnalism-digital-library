# Library quality release — 1 November 2026

Owner scope: one PR from latest main; optimize Library loading, unique audiobook cards, complete discovery facets, accurate literary copy and existing warm gold action links. Root is sole Integration Lane; parallel preparation is read-only/frozen after root adoption. Base 59c9613cb654649b6d18d8209323075fd1a2a17b. Preserve PR600, parked529, dirty canonical work, all live covers/audio and free Reader entitlements.

## Findings and changes

The Library waited for optional Home curation and mounted a CSS-hidden legacy full catalogue. It now requests only books with a 15-second bound, cancellation/stale-response protection and explicit retry; empty/error responses cannot revive bundled cards. The active shelves partition readers, audio editions and preparation candidates, so a book appears once. Approved public audio links retain protected Listener destinations. No auth/financial transport or entitlement is changed.

Discovery metadata covers all 52 live editions: 9 Bengali/43 English; 17 novels or novellas, 27 short stories or collections, 6 nonfiction and 2 essay editions. Language is bound to retained accepted Reader manifests; form/genre are editorial discovery labels, never release or rights authority. The matrix checks 2160 language/form/status/genre/sort combinations. URL history, legacy aliases, literal queries and unknown/malformed input are covered separately. Supported runtime metadata wins only when valid.

Shared accurate access copy preserves free Reader exceptions, three canonical preview pages on eligible editions, active-pass released audio, online consumption, one-time prepaid passes and no automatic renewal. No guaranteed earnings or unsupported universal-device claim is introduced. SEO generation and verification share this contract, require strict commerce state, preserve legal notices/robots/canonicals and do not invent a full-book free flag. Action gold is #D4AA5E with #35231B text, dark border, 44px targets and scoped focus. Computed browser color matches; text contrast 6.90:1, hover 8.57:1.

## Cleanup disposition

157 canonical publication manifests: 52 exposed approved Readers, 101 blocked/hidden, 4 ready for approval. Blockers overlap: missing covers (85), unapproved rights verification (30), missing publication year (13), one unresolved modern translation. 71 blocked records already have approved rights and 100 have passed text QA. None has an evidence-backed terminal retirement decision. Therefore zero permanent full-title/resource deletions are eligible. Do not equate a remediable release hold with permanent impossibility. Hidden resources, masters, rights records, versions, journals, entitlement and financial records are preserved. No cloud storage/cost savings are claimed. Confirmed unused hidden UI rendering is removed. Future irreversible retirement requires exact identity/version/reference/retention inventory and an audit tombstone.

## Evidence boundaries

Anonymous before samples: Library HTML TTFB 0.148–0.150s; books API 0.502–1.859s; optional curation 0.367–2.021s. Small network samples are not browser LCP or cache-hit proof. Removing a request barrier and hidden rendering is verified; no invented global bundle saving. Local browser uses actual production React build and captured public metadata, not production playback/billing evidence. Exact-head CI, published review, merge tree equality and qualified manual frontend-only release remain required. Auto-deploy remains off; no Redis/settings/index/audio/paid-session mutation.

## Final reconciled source qualification

Reconciled normally with merged #614 (f5706d328e08ab330f65f604f51df322b65646f1), preserving continuous-master adoption, current cover/rights bindings and both regression sets. Book detail and Book JSON-LD now use the same discovery taxonomy and validated language as Library; no blanket full-book free-access schema flag is emitted. Free Reader eligibility and all authorization gates are unchanged. Independent copy/taxonomy review found no blocker.

The required browser journey had retained the old primary Bengali Reader-only URL and hidden mobile reset expectations. Its primary menu contract now includes all Bengali editions and exposes usable reset controls; explicit legacy Reader-only parsing/negative tests remain. This is a source-contract correction, not a waiver of browser acceptance. Final local validation: 398 frontend gate tests, 21 additional copy/presentation tests, and a production build with 172 snapshots/3701 SEO assertions passed. Exact-head hosted browser and published reviews remain mandatory.

Latest verified native instruction in the coordinated release chat prohibits deployment, publication and paid sessions. This PR is source integration only until that changes. #615 is already closed as superseded, with its branch preserved. Current-source guarded recovery proposal independently preserves 1949 other delivered files and the current Reader/audio/rights behaviour; this source-only result is not an actual retained provider image, startup/configuration or execution qualification.
