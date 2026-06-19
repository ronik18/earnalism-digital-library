# Deployment Flow Safety Report

Status: `SAFE_FOR_MAIN_BRANCH_DEPLOYMENT_GATE`

Phase 13D separates checks that can be proven before deployment from checks that can only be proven after deployment.

## Pre-Deploy Main-Branch Gate

- `npm run regression:ci` runs before Railway/Vercel deployment.
- This gate validates local/public-content governance, sitemap/robots policy, regression modules, and non-mutating product behavior.
- It does not require current production `/shop` parity because that parity depends on the deployment currently being attempted.

## Report-Only On Pull Requests

- `npm run launch:production-parity` may run on pull requests as report-only evidence.
- Pull request production parity is allowed to fail while production still has stale routes.
- Local PR regression remains strict for `/shop`, `/shop/`, `/shop/*`, `/product/patterned-wrap-dress`, sitemap exclusion, and robots deindexing policy.

## Deployment Blockers

- Dependency install failure.
- Pre-deploy regression failure.
- Railway deploy failure when Railway secrets are configured.
- Vercel production build/deploy failure when Vercel secrets are configured.

## Post-Deploy Canary

- `npm run launch:post-deploy-route-canary` runs after frontend deployment on `main`.
- `npm run regression:canary` runs after the removed-route canary.
- Removed/demo routes must return `410` or `404`, must not redirect, must not serve the generic SPA shell, and must include exactly `X-Robots-Tag: noindex, nofollow, noarchive`.

## Canary Failure / Rollback Handling

- A failed post-deploy canary marks production parity `BLOCKED`.
- Operators must not mark `GO_FOR_CONTROLLED_PUBLICATION` from a failed canary.
- Roll back the last Vercel production deployment or re-deploy the route fix, then rerun the route canary.
- Backend/frontend deployment logs and `output/launch/post_deploy_route_canary.json` are the first artifacts to inspect.

## Why Production Parity Is Post-Deploy

Current production can be stale. Requiring stale production `/shop` to pass before deploying the route fix would deadlock the release. The safe sequence is strict local regression, deploy the fix, then enforce production parity as a canary.
