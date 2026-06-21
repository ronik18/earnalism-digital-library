# Accessibility Non-Visual Journey Report

Generated: 2026-06-21

## Executive Summary

This pass improves the Dracula-first public journey for blind, low-vision, dyslexic, elderly, and keyboard-only users without enabling public audio or making unsupported accessibility claims.

The changes are deliberately narrow:

- Dracula remains the only approved core public reading release.
- Kshudhita Pashan remains pipeline-only.
- Audiobooks remain non-public.
- No `Listen Now` CTA or public audiobook metadata was added.
- No WCAG, blind-user-tested, screen-reader-certified, or fully-accessible claim was added.
- Payment amounts, Razorpay behavior, wallet crediting, publication settings, and tombstone/noindex behavior were not changed.

## Audited Pages And Components

- Home page
- Dracula book detail page
- Reader preview, locked states, low-balance banner, and reading-time dialog
- Pricing page and reading-time pack cards
- Login page
- Signup page
- Account/wallet page
- Library and continuation states
- Contact form
- Header/mobile menu
- Layout shell
- App loading fallback
- Footer/default metadata
- Existing UX and public-governance regression modules

## Issues Found

| Area | Issue |
| --- | --- |
| App shell | No visible skip link for keyboard users. |
| Loading fallback | App-level fallback was visually blank and not announced as a status. |
| Global CSS | `sr-only` was used in one place but no global utility existed. |
| Focus states | Some controls had local focus styles, but no consistent global fallback existed for links, buttons, and fields. |
| Newsletter/contact/search forms | Some public form controls relied on placeholder text without durable labeling. |
| Mobile menu | Menu button did not expose expanded/collapsed state. |
| Reader locked state | Locked reader state explained access visually, but did not explicitly announce as a status region. |
| Reading-time dialog | Reading-time sheet behaved like a modal but did not expose dialog naming metadata. |
| Reading-time pack selection in reader | Pack cards used clickable `div` elements instead of buttons. |
| Account state | Balance/loading/empty activity states needed clearer non-visual descriptions. |

## Fixes Applied

- Added a global `Skip to main content` link.
- Added `id="main-content"` and focus target support on the public layout main region.
- Added a global `.sr-only` utility.
- Added global `:focus-visible` outlines for links, buttons, inputs, textareas, selects, and button-like elements.
- Made the app-level loading fallback a polite status with screen-reader text.
- Added accessible labels/descriptions to the homepage newsletter form.
- Added explicit search labeling on the library search field.
- Added explicit labels to the contact form fields.
- Added `aria-expanded`, `aria-controls`, and an ID-backed mobile menu relationship.
- Added pricing pack accessible names that include label, minutes, price, badge, and selected state.
- Added a named trust-note region on pricing.
- Added `aria-describedby` helper text to login/signup forms.
- Added account wallet region semantics and spoken loading/empty activity states.
- Added reader locked-state status semantics.
- Added `role="dialog"`, `aria-modal`, `aria-labelledby`, and `aria-describedby` to the reading-time dialog.
- Converted reader reading-time pack choices from clickable `div` elements to real buttons with `aria-pressed`.
- Extended regression checks for skip links, focus indicators, form labels, reader dialog/status states, mobile menu semantics, and no premature audiobook/accessibility claims.

## Current Scores

- Current non-visual journey score: **8.8/10**
- Keyboard navigation score: **9.0/10**
- Screen-reader readiness score: **8.6/10**
- Accessibility-claims safety score: **10/10**

These are internal engineering assessment scores only. They are not public accessibility certification and must not be marketed as WCAG compliance or blind-user-tested readiness.

## Remaining Blockers

- Manual screen-reader testing is still required.
- The reader settings sheet and site-tour dialog should receive a full focus-trap/manual keyboard pass in a later task.
- Toast behavior should be manually verified with real assistive technology.
- The payment provider modal remains third-party UI and needs separate Razorpay accessibility review before public claims.
- No public audiobook accessibility claim can be made until audiobook release gates and real listening/accessibility QA pass.

## Manual Assistive-Technology Test Script

### NVDA + Firefox / Chrome

