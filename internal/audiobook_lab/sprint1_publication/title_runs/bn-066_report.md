# আনন্দমঠ Parallel Sprint Report

Generated: `2026-07-12T19:35:15Z`

- Slug: `bn-066`
- Language: `Bengali`
- Assigned lane: `5 - Bengali Long / Repair Lane`
- Assigned agent: `Newton (019f57d2-7f7d-74e3-878b-e5d5b2bfc3e5)`
- Public reader: `Yes`
- Public audiobook: `No`
- Quality evidence: `0.8403/10 ASR-source; listening not run`
- Estimated remaining cost: `$0.1547`
- Final state: `SPRINT_TARGET_INCOMPLETE`
- Blocker: `ASR_LANGUAGE_CONFIG_AND_NORMALIZATION_REPAIR_REQUIRED; PAID_RUNTIME_ENV_GATES_MISSING`
- Evidence: `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/bn-066.json`
- Next action: Complete reader PR if applicable, then run the title's bounded audio repair path after runtime gates are supplied

## Next Command

```bash
PYTHONPYCACHEPREFIX=/tmp/earnalism-pycache python3 internal/audiobook_lab/scripts/bengali_asr_language_calibration.py --slug bn-066 --run-dir internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts --chunk-ids group_0000,group_0076,group_0151 --language-options auto,bn,ben,bengali --output internal/audiobook_lab/public_access/bn_066_asr_calibration_preflight.json
```

No provider call, release-gate mutation, or public audio exposure was performed by this materializer.

## Parallel Diagnostic

The private QA workspace contains the hash-bound Stage 2 audio and calibration harness, but neither is present in `main`. A dry run selected `group_0000`, `group_0076`, and `group_0151`, planned six bounded calls, and estimated `$0.1047`. It made zero provider calls and wrote `/tmp/earnalism-bn066-parallel-asr-calibration-preflight.json`.

```bash
python3 -B internal/audiobook_lab/scripts/bengali_asr_normalization.py --self-test
```
