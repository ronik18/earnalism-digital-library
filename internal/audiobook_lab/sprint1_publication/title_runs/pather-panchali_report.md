# পথের পাঁচালী / Pather Panchali Parallel Sprint Report

Generated: `2026-07-12T19:35:15Z`

- Slug: `pather-panchali`
- Language: `Bengali`
- Assigned lane: `5 - Bengali Long / Repair Lane`
- Assigned agent: `Newton (019f57d2-7f7d-74e3-878b-e5d5b2bfc3e5)`
- Public reader: `Yes`
- Public audiobook: `No`
- Quality evidence: `NOT_RUN`
- Estimated remaining cost: `$1.9477`
- Final state: `SPRINT_TARGET_INCOMPLETE`
- Blocker: `OWNER_DOCUMENT_REQUIRED_FOR_AUDIO_RIGHTS_SOURCE_COVER; PAID_RUNTIME_ENV_GATES_MISSING`
- Evidence: `internal/audiobook_lab/sprint1_publication/sanitized_text_reports/pather-panchali.json`
- Next action: Complete reader PR if applicable, then run the title's bounded audio repair path after runtime gates are supplied

## Next Command

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.batch-1.json --book-slug pather-panchali --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```

No provider call, release-gate mutation, or public audio exposure was performed by this materializer.

## Owner Document Checklist

- Identify the exact source/edition and confirm the 12 imported chapters are the intended complete audiobook corpus, or provide the complete corpus.
- Provide source URL/name, license and license URL, author death year, original publication year, rights basis, commercial-use territories, and attribution requirements.
- Approve derivative audiobook rights explicitly and bind the approval to source/content/provenance hashes.
- Provide front/back cover files with creator, provenance, commercial license, and owner approval.
- Record signed owner identity/date, public metadata/CTA decisions, legal review, QA state, publication cap, and rollback owner/plan.
