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
