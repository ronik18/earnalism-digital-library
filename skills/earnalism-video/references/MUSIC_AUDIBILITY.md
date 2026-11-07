> Release policy: [GO_LIVE.md](GO_LIVE.md) governs. Research, variant and growth tasks are optional; one final candidate decision covers primary checks. Older wording does not add approval steps.

# Music audibility, silence and transitions

Use the selected candidate's bound reports, not a historical version's measurements. Current Moon source: `acoustic_editorial_v12`; its v11 base and older sources are historical. Follow [musical direction](MUSIC_DIRECTION.md) for source-event orchestration before downstream automation.

## Preserve before measuring

Rebuild from the original score through fresh speech ducking, never from an already automated bed. Preserve `score-ducked-before-automation.wav`, source/output/narration hashes, event plan, gain knots and prior reports. Zero music samples must remain zero; verify declared quiet intervals and preserved zero runs in actual audio, not only configuration. Keep B's narration stem unchanged during score corrections.

`mix_score` flush-pads both sidechain inputs, then trims to actual narration duration. The analysis may pad at most one millisecond of rounding and records it; never alter media or widen duration tolerances to conceal truncation.

## Independent engineering screens

| Screen | Current implementation | Required interpretation |
|---|---|---|
| Overall audibility | Median active music-below-voice gap 18–28 dB | Does not prove each passage is audible or speech is clear |
| Individual passages | One-second interior active windows 16–32 dB | Keep every flag/timecode; short decays or pauses still need listening |
| Silence/fades | Music below -65 dBFS or voice below -45 dBFS excluded from overlap; mark silence boundaries | Exclusion does not prove a natural fade |
| Terminal fade | Final window qualifies only with an actual measured zero-valued music tail | Constant weak final music remains a failure |
| Gain motion | Six-second phrase energy, look-ahead, cubic smoothstep; -12/+8 dB bound and <=1 dB/s analytic peak slew | Smooth control curves do not certify absence of pumping |
| Re-entry | Actual rest detection and source-aware shaped ramp recorded in report | Judge the combined source shoulder, instrument attack and post-duck ramp |
| Delivery | Current hashes, stem duration, full decode, safe peaks and downloaded readback | Does not grant musical/listening approval |

The current editorial/v10/v11 source family uses a 0.25-second quintic smootherstep post-duck safety ramp over its existing one-second source shoulders. Earlier registered sources used different ramps; do not infer the actual value from a folder name or automatically stack long fades. Inspect first attack, body and following phrase after every preserved rest. The old one-second gain-chasing controller is superseded.

Do not optimize one metric by regressing another, erase local flags after a slew pass, or weaken bands to manufacture a pass. Inspect 100 ms onset/return windows, local musical dynamics, soft consonants and complete scored/dry versions at normal volume on actual speakers/headphones. Timing-overlap context can supplement a one-second flag but cannot erase it. Record perceptual judgments separately.

## Source correction and scope

Equal peak level of one-shots does not mean equal sustained loudness. Prefer bounded musical voicing/attack/body correction when note attacks crowd speech while tails disappear; avoid faster compression or a blanket gain lift. Current source normalization uses first-1.2-second energy bounded +/-4 dB against the prior peak reference, restrained speech-overlapping leads and sparse support. Moon-specific note gains/timecodes are examples, not future automatic defaults.

Use `remix.py` for a fresh music-only edition, preserving narrator/raw/caption hashes and video streams. For combined image/music work, preserve narrator PCM with the explicit expected-hash guard and review fresh video. Global mix normalization/re-encoding means an unchanged narrator stem is not a claim of bit-identical narrator samples inside the new encoded mix.

`music-balance.json` binds current narration/post-duck hashes; `music-automation.json` binds source/output and transition evidence. Non-fixture mixing stops on unresolved balance issues. An explicitly labeled private fixture may retain flagged evidence for engineering but can never publish; do not relabel it. Source/licensing checks, balance, transition, silence, hearing/resemblance and final publication are separate gates. Keep rejected candidates and measured deltas without describing parameter changes as proven audible improvements.


## Corroborate passage flags with actual speech

Before dismissing a local flag as a pause/decay artifact, inspect the complete thought using canonical script punctuation mapped to actual word timings. `speech_music_context.py` computes energy on the union of those word intervals, excluding intervening gaps and avoiding duplicate overlap. A zero music interval is a rest, not an invented enormous dB gap. Reject out-of-range timing. This supplements the unchanged one-second screen; retain its flags and do not replace listening or weaken bands. If complete spoken thoughts corroborate an over-strong bed, use restrained score-only phrase curves and verify the original narration contribution, actual silent samples and both encoded deliveries. Do not transfer an episode's gain knots into general defaults or describe numeric gains as proven audible improvement.

ASR word spans are alignment envelopes, not continuous voiced phonation. Even high word-span coverage can include a very weak syllable, an internal gap or a breath. Inspect short-window source voice energy and actual boundaries before interpreting a near-equal music/voice ratio: an accent in a low-energy gap is not automatically masked speech. Retain the raw flag and distinguish measurement, a supported listening finding and human acceptance. If a narrow score phrase is genuinely repaired, preserve the established mastering scalar or prove unchanged samples outside its declared support; re-normalizing the whole score can undo a local attenuation or lift unrelated passages.

