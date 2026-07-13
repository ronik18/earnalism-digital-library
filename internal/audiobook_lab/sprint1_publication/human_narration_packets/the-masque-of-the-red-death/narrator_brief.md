# Narration / Import Brief: The Masque of the Red Death

- Slug: `the-masque-of-the-red-death`
- Author: Edgar Allan Poe
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `2264be57608b30c4af99db7b1d430accae5a7c4d9da738ac04651f7ef74bc266`
- Sanitized manuscript SHA-256: `c517483495ef7266f533d077036a8e83bba53dc33cac60580cd895e757f637e3`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Masque of the Red Death
- [ ] Edgar Allan Poe
- [ ] Recurring names/terms: And, But, Death, His, Prince, Prospero, Red, These
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / The Masque of the Red Death: 13885 characters; `c517483495ef7266f533d077036a8e83bba53dc33cac60580cd895e757f637e3`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-masque-of-the-red-death --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
