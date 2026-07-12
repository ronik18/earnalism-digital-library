# গিন্নি Parallel Sprint Report

Generated: `2026-07-12T19:35:15Z`

- Slug: `book-d19e96859f`
- Language: `Bengali`
- Assigned lane: `2 - Short Bengali High-ROI Lane`
- Assigned agent: `Galileo (019f57d2-7210-7930-96bd-df620ee5d77d)`
- Public reader: `Yes`
- Public audiobook: `No`
- Quality evidence: `9.4/10 representative, confidence 0.95; clean 6,485-character full-regeneration preflight PASS; full-book QA not run`
- Estimated remaining cost: `$0.1433`
- Final state: `PROVIDER_RETRY_REQUIRED`
- Blocker: `PAID_RUNTIME_ENV_GATES_MISSING; HISTORICAL_GROUP_REPAIR_CHUNKS_UNAVAILABLE`
- Evidence: `internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_stage2f_preflight.json`
- Next action: Supply the recorded caps and approvals, run one lock-safe fresh Sarvam full-title regeneration with the exact passed Pooja arm, then run ASR/source and listening QA before any release mutation

## Next Command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_stage2f_book_d19_full_tts.py --execute
```

No provider call, release-gate mutation, or public audio exposure was performed by this materializer.
