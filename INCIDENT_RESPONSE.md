# Incident Response

Phase 10 creates local dry-run incident records from high and critical severity observability events.

## Incident Fields

Each incident includes:

- `incident_id`
- `severity`
- `owner`
- `status`
- `source_event_id`
- `summary`
- `rollback_instruction`
- `kill_switch_active`
- `dry_run`

## Severity Levels

- `INFO`: audit trail only
- `LOW`: minor operational note
- `MEDIUM`: review required
- `HIGH`: action blocked and incident opened
- `CRITICAL`: kill switch, unsafe rights, or non-dry-run attempt

## Owners

Owners are deterministic labels:

- `rights`
- `growth`
- `audio`
- `platform`

## Rollback Instructions

Rollback instructions are generated in the incident report. Examples:

- keep content unpublished and rerun rights verification
- reduce the daily queue or budget before retry
- keep automation paused until the kill switch is cleared
- keep affected subsystem paused until health checks recover

## Kill Switch

The kill switch is represented by `kill_switch_active=true`. In Phase 10 it blocks all actions, opens incidents, and writes local reports only.

## Output

Run:

```bash
npm run observability:audit
```

Review:

- `output/observability/incident_report.csv`
- `output/observability/observability_guardrails_report.md`