For score-only revisions, retain the established dry voice channel mapping as well as the raw narration hash; duplicating a mono voice at unity changes stereo loudness. Verify the voice contribution against that dry reference before encoding. When formats share one soundtrack, encode it once and stream-copy it into both masters, then compare elementary audio hashes and durations. Do not claim identical encoded audio merely from identical input PCM.


When a private review exposes remaining music flags, generate its passage list from the current bound report, not a hand-picked time list. Cover every flag and the actual rest fade/return boundaries. Keep the original window gap in a separate field from word-only gap and word coverage; never overwrite or auto-clear the original flag. Label contextual lead-in explicitly. Test review coverage, seek behavior and unknown/no-word cases. Verify actual PCM rest boundaries and controller continuity, but do not call those measurements a perceptual no-pumping verdict or keep changing the mix solely to eliminate flags. Reuse unchanged media evidence and the existing consolidated final decision.


## Qualify an automated listening route before trusting it

Use actual audio, without supplying the transcript first. Before relying on a new model/runtime conversion, test blind known score-only, dry-speech and scored-speech controls. If it invents speech or misses clear speech, reject its perceptual judgments; successful inference and preprocessing tests do not establish listening competence. Preserve the failed raw responses and model/runtime revision. Do not modify a production mix from failed calibration or repeat account-refresh attempts without a new diagnosed cause.

Dry speech is also a negative music control: a reviewer that invents a score in it cannot qualify music balance, even when it transcribes words or identifies pictures correctly. Record the actual responding model and any fallback notice; requesting Pro does not establish that Pro answered. A service-capacity downgrade is not an authentication problem to fix by expanding access or billing. Preserve the failed control and any separately valid visual evidence, but do not seek a favorable listening verdict by repeated prompting or change the soundtrack from that response.

Retain every raw passage flag while supplementing it with explicit authored rest shoulders and declared note spans. An amplitude-based fade guess is not the score plan. Merge overlapping review intervals for efficient listening while retaining all original timecodes and reasons. Unsupported legacy context remains unavailable, rather than silently clearing findings or adding a release requirement. These annotations locate listening questions; they do not certify audibility or natural transitions.

Respect documented input-duration limits. For longer soundtracks, use overlapping context windows that cover the complete union through the final sample; `listening_coverage.py` rejects gaps and over-limit windows. Input coverage is not a listening verdict. Record model findings separately from human acceptance, engineering screens and final approval. Identical elementary soundtrack hashes allow shared audio evidence, while each visual composition still needs its own sync/clearance check. New external destinations require applicable data-handling authorization; never enable billing to rescue a no-charge review.


A short control pass does not qualify a longer production input. Verify actual access at the intended encoding, duration and channel count; a successful upload or audio-specific citation alone is insufficient. Check reported words against the actual excerpt boundaries: impossible boundary words or unavailable inputs limit the result, even when a model correctly detects speech and music in controls. Keep model-located musical concerns as hypotheses until corroborated, and request the existing consolidated human review when the route cannot reliably close listening. This adds no approval stage and never justifies changing a mix merely to satisfy a model.

When full-file access is disputed, a separate, never-publish blind probe with known non-speech events across the recording can test coverage. Withhold its event count, times and truth mapping from the reviewer; retain the unmodified candidate. A claimed complete review that misses probe events or puts speech/music into source-confirmed silent intervals cannot close listening, even if its overall verdict is favorable. Short excerpts may still provide scoped evidence: retain exact source ranges, overlaps, encoding/quantization and every result, verify acoustic access for that batch, and distinguish complete segmented coverage from uninterrupted listening and human acceptance. Failed controls establish a review-route limitation, not a defect in the soundtrack; stop rather than prompting repeatedly for a favorable pass.

For a scored-versus-dry audition, source preservation alone does not establish equal narrator loudness: body mastering can change the scored voice gain. Inspect the actual finishing path. If a comparison is not level-matched, label it, or prepare a separate dry listening derivative with one documented constant gain estimated from narration during authored score-free intervals. Keep the original dry file, full scored master and every production soundtrack untouched. State that this is an approximate voice-energy match, not identical narrator PCM or a perceptual pass. Preserve full-recording access, all flagged passages and silence contexts, and allow only one comparison player at a time.

## Reuse reviewer-access findings

Before sending a new edition to an external listening reviewer, consult its retained access receipt for the same service, interface/model mode and encoding. A new episode or changed soundtrack does not itself repair a known audio-access failure. Re-test only when an identifiable capability, interface, model or supported input path changes; keep that reason explicit. If fresh controls return “not assessable,” stop that route rather than uploading the full recording or seeking a favorable verdict. Retain the result in private project evidence, not raw account data in the reusable skill. Use actual human listening when no verified acoustic reviewer is available, sharing one full listening pass across files with verified identical soundtracks while retaining each format’s visual/sync checks. This adds no separate approval stage and grants no listening or publication acceptance.
