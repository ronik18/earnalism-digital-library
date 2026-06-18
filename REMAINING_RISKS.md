# Remaining Risks

## Non-Critical Risks

1. **Rights audit uses fixture input in Phase 12.**
   - Current command verifies the rights audit machinery, not a fresh production database export.
   - Mitigation: run `scripts/rights_audit.py` against an approved sanitized admin export before enabling any real publishing.

2. **Catalog audit reports many quarantine recommendations.**
   - The audit intentionally quarantines unknown or missing rights metadata.
   - Mitigation: continue Phase 2 rights metadata backfill before moving items into generation/publishing paths.

3. **First batch remains blocked by source metadata and QA gates.**
   - Phase 11 dry-run reports 0 ready publication drafts and 0 public publish actions.
   - Mitigation: add verified source metadata and rerun dry-run gates item by item.

4. **Audio dry-run does not synthesize or listen-test real audio.**
   - Phase 12 confirms metadata-only planning and guards, not final audiobook quality.
   - Mitigation: keep human listening review and QA threshold before any audiobook publish.

5. **Observability sample reports blocked incidents by design.**
   - The sample includes unsafe budget/audio guardrail cases to prove incident generation.
   - Mitigation: use clean production-safe payloads for operational dashboards, and treat any real HIGH/CRITICAL incident as a release stop.

6. **Production deploy validation is not part of this phase.**
   - Phase 12 does not deploy or publish live content.
   - Mitigation: use the GO LIVE workflow and post-deploy canary after a separate explicit deploy instruction.

7. **Some backend integration tests require a running local API server.**
   - A broad `PYTHONPATH=. pytest backend/tests` probe fails in this local environment because HTTP integration suites target `127.0.0.1:8000`.
   - Mitigation: use the supported CI/release commands for this phase, or start the backend API with its required test services before running the full directory probe.

## Critical Blockers

None found in this phase.

## Public Publishing Risk Position

Public publishing remains disabled by default. The system should not expose generated pages, audio, social drafts, email drafts, or product pages publicly without a future explicit activation PR.
