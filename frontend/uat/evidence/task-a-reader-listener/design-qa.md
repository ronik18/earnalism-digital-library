# Task A: Reader and Listener visual QA

**Design QA result: passed**

## Reference and implementation

- Reference: `/Users/ronikbasak/Documents/ChatGPT Image Sep 29, 2026, 11_45_50 PM.png` (1536 × 1024 px).
- Implementation began from merged PR471 `57237eb76c24022f02214ce08fd02b7869fe411` and is now based on current main `e4109a1d173d3fb4928d2f59b5450f3aa2f81f71` (PR470 and PR472 included).
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
- Combined A candidate source fingerprint after rebasing current main and correcting Reader/Listener lockup clipping: `dae7b3c8d9ee47681812d3bda0477dfe392e04bca1695b711248534ee7870fe9` (independently reproduced, 333 hashed files). Both seamless-brand workflow authorities are bound to this exact source fingerprint. The canonical Earnalism logo hash remains unchanged.

## Verification

- Complete frontend Jest suite: 83 suites, 520 tests passed (including focused Reader/Listener release-truth tests).
- `npm run build --prefix frontend`: passed.
- Static SEO verifier: 34/34 snapshots, 703 assertions, 0 failed.
- `git diff --check`: passed.
- Full visual smoke report after the desktop and mobile header corrections: `visual-smoke-report.json`, 16/16 routes PASS. Refreshed viewport screenshots and `screenshots.sha256` are included.

An exact-head GitHub owner-review artifact exists for an earlier candidate but is stale after these corrections; exact-head review must be regenerated. Browser comparison against `e4109a1` exposed logo clipping in three desktop states: the new Reader and Listener headers were 62 px tall around a 79.91 px official lockup. Reader and Listener now follow the shared header contract: 92 px at desktop, 84 px at tablet, and 72 px on mobile. Focused Chromium captures show all three formerly clipped desktop states with `logo.clipped=false`. The post-merge header matrix then exposed that Reader and Listener’s desktop menu toggle was hidden while their desktop navigation was visible; the immersive desktop menu affordance is now available alongside desktop navigation and search. Navigation items and the account action are real links; ordinary clicks continue through the existing session-settlement callback. The full canonical header matrix passes 96 captures across 16 routes and six widths. Reader and Listener measured 92 px headers at 1440/1280, 84 px at 1024/768, and 72 px at 390/360; all logos were within bounds, page overwidth was zero, and the desktop menu toggle passed both pointer and keyboard interaction. A refreshed 16-capture visual smoke report and screenshots are included. The durable exact-head GitHub artifact must be regenerated after pushing the final candidate. This is not a production deployment or release approval; audiobook release remains fail-closed.
