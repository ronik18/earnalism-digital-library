# Earnalism Audiobook Generation

## 1. Overview

`generate_audio.py` creates production audiobook assets for Bengali and English Earnalism ebooks.

Architecture:

- **Bengali primary:** configurable in `voices.json`. Sarvam AI TTS with `bulbul:v2` is available for literary narration; Google Bengali Wavenet can be selected when deterministic SSML word timestamps are preferred.
- **Bengali fallback:** Google Cloud Text-to-Speech `bn-IN` voices.
- **English primary:** Google Cloud Text-to-Speech `en-IN` Neural2.
- **English fallback:** Google WaveNet `en-IN`.
- **Sarvam timestamps:** stable-whisper forced alignment because Sarvam does not return word timing.
- **Google timestamps:** SSML `<mark>` timepoints through `google-cloud-texttospeech` v1beta1.
- **Reader sync:** every provider writes the same `{slug}_timestamps.json` schema.

Generated files are cached. If `{slug}.mp3` already exists, reruns skip that book and consume no new credits.
Sarvam currently accepts up to 3 text inputs per request, so the generator batches Bengali chunks in groups of 3.

## 2. Setup

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

For English Edge polishing only, install the lightweight Edge CLI. This is the
recommended path when Azure Speech is disabled or out of credits:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-audio-edge.txt
```

For the open-source full-catalog onboarding path, install the optional local TTS
stack separately so Railway/Vercel deploys do not pull multi-GB model
dependencies. This pulls `transformers`, Piper, and Parler-style tooling, so do
not use it for the lightweight Edge fallback:

```bash
brew install git-lfs  # macOS, required by Parler audio tooling
git lfs install
python3 -m pip install -r requirements-audio-open-source.txt
```

Install ffmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

Verify:

```bash
ffmpeg -version
ffprobe -version
```

### 2a. Sarvam AI

1. Sign up at Sarvam AI.
2. Create or open the developer dashboard.
3. Copy the API subscription key.
4. Set it locally:

```bash
export SARVAM_API_KEY="your_key_here"
```

The script retries `429`/network/API failures with exponential backoff and then falls back to Google Bengali TTS if Sarvam remains unavailable.

### 2b. Google Cloud TTS

1. Open `console.cloud.google.com`.
2. Create a project, for example `earnalism-tts`.
3. Enable **Cloud Text-to-Speech API**.
4. Go to **IAM → Service Accounts → Create Service Account**.
5. Grant role: **Cloud Text-to-Speech User**.
6. Create a JSON key and save it somewhere private, for example `./gcp_key.json`.
7. Set:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/gcp_key.json"
export GOOGLE_CLOUD_PROJECT="earnalism-tts"
```

Google commonly offers a monthly free tier for TTS characters. Check the current Google Cloud pricing page before bulk runs because pricing and quota terms can change.

### 2c. stable-whisper setup

Install:

```bash
python3 -m pip install stable-ts torch openai-whisper
```

Pre-download the alignment model once:

```bash
python3 -c "import whisper; whisper.load_model('base')"
```

Model cache location: `~/.cache/whisper/`.

| Model | Speed | Bengali alignment quality | Suggested use |
| --- | --- | --- | --- |
| `tiny` | Fastest | Lower | Quick local smoke tests |
| `base` | Balanced | Good | Default production pass |
| `small` | Slower | Better | Final samples where sync drift is visible |

### 2d. Environment file

You can keep local variables in an ignored `.env` file:

```bash
SARVAM_API_KEY=
GOOGLE_APPLICATION_CREDENTIALS=
GOOGLE_CLOUD_PROJECT=
```

Never commit real credential values.

## 3. Usage

Full batch:

```bash
python generate_audio.py \
  --manifest book_import_manifest.json \
  --output-dir ./audio_output/
```

Dry run:

```bash
python generate_audio.py \
  --manifest book_import_manifest.json \
  --dry-run
```

Bengali only:

```bash
python generate_audio.py \
  --manifest book_import_manifest.json \
  --lang ben \
  --output-dir ./audio_output/
```

## 3a. Open-source full-catalog onboarding

Use `scripts/open_source_audiobook_onboarding.py` when the goal is to generate
synced audiobooks for every book already uploaded to the live platform.

Default open-source stack:

- **English:** Piper TTS with a locally downloaded `.onnx` voice model.
- **Bengali catalog default:** `facebook/mms-tts-ben`, a fast open-source
  Bengali TTS model that is practical for full-library generation.
