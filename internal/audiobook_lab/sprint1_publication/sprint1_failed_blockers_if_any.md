# Sprint 1 Stage 2 Remaining Blockers

Generated: `2026-07-12T22:00:32Z`

No title is marked public audio without complete release evidence.

## a-ghost-story / A Ghost Story (Stage 2D resolved)

- Status: `YES_PLUS_YES_PRODUCTION_VALIDATED`
- Resolution: Google Studio-C full narration passed ASR/source `9.88`, first/last checks, and six listening samples at `9.4-9.5`, confidence `0.95`, with no fatal flags.
- Upload evidence: five B2 artifacts resolve with matching local/remote SHA-256 and byte sizes; MP3 range request returned `206`.
- Production validation: manifest `APPROVED` / `QA_PASSED`, book UI approved badge and Listen link present, reader audio element ready, and ranged audio proxy returned HTTP `206` with `1,024` bytes.
- Remaining blocker: none. The in-app browser media-start limitation reproduced on the existing approved `book-2b9853ec52` control and is not an A Ghost Story endpoint regression.
- Estimated Stage 2B through Stage 2D spend: `$3.6328`; actual provider billing not reported.
- Next command:

```bash
curl -sS -H 'Range: bytes=0-1023' -o /dev/null -w '%{http_code} %{size_download}\n' https://api.theearnalism.com/api/reader/book/a-ghost-story/audiobook
```

## bn-066 / আনন্দমঠ

- Blocker: `ASR_LANGUAGE_CONFIG_AND_NORMALIZATION_REPAIR_REQUIRED`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
PYTHONPYCACHEPREFIX=/tmp/earnalism-pycache python3 internal/audiobook_lab/scripts/bengali_asr_language_calibration.py --slug bn-066 --run-dir internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts --chunk-ids group_0000,group_0076,group_0151 --language-options auto,bn,ben,bengali --output internal/audiobook_lab/public_access/bn_066_asr_calibration_preflight.json
```

## radharani / রাধারাণী

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs radharani --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## nishkriti / নিষ্কৃতি

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs nishkriti --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## muchiram-gurer-jibanchorit / মুচিরাম গুড়ের জীবনচরিত

- Status: `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`
- Blocker: `AUTOMATED_NARRATION_PLATEAU: FULL_BOOK_MIN_7.8_CONFIDENCE_0.85_WITH_ROBOTIC_MECHANICAL_LIST_READING_FATAL_FLAGS; TARGETED_ACHIRD_MIN_7.4; TARGETED_AOEDE_SLOW_MIN_7.8`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Conservative estimated spend: `$2.1834`; actual provider billing unknown.
- The source-bound packet exists at `internal/audiobook_lab/sprint1_publication/human_narration_packets/muchiram-gurer-jibanchorit`. Automated paid retries stop.
- Next command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug muchiram-gurer-jibanchorit --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

## book-d19e96859f / গিন্নি

- Status: `ASR_SOURCE_MISMATCH`
- Secondary status: `LISTENING_QA_REPAIR_REQUIRED`
- Blocker: `STAGE2G_RAW_ASR_SOURCE_1.3504_BELOW_REQUIRED_9.7; FIRST_LAST_ASR_WORDS_FAILED; LISTENING_MINIMUM_8.0_CONFIDENCE_0.85_WITH_FATAL_LIST_READING_RHYTHM`
- Reader HTTP: `200`
- Manifest HTTP: `200`, audio disabled with zero assets.
- Prepared narration: `6,485` characters, `998` words, SHA-256 `79b0deba6032c36ab919e4ef4786fc62aa55c9c53c328dfbcf49f03a0f7d05fe`.
- Fresh Sarvam full TTS: PASS, five groups, no fallback/local/stale reuse, private audio only.
- Objective failures: raw ASR/source `1.3504 / 10`, first/last false, listening scores `8.0, 8.0, 9.4, 9.4, 9.4, 8.0`, confidence `0.85`, fatal list-reading rhythm.
- Construction audit `10.0` is provenance evidence only and is not an ASR substitute.
- Conservative estimated spend: `$1.5318` title cumulative; `$0.4226` Stage 2G; actual provider billing unknown.
- Repository release-truth repair prepared: both controlled-publication mirrors now say `PUBLIC_AUDIO_RELEASE_NOT_APPROVED`, expose zero audio assets, and contain no D19 audiobook URL. Reader access is unchanged; PR/deploy remains pending.
- Automated Google and Sarvam retries stop. The source-bound human narration packet is at `internal/audiobook_lab/sprint1_publication/human_narration_packets/book-d19e96859f`.
- Upload, release packet, metadata, endpoint, browser release, and publication remain blocked.
- Next command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug book-d19e96859f --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

## book-f5d593e1f4 / রামকানাইয়ের নির্বুদ্ধিতা

- Status: `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`
- Blocker: `GOOGLE_AOEDE_MIN_7.8_WITH_ROBOTIC_AND_MECHANICAL_FATAL_FLAGS; SARVAM_POOJA_MIN_7.8_BELOW_BENGALI_9.2_GATE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Conservative estimated spend: `$0.62788`; actual provider billing unknown.
- The source-bound packet exists at `internal/audiobook_lab/sprint1_publication/human_narration_packets/book-f5d593e1f4`. Automated paid retries stop.
- Next command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug book-f5d593e1f4 --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

