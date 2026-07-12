# Sprint 1 Parallel Yes+Yes Execution Log

Generated: `2026-07-12T19:35:15Z`

## Coordinator

- Baseline: `origin/main` at `ed42790` in isolated branch `codex/sprint1-parallel-publication`.
- Active target set: 32 titles; reader-public 32; public audiobook 2; audio-hidden 30.
- Paid execution policy: serialized through the existing `paid_tts.lock`; parallel workers are non-paid/read-only.
- Live shell: every required Sprint, TTS, ASR, and listening-QA budget/approval variable is missing.
- Credentials: Sarvam, OpenAI, Google credentials, Google project, and Google ADC are available; ElevenLabs and Azure Speech credentials are absent.
- Lock: preflight PASS, active, current holder `none`, allowed next holders `[]`, SHA-256 `ab57e15c5329256304014ea8a77e086b7ec5748a0fee6423f772f350ef58b50e`.

## Parallel Lanes

1. Approved audio guard: `book-2b9853ec52`, `a-ghost-story`.
2. Short Bengali: `book-d19e96859f`, `book-f5d593e1f4`, `muchiram-gurer-jibanchorit`, `radharani`, `nishkriti`.
3. Short English: The Open Window plus eleven short English targets.
4. Medium/long English: nine active novels, preflight only until short-title stability and coordinator approval.
5. Bengali long/repair: `bn-066`, `devdas`, `pather-panchali`, `book-edfcf810c5`.
6. Production release-truth validation.

## Executed Work

- Ran the `book-d19e96859f` lock-safe wrapper in non-paid preflight mode.
- Source, rights, sanitation, cover, reader, and representative audition gates passed.
- Prepared manuscript: 6,485 characters, 998 words, five groups, SHA-256 `79b0deba6032c36ab919e4ef4786fc62aa55c9c53c328dfbcf49f03a0f7d05fe`.
- Selected arm: Sarvam `bulbul:v3` / `pooja` / `dialogue_human_touch`; representative score `9.4`, confidence `0.95`, no fatal flags.
- Estimated D19 repair pipeline: TTS `$0.0389`, ASR `$0.0544`, listening QA `$0.0500`, total `$0.1433`.
- The wrapper stopped before lock acquisition and before provider access because required runtime gates are missing.
- Provider calls: zero. New estimated/actual spend: `$0.00`. Public release mutations: zero.

## Current Decision

The parallel non-paid lanes continue, but paid generation is fail-closed. No title receives public audio merely from a representative sample, private asset, or plan. The first serialized paid action remains the bounded D19 wrapper after the exact inline gates are supplied.

## Completed Lane Findings

- Medium/long English: all nine readers return public content, but no representative audition has run. The conditional remaining estimate is `$85.7074`; Alice, Call of the Wild, and Time Machine cannot reuse private audio until the files, hashes, and chapter structure are proven.
- Bengali long/repair: all four readers remain live/audio-hidden. The private `bn-066` workspace produced a six-call dry-run calibration plan at `$0.1047`; no call ran. The calibration harness and private asset are absent from `main`.
- `pather-panchali` remains `EXTERNAL_ACTION_REQUIRED_OWNER_DOCUMENT` until complete source scope, derivative-audio rights, cover provenance/approval, owner signature, and rollback evidence are supplied.

## Release-Truth Repairs

- Production timestamps for both approved audiobooks use `start`/`end` seconds. Reader playback consumed `start_ms`, selected terminal cues, and stopped. The frontend now normalizes both schemas.
- Browser QA previously passed on metadata readiness alone. It now clicks the enabled narration control and requires playback time to advance.
- Eight blocked controlled-publication packets contained 88 direct storage URL occurrences. The repo packets are scrubbed without changing reader access or approving audio.
- Cloudinary/B2 credentials are absent, so remote object revocation remains an explicit external action.
- Legacy `/audio/*` requests now route to removed-content instead of receiving SPA HTML with immutable audio cache headers.
- All six sub-agents completed. No sub-agent edited source, called a provider, acquired the lock, published, or deployed.
