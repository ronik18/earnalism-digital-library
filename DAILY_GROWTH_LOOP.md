# Phase 9 Daily Growth Automation Loop

Phase 9 adds a deterministic daily growth automation loop. It reads local metrics, updates demand priorities, checks rights and publishing workflow readiness, queues dry-run candidate metadata, prepares growth draft previews, and writes a daily report.

This phase does not publish content, call providers, send email, post social content, or expose public pages.

## Daily Inputs

The loop accepts:

- yesterday growth metrics
- book/topic records
- optional per-book metrics
- budget caps
- `dry_run`, which must not be `false`
- `emergency_pause`, which blocks all task and draft preparation when `true`

Growth metrics:

- paid readers
- reading starts
- reading completions
- preview listens
- referrals
- conversion rate
- school/institution leads

## Budgets

Budget fields:

- `max_daily_llm_budget`
- `max_daily_audio_budget`
- `max_books_per_day`
- `max_publish_actions_per_day`

`max_publish_actions_per_day` defaults to `0`, and Phase 9 never schedules public publishing.
If a nonzero publish action cap is supplied, the report records a blocker because public publishing remains disabled in this phase.

## Daily Decisions

The dry-run job:

- ranks demand using the deterministic Phase 3 scorer
- identifies top books/topics within `max_books_per_day`
- checks Phase 8 publishing workflow readiness
- queues growth candidate metadata only
- prepares SEO/social/email draft previews
- prepares reading challenge draft previews
- blocks items when rights/workflow gates fail
- blocks tasks when budget caps are reached

Candidate task metadata types:

- `source_ingestion_candidate`
- `edition_generation_candidate`
- `visual_design_candidate`
- `audio_preview_plan`
- `publishing_workflow_candidate`
- `seo_social_email_drafts`
- `reading_challenge_draft`

These are not execution jobs. They are dry-run planning rows for review and later phases.

## Upstream Gates

No candidate tasks or drafts are prepared unless Phase 8 publish readiness is `READY` or already `PUBLISHED`.
That readiness includes checks from earlier phases:

- Phase 2 rights approval
- Phase 3 `READY_FOR_GENERATION` demand status
- Phase 4 `INGESTED` or `CLEANED` ingestion status
- Phase 5 acceptable edition generation status
- Phase 6 acceptable visual design status
- Phase 7 acceptable audio status, or `AUDIO_NOT_REQUIRED`
- QA pass
- cost budget compliance

## Reports

Run:

```bash
npm run growth:daily
```

Outputs:

- `output/daily_growth/daily_growth_report.json`
- `output/daily_growth/daily_growth_report.csv`
- `output/daily_growth/daily_growth_report.md`

## Safety

- dry-run only
- core loop blocks `dry_run=false`
- emergency pause blocks all tasks and drafts
- no provider credentials required
- no LLM/TTS/STT/image/OCR calls
- no email or social posting
- no public publishing
- no database writes
- reports are local files only
- SEO/social/email drafts include previews only, no recipients, send times, or provider identifiers

## Limitations

- Scheduling is represented by the CLI command; no hosted cron is added in Phase 9.
- Drafts are previews, not production campaigns.
- Later phases must explicitly add audited mutation endpoints before any live publishing or outbound marketing action.