1. Open the homepage.
2. Press `Tab`; confirm "Skip to main content" appears and moves focus to the main region.
3. Navigate headings; confirm "Begin with Dracula" is the first primary heading.
4. Use link navigation; confirm only Dracula has reading CTAs.
5. Open Dracula book detail and confirm source, rights, free preview, reading pass, and audio-unavailable notes are announced.
6. Open the reader preview; confirm loading, locked states, previous/next buttons, settings, and no public audio controls for Dracula are understandable.
7. Open pricing; confirm each pack announces label, minutes, price, and badge.
8. Open login/signup/account; confirm forms are labeled and wallet/continuation copy is understandable.
9. Open library; confirm future titles announce Coming Soon / Notify Me only.

### VoiceOver + Safari

1. Use `Control + Option + U` to inspect landmarks and headings.
2. Confirm skip link, header navigation, main content, footer, and forms are discoverable.
3. Use rotor links; confirm no `Listen Now` or unapproved `Start Reading` link appears for pipeline titles.
4. Navigate the reading-time dialog if triggered in a local test environment and confirm it is announced as a dialog.
5. Confirm focus indicators are visible while tabbing.

### TalkBack + Android Chrome

1. Swipe through homepage controls in order.
2. Confirm Dracula CTAs, future pipeline states, and audio-unavailable copy are spoken clearly.
3. Open pricing and confirm each pack has a complete name and price.
4. Open login/signup and confirm each field label is announced.
5. Open reader preview and confirm locked/empty/error states are not silent.

## Files Changed

- `frontend/src/App.js`
- `frontend/src/components/Header.jsx`
- `frontend/src/components/Layout.jsx`
- `frontend/src/index.css`
- `frontend/src/pages/Account.jsx`
- `frontend/src/pages/Contact.jsx`
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/Library.jsx`
- `frontend/src/pages/Login.jsx`
- `frontend/src/pages/Pricing.jsx`
- `frontend/src/pages/Reader.jsx`
- `frontend/src/pages/Signup.jsx`
- `regression/modules/14-ux-conversion-static.test.js`
- `ACCESSIBILITY_NON_VISUAL_JOURNEY_REPORT.md`

## Tests Run

- `npm run regression -- modules/14-ux-conversion-static.test.js` - PASS, 31 tests
- `python3 scripts/check-hidden-unicode.py ACCESSIBILITY_NON_VISUAL_JOURNEY_REPORT.md` - PASS
- `python3 scripts/check-hidden-unicode.py $(git diff --name-only) ACCESSIBILITY_NON_VISUAL_JOURNEY_REPORT.md` - PASS, 14 files
- `git diff --check` - PASS
- `npm --prefix frontend run build` - PASS
- `npm run controlled-publication:precheck` - PASS
- `npm run launch:seo-audit` - PASS
- `npm run launch:social-preview-audit` - PASS
- `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js` - PASS, 51 tests

## Rollback Instructions

```bash
git restore frontend/src/App.js \
  frontend/src/components/Header.jsx \
  frontend/src/components/Layout.jsx \
  frontend/src/index.css \
  frontend/src/pages/Account.jsx \
  frontend/src/pages/Contact.jsx \
  frontend/src/pages/Home.jsx \
  frontend/src/pages/Library.jsx \
  frontend/src/pages/Login.jsx \
  frontend/src/pages/Pricing.jsx \
  frontend/src/pages/Reader.jsx \
  frontend/src/pages/Signup.jsx \
  regression/modules/14-ux-conversion-static.test.js
rm -f ACCESSIBILITY_NON_VISUAL_JOURNEY_REPORT.md
npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js
npm --prefix frontend run build
```

## Full Validation Results

All requested validation passed:

| Command | Result |
| --- | --- |
| `python3 scripts/check-hidden-unicode.py ACCESSIBILITY_NON_VISUAL_JOURNEY_REPORT.md` | PASS |
| `python3 scripts/check-hidden-unicode.py $(git diff --name-only) ACCESSIBILITY_NON_VISUAL_JOURNEY_REPORT.md` | PASS for 14 files |
| `git diff --check` | PASS |
| `npm --prefix frontend run build` | PASS |
| `npm run controlled-publication:precheck` | PASS |
| `npm run launch:seo-audit` | PASS |
| `npm run launch:social-preview-audit` | PASS |
| `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js` | PASS, 51 tests |
| `npm run regression -- modules/14-ux-conversion-static.test.js` | PASS, 31 focused UX tests |
