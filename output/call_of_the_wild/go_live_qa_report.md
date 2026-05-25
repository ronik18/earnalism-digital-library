# The Call of the Wild Go-Live QA

- QA passed: `True`
- Published before: `False`
- Published after: `True`

## Gates
- [x] human approval gate: PUBLISH_LIVE=1 and HUMAN_APPROVED=1 for requested go-live
- [x] book identity: The Call of the Wild by Jack London
- [x] covers present: front and back covers present
- [x] chapter count: 7 chapters found
- [x] chapter titles: chapter titles match canonical seven-chapter structure
- [x] no empty chapters: Chapter I. Into the Primitive=3780 words, Chapter II. The Law of Club and Fang=3335 words, Chapter III. The Dominant Primordial Beast=5183 words, Chapter IV. Who Has Won to Mastership=3233 words, Chapter V. The Toil of Trace and Trail=5409 words, Chapter VI. For the Love of a Man=4805 words, Chapter VII. The Sounding of the Call=6256 words
- [x] substantial chapters: all chapters exceed 1,000 words
- [x] no duplicate chapter titles: chapter titles are unique
- [x] chapter VII restored: Chapter VII has readable content
- [x] no source boilerplate in reader-facing content: forbidden source/repository terms absent from reader-facing payload
- [x] audiobook disabled: audiobook_enabled=False generate_audiobook=False
- [x] commercial rights validation: public-domain rights passed importer validation; source evidence kept internal

## Chapters
- Chapter I. Into the Primitive: 3780 words, 21648 HTML chars
- Chapter II. The Law of Club and Fang: 3335 words, 19173 HTML chars
- Chapter III. The Dominant Primordial Beast: 5183 words, 29703 HTML chars
- Chapter IV. Who Has Won to Mastership: 3233 words, 18371 HTML chars
- Chapter V. The Toil of Trace and Trail: 5409 words, 31091 HTML chars
- Chapter VI. For the Love of a Man: 4805 words, 27733 HTML chars
- Chapter VII. The Sounding of the Call: 6256 words, 35920 HTML chars

## Smoke
- Public API: `200`
- Public API chapters: `7`
- Admin empty chapters after publish: `[]`
- Book page: `200`
- Reader page: `200`
