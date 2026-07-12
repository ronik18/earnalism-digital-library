# book-d19e96859f Stage 2G Report

## Decision

`ASR_SOURCE_MISMATCH`

Secondary classification: `LISTENING_QA_REPAIR_REQUIRED`.

The public reader remains enabled. Public audio remains hidden. Publication was not authorized because objective and listening gates failed.

## Runtime Gates

- `SARVAM_API_KEY`: present, value not printed.
- `OPENAI_API_KEY`: present, value not printed.
- Sprint total cap: `$175`.
- Per-title cap: `$30`.
- Title-specific full-pilot cap: `$1`.
- ASR cap: `$1`.
- ASR retry cap: `$1`.
- Listening-QA cap: `$1`.
- Stop-on-budget: enabled.

## Full TTS

- Provider/model/voice/style: Sarvam / `bulbul:v3` / `pooja` / `dialogue_human_touch`.
- Prepared text: `6,485` characters in five groups.
- Full TTS: PASS.
- Private audio: `internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_stage2f_full_tts/book-d19e96859f_sarvam_bulbul_v3_pooja_dialogue_human_touch_final.mp3`.
- Size: `10,047,021` bytes.
- Duration: `627.875833` seconds.
- SHA-256: `40de51486f663bf9af196f2d9018029d7e01f75d0f4d16fc537910fcfe754da3`.
- Fallback/local/stale reuse: none.

## Release QA

- Raw ASR/source: `1.3504 / 10`, required `9.7`.
- First words: FAIL.
- Last words: FAIL.
- Transcript: mixed Bengali and Devanagari.
- Construction audit: `10.0`, supporting provenance only, not accepted as ASR.
- Listening scores: `8.0`, `8.0`, `9.4`, `9.4`, `9.4`, `8.0`.
- Minimum confidence: `0.85`.
- Fatal flags: `list_reading_rhythm_detected`.

## Cost And Lock

- TTS estimate: `$0.0389`.
- ASR estimate: `$0.0837`.
- Listening-QA estimate: `$0.3000`.
- Stage 2G estimate: `$0.4226`.
- D19 conservative cumulative estimate: `$1.5318`.
- Sprint cumulative estimate: `$10.1766 / $175`.
- Sprint estimated remaining: `$164.8234`.
- Actual provider billing: not reported.
- Lock: restored byte-for-byte to active/current-holder-none/empty-next-holders.
- Lock SHA-256: `ab57e15c5329256304014ea8a77e086b7ec5748a0fee6423f772f350ef58b50e`.

## Release Truth

No upload, public manifest, endpoint, frontend release state, deployment, Listen exposure, or release-gate mutation occurred. The production manifest remains audio-disabled and the audiobook endpoint remains `404`.

Automated Google and Sarvam arms are exhausted for this title. The next repair state is source-bound human narration or licensed-audio import.

## Next Command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug book-d19e96859f --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```
