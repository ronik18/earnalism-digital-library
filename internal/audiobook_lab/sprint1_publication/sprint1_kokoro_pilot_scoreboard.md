# Sprint 1 Kokoro pilot scoreboard

Generated: `2026-07-20T03:30:00Z`

This is private representative-pilot evidence, not full-title release evidence. The release cutoff is listening `>= 9.2`, confidence `>= 0.90`, no fatal flags, ASR/source `>= 9.7`, coverage `>= 0.98`, plus all full-title rights, sync, delivery, endpoint, browser, and publication gates. A `10/10` result is shown separately and is not fabricated.

| Title | Kokoro voice | Whisper ASR / coverage | Listening overall samples | Minimum / cutoff | Result |
| --- | --- | --- | --- | --- | --- |
| The Gift of the Magi | `af_bella` | representative `10.0 / 1.0` on all four; full title `9.9545 / 0.9952` aggregate but exact integrity failed | `9.6, 9.6, 9.5, 9.5` representative only | `9.5 / 9.2` | Full-title objective fail; 11/19 sections passed; configuration closed |
| The Cop and the Anthem | `af_bella` | `10.0 / 1.0` on all four | `8.7, 8.3, 9.5, 9.5` | `8.3 / 9.2` | Fail; configuration closed |
| Désirée's Baby | `af_bella` | repaired `10.0 / 1.0` on all four | not scorable: only one of four judgments transported audio | n/a | Fail; audible sample raised four fatal narration flags; transport-invalid zeroes are not quality scores |
| The Necklace | `af_sarah` | `9.9631/0.9926, 10.0/1.0, 10.0/1.0, 9.8605/0.9815` | not run | n/a | Fail; exact ordered source integrity remained broken after bounded repair |
| The Last Leaf | `af_sarah` | `10.0/1.0, 9.8611/0.9861, 8.6957/0.8642, 10.0/1.0` | not run | n/a | Fail; two passages retained exact source substitutions after bounded repair |

Toolchain: local Kokoro `0.9.4` / `hexgrad/Kokoro-82M` at revision `f3ff3571791e39611d31c381e3a41a3af07b4987`, local Whisper `medium.en`, and independent OpenAI `gpt-audio` listening judgments where objective gates passed. Local synthesis and ASR cost `$0.00`; each four-sample listening run was capped at `$0.20`, with actual billing not reported.

Production remains fail-closed. The four approved titles return `206`: `book-2b9853ec52`, `a-ghost-story`, `sredni-vashtar`, and `the-open-window`. Sampled hidden titles Gift, Cop, Désirée, Tell-Tale Heart, and Monkey's Paw return `404`. The Open Window is live on listening `9.4`, ASR/source `10.0`, coverage `1.0`, measured paragraph sync `10.0`, confidence `0.95`, and no fatal flags; no public `10/10` listening claim is made.
