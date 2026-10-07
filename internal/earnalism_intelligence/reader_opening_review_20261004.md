# Reader opening review — 2026-10-04

## Architecture
The screenshot originates from `ReaderExperienceV2Route` at `/reader/:slug`: manifest bootstrap shows Opening reader, then its first authorized canonical-page request shows Opening page. The manifest supplies title/author before page content is ready. The original page cache, retained authorized page, entitlement/rights checks, identity checks, session settlement, page fetching, and ordinary page-turn transitions remain authoritative. Protected/deep-link denial states retain their existing recovery rather than being presented as network failure. Only network/5xx bootstrap failures use the new retry screen.

The existing canonical opening returns now use ReaderOpening. No second fetch, cover download, minimum animation duration, or readiness state exists. Metadata arrives without restarting the book motif. Initial entry/reload/deep-link bootstrap uses this surface; normal page navigation keeps authorized content and existing inline progress. Authentication remount continues existing principal isolation.

## Design and motion
Book Awakening: warm radial paper light, burgundy covers, cream leaves, gold gutter, editorial title/author. Fixed original copy: “A quiet page, opening into another world.” Thin indeterminate reading line, quiet 44px Back to Library target. Covers open once over 950ms, leaves/light over 1100ms; only the small indicator continues. After 2500ms status becomes Still preparing your page. The opening unmounts immediately upon genuine readiness; the stable reading canvas has a 220ms opacity/3px arrival. Page turns do not remount it. Reduced motion disables all book/progress movement and uses a 150ms opacity-only canvas arrival.

## Actual browser verification
Chrome, actual route/Reader components, loopback generated fixture API. No production/customer data and no production request. Tested CSS viewports: 1440×900, 1279×720 (requested approximately1280), 1024×768, 768×1024, 390×844, 844×390, 1279×600 (requested approximately1280). At every size document width and height matched the viewport; escape remained reachable. Landscape compresses into book/text columns. Screenshots were rendered and inspected for desktop/laptop/tablets/mobile/short-height. Generic and personalized states, static reduced motion, 503 recovery/retry, ready handoff and next-page behavior passed. Browser console errors: zero observed.

Local generated delayed API measurements, milliseconds (request elapsed / response-to-Reader DOM): 300ms fixture 301.7 /28.6; 1s fixture1001 /14.8; 3s fixture3000.6 /16.8; immediate fixture0 /24.5. These measure fixture DOM delivery, not production network/performance. Slow copy stays non-error. No animation wait is added. Earlier diagnostic measurements overwritten by prefetch were discarded.

Evidence outside Git: /Users/ronikbasak/Documents/Earnalism audits/2026-10-04-reader-opening/ (desktop-opening-final.png, mobile-opening-final.png, final viewport screenshots, reduced-motion.png, error.png, reader-ready.png, mobile-reader-ready.png, verification.json).

## Accessibility and safety
Live polite atomic status contains Opening [title]; decorative book is hidden; semantic keyboard buttons, visible focus, 44px escape/retry targets. Focus continuity is restored only if the opening escape had focus; existing Reader focus behavior remains. Text contrasts against warm paper, with no status conveyed solely by color. Long titles wrap; unusually large font content can scroll instead of clipping. Rights/integrity/auth denials remain fail closed and are not converted to a retry bypass.

## Validation and performance
Targeted: 3 suites/53 tests PASS. Full frontend:98 suites/617 tests PASS. Production build PASS; static SEO172 snapshots/3647 assertions/0 failed. No standalone lint/typecheck scripts defined; build compiled successfully. Diff check PASS.

Fresh production build comparison against exact clean main cdb654d51f94f782063cf79a27c4a93a6a2c0809, same dependencies/commands, deterministic gzip sums of JS/CSS excluding source maps: JS474784→475698 bytes (+914); CSS98822→100208 (+1386). Total+2300 bytes. No dependencies/assets added; transforms/opacity, small CSS motif, no canvas/video/Lottie. This is build-size and local fixture timing evidence, not a production startup benchmark.

## Release gate
Local isolated branch codex/reader-opening-premium-transition from cdb654d51f94f782063cf79a27c4a93a6a2c0809. Canonical integration and historical dirty worktrees preserved. PR516 still occupies single focused slot. No push, PR, merge or deploy. Next integration action: after PR516 closes, refresh main and review this focused commit for canonical integration and protected CI. Do not deploy from this local branch.
