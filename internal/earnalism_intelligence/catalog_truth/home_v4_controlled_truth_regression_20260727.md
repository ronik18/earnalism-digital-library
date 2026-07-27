# Home v4 Controlled Truth Regression

Generated: 2026-07-27
Status: `SOURCE_FIX_VALIDATED_DEPLOY_REQUIRED`

Production Home v4 reported 19 live titles and three approved audiobooks after commit `e247c5c843d8dc84fe840d750afc1a6bb39bed76`. It omitted `book-2b9853ec52`, while the independent book endpoint still reported its reader audio as `APPROVED` and `QA_PASSED`.

The Home query used `BOOK_SUMMARY_PROJECTION`, which intentionally excludes audio assets and release evidence. A same-slug database result was marked as seen and prevented the complete controlled-publication artifact from loading. The incomplete summary then failed Home audio truth even though the canonical artifact and reader manifest remained approved.

The repair gives validated controlled artifacts precedence for reader, rights, cover, and audio truth. Database values remain authoritative only for the allowed editorial fields: shelf membership, pinning, rank, do-not-feature, popularity, freshness, release cycle, Sprint ID, and publication time. Admin curation still cannot approve audio, enable readers, or bypass cover audit.

The Home cache identity was rotated so the stale v4 payload cannot survive the deployment. The source contract again exposes `reader_enabled_count`, `sprint1_active_count`, and `approved_audiobook_count`.

Offline canonical reconstruction now proves:

- 43 controlled readers available across the current live catalog.
- All 32 configured Sprint 1 readers present.
- Four approved audiobooks: `book-2b9853ec52`, `a-ghost-story`, `sredni-vashtar`, and `the-open-window`.
- No hidden title gained audio.
- No release gate, audio asset, private media, or paid TTS lock changed.

Validation: 41 focused Home/public-audio tests, 36 release-truth/hidden-audio tests, and 10 isolated B2 routing tests passed; `git diff --check` passed.

Known unrelated baseline debt remains in ten tests that assert the superseded Dracula-only launch configuration and two tests that expect pre-normalization raw reader text.

Next exact command:

```bash
git push origin codex/main-approved-integration
```
