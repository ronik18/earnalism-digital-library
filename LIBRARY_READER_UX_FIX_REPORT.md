# Library And Reader UX Fix Report

Status: READY_FOR_REVIEW_PENDING_VALIDATION

## Scope

This pass fixes the live library and Dracula reader journey while preserving the controlled launch boundaries:

- Dracula remains the only public reading release.
- Chapter 1 remains free.
- Reading continuation remains tied to reading time/pass/wallet behavior.
- Pipeline books remain interest-only.
- Public audiobook release remains blocked.
- No payment behavior was changed.

## Root Cause

The reader frontend could accidentally mix public reading with an admin/login session:

- `getChapterAuthHeaders()` previously reused admin/local generic tokens when no user token existed.
- Normal `/reader/dracula` book loading could fall back to `/admin/books/{slug}` when a public lookup failed and an admin token was present.
- That made normal reader behavior depend on unrelated admin/login state and could produce a blank or unavailable reader path in mixed sessions.

The fix keeps public reading and admin preview separate:

- Normal reader chapter requests use only the user token key.
- Admin preview paths require explicit admin preview mode.
- Admin preview appends `preview=admin` and uses admin auth only in that path.

## Library UX Improvements

- Rebuilt `/library` as a calm reading-room page rather than a ledger-like launch page.
- Added a full-bleed Golden Hour Library hero with Dracula as the only live conversion object.
- Preserved CTA hierarchy:
  - Read Chapter 1 Free
  - Start Dracula
  - Get 7-Day Reading Pass
- Added premium launch facts:
  - Approved classic reading release
  - Chapter 1 free
  - Public-domain source verified
  - Audiobook experience in private review
- Added a Kshudhita Pashan pipeline spotlight using the real local front/back cover assets.
- Removed giant Bengali title treatment from the primary pipeline copy by using "The Hungry Stones" as the visible headline and keeping the Bengali title as a smaller metadata line.
- Replaced raw initial-only fallback covers with designed Earnalism shelf placeholders for pipeline titles without safe local covers.

## Reader Improvements

- Normal `/reader/dracula` no longer borrows the admin token.
- Admin preview remains possible only through explicit admin preview behavior.
- Reader topbar and chapter index use cleaned display titles.
- Book detail chapter list uses the same cleaned display titles.

## Public Guardrails

- Public audio: PUBLIC_AUDIO_RELEASE_BLOCKED
- Audiobook production: PRODUCTION_BLOCKED
- Listen Now CTA: not added
- AudioObject metadata: not added
- Kshudhita public reading/payment/audio CTA: not added
- Payment behavior: unchanged

## Screenshot Artifacts

Visual review output:

- `output/visual-review/library-reader-polish/library-desktop-1440.png`
- `output/visual-review/library-reader-polish/library-laptop-1280.png`
- `output/visual-review/library-reader-polish/library-tablet-768.png`
- `output/visual-review/library-reader-polish/library-mobile-390.png`
- `output/visual-review/library-reader-polish/book-dracula-chapters-desktop-1440.png`
- `output/visual-review/library-reader-polish/reader-dracula-logged-out-desktop-1440.png`

The `/book/dracula` and `/reader/dracula` screenshots use safe local Playwright API mocks because production API CORS blocks a static `127.0.0.1` screenshot origin. The mocks contain no secrets, payment data, or real customer data.

Admin-authenticated reader preview was not screenshot-tested because this worktree has no owner/admin auth fixture. Static regression now verifies that admin preview is explicit and normal `/reader/dracula` does not borrow the admin token.

## Recommendation

Proceed to validation. Do not deploy or merge until the full static, build, canary, and public-audio scans pass.
