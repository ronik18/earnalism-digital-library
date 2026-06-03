# Railway Horizontal Scaling Setup

Prepared on June 3, 2026 for theearnalism.com. Railway Pro is now active, and the backend has been configured for horizontal scaling with Redis-backed shared state and Judoscale autoscaling.

## Live Pro Setup - Completed June 3, 2026

- Railway service: `earnalism` in `production`.
- Backend deploy: autoscaling-ready backend with `/healthz` Railway health check.
- Shared state: Railway Redis service provisioned and backend `REDIS_URL` configured.
- Multi-replica mode: `MULTI_REPLICA_ENABLED=true`.
- Autoscaler: `JUDOSCALE_URL` configured; logs confirm Judoscale FastAPI middleware is enabled.
- Judoscale process type: `earnalism`, autoscaling enabled, min 2 replicas, max 10 replicas, upscale quantity 2, 10-second scale-up sensitivity, 5-minute conservative downscale.
- Runtime logs confirm Redis-backed multi-replica state is enabled.
- Health checks:
  - `https://api.theearnalism.com/healthz`
  - `https://api.theearnalism.com/api/healthz`
  - Expected response now includes a Railway replica id, not `single`.
- Baseline replicas after validation: 2 running replicas in `sfo`.
  - Railway CLI rejected `sfo` as a scale argument; the accepted California alias is `us-west`, which Railway may display as `us-west2`.
  - During testing, Judoscale/Railway briefly used both `sfo` and `us-west2`; the final cost-conscious baseline was restored to `sfo=2` with `railway scale us-west=0`.
- Observed autoscale behavior: during/after the 10X spike test, Railway scaled up beyond baseline, confirming the autoscaling loop reacted.
- Follow-up correction: Judoscale was initially enabled with range `min=1`, `max=5`; corrected via the Judoscale settings API to `min=2`, `max=10`.
- During the old `min=1` cooldown, Railway metrics recorded 3 transient 5xx responses while deployments were reconciling. After the correction, `/healthz` returned clean 200s across both baseline replicas.
- Load test record:
  - Command profile: `K6_BASELINE_VUS=20`, `K6_SPIKE_MULTIPLIER=10`, `K6_LOAD_DURATION=60s`.
  - Result: 16,380 HTTP requests, 0 failed requests, 19,110/19,110 checks passed.
  - k6 p95: 911 ms overall, 1.45 s catalog, 802 ms reader.
  - Railway 10-minute metrics during the run: 13,665 HTTP requests, 0.0% error rate, p95 618 ms.
  - Artifacts: `output/performance/railway_autoscale_20260603T175559Z/`.

## Stateless Audit

Runtime detected: Python/FastAPI backend on Railway, React static frontend. Judoscale integration uses the Python ASGI/FastAPI middleware (`judoscale[asgi]`).

Replica-sensitive findings and fixes:

- `backend/server.py` `_rate_limit_hits`: per-process rate-limit buckets would allow each replica to enforce limits independently. Fixed with Redis sorted-set rate-limit windows when `MULTI_REPLICA_ENABLED=true` and `REDIS_URL` is present. Trial mode keeps the current local buckets.
- `backend/server.py` `_public_cache`: per-process anonymous public cache could serve stale catalogue/settings data on one replica after another replica handles an admin write. Fixed with Redis-backed cache plus generation-based invalidation when `MULTI_REPLICA_ENABLED=true` and `REDIS_URL` is present. Trial mode keeps the current local LRU cache.
- `backend/server.py` `_health_cache`: short-lived per-process `/health` DB-ping cache. It does not affect reader/admin behavior. `/healthz` is uncached and should be used for Railway service health checks after upgrade.
- `backend/server.py` `_process_docx_upload`: admin DOCX validation artifacts were written to replica-local disk. Fixed so Trial mode still uses local disk, while multi-replica mode stores upload artifacts in Mongo GridFS and records `gridfs://...` audit refs.
- `backend/server.py` `_CLOUDINARY_INITIALIZED`: per-process lazy initialization only; safe because cover/chapter image assets are stored in Cloudinary.
- Sessions, reading sessions, wallet transactions, payment intents, webhooks, reader completion rewards, users, books, blog posts, settings, contacts, analytics, and admin audit records are already stored in MongoDB.
- Cron/scheduled jobs: no cron, APScheduler, Celery, RQ, repeated background loop, or scheduled task runner was found in the web runtime. If a cron job is added later, guard it with a Redis leader lock when `MULTI_REPLICA_ENABLED=true`; run normally when false.

