# Earnalism Neural Audio Generation

`generate_audio.py` batch-generates Bengali and English audiobook assets for legally cleared Earnalism books using Microsoft Azure Neural TTS.

## Setup

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Install `ffmpeg` and confirm both commands are available:

```bash
ffmpeg -version
ffprobe -version
```

Set Azure credentials in your shell or a local, ignored secrets file:

Use your local shell or ignored secrets file for `AZURE_SPEECH_KEY` and
`AZURE_SPEECH_REGION`; do not commit credential exports.

The script never reads or writes hardcoded Azure credentials.

## Usage

Full batch run:

```bash
python generate_audio.py --manifest book_import_manifest.json --output-dir ./audio_output/
```

Dry run with SSML and cost estimates only:

```bash
python generate_audio.py --manifest book_import_manifest.json --dry-run
```

Single book by slug:

```bash
python generate_audio.py --manifest book_import_manifest.json --slug denapaona
```

Use pre-scraped source text:

```bash
python generate_audio.py --manifest book_import_manifest.json --text-dir ./texts/
```

If `--text-dir` is provided, files must be named `{slug}.txt`. The slug is taken from `audio_slug`, then `slug`, then the source URL or title.

## Azure Pricing

The cost log uses the provided Neural TTS estimate of `$0.016 / 1,000 characters`.

Each run writes:

- `audio_output/cost_log.csv`
- `audio_output/error_log.json` if synthesis or fallback issues occur
- `audio_output/scrape_failures.json` if source extraction fails

Reruns are credit-optimized: if `{slug}.mp3` already exists, synthesis is skipped and cost is logged as zero for that book.

## Voice Configuration

Voices are configured in `voices.json`:

```json
{
  "ben": {
    "locale": "bn-IN",
    "primary": "bn-IN-TanishaaNeural",
    "fallback": "bn-IN-BashkarNeural"
  },
  "en": {
    "locale": "en-IN",
    "primary": "en-IN-NeerjaNeural",
    "fallback": "en-IN-PrabhatNeural"
  }
}
```

Swap `primary` or `fallback` values without editing the script.

## Output Files

For each book:

- `{slug}.mp3`: 48 kbps mono MP3 for broad browser support.
- `{slug}_timestamps.json`: word-boundary timing in `[{"word","start_ms","end_ms"}]` format.
- `{slug}_chapters.json`: chapter heading start offsets.
- `{slug}_highlight.vtt`: one-word WebVTT cues for browser-native text sync.

Note: Opus is not valid inside a standard `.mp3` container. This tool produces 48 kbps mono MP3 as requested by filename and browser compatibility. If the platform later chooses `.opus` or `.webm`, the ffmpeg output command can be changed safely.

## Reader Highlight Wiring

The Earnalism reader can load `{slug}_timestamps.json` or `{slug}_highlight.vtt` beside the audio URL.

Recommended flow:

1. Fetch `{slug}_timestamps.json` when the audiobook starts.
2. On every `audio.timeupdate`, compute `current_ms = audio.currentTime * 1000`.
3. Find the active timing item where `start_ms <= current_ms < end_ms`.
4. Highlight the matching rendered word span in the reader.
5. Fall back to `{slug}_highlight.vtt` if the browser or player supports native text-track cue callbacks.

Keep the rendered book text and audio source text generated from the same cleaned manuscript to avoid word-offset drift.
