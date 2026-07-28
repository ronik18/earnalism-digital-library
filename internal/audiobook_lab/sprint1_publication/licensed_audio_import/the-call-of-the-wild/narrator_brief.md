# Narration / Import Brief: The Call of the Wild

- Slug: `the-call-of-the-wild`
- Author: Jack London
- Language: `English (en)`
- Candidate kind: `licensed_audio_import`
- Source hash: `e446f6fca02fb231d502760a82af57631256a51631c55421fb4a6c4891daf78a`
- Sanitized manuscript SHA-256: `4b029c10c8cff516ed6f07f1928e55775ed7fd8d3d03dcf61f7ace0c55e8aa90`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] The Call of the Wild
- [ ] Jack London
- [ ] Recurring names/terms: After, Again, Alaska, All, Also, And, Another, Arctic, Barge, Barracks, Barrens, Bay
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / Chapter I. Into the Primitive: 20852 characters; `6ea8f908301e78416b40583c2c62e822463a20e841e52a6496b5e0388eb31124`
- `chapter-002.json` / Chapter II. The Law of Club and Fang: 18545 characters; `98127e9f574ecae3026499e0769a680854598689d26dbc93a19f5008251c05a7`
- `chapter-003.json` / Chapter III. The Dominant Primordial Beast: 28717 characters; `b4264259c059d87d53535b1aabd00f00c70779cd5001fafd1edf0646a8ffaf8e`
- `chapter-004.json` / Chapter IV. Who Has Won to Mastership: 17730 characters; `a965824fe166c058d5bf74b6bb62caa5e3ea2c0d913fb7a83d46a697ddd7a101`
- `chapter-005.json` / Chapter V. The Toil of Trace and Trail: 29977 characters; `3a23f434c7742466496005457bd83b847ee8655c2e4fa926109140ba670bcfad`
- `chapter-006.json` / Chapter VI. For the Love of a Man: 26731 characters; `309bebb9c1ff96b56842f848e0f56032d1198552af856d1d4941f7365e9b87fc`
- `chapter-007.json` / Chapter VII. The Sounding of the Call: 34740 characters; `a0f7e7ed798258e92dbbeca9091e0009a9f39b2458b60585bb1b1d3ed0b74191`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-call-of-the-wild --candidate-kind licensed_audio_import --asset-root . --output-root internal/audiobook_lab/sprint1_publication/licensed_audio_import --received-audio /absolute/path/to/received_narration.wav`
