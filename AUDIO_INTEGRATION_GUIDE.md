# English Audio Integration Guide

## Overview

This guide explains how to integrate the English audio player with word-level highlight sync into your reader.

## Architecture

```
AudioPlayer Component
    ↓
Load MP3 from CDN (Cloudinary)
    ↓
Fetch timestamps JSON
    ↓
Tokenize story text into words
    ↓
Sync playback with highlights
```

## Files Created

| File | Purpose |
|------|---------|
| `frontend/src/components/AudioPlayer.jsx` | React audio player component |
| `frontend/src/components/AudioPlayer.css` | Styling for player and highlights |
| `deploy_audio_to_cdn.py` | Upload to Cloudinary CDN |
| `deploy_english_audio.sh` | Master deployment script |
| `test_audio_sync.py` | Test suite for audio sync |

## Integration Steps

### Step 1: Add AudioPlayer to SecureReader

In your reader component, import and render the AudioPlayer:

```jsx
// frontend/src/components/SecureReader.jsx
import AudioPlayer from "./AudioPlayer";

export default function SecureReader({
  bookSlug,
  title,
  lang = "en",
  // ... other props
}) {
  return (
    <section className="secure-reader">
      {/* Audio Player */}
      {lang === "en" && (
        <AudioPlayer
          bookSlug={bookSlug}
          title={title}
          lang="en"
        />
      )}

      {/* Story Content */}
      <div className="chapter-body">
        {/* Content will be auto-tokenized for highlight sync */}
      </div>
    </section>
  );
}
```

### Step 2: Update Book Detail Page

In your book detail/chapter pages:

```jsx
// frontend/src/pages/BookDetail.jsx
import AudioPlayer from "../components/AudioPlayer";
import { useParams } from "react-router-dom";

export default function BookDetail() {
  const { slug } = useParams();
  const book = /* ... fetch book data */;

  return (
    <div>
      <h1>{book.title}</h1>

      {/* Show audio player for English books */}
      {book.language === "en" && (
        <AudioPlayer
          bookSlug={slug}
          title={book.title}
          lang="en"
        />
      )}

      {/* Reader view */}
      <SecureReader
        bookSlug={slug}
        title={book.title}
        lang={book.language}
        html={book.html}
      />
    </div>
  );
}
```

### Step 3: Ensure Text Tokenization

The AudioPlayer automatically tokenizes text into words. Ensure your story content is in a container with class `chapter-body`:

```jsx
<div className="chapter-body">
  <p>The Tell-Tale Heart by Edgar Allan Poe</p>
  <p>TRUE!—nervous—very, very dreadfully nervous I had been...</p>
  {/* More content */}
</div>
```

### Step 4: CDN Configuration

Audio files are fetched from:
- **MP3**: `https://res.cloudinary.com/earnalism/video/upload/audio/en/{slug}.mp3`
- **Timestamps**: `https://res.cloudinary.com/earnalism/raw/upload/audio/en/{slug}_timestamps.json`

The AudioPlayer handles this automatically using the `bookSlug` prop.

### Step 5: Styling

The AudioPlayer comes with built-in styling in `AudioPlayer.css`. The active word highlight uses these classes:

```css
.word-token {
  /* Inactive word */
  transition: background-color 0.08s ease;
}

.word-token.active {
  /* Currently playing word */
  background-color: rgba(212, 168, 67, 0.35);
  color: var(--brand-burgundy);
  font-weight: 600;
  padding: 0 2px;
  border-radius: 2px;
}
```

## API Reference

### AudioPlayer Props

```jsx
<AudioPlayer
  bookSlug="the-tell-tale-heart"      // Required: Book identifier
  title="The Tell-Tale Heart"          // Required: Display title
  lang="en"                            // Optional: Language (default: "en")
  onSyncReady={(ready) => {}}         // Optional: Callback when sync loads
  className="my-custom-class"          // Optional: Additional CSS class
/>
```

### Events

The AudioPlayer exposes these events via the `onSyncReady` callback:

