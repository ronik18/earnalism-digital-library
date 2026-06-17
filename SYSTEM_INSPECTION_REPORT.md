# Earnalism Automation System - Phase 0 System Inspection Report

Generated: 2026-06-17

## Scope

This report inspects the current Earnalism repository and production-facing public surfaces for the approved Automation System. Phase 0 is documentation-only and does not change production behavior.

## Repository Shape

- Frontend: React 19 single-page app in `frontend/`, built with CRACO/react-scripts and deployed to Vercel.
- Backend: Python FastAPI app in `backend/server.py`, deployed to Railway.
- Database: MongoDB via Motor/PyMongo.
- Cache/state: Redis support for public cache, reader content cache, auth/session/wallet cache, rate limits, startup lock, and autoscaling-safe state.
- Media: Cloudinary for covers/images/small assets; Backblaze B2 S3-compatible routing for large audiobooks.
- Payments: Razorpay top-ups for reading-time wallet.
- Auth: Admin JWT/cookie; reader email/password, Google OAuth, optional OTP; refresh-token reader sessions.
- Admin: React admin dashboard in `frontend/src/pages/Admin.jsx`.
- SEO: Build-time sitemap/robots generation via `frontend/scripts/generate-seo-assets.mjs`; page-level SEO hooks and JSON-LD components exist.
- CI/CD: GitHub Actions regression gate, regression suite, post-deploy k6, and production monitoring workflows.
- Automation base: Existing book import scripts, audiobook onboarding/polish scripts, B2 upload router, regression modules, production monitor, Growth OS control-plane scaffold.

## Public Catalog Snapshot

Read-only public API checks on 2026-06-17:

- `GET https://api.theearnalism.com/api/books`: 105 published books.
- `GET https://api.theearnalism.com/api/categories`: 9 categories.
- `GET https://api.theearnalism.com/api/blog`: 3 journal posts.
- Public category distribution:
  - business: 5
  - gothic-fiction: 19
  - history-strategy: 8
  - literary-fiction: 44
  - adventure: 9
  - science-fiction: 3
  - young-readers: 6
  - technology: 1
  - bengali-classics: 10
- Public API indicated 102 books with mapped audiobook fields/assets.
- Public book responses hide `rights_metadata`, so public inspection cannot prove rights completeness.
- Generated `frontend/public/sitemap.xml` currently contains 123 URLs and does not include admin/login/reader routes.

## Backend Inspection

Main file: `backend/server.py`

Important route groups:

- Public health: `/health`, `/healthz`, `/api/health`, `/api/healthz`.
- Home/catalog: `/api/home`, `/api/home/books`, `/api/categories`, `/api/books`, `/api/books/{slug}`, `/api/books/{slug}/chapters`.
- Reader content: `/api/reader/book/{slug}/manifest`, `/api/reader/chapter/{slug}/{chapter_id}`, reader session and pulse routes.
- Audiobook streaming: reader manifest and B2-aware audiobook proxy helpers are present.
- Auth: admin login/change-password; reader signup/login/logout/refresh; Google OAuth; OTP hooks.
- Admin CMS: books, chapters, cover upload, image upload, categories, blog, newsletter, contacts, settings, featured book.
- Payments/wallet: packs, Razorpay top-up/verify/webhook, simulation endpoints, wallet admin/reconciliation.
- Monitoring/security: reader security events, reader metrics, Redis cache status.
- Growth OS: `/api/admin/growth/overview`, `/api/admin/growth/run-daily`, `/api/admin/growth/kill-switch`.

Current model coverage:

- `Book` supports embedded chapters, cover/back-cover fields, publishing flag, audiobook fields, and generic `rights_metadata` on input.
- `Chapter` supports content, preview flag, language hint, source filename, processing status, and warnings.
- Blog/category/user/wallet/payment/session models are present.
- Growth OS collections/indexes exist for agent runs/actions, guardrails, tool calls, budgets, metrics snapshots, incidents, audit logs, and feature flags.

Gaps for the approved Automation System:

- No deterministic rights verifier model/service yet.
- `rights_metadata` exists but is generic and not enforced as a publication gate.
- No formal publishing workflow state machine for discovered-to-published lifecycle.
- No demand scoring service/dashboard yet.
- No source ingestion connector cache model for Gutenberg/Wikisource/Standard Ebooks/manual/OCR sources.
- No edition artifact model tying source hash + prompt version + quality score to generated outputs.
- No explicit catalog quarantine/noindex/archive/delete model.

## Frontend Inspection

Main routes in `frontend/src/App.js`:

- Public: `/`, `/library`, `/book/:slug`, `/journal`, `/journal/:slug`, `/about`, `/contact`, `/pricing`, `/micro-story`.
- Reader: `/reader/:slug`.
- Admin: `/admin/login`, `/admin`.
- Legacy redirects: `/signin`, `/shop`, `/shop/:slug`, `/publishing/*`.
- Unknown route: wildcard `NotFound`.

