# Kokoro af_heart Evidence Collection Checklist

af_heart cannot be promoted to `ELIGIBLE_INTERNAL_EVAL_ONLY` unless every checklist item is completed and reviewed.

## Current Status

- Voice ID: `af_heart`
- Selected voice status: `HOLD_VOICE_RIGHTS`
- Kokoro model status: `HOLD_VOICE_RIGHTS`
- Production approval: `PRODUCTION_BLOCKED`
- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Eligible internal-eval candidates: `0`

## Required Before Promotion

- [ ] Voice/speaker provenance is documented.
- [ ] Consent evidence or synthetic/non-human status is documented.
- [ ] Voice/license evidence allows local internal evaluation.
- [ ] Attribution requirements are understood and recorded.
- [ ] Restrictions are understood and recorded.
- [ ] Real-person voice clone risk is resolved and not high.
- [ ] Owner approval is recorded with reviewer name and date.
- [ ] Legal/internal review is complete and not blocked.
- [ ] The decision is explicitly recorded as HOLD, ELIGIBLE_INTERNAL_EVAL_ONLY, or BLOCKED.
- [ ] The next action is recorded.

## Non-Negotiable Blocks

- If speaker provenance is missing, keep `HOLD_VOICE_RIGHTS`.
- If consent or synthetic/non-human status is missing, keep `HOLD_VOICE_RIGHTS`.
- If commercial internal-eval permission is unclear, keep `HOLD_VOICE_RIGHTS`.
- If real-person voice clone risk is unresolved or high, keep `HOLD_VOICE_RIGHTS` or `BLOCKED`.
- If owner approval is missing, keep `HOLD_VOICE_RIGHTS`.
- If legal/internal review is blocked, set `BLOCKED`.
- Do not mark production approved in this workflow.
- Do not generate audio in this workflow.

## Output Safety

- No audio files may be written to `frontend/public` or `frontend/build`.
- No public listening CTA may appear publicly.
- No public audio JSON-LD metadata may be emitted.
- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.
