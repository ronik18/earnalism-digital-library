# Narration / Import Brief: The Gift of the Magi

- Slug: `the-gift-of-the-magi`
- Author: O. Henry
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `490b76d444db0d952f5286f60c4ec2834ab91731d47e42dc94a3639d9183d295`
- Sanitized manuscript SHA-256: `be7f050f1affc65144172ae7157ad10ab8a8ee698e196623ff072fe410f4ec5e`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Gift of the Magi
- [ ] O. Henry
- [ ] Recurring names/terms: And, But, Christmas, Dell, Della, Della’s, Dillingham, Don’t, For, Give, Had, Her
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / The Gift of the Magi: 11298 characters; `be7f050f1affc65144172ae7157ad10ab8a8ee698e196623ff072fe410f4ec5e`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-gift-of-the-magi --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
