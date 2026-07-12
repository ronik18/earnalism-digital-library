# Narration / Import Brief: মুচিরাম গুড়ের জীবনচরিত

- Slug: `muchiram-gurer-jibanchorit`
- Author: বঙ্কিমচন্দ্র চট্টোপাধ্যায়
- Language: `Bengali (ben)`
- Candidate kind: `human_narration`
- Source hash: `733466ffdadc8f5c0172023edd5c0ba7327387d65d0c46b1b881a26e303e800a`
- Sanitized manuscript SHA-256: `0e9455b19181966cd83886298b223030bd427f8e9c54aaaafd69aba4c0b743e6`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] মুচিরাম গুড়ের জীবনচরিত
- [ ] বঙ্কিমচন্দ্র চট্টোপাধ্যায়
- [ ] Mark every uncertain proper noun, archaic সাধু form, Sanskrit-derived word, and regional form before recording.
- [ ] Preserve Bengali vowel length, conjunct consonants, and written spelling; do not Anglicize names.

## Style And Performance

- Use idiomatic Bengali phrasing with measured literary pacing and natural sentence-final cadence.
- Keep সাধু or archaic diction intact; do not modernize, paraphrase, translate, or flatten the register.
- Differentiate dialogue lightly without caricature; preserve satire, irony, and emotional restraint.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed punctuation, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / Chapter 1. প্রথম পরিচ্ছেদ: 3708 characters; `2da278011f7705b08e941479981aa83558e56b1c6a3d40f30b14fb8a6f23092e`
- `chapter-002.json` / Chapter 2. দ্বিতীয় পরিচ্ছেদ: 2260 characters; `9c57d79295766ee6651f2193a7d5266e5cfd816ace6621fbe77211cb8240df28`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug muchiram-gurer-jibanchorit --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
