# The Tell-Tale Heart CosyVoice3 BF16 private pilot QA

Status: **REJECTED — full-title generation is not justified**

This review covers only the four private WAV files generated with
`aufklarer/CosyVoice3-0.5B-MLX-bf16` revision
`9b210b2381280b3af1c631d474a250e3e46d7017`. It did not generate more
audio, call a paid provider, upload, publish, change catalog truth, change a
release gate, or touch `paid_tts.lock`.

## Source and model binding

- Reconciled canonical manuscript:
  `316ed82d8ae04a1af3f82ec692e88bc630c4865c06192854a612f29cb017f2bb`
- Controlled chapter content:
  `0d754cdbbbcdc662091824f2078312d78eb3d80262e6301b0465ab4c3db54e4e`
- Whitespace-normalized chapter:
  `6aa43cf6dcf4c6fba097237c01938ab5269a7edda16e4006db05b5a56c7e164e`
- Synthesis attempt fingerprint:
  `4c8e9feb68fc62b3b002b4ae9e94771aa8945b861cc219b78dfa74cc9c1f4f55`
- ASR QA fingerprint:
  `f8d74f4048b76f749047df12963b9c2146c33d4d621e0e9830984e6399096aba`
- Objective verifier: cached `mlx-community/whisper-large-v3-turbo`,
  revision `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb`, weights SHA-256
  `951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6`,
  through `mlx-whisper 0.4.3`.
- Decode settings: English transcription, temperature 0, no prompt,
  no previous-text conditioning, word timestamps enabled, hallucination
  silence threshold 0.5.
- Scoring contract:
  `internal/audiobook_lab/scripts/sprint1_kokoro_title_private_audition.py::ordered_token_integrity`.

The generation runner predated the whitespace-only reconciliation merge, but
its normalized manuscript hash and all four exact passage hashes are unchanged.
The audio remains exactly bound to the post-reconciliation controlled prose.

## Objective result

| Passage | Score | Coverage | First | Last | Ordered exact | Result |
| --- | ---: | ---: | --- | --- | --- | --- |
| Opening unreliable sanity | 10.0000 | 1.0000 | PASS | PASS | PASS | PASS |
| Bedroom suspense/dialogue | 9.5050 | 0.9057 | PASS | PASS | FAIL | FAIL |
| Heartbeat crescendo | 8.4000 | 0.7241 | PASS | FAIL | FAIL | FAIL |
| Final confession | 9.8113 | 0.9811 | PASS | PASS | FAIL | FAIL |
| Concatenated aggregate | 9.3979 | 0.8908 | PASS | PASS | FAIL | FAIL |

The aggregate uses the repository verifier over the concatenated source and
transcript sequences. The source-weighted mean of the four passage scores is
`9.3596`; it is supplementary and does not replace the concatenated gate.

Two failures are material source omissions:

1. Bedroom: 10 ordered source tokens were skipped:
   `for the shutters were close fastened through fear of robbers`.
2. Heartbeat: the WAV ends 32 source tokens early after “for some minutes
   longer”; the entire remaining crescendo through “the sound would be heard
   by a neighbour” is absent.

The final confession transcribes source `here, here` as the homophone
`hear, hear`. No source-equivalence normalization was applied, so the strict
ordered-content gate correctly remains failed.

## Technical audio inspection

All files are mono 24 kHz 16-bit PCM WAV. There are no cross-file assembly
joins to inspect. No sample is hard-clipped, but two files exceed 0 dBTP:

- Bedroom: `+0.58 dBTP`, 835 near-full-scale samples, 1,048 one-sample jumps
  over half scale grouped into 27 clusters.
- Final confession: `+0.59 dBTP`, 2,760 near-full-scale samples, 1,270
  one-sample jumps over half scale grouped into 39 clusters.

Those transients require an audible reviewer before any future reuse. They are
secondary to the already-decisive source omissions.

## Listening truth

No independent audible reviewer was available in this execution environment.
No listening score, confidence, pronunciation judgment, emotional-performance
judgment, or absence-of-fatal-flags claim is made. Robotic texture, mechanical
cadence, list-reading rhythm, choppy joins, pronunciation, and expression
remain explicitly unassessed.

## Decision

Do not widen this configuration to a full title. The representative pilot
already demonstrates a repeatable content-integrity risk: punctuation-delimited
text was omitted and one longer passage was truncated. Full generation would
scale a demonstrated failure and create avoidable QA work.

Keep the title reader-live and audio-hidden. Do not repeat model revision
`9b210b2381280b3af1c631d474a250e3e46d7017` with seed `2026073001`, the same
model-default voice, and these passage hashes. A future pilot must use a
materially different configuration and deterministic sentence-safe chunking,
prove exact chunk reconstruction before synthesis, and pass objective QA before
any full-title generation or listening spend.

The generator stdout contained stale
`REPRESENTATIVE_AUDIO_NOT_GENERATED` text after its status and file list proved
generation completed. That is an evidence-semantics defect, not a release
blocker. This report records only truthful current blockers.

Next exact validation command:

```bash
python3 -m json.tool internal/audiobook_lab/sprint1_publication/title_runs/the-tell-tale-heart_cosyvoice3_bf16_private_objective_qa_v1.json >/dev/null
```
