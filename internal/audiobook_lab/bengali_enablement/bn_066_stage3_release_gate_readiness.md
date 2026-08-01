# bn-066 Stage 3D Release-Gate Readiness

Generated: 2026-07-10T20:02:48Z

## Verdict

`ASR_LANGUAGE_CONFIG_AND_NORMALIZATION_REPAIR_REQUIRED`

The private Stage 2 audiobook and all 152 Stage 3C ASR checkpoints exist, but the source gate is not met. The ASR score is `0.8403/10` against the required `9.7`, raw first and last words do not match, and the transcript is Devanagari-dominant mixed script.

The Stage 3D verifier semantics repair proves the independent TTS-by-construction audit: 152 groups, 100% input coverage, canonical match `1.0`, and first/last construction boundaries pass. This construction evidence is diagnostic only and does not override the failed ASR/source gate.

## Blockers

- ASR/source score below `9.7`.
- First ASR words do not match the manuscript opening.
- Last ASR words do not match the manuscript ending.
- Mixed-script ASR transcript is not reliable release proof; Bengali script ratio is `0.2801`.
- Bengali ASR auto-detection produced inconsistent per-chunk scripts because the configured language code was empty.
- Existing normalization/alignment does not robustly align Devanagari phonetic Bengali to the sanitized TTS source.
- Bounded listening QA did not run because the source gate failed.
- Upload, endpoint, browser, and owner release approvals are not present.

## Release Truth

`bn-066` remains private and audio-hidden. No public Listen CTA, player UI, upload/publication, release-gate mutation, static `/audio/...` fallback, browser speech fallback, word-level sync claim, AudioObject approval, paid Listen approval, or launch-wide 10/10 claim occurred.

## Next Exact Command

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && python3 internal/audiobook_lab/scripts/test_asr_checkpointing.py && python3 internal/audiobook_lab/scripts/test_sarvam_full_pilot_tts_hook.py
```

After separate owner authorization, run a bounded language/model recalibration on a tiny representative set of existing chunks. Do not rerun all 152 chunks, regenerate TTS, or run listening QA until Bengali-script ASR evidence reaches the source threshold.
