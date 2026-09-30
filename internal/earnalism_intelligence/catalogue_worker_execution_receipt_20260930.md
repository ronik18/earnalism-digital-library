# Catalogue worker execution receipt — 2026-09-30

Source main: `e1fa37b4e15c10494cce7a9532a8389a9caa8a2f`, preserving PR #476, #480, #481, #482 and #483.

## Actual execution finding

Run [36770076565](https://github.com/ronik18/earnalism-digital-library/actions/runs/36770076565), job 110075884855, passed the actual unprivileged-account preflight, permission fixtures, Docker service startup, focused release checks, full regression and service cleanup. The full controller regression took roughly three minutes. All worker shell calls, however, failed before process startup with `Permission denied (os error 13)`. Its final message states that it could not read the batch, inspect candidates, run tests or regenerate state. The action returned success anyway. The no-progress issue comment has been corrected; this is blocked implementation, not evidence exhaustion.

## Narrow correction

Move the one clean ephemeral checkout to the physical canonical `/tmp/earnalism-main-approved-integration` directory and retain the GitHub workspace path only as an alias. Do not create a second checkout or lose source bytes. Resolve the worker permission and ownership operations against the physical path. The suspected symlink/sandbox interaction remains a hypothesis until actual worker commands succeed.

Require a worker-created execution receipt, outside Git, bound to the actual source HEAD and SHA-256 of the controller batch. Missing, STARTED, BLOCKED, stale, mismatched or empty/out-of-batch assessments fail before catalogue recomputation or no-progress reporting. Check that the receipt validator and its tests remain unchanged, run validation as the unprivileged worker without exposing credentials, then return new workspace files to controller ownership. Preserve every existing rights, scope, India, audio, immutable registry/revocation, focused/full regression and exact-head protected merge guard.

Six receipt tests passed locally; six actual-UID/bootstrap fixtures must pass hosted required CI. A normal controller permission smoke does not prove the Codex sandbox can start a process: the new main campaign must show executed commands and a valid completed receipt. No source/title/product/release decision is changed by this repair.

Stale-base PR #484 proposed removing duplicate full regression. Current execution proves that full regression works; it does not fix worker EACCES. The conflicting proposal was closed with evidence, retaining its branch and commit `fc496250ac2e33e5a8fa8d0a25336abbac3715f5`.

The baseline remains 231 assessed / seven accepted live / 224 held / 919 blockers. #347 remains resolved, #380 release/readback and #477 factual holds remain open, and #385 is owner-deferred physical-device UAT. The raw-HTML production canary failure on approved historical unavailable routes is independently reproduced and remains a separate focused source repair; do not revert PR #476's correct UI or historical route continuity.

Next exact command: `gh pr checks <execution-receipt-pr> --repo ronik18/earnalism-digital-library --watch --fail-fast`; after protected merge, inspect actual worker execution and receipt validation, not only the overall green run status.
