# Observability

Phase 10 adds deterministic observability for Earnalism automation. It creates structured audit trails for planned automated actions without publishing content, calling providers, writing databases, or changing production behavior.

## Structured Logs

Every evaluated action emits at least one structured log event with:

- `event_id`
- `timestamp`
- `category`
- `phase`
- `action`
- `status`
- `severity`
- `slug`
- `guardrail_type`
- `message`
- `metadata`
- `dry_run`

Supported categories:

- `rights_check`
- `demand_scoring`
- `ingestion`
- `generation`
- `qa`
- `audio_generation`
- `publishing`
- `failure`
- `guardrail_block`

## Reports

Run:

```bash
npm run observability:audit
```

Outputs:

- `output/observability/observability_guardrails_report.json`
- `output/observability/structured_logs.json`
- `output/observability/structured_logs.csv`
- `output/observability/incident_report.csv`
- `output/observability/observability_guardrails_report.md`

The JSON report includes health checks, blocked action count, guardrail type counts, incidents, and dry-run status.

## Phase 1-9 Coverage

The dry-run observability layer maps these automation phases into structured log categories:

- Phase 1 public content governance: `publishing`
- Phase 2 rights verification: `rights_check`
- Phase 3 demand scoring: `demand_scoring`
- Phase 4 source ingestion: `ingestion`
- Phase 5 edition generation: `generation`
- Phase 6 visual generation: `generation`
- Phase 7 audio generation: `audio_generation`
- Phase 8 publishing workflow: `publishing`
- Phase 9 daily growth loop: `demand_scoring`

## Health Checks

The dry-run report includes health checks for:

- API health
- queue health
- storage health
- publishing health

Statuses are `OK`, `DEGRADED`, or `DOWN`. Non-OK health checks generate structured logs and high-severity incidents when appropriate.

## Emergency Stop

Two dry-run stops are supported:

- `kill_switch_active=true`
- `feature_flags: { "automation_enabled": false }`

Both stop all actions, create guardrail logs, and open critical incidents. No external alert delivery is configured in Phase 10.

## Scope

This phase is local and deterministic. It does not install hosted monitoring, cron jobs, alert delivery, provider integrations, or production mutation hooks.
