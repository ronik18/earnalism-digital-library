# bn-066 Stage 3D ASR Mismatch Diagnosis

Generated: 2026-07-10T20:02:48Z

## Verdict

`ASR_LANGUAGE_CONFIG_AND_NORMALIZATION_REPAIR_REQUIRED`

This is not a final NO-GO and it is not evidence of a true audio/source mismatch. Stage 3C produced 152/152 successful checkpoints, but Bengali language handling intentionally passed no language code to `whisper-1`, leaving each chunk to auto-detection. The resulting transcript is Devanagari-dominant and cannot satisfy the strict Bengali ASR/manuscript gate.

No provider call or listening-QA call ran in Stage 3D. `bn-066` remains private and audio-hidden.

## Group-Repair Semantics

`group_repair.status: NOT_REQUESTED` means the Stage 2 audio was a fresh generation and no repair manifest was supplied. Group repair is optional. The old verifier rejected this status before checking source coverage and hashes, which incorrectly blocked a valid fresh-generation construction audit.

The repaired semantics are fail-closed:

- New fresh-generation manifests record `NOT_NEEDED` with `repair_requested: false`.
- Legacy `NOT_REQUESTED` is accepted only when no repair marker exists and the complete construction audit passes.
- `NOT_REQUESTED` remains blocked if repair was required, attempted, failed, or construction evidence is incomplete.

Offline replay against the existing private artifacts passed: 152 groups, 100% TTS input coverage, canonical match `1.0`, first/last construction boundaries pass, and no verifier blockers.

## Checkpoint Diagnosis

| Chunk | Duration | Script profile | Transcript | Expected source | Diagnosis |
| --- | ---: | --- | ---: | --- | --- |
| `group_0000` | 145.84 s | 99.68% Devanagari | 1,167 chars | `অতি বিস্তৃত অরণ্য...` | Phonetic Bengali rendered as `ओती बिस्ट्रितो अरन्नो...`; normalized similarity `0.6705`, phonetic `0.8283`. |
| `group_0076` | 135.22 s | 99.71% Devanagari | 1,289 chars | `আজ যাহা লুঠিয়া আনিয়াছি...` | Phonetic Bengali rendered as `आज जहा लुठिया आनी आछी...`; normalized similarity `0.7817`, phonetic `0.9174`. |
| `group_0151` | 66.63 s | 100% Bengali | 308 chars | `কি প্রকারে আসিলাম?—হাঁটিয়া...` | Bengali output starts `তী প্রকারে আশিলাম...` with omissions/spelling variants; normalized similarity `0.7455`, phonetic `0.7918`. |

Full transcript script counts are 22,749 Bengali, 57,779 Devanagari, and 700 Latin characters. The Bengali ratio is only `0.2801`; this is not release-grade ASR evidence.

## Source Layers

The raw ASR verifier compared against `clean_manuscript.txt`, which begins with `১৮৮৩ (পৃ. ১-২)`. Stage 2 TTS used the separately sanitized prepared manuscript, which starts directly with `অতি বিস্তৃত অরণ্য।` The prepared manuscript and reconstructed chunk sequence are normalized-identical, score `10.0`, cover 100% of tokens, and pass both first and last boundaries.

Raw first/last ASR checks fail, while the existing Bengali projection report marks projected first/last edges as present. That inconsistency confirms expectation/alignment-layer repair is needed; it does not authorize a pass.

## Root Cause

Confirmed:

- `ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED`
- `ASR_MODEL_OUTPUT_MIXED_SCRIPT`
- `ASR_NORMALIZATION_REPAIR_REQUIRED`
- `SOURCE_ALIGNMENT_LAYER_MISMATCH`
- `FIRST_LAST_EXPECTATION_LAYER_MISMATCH`
- `GROUP_REPAIR_VERIFIER_SEMANTICS_BUG`

Not proven:

- `TRUE_AUDIO_SOURCE_MISMATCH`
- `TTS_CHUNK_ORDER_MISMATCH`
- `CHECKPOINT_TRANSCRIPT_CORRUPT`

The ASR score remains `0.8403/10` against the required `9.7`. Construction proof is diagnostic only and does not override this failed source gate. Listening QA remains blocked.

## Next Action

Use an owner-authorized, bounded ASR recalibration on a tiny representative set of existing chunks. Require Bengali-script output from a repo-supported model/language configuration before attempting any full-book alignment retry. If Bengali-script output still fails, repair the normalization/alignment layer; do not regenerate TTS audio without evidence of a true mismatch.

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && python3 internal/audiobook_lab/scripts/test_asr_checkpointing.py && python3 internal/audiobook_lab/scripts/test_sarvam_full_pilot_tts_hook.py
```
