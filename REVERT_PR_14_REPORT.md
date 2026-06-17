# Revert PR #14 Stabilization Report

## Summary

This branch reverts merge commit `f56aacd` using:

```bash
git revert -m 1 f56aacd --no-edit
```

The revert restores the stable post-PR #13 catalog governance state and removes the broad/stale PR #14 changes without adding new features.

## Scope

- Reverted PR #14 merge commit `f56aacd`.
- Preserved Phase 1B public catalog governance files from the post-PR #13 state.
- Added this report for auditability.
- No production content was mutated.

## Validation

| Check | Result |
| --- | --- |
| `python3 -m py_compile backend/server.py` | Passed |
| `node --check scripts/audit-public-content.mjs` | Passed |
| `node --check regression/modules/13-public-content-governance.test.js` | Passed |
| `npm run catalog:audit` | Passed, 251 items audited |
| `npm run regression -- modules/13-public-content-governance.test.js` | Passed, 15/15 tests |
| `npm --prefix frontend run build` | Passed |

## File Health Confirmed

- `scripts/audit-public-content.mjs` has a standalone shebang and normal line breaks.
- `scripts/audit-public-content.mjs` has 1,299 physical lines.
- `regression/modules/13-public-content-governance.test.js` has 295 physical lines.
- `backend/server.py` compiles with Python syntax validation.

## Notes

- The fresh validation worktree required local dependency installation before running Jest and the frontend build.
- `npm --prefix frontend ci` is currently blocked by a pre-existing frontend `package.json` / `package-lock.json` mismatch for TypeScript and React type packages.
- To validate without mutating the lockfile, frontend dependencies were installed with `npm --prefix frontend install --package-lock=false`, then the requested build command was run successfully.
- `npm --prefix frontend run build` regenerated `frontend/public/sitemap.xml` during validation; that generated diff was restored and is not included in this PR.

## Rollback

If this revert PR needs to be undone, revert the revert commit from this branch after confirming PR #14 content is safe to restore.

