# Earnalism Regression Gate

This suite is the mandatory pre-GO LIVE regression gate for theearnalism.com.

## Run Modes

- PR mode: `npm run regression:ci`
  Fast, deterministic checks. Destructive DB/cache mutation is refused.
- GO LIVE mode: `npm run regression:go-live`
  Full staging gate. Every mandatory module must score exactly `100`.
- Canary mode: `npm run regression:canary`
  Lightweight production smoke after deploy. It does not mutate production.
- Visual baseline update: `npm run regression:visual:update`
  Local-only screenshot baseline refresh. CI never auto-generates baselines.
- Visual CI: `npm run regression:visual:ci`
  Fails when required baselines are missing.

Every run writes `regression/results.json`. The gate fails only after that report is generated.

## Common Env Vars

- `REGRESSION_MODE`: `pr`, `go-live`, `canary`, or `visual-ci`.
- `REGRESSION_FRONTEND_URL` or `FRONTEND_URL`: frontend target.
- `REGRESSION_API_URL` or `API_URL`: backend API target.
- `MONGODB_URL`: enables MongoDB index/data checks.
- `REDIS_URL`: enables Redis checks.
- `JUDOSCALE_URL` or `RAILWAY_TOKEN`: required for GO LIVE infrastructure readiness.
- `REGRESSION_ENABLE_LOAD_TEST=true`: required for GO LIVE load testing against non-production.

## Safety Rules

- Mutations require `NODE_ENV` in `test`, `ci`, or `staging`, `REGRESSION_ALLOW_MUTATION=true`, and a non-production target.
- Redis `FLUSHDB` is never used by this suite. Helpers only allow it when `REDIS_ALLOW_FLUSH_FOR_REGRESSION=true` and the Redis URL is test-only.
- Load tests are refused against production.
- Production canary checks never write data.
- Secrets are never printed.

## Content Hash Updates

When a book is intentionally revised, update its approved cleaned-source hash in the admin/internal provenance flow, then rerun `npm run regression:go-live`. Do not edit public metadata to carry internal source URLs or review notes.

## Reading Failures

Open `regression/results.json` and inspect `modules[].failures`. Mandatory module scores below `100` block deploy. PR mode may allow some heavy checks to skip; GO LIVE mode does not.

## Rollback And Canary

After deploy, run `npm run regression:canary`. If canary fails, mark the deployment failed, roll back the last Railway/Vercel deployment, and inspect `regression/results.json` plus uploaded artifacts.
