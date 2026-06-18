# Phase 8 Admin Publishing Workflow

Phase 8 adds a deterministic dry-run publishing workflow model for Earnalism. It gives admins a clear view of state, blockers, rollback readiness, pause controls, cost status, and dry-run publication drafts without exposing content publicly.

## Workflow States

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

## Admin Dashboard Sections

The admin book cards now show a read-only publishing workflow panel with:

- rights status
- demand score
- ingestion status
- edition generation status
- visual status
- audio status
- QA warnings
- cost used
- publish readiness
- rollback dry-run button
- pause dry-run button

The rollback and pause controls are disabled in Phase 8. They document the intended operator workflow without mutating production state.

## Publishing Rules

Publishing is blocked when:

- rights are missing or not approved
- QA has not passed
- cost budget is exceeded
- Tier B rights are targeted globally
- Tier C rights are present anywhere
- rights `blocked_reason` is still set

## Dry-Run Publish

The dry-run publish model creates private draft descriptions only:

- page draft
- SEO metadata draft
- reading challenge draft

Dry-run publication never exposes content publicly and writes no production state.

## Rollback

Every dry-run publication plan includes rollback steps:

- delete draft page
- delete SEO metadata draft
- delete reading challenge draft
- keep audit log entry for traceability

Blocked dry-runs create no drafts and return a rollback note explaining that no draft artifacts were created.

## CLI

Run:

```bash
npm run publish:workflow
```

Outputs:

- `output/publishing_workflow/publishing_workflow_report.json`
- `output/publishing_workflow/publishing_workflow_report.csv`
- `output/publishing_workflow/publishing_workflow_report.md`

The CLI rejects `--commit`, `--publish`, and `--write`.

## Limitations

- No production book is published.
- No public page is created.
- No backend admin mutation endpoint is added in Phase 8.
- The admin dashboard panel is read-only.
- Live rollback and pause actions require a later explicitly approved phase.
