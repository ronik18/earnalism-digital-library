# Earnalism Automation System - Risks And Blockers

Generated: 2026-06-17

## Critical Blockers

### 1. Rights metadata is not yet structured or enforced

Current state:

- `BookIn` accepts generic `rights_metadata`.
- Public book responses strip rights metadata.
- No deterministic rights verifier currently blocks publication.

Impact:

- The platform cannot safely auto-publish public-domain editions, study guides, visuals, or audiobooks until rights tiering is first-class.

Mitigation:

- Build Phase 2 rights model and verifier before any generated edition publishing.
- Require rights tier A or explicitly configured regional restriction for any public release.

### 2. Public catalog governance is not yet automated

Current state:

- Sitemap excludes private/admin routes.
- Unknown app routes render `NotFound`.
- Legacy redirects exist for shop/publishing routes.
- No dry-run catalog audit script exists yet to score relevance, thin pages, demo/template pages, broken URLs, or missing CTAs.

Impact:

- Irrelevant or low-quality catalog content could remain public and dilute SEO/conversion trust.

Mitigation:

- Phase 1 must run before Phase 2 generation.
- Add `KEEP / REWRITE / NOINDEX / QUARANTINE / ARCHIVE / DELETE` recommendations in dry-run reports.

### 3. Automation cost budgets are not centralized yet

Current state:

- Some scripts have dry-run defaults and chunk/progress caches.
- Growth OS has daily budget config.
- There is no central budget ledger for LLM, audio, image, OCR, or provider spend.

Impact:

- Repeated generation jobs could accidentally exceed cost targets.

Mitigation:

- Add cost-control models before generation phases:
  - `max_daily_llm_budget`
  - `max_book_generation_budget`
  - `max_audio_generation_budget`
  - `max_image_generation_budget`
  - source-hash + prompt-version cache keys

### 4. Publishing workflow state machine is missing

Current state:

- Books have `is_published`.
- Import scripts default to dry-run/draft behavior.
- No formal lifecycle exists from `DISCOVERED` to `PUBLISHED`.

Impact:

- It is hard to prevent a generated artifact from bypassing rights/quality/performance gates.

Mitigation:

- Phase 8 must add explicit workflow states and enforce publish gates server-side.

### 5. Demand scoring is not present

Current state:

- Internal analytics events exist.
- Reader sessions and payments exist.
- No demand score model or prioritization queue exists.

Impact:

- Content generation could spend credits on low-return books/topics.

Mitigation:

- Phase 3 should use internal metrics first, then cached public/manual popularity signals.

## High Risks

### Rights complexity for translations, illustrations, annotations, and modern editions

Risk:

- A public-domain original can have non-public-domain translations, illustrations, notes, or scans.

Mitigation:

- Treat author, translator, illustrator, editor, source, and edition as separate rights objects.
- Block if any required rights object is missing or tier C.

### Bengali and historical OCR quality

Risk:

- Bengali OCR can produce silent quality failures that damage reader trust and audiobook scripts.

Mitigation:

- OCR confidence threshold.
- Manual cleanup queue.
- No public publishing below threshold.
- Keep raw source, cleaned text, and source hash.

### Audiobook QA still script-centric

Risk:

- Audio polish reports exist, but QA results are not yet normalized into backend records/admin dashboards.

Mitigation:

- Phase 7 should create persistent audio QA records linked to book slug, source hash, provider, voice, WER, loudness, clipping, silence, and score.

### Generated study material could hallucinate

Risk:

- Summaries, historical context, teacher notes, and quizzes can contain unsupported facts.

Mitigation:

- Mark interpretive content explicitly.
- Require citations/source links for factual study notes.
- Cache generated artifacts and QA by source hash and prompt version.
- Block publication if citation coverage or factuality score is below threshold.

### Admin dashboard complexity

Risk:

- Adding rights, demand, ingestion, edition, QA, audio, and publishing workflow screens inside one large `Admin.jsx` file could become hard to maintain.

Mitigation:

- Split future Automation System UI into `frontend/src/components/Admin/automation/*` or `frontend/src/pages/AdminAutomation/*` before Phase 2/3 UI grows.

## Operational Risks

### Dirty working tree

Current state:

- The repository has multiple modified and untracked files from prior SEO/audio/Growth OS tasks.

Impact:

- Phase 1 changes must avoid reverting unrelated work and should be committed as a focused PR.

Mitigation:

- Review `git status --short` before each phase.
- Stage only phase-specific files.

### Production API dependence during sitemap build

Current state:

- `frontend/scripts/generate-seo-assets.mjs` fetches public API endpoints during build and falls back to empty lists on fetch failure.

Impact:

- A transient API issue can produce a reduced sitemap if not caught.

Mitigation:

- Add sitemap regression checks and cached build inputs in Phase 1 or Phase 10.

### Automation jobs may run longer than CI/serverless limits

Risk:

- OCR, TTS, edition generation, and large catalog audits can be long-running.

Mitigation:

- Use resumable batch jobs, progress files, small chunks, and report-first dry-runs.
- Avoid running heavy jobs inside frontend build or request handlers.

### Multi-region reader base versus single backend region

Risk:

- India, USA, and UK users may experience backend latency if most reads pass through one Railway region.

Mitigation:

- Keep media on CDN/B2/Cloudinary.
- Keep public catalog cache warm.
- Avoid Redis for media binaries.
- Consider future CDN/API edge strategy for read-heavy public metadata.

## Security And Compliance Risks

### Public/private data separation

Risk:

- Source URLs, rights evidence, and import logs should be internal/admin-only.

Mitigation:

- Keep source traceability in admin-only collections.
- Never expose raw source evidence in public metadata unless legally required.

### Payment/refund automation

Risk:

- Any automated refund, discount, coupon, or price change can create financial liability.

Mitigation:

- Keep finance guardrails blocking all pricing/refund/coupon actions until explicit admin approval.

### Outreach/spam risk

Risk:

- Email/WhatsApp automation can damage deliverability and brand trust.

Mitigation:

- Require opt-in status, frequency caps, unsubscribe handling, and admin review before any send.

## Immediate Blockers Before Phase 1

None that prevent a dry-run catalog audit implementation.

## Immediate Blockers Before Phase 2+

- Need structured rights model.
- Need clear policy thresholds for India/global publication.
- Need source evidence storage schema.
- Need admin-only rights visibility.

## Immediate Blockers Before Auto-Publishing

- Rights gate.
- Demand gate.
- Content QA gate.
- Audio QA gate.
- Performance gate.
- Cost budget gate.
- Rollback workflow.
- Admin kill switch.
