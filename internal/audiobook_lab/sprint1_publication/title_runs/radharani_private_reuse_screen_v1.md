# Radharani private reuse screen v1

## Outcome

Radharani is the highest-probability next Sprint 1 Bengali canary, but the retained historical MP3 is **not release eligible**. It remains private and production remains reader-live/audio-hidden.

The source-bound Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing` representative audition passed at `9.4`, confidence `0.95`, with no fatal flags. That proves the selected arm is suitable for one guarded full-title canary; it does not validate a different historical recording.

## Canonical binding

- Slug: `radharani`
- Title: `রাধারাণী`
- Author: `বঙ্কিমচন্দ্র চট্টোপাধ্যায়`
- Chapters: `8`
- Canonical characters: `38,022`
- Canonical source SHA-256: `53b00ba494263f54f97c8c94bb64ed6e07e1819fc8060aafee90f57ea5a9541d`
- Source hash: `e29154e89183d17245392bca25de332e4f58420c0977ba795d081a5ca36ae65e`
- Rights and sanitation: PASS
- Front/back cover audit: PASS

## Retained candidate identity

The private B2 object was downloaded to a private temporary path and matched the expected SHA-256 `4de991f9afc420037ec09683aa4b53e4e62de8a4ae782ebdfb766ec48bb18a56`. It is a 3,586.200136-second, mono 22,050 Hz MP3. The checksum proves asset identity only.

Retained metadata says `provider=command` and `voice/model=bn-IN-TanishaaNeural`. No checksum-bound paid Azure subscription or generation-transaction evidence was found. Microsoft voice terms cannot be inferred onto this exact candidate from a voice name alone.

## Objective screen

A bounded 60-second multilingual Whisper-medium Bengali screen partly recognized the opening phonetically, shifted into Devanagari, then collapsed into repeated Bengali characters. The result is classified `OFFLINE_ASR_TOOL_INADEQUATE_NOT_SOURCE_MISMATCH`: it is not evidence of a wrong book, and it cannot support the mandatory audio-derived ASR/source score of `9.7`.

The retained sidecars also cannot pass release sync: existing cues contain empty entries and the fallback manifest uses estimated timing. Estimated sync is blocked by policy.

## Release decision

No upload, public metadata mutation, Listen exposure, or publication occurred. Exact remaining blockers are:

1. Exact historical recording voice-rights/provenance evidence is missing.
2. Full audio-derived ASR/source `>=9.7`, first/last words, and ordered-content integrity are unproven.
3. Measured paragraph/stanza sync is missing.
4. Full six-sample listening QA is missing.
5. Upload, metadata, endpoint, and browser gates have not run.

The cheapest safe path is one fresh, source-bound Radharani full-title canary with the passed Sarvam arm after all explicit campaign budget/approval variables are present and `paid_tts.lock` is idle and scoped to `radharani`. The current lock is scoped to Nishkriti and remained byte-identical at SHA-256 `f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3`. Publication remains forbidden unless every gate passes.

## Next exact command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_next_two_audiobook_fastpath.py --asset-root /private/tmp/earnalism-bengali-go-live --lock-path /Users/ronikbasak/Documents/GitHub/earnalism-digital-library/internal/earnalism_intelligence/locks/paid_tts.lock --candidate-slugs radharani --max-new-publications 1 --reuse-first --fail-closed
```

With the current missing campaign variables and Nishkriti-only lock scope, this command is intentionally a fail-closed preflight and starts no provider call.