- **Bengali premium option:** `ai4bharat/indic-parler-tts` with a Bengali
  literary narration prompt. This gives more expressive narration, but should
  be run on a GPU worker for full-book/catalog batches.
- **Sync:** stable-ts / Whisper forced alignment into the existing
  `{slug}_timestamps.json` schema, with deterministic proportional timestamps
  only as a fallback when alignment coverage is too low.

Preflight:

```bash
npm run audio:preflight
```

Expected production-ready environment:

```bash
export PIPER_MODEL_PATH="/absolute/path/to/en_US-lessac-medium.onnx"
export PIPER_CONFIG_PATH="/absolute/path/to/en_US-lessac-medium.onnx.json"
export PIPER_BINARY="/absolute/path/to/piper"
export HF_TOKEN="hf_..."  # required for gated/parler runs and model downloads
```

Audit live uploaded books against existing reader assets:

```bash
npm run audio:audit
```

Dry-run all uploaded books without generating audio:

```bash
npm run audio:onboard:dry
```

Generate the catalog into `output/open_source_audiobooks` without touching the
frontend bundle or live database:

```bash
python3 scripts/open_source_audiobook_onboarding.py generate
```

Generate, copy passing bundles into `frontend/public/audio`, and patch live
admin audiobook flags only after each bundle validates:

```bash
python3 scripts/open_source_audiobook_onboarding.py generate \
  --copy-to-public \
  --sync-flags
```

For Cloudinary-backed production delivery, run with Railway backend variables
so `HF_TOKEN` and Cloudinary credentials are available to the local generator:

```bash
railway run --service earnalism --environment production -- \
  .venv-audio/bin/python scripts/open_source_audiobook_onboarding.py generate \
  --piper-binary "$PWD/.venv-audio/bin/piper" \
  --piper-model "$PWD/.cache/audio_models/piper/en_US-lessac-medium/en_US-lessac-medium.onnx" \
  --piper-config "$PWD/.cache/audio_models/piper/en_US-lessac-medium/en_US-lessac-medium.onnx.json" \
  --upload-to-cloudinary \
  --sync-flags \
  --order-shortest-first
```

## 3b. Bengali audiobook QA and polishing

Use `scripts/audio/polishBengaliAudiobooks.js` when existing Bengali
audiobooks need a quality audit or a careful regeneration pass. The job is
dry-run by default, writes resumable progress, and never patches production
audiobook fields unless `--commit` is present.

The script inspects live admin book data, current audiobook storage metadata,
timestamp sidecars, narration text, punctuation, mixed Bengali-English terms,
and pronunciation lexicon coverage. It writes:

- `output/bengali_audiobook_polish/<job-id>/bengali_audiobook_polish_report.json`
- `output/bengali_audiobook_polish/<job-id>/progress.json`
- prepared `.txt` and `.ssml` narration files per checked book
- generated audiobook bundles only in `--commit` mode

Random audit only:

```bash
npm run audiobook:bengali:polish -- \
  --sample 5 \
  --env-file .secrets/earnalism-import.env
```

Process one Bengali audiobook in dry-run/reporting mode:

```bash
npm run audiobook:bengali:polish -- \
  --slug bn-066 \
  --job-id polish-bn-066-audit \
  --verbose \
  --env-file .secrets/earnalism-import.env
```

Run local text-normalization and SSML checks without admin API access or Azure
usage:

```bash
npm run audiobook:bengali:self-test
```

Audio regeneration command matrix:

Local self-test only. This uses no Azure, admin API, upload, or production
write:

```bash
npm run audiobook:bengali:self-test
```

Generate a sequential Bengali audiobook regeneration queue sorted by smallest
generation size first:

```bash
npm run audiobook:bengali:queue -- \
  --env-file .secrets/earnalism-import.env
```

The generated queue is written to:

```text
audio_manifests/bengali_audiobook_regeneration_queue_20260612.json
```

Each queue item includes `sequence`, `slug`, title/author, normalized
`generation_size_chars`, `word_count`, estimated chunk count, and current MP3
size when available. `generation_size_chars` is the default sort key because it
is the best proxy for Azure generation time and cost. To sort by current MP3
byte size instead:

```bash
npm run audiobook:bengali:polish -- \
  --export-queue audio_manifests/bengali_audiobook_regeneration_queue_audio_size_20260612.json \
  --queue-sort current-audio-size \
  --env-file .secrets/earnalism-import.env
```

