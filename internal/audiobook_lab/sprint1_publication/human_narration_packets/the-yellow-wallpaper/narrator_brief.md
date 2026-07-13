# Narration / Import Brief: The Yellow Wallpaper

- Slug: `the-yellow-wallpaper`
- Author: Charlotte Perkins Gilman
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `ef4b3a11042ebd451e1abc73007c6d5f5fb9910ab2571db97d33457f1ddcfa00`
- Sanitized manuscript SHA-256: `2dfdf07425d74f291d57ce25a755b373aef59c2066804b0b2c4c98ba7f9b6cc3`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Yellow Wallpaper
- [ ] Charlotte Perkins Gilman
- [ ] Recurring names/terms: And, Besides, But, Cousin, For, Henry, How, I’m, I’ve, Jennie, John, John’s
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / The Yellow Wallpaper: 31777 characters; `2dfdf07425d74f291d57ce25a755b373aef59c2066804b0b2c4c98ba7f9b6cc3`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-yellow-wallpaper --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