## pather-panchali / পথের পাঁচালী / Pather Panchali

- Blocker: `OWNER_DOCUMENT_REQUIRED_FOR_AUDIO_RIGHTS_SOURCE_COVER`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug pather-panchali --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## devdas / দেবদাস / Devdas

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs devdas --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## book-edfcf810c5 / ক্ষুধিত পাষাণ

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug book-edfcf810c5 --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## dracula / Dracula

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs dracula --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## frankenstein / Frankenstein

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs frankenstein --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## jekyll-and-hyde / The Strange Case of Dr. Jekyll and Mr. Hyde

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs jekyll-and-hyde --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## picture-of-dorian-gray / The Picture of Dorian Gray

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs picture-of-dorian-gray --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## the-time-machine / The Time Machine

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-time-machine --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-call-of-the-wild / The Call of the Wild

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-call-of-the-wild --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## white-fang / White Fang

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug white-fang --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## pride-and-prejudice / Pride and Prejudice

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug pride-and-prejudice --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-secret-garden / The Secret Garden

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-secret-garden --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## alices-adventures-in-wonderland / Alice's Adventures in Wonderland

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs alices-adventures-in-wonderland --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## the-gift-of-the-magi / The Gift of the Magi

- Status: `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`
- Blocker: `STUDIO_C_MIN_8.5; CHIRP_AOEDE_MIN_7.2_WITH_ROBOTIC_AND_MECHANICAL_FATAL_FLAGS; CONTEXTUAL_STUDIO_C_MIN_8.3`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Conservative estimated spend: `$0.6734`; actual provider billing unknown.
- Next command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-gift-of-the-magi --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets
```

## the-tell-tale-heart / The Tell-Tale Heart

- Status: `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`
- Blocker: `CONTEXTUAL_STUDIO_C_MIN_8.5; SLOW_CONTEXTUAL_STUDIO_C_MIN_8.4`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Conservative estimated spend: `$0.44604`; actual provider billing unknown.
- Next command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-tell-tale-heart --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets
```

## the-open-window / The Open Window

