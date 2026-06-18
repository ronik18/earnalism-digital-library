# Guardrails

Phase 10 guardrails evaluate automated actions before they can be queued for future execution. All checks are deterministic and dry-run only in this phase.

## Blocking Guardrails

The observability engine emits `guardrail_block` logs for:

- `rights_blocked`
- `source_missing`
- `hallucination_risk`
- `unsafe_child_facing_content`
- `copyrighted_image_risk`
- `low_quality_audio`
- `budget_exceeded`
- `kill_switch`

## Rights Blocked

Actions are blocked when rights metadata is Tier C, has a `blocked_reason`, or lacks approved/verified rights status.

## Source Missing

Source-dependent actions are blocked when `source_url` or `source_hash` is missing.

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

## Kill Switch

When `kill_switch_active=true`, every action is blocked and a critical incident is opened. The kill switch does not require external services or credentials.