```jsx
<AudioPlayer
  bookSlug={slug}
  title={title}
  onSyncReady={(syncReady) => {
    if (syncReady) {
      console.log("✓ Audio sync is ready");
    } else {
      console.log("✗ Could not load timestamps");
    }
  }}
/>
```

## Testing

### Test on Sample Books

```bash
# Run test suite on sample books
python3 test_audio_sync.py \
  --audio-dir ./audio_output/en \
  --books the-tell-tale-heart the-gift-of-the-magi the-necklace
```

### Manual Testing

1. Open reader page with English book
2. Audio player should appear
3. Click Play button
4. Words should highlight as audio plays
5. Click on any position in progress bar to seek
6. Verify highlight follows playback

### Debug Mode

Check browser console for:

```javascript
// AudioPlayer logs
console.log("Loaded X words from timestamps");
console.log("Current word index:", currentWordIndex);
```

## Deployment

### Quick Start

```bash
# Make script executable
chmod +x deploy_english_audio.sh

# Run full deployment
./deploy_english_audio.sh ./audio_output/en ./book_import_manifest.json
```

### Manual Steps

1. **Test** sample books:
   ```bash
   python3 test_audio_sync.py
   ```

2. **Deploy** to CDN:
   ```bash
   python3 deploy_audio_to_cdn.py \
     --audio-dir ./audio_output/en \
     --manifest ./book_import_manifest.json
   ```

3. **Verify** deployment:
   ```bash
   cat ./audio_output/cloudinary_deployment_manifest.json
   ```

4. **Integrate** into reader code (see steps above)

## Troubleshooting

### Audio player not appearing

- Check book `language` field is set to "en"
- Verify `bookSlug` is correct
- Check browser console for errors

### Timestamps not loading

- Verify CDN URLs are accessible:
  ```bash
  curl https://res.cloudinary.com/earnalism/raw/upload/audio/en/the-tell-tale-heart_timestamps.json
  ```
- Check CORS settings on Cloudinary
- Verify timestamp file exists in deployment manifest

### Highlights not syncing

- Check `.word-token` elements exist in DOM
- Verify timestamps have `start_ms` and `end_ms` fields
- Check browser console for JavaScript errors
- Ensure audio is actually playing (not paused)

### Audio cutting off early

- This is likely a source file issue, not a sync issue
- Check MP3 duration: `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1:nofile=1 audio.mp3`
- Regenerate audio if needed: `python3 generate_audio.py --lang en --slug {slug}`

## Performance Notes

- Timestamps are cached by browser (Cache-Control headers)
- AudioPlayer uses lazy loading for audio
- Word highlighting uses CSS transitions (60fps)
- Binary search for word lookup is O(log n)

## Browser Support

| Browser | Audio | Highlight |
|---------|-------|-----------|
| Chrome 90+ | ✓ | ✓ |
| Firefox 88+ | ✓ | ✓ |
| Safari 14+ | ✓ | ✓ |
| Edge 90+ | ✓ | ✓ |

## Security Notes

- Audio files are served from Cloudinary with SSL
- Timestamps are static JSON files
- No authentication required (public-facing content)
- DRM/watermarking handled separately by SecureReader

## Analytics

Track audio engagement with:

```javascript
// In your analytics code
function trackAudioEvent(event, bookSlug) {
  analytics.track('audio_' + event, {
    book_slug: bookSlug,
    timestamp: new Date().toISOString()
  });
}

// Then in reader:
<AudioPlayer
  {...props}
  onPlay={() => trackAudioEvent('play', slug)}
  onPause={() => trackAudioEvent('pause', slug)}
  onSeek={(time) => trackAudioEvent('seek', slug)}
/>
```

## Next Steps

1. ✅ Audio generated with emotional expression
2. ✅ Deployed to Cloudinary CDN
3. ✅ React component created
4. → Integrate into reader UI
5. → Test on 3-5 sample books
6. → Collect user feedback
7. → Deploy to production
8. → Scale to other languages

---

**Last Updated:** June 6, 2026
**Status:** Ready for integration
**Contact:** For technical support, see ENGLISH_AUDIO_SYNC_PIPELINE.md
