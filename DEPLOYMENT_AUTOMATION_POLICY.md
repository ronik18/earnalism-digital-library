# Deployment Automation Policy

Earnalism production deployments are intentionally main-branch only.

## Trigger

Production deployment is triggered by a GitHub `push` event to:

```text
refs/heads/main
```

Pull requests, feature branches, `release/**`, `production-deploy`, and manual workflow dispatches do not deploy production.

## Backend

Backend deployment is handled by `.github/workflows/regression.yml` after the GO LIVE regression gate passes on a `main` push.

Required GitHub secrets:

- `RAILWAY_TOKEN`
- `RAILWAY_SERVICE_ID`

Optional GitHub variable:

- `RAILWAY_ENVIRONMENT`, default `production`

The workflow deploys only the backend directory:

```bash
railway up backend --path-as-root --service "$RAILWAY_SERVICE_ID" --environment "$RAILWAY_ENVIRONMENT"
```

## Frontend

Frontend deployment is handled by `.github/workflows/regression.yml` after the GO LIVE regression gate passes on a `main` push.

Required GitHub secrets:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

Optional GitHub secret or variable:

- `VERCEL_SCOPE`

The workflow links and runs Vercel from `frontend/`, where `frontend/vercel.json` lives.

`frontend/vercel.json` also includes an `ignoreCommand` so Vercel Git integration ignores non-main branches. This prevents accidental Preview/Production deployment from feature branches if Git integration is enabled outside GitHub Actions.

## Post-Deploy

The post-deploy k6 smoke workflow runs only after a `main` push. It does not deploy anything.

## Manual Dispatch

Manual workflow dispatch is allowed for validation and monitoring, but production deployment jobs are guarded by:

```text
github.event_name == 'push' && github.ref == 'refs/heads/main'
```

This keeps production deploys tied to commits that actually land on `origin/main`.
