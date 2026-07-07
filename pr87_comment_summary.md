PR #87 blocker rescue summary:

- Restored Kshudhita pipeline selectors and safe notify CTA expected by browser regression.
- Updated controlled-launch/catalog regression tests to enforce release truth without stale exact catalog equality in source-only PR mode.
- Replaced Vercel non-main blanket ignore with a fail-safe changed-file ignore helper so PR previews can build.
- Made visual smoke fail closed and require real Playwright browser execution; local run completed 24/24 checks.
- Fixed production-equivalent `/api` override so local same-origin validation no longer calls the production API from `127.0.0.1`.

Local validation:

- `npm ci --prefix frontend`: PASS
- Audio safety test: PASS, 4/4
- Build: PASS
- Cover audit: PASS, 0 typography-only customer-facing covers
- Visual smoke: PASS, browser executed
- Lighthouse: performance 96, LCP 2803ms, accessibility 100, SEO 100
- Targeted regression modules: PASS, 72 tests
- Full local regression suite: PASS, including Kshudhita browser e2e
- Backend publication safety: PASS, 10 tests

Preview status: fixed locally but pending commit/push and Vercel rerun. Do not merge until preview/checks rerun or owner explicitly accepts local production-equivalent validation plus post-merge verification.
