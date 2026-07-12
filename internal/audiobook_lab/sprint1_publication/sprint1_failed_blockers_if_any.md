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

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug dsires-baby --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
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

- Conservative estimated spend: `$10.17660 / $175`.
- Estimated remaining budget: `$164.82340`.
- Actual provider billing: `UNKNOWN_NOT_REPORTED_BY_PROVIDERS`.
- No new publication or public release-state mutation is claimed by this reconciliation.

## Release-Truth Containment

- Public audiobooks remain exactly `book-2b9853ec52` and `a-ghost-story`; all other Sprint 1 titles remain audio-hidden.
- Alice and Nishkriti plus six non-Sprint blocked titles: direct URLs were removed from current controlled-publication packets, but already-known Cloudinary/B2 objects remain reachable until storage credentials permit revocation/privacy changes.
- `/audio/*`: source fix pending deployment routes this legacy namespace to removed-content rather than SPA HTML.
