# Editorial chamber score v12

This is a reversible accompaniment edit for the Moon's new private review edition. It uses the existing licensed piano/harp samples and the same D–A–E–F question, harp answer and reversed F–E–A–D return. It reads no voice recording and changes no narration, notes, note timing, instruments or authored silence.

`editorial_score.compose(path, seconds, quiet_intervals=(), rate=24000, scenes=(), asset_root=ASSETS, speech_intervals=())` has the same ordinary call signature as the existing chamber composer. Use a new output directory; the existing compositor refuses overwriting stems.

The explicit event hook in `final_chamber_score.compose` runs after the existing written arrangement and before sample rendering. It permits only bounded written-dynamics changes and rejects changed pitches, time, instruments or event counts. Existing callers with no hook retain their prior arrangement.

The revision reduces a soft-support attack by 2 dB when its start lies within 300 ms of a principal motif/reveal event. The returning piano A4 lead is reduced by 1 dB. These are source-event decisions, not sample-by-sample gain chasing. The original -34 LUFS accompaniment target remains; there is no explicit global gain boost. Subsequent mastering means final sample amplitudes must still be measured rather than assumed uniformly lower.

The v30 case identifies support attacks near 8.589, 9.909, 21.129, 35.029 and 69.813 seconds and the returning A4 at 59.819 seconds. Future timings follow actual scene/anchor data rather than these absolute times.

Integration owned by the main lane:

- Dispatch palette `acoustic_editorial_v12` to `editorial_score.compose`.
- Register version `moon-score-v12-editorial-orchestration` to `editorial_score.py` in `rights_audit.py`'s acoustic composers mapping. Its `composition_source_sha256` binds the new module. Also verify `base_composition_source_sha256` against `final_chamber_score.py` for this version.
- Include that version in the v10/v11 branches in `music_automation.py` for the existing 0.25-second smootherstep safety ramp. The source compositor's one-second silence shoulders are preserved. Do not silently use the unknown-version fallback.
- Recompose only accompaniment, then mix against the exact preserved B narration; run passage balance, fade, transition, peak, hash and full audiovisual checks. Keep failed report evidence and new human approvals pending.

Executed focused tests compose real temporary licensed sample audio and verify source-asset hashes, exact silence, output/provenance hashes, bounded event changes, default version behavior, rejected note changes, input immutability and overwrite refusal. This establishes engineering behavior, not musical quality, therapeutic benefit, sustained attention or revenue. Full scored/dry listening remains required.
