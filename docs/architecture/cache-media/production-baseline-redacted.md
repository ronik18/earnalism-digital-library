# Read-only production baseline

No credential values, object URLs, user identity, or protected-media URLs were accessed or recorded.

## Evidence

| Topic | Current finding | Evidence |
|---|---|---|
| deployed backend SHA, service health, region, replicas, CPU/RSS, latency, 5xx | Railway CLI returned no linked project | production-baseline-redacted.json |
| Redis INFO, DBSIZE, config, hit/miss, evictions | no repository-sanctioned live Redis connection was available | production-baseline-redacted.json |
| object count/size/MIME/ETag distribution | no safe object-store metadata authorization available | production-baseline-redacted.json |
