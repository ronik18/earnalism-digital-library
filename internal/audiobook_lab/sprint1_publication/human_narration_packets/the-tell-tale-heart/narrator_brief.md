# Narration / Import Brief: The Tell-Tale Heart

- Slug: `the-tell-tale-heart`
- Author: Edgar Allan Poe
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `f5d856baf4abec894c1fdc82f8676a416dc96efd3708162c04bcde0ff0a4579b`
- Sanitized manuscript SHA-256: `df1b85c210aab99b3b14c106e0a28c4305e7c4dbc8aa16aa11f1877bb9502981`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Tell-Tale Heart
- [ ] Edgar Allan Poe
- [ ] Recurring names/terms: And, But, For, God, His, Now, Yes, Yet, You
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / The Tell-Tale Heart: 11319 characters; `df1b85c210aab99b3b14c106e0a28c4305e7c4dbc8aa16aa11f1877bb9502981`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-tell-tale-heart --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
