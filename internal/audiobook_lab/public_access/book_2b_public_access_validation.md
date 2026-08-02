# book-2b9853ec52 Public Access Validation

## Decision

`ALREADY_PUBLIC_APPROVED_NO_MUTATION_REQUIRED`

## Evidence

- Latest complete release packet: `internal/audiobook_lab/release_gate/book-2b9853ec52_20260707T053510Z/`.
- Schema: 3.
- Inventory, cover, manuscript, rights, TTS, ASR/sync, listening QA, upload, metadata, and browser gates: PASS.
- Published: true.
- Production closeout: book API HTTP 200, manifest HTTP 200, `APPROVED`, `QA_PASSED`, provider-backed assets, Audiobook Approved, Listen in Reader, and working player.
- Public asset policy: no static `/audio/...` path and no word-level-sync claim; public copy remains section-following narration.

Older partial ASR reports are historical and are superseded by the complete schema-3 publication packet and same-day production proof.

## Current Refresh Limitation

The current shell again could not resolve `api.theearnalism.com` or `theearnalism.com`. This report therefore uses the production closeout captured at `2026-07-11T14:31:37+05:30` rather than claiming a second live refresh. No P0 source fix was opened because the last authoritative production evidence shows the approved title accessible and functional.

## Next Command

```bash
curl -sS https://api.theearnalism.com/api/reader/book/book-2b9853ec52/manifest | jq '{enabled:.audio.enabled,release_gate:.audio.release_gate,qa_status:.audio.qa_status,provider:.audio.provider,url:.audio.url}'
```
