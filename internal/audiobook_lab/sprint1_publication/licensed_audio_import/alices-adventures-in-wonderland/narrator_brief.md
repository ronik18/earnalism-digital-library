# Narration / Import Brief: Alice's Adventures in Wonderland

- Slug: `alices-adventures-in-wonderland`
- Author: Lewis Carroll
- Language: `English (en)`
- Candidate kind: `licensed_audio_import`
- Source hash: `49c44704fee971be4aff3b6ebf4764b9aabf0c1f338ca72942216a301205bd8d`
- Sanitized manuscript SHA-256: `868c0ce92dba1c9821e38a940732aab8c5aa69fa0e6136c5350e1fae91a4d7bd`
- Public audio state: `AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES`

Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.
Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.

## Pronunciation Checklist

- [ ] Alice's Adventures in Wonderland
- [ ] Lewis Carroll
- [ ] Recurring names/terms: Adventures, After, Alice, Alice’s, All, And, Ann, Are, Beau, Beautiful, Bill, Bill’s
- [ ] Confirm every proper noun and period-specific term before recording; preserve the written form.

## Style And Performance

- Use clear literary English with natural dialogue changes and deliberate punctuation pauses.
- Preserve period diction, irony, tension, and humor without melodrama or character caricature.
- Do not paraphrase names, quoted speech, spelling, or narrative transitions.
- Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.

## Chapter Boundaries

- `chapter-001.json` / CHAPTER I: 11511 characters; `104b7e3c2477c11fdc4e40b3fb9a12076626f568fb7aaa167f8523c9d102850d`
- `chapter-002.json` / CHAPTER II. The Pool of Tears: 11039 characters; `6c6f2b8bc11d718232094298818bac6b323ad608141fa6f82fb928f28227c5fc`
- `chapter-003.json` / CHAPTER III: 9291 characters; `c50c5aefd1a01b9be1a2d5b40f87dc7ea673860f1fbffe7b6fd82b25407bcc08`
- `chapter-004.json` / CHAPTER IV: 14044 characters; `761d82ed79944f4da40c4d397b38afac3cfc94597a1fdc31807333e6da5b41c2`
- `chapter-005.json` / CHAPTER V: 11978 characters; `8305040604b29175dd8c29a553f9e6b8db34bedbc00f3a06a3cd878ab920770e`
- `chapter-006.json` / CHAPTER VI: 13963 characters; `cd589a3daec2bf869814f848044cd88eb6c46180b224153d3a8c0f077bad5894`
- `chapter-007.json` / CHAPTER VII. A Mad Tea-Party: 12776 characters; `21306464b88f0206b688b6e8a095e04aaa2c4486205d31217634c694b26c3d4c`
- `chapter-008.json` / CHAPTER VIII. The Queen’s Croquet-Ground: 13786 characters; `41dbcdb545ee4e39a2a66c66f0f5763ef7c0a9e7510938afdf3219a1ad7a5d5b`
- `chapter-009.json` / CHAPTER IX. The Mock Turtle’s Story: 12724 characters; `9eb262d5d18b68081aa87e2f2b2f2017d04b70d759ce6efdc31b9606217ba284`
- `chapter-010.json` / CHAPTER X. The Lobster Quadrille: 11472 characters; `1f0aafded3a9f082d417a271c62ee3e88418b6e0d1dfba3c102c7e334424099e`
- `chapter-011.json` / CHAPTER XI: 10471 characters; `fb900ae7a9d3eaab2eb9ef5753ec64b1e9e7d288b7809699d46fc598ff6f601f`
- `chapter-012.json` / CHAPTER XII. Alice’s Evidence: 11712 characters; `e3af4d59424d8218c50902efb4e1c352d2132991c0029f363c847cbb4cbd4764`

Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.

## Exact Validation Command After Received Audio

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug alices-adventures-in-wonderland --candidate-kind licensed_audio_import --asset-root . --output-root internal/audiobook_lab/sprint1_publication/licensed_audio_import --received-audio /absolute/path/to/received_narration.wav`
