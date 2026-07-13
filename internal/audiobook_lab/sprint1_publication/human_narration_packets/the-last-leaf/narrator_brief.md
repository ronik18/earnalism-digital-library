# Narration / Import Brief: The Last Leaf

- Slug: `the-last-leaf`
- Author: O. Henry
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `3b86fb4d8aae47c9471240ba708f681dc16aec5b34d97976faa9a642339290ba`
- Sanitized manuscript SHA-256: `e3a825f58d8a086967586988d7eeaf902fbb415b53cd164340d935f98d7645f7`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Last Leaf
- [ ] O. Henry
- [ ] Recurring names/terms: And, Bay, Behrman, But, California, Didn’t, Don’t, Dutch, For, Gott, Has, I’ll
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / The Last Leaf: 12935 characters; `e3a825f58d8a086967586988d7eeaf902fbb415b53cd164340d935f98d7645f7`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-last-leaf --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
