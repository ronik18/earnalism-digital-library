# bn-066 Stage 2 Full-Book TTS Report

Generated: 2026-07-10T10:54:33Z

## Result

`FULL_BOOK_TTS_PASS_QA_PENDING`

Stage 2 verified the Stage 1F representative audition, used the existing guarded Sarvam full-book TTS hook, and generated a private full-book `bn-066` audiobook. This is not a public release approval. Release-gate readiness remains blocked until bounded ASR/source alignment and full-book listening QA pass.

## Stage 1F Evidence

- Status: `AUDITION_PASS`
- Provider/voice/style: `sarvam` / `pooja` / `literary_warm_pacing`
- Overall score: `9.3`
- Confidence: `0.95`
- Fatal flags: none
- Representative sample exists and is non-empty.

## Pipeline

- Entrypoint: `internal/audiobook_lab/scripts/factory_hooks/tts_hook.py`
- Orchestrator: `internal/audiobook_lab/scripts/release_catalog_factory.py`
- Stage 2 arm: `bn-066` / `sarvam` / `bulbul:v3` / `pooja` / `literary_warm_pacing`

## Budget And Spend

- Authorized Stage 2 cap: `5.00 USD`
- Estimated Sarvam TTS spend: `1.2226 USD`
- Actual provider billing: not reported by provider tools
- Budget remaining by estimate: `3.7774 USD`
- Full-book listening/ASR QA spend this stage: `0.0000 USD`

## Lock

- Before: active with `current_holder: none`, `allowed_next_holders: []`
- During: held by `audiobook_enablement_sprint_2_bn_066`
- After: active with `current_holder: none`, `allowed_next_holders: []`
- Last closeout status: `FULL_BOOK_TTS_PASS`

## Outputs

- Final private MP3: `internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts/bn-066_sarvam_bulbul_v3_pooja_literary_warm_pacing_final.mp3`
- Final MP3 bytes: `343198509`
- Duration seconds: `21449.85075`
- Chunk manifest: `internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts/tts_chunk_manifest.json`
- Chunks: `152`
- Sarvam report: `internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts/sarvam_full_pilot_tts_report.json`
- Cost decision: `internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts/cost_optimization_decision.json`
- Content-integrity recovery: `internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts/tts_content_integrity_recovery.json`
- QA result file: `internal/audiobook_lab/bengali_enablement/bn_066_full_book_qa_results.json`

## Generation Integrity

- TTS hook status: `PASS`
- Fallback TTS used: `false`
- Local audio reused: `false`
- Stale audio reused: `false`
- Cache hits: `0`
- Cache misses: `152`
- Prepared text hash matches Sarvam report: `true`
- Source/page terms in prepared chunk text: `[]`
- First words: `PASS` against chunk manifest
- Last words: `PASS` against chunk manifest

## QA Status

- Manifest/audio existence: `PASS`
- ASR/source alignment: `NOT_RUN_ASR_BUDGET_GATE_MISSING`
- Bengali normalization: `NOT_RUN_ASR_BUDGET_GATE_MISSING`
- Phonetic shadow score: `NOT_RUN_ASR_BUDGET_GATE_MISSING`
- Full-book listening QA: `NOT_RUN_PENDING_BOUNDED_FULL_BOOK_QA_STAGE`

## Release Truth

- Public audio approval: none
- Upload/publication: none
- Public Listen CTA: none
- Public player UI: none
- Static `/audio/...` fallback: none
- Browser speech fallback: none
- Word-level sync claim: none
- AudioObject for non-approved audio: none
- Paid Listen approval: none

## Classification

`bn-066` is `FULL_BOOK_TTS_PASS_QA_PENDING`, not `READY_FOR_RELEASE_GATE_OWNER_APPROVAL`.

## Next Exact Command

Do not run unbounded ASR. Add or authorize a bounded ASR/source-alignment budget gate, then run the existing ASR/sync hook for `bn-066` against the private Stage 2 audio.
