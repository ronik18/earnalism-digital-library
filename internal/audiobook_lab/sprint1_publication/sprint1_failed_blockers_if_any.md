# Sprint 1 Stage 2 Remaining Blockers

Generated: `2026-07-12T09:35:33Z`

No title is marked public audio without complete release evidence.

## a-ghost-story / A Ghost Story (Stage 2B)

- Status: `AUDIO_HIDDEN_LISTENING_QA_REPAIR_REQUIRED`
- Blocker: `middle_60s` scored `8.3/10` overall (`7.9` pacing, `8.2` emotional expression), below the owner minimum `9.4`.
- Passing evidence: ASR/source `9.7882`, first/last checks pass, confidence `0.90`, and no fatal listening flags.
- Public truth: reader remains public; audio remains hidden; manifest audio disabled; audiobook endpoint `404`.
- Repair policy: do not repeat the same audio hash/model QA. Prepare this weak passage for a separately authorized targeted literary-voice audition.
- Next command:

```bash
mkdir -p /tmp/earnalism-a-ghost-stage2c-middle-repair && ffmpeg -hide_banner -loglevel error -y -ss 352.787 -t 60 -i internal/audiobook_lab/release_gate/a-ghost-story_20260705T044404Z/a-ghost-story_existing_audio_candidate.mp3 /tmp/earnalism-a-ghost-stage2c-middle-repair/middle_60s_reference.mp3 && sed -n '173,240p' internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/clean_manuscript.txt > /tmp/earnalism-a-ghost-stage2c-middle-repair/middle_source.txt
```

## bn-066 / আনন্দমঠ

- Blocker: `ASR_LANGUAGE_CONFIG_AND_NORMALIZATION_REPAIR_REQUIRED; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
PYTHONPYCACHEPREFIX=/tmp/earnalism-pycache python3 internal/audiobook_lab/scripts/bengali_asr_language_calibration.py --slug bn-066 --run-dir internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts --chunk-ids group_0000,group_0076,group_0151 --language-options auto,bn,ben,bengali --output internal/audiobook_lab/public_access/bn_066_asr_calibration_preflight.json
```

## radharani / রাধারাণী

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs radharani --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## nishkriti / নিষ্কৃতি

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs nishkriti --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## muchiram-gurer-jibanchorit / মুচিরাম গুড়ের জীবনচরিত

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py --manifest book_import_manifest.json --candidate-slugs muchiram-gurer-jibanchorit --max-passages 1 --max-seconds-per-sample 20 --providers sarvam --max-voices-per-provider 1 --voice-filter sarvam:ratan --style-profiles literary_warm_pacing --bengali-audiobook-92-rescue --fail-closed --run-dir internal/audiobook_lab/sprint1_publication/muchiram_split_audition
```

## book-d19e96859f / গিন্নি

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs book-d19e96859f --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## book-f5d593e1f4 / রামকানাইয়ের নির্বুদ্ধিতা

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs book-f5d593e1f4 --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## pather-panchali / পথের পাঁচালী / Pather Panchali

- Blocker: `OWNER_DOCUMENT_REQUIRED_FOR_AUDIO_RIGHTS_SOURCE_COVER; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug pather-panchali --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## devdas / দেবদাস / Devdas

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs devdas --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## book-edfcf810c5 / ক্ষুধিত পাষাণ

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug book-edfcf810c5 --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## a-ghost-story / A Ghost Story

- Blocker: `MIDDLE_60S_LISTENING_QA_FAIL_OVERALL_8.3_PACING_7.9_EXPRESSION_8.2`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Current audio endpoint: `404` fail-closed
- Existing audio/ASR: hash verified; `9.7882/10` source match; first/last `PASS`
- Listening QA: six bounded samples; minimum `8.3`, confidence `0.90`, no fatal flags
- Spend: `$0.30` estimated; actual provider billing not reported
- Next command:

```bash
mkdir -p /tmp/earnalism-a-ghost-stage2c-middle-repair && ffmpeg -hide_banner -loglevel error -y -ss 352.787 -t 60 -i internal/audiobook_lab/release_gate/a-ghost-story_20260705T044404Z/a-ghost-story_existing_audio_candidate.mp3 /tmp/earnalism-a-ghost-stage2c-middle-repair/middle_60s_reference.mp3 && sed -n '173,240p' internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/clean_manuscript.txt > /tmp/earnalism-a-ghost-stage2c-middle-repair/middle_source.txt
```

## dracula / Dracula

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs dracula --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## frankenstein / Frankenstein

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs frankenstein --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## jekyll-and-hyde / The Strange Case of Dr. Jekyll and Mr. Hyde

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs jekyll-and-hyde --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## picture-of-dorian-gray / The Picture of Dorian Gray

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs picture-of-dorian-gray --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## the-time-machine / The Time Machine

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-time-machine --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-call-of-the-wild / The Call of the Wild

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-call-of-the-wild --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## white-fang / White Fang

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug white-fang --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## pride-and-prejudice / Pride and Prejudice

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug pride-and-prejudice --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-secret-garden / The Secret Garden

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-secret-garden --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## alices-adventures-in-wonderland / Alice's Adventures in Wonderland

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs alices-adventures-in-wonderland --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

## the-gift-of-the-magi / The Gift of the Magi

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-gift-of-the-magi --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-tell-tale-heart / The Tell-Tale Heart

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-tell-tale-heart --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-open-window / The Open Window

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-open-window --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## sredni-vashtar / Sredni Vashtar

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug sredni-vashtar --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## dsires-baby / Désirée's Baby

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug dsires-baby --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-cop-and-the-anthem / The Cop and the Anthem

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-cop-and-the-anthem --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-last-leaf / The Last Leaf

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-last-leaf --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-masque-of-the-red-death / The Masque of the Red Death

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-masque-of-the-red-death --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-yellow-wallpaper / The Yellow Wallpaper

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-yellow-wallpaper --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-monkeys-paw / The Monkey's Paw

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-monkeys-paw --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

## the-necklace / The Necklace

- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Reader HTTP: `200`
- Manifest HTTP: `200`
- Next command:

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug the-necklace --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```
