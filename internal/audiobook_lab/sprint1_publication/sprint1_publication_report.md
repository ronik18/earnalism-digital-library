# Sprint 1 Publication Stage 2 Report

Generated: `2026-07-12T18:57:04Z`

## Outcome

- Sprint target: `INCOMPLETE`
- Current public readers: `32/32`
- Reader repairs merged/deployed from PR #101: `17`
- Current public audiobooks: `2/32` in production
- New public audiobooks: `1`
- Provider calls: bounded A Ghost Story production plus bounded Google/OpenAI representative auditions for The Open Window; no Stage 2E full TTS or publication
- Estimated Stage 2B through Stage 2E spend: `$4.2862`; actual provider billing was not reported
- Authorized budget remaining after estimate: `$170.7138`
- Remaining known queue estimate: `$97.6035` after replacing unverifiable D19 group reuse with fresh full-title regeneration
- Production API: `32/32 book routes and 32/32 manifests HTTP 200`
- Production browser: prior `132/132` desktop/mobile route checks pass; Stage 2D book and reader release-state checks pass

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
| `book-d19e96859f` | গিন্নি | Bengali | Yes | No | 9.4/10 representative, confidence 0.95; clean full-regeneration preflight PASS; full-book QA not run | `internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_stage2f_preflight.json` | $0.0000 | PROVIDER_RETRY_REQUIRED |
| `book-f5d593e1f4` | রামকানাইয়ের নির্বুদ্ধিতা | Bengali | Yes | No | 9.4/10 representative only; full-book source gate failed | `internal/audiobook_lab/release_gate/book-f5d593e1f4_20260705T150741Z/goliveevidence.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `pather-panchali` | পথের পাঁচালী / Pather Panchali | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/pather-panchali.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `devdas` | দেবদাস / Devdas | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/devdas.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `book-edfcf810c5` | ক্ষুধিত পাষাণ | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/book-edfcf810c5.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `a-ghost-story` | A Ghost Story | English | Yes | Yes | ASR/source 9.88; first/last PASS; six listening samples 9.4-9.5, confidence 0.95, no fatal flags; 10.0 not claimed | `internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_release_gate_evidence.json` | $3.6328 estimated; actual not reported | Yes, publicly rendered book + Yes, publicly available audiobook |
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
| `the-open-window` | The Open Window | English | Yes | No | Google Studio-C attempts 8.0-9.5; final Studio-B 7.2-9.5, confidence 0.90-0.95; twilight sample has robotic texture and mechanical cadence fatal flags; 10.0 not claimed | `internal/audiobook_lab/sprint1_publication/title_runs/the-open-window_human_narration_packet_report.md` | $0.6534 estimated; actual not reported | HUMAN_NARRATION_OR_ALTERNATE_PROVIDER_REQUIRED |
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

## Stage 2D: A Ghost Story

Google ADC was restored. Baseline Studio-B and Studio-C auditions reproduced the weak middle cadence, while one source-preserving Studio-C prosody repair passed all three representative samples at `9.4`, confidence `0.95`, with no fatal flags. Because safe cross-provider segment splicing was unavailable, one new full Studio-C candidate was generated in nine sentence-safe chunks.

Full QA passed at `9.88` ASR/source, first/last PASS, and six listening samples of `9.4-9.5` with minimum confidence `0.95` and no fatal flags. The existing upload hook then stored five B2 artifacts and verified every remote SHA-256 and byte size. A direct MP3 range request returned `206` and 1,024 bytes. The release source packet exposes only section-following narration and does not claim deterministic `10/10` or word-level sync.

## Stage 2D Production Closeout

Release PR `#105` and cache repair PR `#106` are merged. Railway deployment `8a14b747-b0f3-4da9-903c-96734ab58b2d` serves the approved A Ghost Story manifest and ranged audio proxy. Production UI shows the evidence-backed approval badge, Listen link, section-following narration control, and a fully buffered audio element. No static `/audio/...`, browser speech, word-level claim, or non-approved `AudioObject` is present.

The in-app browser could not start media for either A Ghost Story or the existing approved `book-2b9853ec52` control, so this observation is isolated to that browser runtime rather than the new endpoint. The main regression and GO LIVE workflows pass. k6 recorded `32,808/32,808` functional checks with zero HTTP failures; only catalog p95 measured `1.28s` against its separate `1.20s` threshold. Performance work remains outside this audio repair authorization.

## Stage 2D Queue Continuation: The Open Window

The controlled reader source, rights, sanitation, and covers remain valid, while the historical Piper asset remains ineligible. A new lock-safe Google Studio-C wrapper bound four sub-30-second samples to the sanitized source hash and ran schema-3 listening QA. Baseline scores were `9.4`, `8.4`, `8.0`, and `8.4`. One source-preserving prosody retry improved them to `9.5`, `9.4`, `8.5`, and `9.4`, with no fatal flags.

The twilight transition still failed the `9.4` owner minimum, so no full TTS, upload, manifest mutation, or publication ran. The title remains reader-public/audio-hidden with a separately owner-approved Studio-B audition as the exact next repair action.

## Stage 2E: The Open Window

The final bounded `en-GB-Studio-B` audition ran against four source-bound passages. Opening, shooting-party, and ending samples scored `9.4`, `9.5`, and `9.4`; the twilight transition scored `7.2` at confidence `0.90` and triggered `robotic_texture_detected` plus `mechanical_cadence_detected`. The stricter `schema3_universal_9_7` policy therefore returned `AUDITION_REPAIR_REQUIRED`.

No full audio, upload, manifest, endpoint, frontend release state, or production audio exposure was created. Estimated Stage 2E spend is `$0.2178`, title cumulative estimate is `$0.6534`, and Sprint 1 cumulative estimate is `$4.2862 / $175`. The lock restored byte-for-byte. Automated Google retries stop; the executable repair track is a source-bound human narration or licensed-audio packet followed by the complete release gate.

## Stage 2F: The Open Window And book-d19e96859f

PR `#109` was reviewed as evidence-only fail-closed work with source/test guardrails and no public audio mutation, then squash-merged as `5b20775`. The Open Window now has a complete source-bound human narration packet containing the sanitized manuscript, narrator brief, failed-TTS summary, format/delivery checklist, QA/release checklist, hashes, and an executable received-audio preflight. Its durable classification is `HUMAN_NARRATION_OR_ALTERNATE_PROVIDER_REQUIRED`; public audio remains hidden.

For `book-d19e96859f`, the latest historical group-repair chunks cannot be verified or reused. The narration-only sanitizer was repaired to remove the trailing standalone source year without changing public reader text. The resulting 6,485-character manuscript hashes to `79b0deba6032c36ab919e4ef4786fc62aa55c9c53c328dfbcf49f03a0f7d05fe` and forms five clean groups. Exact title-specific audition evidence confirms Sarvam `bulbul:v3` / `pooja` / `dialogue_human_touch` at `9.4`, confidence `0.95`, with no fatal flags.

Fresh title-only TTS, ASR, and configured listening QA are estimated at `$0.1433`. Both provider keys are present, but all budget/approval/ASR/listening environment gates are absent, so the lock-safe wrapper stopped before acquisition and made zero provider calls. D19 remains public-reader/audio-hidden with classification `PROVIDER_RETRY_REQUIRED`; no release gate or public endpoint was changed.
