# PR #14 Reconciliation Report

## Objective

Verify whether merged PR #14 preserved the approved Phase 1A/1B public catalog governance baseline from PR #12 and PR #13, and define the smallest safe corrective PR.

## Baseline Compared

- Intended Phase 1A/1B baseline: merge commit `4248498` (`Merge pull request #13 from ronik18/codex/public-catalog-governance-phase1b`)
- Current main after PR #14: merge commit `f56aacd` (`Merge pull request #14 from ronik18/codex/public-content-cleanup`)
- Corrective branch: `codex/revert-pr-14-stabilization`

## Comparison Result

PR #14 was broad and mixed-scope. It changed 41 files with approximately 12,419 insertions and 52 deletions relative to the PR #13 baseline.

Notable PR #14 change areas:

- Backend runtime changes in `backend/server.py`, including Growth OS control-plane models, indexes, and endpoints.
- Root package script changes in `package.json`.
- Frontend page and SEO hook changes.
- Audio polish/cleanup scripts and TTS wrappers.
- Large audio assets under `assets/`.
- Multiple docs, manifests, requirements files, and env examples.

The approved Phase 1A/1B governance files were not the primary source of the broad diff, but the PR #14 merge still introduced unrelated runtime/tooling changes into `main`. The smallest safe correction is to revert PR #14 only.

## Governance File Reconciliation

| Area | Status after corrective revert |
| --- | --- |
| `frontend/api/removed-content.js` | Present and returns `410` for known retired demo paths, `404` for unknown retired paths |
| `frontend/vercel.json` removed-route routing | Present; demo/ecommerce/fashion routes rewrite to `/api/removed-content` |
| `frontend/public/robots.txt` deindexing strategy | Present; removed demo URLs are crawlable so crawlers can observe `410` + `X-Robots-Tag` |
| `frontend/public/sitemap.xml` | Excludes blocked demo/ecommerce/fashion terms |
| `frontend/scripts/generate-seo-assets.mjs` | Keeps removed URLs out of sitemap while not robots-blocking retired demo route families |
| `frontend/src/App.js` `/shop/:slug` behavior | No `/shop/:slug -> /book/:slug` redirect exists |
| `regression/modules/13-public-content-governance.test.js` | Present, readable, and validates removed routes and catalog audit behavior |
| `scripts/audit-public-content.mjs` | Present, readable, standalone shebang, fixture support, degraded source reporting |

## PR #14 Runtime Risk

PR #14 introduced broad changes that were not part of the approved Phase 1A/1B governance scope. Even where syntax validates, these changes should not remain in `main` without a separate reviewed PR because they affect backend behavior, frontend UX/SEO surfaces, package scripts, docs, and audio tooling.

## Corrective PR Decision

Use the smallest safe correction:

```bash
git revert -m 1 f56aacd --no-edit
```

This branch does exactly that and adds audit reports only. It does not add new features and does not mutate production content.

## Validation Summary

| Command | Result |
| --- | --- |
| `python3 -m py_compile backend/server.py` | Passed |
| `node --check scripts/audit-public-content.mjs` | Passed |
| `node --check regression/modules/13-public-content-governance.test.js` | Passed |
| `node scripts/audit-public-content.mjs --fixture regression/fixtures/catalog-audit --output-dir /tmp/earnalism-catalog-audit-check` | Passed |
| `npm run catalog:audit` | Passed, 251 items audited |
| `npm run regression -- modules/13-public-content-governance.test.js` | Passed, 15/15 tests |
| `npm --prefix frontend run build` | Passed |

## Remaining Notes

- `npm --prefix frontend ci` is currently blocked by a pre-existing frontend `package.json` / `package-lock.json` mismatch for React type and TypeScript packages. The requested frontend build was validated after installing dependencies with `npm --prefix frontend install --package-lock=false`, which did not mutate the lockfile.
- `npm --prefix frontend run build` regenerates `frontend/public/sitemap.xml`; generated validation diffs were restored and are not included in this corrective PR.

## Recommendation

Merge the PR #14 revert branch first to restore the approved Phase 1A/1B governance baseline. Reintroduce any desired Growth OS, audio polish, or marketing documentation changes later through separate, scoped PRs with their own tests and production-readiness review.

