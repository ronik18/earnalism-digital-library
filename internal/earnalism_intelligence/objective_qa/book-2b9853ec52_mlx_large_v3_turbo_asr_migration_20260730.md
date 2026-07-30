# Book 2B MLX Large-v3-turbo ASR Migration Revalidation

Status:
`MLX_LARGE_V3_TURBO_RAW_ASR_FAIL_PACKAGE_V2_MIGRATION_BLOCKED`

The materially distinct MLX Whisper large-v3-turbo lane completed against the
exact approved `book-2b9853ec52` audio. It emitted predominantly Bengali
script and improved the best completed raw score, but it did not approach the
unchanged objective release gate.

## Identity and license

- Conversion repository: `mlx-community/whisper-large-v3-turbo`
- Conversion revision: `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb`
- Weights SHA-256:
  `951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6`
- Weights size: `1,613,977,612` bytes
- Upstream: `openai/whisper-large-v3-turbo`
- Upstream revision: `41f01f3fe87f28c78e2fbf8b568835947dd65ed9`
- Upstream license: MIT
- Runtime: `mlx-whisper 0.4.3`, MIT

The conversion is public and ungated, and its architecture matches
large-v3-turbo. Its card omits explicit license and base-model metadata, so
the recorded decision is deliberately limited to private QA using the verified
MIT upstream basis. No model or runtime artifact is committed.

## Exact result

| Gate | Required | Result |
| --- | ---: | ---: |
| Raw ASR/manuscript score | 9.7 | 3.3775 |
| Exact token coverage | 0.98 | 0.3377 |
| First boundary | PASS | FAIL |
| Last boundary | PASS | FAIL |

Additional measurements:

- Character similarity: `0.7725`
- Token-order similarity: `0.3666`
- Bengali characters: `1,973`
- Devanagari characters: `47`
- Full-audio runtime: `127.624` seconds
- Transcript SHA-256:
  `2fe1c55562589f58f9e7372df409d22c69d01c3d68384dbcbaec6457972c36eb`
- Diagnostic phonetic projection: `7.596`; it cannot replace the raw gate.

The first invocation requested beam search and stopped before decoding because
`mlx-whisper 0.4.3` does not implement a beam decoder. The single bounded
compatibility repair used the runtime-supported temperature-zero greedy
decoder with the same model, audio, Bengali language, and no manuscript
prompt.

## Release decision

Package-v2 promotion remains blocked. The existing approved legacy audiobook
and public catalog truth remain unchanged. No provider call, paid call, TTS,
audio regeneration, upload, release-gate mutation, catalog mutation, or
`paid_tts.lock` operation occurred.