Dry-run the queue in the prepared sequence:

```bash
npm run audiobook:bengali:polish -- \
  --manifest audio_manifests/bengali_audiobook_regeneration_queue_20260612.json \
  --job-id bengali-polish-queue-audit-v1 \
  --restart \
  --verbose \
  --env-file .secrets/earnalism-import.env
```

Commit the queue sequentially:

```bash
railway run --service earnalism --environment production -- \
  npm run audiobook:bengali:polish -- \
  --manifest audio_manifests/bengali_audiobook_regeneration_queue_20260612.json \
  --job-id bengali-polish-queue-v1 \
  --commit \
  --concurrency 1 \
  --env-file .secrets/earnalism-import.env
```

If Azure returns `HTTP 429 Quota Exceeded`, the job pauses on the current book
with `PAUSED_QUOTA` instead of continuing to the next title. Already generated
chunk audio for that book is preserved under the job folder and reused on
resume. After Azure quota is restored, rerun the same job id without `--restart`:

```bash
railway run --service earnalism --environment production -- \
  npm run audiobook:bengali:polish -- \
  --manifest audio_manifests/bengali_audiobook_regeneration_queue_20260612.json \
  --job-id bengali-polish-queue-v1 \
  --resume \
  --commit \
  --concurrency 1 \
  --env-file .secrets/earnalism-import.env
```

Do not use `--restart` for quota recovery unless you intentionally want to
discard saved progress/chunks for that job. The default
`BENGALI_TTS_REQUEST_DELAY_MS=3000` adds a pause between Azure calls, and the
job retries Azure `429` responses up to `BENGALI_TTS_MAX_RETRIES=8` with capped
exponential backoff. Keep `BENGALI_TTS_PAUSE_ON_429=true` for catalog runs so a
quota wall preserves progress and prints a next resume command.

Dry-run one book. This prepares normalized text, SSML, verbose QA diagnostics,
and reports without generating/uploading audio:

```bash
npm run audiobook:bengali:polish -- \
  --slug bn-066 \
  --job-id polish-bn-066-audit \
  --restart \
  --verbose \
  --env-file .secrets/earnalism-import.env
```

The dry-run report intentionally separates two scores:

- `overall_score` grades the currently live audiobook asset.
- `regeneration_readiness_score` grades the prepared Azure SSML regeneration
  path before spending Azure credits or updating production.

When the current audio is an older `mms-tts` asset, `overall_score` can stay
below 9 while `regeneration_readiness_score` is 9+ and ready for a commit run.

Regenerate one audiobook and update production audiobook fields after manual
dry-run review:

```bash
railway run --service earnalism --environment production -- \
  npm run audiobook:bengali:polish -- \
  --slug bn-066 \
  --job-id polish-bn-066-v1 \
  --commit \
  --concurrency 1 \
  --env-file .secrets/earnalism-import.env
```

Force regeneration even when the current audiobook passes QA:

```bash
railway run --service earnalism --environment production -- \
  npm run audiobook:bengali:polish -- \
  --slug bn-066 \
  --job-id polish-bn-066-force-v1 \
  --commit \
  --force-regenerate \
  --concurrency 1 \
  --env-file .secrets/earnalism-import.env
```

Regenerate all Bengali audiobooks. Run this only after testing a few individual
books:

```bash
railway run --service earnalism --environment production -- \
  npm run audiobook:bengali:polish -- \
  --all-bengali \
  --job-id bengali-polish-catalog-v1 \
  --commit \
  --concurrency 1 \
  --env-file .secrets/earnalism-import.env
```

Resume an interrupted catalog job:

```bash
npm run audiobook:bengali:polish -- \
  --all-bengali \
  --job-id bengali-polish-catalog-v1 \
  --commit \
  --concurrency 1 \
  --env-file .secrets/earnalism-import.env
```

Restart the same catalog job from scratch:

```bash
npm run audiobook:bengali:polish -- \
  --all-bengali \
  --job-id bengali-polish-catalog-v1 \
  --restart \
  --commit \
  --concurrency 1 \
  --env-file .secrets/earnalism-import.env
```

Required configuration for commit mode:

