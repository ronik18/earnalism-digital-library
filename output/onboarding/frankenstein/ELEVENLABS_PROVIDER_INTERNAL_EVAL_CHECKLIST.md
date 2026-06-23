# ElevenLabs Provider Internal-Eval Checklist

ElevenLabs cannot be promoted to `ELIGIBLE_INTERNAL_EVAL_ONLY` unless every checklist item is completed and reviewed.

## Current Status

- Provider ID: `elevenlabs`
- Internal-eval status: `HOLD_PROVIDER_REVIEW`
- Production approval: `PRODUCTION_BLOCKED`
- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`

## Required Before Promotion

- [ ] Paid provider plan evidence is documented.
- [ ] Official commercial-use evidence is owner/legal reviewed.
- [ ] Standalone audio distribution permission is owner/legal reviewed.
- [ ] Beta features remain excluded.
- [ ] Exact selected voice ID and display name are recorded.
- [ ] Selected voice license and voice-rights evidence are documented.
- [ ] Attribution requirements are understood and recorded.
- [ ] Data/privacy and retention notes are reviewed.
- [ ] Owner approval is recorded with reviewer name and date.
- [ ] Legal/internal review is complete and not blocked.
- [ ] The decision is explicitly recorded as HOLD, ELIGIBLE_INTERNAL_EVAL_ONLY, or BLOCKED.

## Non-Negotiable Blocks

- If beta features are required, keep `BLOCKED`.
- If selected voice evidence is missing, keep `HOLD_PROVIDER_REVIEW`.
- If commercial standalone output evidence is missing, keep `HOLD_PROVIDER_REVIEW`.
- If owner approval is missing, keep `HOLD_PROVIDER_REVIEW`.
- If legal/internal review is blocked, set `BLOCKED`.
- Do not mark production approved in this workflow.
- Do not generate audio in this workflow.
