# Sprint Integration Report

Generated: 2026-07-06

## Integration Status

Status: `BLOCKED_FOR_DIRECT_MERGE`

Both sprint workstreams produced useful changes, but neither branch/worktree is safe to merge wholesale. The safe path is to create a clean integration branch from the latest protected base, then selectively apply only reusable source, config, tests, and sprint documentation.

## Source Workstreams

| Workstream | Branch / worktree | Result | Merge readiness |
| --- | --- | --- | --- |
| Book Publishing Factory | `sprint/book-publishing-factory` / `/private/tmp/earnalism-sprint-book-factory` | `BOOK FACTORY SPRINT YELLOW`: no unsafe publish; `the-gift-of-the-magi` reached TTS but is blocked by ASR ending mismatch and missing timestamps | Not merge-ready as-is; source changes are salvageable, generated release artifacts and copied book data must be excluded |
| Luxury Frontend UX Rebirth | `sprint/luxury-ux-rebirth` / `/Users/ronikbasak/Documents/GitHub/earnalism-digital-library` | `UX SPRINT YELLOW`: luxury UX score `9.53/10`, build/tests pass, release-gate-safe audio UI implemented | Not merge-ready as-is; worktree contains unrelated generated/imported catalog files and needs deployed same-origin validation |

## Book Publishing Status

| Metric | Value |
| --- | ---: |
| Total unique titles | 262 |
| Fully audiobook-live count | 1 |
| Fully audiobook-live slugs | `a-ghost-story` |
| Reader-only live count | 160 |
| New audiobook publishes in sprint pass | 0 |
| OpenAI listening-QA quota probe | PASS |
| Latest estimated TTS spend | `$0.1695` |

Book factory evidence:

- Broad controlled wave attempted ten titles and spent `$0`; all were blocked before paid audio by structured rights metadata gaps, specifically missing `author_death_year` and `original_publication_year`.
- Targeted English run for `the-gift-of-the-magi` passed content/source, rights metadata, cover, and OpenAI TTS.
- `the-gift-of-the-magi` remains blocked at ASR/sync because the final narrated words did not match the manuscript ending and the ASR path did not return word/segment timestamps.
- Listening QA, upload/checksum, metadata approval, and browser publishing were correctly not run after ASR/sync failed.
- No unapproved audiobook was uploaded, approved, browser-published, or exposed.

## UX Status

| Metric | Value |
| --- | ---: |
| Luxury UX Index | 9.53 / 10 |
| Target score | 9.7 / 10 |
| Lowest category | `no_regressions` at 8.7 |
| Release-gate truth status | PASS for changed UI |
| Accessibility status | PASS on local axe subset |
| Build status | PASS |
| Unit test status | PASS |

UX evidence:

- Added release-gate-safe audiobook visibility helper.
- Added approved-audiobook spotlight gated by reader-manifest proof.
- Added premium coming-soon board and controlled shelf messaging.
- Updated book cards, detail pages, reader, and audio UI so unapproved audio is not exposed.
- Added audiobook release-safety unit tests.
- Local production static routes `/`, `/library/`, `/book/dracula`, and `/reader/dracula` returned HTTP 200.
- Local axe subset passed with 0 violations.
- Final 9.7 claim is blocked by missing deployed same-origin validation, missing Lighthouse/Core Web Vitals evidence, remaining polish gaps, and dirty worktree state.

## Conflicts And Overlaps

Files changed in both workstreams and requiring manual resolution:

- `.gitignore`
- `repo_cleanup_report.md`
- `sprint_go_live_dashboard.md`
- `content/books/the-gift-of-the-magi/*`
- `data/controlled_publications/the-gift-of-the-magi/*`
- `data/controlled_publications/frankenstein/public_book.json`
- `internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py`
- `internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py`
- Several other `internal/audiobook_lab/scripts/*` files present in both dirty states

Recommended handling:

