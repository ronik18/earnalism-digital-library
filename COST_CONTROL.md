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

- `estimated_cost > budget_remaining`
- `budget_used + estimated_cost > budget_limit`

The block emits:

- structured log category: `guardrail_block`
- guardrail type: `budget_exceeded`
- severity: `HIGH`
- incident owner: `growth`

## Dry-Run Only

Phase 10 does not call LLM, TTS, STT, OCR, image, paid, or external APIs. It only evaluates supplied metadata and writes local reports.

## Operator Workflow

1. Run `npm run observability:audit`.
2. Review `output/observability/structured_logs.csv`.
3. Review `output/observability/incident_report.csv`.
4. Reduce queue size, lower estimated work, or approve a future budget change outside Phase 10.
5. Rerun the dry-run audit.

No budget violation should be overridden without explicit human approval in a later phase.