## Section A - Completed During Trial Preparation

1. Merge all Phase 1 code changes:
   - Dormant Judoscale FastAPI middleware, activated only when `JUDOSCALE_URL` exists.
   - Redis-backed public cache and rate limiter, activated only when `MULTI_REPLICA_ENABLED=true`.
   - Mongo GridFS storage for admin DOCX artifacts in multi-replica mode.
   - Graceful SIGTERM drain marker plus 15-second Uvicorn graceful shutdown timeout.
   - `/healthz` and `/api/healthz` routes returning HTTP 200 with `{"status":"ok","replica":"single"}` while Trial mode is active.
   - `npm run loadtest` 60-second 10X spike scaffold.
2. Sign up at https://judoscale.com/railway and get the `JUDOSCALE_URL` API key ready.
3. Run a baseline load test and record p95 latency:

```bash
npm run loadtest
```

Useful baseline overrides:

```bash
K6_BASELINE_VUS=50 K6_SPIKE_MULTIPLIER=10 K6_LOAD_DURATION=60s npm run loadtest
K6_SPIKE_VUS=500 K6_HTTP_P95_THRESHOLD='p(95)<3000' npm run loadtest
```

4. During Trial, keep these Railway variables unchanged:
   - `MULTI_REPLICA_ENABLED=false`
   - no `JUDOSCALE_URL`
   - no replica scaling commands

## Section B - Completed On Pro Upgrade

```bash
# 1. Set minimum replica baseline.
# Final validated baseline is sfo=2. Railway's CLI accepts us-west,
# which may appear as us-west2 in service status during autoscale events.
railway scale us-west=0   # remove temporary us-west2 replicas after validation

# 2. Add Judoscale secret in Railway dashboard.
#    Settings -> Variables -> Add: JUDOSCALE_URL=<your key from Judoscale dashboard>

# 3. Enable multi-replica mode
#    Settings -> Variables -> Add: MULTI_REPLICA_ENABLED=true

# 4. Add REDIS_URL if not already present (via Railway Redis plugin)
#    Settings -> Add Plugin -> Redis

# 5. Set health check path in Railway
#    Service Settings -> Health Check Path -> /healthz

# 6. Configure Judoscale
#    - Min replicas: 2
#    - Max replicas: 10  (covers 10X spike headroom)
#    - Scale-up quantity: 2 replicas per step
#    - Scale-up sensitivity: 10 seconds (fastest)
#    - Scale-down: conservative (5 min cooldown to avoid yo-yo)

# 7. Re-run load test to confirm autoscaler fires.
K6_BASELINE_VUS=20 K6_SPIKE_MULTIPLIER=10 K6_LOAD_DURATION=60s npm run loadtest
```

Post-upgrade verification:

```bash
curl -s https://api.theearnalism.com/healthz
curl -s https://api.theearnalism.com/api/healthz
```

Expected while `MULTI_REPLICA_ENABLED=false`:

```json
{"status":"ok","replica":"single"}
```

Expected after enabling multi-replica mode:

```json
{"status":"ok","replica":"<railway replica id or multi>"}
```

## Section C - Emergency manual override (any time after Pro)

```bash
# If Judoscale is slow to react during a sudden viral spike.
# This adds about 8 us-west2 replicas while existing sfo replicas remain.
railway scale us-west=8

# Scale back down after spike subsides.
# This removes temporary us-west2 replicas and returns to the sfo baseline.
railway scale us-west=0
```

## Rollback Notes

- Removing `JUDOSCALE_URL` disables Judoscale middleware on the next deploy.
- Setting `MULTI_REPLICA_ENABLED=false` returns cache, rate-limit, and DOCX artifact handling to single-replica trial behavior.
- Keep `REDIS_URL` configured after Pro even if Judoscale is temporarily disabled; it is the shared state backend for multi-replica safety.
