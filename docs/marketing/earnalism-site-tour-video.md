# Earnalism Premium Site-Tour Video

Purpose: create a 75-90 second premium walkthrough for theearnalism.com that can be used on YouTube, LinkedIn, Instagram, Facebook, X, WhatsApp/community channels, and paid ads.

Positioning:

- Brand line: Earnalism - Where Learning Becomes Earning.
- Core CTA: Preview first. Pay only for reading time. Read beautifully. Listen deeply.
- Growth claim discipline: treat "1000X revenue in 100 days" as an aggressive internal stretch target, never a public guarantee.

## Recording Automation

Run from the repository root:

```bash
npm run marketing:site-tour
```

Useful options:

```bash
SITE_TOUR_HEADED=1 npm run marketing:site-tour
SITE_TOUR_OUTPUT_DIR=output/marketing/site-tour npm run marketing:site-tour
SITE_TOUR_ENGLISH_SLUG=pride-and-prejudice SITE_TOUR_BENGALI_SLUG=bolai npm run marketing:site-tour
SITE_TOUR_SCORE_PATH=/absolute/path/to/music.mp3 npm run marketing:site-tour
node scripts/record_earnalism_site_tour.mjs --dry-run
```

Output:

- Raw recording: `output/marketing/site-tour/earnalism-site-tour-raw.webm`
- Optional scored recording: `output/marketing/site-tour/earnalism-site-tour-with-score.webm`

Optional background score path:

- Preferred local file: `assets/marketing/earnalism-site-tour-score.mp3`
- Or set `SITE_TOUR_SCORE_PATH=/absolute/path/to/score.mp3`
- The script does not fail if the score or `ffmpeg` is missing.

## 75-90 Second Storyboard

| Time | Scene | Visual Direction | Text Overlay | CTA |
| --- | --- | --- | --- | --- |
| 0-6s | Homepage hero | 80% browser zoom, full luxury hero, logo visible | Earnalism - Where Learning Becomes Earning | Preview first |
| 6-14s | Hero CTA and cover rail | Smooth cursor toward Start Reading, scroll to live books | A digital library designed for focus | Start Reading |
| 14-24s | Library browsing | Library page, shelf filters, search, book cards | Browse by shelf, mood, and purpose | Explore the library |
| 24-38s | English reader | Open English reader, show typography and Next Page | Read beautifully | Turn the page |
| 38-48s | English audio | Tap Play if synced audio is available | Listen deeply | Play audiobook |
| 48-62s | Bengali reader | Open Bengali reader, show Bengali rendering and page controls | Bengali classics, rendered with care | Read in Bengali |
| 62-70s | Bengali audio | Tap Play if available; skip gracefully if not | Synced audio when available | Listen |
| 70-80s | Pricing | Pricing page, reading-time packs, no payment click | Pay only for reading time | Choose a pack |
| 80-90s | Final CTA | Return to library with campaign URL | Preview first. Read beautifully. Listen deeply. | Start at theearnalism.com |

## Exact Voiceover Script

Earnalism is a digital library and audiobook platform by Reo Enterprise.

Here, every reading journey starts with trust: preview first, then pay only for the reading time you actually need.

Browse a focused library of Bengali classics, English literature, business, history, technology, young readers, and more.

Open a book into a quiet reader built for attention: elegant typography, calm spacing, and simple next-page and previous-page controls.

For supported titles, tap Play and move between reading and listening with synced narration.

Earnalism is made for thoughtful readers: people who want to read beautifully, listen deeply, and return often.

No subscription pressure. No noisy shelf sprawl. Just preview, choose, read, and listen.

Earnalism - Where Learning Becomes Earning.

Start at theearnalism.com.

## Text Overlay Plan

- Opening: "Earnalism - Where Learning Becomes Earning"
- Hero: "Preview first. Pay only for reading time."
- Library: "Browse curated shelves"
- English reader: "Read beautifully"
- Page controls: "Next page. Previous page. Stay in flow."
- Audio: "Listen deeply with synced narration"
- Bengali reader: "Bengali classics, rendered with care"
- Pricing: "No subscription pressure"
- Final: "Start reading at theearnalism.com"

## CTA Screens

Primary end card:

- Headline: "Preview first. Read beautifully. Listen deeply."
- Subcopy: "Pay only for reading time."
- URL: `theearnalism.com`
- Button text: "Start Reading"

Secondary retargeting end card:

- Headline: "Your next book is waiting."
- Subcopy: "Open a preview before you pay."
- URL: `theearnalism.com/library?utm_source=video&utm_medium=retargeting&utm_campaign=100_day_growth`

## Platform Cuts

YouTube 16:9:

- Export: 1920x1080, 24 or 30 fps, H.264, AAC.
- Use full 75-90s story.
- Add chapters in description: Browse, Read, Listen, Pricing.

Reels/Shorts 9:16:

- Crop with browser centered on the active panel.
- Keep overlays large and below the main UI when possible.
- Use 30s and 15s variants from `docs/marketing/video-variants.md`.

Square 1:1:

- Export 1080x1080.
- Best for carousel ads and feed posts.
- Use the library, reader, and pricing scenes only.

## Background Score Guidance

- Mood: premium, literary, calm, optimistic.
- Instrumentation: piano, warm strings, low ambient texture.
- Avoid: hard beats, dramatic rises, distracting vocals, stock corporate jingles.
- Mix target: music at roughly 14-18% under voiceover.

## Thumbnail Text

Primary thumbnail:

- "Preview First. Read Beautifully."
- Subline: "Earnalism Digital Library"

Alternate thumbnails:

- "Pay Only For Reading Time"
- "Read + Listen In One Place"
- "Bengali Classics. English Literature. One Calm Library."

## Export Settings

- Master: 1920x1080, 30 fps, H.264, 15-20 Mbps, AAC 320 kbps.
- Web preview: 1920x1080, H.264, 8-10 Mbps.
- Short-form: 1080x1920, 30 fps, H.264, 10-14 Mbps.
- Square: 1080x1080, 30 fps, H.264, 8-12 Mbps.
- Captions: burn in short overlays and also upload SRT captions where supported.
