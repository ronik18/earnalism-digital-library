# bn-066 Stage 1D Pooja Representative Audition Report

Generated: 2026-07-10T06:42:30Z

## Strategy Summary

Stage 1D was authorized to run one paid representative audition for `bn-066` with Sarvam `pooja`, `literary_warm_pacing`, max `45` seconds, and a hard `5 USD` cap. The inline paid env gates and `SARVAM_API_KEY` were present. The paid TTS lock was acquired and then restored.

## Result

`AUDITION_BLOCKED_LISTENING_QA_NOT_AVAILABLE`

The bakeoff selected Sarvam `pooja`, prepared the `narrative_opening` passage, and estimated spend at `0.0119 USD`, but it stopped before synthesis because schema-3 listening QA was unavailable.

## Evidence

- Run dir: `internal/audiobook_lab/bengali_enablement/bn_066_stage1d_pooja_audition`
- Bakeoff report: `internal/audiobook_lab/bengali_enablement/bn_066_stage1d_pooja_audition/bengali_tts_provider_bakeoff_report.json`
- Sample text: `internal/audiobook_lab/bengali_enablement/bn_066_stage1d_pooja_audition/bakeoff_passages.json`
- Listening QA probe: `internal/audiobook_lab/bengali_enablement/bn_066_stage1d_pooja_audition/openai_listening_qa_quota_probe.json`

## Budget

- Authorized cap: `5.00 USD`
- Estimated cost: `0.0119 USD`
- Actual spend observed: `0.00 USD`
- New samples generated: `0`
- Output audio path: none

## Voice / Provider

- Provider: `sarvam`
- Voice: `pooja`
- Language code: `bn-IN`
- Style profile: `literary_warm_pacing`
- Sarvam key: present, value not printed

## Lock

- Before: active with `current_holder: none`, `allowed_next_holders: []`
- During: `audiobook_enablement_sprint_1`
- After: active with `current_holder: none`, `allowed_next_holders: []`

## QA

No generated audio exists, so listening QA, ASR/source alignment, first/last word checks, pronunciation notes, and pacing notes could not run.

Classification: `AUDITION_REPAIR_REQUIRED_LISTENING_QA_NOT_AVAILABLE`

## Release Truth

No public audio approval changed. `bn-066` remains audio-hidden and is not ready for full-book TTS owner approval. No Listen CTA, upload, publication, release-gate mutation, static audio fallback, browser speech fallback, word-level sync claim, or non-approved `AudioObject` was introduced.

## Next Action

Enable schema-3 listening QA in the same bounded environment, then rerun exactly one Sarvam/pooja representative sample for `bn-066`.
