# Narration / Import Brief: Sredni Vashtar

- Slug: `sredni-vashtar`
- Author: Saki
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `089628df1446736886ddae93252fc070854ec17606ade714a70ba77b55e6ea02`
- Sanitized manuscript SHA-256: `7d3a52056069e59d30cc15d474a3612479800dc01345f06719447b060a54fe94`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] Sredni Vashtar
- [ ] Saki
- [ ] Recurring names/terms: Anabaptist, And, But, Conradin, Conradin's, His, Houdan, Mrs, Ropp, Sredni, Such, Vashtar
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / Sredni Vashtar: 10370 characters; `7d3a52056069e59d30cc15d474a3612479800dc01345f06719447b060a54fe94`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug sredni-vashtar --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
