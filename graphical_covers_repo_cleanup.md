# Graphical Covers + Calm Typography Cleanup

Generated: 2026-07-06

## Source Changes

- Added shared graphical cover resolver: `frontend/src/lib/bookCoverResolver.js`.
- Updated cover source selection: `frontend/src/lib/images.js`.
- Replaced typography-heavy fallback rendering in `frontend/src/components/BookCoverImage.jsx`.
- Updated Shelf II to use the shared cover component: `frontend/src/components/ShelfTwoSlideshow.jsx`.
- Calmed homepage/library/card typography in `frontend/src/pages/Home.jsx`, `frontend/src/pages/Library.jsx`, `frontend/src/components/BookCard.jsx`, and `frontend/src/index.css`.
- Reduced above-fold weight by switching the homepage Dracula hero to `dracula-hero-hardcopy.webp`, removing the photographic hero background layer, and removing blocking external font imports.
- Fixed production same-origin API override support in `frontend/src/lib/api.js`.
- Added cover audit and visual smoke scripts.
- Added cover policy: `internal/earnalism_intelligence/cover_acceptance_policy.json`.
- Updated `frontend/package-lock.json` with `npm --prefix frontend install --package-lock-only` after `npm ci` exposed pre-existing lock drift.

## Cover Assets

- No new raster cover assets were committed.
- Existing approved graphical covers were reused.
- Missing covers now resolve to lightweight runtime SVG graphical fallbacks with no title/author text baked into the image.

## Generated Artifacts Excluded

- `/tmp/earnalism-graphical-covers-visual-smoke/`
- `/tmp/earnalism-graphical-covers-lighthouse/`
- `frontend/build/`
- Existing release-gate outputs, audio, sidecars, logs, caches, screenshots, and rollback payloads.

## Validation

- `npm ci --prefix frontend` - PASS after package-lock-only sync.
- `npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false` - PASS, 4/4.
- `REACT_APP_BACKEND_URL=/api npm --prefix frontend run build` - PASS.
- `node frontend/scripts/audit-book-covers.mjs` - PASS, 164 records, 0 typography-only covers.
- `node frontend/scripts/visual-luxury-smoke.mjs` - PASS.
- `VISUAL_SMOKE_BASE_URL=http://127.0.0.1:4173 node frontend/scripts/visual-luxury-smoke.mjs` - PASS.
- `python3 -m py_compile internal/audiobook_lab/scripts/generate_graphical_book_covers.py` - PASS.
- `python3 internal/audiobook_lab/scripts/generate_graphical_book_covers.py` - PASS.
- `git diff --check` - PASS.
- Lighthouse on `http://127.0.0.1:4173/` - PARTIAL: performance 90, accessibility 100, SEO 100, best practices 100, LCP 3.6s.

## Merge Safety

Not merge-ready as a whole worktree. There are many unrelated dirty book/catalog/release artifacts. Stage only the cover/type source files, scripts, policy/docs, and any intentional package-lock repair after review.

## Rollback Plan

- Revert `frontend/src/lib/bookCoverResolver.js`, `frontend/src/lib/images.js`, `BookCoverImage.jsx`, and `ShelfTwoSlideshow.jsx` to restore previous cover behavior.
- Revert typography class changes in Home/Library/BookCard/index.css if visual QA regresses.
- Revert `frontend/public/index.html` font/static-shell changes if deployment policy rejects a critical home shell.

## Remaining Risk

Lighthouse performance is improved from the local baseline captured during this pass but still below the requested guardrail. The next fix should address CRA client-render LCP or add an approved static/prerendered homepage path.

## Performance Rescue - 2026-07-07

- Activated achievement-aware cost governor and froze Bengali reader-only, Sarvam provider-limit, graphical cover, visual smoke, and audio-safety wins.
- Root cause: Lighthouse LCP was held by the mobile hero image, then by automatic first-visit tour text and early idle prefetch/settings work.
- Fix: responsive compressed Dracula hero variants, mobile procedural cover face, lazy/delayed first-visit tour, delayed route prefetch/settings fetch, optimized bundled brand mark.
- Lighthouse: performance `90` -> `96`, LCP `3.6 s` -> `2.7 s`, total byte weight `Total size was 417 KiB` -> `Total size was 239 KiB`.
- Cover audit remains PASS: 164 covers, 0 typography-only covers.
- Visual smoke remains PASS. Audio safety remains PASS. Accessibility and SEO remain 100.
- No paid operations, provider calls, Bengali mutations, deployments, or broad catalog waves were run.