- Status: `HUMAN_NARRATION_OR_ALTERNATE_PROVIDER_REQUIRED`
- Blocker: `REPRESENTATIVE_AUDITION_STUDIO_B_TWILIGHT_SCORE_7.2_WITH_ROBOTIC_AND_MECHANICAL_FATAL_FLAGS`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Historical asset: Piper with synthetic alignment; it remains ineligible.
- Google Studio-C baseline scores: `9.4`, `8.4`, `8.0`, `8.4`.
- Single prosody retry scores: `9.5`, `9.4`, `8.5`, `9.4`; no fatal flags; lock restored.
- Final Google Studio-B scores: `9.4`, `9.5`, `7.2`, `9.4`; the twilight sample has robotic texture and mechanical cadence fatal flags.
- Estimated audition spend: `$0.6534`; actual provider billing not reported.
- Automated Google retries stop. The generated packet at `internal/audiobook_lab/sprint1_publication/human_narration_packets/the-open-window` is the source-bound human narration or alternate-provider track.
- Next command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_prepare_human_narration_packet.py --slug the-open-window --asset-root /Users/ronikbasak/Documents/GitHub/earnalism-digital-library --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

## sredni-vashtar / Sredni Vashtar

- Status: `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`
- Blocker: `STUDIO_C_MIN_7.3_WITH_ROBOTIC_AND_MECHANICAL_FATAL_FLAGS; CHIRP_ACHIRD_MIN_8.5_BELOW_ENGLISH_9.3_GATE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Conservative estimated spend: `$0.42788`; actual provider billing unknown.
- Next command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug sredni-vashtar --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets
```

## dsires-baby / Désirée's Baby

- Repair state: `ALTERNATE_VOICE_AUDITION_REQUIRED`
- Blocker: Studio-C scores `9.4, 8.4, 7.5, 9.4`; minimum confidence `0.85`; the risk passage has fatal robotic texture and mechanical cadence.
- Reader HTTP: `200`
- Manifest HTTP: `200`; audio remains disabled.
- Source preflight: `PASS`, 11,974 characters, rights/sanitation bound to SHA-256 `587455ed554ef64d19f0ea7dcd31940d242aa759f5132b6514b130efa4a64a89`.
- Attempt: Studio-C fingerprint `bccf002da4e9713e3870b602c07e65ae1ad0a49fbd1904e5730b823a0d605d4e`; four synthesis calls completed; `$0.23616` conservatively estimated including listening QA; actual billing unknown; lock restored byte-for-byte.
- Next action: run one materially different `en-GB-Chirp3-HD-Achird` audition. If it fails, stop automated Google retries and build a human narration or licensed-audio import packet.
- Next command:

```bash
SPRINT1_TOTAL_AUDIO_BUDGET_USD=175 SPRINT1_MAX_USD_PER_TITLE=30 MAX_TTS_BUDGET_USD=175 EARNALISM_STOP_ON_BUDGET_EXCEEDED=true EARNALISM_APPROVE_GOOGLE_TTS_AUDITIONS=true EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD=1 EARNALISM_APPROVE_GOOGLE_ENGLISH_PRIVATE_AUDITION=true EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD=2 EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD=0.05 EARNALISM_ENABLE_OPENAI_LISTENING_QA=true EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_google_english_private_pipeline.py audition --sanitized-source /tmp/earnalism-dsires-stage-acceleration-input/dsires-baby/sanitized_source.txt --input-manifest /tmp/earnalism-dsires-stage-acceleration-input/dsires-baby/input_manifest.json --paid-lock /Users/ronikbasak/Documents/GitHub/earnalism-digital-library/internal/earnalism_intelligence/locks/paid_tts.lock --private-output-dir /tmp/earnalism-dsires-stage-acceleration-private --voice en-GB-Chirp3-HD-Achird --language-code en-GB --usd-per-million-chars 20 --run-budget-usd 1 --title-budget-usd 30 --title-spend-usd 0.23616 --sprint-budget-usd 175 --sprint-spend-usd 10.41276 --minimum-listening-score 9.4 --minimum-listening-confidence 0.9 --speaking-rate 0.90 --execute
```

