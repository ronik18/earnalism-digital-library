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

The admin panel prefers backend/report-style workflow data from `publishing_workflow_report` or `workflow_report` when present. If that data is unavailable, it computes a read-only dry-run estimate using the same documented gate categories. The panel does not call mutation APIs.

## Publishing Rules

Normal publication readiness requires:

- `rights_tier=A`
- `verification_status=APPROVED`
- empty `blocked_reason`
- `action_status=READY_FOR_GENERATION`
- `ingestion_status=INGESTED` or `CLEANED`
- `edition_generation_status=READY_FOR_REVIEW`, `PARTIAL_DRY_RUN`, or `QA_PASSED`
- `visual_status=READY_FOR_REVIEW`, `PARTIAL_DRY_RUN`, or `QA_PASSED`
- `audio_status=DRY_RUN_READY`, `READY_FOR_REVIEW`, `QA_PASSED`, or `AUDIO_NOT_REQUIRED`
- `qa_status=QA_PASSED`
- cost used at or below the configured budget

Blocking behavior:

- missing or unknown rights returns `RIGHTS_PENDING`
- Tier B returns `publish_readiness=REGION_GATED_REVIEW`, not normal `READY`
- Tier C returns `QUARANTINED` with `BLOCKED_RIGHTS`
- missing demand status returns `BLOCKED_PRIORITY_GATE`
- missing ingestion returns `BLOCKED_INGESTION`
- missing or failed edition status returns `BLOCKED_EDITION_GATE`
- missing or failed visual status returns `BLOCKED_VISUAL_GATE`
- missing or failed audio status returns `BLOCKED_AUDIO_GATE`
- missing QA pass returns `QA_PENDING`
- budget overrun returns `BLOCKED_COST`

`AUDIO_NOT_REQUIRED` is available for text-only editions where a narrated preview is intentionally out of scope for the current release.

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
