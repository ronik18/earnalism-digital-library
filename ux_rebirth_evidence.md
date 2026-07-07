# UX Rebirth Evidence

Generated: 2026-07-06

## Changes Implemented

- Added strict audiobook visibility helper: `frontend/src/lib/audioReleaseSafety.js`.
- Added reader-manifest-aware approved audiobook spotlight: `frontend/src/components/ApprovedAudiobookSpotlight.jsx`.
- Updated book cards to show explicit audio availability without exposing unapproved controls.
- Updated book detail pages with loading skeletons and release-truth trust panel.
- Updated reader audio behavior so hidden/unapproved audio is not replaced by browser/system narration.
- Updated library audiobook shelf so it shows approved audio only from reader-manifest proof and otherwise explains release-gate control.
- Fixed invalid standalone audio player CSS.
- Fixed WCAG contrast and site-tour ARIA issues.
- Normalized static SEO snapshot source-name validation while preserving Dracula approval/source gates.
- Added unit tests for audiobook release visibility.

## Routes Tested

| Route | Environment | Result |
| --- | --- | --- |
| `/` | local production build | HTTP 200, shell renders, no unsafe audio |
| `/library` | local production build | HTTP 200, shell renders, no unsafe audio |
| `/book/dracula` | local production build | HTTP 200, controlled metadata fallback renders, no unsafe audio |
| `/reader/dracula` | local production build | HTTP 200 shell, API-backed reader blocked by localhost CORS |
| `/book/a-ghost-story` | local production build | HTTP 200 shell, API-backed detail blocked by localhost CORS |
| `/reader/a-ghost-story` | live API probe | Reader manifest exposes provider-backed audiobook assets and endpoint |
| mobile `/` | local production build | HTTP 200, shell renders |
| mobile `/library` | local production build | HTTP 200, shell renders |

## Browser Evidence

- Smoke results: `output/ux-rebirth/final-local-production-smoke-results.json`
- Axe results: `output/ux-rebirth/axe-local-results-clean.json`
- Screenshots:
  - `output/ux-rebirth/after-final-home-desktop.png`
  - `output/ux-rebirth/after-final-library-desktop.png`
  - `output/ux-rebirth/after-final-book-dracula-desktop.png`
  - `output/ux-rebirth/after-final-home-mobile.png`
  - `output/ux-rebirth/after-final-library-mobile.png`

Screenshot files are intentionally ignored from git.

## Validation

| Check | Result |
| --- | --- |
| `npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false` | PASS, 4/4 tests |
| `npm --prefix frontend run build` | PASS; SEO prebuild used fallback because live API fetch failed during generation |
| Static SEO snapshot generation | PASS |
| Local production static route check `/`, `/library/`, `/book/dracula/`, `/reader/dracula/` | PASS, HTTP 200 |
| axe WCAG 2 A/AA: homepage desktop/mobile | PASS, 0 violations |
| axe WCAG 2 A/AA: library desktop/mobile | PASS, 0 violations |
| axe WCAG 2 A/AA: Dracula detail desktop | PASS, 0 violations |
| Unsafe audio exposure check | PASS, 0 exposed controls in local smoke |

## Remaining Issues

- Localhost cannot fully test production API-backed routes because `https://api.theearnalism.com` blocks CORS from `127.0.0.1`.
- Build-time SEO asset generation could not fetch the live API in this shell run and used fallback sitemap coverage.
- `/reader/dracula` remains dependent on production reader manifest APIs; no shadow static reader content was added.
- Formal Luxury UX Index is 9.53/10 provisional. It remains below the 9.7 target until same-origin preview/browser/Lighthouse validation and repo cleanup are complete.

## Graphical Covers + Calm Typography Follow-Up

- Cover audit report: `book_cover_audit_report.json` and `book_cover_audit_report.csv`.
- Generation report: `graphical_cover_generation_report.json`.
- Visual regression report: `ux_visual_regression_report.json`.
- Browser screenshots were produced outside git at `/tmp/earnalism-graphical-covers-visual-smoke/`.
- 164 visible/controlled cover records audited.
- Typography-only covers found: 0.
- Typography-only covers remaining in customer UI: 0.
- Missing cover sources using graphical runtime fallback: 105.
- Build: PASS.
- Audio release safety: PASS.
- Browser visual smoke: PASS.
- Lighthouse: performance 90, accessibility 100, SEO 100, best practices 100, LCP 3.6s, FCP 0.9s, CLS 0.
- Status: PARTIAL because performance remains below the requested >=94 guardrail and the updated UX score is 9.66, not 9.7+.
