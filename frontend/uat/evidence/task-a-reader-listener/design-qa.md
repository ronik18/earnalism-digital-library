# Task A: Reader and Listener visual QA

**Design QA result: passed**

## Reference and implementation

- Reference: `/Users/ronikbasak/Documents/ChatGPT Image Sep 29, 2026, 11_45_50 PM.png` (1536 × 1024 px).
- Implementation began from merged PR471 `57237eb76c24022f02214ce08fd02b7869fe411` and is being rebased onto current main `5fd063f5e8d1d569c1d2917d21daa882d81b63d6` (PR472).
- Screenshots and browser report: this directory. Browser capture used the repository Playwright smoke runner, Chromium, device scale factor 1, viewport screenshots (`fullPage: false`).
- Screenshot inputs are local review fixtures. The Reader has public-domain Dracula chapter text and real book metadata; account progress and balance are omitted. The Listener uses the actual one-chapter A Ghost Story metadata and cover, with no approved audio, media URL, media element, or playback controls.

## Screenshot coverage

Both routes were captured at every requested CSS viewport: 1600 × 1000, 1440 × 1000, 1280 × 900, 1024 × 900, 768 × 1024, 430 × 932, 390 × 844, and 360 × 800. Each image is a viewport screenshot at CSS-pixel scale, device scale factor 1. `screenshots.sha256` records SHA-256 for all 16 images.

## Review findings

- The Reader follows the reference's warm parchment background, espresso and maroon type, clear reading column, edition details, and responsive controls. At 390 px it retains readable line length, page selection, settings, and previous/next navigation without horizontal overflow.
- The Listener follows the reference's dark, warm record-room treatment, with the official book cover, chapter details, and a truthful Reading Pass required state. It states that playback is disabled until an approved recording exists. No synthetic player appears in the unapproved review fixture.
- The official Earnalism brand lockup remains in the shared header. English uses the literary serif default; Bengali retains its sans-serif default.
- Navigation actions in production Reader and Listener routes pass through the existing session settlement flow before leaving. Focus-visible styling and reduced-motion rules are present.
- The Playwright report records 16/16 routes completed, zero blockers, zero horizontal overflow, no visible interactive target below 44 × 44 px, no unlabeled visible controls, and no console errors.

## Production-surface fingerprint

- Base source fingerprint (PR471 main at `57237eb76c24022f02214ce08fd02b7869fe411`): `211b1ce39a61ace6fe92d3a6162cd85b5e5009b6ac819f94b8e89cce966ce3c9` (independently reproduced from a `git archive` copy; 330 hashed files).
- PR472 merged-main source fingerprint: `ce26abb38ce5d4a835c589c0b784ceaf91f4647373f4517bc7c96814b2bdffc7`.
- Combined A candidate source fingerprint after rebasing PR472 and correcting Reader/Listener mobile lockup clipping: `5fd698e66342f87aa8bbfc5bd3593350079027f9da83ad6879d602f91f1139c0` (independently reproduced, 331 hashed files). Both seamless-brand workflow authorities are bound to this exact source fingerprint. The canonical Earnalism logo hash remains unchanged.

## Verification

- Complete frontend Jest suite: 83 suites, 520 tests passed (including focused Reader/Listener release-truth tests).
- `npm run build --prefix frontend`: passed.
- Static SEO verifier: 34/34 snapshots, 703 assertions, 0 failed.
- `git diff --check`: passed.
- Full visual smoke report after the 58 px correction: `visual-smoke-report.json`, 16/16 routes PASS. Refreshed viewport screenshots and `screenshots.sha256` are included.

An exact-head GitHub owner-review artifact was published for the prior candidate `8d44970ccabe8146c1b3538fd4ae1dd18630f908`: artifact `pr473-fresh-mobile-header-menu-review-8d44970ccabe8146c1b3538fd4ae1dd18630f908` (run 36685329332). Exact-head review will be regenerated for the corrected candidate. The current-head seamless-brand workflow exposed Reader and Listener lockup bounding boxes 0.69 px above the top edge at mobile 100% zoom, caused by their 56 px mastheads being shorter than the 56.39 px canonical lockup. Both mobile mastheads now use 58 px. The Reader high-zoom gate passes all 23 assertions, and the experience/footer zoom gate passes all 24 assertions against corrected fixture builds. Current main used the shared 72 px mobile masthead, so both were Task A regressions. This is not a production deployment or release approval; audiobook release remains fail-closed.
