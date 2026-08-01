# Launch Gate 0 Evidence

Generated: 2026-07-08 00:30 IST

## Strategy Summary

Launch Gate 0 was executed as a production-truth and validation lock, not a visual expansion sprint. The objective was to prove whether Earnalism can safely begin the first 30-day campaign without exposing unapproved audiobooks, stale audio URLs, fake sync claims, or unvalidated marketing copy.

Decision: `LIMITED GO`.

- Organic reader-first and brand campaign: `GO`.
- `book-2b9853ec52` Bengali Listen campaign: `GO`.
- A Ghost Story paid Listen campaign: `HOLD`.
- Full Earnalism 10/10 UX claim: `HOLD`.

## Exact UX / Release Target

Launch Gate 0 target:

- Only `book-2b9853ec52` and A Ghost Story may be treated as audio candidates.
- No non-live Tier 1 title may expose Listen CTA, player UI, stale audio URL, narrator metadata, waveform, duration, or structured audio metadata.
- A Ghost Story paid Listen campaigns require final production route/manifest/player evidence.
- Bengali failed/blocked titles remain reader-only, audio-hidden, or coming soon.
- Home, Library, Reader, Book Detail, and Audiobook Player must build after dependency repair.
- Cover audit remains zero typographic-only public covers.
- Audio safety tests pass.
- Visual smoke passes.
- Lighthouse/accessibility must be run or documented as blocked.

## Canonical Repo State

- Branch: `sprint/luxury-ux-rebirth`
- Dirty workspace: yes. This sprint changed source hardening files and generated validation artifacts; existing unrelated dirty content remains.
- Stale dependency tree: `frontend/node_modules.stale-20260708T001931` preserved locally and ignored via `.gitignore`.

## Files Inspected

- `frontend/src/lib/api.js`
- `frontend/src/lib/api.test.js`
- `frontend/src/components/AudioPlayer.jsx`
- `frontend/src/components/AudioPlayer 2.jsx`
- `frontend/src/components/AudioPlayer.css`
- `frontend/public/index.html`
- `frontend/public/service-worker.js`
- `frontend/src/lib/audioReleaseSafety.js`
- `frontend/src/lib/audioReleaseSafety.test.js`
- `frontend/src/pages/BookDetail.jsx`
- `frontend/src/pages/Reader.jsx`
- `frontend/src/components/BookCard.jsx`
- `frontend/src/components/ApprovedAudiobookSpotlight.jsx`
- Season 1 launch and marketing files listed in `launch_gate_0_marketing_truth_matrix.json`

## Files Changed

- `.gitignore`: ignore stale renamed dependency trees.
- `frontend/src/lib/api.js`: production default now resolves to same-origin `/api` when no safe explicit backend is configured.
- `frontend/src/lib/api.test.js`: added production same-origin fallback tests.
- `frontend/public/index.html`: removed direct `api.theearnalism.com` DNS/preconnect hints.
- `frontend/public/service-worker.js`: removed legacy `/audio/` cache handling.
- `frontend/src/components/AudioPlayer.jsx`: legacy player now fails closed unless explicit approved audio URLs are passed.
- `frontend/src/components/AudioPlayer 2.jsx`: re-exported the hardened legacy player instead of duplicating stale logic.

Generated/validation side effects intentionally excluded from commit:

- `frontend/build/**`
- `frontend/public/sitemap.xml`
- `ux_visual_regression_report.json`
- `frontend/node_modules.stale-*`

## Validation Commands Run

| Command | Status | Summary |
| --- | --- | --- |
| `npm ci --prefix frontend --legacy-peer-deps --no-audit --no-fund` | PASS | Dependency state repaired after stale tree rename. |
| `npm test --prefix frontend -- --watchAll=false` | PASS | 3 suites, 12 tests. |
| `npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js src/lib/api.test.js --watchAll=false` | PASS | 2 suites, 8 tests. |
| `npm run build --prefix frontend` | PASS | CRA/Craco build passed; main JS 116.32 kB gzip. |
| `node frontend/scripts/audit-book-covers.mjs` | PASS | 164 scanned, 0 typographic-only public covers. |
| `node frontend/scripts/visual-luxury-smoke.mjs` | PASS | 72/72 local production-equivalent route checks. |
| `VISUAL_SMOKE_BASE_URL=https://www.theearnalism.com ... visual-luxury-smoke.mjs` | PASS | 72/72 production route checks. |
| `git diff --check` | PASS | No whitespace errors. |

