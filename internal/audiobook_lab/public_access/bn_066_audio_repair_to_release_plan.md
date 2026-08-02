# bn-066 Audio Repair to Release Plan

## Current State

- Public reader: enabled, 46 chapters.
- Public audio: hidden; endpoint fail-closed.
- Private full-book audio: present.
- Construction audit: 100% input coverage and canonical match 1.0.
- ASR/source: 0.8403/10; Bengali ratio 0.2801, Devanagari ratio 0.7113.
- First/last words: failed.
- Listening QA: not run because ASR/source failed.

Classification: `ASR_LANGUAGE_CONFIG_AND_NORMALIZATION_REPAIR_REQUIRED`.

## Prepared Calibration

The bounded calibration uses existing private chunks only:

- opening: `group_0000`
- middle: `group_0076`
- ending: `group_0151`

It probes `auto`, `bn`, `ben`, and `bengali` on the opening, then validates the best result on middle and ending. Estimated cost is `$0.1047` at the configured `$0.008/minute` estimate.

Dry-run result: `DRY_RUN_BLOCKED_PAID_GATES`; zero provider calls.

## Required Before Execute

- Set `MAX_TTS_BUDGET_USD` to an owner-approved cap.
- Set `EARNALISM_STOP_ON_BUDGET_EXCEEDED=true`.
- Set `EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD` to a bounded owner-approved cap at or above the estimate.
- Keep `OPENAI_API_KEY` available without printing it.
- Assign `paid_tts.lock.current_holder` to `audiobook_public_access_sprint_1_bn_066_asr_calibration` and keep `allowed_slugs` limited to `bn-066`.

## Release Sequence

1. Run the calibration with `--execute`.
2. Require predominantly Bengali-script output and useful chunk/source alignment.
3. Select one supported language mode; do not loop through paid models.
4. Run a bounded full checkpoint resume using that mode.
5. Require ASR/source >= 9.7 and first/last PASS.
6. Run bounded schema-3 listening QA; require >= 9.2, confidence >= 0.90, and no fatal flags.
7. Validate manifest, endpoint, frontend controls, and title-specific owner release approval.
8. Only then update public release evidence and expose Listen.

## Next Exact Command

```bash
PYTHONPYCACHEPREFIX=/tmp/earnalism-pycache python3 internal/audiobook_lab/scripts/bengali_asr_language_calibration.py --slug bn-066 --run-dir internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts --chunk-ids group_0000,group_0076,group_0151 --language-options auto,bn,ben,bengali --output internal/audiobook_lab/public_access/bn_066_asr_calibration_preflight.json
```
