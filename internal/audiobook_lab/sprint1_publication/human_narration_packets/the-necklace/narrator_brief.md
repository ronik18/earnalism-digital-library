# Narration / Import Brief: The Necklace

- Slug: `the-necklace`
- Author: Guy de Maupassant
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `bc5f461772b5583801472773e623c39ee14a218ae50b87715e24aa14b026549c`
- Sanitized manuscript SHA-256: `0f4d8061191d56b12860a8997f26bd75939c766784b732a73526b8f8ccd00b7f`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Necklace
- [ ] Guy de Maupassant
- [ ] Recurring names/terms: All, And, But, Come, Every, Forestier, Her, How, Instruction, Loisel, Madame, Mathilde
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / The Necklace: 16092 characters; `0f4d8061191d56b12860a8997f26bd75939c766784b732a73526b8f8ccd00b7f`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-necklace --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
