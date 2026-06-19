# Publication Report

Generated at: `2026-06-19T11:53:17Z`
Mode: `commit`
Status: `PUBLISHED`

## Scope

- Published item: `dracula` only.
- Rights allowed: Tier A approved only.
- Tier B items: not published.
- Tier C items: not published.
- Excluded: full study guide, full visual edition, full audiobook, ads, emails, and social campaigns.
- Publication cap respected: Dracula core reading candidate only.

## Production Mutation

- Mutation performed: `True`
- Matched database rows: `1`
- Modified database rows: `1`
- Cache invalidation: `{'attempted': True, 'error': 'Error 8 connecting to redis.railway.internal:6379. nodename nor servname provided, or not known.', 'reason': 'Redis invalidation failed; live verification may depend on TTL or an admin cache clear.'}`

## Before State

```json
{
  "exists": true,
  "slug": "dracula",
  "title": "Dracula",
  "is_published": true,
  "rights_tier": "A",
  "verification_status": "approved",
  "chapter_count": 27,
  "preview_chapter_count": 0,
  "audiobook_enabled": false,
  "generate_audiobook": false,
  "audiobook_provider": "",
  "audio_asset_count": 0,
  "controlled_publication_status": "PUBLISHED_CORE_READING_ONLY"
}
```

## After State

```json
{
  "exists": true,
  "slug": "dracula",
  "title": "Dracula",
  "is_published": true,
  "rights_tier": "A",
  "verification_status": "approved",
  "chapter_count": 27,
  "preview_chapter_count": 0,
  "audiobook_enabled": false,
  "generate_audiobook": false,
  "audiobook_provider": "",
  "audio_asset_count": 0,
  "controlled_publication_status": "PUBLISHED_CORE_READING_ONLY"
}
```

## Live Verification

```json
{
  "book_api_status": 200,
  "book_slug": "dracula",
  "book_is_published": true,
  "reader_manifest_status": 200,
  "manifest_chapter_count": 27,
  "manifest_audio_enabled": false,
  "manifest_audio_asset_count": 0,
  "preview_chapter_status": 200,
  "preview_chapter_unlocked": true,
  "preview_chapter_content_length": 32123,
  "audiobook_endpoint_status": 404,
  "book_page_status": 200,
  "pass": true,
  "audiobook_endpoint_payload": {}
}
```

## Rollback Plan

- Run a targeted MongoDB update for slug `dracula` only.
- Restore `is_published` to `True`.
- Restore previous `rights_metadata` only if rights rollback is legally required.
- Restore previous audiobook fields only after separate audiobook QA approval.
- Increment Redis `public-cache:generation` and `reader-content-cache:generation` after rollback.
- Re-run live checks for /api/books/dracula and /api/reader/book/dracula/manifest.

## Notes

- No Tier B or Tier C item was changed.
- No audiobook asset was published by this activation.
- No ad, email, social, LLM, TTS, STT, OCR, image, or paid provider call was performed.