```bash
BENGALI_TTS_PROVIDER=command
BENGALI_TTS_COMMAND='node scripts/audio/tts/azureBengaliTts.js --input "{input}" --output "{output}" --voice "bn-IN-TanishaaNeural"'
BENGALI_TTS_SUPPORTS_SSML=true
BENGALI_TTS_VOICE_ID='bn-IN-TanishaaNeural'
BENGALI_TTS_OUTPUT_FORMAT=mp3
BENGALI_TTS_CHUNK_CHARS=3600
BENGALI_TTS_COMMAND_TIMEOUT_MS=300000
BENGALI_TTS_CONCURRENCY=1
BENGALI_TTS_REQUEST_DELAY_MS=3000
BENGALI_TTS_MAX_RETRIES=8
BENGALI_TTS_RETRY_BASE_DELAY_MS=30000
BENGALI_TTS_RETRY_MAX_DELAY_MS=600000
BENGALI_TTS_RETRY_JITTER=true
BENGALI_TTS_PAUSE_ON_429=true
BENGALI_TTS_RATE=+3%
BENGALI_TTS_PITCH=+1Hz
BENGALI_TTS_PAUSE_PROFILE=natural-expressive
BENGALI_AUDIO_QA_THRESHOLD=9.3
BENGALI_AUDIO_PRONUNCIATION_LEXICON=/absolute/path/to/bengali-pronunciation-lexicon.json
AZURE_SPEECH_KEY='...'
AZURE_SPEECH_REGION='centralindia'
AZURE_SPEECH_FALLBACK_REGIONS=''
AZURE_BENGALI_VOICE='bn-IN-TanishaaNeural'
B2_S3_MAX_ATTEMPTS=5
```

If you configure fallback Azure regions, provide a separate key for each region
using an uppercase, underscore-safe suffix. Example:
`AZURE_SPEECH_FALLBACK_REGIONS=eastus,uksouth`,
`AZURE_SPEECH_KEY_EASTUS=...`, and `AZURE_SPEECH_KEY_UKSOUTH=...`. The adapter
will not reuse the primary key for another region.

The command adapter receives these environment variables for every chunk:

- `EARNALISM_TTS_INPUT`
- `EARNALISM_TTS_OUTPUT`
- `EARNALISM_TTS_SSML`
- `EARNALISM_TTS_TEXT`
- `EARNALISM_TTS_CHUNK_INDEX`
- `EARNALISM_TTS_SLUG`

The bundled Azure adapter lives at `scripts/audio/tts/azureBengaliTts.js`.
If a polish run fails with `Cannot find module .../scripts/audio/tts/azureBengaliTts.js`,
pull the latest code or confirm this file exists locally. The adapter reads
`EARNALISM_TTS_INPUT` and `EARNALISM_TTS_OUTPUT` automatically, but the explicit
`--input "{input}" --output "{output}"` command is preferred for auditable logs.

The Bengali polish path normalizes only the generated TTS input, not the source
book content in MongoDB. It applies a natural-expressive SSML profile by default:
`rate="+3%"`, `pitch="+1Hz"`, shorter punctuation pauses, Bengali/English
hyphen cleanup, numeric ranges as `থেকে`, true negative numbers as `ঋণাত্মক`,
and lexicon replacements such as `AI -> এ আই`, `technology -> টেকনোলজি`, and
`digital library -> ডিজিটাল লাইব্রেরি`. Use `--verbose` during dry-runs to save
normalized text previews, SSML previews, pause distributions, lexicon counts,
hyphen/dash counts, chunk sizing, and the redacted TTS command.

Tuning:

- Still too slow: raise `BENGALI_TTS_RATE` gradually, for example `+5%`.
- Too fast: lower `BENGALI_TTS_RATE`, for example `+1%` or `0%`.
- Too flat: try `BENGALI_TTS_PITCH=+2Hz`, or test the male voice with `--voice "bn-IN-BashkarNeural"`.
- Too pause-heavy: keep `BENGALI_TTS_PAUSE_PROFILE=natural-expressive`; inspect `averagePauseMs`, `pausesOver650ms`, and `totalInsertedPauses` in the verbose report before changing code.

Generated audio is uploaded through `lib/storage/audioUploader.js`, so
Cloudinary remains the path for smaller MP3s and Backblaze B2 is used for
large MP3s. The script uploads to a versioned polished-audiobook folder and
then patches the book through the existing admin audiobook endpoint. Existing
storage objects are not deleted.

