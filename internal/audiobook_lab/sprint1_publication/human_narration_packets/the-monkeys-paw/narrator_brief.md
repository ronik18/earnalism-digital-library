# Narration / Import Brief: The Monkey's Paw

- Slug: `the-monkeys-paw`
- Author: W.W. Jacobs
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `e435de0511bd61d2373a445b0c5e054b747072357b5373e27b7a4b8a5b40cd01`
- Sanitized manuscript SHA-256: `993ea84df5163bddcb4d4579a78ee5fb4b5ad9002a9659f9ac2e2f73198ec6b7`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Monkey's Paw
- [ ] W.W. Jacobs
- [ ] Recurring names/terms: And, Better, But, Come, Get, God, Her, Herbert, His, How, India, It’s
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / I: 9629 characters; `1184a3e5b2d86508fc2c6bceac7519235581387e02e31a2c2dbfab03628ac942`
- `chapter-002.json` / II: 5330 characters; `d0eafaa9c6af9c96bd56ce956a8f59ba94da1ec9e19b3e6cf38b4f8b206cc9ee`
- `chapter-003.json` / III: 7112 characters; `7ad74f2ca75e5d2e5f1dbc0a43c440f9fb510cbcc32e739ec634b0cc21b30758`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-monkeys-paw --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
