# Earnalism English Audio Generation & Sync Pipeline

## Overview

This document describes the complete pipeline for generating and syncing English audiobooks with highlighted story text for all draft books.

## Status

**Current Process:** Audio generation for 100 English draft books is running.

### Configuration Used
- **Provider:** Google Cloud Text-to-Speech
- **Voice:** en-IN-Neural2-B (Indian English with emotional expression)
- **Voice Settings:**
  - Rate: -8% (slower, more deliberate pacing for emotional depth)
  - Pitch: -1% (slightly deeper tone for better presence)
- **Word-Level Sync:** SSML marks for precise timestamp generation
- **Output:** MP3 audio + JSON timestamp files

## Generated Pipeline Scripts

### 1. `generate_english_audio_sync.py`
Orchestrates the complete audio generation and sync pipeline for English books.

**Features:**
- Filters manifest for English books in draft state
- Validates audio generation requirements
- Generates comprehensive sync report
- Verifies output files

**Usage:**
```bash
# Generate audio for all English draft books
python3 generate_english_audio_sync.py \
  --manifest book_import_manifest.json \
  --output-dir ./audio_output

# Verify existing files without re-generating
python3 generate_english_audio_sync.py \
  --manifest book_import_manifest.json \
  --output-dir ./audio_output \
  --verify-only
```

## Output Structure

```
audio_output/
├── en/
│   ├── en-001.mp3                    # Generated audio file
│   ├── en-001_timestamps.json        # Word-level sync markers
│   ├── en-002.mp3
│   ├── en-002_timestamps.json
│   └── ... (100 files total)
├── texts/
│   └── [cached source text files]
└── english_audio_sync_report.json    # Generation report
```

## Timestamps JSON Format

Each `_timestamps.json` file contains:

```json
{
  "slug": "en-001",
  "language": "en",
  "words": [
    {
      "word": "For",
      "start_ms": 0,
      "end_ms": 250
    },
    {
      "word": "your",
      "start_ms": 250,
      "end_ms": 520
    }
    // ... more words
  ]
}
```

## Reader Integration

### JavaScript Sync Module

The `highlight_sync.js` script handles real-time synchronization:

1. **Load Timestamps:** Fetches JSON file for the active book slug
2. **Tokenize Text:** Wraps story text in word-level `<span>` elements
3. **Binary Search:** Efficient O(log n) lookup for current word during playback
4. **Highlight Updates:** As audio plays, active word is highlighted in real-time
5. **CSS Classes:** `.word-token` class enables custom styling

### Integration Steps

```html
<!-- 1. Include audio element -->
<audio id="earnalism-audio" controls>
  <source src="/audio/en/book-slug.mp3" type="audio/mpeg">
</audio>

<!-- 2. Story text container -->
<div class="chapter-body">
  <!-- Story content auto-tokenized -->
</div>

<!-- 3. Include sync script -->
<script src="/highlight_sync.js"></script>
<script>
  EarnalismHighlightSync.attach({
    slug: 'en-001',
    lang: 'en',
    bodySelector: '.chapter-body',
    audioSelector: '#earnalism-audio'
  });
</script>
```

### CSS for Highlighting

```css
.word-token {
  transition: background-color 0.1s ease, color 0.1s ease;
}

.word-token.active {
  background-color: rgba(212, 168, 67, 0.35);
  color: var(--brand-burgundy);
  font-weight: 600;
}
```

## Voice Characteristics

**Google Neural2 en-IN-Neural2-B** has been selected for:

- **Emotional Expression:** Natural pacing allows for emotional depth in Gothic/literary works
- **Voice Clarity:** Indian English variant provides distinct, clear articulation
- **Intensity Control:** -8% rate adjustment creates deliberate, engaging narration
- **Listener Appeal:** Suitable for long-form reading sessions without fatigue

## Books Being Processed

All 100 English draft books:

1. EN-001: The Tell-Tale Heart
2. EN-002: The Fall of the House of Usher
3. EN-003: The Murders in the Rue Morgue
4. EN-004: The Masque of the Red Death
5. EN-005: The Cask of Amontillado
... (95 more titles)

## Monitoring Progress

### Check Generation Log
```bash
tail -f english_audio_sync.log
```

### Monitor Audio Files
```bash
# Count generated MP3 files
ls -1 audio_output/en/*.mp3 | wc -l

# Count timestamp files
ls -1 audio_output/en/*_timestamps.json | wc -l

# Check total size
du -sh audio_output/en/
```

### View Sync Report
```bash
cat audio_output/english_audio_sync_report.json | jq
```

## Cost Considerations

Google Cloud TTS pricing for English (Neural2):
- $0.016 per 1,000 characters
- Average book: ~160K characters = ~$2.56 per book
- 100 books estimate: ~$256 total

All costs are monitored and logged in the generation output.

## Troubleshooting

### Authentication Issues
```bash
# Refresh Google Cloud credentials
gcloud auth application-default login
```

### Resume Interrupted Generation
The script caches generated files by slug. To retry:
```bash
# Files are cached - delete specific MP3 to regenerate
rm audio_output/en/en-001.mp3
rm audio_output/en/en-001_timestamps.json

# Then rerun the pipeline
python3 generate_english_audio_sync.py \
  --manifest book_import_manifest.json \
  --output-dir ./audio_output
```

### Verify Timestamp Sync
```bash
# Test sync on a specific book
python3 -c "
import json
with open('audio_output/en/en-001_timestamps.json') as f:
    data = json.load(f)
print(f'Words: {len(data[\"words\"])}')
print(f'Duration: {data[\"words\"][-1][\"end_ms\"]/1000:.1f}s')
print('First 5 words:', [w['word'] for w in data['words'][:5]])
"
```

## Next Steps

1. **Wait for generation to complete** (~2-4 hours for 100 books)
2. **Verify all MP3 + JSON files** exist in `audio_output/en/`
3. **Review sync report** at `audio_output/english_audio_sync_report.json`
4. **Deploy to CDN** (audio files should be served from `/audio/en/` path)
5. **Enable in reader UI** by updating book detail pages with audio player
6. **Test highlights** with sample books before full rollout

## Integration Checklist

- [ ] All 100 MP3 files generated
- [ ] All 100 timestamp JSON files created
- [ ] Audio files uploaded to CDN at `/audio/en/{slug}.mp3`
- [ ] Timestamp files accessible at `/audio/en/{slug}_timestamps.json`
- [ ] Reader template updated with audio player
- [ ] `highlight_sync.js` deployed to frontend
- [ ] CSS styling added for word highlights
- [ ] Testing completed on 3-5 sample books
- [ ] Reader launch for English books

## Files Reference

- **Generation Script:** `generate_audio.py` (main pipeline)
- **Sync Orchestrator:** `generate_english_audio_sync.py` (new)
- **Highlight Sync:** `highlight_sync.js` (reader integration)
- **Voice Config:** `voices.json` (contains all TTS settings)
- **Manifest:** `book_import_manifest.json` (book catalog)

---

**Generated:** June 6, 2026
**Status:** Audio generation in progress
**Expected Completion:** Monitor log for progress updates
