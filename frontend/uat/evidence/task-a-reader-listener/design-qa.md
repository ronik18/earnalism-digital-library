# Task A: Reader and Listener visual QA

**Design QA result: passed**

## Reference and implementation

- Reference: `/Users/ronikbasak/Documents/ChatGPT Image Sep 29, 2026, 11_45_50 PM.png` (1536 × 1024 px).
- Local implementation: clean `codex/reader-listener-beige-experience` worktree based on merged PR471 `57237eb76c24022f02214ce08fd02b7869fe411`.
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

## Verification

- Complete frontend Jest suite: 83 suites, 520 tests passed (including focused Reader/Listener release-truth tests).
- `npm run build --prefix frontend`: passed.
- Static SEO verifier: 34/34 snapshots, 703 assertions, 0 failed.
- `git diff --check`: passed.
- Full visual smoke report: `visual-smoke-report.json`, PASS.

This packet supports owner review of the exact pull request head when published by the repository's PR469 post-merge recovery owner-evidence workflow. It is not a production deployment or release approval; audiobook release remains fail-closed.
