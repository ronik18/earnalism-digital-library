# English Audiobook Model Research

Scope: Dracula internal audiobook model bake-off.

Current launch truth:

- Dracula is the only live approved Tier A core reading title.
- Dracula audio is disabled.
- No public audiobook, Listen Now CTA, full audiobook claim, or public audio URL may appear.
- No paid provider APIs, cloud APIs, uploads, or production data mutations are allowed by this PR.
- Generated audio, if created later by an explicitly approved local command, is INTERNAL_REVIEW_ONLY.

## Shortlist

| Model | Status | Reason |
| --- | --- | --- |
| Chatterbox TTS | PRIMARY_BENCHMARK | Expressive English narration and emotion/exaggeration controls; approved reference/style voice required. |
| Dia | DRAMATIC_DIALOGUE_BENCHMARK | Useful for dialogue and nonverbal-tag experimentation; license review required. |
| Kokoro 82M | FAST_BASELINE | Lightweight local baseline for speed and chunking iteration. |
| F5-TTS | RESEARCH_ONLY_LICENSE_CHECK_REQUIRED | Useful research comparison, but pretrained weights are not commercial-approved. |
| XTTS-v2 | RESEARCH_ONLY_LICENSE_CHECK_REQUIRED | Voice-cloning baseline only; license and reference-voice governance required. |

## Benchmark Policy

- This PR benchmarks planning, chunking, adapter readiness, and QA workflow only.
- Local generation refuses to run unless `data/audiobook_governance/dracula.local_generation_approval.json` exists with local internal-review approval.
- No adapter executes subprocesses, network calls, or provider APIs in this PR.
- No real-person or celebrity imitation is allowed.
- No model is approved for public Earnalism audio.

## Dracula Fit Criteria

- Female literary narrator with warmth, clarity, and emotional restraint.
- Gothic atmosphere should be present but not melodramatic.
- Dialogue should be distinct without caricature.
- Diary entries should remain intimate and close to the page.
- Victorian punctuation and abbreviations should be normalized carefully for spoken clarity.

