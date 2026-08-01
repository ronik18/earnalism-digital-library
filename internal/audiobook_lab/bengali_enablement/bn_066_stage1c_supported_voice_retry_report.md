# bn-066 Stage 1C Supported-Voice Retry Report

Generated: 2026-07-10T06:31:44Z

## Strategy Summary

Stage 1C was authorized to retry `bn-066` with a supported Sarvam voice under a hard `5 USD` cap. The retry stopped before lock acquisition and before any provider call because the live shell did not expose the required paid approval and budget environment gates.

## Paid Gate Status

- `SARVAM_API_KEY`: present, value not printed
- `MAX_TTS_BUDGET_USD=5`: missing
- `EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS=true`: missing
- `EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true`: missing
- `EARNALISM_STOP_ON_BUDGET_EXCEEDED=true`: missing
- `EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD=5`: missing
- `EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE=2`: missing

## Voice Decision

- Preferred voice: `ratan`
- Stage 1B detected voice: `pooja`
- Stage 1B did not list `ratan`.
- The bakeoff script matches voice filters as `ratan` or `sarvam/ratan`, not `sarvam:ratan`.
- Stage 1C owner scope permits falling back to `pooja` if `ratan` is unavailable.
- No fresh provider capability call was made in Stage 1C because paid gates were missing.

## Lock Status

- Before: `paid_tts.lock` active with `current_holder: none` and `allowed_next_holders: []`
- During: no Stage 1C holder acquired
- After: unchanged, active blocking state

## Result

`AUDITION_BLOCKED_MISSING_PAID_ENV_GATES`

No audio was generated. No ASR, listening QA, first/last word check, upload, publication, release-gate mutation, or public Listen approval occurred.

## Next Action

Set the required paid env gates in the shell, then run one supported-voice retry. Current evidence supports using `pooja` as the fallback unless a fresh capability probe lists `ratan`.

Do not run full-book TTS until a representative audition passes and the owner separately approves full-book generation.
