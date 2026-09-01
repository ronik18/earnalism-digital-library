# Repository and deployment discovery

Checked-in configuration is repository evidence only. Live Railway state was not inferred from it.

## Evidence

| Topic | Current finding | Evidence |
|---|---|---|
| Backend | FastAPI 0.110.1 | backend/requirements-runtime.txt; backend/server.py |
| Frontend | React ^19.0.0 with CRACO ^7.1.0 / react-scripts 5.0.1 | frontend/package.json |
| Railway | READ_ONLY_PRODUCTION_METRICS_UNAVAILABLE: Railway CLI has no linked project | railway status; backend/railway.json |
| Canary | Deployment-status event gates GET/HEAD-only backend canary. | .github/workflows/railway-deployment-canary.yml |
