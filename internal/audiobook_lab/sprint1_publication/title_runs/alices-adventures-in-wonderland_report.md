# Alice's Adventures in Wonderland Parallel Sprint Report

Generated: `2026-07-12T19:35:15Z`

- Slug: `alices-adventures-in-wonderland`
- Language: `English`
- Assigned lane: `4 - Medium/Long English Lane`
- Assigned agent: `Goodall (019f57d2-7aed-7840-95b5-642a9a5ed578)`
- Public reader: `Yes`
- Public audiobook: `No`
- Quality evidence: `NOT_RUN`
- Estimated remaining cost: `$1.5053`
- Final state: `SPRINT_TARGET_INCOMPLETE`
- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Evidence: `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/alices-adventures-in-wonderland.json`
- Next action: Complete reader PR if applicable, then run the title's bounded audio repair path after runtime gates are supplied

## Next Command

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.batch-1.json --slugs alices-adventures-in-wonderland --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

No provider call, release-gate mutation, or public audio exposure was performed by this materializer.

## Storage Containment

Classification: `PUBLIC_UNAPPROVED_STORAGE_OBJECT_REACHABLE`. Eleven direct URL occurrences were removed from the controlled publication packet. The API/UI remains audio-hidden; remote Cloudinary object revocation or privacy enforcement is still required before any new audition or release work.
