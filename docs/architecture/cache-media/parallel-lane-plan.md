# Parallel implementation plan

Foundation extraction is serial first. No two lanes edit `backend/server.py` before the named interfaces are extracted. Frontend work waits for PR #344.

- **A Redis abstraction** — `codex/cache-media-redis-codec`; depends on foundation; owns backend/cache/**.
- **B Audio hardening** — `codex/cache-media-audio-streaming`; depends on foundation; owns backend/media/**.
- **C PDF** — `codex/cache-media-pdf-discovery`; depends on explicit product approval; owns docs/architecture/cache-media/pdf/**.
- **D Metrics** — `codex/cache-media-metrics`; depends on foundation interfaces; owns backend/cache/**, scripts/cache_media/**.
- **E Frontend lifecycle** — `codex/cache-media-frontend-lifecycle`; depends on PR #344 merged and audio contract; owns frontend/src/experiences-v2/**, frontend/src/components/**.
- **F CI/release** — `codex/cache-media-ci-release`; depends on A/B/D merged; owns .github/workflows/**.