The quality gate is intentionally conservative. Automated scoring can flag
clarity, punctuation, pacing, timestamp health, provider risk, and
pronunciation-lexicon coverage, but it does not pretend to prove human-like
9.9/10 narration by itself. With the default `BENGALI_AUDIO_QA_THRESHOLD=9.3`,
generated audio may be held as `needs manual review` unless a listening review
is recorded with `--human-reviewed`, or you deliberately allow a review commit
with `--allow-review-commit`.

## 3c. English audiobook QA and polishing

Use `scripts/audio/polishEnglishAudiobooks.js` for English audiobooks. It is
parallel to the Bengali job but uses separate `ENGLISH_*` config, English
normalization, English pause/prosody rules, and provider-aware TTS execution.
Azure remains supported, but free non-Azure providers can be used when Azure
credits are disabled. Dry-run is still the default; production audio is not
uploaded or patched unless `--commit` is present.

Recommended free Edge TTS configuration:

```bash
ENGLISH_TTS_PROVIDER=edge
# Optional override. The built-in edge provider uses this command shape by default:
EDGE_TTS_COMMAND='edge-tts --voice en-IN-NeerjaNeural --rate=+4% --pitch=+1Hz --file "{input}" --write-media "{output}"'
ENGLISH_TTS_SUPPORTS_SSML=false
ENGLISH_TTS_VOICE_ID=en-IN-NeerjaNeural
ENGLISH_AUDIO_QA_THRESHOLD=9.3
ENGLISH_TTS_RATE=+4%
ENGLISH_TTS_PITCH=+1Hz
ENGLISH_TTS_PAUSE_PROFILE=english-natural-expressive
ENGLISH_TTS_CHUNK_CHARS=3600
ENGLISH_TTS_CONCURRENCY=1
ENGLISH_TTS_REQUEST_DELAY_MS=3000
ENGLISH_TTS_MAX_RETRIES=8
ENGLISH_TTS_RETRY_BASE_DELAY_MS=30000
ENGLISH_TTS_RETRY_MAX_DELAY_MS=600000
ENGLISH_TTS_RETRY_JITTER=true
ENGLISH_TTS_PAUSE_ON_429=true
ENGLISH_AUDIO_PRONUNCIATION_LEXICON=
ENGLISH_TTS_KEEP_CHUNKS=true
```

Azure configuration if the Speech resource is active again:

```bash
ENGLISH_TTS_PROVIDER=azure
AZURE_ENGLISH_TTS_COMMAND='node scripts/audio/tts/azureEnglishTts.js --input "{input}" --output "{output}" --voice "en-IN-NeerjaNeural"'
ENGLISH_TTS_SUPPORTS_SSML=true
ENGLISH_TTS_VOICE_ID=en-IN-NeerjaNeural
AZURE_ENGLISH_VOICE=en-IN-NeerjaNeural
AZURE_ENGLISH_LOCALE=en-IN
```

Piper local/offline configuration:

```bash
ENGLISH_TTS_PROVIDER=piper
PIPER_TTS_COMMAND='scripts/audio/tts/piperEnglishTts.sh "{input}" "{output}"'
ENGLISH_TTS_SUPPORTS_SSML=false
ENGLISH_TTS_VOICE_ID=en_US-lessac-medium
PIPER_ENGLISH_MODEL=models/piper/en/en_US-lessac-medium.onnx
```

Alternative Azure male voice:

```bash
ENGLISH_TTS_VOICE_ID=en-IN-PrabhatNeural
AZURE_ENGLISH_VOICE=en-IN-PrabhatNeural
```

When `ENGLISH_TTS_SUPPORTS_SSML=false`, the polish script writes plaintext TTS
input. It preserves punctuation normalization and pronunciation replacements,
but it does not send raw `<speak>`, `<voice>`, `<prosody>`, or `<break>` tags to
the provider. Chunk cache metadata stores provider, voice, and SSML/plaintext
mode, so switching from Azure to Edge/Piper does not accidentally reuse mixed
provider chunks unless `--reuse-mixed-provider` is passed explicitly.
The built-in `edge` and `piper` providers ignore a stale generic
`ENGLISH_TTS_COMMAND`; use `ENGLISH_TTS_PROVIDER=command` only when you want to
run a fully custom command.

Commands:

