# Narration / Import Brief: The Open Window

- Slug: `the-open-window`
- Author: Saki
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `a107f7212542030d90e15e1b7daeeee6dcef9a77ea18887ce009afbf61457078`
- Sanitized manuscript SHA-256: `f43d04cc2097668e91190ada89e283ad4908c360c4d7f6011a44b8f83d9659be`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Open Window
- [ ] Saki
- [ ] Recurring names/terms: Bertie, Framton, Her, Mrs, Nuttel, Poor, Sappleton
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / The Open Window: 6918 characters; `f43d04cc2097668e91190ada89e283ad4908c360c4d7f6011a44b8f83d9659be`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-open-window --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