- Keep the `.gitignore` ignore rules for release-gate outputs, local Python caches, build outputs, traces, screenshots, and audio artifacts after reviewing exact diffs.
- Treat `repo_cleanup_report.md` and `sprint_go_live_dashboard.md` as semantic documentation conflicts. Rewrite them once on the clean integration branch instead of taking either branch version blindly.
- Do not merge generated `content/books/*` or `data/controlled_publications/*` changes unless separately reviewed as deliberate production content changes.
- Keep book-factory script changes only from the book-factory worktree after scoped diff review.
- Keep UX component/style/test changes only from the UX branch after scoped diff review.

## Keep List

Book-factory changes to consider keeping:

- `.gitignore` release-gate/cache ignores
- `internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py`
- `internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py`
- Any directly related tests already present under `internal/audiobook_lab/scripts/test_*.py` if their diffs are source changes, not generated cache churn
- `book_factory_sprint_report.md` as sprint documentation, if root-level sprint reports are intended to be retained

UX changes to consider keeping:

- `frontend/src/lib/audioReleaseSafety.js`
- `frontend/src/lib/audioReleaseSafety.test.js`
- `frontend/src/components/ApprovedAudiobookSpotlight.jsx`
- `frontend/src/components/ComingSoonBoard.jsx`
- `frontend/src/components/BookCard.jsx`
- `frontend/src/components/FirstVisitSiteTour.jsx`
- `frontend/src/components/AudioPlayer.css`
- `frontend/src/pages/BookDetail.jsx`
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/Library.jsx`
- `frontend/src/pages/Reader.jsx`
- `frontend/src/index.css`
- `frontend/scripts/generate-static-seo-snapshots.mjs`
- `ux_rebirth_audit.md`
- `earnalism_luxury_design_system.md`
- `earnalism_luxury_ux_index.json`
- `ux_rebirth_evidence.md`
- `ux_rebirth_repo_cleanup.md`
- `frontend_luxury_sprint_report.md`

## Do Not Keep

Do not stage or merge:

- `internal/audiobook_lab/release_gate/**`
- `frontend/build/**`
- `output/ux-rebirth/**`
- MP3/WAV/FLAC audio artifacts
- `timestamps.json`, `highlight.vtt`, `chapters.json`, `meta.json` generated sidecars
- Playwright traces, screenshots, videos, logs, PID files, heartbeat files, caches
- Signed URLs, provider credentials, or environment dumps
- Generated cover metadata and release-gate dashboard outputs
- Copied `content/books/*` or `data/controlled_publications/*` inputs unless reviewed and approved as intentional content promotion

## Tests To Rerun After Clean Integration

Required before PR:

```bash
git diff --check
PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile internal/audiobook_lab/scripts/release_catalog_factory.py internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py internal/audiobook_lab/scripts/factory_hooks/*.py internal/audiobook_lab/scripts/providers/*.py
PYTHONPYCACHEPREFIX=.pycache-local python3 internal/audiobook_lab/scripts/test_listening_qa_schema3.py
PYTHONPYCACHEPREFIX=.pycache-local python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py
npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false
npm --prefix frontend run build
```

Required before production deploy:

- Same-origin deployed preview smoke test for homepage, catalog, book detail, reader, approved-audiobook page, and reader-only/audio-hidden page.
- Axe/WCAG AA scan on deployed preview.
- Lighthouse/Core Web Vitals run on deployed preview.
- Console-error scan on desktop and mobile widths.
- Public asset safety scan proving `frontend/public` and `frontend/build` do not contain unapproved audio.
- Railway factory status/probe only; do not publish another book until `the-gift-of-the-magi` ASR/sync repair is implemented and rerun.

## Merge Order Recommendation

1. Create a new clean integration branch from the latest protected base.
2. Apply book-factory reusable source changes first: scoped `.gitignore`, `bengali_tts_provider_bakeoff.py`, `asr_sync_hook.py`, and any directly related tests.
3. Run Python compile/tests.
4. Apply UX source changes second: audio release safety helper/test, approved audiobook spotlight, coming-soon board, route/component/style changes, and UX docs.
5. Resolve `.gitignore`, `repo_cleanup_report.md`, and `sprint_go_live_dashboard.md` manually.
6. Run frontend tests/build.
7. Deploy a preview with the current Vercel CLI; if CLI blocks or warns, upgrade Vercel CLI first with `npm i -g vercel@latest` or use the project-approved package-manager equivalent.
8. Run same-origin browser, accessibility, performance, and release-gate truth checks.
9. Open PR only after the clean integration branch contains no generated artifacts.

## Rollback Plan

- If internal audiobook scripts fail validation, revert only the selected book-factory script and `.gitignore` hunks from the clean integration branch.
- If frontend build, tests, or deployed preview checks fail, revert only UX frontend/docs changes.
- If deployment causes frontend regression, roll back to the previous Vercel production deployment.
- No production metadata rollback is required from this sprint integration because no new audiobook was published.
- Do not roll back `a-ghost-story`; it remains the only confirmed fully live audiobook.

## Production Deploy Plan

Do not deploy directly from either dirty worktree.

Recommended deploy path:

1. Build a clean integration branch.
2. Open a PR with only scoped source/config/tests/docs.
3. Deploy Vercel preview for the UX changes.
4. Run same-origin route, accessibility, performance, and release-gate safety checks.
5. If frontend validation passes, merge/deploy frontend changes.
6. Keep book-factory changes internal until `the-gift-of-the-magi` final-chunk/sync repair is implemented, then rerun the targeted Railway command.

## Next Exact Commands

Clean branch setup:

```bash
git switch main
git pull --ff-only
git switch -c sprint/integration-clean
```

Scoped validation after applying selected changes:

```bash
git diff --check
PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile internal/audiobook_lab/scripts/release_catalog_factory.py internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py internal/audiobook_lab/scripts/factory_hooks/*.py internal/audiobook_lab/scripts/providers/*.py
PYTHONPYCACHEPREFIX=.pycache-local python3 internal/audiobook_lab/scripts/test_listening_qa_schema3.py
PYTHONPYCACHEPREFIX=.pycache-local python3 internal/audiobook_lab/scripts/test_release_catalog_factory_stop_guards.py
npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false
npm --prefix frontend run build
```

Book-factory continuation after ASR/sync repair:

```bash
railway run --project a8533934-35c4-463e-9f43-577a9ac391ee \
  --service 5af42e7e-f518-4f6a-b602-d9950866501f \
  --environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 -- \
env \
EARNALISM_APPROVE_PAID_OPENAI_TTS=true \
EARNALISM_TTS_MAX_ESTIMATED_USD=35 \
EARNALISM_STOP_ON_BUDGET_EXCEEDED=true \
EARNALISM_ENABLE_OPENAI_LISTENING_QA=true \
EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio \
EARNALISM_FACTORY_ASR_MODEL=gpt-4o-transcribe \
PYTHONPYCACHEPREFIX=.pycache-local \
python3 internal/audiobook_lab/scripts/release_catalog_factory.py \
  --manifest book_import_manifest.json \
  --slugs the-gift-of-the-magi \
  --languages eng,ben \
  --max-books-active 1 \
  --max-preflight-workers 1 \
  --max-audio-reuse-workers 1 \
  --max-tts-workers 1 \
  --max-paid-workers 1 \
  --max-asr-workers 1 \
  --max-cover-workers 1 \
  --max-upload-workers 1 \
  --max-metadata-workers 1 \
  --max-browser-workers 1 \
  --max-attempts 2 \
  --priority ready-first \
  --order-by content-size \
  --release-order ascending-content-size \
  --allow-blocked-order-skip \
  --exclude-slugs "$(cat internal/audiobook_lab/release_gate/terminal_blocker_exclusions.txt)" \
  --publish-approved \
  --fail-closed \
  --stop-after-published 1 \
  --max-run-minutes 90
```

## Final Recommendation

Integration is blocked for direct merge. Proceed with a clean integration branch and scoped source-file application. The UX branch is closer to PR readiness but still below the 9.7 UX threshold and needs deployed preview validation. The book-factory branch has useful ASR/listening-QA reliability changes, but the publishing path still needs `the-gift-of-the-magi` ASR/sync repair before the next publish attempt.
