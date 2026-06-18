# Cost Control

Phase 10 protects automation from uncontrolled spend by evaluating cost before an action can proceed.

## Budget Inputs

Actions may include:

- `estimated_cost`
- `budget_remaining`
- `budget_limit`
- `budget_used`

## Blocking Rules

An action is blocked when:

- `estimated_cost < 0`
- `budget_remaining < 0`
- `budget_used < 0`
- `budget_limit < 0`
- `estimated_cost > 0` without either `budget_remaining` or `budget_limit`
- `estimated_cost > budget_remaining`
- `budget_used + estimated_cost > budget_limit`

The block emits:

- structured log category: `guardrail_block`
- guardrail type: `budget_exceeded`
- severity: `HIGH`
- incident owner: `growth`

## Dry-Run Only

Phase 10 does not call LLM, TTS, STT, OCR, image, paid, or external APIs. It only evaluates supplied metadata and writes local reports.

## Traceability And Rights Context

Cost approval is never enough by itself. Source-dependent actions still require `source_url`, `source_name`, `source_license`, `source_hash`, `content_hash`, and `provenance_hash`. Tier B work must be India-only and explicitly region-gate acknowledged; Tier C and unknown rights stay blocked.

## Operator Workflow

1. Run `npm run observability:audit`.
2. Review `output/observability/structured_logs.csv`.
3. Review `output/observability/structured_logs.json`.
4. Review `output/observability/incident_report.csv`.
5. Reduce queue size, lower estimated work, or approve a future budget change outside Phase 10.
6. Rerun the dry-run audit.

No budget violation should be overridden without explicit human approval in a later phase.
