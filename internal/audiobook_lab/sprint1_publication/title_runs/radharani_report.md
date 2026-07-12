# রাধারাণী Parallel Sprint Report

Generated: `2026-07-12T19:35:15Z`

- Slug: `radharani`
- Language: `Bengali`
- Assigned lane: `2 - Short Bengali High-ROI Lane`
- Assigned agent: `Galileo (019f57d2-7210-7930-96bd-df620ee5d77d)`
- Public reader: `Yes`
- Public audiobook: `No`
- Quality evidence: `NOT_RUN`
- Estimated remaining cost: `$0.3681`
- Final state: `SPRINT_TARGET_INCOMPLETE`
- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Evidence: `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/radharani.json`
- Next action: Complete reader PR if applicable, then run the title's bounded audio repair path after runtime gates are supplied

## Next Command

```bash
python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.batch-1.json --slugs radharani --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1
```

No provider call, release-gate mutation, or public audio exposure was performed by this materializer.
