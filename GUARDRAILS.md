# Guardrails

Phase 10 guardrails evaluate automated actions before they can be queued for future execution. All checks are deterministic and dry-run only in this phase.

## Blocking Guardrails

The observability engine emits `guardrail_block` logs for:

- `rights_blocked`
- `region_gated`
- `source_missing`
- `traceability_missing`
- `hallucination_risk`
- `unsafe_child_facing_content`
- `copyrighted_image_risk`
- `low_quality_audio`
- `budget_exceeded`
- `kill_switch`
- `feature_flag_disabled`

## Rights Blocked

Actions are blocked when rights metadata is Tier C, has a `blocked_reason`, lacks a known rights tier, or lacks approved/verified rights status.

Tier B is never treated as normal global automation. Tier B requires:

- `publication_region` set to `IN`, `india`, `india-only`, `in-only`, or `region-gated-india`
- `region_gate_acknowledged=true`

When those requirements are met, Tier B is allowed only as region-gated dry-run work and emits a non-blocking `region_gated` structured log.

## Source Missing

Source-dependent actions are blocked when any source identity field is missing:

- `source_url`
- `source_name`
- `source_license`

They are also blocked when any Phase 4 traceability hash is missing:

- `source_hash`
- `content_hash`
- `provenance_hash`

## Hallucination Risk

Actions with high hallucination risk are blocked for editorial review. Phase 10 does not call LLMs or attempt automated correction.

## Child-Facing Safety

Child-facing actions are blocked when unsafe child-facing content is flagged.

## Image Risk

Actions are blocked when copyrighted image risk or external image dependency risk is present.

## Audio Quality

Audio actions are blocked when quality score is below `9.0` or audio QA has failed.

## Budget Exceeded

Actions are blocked when estimated cost exceeds remaining budget or would exceed the configured budget limit.
Invalid cost metadata also blocks action:

- negative `estimated_cost`
- negative `budget_remaining`
- negative `budget_used`
- negative `budget_limit`
- positive `estimated_cost` without either `budget_remaining` or `budget_limit`

## Kill Switch

When `kill_switch_active=true`, every action is blocked and a critical incident is opened. The kill switch does not require external services or credentials.

## Feature Flag Stop

When `feature_flags.automation_enabled=false`, every action is blocked with `feature_flag_disabled`. This is local report metadata only and does not mutate production state.
