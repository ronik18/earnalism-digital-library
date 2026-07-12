# The Open Window Stage 2C Non-Paid Preflight

Generated: `2026-07-12`

## Current Truth

- Production book API: `HTTP 200`, reader enabled.
- Production reader manifest: `HTTP 200`, one chapter, audio disabled.
- Source rights: `PASS`.
- Sanitized text: `PASS`, 6,919 characters and 1,229 words.
- Existing private asset: 389.573 seconds, SHA-256 `5b9dfb75aa7dbda9af79553cef3164979b248e8e9502b69d6c8a58c6e0286aed`.
- Existing provider: `piper`; alignment mode: `synthetic`.
- Public audiobook: `NO`.

## Diagnosis

The historical `2.7796` ASR score used the former character-only verifier. Current non-paid re-evaluation scores `9.7826`. The spoken title intro is legitimate audiobook text but is absent from the canonical reader manuscript; a title-prefixed audio manuscript makes both first and last boundaries pass.

The asset still cannot be released because Piper is disallowed public-audio provenance and the synthetic sidecar is not measured release-grade synchronization. No paid provider call ran for this title.

## Next Action

After Google ADC is repaired, run one bounded literary-voice representative audition from the sanitized text. Do not expose the historical Piper asset.

```sh
gcloud auth application-default login
```
