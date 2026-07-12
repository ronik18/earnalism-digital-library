# Sprint 1 Publication Stage 2 Report

Generated: `2026-07-12T11:11:53Z`

## Outcome

- Sprint target: `INCOMPLETE`
- Current public readers: `32/32`
- Reader repairs merged/deployed from PR #101: `17`
- Current public audiobooks: `1/32`
- New public audiobooks: `0`
- Provider calls: bounded OpenAI selector, TTS, ASR, and listening-QA work for A Ghost Story only
- Estimated Stage 2B plus Stage 2C spend: `$2.3295`; actual provider billing was not reported
- Authorized budget remaining after estimate: `$172.6705`
- Remaining known queue estimate excluding the now-unknown A Ghost Story repair: `$97.5724`
- Production API: `32/32 book routes and 32/32 manifests HTTP 200`
- Production browser: `132/132 desktop/mobile checks pass`

## Reader Repair

PR [https://github.com/ronik18/earnalism-digital-library/pull/101](https://github.com/ronik18/earnalism-digital-library/pull/101) merged as `faf8587` and deployed to Railway as `4e190b99-acec-4755-83db-82cbe15bd852`. It restored 17 reader-only packets, stripped legacy audio approval/assets, and preserved the one-title audio allowlist. PR #102 then restored cache-header CORS and deployed as `9100d4d8-47b5-4859-94b5-9ca118cff32c`.

## Paid Gate

Stage 2B supplied every required cap in the same process and ran exactly six bounded OpenAI listening-QA judgments. The weakest middle sample scored `8.3`, below the owner minimum of `9.4`, so fail-closed policy blocked publication. No TTS, ASR, upload, deployment, or public release-state mutation occurred.

| slug | title | language | Publicly rendered book | Publicly available audiobook | Quality score | Evidence path | Cost used | Final status |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| `book-2b9853ec52` | দুই বিঘা জমি | Bengali | Yes | Yes | 9.4/10 listening, confidence 0.95; approved minimum passed, 10.0 not claimed | `internal/audiobook_lab/release_gate/book-2b9853ec52_20260707T053510Z/goliveevidence.json` | $0.0000 | Yes, publicly rendered book + Yes, publicly available audiobook |
| `bn-066` | আনন্দমঠ | Bengali | Yes | No | 0.8403/10 ASR-source; listening not run | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/bn-066.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `radharani` | রাধারাণী | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/radharani.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `nishkriti` | নিষ্কৃতি | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/nishkriti.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `muchiram-gurer-jibanchorit` | মুচিরাম গুড়ের জীবনচরিত | Bengali | Yes | No | 0.039/10 ASR-source; representative timed out | `internal/audiobook_lab/release_gate/muchiram-gurer-jibanchorit_20260705T150228Z/goliveevidence.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `book-d19e96859f` | গিন্নি | Bengali | Yes | No | 9.4/10 representative only; full-book source gate failed | `internal/audiobook_lab/release_gate/book-d19e96859f_20260705T150228Z/goliveevidence.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `book-f5d593e1f4` | রামকানাইয়ের নির্বুদ্ধিতা | Bengali | Yes | No | 9.4/10 representative only; full-book source gate failed | `internal/audiobook_lab/release_gate/book-f5d593e1f4_20260705T150741Z/goliveevidence.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `pather-panchali` | পথের পাঁচালী / Pather Panchali | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/pather-panchali.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `devdas` | দেবদাস / Devdas | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/devdas.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `book-edfcf810c5` | ক্ষুধিত পাষাণ | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/book-edfcf810c5.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `a-ghost-story` | A Ghost Story | English | Yes | No | ASR/source 9.928 PASS; first/last PASS; listening minimum 8.3, confidence 0.90, list-reading rhythm; FAIL | `internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_release_gate_evidence.json` | $2.3295 estimated; actual not reported | AUDIO_HIDDEN_ALTERNATE_PROVIDER_REPAIR_REQUIRED |
| `dracula` | Dracula | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/dracula.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `frankenstein` | Frankenstein | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/frankenstein.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `jekyll-and-hyde` | The Strange Case of Dr. Jekyll and Mr. Hyde | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/jekyll-and-hyde.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `picture-of-dorian-gray` | The Picture of Dorian Gray | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/picture-of-dorian-gray.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-time-machine` | The Time Machine | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-time-machine.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-call-of-the-wild` | The Call of the Wild | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-call-of-the-wild.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `white-fang` | White Fang | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/white-fang.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `pride-and-prejudice` | Pride and Prejudice | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/pride-and-prejudice.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-secret-garden` | The Secret Garden | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-secret-garden.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `alices-adventures-in-wonderland` | Alice's Adventures in Wonderland | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/alices-adventures-in-wonderland.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-gift-of-the-magi` | The Gift of the Magi | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-gift-of-the-magi.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-tell-tale-heart` | The Tell-Tale Heart | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-tell-tale-heart.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-open-window` | The Open Window | English | Yes | No | Non-paid ASR re-evaluation 9.7826 with title-prefixed audio manuscript; Piper/synthetic provenance blocked | `internal/audiobook_lab/sprint1_publication/title_runs/the-open-window_release_gate_evidence.json` | $0.0000 | AUDIO_HIDDEN_DISALLOWED_PIPER_PROVENANCE_REPLACEMENT_REQUIRED |
| `sredni-vashtar` | Sredni Vashtar | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/sredni-vashtar.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `dsires-baby` | Désirée's Baby | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/dsires-baby.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-cop-and-the-anthem` | The Cop and the Anthem | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-cop-and-the-anthem.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-last-leaf` | The Last Leaf | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-last-leaf.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-masque-of-the-red-death` | The Masque of the Red Death | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-masque-of-the-red-death.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-yellow-wallpaper` | The Yellow Wallpaper | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-yellow-wallpaper.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-monkeys-paw` | The Monkey's Paw | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-monkeys-paw.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `the-necklace` | The Necklace | English | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/the-necklace.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |

## Stage 2A: A Ghost Story

The non-paid preflight passed source, rights, sanitation, cover, existing-audio hash, and ASR/source checks. The private asset is reusable and does not require regeneration. Paid schema-3 listening QA did not run because every required budget/listening-QA variable was missing from the live shell. A Ghost Story therefore remains reader-public/audio-hidden; no provider call, release-gate mutation, deployment, or new public audio exposure occurred.

## Stage 2B: A Ghost Story

All runtime gates and `OPENAI_API_KEY` were present in the exact command process. The hash-bound private asset was reused, and six listening samples were judged under the `$2` listening-QA sub-cap. Five samples scored `9.4-9.5`, but `middle_60s` at `352.787s` scored `8.3` overall with pacing `7.9` and emotional expression `8.2`. Confidence was `0.90`, and no fatal flags were detected.

The conditional release authorization was therefore not triggered. A Ghost Story remains reader-public/audio-hidden; its manifest still exposes no audio and its audiobook endpoint remains `404`. The approved `book-2b9853ec52` manifest remains audio-enabled and its range endpoint returned `206`; `bn-066` remains audio-hidden.

The wrapper's historical run returned shell success even though the hook was `BLOCKED`. The focused source fix now maps a blocked hook to a nonzero exit and also prevents repeating the same completed audio-hash/model QA attempt.

## Stage 2C: A Ghost Story

Stage 2C repaired a misaligned middle sample, compound-word boundary semantics, mid-sentence TTS chunking, missing ASR checkpoints, and full-book sample distribution. Three full private candidates were evaluated. The final 1,600-character sentence-safe candidate passed source alignment at `9.928` with both boundaries passing, but its listening minimum remained `8.3` and list-reading rhythm was detected. OpenAI therefore reached a measured provider-quality plateau and no publication gate was mutated.

Google Cloud TTS capability discovery is blocked by expired Application Default Credentials, while ElevenLabs credentials are absent. The exact next action is `gcloud auth application-default login`, followed by one bounded alternate-provider audition. Current private candidates remain non-public.

## Stage 2C Queue Continuation

The Open Window was processed non-paid. Production reader routes are healthy, sanitation and rights pass, and current ASR semantics score the historical transcript at `9.7826` when the legitimate spoken title is included in the audio manuscript. Its existing audio is Piper with synthetic alignment, which is disallowed public provenance. It remains audio-hidden pending the same alternate-provider capability repair.
