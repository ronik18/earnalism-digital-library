# Earnalism Automation System - Phased Implementation Plan

Generated: 2026-06-17

## Principles

- Dry-run first for every phase.
- No public publishing without deterministic rights approval.
- No generated study material without QA.
- No audiobook publishing without audio QA.
- No automated spend without budget checks.
- Prefer deterministic code, cached metadata, and internal analytics before LLM calls.
- Store raw inputs, source hashes, prompt versions, model/provider versions, and generated artifacts.
- One focused PR per phase.

## Phase 0 - Inspection And Documentation

Status: completed in this documentation pass.

Deliverables:

- `SYSTEM_INSPECTION_REPORT.md`
- `CURRENT_ARCHITECTURE.md`
- `RISKS_AND_BLOCKERS.md`
- `PHASED_IMPLEMENTATION_PLAN.md`

Tests:

- No production behavior changed.
- Optional validation: markdown-only diff review.

Rollback:

- Remove the four Phase 0 markdown files.

## Phase 1 - Public Catalog Cleanup And Content Governance

Goal:

Create a dry-run catalog audit system that scans public pages, API records, media references, sitemap entries, and route behavior without changing public content by default.

Implementation:

1. Add `scripts/audit-public-content.mjs`.
2. Read public API endpoints:
   - `/api/books`
   - `/api/categories`
   - `/api/blog`
   - homepage/library/book/journal URLs from sitemap
3. Score each public entity:
   - relevance score
   - thin-content score
   - CTA presence
   - duplicate/generic fallback risk
   - media/audiobook linkage
   - rights/source metadata presence if admin data is available
4. Produce recommendations:
   - `KEEP`
   - `REWRITE`
   - `NOINDEX`
   - `QUARANTINE`
   - `ARCHIVE`
   - `DELETE`
5. Generate:
   - `output/catalog_audit/catalog_audit_report.json`
   - `output/catalog_audit/catalog_audit_report.csv`
   - `output/catalog_audit/catalog_cleanup_report.md`
6. Add route/sitemap regression tests:
   - irrelevant demo URLs do not return `200`
   - sitemap excludes quarantined/removed content
   - unknown routes render/return 404
   - approved reader/book pages remain live
   - audit script emits JSON and CSV

Cost controls:

- No LLM calls.
- Public requests only unless admin token is explicitly provided.
- Cache fetched URLs under `output/catalog_audit/cache`.

Rollback:

- Remove script/tests/output.
- No production data changes in dry-run.

Production readiness target after Phase 1:

- 7.5/10 for governance readiness.

## Phase 2 - Rights And Public-Domain Verification Engine

Goal:

Build deterministic rights verification before any public-domain automation.

Implementation:

1. Add rights metadata models:
   - work
   - author
   - translator
   - illustrator
   - editor
   - source
   - edition
   - country_of_origin
   - first_publication_year
   - author_death_year
   - rights_basis
   - rights_tier
   - publication_region
   - license_url
   - source_url
   - verification_status
   - verification_notes
   - blocked_reason
2. Add deterministic `rights_verifier` service.
3. Add admin-only rights endpoints.
4. Add rights quarantine queue.
5. Add rights import/export.
6. Add rights audit logs.
7. Add tests:
   - pre-threshold author death passes India rule
   - unknown death year blocks
   - modern translation blocks
   - missing source blocks
   - Tier B requires regional restriction
   - Tier C blocks publishing

Cost controls:

- No LLM rights judgment.
- Deterministic rules only.

Rollback:

- Feature flag rights enforcement initially report-only.
- Disable rights enforcement flag if rollout causes false positives.

Production readiness target after Phase 2:

- 8.2/10 for legal safety.

## Phase 3 - Demand And Popularity Scoring

Goal:

Prioritize content production by likely reader value, SEO potential, school usefulness, audiobook potential, and conversion impact.

Implementation:

