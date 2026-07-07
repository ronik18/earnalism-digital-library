# Railway Backend Cost And Memory Remediation

Generated: 2026-07-05

## Diagnosis

Suspected root causes of high Railway backend memory/cost:

- Railway backend start command used `uvicorn ... --workers ${WEB_CONCURRENCY:-2}`, doubling Python app memory by default.
- `Dockerfile` fallback also defaulted to two workers, so container-based deploys could regress.
- Backend lifespan always ran startup database maintenance/seeding before serving.
- Admin import/cover/chapter/image endpoints could read 10-50 MB files into memory and invoke processing/Cloudinary code without a production cost-control gate.
- Mongo connection pool default was 25 connections per process, multiplied by worker count.
- Public in-process cache default was 256 entries and home payloads could request up to 500 books.

No evidence was found that the backend lifespan directly starts audiobook generation, catalog factory, cover generation batches, queue consumers, or file watchers. The immediate cost risk was unsafe production defaults and unguarded heavy admin processing routes.

## Files Changed

- `backend/start_prod.sh`
- `backend/railway.json`
- `backend/Procfile`
- `backend/Dockerfile`
- `backend/server.py`
- `scripts/verify_railway_cost_controls.py`
- `package.json`

## Start Command

Before:

```sh
uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips '*' --timeout-keep-alive ${UVICORN_KEEP_ALIVE:-15} --timeout-graceful-shutdown ${UVICORN_GRACEFUL_TIMEOUT:-15}
```

After:

```sh
sh ./start_prod.sh
```

`backend/start_prod.sh` now starts one lightweight API worker by default and exports safe cost-control defaults before launching Uvicorn.

## Production Defaults Added

```sh
COST_CONTROL_MODE=true
ENABLE_BACKGROUND_WORKERS=false
ENABLE_AUDIOBOOK_PIPELINE=false
ENABLE_BOOK_RENDERING_JOBS=false
ENABLE_COVER_GENERATION=false
ENABLE_SCHEDULED_JOBS=false
ENABLE_QUEUE_CONSUMER=false
ENABLE_ADMIN_MEDIA_UPLOADS=false
ENABLE_STARTUP_DB_MAINTENANCE=false
MAX_CONCURRENT_JOBS=1
WEB_CONCURRENCY=1
MALLOC_ARENA_MAX=2
MONGODB_MAX_POOL_SIZE=8
PUBLIC_CACHE_MAX_ENTRIES=96
HOME_BOOK_LIMIT=120
REQUEST_BODY_LIMIT_BYTES=2097152
DOCX_UPLOAD_MAX_BYTES=8388608
CHAPTER_UPLOAD_MAX_BYTES=8388608
ADMIN_MEDIA_UPLOAD_MAX_BYTES=4194304
```

## Heavy Jobs Disabled By Default

The production web service now fails closed unless explicitly enabled and confirmed:

- DOCX import / book rendering jobs
- Chapter file processing jobs
- Cover processing/upload jobs
- Generic admin media uploads
- Startup DB maintenance/seeding
- Background workers
- Audiobook pipelines
- Scheduled jobs
- Queue consumers

Admin heavy-processing endpoints now require admin auth, a matching `ENABLE_*` flag, `confirm_expensive_job=true`, and an available expensive-job concurrency slot. If disabled, endpoints return a clear 503 instead of starting expensive work.

## Memory And Concurrency Caps

- Uvicorn default workers reduced from 2 to 1.
- `MALLOC_ARENA_MAX=2` set for Python allocator behavior.
- Mongo pool default reduced from 25 to 8 in cost-control mode.
- In-process public cache default reduced from 256 to 96 entries.
- Home book payload cap reduced from 500 to 120 in cost-control mode.
- Request body middleware rejects oversized requests before endpoint work.
- Upload limits reduced under cost-control mode.
- Expensive admin jobs use `MAX_CONCURRENT_JOBS=1` by default.

## Observability Added

Admin-only endpoint:

```text
GET /api/admin/system/cost-control
```

It reports RSS/max RSS memory, uptime, active expensive jobs, cost-control flag state, safe key-detection booleans, and current caps. It does not expose secrets.

## Verification

Commands run:

```sh
python3 -m py_compile backend/server.py scripts/verify_railway_cost_controls.py
npm run cost:audit
```

Verification result: `PASS`.

Verified:

- Railway start command uses `sh ./start_prod.sh`.
- Procfile uses `sh ./start_prod.sh`.
- Docker CMD uses `backend/start_prod.sh`.
- `WEB_CONCURRENCY` defaults to 1.
- Start surfaces contain no reload/watch/pipeline command.
- Heavy `ENABLE_*` flags default false.
- Allocator, Mongo, cache, and concurrency caps are exported.
- Server defines cost-control flags and limits.
- Admin processing routes require flags, confirmation, and a job slot.
- Startup DB maintenance is explicitly gated.
- Admin-only cost-control diagnostic route exists.
- Request body limit middleware exists.
- `npm run cost:audit` is wired.

Railway runtime variable check after `railway variable set ... --skip-deploys` and `railway redeploy`:

```text
COST_CONTROL_MODE=true
WEB_CONCURRENCY=1
ENABLE_AUDIOBOOK_PIPELINE=false
ENABLE_BOOK_RENDERING_JOBS=false
ENABLE_COVER_GENERATION=false
ENABLE_QUEUE_CONSUMER=false
ENABLE_STARTUP_DB_MAINTENANCE=false
MAX_CONCURRENT_JOBS=1
MONGODB_MAX_POOL_SIZE=8
PUBLIC_CACHE_MAX_ENTRIES=96
```

## Railway Variables

The non-secret variables above were set on the specified Railway backend service and the existing deployment was redeployed so `WEB_CONCURRENCY=1` can apply immediately. The source-code safeguards still require the normal commit/push/deploy path.

Redeploy after merge/push:

```sh
railway redeploy \
  --project a8533934-35c4-463e-9f43-577a9ac391ee \
  --service 5af42e7e-f518-4f6a-b602-d9950866501f \
  --environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 \
  --from-source \
  --yes
```

## Remaining Risks

- `backend/requirements.txt` still installs heavy dev/AI libraries in production. Splitting production requirements from pipeline/dev requirements would reduce image size and cold-start memory further.
- Admin list endpoints still allow large admin result sets; they are admin-only but should be paginated in a later pass.
- Startup DB maintenance is disabled by default. Future schema/index migrations should be run intentionally as one-off jobs, then disabled again.
- Heavy audiobook/catalog scripts remain available as manual commands, but they are no longer part of the Railway web start path.
