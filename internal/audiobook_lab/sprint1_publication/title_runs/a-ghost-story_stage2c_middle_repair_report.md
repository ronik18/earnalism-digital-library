# A Ghost Story Stage 2C Middle Repair Report

Generated: `2026-07-12`

Owner decision: `AUTHORIZE_STAGE_2C_A_GHOST_STORY_AUDIO_REPAIR_AND_PUBLICATION_IF_QUALITY_10_TARGET_PASSES`

## Decision

- Public reader: `YES`
- Public audiobook: `NO`
- Publication performed: `NO`
- Final state: `AUDIO_HIDDEN_ALTERNATE_PROVIDER_REPAIR_REQUIRED`
- Release reason: OpenAI audio reached strong source fidelity but did not meet the listening-quality gate.

## Diagnosis And Repair

1. The original `352.787s` middle window began inside a word. Sentence-aligned revalidation proved the audio still had a real weak section: minimum `6.8`, confidence `0.85`, with robotic texture and mechanical cadence.
2. Three bounded OpenAI selector arms were tested. `verse` with `mystery_suspense_narrator` was best at `9.5`, confidence `0.95`, with no fatal flags. `verse/classic_literary` scored `9.4`; `coral/mystery_suspense` scored `8.3`.
3. Full candidate v1 passed ASR at `9.7719`, but chunk resets occurred inside sentences and listening QA fell to `8.3` in the weak section.
4. The general boundary verifier was repaired for exact compound-word equivalence such as `bath-tub` versus `bathtub`. A genuinely missing ending still fails.
5. Full candidate v2 used sentence-terminal chunks. It exposed a real 50-token provider omission and scored `9.6879` ASR/source, so it was rejected before listening QA.
6. Full candidate v3 reduced requests to sentence-safe chunks of at most 1,600 characters. It passed ASR/source at `9.928`, with first and last boundaries passing and no missing source span.
7. Candidate v3 still failed listening QA. Five judged samples scored `9.4`; the sample at `525.624s` scored `8.3`, confidence `0.90`, with list-reading rhythm. The OpenAI lane therefore plateaued below the repo's universal `9.7` release rubric.

## Tooling Repairs

- Sentence-safe OpenAI TTS chunking now ignores source line-wrap blank lines.
- TTS chunk size is configurable with `EARNALISM_OPENAI_TTS_MAX_CHARS_PER_CHUNK`.
- Whisper results are checkpointed by audio hash, source hash, slug, model, and language before downstream verification.
- Completed ASR checkpoints skip repeat transcription.
- ASR listening samples are distributed across the full chunk sequence and include the actual ending.
- Paid wrappers validate caps before provider construction and restore `paid_tts.lock` byte-for-byte.

## Budget

- Authorized total: `$175.00`
- Estimated Stage 2B plus Stage 2C provider work: `$2.3295`
- Actual provider billing: `NOT_REPORTED`
- Estimated remaining budget: `$172.6705`
- No upload, publication, deployment, or public release-state mutation occurred.

## Evidence

- Final private candidate: `/tmp/earnalism-a-ghost-stage2c-full-tts-v3/a-ghost-story_openai_tts_final.mp3`
- Final audio hash: `8524448cb77b63fa125e443e1e36469c3e887b058e77b5e4ae43dc7466612905`
- Final ASR checkpoint: `/tmp/earnalism-a-ghost-stage2c-full-tts-v3/asr_provider_checkpoint.json`
- Final listening report: `/tmp/earnalism-a-ghost-stage2c-full-tts-v3/listening_quality_report.json`
- Runtime summary: `internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_stage2c_full_qa_runtime.json`

## Next Action

Reauthenticate Google Application Default Credentials, then run one bounded alternate-provider representative audition. Do not rerun OpenAI variants or publish the current private candidates.

```sh
gcloud auth application-default login
```
