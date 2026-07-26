# Sprint 1 audiobook 9.0 cutoff impact report

Generated: 2026-07-26
Policy: `sprint1_audiobook_acceptance_v3_90`

## Decision

The owner-approved overall listening floor is `9.0` for new Sprint 1 Bengali
and English evaluations. Confidence remains `>= 0.90`; existing per-dimension
floors and fatal-flag rejection remain unchanged. Objective release gates
remain non-substitutable: ASR/manuscript `>= 9.7`, coverage `>= 0.98`, exact
opening/ending and order, measured sync, rights, covers, checksum-bound private
delivery, production metadata, ranged endpoint, browser playback, and an empty
blocker list.

No additional title becomes release-ready from this policy change. Production
truth remains 32 readers and four approved audiobooks.

## Reading the matrix

- `R-L` means best representative-sample listening evidence.
- `F-L` means full-title or full-package listening evidence.
- `R-ASR` and `F-ASR` mean representative and full-title audio-derived
  manuscript-match evidence.
- These values are not interchangeable. A representative sample cannot approve
  a full audiobook, and a listening score cannot compensate for failed source
  fidelity.

## Per-title impact

| # | Slug and canonical title | Best admissible evidence found | Current GO LIVE blocker | Customer impact of forced release |
|---:|---|---|---|---|
| 1 | `book-2b9853ec52` — দুই বিঘা জমি | F-L `9.4`, confidence `0.95`; live evidence passed | None; already approved and live | Healthy approved experience |
| 2 | `bn-066` — আনন্দমঠ | R-ASR `9.0625`, coverage `0.9062` | ASR/coverage and boundaries fail; listening, sync, and delivery absent | Missing or changed Bengali with unverified continuity |
| 3 | `radharani` — রাধারাণী | R-L `9.4`; retained full candidate raw ASR `1.0962` | Full-title fidelity, provenance, measured sync, and delivery fail | Pleasant excerpts could conceal major manuscript mismatch |
| 4 | `nishkriti` — নিষ্কৃতি | Best isolated R-L `9.5`; completed Sarvam set `9.4/5.5/0/0`, Gemini set `9.5/7.0/0/0` | Four-passage generalization and fatal-quality gates fail | A polished opening followed by robotic, mechanical, or unusable passages |
| 5 | `muchiram-gurer-jibanchorit` — মুচিরাম গুড়ের জীবনচরিত | R-L `9.3`; F-L `7.8`, confidence `0.85` | Full-title robotic/mechanical/list-reading quality failure | Strong opening followed by tiring mechanical sections |
| 6 | `book-d19e96859f` — গিন্নি | R-L `9.4`; R-ASR anchor `9.375`; retained F-L `8.0` | Fidelity below `9.7`; full-title list-reading failure | Misread or omitted Bengali plus list cadence |
| 7 | `book-f5d593e1f4` — রামকানাইয়ের নির্বুদ্ধিতা | R-L `7.8`; retained F-ASR `6.1988` | Listening and manuscript fidelity fail | Robotic narration of mismatched or unverifiable text |
| 8 | `pather-panchali` — পথের পাঁচালী / Pather Panchali | No admissible audio score | Exact rights/source/cover/audio release package absent | Broken or legally/provenance-unsupported audio |
| 9 | `devdas` — দেবদাস / Devdas | Best isolated R-L `9.4`; two Gemini sets `9.2/5.5/0/0` and `9.4/5.5/0/0` | Four-passage listening fails; matched cover pair and complete package absent | An attractive first clip followed by severe quality collapse |
| 10 | `book-edfcf810c5` — ক্ষুধিত পাষাণ | Best isolated R-L `9.5`; latest Gemini sets include `9.3/9.0/5.5/0`; retained F-ASR `7.0362` | Generalization and objective source fidelity fail; sync/delivery absent | Natural moments mixed with unusable or incorrect Bengali |
| 11 | `a-ghost-story` — A Ghost Story | F-ASR `9.88`; F-L `9.4`, confidence `0.95`; live | None; already approved and live | Healthy approved experience |
| 12 | `dracula` — Dracula | No audited full candidate | Full candidate, objective QA, sync, and delivery absent | Missing or unverified playback |
| 13 | `frankenstein` — Frankenstein | No admissible audio score | Candidate and all downstream evidence absent | Missing or unverified playback |
| 14 | `jekyll-and-hyde` — The Strange Case of Dr. Jekyll and Mr. Hyde | Source preparation only | Representative/full listening, objective QA, sync, and delivery absent | No customer-ready audiobook |
| 15 | `picture-of-dorian-gray` — The Picture of Dorian Gray | No admissible audio score | Candidate and all downstream evidence absent | Missing or unverified playback |
| 16 | `the-time-machine` — The Time Machine | R-ASR `10.0`; R-L `9.0`, confidence `1.0`; emotional expression `8.0` | Per-dimension listening floor fails; no full package | Accurate short clip but flat emotional delivery |
| 17 | `the-call-of-the-wild` — The Call of the Wild | No admissible audio score | Candidate and all downstream evidence absent | Missing or unverified playback |
| 18 | `white-fang` — White Fang | No admissible audio score | Candidate and all downstream evidence absent | Missing or unverified playback |
| 19 | `pride-and-prejudice` — Pride and Prejudice | No admissible audio score | Candidate and all downstream evidence absent | Missing or unverified playback |
| 20 | `the-secret-garden` — The Secret Garden | No admissible audio score | Candidate and all downstream evidence absent | Missing or unverified playback |
| 21 | `alices-adventures-in-wonderland` — Alice's Adventures in Wonderland | Stale direct audio was removed; no approved candidate | Exact release candidate and downstream gates absent | Broken playback or re-exposure of an unapproved object |
| 22 | `the-gift-of-the-magi` — The Gift of the Magi | R-L set minimum `9.5`; F-ASR `9.9545` but order fails | Sections 7, 17, and 18 have content/order errors; measured sync and delivery incomplete | Premium passages with omitted, substituted, or reordered sentences |
| 23 | `the-tell-tale-heart` — The Tell-Tale Heart | Best isolated R-L `9.6`; latest derivative F-L `9.0`, confidence `0.95`, F-ASR `9.8529` | Ordered content integrity fails; exact downstream package incomplete | Good excerpts but unreliable wording and continuity |
| 24 | `the-open-window` — The Open Window | F-ASR `10.0`; F-L `9.4`, minimum sample `9.2`; live | None; already approved and live | Healthy approved experience |
| 25 | `sredni-vashtar` — Sredni Vashtar | F-ASR `9.8426`; F-L `9.4`, confidence `0.95`; live | None; already approved and live | Healthy approved experience |
| 26 | `dsires-baby` — Désirée's Baby | R-ASR `10.0`; one transport-valid listening result `9.2` | Robotic/mechanical/choppy/fallback fatal flags; other evidence invalid | Accurate words with conspicuously synthetic joins |
| 27 | `the-cop-and-the-anthem` — The Cop and the Anthem | R-ASR `10.0` across four samples; R-L minimum `8.3`, confidence `0.85` | Listening and confidence fail; no full package | Accurate but uneven and non-premium narration |
| 28 | `the-last-leaf` — The Last Leaf | R-L minimum `8.4`; Kokoro fidelity passed only 2/4 samples | Name/dialect substitutions and listening failure | Mispronunciations and altered dialect |
| 29 | `the-masque-of-the-red-death` — The Masque of the Red Death | R-L minimum `8.4`; Kokoro integrity passed 1/4 samples | Missing/substituted content and trailing speech | Incomplete wording and distracting trailing audio |
| 30 | `the-yellow-wallpaper` — The Yellow Wallpaper | Representative set minimum L `8.4` | Listening plateau and no complete release package | Flat, non-premium narration |
| 31 | `the-monkeys-paw` — The Monkey's Paw | Repaired F-ASR `9.8519`; repaired F-L `8.4` | Listening fails; required B2 bytes/hash are unavailable or different | Either broken delivery or known poor-quality audio |
| 32 | `the-necklace` — The Necklace | R-L minimum `8.5`; Kokoro fidelity passed 2/4 samples | Missing/substituted words and listening failure | Noticeable wording errors and uneven narration |

## Net release effect

- Newly eligible on overall listening alone: isolated evidence for portions of
  `the-gift-of-the-magi` and `the-tell-tale-heart`.
- Newly full-title release-ready: `0`.
- Newly published: `0`.
- Safe public state: unchanged.

The quickest credible next repair is content-bound, not another cutoff change:
repair the exact ordered-content defects in `the-tell-tale-heart` or
`the-gift-of-the-magi`, rerun audio-derived ASR and six-sample full-title
listening on the repaired hash, then complete measured sync, private upload,
checksum, metadata, endpoint, and browser evidence.