Unavailable scripts:

- `npm run lint --prefix frontend`
- `npm run typecheck --prefix frontend`
- `npm run test:e2e --prefix frontend`
- `npm run test:a11y --prefix frontend`
- `npm run lighthouse --prefix frontend`

Because Lighthouse/accessibility scripts are missing, page-level UX score claims remain capped at 9.4.

## Audiobook Exposure Matrix

| Title | Production evidence | Marketing state | Decision |
| --- | --- | --- | --- |
| `book-2b9853ec52` / দুই বিঘা জমি | Book API 200, manifest 200, audiobook endpoint 200, audio/sidecars 200 | Live audio-marketable | GO |
| `a-ghost-story` / A Ghost Story | Reader/book routes 200, local approved assets 200, guessed production API book/manifest/audiobook routes 404 | Approved local asset-backed, production API route unresolved | HOLD for paid Listen |
| `muchiram-gurer-jibanchorit` | No public audiobook evidence | Coming soon / reader-first only | No Listen |
| `book-d19e96859f` | Audiobook endpoint 404; ASR/source mismatch known | Coming soon / reader-first only | No Listen |
| `book-f5d593e1f4` | No public audiobook evidence; ASR/source mismatch known | Coming soon / reader-first only | No Listen |
| Other Tier 1 candidates | No public audiobook evidence | Coming soon / reader-first only | No Listen |

## Campaign Truth Matrix

See `launch_gate_0_marketing_truth_matrix.json`.

Summary:

- Audio teaser posts are restricted to live/approved titles.
- Non-live Tier 1 candidates use Read, Coming Soon, or Follow language.
- Reader-first titles are framed as premium reader editions.
- A Ghost Story paid Listen ads are held until exact production manifest/player route evidence passes.

## Route Smoke Results

Production probes:

- `/`: 200
- `/library`: 200
- `/book/book-2b9853ec52`: 200
- `/reader/book-2b9853ec52`: 200
- `/api/books/book-2b9853ec52`: 200
- `/api/reader/book/book-2b9853ec52/manifest`: 200
- `/api/reader/book/book-2b9853ec52/audiobook`: 200
- `/book/a-ghost-story`: 200
- `/reader/a-ghost-story`: 200
- `/api/books/a-ghost-story`: 404
- `/api/reader/book/a-ghost-story/manifest`: 404
- `/api/reader/book/a-ghost-story/audiobook`: 404
- `/api/reader/book/book-d19e96859f/audiobook`: 404
- `/api/reader/book/the-gift-of-the-magi/audiobook`: 404

## Source Guard Results

- Direct `api.theearnalism.com` frontend references: 0.
- Browser/system speech fallback references: 0.
- `AudioObject` structured data references: 0.
- `word-level` / `word level` public copy references in frontend source/build: 0.
- Static audio path assumption: no public static path remains; the only `/audio/` exact source/build match is regex `/audio/i` in an admin blocker classifier.

## Lighthouse / Accessibility Status

Not rerun. The repo has no `lint`, `typecheck`, `test:a11y`, or `lighthouse` npm scripts in `frontend/package.json`. This blocks any full 10/10 claim.

## Blockers

1. A Ghost Story paid Listen is still on HOLD because guessed production API book/manifest/audiobook routes return 404.
2. Lighthouse/accessibility score cannot be refreshed without adding or running an external tool.
3. The canonical workspace remains broadly dirty; only Launch Gate 0 source changes should be promoted.
4. Vercel CLI is outdated in this environment; upgrade before serious Vercel deploy/preview management.

## Go / No-Go Decision

`LIMITED GO`.

Allowed now:

- Organic reader-first campaign.
- Organic brand/trust campaign.
- `book-2b9853ec52` Listen campaign.
- Coming-soon campaign for Tier 1 candidates with no Listen CTA.

Held:

- A Ghost Story paid Listen campaign.
- Full 10/10 UX score claim.
- Any broad paid campaign implying multiple live audiobooks beyond verified evidence.

## Next Exact Command

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && VISUAL_SMOKE_BASE_URL=https://www.theearnalism.com VISUAL_SMOKE_SCREENSHOT_DIR=/tmp/launch-gate-0-production-smoke node frontend/scripts/visual-luxury-smoke.mjs && git diff --check
```
