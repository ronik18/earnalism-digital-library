# Narration / Import Brief: Désirée's Baby

- Slug: `dsires-baby`
- Author: Kate Chopin
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `2006e24206b918744a8a8a7589e883389759ccd9cbef93ae8ce260d633dab5d9`
- Sanitized manuscript SHA-256: `0d6836a211ade599274d1a4b97d4081dc2ae0fb8b74301de3617c6a74d17bd98`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] Désirée's Baby
- [ ] Kate Chopin
- [ ] Recurring names/terms: And, Armand, Aubigny, Aubigny’s, Blanche’s, But, Come, For, God, Look, L’Abri, Madame
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / Désirée's Baby: 11973 characters; `0d6836a211ade599274d1a4b97d4081dc2ae0fb8b74301de3617c6a74d17bd98`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug dsires-baby --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
