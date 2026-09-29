# Sherlock Holmes publication decision packet — 2026-09-29

## Decision requested

One authenticated owner/legal decision is needed:

> After qualified review, authorize or decline commercial text-reader publication in India of **The Adventures of Sherlock Holmes**, slug `the-adventures-of-sherlock-holmes`, edition Project Gutenberg eBook #1661, with source SHA-256 `922e2a12ccb43a4c9544c260b2166c6ad2097aeb5957faeee113f173bb857cd0` and corrected normalized reader-content SHA-256 `d6cb7d46af3d95b071c3783bf3b093f8c8397144ae717bbfbe87b8fc336fdc5c`. The decision must explicitly bind this edition and the Earnalism reader-publication scope. If authorized, the existing protected workflow must record the actual approver, decision time, edition identity, source/content hashes, India territory, and publication scope in the trusted rights registry and publication authorization. No audio authorization is requested.

The source’s United States public-domain notice alone does not decide India commercial rights. No legal conclusion or owner approval is asserted in this packet.

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
- **Current source rights status:** `REVIEW_REQUIRED`; no accepted title-specific decision exists.
- **Reader/package validation:** 12 chapters, chapter/content hashes rebound; publication manifest is schema/checksum valid but `reader_release=BLOCKED` solely by the rights review status and explicit blocked reason. Package checksum bundle covers the current package files.
- **Cover provenance:** deterministic Earnalism first-party vector/typography covers; no external art. Front SHA-256 `2207b2aa7c703f1bd20adb181a4b05a0ecfaac91d95823d62c85c8e18b5c5ba9`, back SHA-256 `622ad67239da00c96cfd9730b1e07a1fdf2220cad143d6ad45fda33c03cb2f04`; both visually inspected at 800x1200.
- **Publication authorization:** absent. `approval_evidence.json` is explicitly marked historical/non-authorizing; `approved_to_publish=false`.
- **Catalog status:** non-live, not excluded, not in the canonical live set.
- **Current canonical live set:** `a-ghost-story`, `the-tell-tale-heart`, `radharani`, `a-white-heron`, `the-gift-of-the-magi`, `the-canterville-ghost`
- **Runtime control:** same scoped production probe returns HTTP 200 for `a-ghost-story`; Sherlock returns HTTP 451. Local rights gate identifies `ACCEPTED_DECISION_MISSING` for Sherlock catalog/reader paths.
- **Audio:** `NOT_REQUESTED`, not exposed, not part of this decision.

## Exact future activation diff — NOT APPLIED

Only after the decision is approved and the trusted registry and runtime checks pass, the canonical `data/controlled_launch.json` live list would append this single slug:

```diff
   "live_approved_slugs": [
     ...existing six approved slugs unchanged,
+    "the-adventures-of-sherlock-holmes"
   ]
```

The backend mirror and any generated publication authorization must be updated only through the repository’s governed release process. This PR does not change either live-approval authority.
