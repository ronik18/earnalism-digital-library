# Railway Horizontal Scaling Setup

Prepared on June 3, 2026 for theearnalism.com. Railway Trial does not support horizontal scaling or multiple replicas, so this repository now contains only trial-safe code changes. Do not run `railway scale`, set replica counts, or add autoscaling secrets until the Railway Pro plan is active on or after June 10, 2026.

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

## Section A - Do NOW (trial period, before June 10)

1. Merge all Phase 1 code changes:
   - Dormant Judoscale FastAPI middleware, activated only when `JUDOSCALE_URL` exists.
   - Redis-backed public cache and rate limiter, activated only when `MULTI_REPLICA_ENABLED=true`.
   - Mongo GridFS storage for admin DOCX artifacts in multi-replica mode.
   - Graceful SIGTERM drain marker plus 15-second Uvicorn graceful shutdown timeout.
   - `/healthz` and `/api/healthz` routes returning HTTP 200 with `{"status":"ok","replica":"single"}` while Trial mode is active.
   - `npm run loadtest` 60-second 10X spike scaffold.
2. Sign up at https://judoscale.com/railway and get the `JUDOSCALE_URL` API key ready. Do not add it to Railway yet.
3. Run a baseline load test and record p95 latency:

```bash
npm run loadtest
```

Useful baseline overrides:

```bash
K6_BASELINE_VUS=50 K6_SPIKE_MULTIPLIER=10 K6_LOAD_DURATION=60s npm run loadtest
K6_SPIKE_VUS=500 K6_HTTP_P95_THRESHOLD='p(95)<3000' npm run loadtest
```

4. Keep these Railway variables unchanged during Trial:
   - `MULTI_REPLICA_ENABLED=false`
   - no `JUDOSCALE_URL`
   - no replica scaling commands

## Section B - Do ON DAY OF Pro upgrade (June 10+)

```bash
# 1. Set minimum replica baseline
railway scale us-east=2   # adjust region to match theearnalism.com's Railway region

# 2. Add Judoscale secret in Railway dashboard
#    Settings -> Variables -> Add: JUDOSCALE_URL=<your key from judoscale dashboard>

# 3. Enable multi-replica mode
#    Settings -> Variables -> Add: MULTI_REPLICA_ENABLED=true

# 4. Add REDIS_URL if not already present (via Railway Redis plugin)
#    Settings -> Add Plugin -> Redis

# 5. Set health check path in Railway
#    Service Settings -> Health Check Path -> /healthz

# 6. Configure Judoscale dashboard
#    - Min replicas: 2
#    - Max replicas: 10  (covers 10X spike headroom)
#    - Scale-up sensitivity: 10 seconds (fastest)
#    - Scale-down: conservative (5 min cooldown to avoid yo-yo)

# 7. Re-run load test to confirm autoscaler fires
npm run loadtest
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
# If Judoscale is slow to react during a sudden viral spike:
railway scale us-east=8

# Scale back down after spike subsides:
railway scale us-east=2
```

## Rollback Notes

- Removing `JUDOSCALE_URL` disables Judoscale middleware on the next deploy.
- Setting `MULTI_REPLICA_ENABLED=false` returns cache, rate-limit, and DOCX artifact handling to single-replica trial behavior.
- Keep `REDIS_URL` configured after Pro even if Judoscale is temporarily disabled; it is the shared state backend for multi-replica safety.