1. Add demand score model/service.
2. Use internal analytics first:
   - page views
   - reading starts
   - completions
   - audio preview listens
   - referrals
   - payments
3. Add optional cached/manual external popularity imports.
4. Add demand dashboard.
5. Add priority queue for approved titles.
6. Add tests for score composition and penalty behavior.

Cost controls:

- No aggressive scraping.
- Cache all external metadata.
- Manual CSV imports allowed.

Rollback:

- Demand scores are advisory until later phases.

Production readiness target after Phase 3:

- 8.5/10 for content prioritization.

## Phase 4 - Public-Domain Content Ingestion Engine

Goal:

Build source-traceable ingestion for public-domain works.

Implementation:

1. Add connectors:
   - Project Gutenberg
   - Wikisource
   - Standard Ebooks if useful
   - manual upload
   - scanned PDF upload
2. Store:
   - raw source
   - source URL/license
   - source hash
   - cleaned text
   - chapter segmentation
   - language
   - metadata
   - ingestion log
3. Add OCR hooks:
   - Tesseract
   - Kraken/eScriptorium integration placeholders
4. Add OCR confidence and cleanup queue.
5. Add tests for duplicate source, missing license, source hash, OCR block, chapter segmentation.

Cost controls:

- Do not regenerate cleaned text if source hash is unchanged.
- OCR dry-run by default.

Rollback:

- Keep ingestion artifacts internal-only.

Production readiness target after Phase 4:

- 8.7/10 for source traceability.

## Phase 5 - Earnalism Edition Generator

Goal:

Generate Earnalism editions only for rights-approved, demand-prioritized works.

Implementation:

1. Add generation artifact model keyed by:
   - work id
   - source hash
   - prompt version
   - model version
   - artifact type
2. Generate:
   - clean reading edition
   - summaries
   - character map
   - historical context
   - themes
   - glossary
   - notes
   - timeline
   - reading difficulty
   - reading plan
   - quiz
   - teacher/parent notes
   - why-it-matters
   - social/email/SEO drafts
   - audiobook narration script
3. Add quality evaluators.
4. Add generated artifact storage.
5. Add tests for cache reuse, gate failures, and artifact completeness.

Cost controls:

- Generate top-priority approved works only.
- Section-level caching.
- Max book generation budget.

Rollback:

- Generated artifacts remain drafts until publication workflow approves them.

Production readiness target after Phase 5:

- 8.8/10 for edition generation.

## Phase 6 - Visual Explainer And Design Engine

Goal:

Generate deterministic, lightweight study visuals and publication formats.

Implementation:

1. Build templates using Mermaid, SVG, HTML/CSS, Pandoc/EPUB/PDF tooling.
2. Generate diagrams, timelines, flow maps, vocabulary cards, worksheets, EPUB/PDF, and social cards.
3. Add visual QA and performance checks.

Cost controls:

- No AI images by default.
- Prefer deterministic diagrams and typography.

Rollback:

- Visuals remain drafts until QA and publish workflow pass.

Production readiness target after Phase 6:

- 8.9/10 for study asset production.

## Phase 7 - Audiobook And Voice Pipeline

Goal:

Normalize audiobook generation/QA into the Automation System.

Implementation:

1. Unify current Bengali/English polish scripts under persistent job records.
2. Add Hindi support hooks.
3. Add provider abstraction:
   - OpenAI TTS
   - AI4Bharat/Indic hook
   - Piper/local hook
   - manual upload fallback
4. Add FFmpeg mastering and preview generation.
5. Add audio QA:
   - transcript comparison
   - WER
   - missing paragraphs
   - repeated lines
   - clipping
   - silence
   - loudness
   - file size
   - pronunciation risk
6. Add tests and admin QA views.

Cost controls:

- Chunk cache.
- Resume support.
- Max audio generation budget.

Rollback:

- Never delete previous production audio until new audio is verified and cleanup report is reviewed.

Production readiness target after Phase 7:

