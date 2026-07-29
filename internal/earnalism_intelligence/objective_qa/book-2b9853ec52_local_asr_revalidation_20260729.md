# book-2b9853ec52 Local ASR Revalidation

Generated: `2026-07-29T10:17:47Z`

## Outcome

`FAIL_CLOSED_NO_NEW_ASR_9_7_PASS`

The revalidation used the exact approved production narration:

- Audio SHA-256: `a974819392d7bc4e7239828e29cf36f31661326ae71c1218273716d16bd462a5`
- Size: `5,233,965` bytes
- Duration: `327.069083` seconds
- Clean manuscript SHA-256:
  `788851c603ab1700f9e33bdfdc6a3e3c04f2ebb79890b88bc8c88f138270095d`
- Controlled content SHA-256:
  `1e1d0b25627df784b861b8c6314b8bade1baabc554122dabf00dd8c5f2ae4dd9`

The clean manuscript is the exact controlled chapter content plus one terminal
newline.

## Local results

Cached multilingual Whisper-base completed the full title in `114.04` seconds,
but emitted a punctuation-only transcript with no Bengali lexical characters.
Its raw source score and coverage were both `0.0`; first and last spans failed.
It is not release evidence.

Cached multilingual Whisper-medium was hash-verified as
`345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1`.
The word-timestamp run reached only 23% after `661.07` seconds and was stopped
as a bounded-runtime decision. It created no transcript JSON, so no medium
accuracy score exists. A follow-up no-timestamp run was stopped on coordinator
direction after `37.63` seconds and likewise created no result.

## Existing audio-derived evidence

The authoritative prior audio-derived transcript for this exact audio and
manuscript reports:

- Raw ASR score: `1.1258`
- Coverage: `0.1126`
- Character similarity: `0.4064`
- Token-order similarity: `0.1466`
- Raw first words: fail
- Raw last words: fail
- Word timestamps: `443`
- Classification: `SUPPORTING_DIAGNOSTIC_WEAK`

The historical `10.0` transcript/source match was produced by a clean-TTS-source
provenance construction audit. It proves the intended TTS input binding but
does not replace the required raw audio-derived ASR score of `9.7`.

## Safety boundary

This diagnostic did not generate TTS, call a paid provider, upload audio,
change controlled catalog data, mutate a release gate, touch `paid_tts.lock`,
or change the title's existing public state.

## Next exact command

```bash
python3 -m json.tool internal/earnalism_intelligence/objective_qa/book-2b9853ec52_local_asr_revalidation_20260729.json >/dev/null
```
