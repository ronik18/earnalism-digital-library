# Bengali Post-Live Stabilization PR Readiness

Generated: 2026-07-07T12:55:00Z

## PR

- URL: https://github.com/ronik18/earnalism-digital-library/pull/88
- Number: 88
- Branch: `codex/bengali-post-live-stabilization`
- Commit: `75b1c22a0fa832eee24e343058b79e724097b8f1`
- Base: `codex/source-only-clean-integration`
- Dependency: stacked on `codex/source-only-clean-integration` at `3bd423c608f9f8db437175475fe06a1d7e66fb73`

## Dependency Status

`codex/source-only-clean-integration` is not merged into `origin/main`, and this stabilization branch is based on that source-only base. The PR is therefore intentionally stacked. Do not merge the stabilization patch into `main` before the source-only base unless GitHub diff review explicitly accepts the combined source-only integration diff.

## Scope

- `BookDetail` merges reader-manifest audiobook evidence so `book-2b9853ec52` no longer shows stale "Audiobook held for QA" copy after deploy.
- `audioReleaseSafety` recognizes approved `manifest.audio.url` evidence while keeping incomplete/unapproved Bengali audio hidden.
- Audio safety tests cover manifest-backed approved audio, incomplete evidence blocking, unapproved controls, and paragraph/stanza wording.
- Canary preflight remains preparation-only; no TTS, ASR, sync, upload, metadata mutation, or canary run is included.

## Generated Artifacts Excluded

Excluded from the PR: `internal/audiobook_lab/release_gate/**`, generated audio, sidecars, `frontend/build/**`, screenshots, traces/videos, logs, caches, signed URLs, secrets, generated sitemap, package-lock drift, and local evidence reports not selected for this source-only PR.

## Validation

Already passed in the clean source-only worktree before PR creation:

- Python factory/hooks compile checks
- stop-guard tests
- Sarvam full-pilot hook tests
- listening QA schema tests
- `npm ci --prefix frontend`
- `audioReleaseSafety.test.js` PASS 6/6
- frontend build PASS
- cover audit PASS, 0 typographic-only covers
- visual smoke PASS, 72/72
- `git diff --check` PASS

GitHub/Vercel status is tracked on PR #88. At report creation, Vercel succeeded and the regression suite was still running.

## Merge And Deploy Readiness

Merge readiness is dependency-gated:

1. Review or merge `codex/source-only-clean-integration`.
2. Let PR #88 checks pass against the stacked base.
3. Merge PR #88 only after explicit owner approval.
4. Deploy frontend production through the normal Vercel path.
5. Verify `/book/book-2b9853ec52` no longer shows stale QA-held copy and still gates all unapproved Bengali audio.

No production deploy or metadata mutation was performed by this PR-readiness pass.