## the-cop-and-the-anthem / The Cop and the Anthem

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-cop-and-the-anthem --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-last-leaf / The Last Leaf

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-last-leaf --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-masque-of-the-red-death / The Masque of the Red Death

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-masque-of-the-red-death --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-yellow-wallpaper / The Yellow Wallpaper

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-yellow-wallpaper --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-monkeys-paw / The Monkey's Paw

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-monkeys-paw --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-necklace / The Necklace

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-necklace --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## Conservative Spend Checkpoint

- Conservative estimated spend: `$10.41276 / $175`.
- Estimated remaining budget: `$164.58724`.
- Actual provider billing: `UNKNOWN_NOT_REPORTED_BY_PROVIDERS`.
- No new publication or public release-state mutation is claimed by this reconciliation.

## Release-Truth Containment

- Public audiobooks remain exactly `book-2b9853ec52` and `a-ghost-story`; all other Sprint 1 titles remain audio-hidden.
- Alice and Nishkriti plus six non-Sprint blocked titles: direct URLs were removed from current controlled-publication packets, but already-known Cloudinary/B2 objects remain reachable until storage credentials permit revocation/privacy changes.
- `/audio/*`: source fix pending deployment routes this legacy namespace to removed-content rather than SPA HTML.

## Autonomous V2 Executable Repair Tracks

The owner-authorized automated queue was exhausted without weakening the all-samples listening gate. These are external production tracks, not dead-end holds:

| Slug | Exact repair state | Estimated automated spend | Exact next command |
| --- | --- | ---: | --- |
| `the-cop-and-the-anthem` | `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED` | `$0.47452` | `PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-cop-and-the-anthem --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav` |
| `the-last-leaf` | `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED` | `$0.46860` | `PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-last-leaf --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav` |
| `the-masque-of-the-red-death` | `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED` | `$0.45940` | `PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-masque-of-the-red-death --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav` |
| `dsires-baby` | `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED` | `$0.47232` | `PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug dsires-baby --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav` |
| `the-necklace` | `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED` | `$0.46080` | `PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-necklace --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav` |
| `the-monkeys-paw` | `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED_AFTER_FULL_QA_REPAIR_FAILED` | `$1.92142` | `PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-monkeys-paw --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav` |
| `the-yellow-wallpaper` | `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED` | `$0.47248` | `PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-yellow-wallpaper --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav` |

The conservative Sprint checkpoint is `$14.90614 / $175`; estimated remaining budget is `$160.09386`. Actual provider billing is not reported. No additional paid action is currently safe without external narration, rights/source evidence, or a materially new provider family.

## Autonomous V3 Closeout

- Current public truth remains `2/32` YES+YES: `book-2b9853ec52` and `a-ghost-story`.
- Fourteen exhausted-provider titles are now consistently classified as `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`; their complete packets and received-audio commands are indexed in `sprint1_human_narration_intake_board.json`.
- No received narration or licensed-audio file is present, so no intake QA or publication can run yet.
- `jekyll-and-hyde` is source-, rights-, sanitation-, and cover-ready, but Google ADC requires interactive reauthentication. Exact next command: `gcloud auth application-default login`.
- `radharani`, `nishkriti`, `devdas`, and `book-edfcf810c5` passed non-paid reader/source/sanitation/cover preflight; Bengali campaign pilot and campaign-specific paid gates still prohibit scaling.
- `bn-066` remains private-audio-only pending lock-safe three-chunk ASR language calibration with the private Stage 2 artifacts.
- `pather-panchali` remains `OWNER_DOCUMENT_REQUIRED` for audiobook rights/source/cover proof.
- Six non-approved titles have historical Cloudinary/B2 objects that are still directly reachable. Current API/UI state is fail-closed, but remote deletion or private migration is destructive and requires an explicit storage operation; see `sprint1_unapproved_remote_audio_exposure_audit.json`.
- No provider call, upload, public release mutation, deployment, or paid-lock mutation occurred in V3. Estimated spend remains `$14.90614`; estimated remaining cap remains `$160.09386`.