```bash
ENGLISH_TTS_PROVIDER=edge node scripts/audio/polishEnglishAudiobooks.js --slug dracula --dry-run --concurrency 1 --job-id english-polish-edge-v1 --force --verbose
ENGLISH_TTS_PROVIDER=edge node scripts/audio/polishEnglishAudiobooks.js --sample 3 --dry-run --concurrency 1 --job-id english-polish-edge-sample-v1 --verbose
ENGLISH_TTS_PROVIDER=edge node scripts/audio/polishEnglishAudiobooks.js --all-english --dry-run --concurrency 1 --job-id english-polish-edge-queue-v1 --verbose
ENGLISH_TTS_PROVIDER=edge node scripts/audio/polishEnglishAudiobooks.js --slug dracula --commit --concurrency 1 --job-id english-polish-edge-v1 --force
```

The English job writes reports under
`output/english_audiobook_polish/<job-id>/english_audiobook_polish_report.json`.
Large MP3s continue to use the existing Cloudinary/B2 routing; reader playback
still relies on byte-range streaming and `preload="metadata"`.
If Azure returns `HTTP 401`, the job marks the run as `BLOCKED_AUTH` with a
clear credential/subscription message instead of retrying it like quota.

## 3d. Orphaned audiobook storage cleanup

Use `scripts/audio/cleanupAudiobookStorage.js` after polished audiobooks have
been verified in the reader. This cleanup job compares every live admin book's
current `audiobook_assets` and nested `audiobook` URLs against Cloudinary and
Backblaze B2 objects under configured audiobook prefixes. It writes a report by
default and deletes only when `--commit-delete` is explicitly present.

Default scanned prefixes:

```bash
earnalism/audiobooks/
earnalism/audiobooks-polished/
```

Generate the cleanup report only:

```bash
railway run --service earnalism --environment production -- \
  npm run audiobook:storage:cleanup -- \
  --job-id audiobook-storage-cleanup-report \
  --env-file .secrets/earnalism-import.env
```

Scan only B2:

```bash
railway run --service earnalism --environment production -- \
  npm run audiobook:storage:cleanup -- \
  --provider b2 \
  --job-id audiobook-b2-cleanup-report \
  --env-file .secrets/earnalism-import.env
```

Scan only Cloudinary:

```bash
railway run --service earnalism --environment production -- \
  npm run audiobook:storage:cleanup -- \
  --provider cloudinary \
  --job-id audiobook-cloudinary-cleanup-report \
  --env-file .secrets/earnalism-import.env
```

Delete reviewed orphan candidates after the dry-run report looks correct:

```bash
railway run --service earnalism --environment production -- \
  npm run audiobook:storage:cleanup -- \
  --commit-delete \
  --min-age-days 7 \
  --delete-limit 50 \
  --job-id audiobook-storage-cleanup-delete-v1 \
  --env-file .secrets/earnalism-import.env
```

The report is written to:

```text
output/audiobook_storage_cleanup/<job-id>/audiobook_storage_cleanup_report.json
```

Safety rules:

- dry-run is the default
- `--commit-delete` is required for deletion
- objects referenced by any admin book are never candidates
- recent orphan uploads are protected by `--min-age-days`
- `--delete-limit` caps every destructive run
- the cleanup does not modify MongoDB, reader behavior, or SEO metadata

Optional cleanup env defaults:

```bash
AUDIOBOOK_CLEANUP_PREFIXES=earnalism/audiobooks/,earnalism/audiobooks-polished/
AUDIOBOOK_CLEANUP_MIN_AGE_DAYS=2
AUDIOBOOK_CLEANUP_DELETE_LIMIT=100
```

Use `--lang en` or `--lang ben` to split long catalog jobs. The script skips
books that already have reader-ready `audiobook_assets.mp3` and
`audiobook_assets.timestamps` mapped in the database unless
`--no-skip-live-audio-assets` is passed.

For premium Bengali narration on a GPU-capable machine:

```bash
python3 scripts/open_source_audiobook_onboarding.py generate \
  --lang ben \
  --bengali-provider indic-parler-tts \
  --indic-model ai4bharat/indic-parler-tts
```

Cloudinary upload mapping:

- `mp3` uploads as Cloudinary `video`
- `timestamps`, `vtt`, `chapters`, and `meta` upload as Cloudinary `raw`
- returned HTTPS URLs are stored on the book under `audiobook_assets`
- the reader prefers those URLs before falling back to `/audio/{lang}/{slug}...`

For a safe first production pass, run one title first:

