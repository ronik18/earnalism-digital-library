# Audiobook Model Bake-Off Human Review Form

Scope: `INTERNAL_REVIEW_ONLY`.

Book: `kshudhita-pashan`

Default approval state:

- owner_approved_model = false
- public_preview_approved = false
- full_audiobook_approved = false

## Review Grid

| Model | Chunk | Bengali pronunciation | Naturalness | Punctuation timing | Gothic mood | Emotion subtlety | No robotic artifacts | Listening comfort | Consistency | Brand luxury | Commercial readiness | Blockers |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Svara-TTS v1 | representative chunks |  |  |  |  |  |  |  |  |  |  |  |
| MahaTTS/MahaTTSv2 | representative chunks |  |  |  |  |  |  |  |  |  |  |  |
| AI4Bharat Indic-TTS | representative chunks |  |  |  |  |  |  |  |  |  |  |  |
| F5-TTS | representative chunks |  |  |  |  |  |  |  |  |  |  |  |

## Blocking Rules

- Pronunciation below `8.5` blocks model.
- Naturalness below `8.5` blocks model.
- Emotion subtlety below `8.5` blocks model.
- Fake/cartoonish sobbing or laughter blocks model.
- Public preview candidate requires average `>= 9.2`.
- Full audiobook candidate requires average `>= 9.5`.
- `10/10` requires owner human review approval.

## Owner Decision

- owner_approved_model = false
- public_preview_approved = false
- full_audiobook_approved = false

Required edits:

- 
