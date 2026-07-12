# A Ghost Story Parallel Sprint Report

Generated: `2026-07-12T19:35:15Z`

- Slug: `a-ghost-story`
- Language: `English`
- Assigned lane: `1 - Currently Approved Audio Guard`
- Assigned agent: `Russell (019f57d2-6c5c-7792-a11d-0c4468ac6226)`
- Public reader: `Yes`
- Public audiobook: `Yes`
- Quality evidence: `ASR/source 9.88/10; first/last PASS; 6 listening samples 9.4-9.5, confidence 0.95, no fatal flags; 10.0 not claimed`
- Estimated remaining cost: `$0.3000`
- Final state: `Yes, publicly rendered book + Yes, publicly available audiobook`
- Blocker: `NONE`
- Evidence: `internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_release_gate_evidence.json`
- Next action: Monitor the approved endpoint and continue the Sprint 1 queue with The Open Window replacement-provider audition.

## Next Command

```bash
curl -sS -H 'Range: bytes=0-1023' -o /dev/null -w '%{http_code} %{size_download}\n' https://api.theearnalism.com/api/reader/book/a-ghost-story/audiobook
```

No provider call, release-gate mutation, or public audio exposure was performed by this materializer.

## Approved-Audio Guard

The manifest, checksum, six-sample QA, and HTTP range endpoint pass. All 2,450 production word timestamps use `start`/`end` seconds, while the deployed Reader consumed `start_ms`. Classification: `FRONTEND_READER_TIMING_SCHEMA_MISMATCH`. Existing Google audio is reusable; no provider retry is warranted.
