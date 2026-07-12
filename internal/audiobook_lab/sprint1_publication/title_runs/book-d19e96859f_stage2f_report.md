# book-d19e96859f Stage 2F Report

## Result

- Classification: `PROVIDER_RETRY_REQUIRED`
- Public reader: `Yes`
- Public audiobook: `No`
- Provider calls: `0`
- Spend added: `$0.0000`
- Lock preflight: `PASS`; lock remained active with holder `none` and no allowed next holders

The live shell had `SARVAM_API_KEY` and `OPENAI_API_KEY`, but every required Sprint 1 budget, title cap, Sarvam approval, ASR cap, and listening-QA gate was absent. The run stopped before lock acquisition and before provider calls.

## Diagnosis

The legacy full audio is not reusable: prior ASR/source evidence failed and the historical group-repair chunk files are unavailable. The canonical reader text remains unchanged. The TTS-only sanitation layer now removes both the source frontmatter and the trailing standalone edition year `১২৯৮?`.

Prepared narration evidence:

- Characters: `6,485`
- Words: `998`
- SHA-256: `79b0deba6032c36ab919e4ef4786fc62aa55c9c53c328dfbcf49f03a0f7d05fe`
- Sarvam groups: `5`
- Source terms remaining: none
- Rights/sanitation/cover/reader: `PASS`

The exact title-specific representative arm is reusable:

- Provider/model: `Sarvam / bulbul:v3`
- Voice/style: `pooja / dialogue_human_touch`
- Score/confidence: `9.4 / 0.95`
- Fatal flags: none

## Cost

- Fresh full TTS: `$0.0389`
- Full ASR estimate: `$0.0544`
- Configured listening-QA estimate: `$0.0500`
- Repair pipeline estimate: `$0.1433`
- Actual Stage 2F spend: `$0.0000`

## Release Truth

No TTS, ASR, listening QA, upload, publication, endpoint mutation, Listen exposure, or public release approval occurred. Full TTS, ASR/source `>=9.7`, first/last, listening, manifest, endpoint, frontend, production, and owner release gates remain required.

Production revalidation returned an audio-disabled manifest with no URL/assets and a `404` audiobook endpoint. Approved controls A Ghost Story and `book-2b9853ec52` both retained `APPROVED / QA_PASSED` manifests and `206` range responses; `bn-066` remained audio-hidden.

The exact bounded retry command is recorded in `book-d19e96859f_stage2f_preflight.json` and invokes the lock-safe wrapper with `--execute` only after every inline gate is supplied.
