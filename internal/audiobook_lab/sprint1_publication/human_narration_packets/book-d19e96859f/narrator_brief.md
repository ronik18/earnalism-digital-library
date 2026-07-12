# Narration / Import Brief: গিন্নি

- Slug: `book-d19e96859f`
- Author: রবীন্দ্রনাথ ঠাকুর
- Language: `Bengali (ben)`
- Candidate kind: `human_narration`
- Source hash: `44ddaba6e31e687d4eddeb70223d42ac78ab5240db01e4b7d77e8a7ca2e4c8ce`
- Sanitized manuscript SHA-256: `013a0c4f7ac3e2e4fdbe80732c951c728d6d8e231e278a1ce856a66c87925c77`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] গিন্নি
- [ ] রবীন্দ্রনাথ ঠাকুর
- [ ] Mark every uncertain proper noun, archaic সাধু form, Sanskrit-derived word, and regional form before recording.
- [ ] Preserve Bengali vowel length, conjunct consonants, and written spelling; do not Anglicize names.

## Style And Performance

- Use idiomatic Bengali phrasing with measured literary pacing and natural sentence-final cadence.
- Keep সাধু or archaic diction intact; do not modernize, paraphrase, translate, or flatten the register.
- Differentiate dialogue lightly without caricature; preserve satire, irony, and emotional restraint.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed punctuation, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / Full Text: 6452 characters; `013a0c4f7ac3e2e4fdbe80732c951c728d6d8e231e278a1ce856a66c87925c77`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug book-d19e96859f --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
