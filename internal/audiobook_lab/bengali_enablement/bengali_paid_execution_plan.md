# Bengali Paid Audition Execution Plan

Generated: 2026-07-09T05:54:16Z

## Strategy Summary

Stage 1 is authorized as a paid representative-audition sprint with a hard 5 USD cap. It is not a full-book generation, publication, public Listen, or release-gate mutation sprint.

The current shell does not expose `MAX_TTS_BUDGET_USD=5`, and the active Bengali campaign policy also requires explicit repo env gates before provider calls. Because those gates are missing, the safe result for this run is a zero-spend blocked preflight plus candidate-specific next actions.

## Required Gates Before Paid Calls

- `MAX_TTS_BUDGET_USD=5`
- `EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS=true`
- `EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true`
- `EARNALISM_STOP_ON_BUDGET_EXCEEDED=true`
- `EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD=5`
- `EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE`, recommended `2` for this bounded sprint
- `paid_tts.lock` holder must be `audiobook_enablement_sprint_1`

## Candidate Order

1. `bn-066`: primary candidate. Source/rights pass; reader data exists; representative samples need source/page boilerplate stripping before synthesis.
2. `muchiram-gurer-jibanchorit`: conditional candidate. Use compact split samples only after timeout-risk repair.
3. `book-d19e96859f`: repair diagnostic only. One targeted cleaned group sample if it isolates the ASR/source mismatch.
4. `book-f5d593e1f4`: repair diagnostic only. One targeted cleaned group sample if it isolates the ASR/source mismatch.

Skipped for paid execution in this sprint:

- `pather-panchali`: rights/source/cover repair track before audio.
- `a-ghost-story`: Bengali candidates take priority; it remains reader-first/audio-hidden.

## Stop Conditions

- Budget would exceed 5 USD.
- Required env gate is missing.
- Source or rights preflight fails.
- Provider timeout repeats.
- Generated audio is empty, corrupt, or too short.
- Listening QA has fatal red flags.
- Any path would expose public audio before full release gates.

## Next Exact Command

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && MAX_TTS_BUDGET_USD=5 EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS=true EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true EARNALISM_STOP_ON_BUDGET_EXCEEDED=true EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD=5 EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE=2 python3 internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py --manifest book_import_manifest.json --candidate-slugs bn-066 --max-passages 1 --max-seconds-per-sample 45 --providers sarvam --max-voices-per-provider 1 --voice-filter sarvam:ratan --style-profiles literary_warm_pacing --bengali-audiobook-92-rescue --fail-closed --run-dir internal/audiobook_lab/bengali_enablement/bn_066_stage1_audition
```
