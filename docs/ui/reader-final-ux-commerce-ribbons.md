# Reader final UX and Commerce ribbons

## Scope and dependency

This local follow-up is based on PR #516 head `d20f59fa6eac264302de9ad15cb7df6f75f874d6`, which supplies the shared header polish and “NO auto-renewals” presentation correction. Integrate this follow-up only after that dependency is reconciled. It changes no Reader application, backend, catalogue, rights, payment, entitlement, audio, or deployment behavior. No production deployment or ingestion was performed.

## Reader verification

The existing merged public Reader was exercised using the normal production build and generated, repository-owned three-page/two-chapter API fixtures. This proves rendered UI behavior, not production content authorization or backend availability. The committed browser runner rejects non-loopback base URLs, blocks mutations, and writes evidence outside Git.

All seven Chromium viewports passed: 1440×900, 1280×720, 1024×768, 768×1024, 390×844, 844×390, and 1280×600. Actual Chrome tab zoom of 125% and 150% also passed; physical 1440×900 produced CSS viewports 1152×720 and 960×600 respectively.

Verified first/last disabled arrows, chapter transitions, directional animations, internal scrolling for oversized content, no horizontal overflow or unnecessary outer scrolling, rapid and alternating navigation, keyboard navigation and exclusions for form/editable/media/ARIA controls, Back/Forward, refresh, focus reachability, reduced motion, and no console/runtime errors or unexpected writes. Screenshots were inspected after finite animations completed. No Reader code correction was required.

Reproduction against a local production-built frontend:

```sh
READER_UX_BASE_URL=http://127.0.0.1:13384 node scripts/verify_reader_final_ux.mjs
```

Local evidence: `/tmp/reader-final-ux/summary.json`, first/last screenshots per viewport; `/tmp/reader-final-ux-zoom125/native-reader-first.png`; `/tmp/reader-final-ux-zoom150/native-reader-first.png`. These temporary paths are execution evidence, not durable hosted artifacts.

## Header and Blog

The shared Header consumes `frontend/src/config/publicNavigation.js`; Blog is already declared once and links to `/journal`. The reported omission was not reproduced in a fresh anonymous production Home browser: desktop Blog was visible; at mobile width it was visible after opening the collapsed navigation menu. Unexpected writes, including analytics POSTs, were blocked. No duplicate Blog item or new header code was added.

Local header checks passed at 1440×900 and 390×844 across Home, Library, Book Detail, Commerce, About, Journal, Login, and Signup. The Reader checks also used the shared primary header. Official artwork and responsive logo sizing were preserved.

## Commerce treatment

All three Institutions/Publishers/Gift cards retain the same compact COMING SOON label. The shared rule now uses a burgundy theme-token fill, cream text, gold border, 28px minimum height, 5px/11px padding, 11px semibold type, and restrained letter spacing. The rendered theme colors are `#351018` and `#FFF3D7`, giving approximately 15.38:1 text contrast. No business or renewal logic changed. “NO auto-renewals” is present in the PR #516 baseline.

Commerce cards were inspected at 1440×900 and 390×844. Screenshot-only suppression of the sticky header was used for the mobile card crop so it does not obscure the first badge; application header behavior was unchanged. Local screenshots: `/tmp/reader-header-commerce-final/commerce-ribbons-1440.png` and `commerce-ribbons-390.png`.

## Validation

- Focused Header/Commerce tests: 5 suites, 34 tests passed.
- Full frontend: 97 suites, 619 tests passed.
- Production build: passed.
- Static SEO: 172 snapshots, 3,647 assertions, zero failures.
- Browser: seven Reader sizes, two actual zoom levels, sixteen primary-header route/viewport combinations, and two Commerce card views passed.
- No standalone lint/typecheck script is defined in the frontend package; the production build performs its existing checks.
- Git whitespace/diff check: passed before commit.

PR #516 still occupies the single focused-PR slot. Its seamless-brand workflow failed on the separate deterministic assertion “binds both production-hash authorities to checked-in production source”; this follow-up does not alter or bypass that gate. No follow-up PR was opened or pushed, and no merge or deployment was performed.