Key components:

- `BookCard`, `BookCoverImage`, `AudioPlayer`, `SecureReader`, `ShareButtons`, `JsonLd`, `FirstVisitSiteTour`.
- Admin upload components: `ChapterUpload`, `CoverUpload`.
- SEO hook: `useSEO`.
- API clients: `frontend/src/lib/api.js`.
- Funnel analytics helpers: `frontend/src/lib/funnelAnalytics.js`.

Admin dashboard currently supports:

- Books, blog, categories, newsletter, contacts, users, payments, security, Growth OS, settings, account.

Gaps:

- No rights-specific admin UI.
- No demand score dashboard.
- No source traceability dashboard.
- No publication workflow board.
- No catalog cleanup/quarantine UI.
- No edition-generation artifact viewer.

## CMS And Publishing Pipeline

Existing capabilities:

- Admin book CRUD and chapter CRUD.
- DOCX upload and validation path.
- `scripts/import_books.py` supports legally-cleared source ingestion, source boilerplate stripping, dry-run by default, and optional admin upload.
- `scripts/bulk_publishing_pipeline.py` orchestrates import, readiness checks, regression, and deployment steps.
- `scripts/open_source_audiobook_onboarding.py` generates/onboards synced audiobook bundles.
- `scripts/audio/polishBengaliAudiobooks.js` and `scripts/audio/polishEnglishAudiobooks.js` support resumable audiobook polish jobs.

Gaps:

- Rights verification is embedded in import heuristics rather than a reusable rights engine.
- No deterministic first-publication/death-year/publication-region rights tiering.
- No OCR ingestion workflow.
- No formal generated study-material pipeline with cached artifact reuse.
- No automated quality gates for study usefulness, factuality, citation coverage, and visual clarity.

## Media And Audio Assets

- Cloudinary upload support exists via backend config and admin routes.
- `lib/storage/audioUploader.js` routes audiobooks at or below 100 MB to Cloudinary and larger files to B2 with multipart upload.
- Reader/audio code is designed to avoid Redis media-binary caching.
- Audiobook polish scripts have QA scoring, chunk cache/progress files, provider abstraction, and storage cleanup script.

Gaps:

- Audio QA is script-centric, not yet a first-class backend model/dashboard.
- No formal linked-book rights gate before publishing audio beyond script conventions.
- No unified audio QA report collection.
- No Hindi pipeline yet.

## Environment And Deployment

Backend example env includes:

- MongoDB, JWT, CORS/cookies, Redis, rate limits, public cache, Judoscale.
- Razorpay, Cloudinary, B2.
- Bengali/English audiobook polish settings.
- Growth OS dry-run flags.
- Google OAuth and OTP.

Deployment:

- Backend Railway config: `backend/railway.json`, `backend/Dockerfile`, `backend/Procfile`.
- Frontend Vercel deploy support through GitHub Actions when Vercel secrets are configured.
- `scripts/commit_push_deploy.sh` exists for local terminal commit/push/deploy flow.

## Tests And CI

Backend tests:

- Payment/Razorpay policy tests.
- Reader billing and chapter gating tests.
- Redis cache policy tests.
- Content processor safety tests.
- Bengali content pipeline tests.
- B2 audiobook routing tests.
- Growth OS tests.

Regression suite:

- Book integrity.
- Rendering/visual.
- Audiobook sync.
- Legal compliance.
- URL navigation.
- SEO.
- Redis cache.
- MongoDB performance.
- Infrastructure readiness.
- E2E UAT.
- Security access control.
- Migration/data consistency.

CI workflows:

- `.github/workflows/regression.yml`: GO LIVE gate, Railway deploy, Vercel deploy.
- `.github/workflows/regression-suite.yml`: backend/frontend/browser regression.
- `.github/workflows/post-deploy-k6.yml`: k6 smoke/load checks.
- `.github/workflows/production-monitor.yml`: scheduled production monitor.

## Observability

Existing:

- Structured backend request logs with request IDs and response time headers.
- Security headers and no-store admin/user/reader cache headers.
- Reader RUM metrics endpoint and Redis aggregation support.
- Production monitor script.
- GitHub Actions artifacts for monitor/regression.
- Redis cache status admin endpoint.
- Growth OS audit logging scaffold.

Gaps:

- No dedicated Sentry/error-monitor integration found in repository.
- No dead-letter queue for automation jobs.
- No unified cost dashboard.
- No first-class job-run database collection for ingestion/generation/audio jobs outside Growth OS.

## Phase 0 Conclusion

The repository is ready for a phased Automation System, but the next phase should not generate or publish new content. The safest next step is Phase 1: a dry-run public catalog audit and governance layer that discovers irrelevant, thin, duplicate, broken, or rights-incomplete public content without changing public behavior until reports are reviewed.
