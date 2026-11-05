# Evidence-led voice engineering and theatrical scoring

Research checked 1 November 2026. Use with [narrative performance](narrative-performance.md) for new narration, a performance repair or a revised scored edition. It is a diagnostic and production method, not evidence that an existing master passed. Current title-specific policies, rights, budgets and owner restrictions still govern execution.

## Start with the actual cause, not a global audio preset

Read the full authoritative work and listen to the reported region with adjacent context. Inspect the exact text that reached the worker, not only the Reader manuscript. Compare source, synthesized-text and audio hashes; unit/run boundaries; base and scene instructions; voice/model/runtime revisions; sampling settings and seed/RNG state. Separate measured facts, reported listening defects and causal hypotheses. A matching speaker ID does not establish a matching performance.

| Symptom | Inspect first | Smallest credible remedy |
|---|---|---|
| Strange pauses inside a sentence | Worker input line wraps, syntax, breaths, actual word times, pitch/stress on either side | Remove only verified surplus non-speech where the surrounding delivery remains grammatical; wrong stress/intonation needs a suitable retained take or authorized performance replacement |
| Different person at a unit boundary | Neutral narrator passages, timbre/accent/age impression, source runs, instructions, pace and local levels | First compare equivalent neutral narrator lines, not an excited character against calm narration; distinguish level/recording changes from identity/performance changes, then choose a justified level correction or accepted matching take |
| Uneven gaps at joins | Generated trailing silence plus inserted gap plus next leading silence; semantic boundary type | Edit the measured boundary as one complete pause, preserving breaths and consonants; never flatten every boundary to one duration |
| Robotic or emotionally wrong delivery | Full sentence intent, subtext, phrasing and the model's actual supported controls | Direct the performance before synthesis; do not try to manufacture acting through a chain of global pitch/EQ/speed effects |
| Score distracts or feels generic | Dramatic purpose, instrumentation/density, speech-active masking, cue changes and pumping | Rewrite/reduce the cue, automate its level, duck the music or use deliberate silence; leave narration intelligible |

## Prevent formatting from becoming acting instructions

Maintain two separate artifacts: the immutable authoritative text and a source-mapped TTS rendering. Remove visual wraps only after identifying them as layout, preserving words, spelling, meaningful punctuation and real structural breaks. Reconstruct paragraph/scene structure from reliable edition evidence and reviewed context; neither splitting every newline nor globally joining every whitespace sequence is a universal solution. Preserve poetry/stanzas, intentional lineation, lists and headings under their audio treatment policy. Do not silently dehyphenate words or change a question into a statement.

Record each transformation and a reversible source-offset/token mapping, plus the source and rendered-text hashes. Validate complete ordered token coverage before inference. If punctuation must be adapted for an approved audio treatment, record that exact exception separately. Keep scene directions, pause annotations and unspoken context outside the narration string. Never pass SSML/audio tags to an adapter merely because another engine supports them.

