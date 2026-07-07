# Original Workspace Cleanup Plan

Workspace: `/Users/ronikbasak/Documents/GitHub/earnalism-digital-library`

This plan is non-destructive. It documents how to clean the original workspace after the source-only integration branch is reviewed.

## Preserve First

- Preserve `local_evidence_preservation_manifest.json`.
- Preserve Bengali pilot rollback payloads under `internal/audiobook_lab/release_gate/`.
- Preserve `internal/earnalism_intelligence/decision_ledger.jsonl`.
- Preserve `internal/earnalism_intelligence/provider_performance_memory.json`.
- Preserve `internal/earnalism_intelligence/title_decision_history.json`.
- Preserve any source changes already promoted into `/private/tmp/earnalism-source-only-clean-integration`.

## Never Delete Without Owner Review

- `LOCAL_EVIDENCE_PRESERVE_NOT_GIT`
- `ROLLBACK_PAYLOAD_PRESERVE_NOT_GIT`
- `UNKNOWN_REQUIRES_OWNER_DECISION`
- `APPROVED_CONTENT_INPUT_REVIEW_REQUIRED`
- any secrets or signed URL reports

## Safe Cleanup Classes After Approval

Only after `EARNALISM_APPROVE_DESTRUCTIVE_REPO_CLEANUP=true`, remove paths classified as:

- `BUILD_OUTPUT_DELETE_OR_IGNORE`
- `CACHE_DELETE_OR_IGNORE`
- `GENERATED_ARTIFACT_IGNORE`

## Dry-Run Commands

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library
git clean -nd
git clean -ndX
```

## Destructive Cleanup Guard

Do not run destructive cleanup by default. If approved, use the repo hygiene inventory to remove only generated/cache/build classes and never rollback/evidence/content-owner-review paths.