```bash
python3 scripts/open_source_audiobook_onboarding.py generate \
  --book-slug the-gift-of-the-magi \
  --copy-to-public \
  --sync-flags
```

Every run writes a JSON report to `output/audio_onboarding/`. The script does
not write story content back to the platform; it only reads chapters, writes
local narration text snapshots, generates audio assets, and optionally calls
`PATCH /api/admin/books/{slug}/audiobook` after validation passes.

For the complete catalog, prefer object storage/CDN for generated audio instead
of committing every MP3 into the Vercel frontend. Set:

```bash
REACT_APP_AUDIO_ASSET_BASE_URL=https://your-audio-cdn.example
```

The reader falls back to `/audio/{lang}/{slug}...` when the variable is empty.

English only:

```bash
python generate_audio.py \
  --manifest book_import_manifest.json \
  --lang en \
  --output-dir ./audio_output/
```

Single book:

```bash
python generate_audio.py \
  --manifest book_import_manifest.json \
  --slug denapaona \
  --output-dir ./audio_output/
```

Use pre-scraped text:

```bash
python generate_audio.py \
  --manifest book_import_manifest.json \
  --text-dir ./texts/ \
  --output-dir ./audio_output/
```

WaveNet tier for English:

```bash
python generate_audio.py \
  --manifest book_import_manifest.json \
  --lang en \
  --voice-tier wavenet \
  --output-dir ./audio_output/
```

## 4. voices.json reference

`voices.json` controls provider selection and voice tuning:

```json
{
  "ben": {
    "primary_provider": "sarvam",
    "sarvam": {
      "target_language_code": "bn-IN",
      "speaker": "anushka",
      "pace": 0.82,
      "pitch": 0.0,
      "loudness": 1.5,
      "model": "bulbul:v2",
      "enable_preprocessing": true,
      "speech_sample_rate": 22050
    },
    "fallback_provider": "google",
    "google": {
      "neural2": {
        "primary": "bn-IN-Wavenet-C",
        "fallback": "bn-IN-Wavenet-D"
      },
      "wavenet": {
        "primary": "bn-IN-Wavenet-C",
        "fallback": "bn-IN-Wavenet-D"
      },
      "rate": "-12%",
      "pitch": "-2%"
    }
  }
}
```

For Bengali batches where low-latency reader highlighting is more important than Sarvam voice style, set `"primary_provider": "google"` in the Bengali voice config. The generator will use the same `{slug}_timestamps.json` schema and skip future reruns when `{slug}.mp3` already exists.

When Google credentials are not available for an operator machine, set `ENABLE_GOOGLE_FALLBACK=0` before a Sarvam batch. A Sarvam outage will then skip the affected book with a clear log entry instead of spending minutes on a fallback that cannot authenticate.

Sarvam pace guide:

- `0.70`: slow and dramatic
- `0.82`: comfortable literary Bengali narration
- `1.00`: default conversational pace

Swap speakers or Google voice names in `voices.json`; no script edit is needed.
Google currently exposes Bengali Wavenet/Standard/Chirp voices, but not Bengali Neural2 voices in this project. The Bengali Google fallback therefore uses Wavenet voices because they support SSML marks for word-highlight timestamps; Chirp audio works, but returned no SSML mark timepoints in local testing.

## 5. Cost table

| Provider | Language | Tier | Per 1K chars | 67-book estimate |
| --- | --- | --- | --- | --- |
| Sarvam AI | Bengali | Neural | ~$0.00 | ~$0.00 if free tier covers catalog |
| Google Cloud | English | Neural2 | $0.016 | ~$2.68 |
| Google Cloud | English | WaveNet | $0.008 | ~$1.34 |
| Google Cloud | Bengali | Neural2 | $0.016 | fallback only |

The script writes `audio_output/cost_log.csv` with:

```text
slug,language,provider_used,voice,characters,estimated_cost_usd,generated_at
```

Dry runs estimate Google SSML overhead by adding 15% to raw character count.

## 6. Output directory

```text
audio_output/
├── ben/
│   ├── denapaona.mp3
│   ├── denapaona_timestamps.json
│   ├── denapaona_highlight.vtt
│   ├── denapaona_chapters.json
│   └── denapaona_meta.json
├── en/
│   ├── hungry-stones.mp3
│   ├── hungry-stones_timestamps.json
│   ├── hungry-stones_highlight.vtt
│   ├── hungry-stones_chapters.json
│   └── hungry-stones_meta.json
├── texts/
│   └── denapaona.txt
├── cost_log.csv
└── error_log.json
```

