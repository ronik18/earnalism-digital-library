# Phase 9 Daily Growth Automation Loop

Phase 9 adds a deterministic daily growth automation loop. It reads local metrics, updates demand priorities, checks rights and publishing workflow readiness, queues dry-run tasks, prepares growth drafts, and writes a daily report.

This phase does not publish content, call providers, send email, post social content, or expose public pages.

## Daily Inputs

The loop accepts:

- yesterday growth metrics
- book/topic records
- optional per-book metrics
- budget caps

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

## Daily Decisions

The dry-run job:

- ranks demand using the deterministic Phase 3 scorer
- identifies top books/topics within `max_books_per_day`
- checks Phase 8 publishing workflow readiness
- queues ingestion/generation task metadata only
- prepares SEO/social/email draft previews
- prepares reading challenge draft previews
- blocks items when rights/workflow gates fail
- blocks tasks when budget caps are reached

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
- no provider credentials required
- no LLM/TTS/STT/image/OCR calls
- no email or social posting
- no public publishing
- no database writes
- reports are local files only

## Limitations

- Scheduling is represented by the CLI command; no hosted cron is added in Phase 9.
- Drafts are previews, not production campaigns.
- Later phases must explicitly add audited mutation endpoints before any live publishing or outbound marketing action.