W3C SSML distinguishes linguistic break strength from an explicit duration, with context determining ordinary breaks. Use that as a planning model, not as proof that Qwen implements SSML. [W3C speech synthesis specification](https://www.w3.org/TR/speech-synthesis/#S3.2.3).

## Build a stable identity with a changing performance

The performance plan records narrator identity and an accepted reference, accent, base texture/register, pronunciation lexicon, viewpoint and scene arc. Each sentence/phrase adds speaker, intention, focus word, syntactic phrase boundaries, emotional change, pacing and transition intent. Direct connected meaning rather than independent settings for every punctuation mark. Keep character dialogue distinguishable without accidentally replacing the narrator or inventing an unapproved cast.

Use a short, stable base direction and concise scene-specific changes. Do not contradict the scene with a globally mournful or angry instruction. Archive the actual combined request and effective settings. Before full production, an authorized audition must include two consecutive units and their join, a neutral narrator passage, dialogue and an emotional turn; do not judge identity only from unrelated snippets. On resume, compare new material with the retained identity reference before committing further generation.

The Qwen 1.7B CustomVoice interface supports a stock speaker and natural-language `instruct`; its 0.6B counterpart has a different instruction contract. Freeze the actual adapter/revision, not a product label. Sampling and recorded RNG state aid reproducibility; a fixed seed does not certify identity or naturalness. Do not assume batches share acoustic history, invent cross-unit conditioning arguments, disable sampling by default or copy undocumented numerical emotion controls. Future settings comparisons require actual authorized auditions; no new model, cloning or speculative downloads are implied. [Official model matrix](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice), [official inference implementation](https://github.com/QwenLM/Qwen3-TTS/blob/main/qwen_tts/inference/qwen3_tts_model.py).

## Make an edit decision list before touching the master

For each defect record the source phrase, exact input hash/sample interval, intended grammatical/scene function, audible finding, proposed action and neighbouring review window. Mark the action as retained-take selection, non-speech timing edit, technical level correction, or performance replacement requiring authority. Keep unsupported cases held. Whole-unit WPM, F0, spectral or speaker-similarity measurements flag review locations; none establishes a correct emotion or the same perceived person, and whole-unit WPM includes pauses.

Choose a pause by its purpose: connected clause, sentence completion, paragraph reflection, scene transition or chapter. Derive useful working ranges from genuinely approved passages of this work; retain intentional exceptions. Do not impose a universal comma duration or repair pace by stretching all speech. A low-energy region can contain breath, an unvoiced consonant or a quiet word: it is not an automatically safe cut. Check waveform/spectrogram and aligned words, then listen before approving it.

Edit a lossless copy and preserve the originals. Use short, material-appropriate fades only where needed to avoid a discontinuity; never crossfade over distinct spoken words or use long overlaps to conceal an identity change. Save exact input/output sample counts and the edit list. Preserve unchanged spoken samples where feasible. After a timing edit update chapter/navigation media times and affected package hashes; regenerate measured text alignment only where the selected path consumes it; old times must not be relabelled as new measured sync. Validate affected words and both joins before a complete assembled listen.

## Score the dramatic meaning, then engineer its audibility

Use a small musical vocabulary whose motifs, harmony, register, texture and density follow the story. The cue sheet specifies scene/phrase anchors, purpose, actual measured entry/exit times, licence/attribution, asset hash, fades, level and ducking. Include silence as a conscious cue. Do not change musical tracks at every generation boundary or beat-match the narrator. Avoid premature revelations, constant melodic competition and repeated emotional swells. Atmospheric music can establish place, tension, tenderness or time while leaving the listener room to imagine. [Audio-theatre practitioner guidance on clear transitions and silence](https://www.ruyasonic.com/wrt_time_transitions.htm).

Validate the union of measured cues and explicitly reviewed silence intervals across the complete narration. Maintain a per-unit coverage table including music continuing into/out of every join; track exhaustion or a generation boundary cannot justify an unexplained gap. Separately listen for audible music throughout the intended scored passages: nonzero samples, a foreground/background ratio and an audible opening do not establish a sustained perceived bed.

Fix narration first, retaining dry narration and score as separate stems. Begin with manual cue-level automation. When useful, process the **music** using narration as a sidechain detector, then mix it with untouched narration; do not accidentally compress the narration with music. Tune attack/release and detector sensitivity against quiet speech and breaths so the bed does not pump between words. Reduce competing instrumentation and density before pushing speech louder. A fader percentage says nothing about the actual speech/background difference.

WCAG 1.4.7 offers a Level AAA option of at least 20 dB speech/background separation, alongside no-background or background-off alternatives. Use that relative difference as an accessibility-oriented mixing goal, checking quiet speech, without confusing it with -20 dBFS or claiming compliance from whole-book averages. A proposed music-off feature must actually exist. [W3C criterion explanation](https://www.w3.org/WAI/WCAG22/Understanding/low-or-no-background-audio.html), [G56 technique](https://www.w3.org/WAI/WCAG22/Techniques/general/G56).

## Master for the real delivery path and review the encoded result

Declare the applicable delivery target before rendering; retain integrated loudness, loudness range and true-peak measurements. EBU's broadcast reference is -23 LUFS; its streaming supplement permits contextual adaptation, so -14, -16 or -18 LUFS must not be treated as a universal audiobook requirement. Preserve the actual title/player specification. [EBU R128](https://tech.ebu.ch/docs/r/r128.pdf), [streaming supplement](https://tech.ebu.ch/docs/r/r128s2.pdf).

Meter true peaks rather than sample peaks alone, and retain codec headroom. [ITU-R BS.1770](https://www.itu.int/rec/R-REC-BS.1770-5-202311-I/en). A practical render uses a lossless working mix, measured normalization with conservative dynamics treatment where required, one delivery encode and remeasurement of the decoded delivery file. Check mono compatibility, starts/tails, cue transitions and quiet lines on available headphones and ordinary speakers; do not claim unperformed device tests.

FFmpeg provides `sidechaincompress`, `acrossfade` and measured `loudnorm`. Confirm the installed filter options, explicitly control output rate/channels, account for `amix` gain/normalization behaviour, and verify whether requested linear normalization remained linear. Filters implement processing, not editorial judgement. [Official filter documentation](https://ffmpeg.org/ffmpeg-filters.html). Independent fresh-ear listening and speech audibility on normal consumer playback remain essential. [BBC drama sound guidance](https://downloads.bbc.co.uk/academy/collegeofproduction/docs/clear_sound_recording_drama_ts.pdf).

Retain three distinct dispositions: dry narration quality, final scored-mix quality, and production playback/accounting. Review the complete exact final scored edition privately with the owner before publication. A clean dry stem does not qualify a new mix; good music does not clear poor acting; a successful player test does not qualify either. All known material findings must have actual repair/review evidence, not just resolved labels.

## Export native-ASR evidence while it exists

For an authorized native recognizer run, arrange these exports in the existing output/journal before inference. Capture authentic raw text, native output and provider completion/usage before source comparison or a semantic check can raise an error. This is a capture contract, not permission for another run or a new release method.

| Retain once | Minimum useful contents |
|---|---|
| Audio and assembly clock | Exact delivered-master and analysis-PCM hashes; actual decode/resample/channel treatment; sample rate/count; each input's exact sample bounds, unit/global offset, context and any assembly/edit mapping. No duration-proportional source timing. |
| Recognition identity | Actual model/revision/artifact and tokenizer/vocabulary/class-map hashes; blank ID, language/subset order, text normalization and exact spoken-form/source-offset map. |
| Authentic outputs | Raw transcript and done/usage/error records; greedy IDs/runs where exposed; native and selected emissions with dtype/layout/shape/valid lengths. Save them durably and atomically before fidelity checks; keep an authentic failed take blocked. |
| Output semantics | Whether values are logits, probabilities or log probabilities; exact masking/normalization/class axis and decoder time-axis transforms. A variable named logprobs is not evidence of normalization. |
| Timing and uncertainty | The actual supported frame origin/step/padding/subsampling and source of that information; per-input clocks/seams and measured word/paragraph method. Retain available posterior/confidence with its definition; otherwise mark unavailable. A token activation cell is not automatically an acoustic onset/offset. |
| Fidelity and reuse | Raw ordered comparison/counts, scoped adjudications and independent cue validation; exact source/audio dependencies and unperformed items. Keep construction coverage, ASR score, listening and sync separate. |

For a hosted interface that does not expose native arrays, record that limitation and choose an already authorized supported proof path; do not fabricate arrays or make impossible exports a retroactive gate. Validate the export/import contract offline before spending the run. Preserve all full raw windows before any overlap reconciliation; do not infer a uniform clock from output length, merge whichever recognizer words look best, or force the manuscript into a fidelity PASS. Measured sync must satisfy the actual repository method/tier and audio/source binding, without inventing a universal mathematical-zero-error or two-model requirement. When a necessary capability is absent, state it early instead of launching open-ended forensic recovery.

Primary local contracts: the repository's [sync acceptance policy](https://github.com/ronik18/earnalism-digital-library/blob/main/internal/earnalism_intelligence/sync_acceptance_policy.json) and [factory evidence normalizer](https://github.com/ronik18/earnalism-digital-library/blob/main/internal/audiobook_lab/scripts/sprint1_factory_release_evidence_normalizer.py) define accepted measured evidence; this diagnostic record does not silently add itself to those methods. The source-mapped input and raw-before-comparison requirements preserve the distinction between observations and the text being checked.

## Minimum reusable production record

Keep one source-bound packet with: full-book interpretation and casting rationale; authoritative/TTS-text hashes and transformation map; identity reference and effective model/run settings; phrase/scene directions; exact defect/edit list with neighbouring windows; licensed score assets and measured cue sheet; narration/score/final mix hashes; alignment and delivery measurements; complete listening findings and actual owner evaluation; unresolved items and consumed budgets. Start the next authorized action from that record, without recreating healthy audio or repeating a consumed provider attempt.


Read-along, narration-linked highlighting and text-linked audio navigation are permanently retired from supported current and legacy customer paths. Do not offer, advertise or re-enable them from stored flags. Ordinary Reader page/chapter navigation, text selection/manual annotations, and native audio chapter/seek controls remain. Reuse historical measured evidence only in its actual scope; never delete it or relabel it PASS/N/A. Record candidate-bound NOT_APPLICABLE for a verified nonconsumer without fabricating cues; caption/cue-consuming production remains strict where actually selected. This source policy grants no runtime retry, allocation or release authority.
