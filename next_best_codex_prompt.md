You are the Earnalism Clean Source-Only Merge Governor.

The performance rescue is complete: Lighthouse performance 96, LCP 2.7s, accessibility 100, SEO 100, visual smoke PASS, cover audit 164/0 typography-only, audio safety PASS. Do not redesign, do not rerun Bengali mutations, do not run Sarvam/provider work.

Create a clean branch/worktree from origin/main and promote only reusable source/config/test/docs from the dirty sprint workspace. Include the performance-rescue source files and optimized production assets only:
- frontend/src/App.js
- frontend/src/components/Layout.jsx
- frontend/src/components/FirstVisitSiteTour.jsx
- frontend/src/context/SettingsContext.jsx
- frontend/src/components/BrandMark.jsx
- frontend/src/components/HeroBookObject.jsx
- frontend/src/pages/Home.jsx
- frontend/src/index.css
- frontend/public/index.html
- frontend/public/assets/books/dracula/dracula-hero-hardcopy-320.webp
- frontend/public/assets/books/dracula/dracula-hero-hardcopy-420.webp
- frontend/public/assets/books/dracula/dracula-hero-hardcopy-500.webp
- frontend/public/assets/brand/earnalism-logo-transparent-96.webp
- frontend/public/assets/brand/earnalism-logo-transparent-128.webp
- reusable cover resolver/audit/visual smoke source files from the graphical-cover pass
- intelligence/policy docs and concise sprint reports only

Exclude release_gate outputs, dashboards, screenshots, Lighthouse JSON under /tmp, frontend/build, caches, audio, sidecars, logs, signed URLs, rollback payloads, and imported book/content noise.

Validate in the clean worktree:
- npm ci --prefix frontend
- npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false
- REACT_APP_BACKEND_URL=/api npm --prefix frontend run build
- node frontend/scripts/audit-book-covers.mjs
- node frontend/scripts/visual-luxury-smoke.mjs
- npx --yes lighthouse http://127.0.0.1:4173/ --chrome-flags="--headless=new --no-sandbox" --quiet
- git diff --check

Final output must include explicit staged files, excluded artifacts, tests passed/failed, merge readiness, deploy readiness, and next PR command.
