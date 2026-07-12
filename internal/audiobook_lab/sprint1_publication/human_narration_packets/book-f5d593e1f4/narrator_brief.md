# Narration / Import Brief: রামকানাইয়ের নির্বুদ্ধিতা

- Slug: `book-f5d593e1f4`
- Author: রবীন্দ্রনাথ ঠাকুর
- Language: `Bengali (ben)`
- Candidate kind: `human_narration`
- Source hash: `f4bd2ecf4d9eb2dc5e3917bc45965c768463a34d9ced5f1dfe1e1f336b300827`
- Sanitized manuscript SHA-256: `94aa1e3f4446f201905cd31429d5ee1e61eecc227df548ddaf6ad6539843260e`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] রামকানাইয়ের নির্বুদ্ধিতা
- [ ] রবীন্দ্রনাথ ঠাকুর
- [ ] Mark every uncertain proper noun, archaic সাধু form, Sanskrit-derived word, and regional form before recording.
- [ ] Preserve Bengali vowel length, conjunct consonants, and written spelling; do not Anglicize names.

## Style And Performance

- Use idiomatic Bengali phrasing with measured literary pacing and natural sentence-final cadence.
- Keep সাধু or archaic diction intact; do not modernize, paraphrase, translate, or flatten the register.
- Differentiate dialogue lightly without caricature; preserve satire, irony, and emotional restraint.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed punctuation, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / Full Text: 9411 characters; `94aa1e3f4446f201905cd31429d5ee1e61eecc227df548ddaf6ad6539843260e`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug book-f5d593e1f4 --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
