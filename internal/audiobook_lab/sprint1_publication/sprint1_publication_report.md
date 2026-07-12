# Sprint 1 Publication Stage 2 Report

Generated: `2026-07-12T22:00:32Z`

## Outcome

- Sprint target: `INCOMPLETE`
- Current public readers: `32/32`
- Reader repairs merged/deployed from PR #101: `17`
- Current public audiobooks: `2/32` in production
- New public audiobooks in this reconciliation: `0`
- Public audiobook allowlist remains exactly `book-2b9853ec52` and `a-ghost-story`
- Provider calls: prior bounded production/QA plus later serialized D19, Muchiram, F5, Sredni, Gift, and Tell evidence; no publication or release-state mutation in this reconciliation
- Conservative estimated spend through the latest completed checkpoint: `$9.75400 / $175`; actual provider billing is unknown
- Authorized budget remaining after estimate: `$165.24600`
- Remaining known automated queue estimate remains a conditional legacy estimate; human narration/licensed-audio tracks are unpriced and D19 requires ASR language/config repair before any upload path
- Production API: `32/32 book routes and 32/32 manifests HTTP 200`
- Production browser: prior `132/132` desktop/mobile route checks pass; Stage 2D book and reader release-state checks pass

## Reader Repair

PR [https://github.com/ronik18/earnalism-digital-library/pull/101](https://github.com/ronik18/earnalism-digital-library/pull/101) merged as `faf8587` and deployed to Railway as `4e190b99-acec-4755-83db-82cbe15bd852`. It restored 17 reader-only packets, stripped legacy audio approval/assets, and preserved the one-title audio allowlist. PR #102 then restored cache-header CORS and deployed as `9100d4d8-47b5-4859-94b5-9ca118cff32c`.

## Latest Release Truth

All 32 active readers remain public. Public audiobooks remain exactly `book-2b9853ec52` and `a-ghost-story`; this reconciliation claims no new publication. D19's private Google TTS, six-sample listening QA, and measured paragraph/stanza sync pass, but raw ASR/source is `0.6838`, below the mandatory `9.7` gate. Its construction audit score of `10.0` is provenance evidence only and cannot substitute for ASR.

| slug | title | language | Publicly rendered book | Publicly available audiobook | Quality score | Evidence path | Cost used | Final status |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| `book-2b9853ec52` | দুই বিঘা জমি | Bengali | Yes | Yes | 9.4/10 listening, confidence 0.95; approved minimum passed, 10.0 not claimed | `internal/audiobook_lab/release_gate/book-2b9853ec52_20260707T053510Z/goliveevidence.json` | $0.0000 | Yes, publicly rendered book + Yes, publicly available audiobook |
| `bn-066` | আনন্দমঠ | Bengali | Yes | No | 0.8403/10 ASR-source; listening not run | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/bn-066.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `radharani` | রাধারাণী | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/radharani.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `nishkriti` | নিষ্কৃতি | Bengali | Yes | No | NOT_RUN | `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/nishkriti.json` | $0.0000 | SPRINT_TARGET_INCOMPLETE |
| `muchiram-gurer-jibanchorit` | মুচিরাম গুড়ের জীবনচরিত | Bengali | Yes | No | Full QA minimum 7.8 with robotic/mechanical/list-reading fatal flags; targeted repairs minimum 7.4/7.8 | `internal/audiobook_lab/sprint1_publication/title_runs/muchiram_google_full_qa.json` | $2.1834 estimated; actual unknown | HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED |
| `book-d19e96859f` | গিন্নি | Bengali | Yes | No | Stage 2G Sarvam full TTS PASS; raw ASR/source 1.3504; first/last FAIL; listening minimum 8.0, confidence 0.85, fatal list-reading rhythm | `internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_release_gate_evidence.json` | $1.5318 conservative cumulative estimate; actual unknown | ASR_SOURCE_MISMATCH |
| `book-f5d593e1f4` | রামকানাইয়ের নির্বুদ্ধিতা | Bengali | Yes | No | Google and Sarvam bounded auditions minimum 7.8; Google has robotic/mechanical fatal flags | `internal/audiobook_lab/sprint1_publication/title_runs/book-f5d593e1f4_google_audition/bengali_representative_audition_report.json` | $0.62788 estimated; actual unknown | HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED |
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
| `the-gift-of-the-magi` | The Gift of the Magi | English | Yes | No | Three bounded auditions failed: minima 8.5, 7.2 with robotic/mechanical flags, and 8.3 | `internal/audiobook_lab/private_runs/google_english/the-gift-of-the-magi/audition/716473a1705c4aa3/audition_listening_evidence.json` | $0.6734 estimated; actual unknown | HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED |
| `the-tell-tale-heart` | The Tell-Tale Heart | English | Yes | No | Contextual and slow-contextual Studio-C minima 8.5/8.4, below English 9.3 gate | `internal/audiobook_lab/private_runs/google_english/the-tell-tale-heart/audition/4f7b571d8625924e/audition_listening_evidence.json` | $0.44604 estimated; actual unknown | HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED |
| `the-open-window` | The Open Window | English | Yes | No | Google Studio-C attempts 8.0-9.5; final Studio-B 7.2-9.5, confidence 0.90-0.95; twilight sample has robotic texture and mechanical cadence fatal flags; 10.0 not claimed | `internal/audiobook_lab/sprint1_publication/title_runs/the-open-window_human_narration_packet_report.md` | $0.6534 estimated; actual not reported | HUMAN_NARRATION_OR_ALTERNATE_PROVIDER_REQUIRED |
| `sredni-vashtar` | Sredni Vashtar | English | Yes | No | Studio-C minimum 7.3 with robotic/mechanical flags; Chirp Achird minimum 8.5 below English 9.3 gate | `internal/audiobook_lab/private_runs/google_english/sredni-vashtar/audition/3855fd15b4ecf50d/audition_listening_evidence.json` | $0.42788 estimated; actual unknown | HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED |
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

For `book-d19e96859f`, the later private Google candidate preserves the source-bound 6,485-character manuscript and passes full TTS, six listening samples at `9.4` with confidence `0.95` and no fatal flags, and measured paragraph/stanza sync with `auto_estimated_sync=false`. Raw ASR/source is only `0.6838`, below the required `9.7`. The `10.0` construction audit remains separate provenance evidence and is not accepted as ASR.

D19 is therefore `AUTOMATED_ASR_ARMS_EXHAUSTED_NORMALIZATION_REPAIR_REQUIRED_PRIVATE_TTS_PASS`, not ready for upload, a release packet, admin metadata mutation, endpoint enablement, browser release QA, or publication. It remains public-reader/audio-hidden.

## Post-Stage 2F Evidence Reconciliation

Muchiram's private full candidate failed listening at a `7.8` minimum with robotic, mechanical, and list-reading fatal flags; targeted Achird and slower Aoede repairs also failed at `7.4` and `7.8`. F5's Google Aoede and Sarvam Pooja auditions both bottomed at `7.8`. Their source-bound human narration packets are ready, and additional automated retries stop.

Sredni Vashtar failed Studio-C at `7.3` with robotic/mechanical flags and Chirp Achird at `8.5`. The Gift of the Magi failed three bounded auditions at `8.5`, `7.2`, and `8.3`; the Chirp attempt carried robotic/mechanical flags. The Tell-Tale Heart failed contextual and slow-contextual Studio-C at `8.5` and `8.4`. These titles move to source-bound human narration or licensed-audio import packets; none is public audio.

The conservative estimate through the final D19 ASR repair checkpoint is `$9.75400 / $175`, leaving `$165.24600` by estimate. Actual provider billing is unknown. No new publication, upload, release-gate mutation, lock mutation, or public audio exposure is claimed by this reconciliation.

## Parallel Yes+Yes Sprint

Six read-only/non-paid lanes were launched under one coordinator. Every active title is assigned exactly once to an analysis/repair lane, while paid provider execution remains serialized through `paid_tts.lock`.

The live shell has Sarvam, OpenAI, and Google credentials plus valid Google ADC, but all Sprint budget, per-title budget, stop-on-budget, title approval, ASR cap, and listening-QA cap variables are missing. The coordinator therefore reran D19's non-paid preflight only: all cheap gates passed, the planned pipeline remains `$0.1433`, and the wrapper stopped before lock acquisition or provider access. Public audiobook truth remains exactly `book-2b9853ec52` and `a-ghost-story`.

Parallel production validation also found two release-truth defects unrelated to provider generation. Both approved timestamp sidecars use seconds while Reader consumed milliseconds, and eight blocked title packets retained direct storage URLs. Source repairs now normalize timing, require real playback advancement in browser QA, scrub 88 URL occurrences, and fail closed the legacy `/audio/*` namespace. Deployment and remote storage revocation remain pending.

## Stage 2G: book-d19e96859f

The title-only Sarvam `bulbul:v3` / `pooja` / `dialogue_human_touch` wrapper generated five fresh groups from the 6,485-character sanitized manuscript. The private MP3 is `627.875833s`, `10,047,021` bytes, and SHA-256 `40de51486f663bf9af196f2d9018029d7e01f75d0f4d16fc537910fcfe754da3`; no fallback, local, or stale audio was reused.

Release QA failed on raw audio-derived evidence. ASR/source scored `1.3504 / 10`, both first/last ASR boundaries failed, and the mixed Bengali/Devanagari transcript cannot satisfy the `9.7` gate. Six listening samples scored `8.0`, `8.0`, `9.4`, `9.4`, `9.4`, and `8.0`; minimum confidence was `0.85`, with `list_reading_rhythm_detected` fatal. The construction audit remains `10.0` provenance evidence only and was not accepted as ASR.

No upload, public manifest, endpoint, frontend state, deployment, or release gate changed. The title remains public-reader/audio-hidden with classification `ASR_SOURCE_MISMATCH`; automated Google and Sarvam arms stop, and the executable repair state is source-bound human narration or licensed-audio import followed by full QA. Stage 2G estimated spend is `$0.4226`; cumulative Sprint estimate is `$10.1766 / $175`, with `$164.8234` remaining. Actual provider billing was not reported, and `paid_tts.lock` restored byte-for-byte.
