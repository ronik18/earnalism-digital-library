# Open issue reconciliation — 2026-09-30

Source inspected: merged main `de5d669a484f82e693b654565923ce96b4b9ad1a`. This record describes verified source and a narrow regression candidate. It does not declare CUSTOMER_READY or new publication authority.

## Issue #347: audiobook test follow-up

The three reported tests still failed. The full routing file exposed five more stale-fixture failures (8 failed, 25 passed). Package transports now use `_reader_audio_package_book_for_slug`; several fixtures intercepted only the older resolver. The stale-version negative case could pass at the earlier title gate without exercising version rejection.

The candidate restores transport fixtures at the correct boundary, retains exact version/segment/range/receipt/canary checks, and exercises a real accepted reader-only control for cache invalidation. Public metadata must remain URL-free. Private-store proxy mapping is tested directly, while real unapproved Open Window audio must fail before package selection or storage. A separate synthetic presentation case preserves provider, voice, QA, duration, size and disclosure coverage. No public release predicate is changed.

The revised Agentic AI detail test now distinguishes committed source from current launch authority. A held title must return 404; a genuinely released future title must serialize the revised reader-only artifact. The regression launcher includes both complete test files and current Auth/Account, Library and Pricing checks.

Local candidate validation: 89 backend tests passed, including 34 routing and 3 manuscript tests; 27 focused frontend tests passed. Workflow YAML, all campaign shell steps, the regression launcher shell and `git diff --check` passed. Required candidate CI and protected merge remain pending at this record's creation.

## Issue #380: inclusion proof and remaining release acceptance

The original source findings are stale. Both handoff archives were retrieved and their checksum inventories independently verified: UI 225/225; revised manuscript 428/428. Archive SHA-256 values match the issue's recorded authorities. All seven Commerce artwork crops match current canonical assets byte for byte. All 14 selected chapter contents, titles and order match the runtime package; root/runtime chapter files are byte-identical. Code indentation and pre/code boundaries therefore remain the selected revision's exact bytes.

| Requirement | Current canonical source / check | Disposition |
| --- | --- | --- |
| Latest Home and Header | `Home.jsx`, `EditorialHomeLibrarySurfaces.jsx`, `HomeOptionB.css`; Reference surface tests | Preserve the later approved Option B beige surface; the old prototype must not replace it. |
| Library search, filters, reset, URL history, states and drawer | `Library.jsx`, `EditorialHomeLibrarySurfaces.jsx`, `LibraryBrowseShelf.jsx`; Library tests | Present; reset preserves search, sort and unrelated parameters. Newer catalogue error recovery is retained. |
| Original hourglass invitation | `LibraryReadingPassCard.jsx`, scoped Library styles and `reading-pass-reference.png` | Desktop sidebar and compact placement remain responsive, with live copy and `/pricing` link. |
| Reading Passes, artwork, FAQs, enquiries | `ReadingPassesSurface.jsx`, `reading-passes.css`, `readingPassOffers.js`, `Pricing.jsx`; Pricing/Reference tests | Exact seven artwork crops; current configured offers and checkout remain authoritative. Later approved unused-minute semantics override the prototype's illustrative terms. Coming-soon institution/publisher/gift treatments remain. |
| Revised manuscript and identity | Both `controlled_publications/agentic-ai-with-python` trees; manuscript tests | 14/14 selected content bodies, titles and order match; canonical identity preserved. |
| No automated audio/TTS for this title | `reader_only_audio_policy.py`, controlled launch exclusion and pipeline refusal test | Reader-only; generation refused before output. |
| Auth/Account follow-up | `AuthContext.jsx`, `Account.jsx`, `authAccountLifecycle.test.jsx` | Six mounted lifecycle tests pass; latest recovery/generation safeguards preserved. |

Remaining acceptance is live release/readback and the final CUSTOMER_READY proof. The title currently has two accepted-decision blockers in the catalogue campaign; source inclusion is not their substitute. No authenticated production readback, device UAT, legal fact, successful deployment or CUSTOMER_READY result is invented. Keep #380 open until its remaining release acceptance is evidenced, and coordinate title clearance through #477.

## Issue #477: catalogue campaign

Independent `process_full_catalogue.py --check` reproduced 231 assessed titles, 162 prepared packages / 1,012 chapters, seven accepted live titles, 224 holds and 69 missing cleared packages. Audio activations, new publications and uploads are zero. Campaign run 36748172557 still reported its implementation step in progress after its configured 45-minute step budget; this is neither a completed compliance review nor an evidence-exhaustion result. No title-specific fact or accepted decision is fabricated.

The candidate retains the shared integration branch after campaign merges and binds automated merge to the exact candidate head. Normal fast-forward pushes and all release/rights/integrity gates remain mandatory. A stale hosted worker may not replace a newer approved branch history. Preserve any eventual candidate and inspect its independent validation before accepting it.

## Issue #385: physical-device lifecycle UAT

Retain `DEFERRED_BY_OWNER_POST_CUSTOMER_READY_UAT`, Android and iOS `NOT_RUN / UNVERIFIED`, and the owner's narrow nonblocking decision. No authorized physical device is available here. Issue comment 5916449791 records the verified scheduling state and complete resumption trigger. Existing isolated authorization, settlement and Stop coverage is not a physical-device pass.

Next exact command: `gh pr checks <candidate-pr> --repo ronik18/earnalism-digital-library --watch --fail-fast`; then use an exact-head protected merge and verify merged-main regression. Separately inspect `gh run view 36748172557 --repo ronik18/earnalism-digital-library --log-failed` before making any campaign outcome claim.
