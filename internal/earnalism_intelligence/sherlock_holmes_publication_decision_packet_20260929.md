# Sherlock Holmes publication decision packet — 2026-09-29

## Decision received and bound

The user supplied the following genuine authorized owner/legal decision directly in the task instruction:

> APPROVE commercial text-reader publication in India for slug `the-adventures-of-sherlock-holmes`, Project Gutenberg eBook #1661, source SHA-256 `922e2a12ccb43a4c9544c260b2166c6ad2097aeb5957faeee113f173bb857cd0`, and normalized content SHA-256 `d6cb7d46af3d95b071c3783bf3b093f8c8397144ae717bbfbe87b8fc336fdc5c`.

Scope is **TEXT READER ONLY**. The decision does not authorize audiobook release, audio playback, Listen CTA, audio entitlement, or any other edition. The individual approver identity was not stated; no personal identity is asserted. It was recorded in repository evidence at `2026-09-29T08:21:18Z` as the receipt/transcription time, not represented as the original decision timestamp.

The source’s United States public-domain notice remains source context only; this record does not broaden the supplied decision.

## Evidence for review

- **Title / slug:** The Adventures of Sherlock Holmes / `the-adventures-of-sherlock-holmes`
- **Edition/source:** Project Gutenberg eBook #1661, Arthur Conan Doyle, 12 stories
- **Source page:** https://www.gutenberg.org/ebooks/1661
- **Exact text:** https://www.gutenberg.org/cache/epub/1661/pg1661.txt
- **Source snapshot SHA-256:** `922e2a12ccb43a4c9544c260b2166c6ad2097aeb5957faeee113f173bb857cd0`
- **Normalized package content SHA-256:** `d6cb7d46af3d95b071c3783bf3b093f8c8397144ae717bbfbe87b8fc336fdc5c`
- **Source-to-manuscript comparison:** all 12 chapter bodies match after HTML/line-break and Gutenberg emphasis normalization; two source omissions were restored in chapters 2 and 5.
- **Rights source statement:** Project Gutenberg #1661 identifies its work as public domain in the USA and directs non-US users to check local law.
- **India law reference for qualified review:** https://copyright.gov.in/Copyright_Act_1957/chapter_v.html (Copyright Act 1957, section 22). This citation is not itself a legal conclusion.
- **Current source rights status:** owner/legal decision bound to an accepted `earnalism.rights-decision.v1` India-only record; exact source/content hashes are retained.
- **Reader/package validation:** 12 chapters, chapter/content hashes rebound; publication manifest is schema/checksum valid but `reader_release=BLOCKED` solely by the rights review status and explicit blocked reason. Package checksum bundle covers the current package files.
- **Cover provenance:** deterministic Earnalism first-party vector/typography covers; no external art. Front SHA-256 `2207b2aa7c703f1bd20adb181a4b05a0ecfaac91d95823d62c85c8e18b5c5ba9`, back SHA-256 `622ad67239da00c96cfd9730b1e07a1fdf2220cad143d6ad45fda33c03cb2f04`; both visually inspected at 800x1200.
- **Publication authorization:** `approval_evidence.json` now records the exact edition, approved hashes, India territory, text-reader-only scope, exclusions, and unknown personal approver identity. `rights_decision.json` is hash-bound and registered.
- **Catalog status:** non-live before this PR, not excluded; the single Sherlock slug is added to both controlled-launch authorities in this branch after local gates passed.
- **Starting canonical live set:** `a-ghost-story`, `the-tell-tale-heart`, `radharani`, `a-white-heron`, `the-gift-of-the-magi`, `the-canterville-ghost`. Sherlock is the only addition in this branch.
- **Runtime validation:** local hash-bound checks pass for `a-ghost-story` control and Sherlock catalog/reader/preview/chapter/Reading Pass actions. The previously deployed production still needs post-deploy verification; no production status is claimed here.
- **Audio:** `NOT_REQUESTED`, not exposed, not part of this decision.

## Controlled activation diff in this PR branch — pending protected merge/deployment

After the supplied decision was bound and all local rights/package/runtime gates passed, both canonical controlled-launch mirrors append only this slug:

```diff
   "live_approved_slugs": [
     ...existing six approved slugs unchanged,
+    "the-adventures-of-sherlock-holmes"
   ]
```

The exact merge and production deployment remain pending protected checks. Audio allowlists remain empty; checkout/payment and entitlement implementations are unchanged.
