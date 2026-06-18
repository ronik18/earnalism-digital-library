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
- `output/observability/structured_logs.csv`
- `output/observability/incident_report.csv`
- `output/observability/observability_guardrails_report.md`

## Health Checks

The dry-run report includes health checks for:

- API health
- queue health
- storage health
- publishing health

Statuses are `OK`, `DEGRADED`, or `DOWN`. Non-OK health checks generate structured logs and high-severity incidents when appropriate.

## Scope

This phase is local and deterministic. It does not install hosted monitoring, cron jobs, alert delivery, provider integrations, or production mutation hooks.