- 9.0/10 for audio safety.

## Phase 8 - Publishing Workflow And Admin Dashboard

Goal:

Add explicit states and gated publishing controls.

States:

- `DISCOVERED`
- `RIGHTS_PENDING`
- `RIGHTS_APPROVED`
- `DEMAND_SCORED`
- `INGESTED`
- `CLEANED`
- `EDITION_GENERATED`
- `VISUALS_GENERATED`
- `AUDIO_PREVIEW_GENERATED`
- `QA_PENDING`
- `QA_PASSED`
- `READY_FOR_PUBLICATION`
- `PUBLISHED`
- `PAUSED`
- `QUARANTINED`
- `ARCHIVED`

Implementation:

1. Add workflow model and admin board.
2. Add publish/pause/rollback buttons.
3. Enforce server-side publish gates.
4. Update sitemap/internal search/recommendations only after publish.
5. Add tests for blocked publish paths and rollback.

Cost controls:

- Publishing does not call generation providers.

Rollback:

- State transition from `PUBLISHED` to `PAUSED`/`ARCHIVED` plus sitemap invalidation.

Production readiness target after Phase 8:

- 9.2/10 for publication safety.

## Phase 9 - Growth Automation Loop

Goal:

Extend Growth OS daily loop to orchestrate rights, demand, ingestion, generation, QA, and draft growth assets.

Implementation:

1. Read yesterday's metrics.
2. Update demand scores.
3. Select opportunities.
4. Run rights checks.
5. Run ingestion/generation only in dry-run unless enabled.
6. Create reading challenges, landing page drafts, social/email drafts.
7. Produce daily report.

Cost controls:

- Central budget checks before any provider call.
- Dry-run default.

Rollback:

- Emergency pause feature flag.
- Disable scheduled job without changing code.

Production readiness target after Phase 9:

- 9.4/10 for safe automation.

## Phase 10 - Observability, Guardrails, Reliability

Goal:

Make automation observable and recoverable.

Implementation:

1. Structured job logs.
2. Guardrail logs.
3. Tool-call logs.
4. Error monitoring hook.
5. Retry policy.
6. Dead-letter queue.
7. Cost dashboard.
8. Quality dashboard.
9. Synthetic tests.
10. Incident response docs.

Cost controls:

- Daily budget burn alerts.
- Provider error backoff.

Rollback:

- Disable automation job workers and keep public app running.

Production readiness target after Phase 10:

- 9.7/10 for reliability.

## Phase 11 - First Production Batch In Dry-Run Only

Goal:

Prepare the first 10 approved products as dry-run artifacts only.

Batch:

1. Anandamath Visual Study Companion
2. Devdas Study Edition
3. Abol Tabol Illustrated Reader
4. Sultana's Dream Feminist Sci-Fi Edition
5. Sherlock Holmes Logic Workbook
6. Dracula Gothic Fiction Visual Guide
7. Frankenstein Science and Ethics Guide
8. Tagore Short Stories for Young Readers
9. Calculus Made Easy Visual Guide
10. Chander Pahar Adventure Companion

For each:

- rights report
- source report
- demand score
- reading edition draft
- study guide draft
- visual explainer draft
- quiz draft
- reading challenge draft
- SEO page draft
- audiobook preview script
- optional audio preview if provider configured
- QA report
- estimated cost
- growth rationale

Cost controls:

- Stop after budget threshold.
- No full audiobook generation by default.
- No auto-publish.

Rollback:

- Delete dry-run artifacts only.

Production readiness target after Phase 11:

- 9.9/10 for dry-run automation readiness.

## Recommended Next PR

Implement Phase 1 only:

- `scripts/audit-public-content.mjs`
- catalog audit reports under `output/catalog_audit/`
- route/sitemap tests
- `CATALOG_GOVERNANCE.md`

Do not implement rights verifier, demand scoring, ingestion, generation, or publishing in the Phase 1 PR.
