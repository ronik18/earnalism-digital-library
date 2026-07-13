# Narration / Import Brief: The Cop and the Anthem

- Slug: `the-cop-and-the-anthem`
- Author: O. Henry
- Language: `English (en)`
- Candidate kind: `human_narration`
- Source hash: `e1e65254ba428e929553edaef131babdf3a2cba3ee18acf61d0c2cd81fa2e45b`
- Sanitized manuscript SHA-256: `77a6d1c7ff6162cc7aad47b950666c6bb1dedf0beb55a08f3f476e27e57bd3ab`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Cop and the Anthem
- [ ] O. Henry
- [ ] Recurring names/terms: And, Avenue, Broadway, But, Don’t, For, Island, Jack, Madison, Sabbath, Soapy, Soapy’s
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / The Cop and the Anthem: 13232 characters; `77a6d1c7ff6162cc7aad47b950666c6bb1dedf0beb55a08f3f476e27e57bd3ab`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-cop-and-the-anthem --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
