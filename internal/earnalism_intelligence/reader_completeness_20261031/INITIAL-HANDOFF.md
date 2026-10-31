# Reader completeness — local review handoff

Owner scope: finish remaining Reader verification and prepare fixes, preserve gates; **no deployment or publication**.

Base: `9a1b166e189cebc9b2b75baf20a95d2eb33a3c12`. Preparation commit: `d10a9c7`. Isolated branch `codex/reader-completeness-20261031`; no shared worktree edits.

All 52 complete controlled packages validate locally. Fresh metadata readback:52/52 succeeded and all canonical manifests match the retained snapshot. 40 complete-source page sets match; 12 require source/version adjudication. Eight titles have direct complete/free or protected-final-section delivery observations. This is not an all-title LIVE declaration.

The Python preparer writes hash-only **local inactive plans**. It sends no HTTP request, calls no database operation and has no apply/publish switch. It rejects renderer warnings and cannot treat HTTP200/session admission as delivered text. Unit coverage includes missing/reordered/changed content, stale receipts, sanitizer failure, explicit illustration-label policy and no source mutation.

Local validation:369 tests passed across the new preparer tests and existing segment-promotion/bootstrap suites. Exact-head hosted CI and independent PR review have not run; no source was pushed.

## Source mismatches and complete successors

| Title | Live pages | Complete candidate pages | Missing indexed chapter IDs |
|---|---:|---:|---|
| মুচিরাম গুড়ের জীবনচরিত | 3 | 20 | chapter-003, chapter-004, chapter-005, chapter-006, chapter-007, chapter-008, chapter-009, chapter-010, chapter-011, chapter-012, chapter-013, chapter-014 |
| ক্ষুধিত পাষাণ | 8 | 9 | None; hash/text adjudication required |
| কমলাকান্তের দপ্তর | 47 | 48 | None; hash/text adjudication required |
| লোকরহস্য | 52 | 54 | None; hash/text adjudication required |
| The Time Machine | 63 | 70 | chapter-017 |
| The Wonderful Wizard of Oz | 76 | 77 | chapter-000 |
| Acres of Diamonds | 79 | 79 | None; hash/text adjudication required |
| মৃণালিনী | 85 | 87 | None; hash/text adjudication required |
| আনন্দমঠ | 87 | 87 | None; hash/text adjudication required |
| Frankenstein | 144 | 144 | None; hash/text adjudication required |
| Pride and Prejudice | 241 | 258 | None; hash/text adjudication required |
| Dracula | 275 | 276 | chapter-000 |

Muchiram’s live three pages contain only the beginning of its 14-chapter retained edition. Time Machine’s separate Epilogue, and Dracula/Wizard front matter, are absent from their live page indexes. Same-page-count mismatches are not automatically missing literary content. Preserve the old versions and rollback records.

## Access diagnosis and safe next operation

Observed five title admission requests returned HTTP503 `CONTENT_AUTHORITY_UNAVAILABLE`. Current source requires a physical activation pointer, while startup deliberately preserves older active manifests. This is a candidate root cause, not a live database diagnosis; read-only Railway SSH was unavailable because no existing SSH key was present, and no new key was created.

For each affected title, Integration Lane must first read `/api/admin/reading-pass/books/{slug}/segments/active`, reconcile the actual activation record and source/rights identity, and use existing `migrate_reading_pass_segments.py` candidate preparation with `activate:false`. Review exact full-source hashes. Only after separately authorized release use guarded expected-version promotion with the freshly observed generation. Never infer generation zero from public metadata, overwrite old pages, bypass rights or auto-repair a revoked pointer.

Do not alter source packages, release registries, startup plans or consumer admission merely to make legacy metadata look ready. There are no runtime application changes in this patch.

Remaining paid customer-path checks are held for the specific failed-load lease-expiry confirmation after automatic approval review rejection. Last observed cumulative verification charge:59 seconds of the existing300-second cap. No purchase/top-up/listening or other-device takeover.

Local output packet and customer-path evidence are retained privately at `/Users/ronikbasak/Documents/ChatGPT/earnalism-studio/evidence/live-reader-completeness-20261031`. Generated packets are intentionally not committed. Superseded intermediate packets are historical, not release authority.

Next integration action: review this local preparer and exact current inactive successor packet alongside existing reader-controller evidence; preserve the no-deploy/no-publish hold.