## 7. Word highlight sync wiring

1. Place files in the frontend public folder:

```text
frontend/public/audio/{lang}/{slug}.mp3
frontend/public/audio/{lang}/{slug}_timestamps.json
```

2. Add the audio element:

```html
<audio id="earnalism-audio" src="/audio/ben/denapaona.mp3" preload="metadata"></audio>
```

3. Add language metadata to the reading surface:

```html
<div class="chapter-body" data-lang="ben"></div>
```

4. Include `highlight_sync.js` and initialize after fonts load:

```html
<script src="/highlight_sync.js"></script>
<script>
  document.fonts.ready.then(() => {
    window.EarnalismHighlightSync.initReader("denapaona", "ben");
  });
</script>
```

5. The helper wraps each word in:

```html
<span class="word-token" data-index="0">...</span>
```

6. CSS classes use Earnalism tokens:

```css
.word-token {
  display: inline;
  border-radius: 2px;
  transition: background 0.15s ease, color 0.3s ease;
}
.word-active {
  background: var(--earnalism-gold-light);
  color: var(--earnalism-ink);
}
.word-read {
  color: var(--earnalism-muted);
}
```

For Bengali, wait for `Noto Serif Bengali` or `Noto Sans Bengali` before tokenization so text wrapping remains stable.

## 8. SSML and pacing reference

### Bengali Google SSML

| Punctuation | Markup |
| --- | --- |
| `।` | `।<break time="650ms"/>` |
| `॥` | `॥<break time="950ms"/>` |
| `…` or `...` | `<break time="750ms"/>` |
| `—` | `<break time="400ms"/>` |
| `,` | `,<break time="180ms"/>` |
| `;` | `;<break time="280ms"/>` |
| `:` | `:<break time="300ms"/>` |
| paragraph break | `<break time="950ms"/>` |
| question | `<prosody pitch="+6%" rate="-5%">...</prosody><break time="550ms"/>` |
| exclamation | `<prosody pitch="+4%" rate="+3%">...</prosody><break time="500ms"/>` |

Outer Bengali prosody: `rate="-12%" pitch="-2%"`.

### English Google SSML

| Punctuation | Markup |
| --- | --- |
| `.` | `.<break time="580ms"/>` |
| `…` or `...` | `<break time="700ms"/>` |
| `—` | `<break time="380ms"/>` |
| `,` | `,<break time="160ms"/>` |
| `;` | `;<break time="260ms"/>` |
| `:` | `:<break time="280ms"/>` |
| paragraph break | `<break time="880ms"/>` |
| question | `<prosody pitch="+7%" rate="-4%">...</prosody><break time="520ms"/>` |
| exclamation | `<prosody pitch="+5%" rate="+4%">...</prosody><break time="480ms"/>` |

Outer English prosody: `rate="-8%" pitch="-1%"`.

### Sarvam Bengali preprocessing

Sarvam does not support SSML, so spacing is used for subtle pacing:

- `।` → `।  `
- `॥` → `॥   `
- `—` → ` — `
- `…` or `...` → `...  `
- paragraph breaks are used as chunk boundaries

## 9. Troubleshooting

**stable-whisper timestamps are off by 1–2 seconds**

Use a larger Whisper model by editing `stable_whisper_model()` to load `small`, then regenerate the affected book. Confirm temp WAV files are 22050Hz mono before alignment.

**Sarvam returns garbled audio on long chunks**

Lower `MAX_SARVAM_CHARS` in `generate_audio.py` from `500` to `350`, or reduce paragraph length in the cached text file.

**Google timepoints are shorter than word count**

Check `insert_word_marks()` in `generate_audio.py`. Marks must appear before every whitespace-delimited word token and never inside SSML tags.

**Word highlights drift after a chapter**

Check offset accumulation. The script measures duration after ffmpeg normalization, not from raw API response size, to keep offsets consistent.

**Bengali words split incorrectly**

The reader helper splits on whitespace only, preserving ZWJ and ZWNJ inside Bengali tokens. Avoid custom regex that splits inside Bengali conjuncts.

**Audio plays but highlighting does not appear**

Check browser console for `/audio/{lang}/{slug}_timestamps.json` fetch errors, confirm `.chapter-body` exists, and confirm `initReader(slug, lang)` runs after fonts are ready.
