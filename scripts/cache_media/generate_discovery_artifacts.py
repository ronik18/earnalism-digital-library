#!/usr/bin/env python3
"""Render architecture-only cache/media baseline artifacts from repository evidence."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


E = "backend/server.py"


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def md(title: str, summary: str, facts: list[dict]) -> str:
    lines = [f"# {title}", "", summary, "", "## Evidence", "", "| Topic | Current finding | Evidence |", "|---|---|---|"]
    for item in facts:
        lines.append(f"| {item['topic']} | {item['finding']} | {item['evidence']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("docs/architecture/cache-media"))
    parser.add_argument("--origin-main-sha", required=True)
    parser.add_argument("--pr-overlap", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    overlap = json.loads(args.pr_overlap.read_text(encoding="utf-8"))
    write_json(out / "pr344-overlap-map.json", overlap)
    (out / "pr344-overlap-map.md").write_text(md("PR #344 overlap map", "PR #344 is active primary-UI work. This baseline owns only new cache/media documentation, characterization tests, and scripts; it edits no listed PR path.", [
        {"topic": "PR state", "finding": overlap["pr"]["state"], "evidence": "GitHub CLI read-only PR metadata"},
        {"topic": "Changed path count", "finding": str(overlap["changed_path_count"]), "evidence": "GitHub CLI read-only PR metadata"},
        {"topic": "Overlap result", "finding": overlap["overlap_result"], "evidence": "docs/architecture/cache-media/pr344-overlap-map.json"},
    ]), encoding="utf-8")

    repository = {
        "schema_version": "cache-media-repository-discovery.v1", "origin_main_sha": args.origin_main_sha,
        "backend": {"framework": "FastAPI 0.110.1", "python": "3.11", "requirements_authorities": ["backend/requirements-runtime.txt", "backend/requirements.txt"], "entrypoint": "backend/server.py:api", "command": "backend/start_prod.sh via backend/Dockerfile and backend/Procfile", "process_model": "Uvicorn process configured by start_prod.sh; worker count requires runtime evidence", "async_sync_boundaries": "FastAPI async handlers call synchronous boto3 body reads through a generator", "health": "/healthz", "shutdown": "lifespan plus SIGTERM drain marker", "evidence": ["backend/Dockerfile", "backend/Procfile", "backend/server.py:4356"]},
        "frontend": {"framework": "React ^19.0.0 with CRACO ^7.1.0 / react-scripts 5.0.1", "package_manager": "npm lockfile", "build": "npm run build", "deployment": "frontend/vercel.json and .github/workflows/regression.yml", "evidence": ["frontend/package.json", "frontend/vercel.json", ".github/workflows/regression.yml"]},
        "railway": {"checked_in_authority": "backend/railway.json", "builder": "DOCKERFILE", "watch_patterns": ["/backend/**"], "start_command": "sh ./start_prod.sh", "healthcheck": "/healthz", "checked_in_region": "sfo with one replica", "autoscaling": "README describes Railway Pro + Redis + Judoscale, but active runtime authority is unavailable", "rollback": "provider deployment history not accessible from this checkout", "production_state": "READ_ONLY_PRODUCTION_METRICS_UNAVAILABLE: Railway CLI has no linked project", "evidence": ["backend/railway.json", "backend/Dockerfile", "README.md", "railway status (read-only)"]},
        "ci_cd": {"backend_contract": ".github/workflows/backend-container-contract.yml", "regression_and_frontend_deploy": ".github/workflows/regression.yml", "backend_canary": ".github/workflows/railway-deployment-canary.yml", "post_deploy_load_workflow": ".github/workflows/post-deploy-k6.yml", "branch_protection": "not discoverable from repository files", "preview": "frontend Vercel deployment is conditional on credentials and changed frontend files"},
    }
    write_json(out / "repository-deployment-discovery.json", repository)
    (out / "repository-deployment-discovery.md").write_text(md("Repository and deployment discovery", "Checked-in configuration is repository evidence only. Live Railway state was not inferred from it.", [
        {"topic": "Backend", "finding": repository["backend"]["framework"], "evidence": "backend/requirements-runtime.txt; backend/server.py"},
        {"topic": "Frontend", "finding": repository["frontend"]["framework"], "evidence": "frontend/package.json"},
        {"topic": "Railway", "finding": repository["railway"]["production_state"], "evidence": "railway status; backend/railway.json"},
        {"topic": "Canary", "finding": "Deployment-status event gates GET/HEAD-only backend canary.", "evidence": ".github/workflows/railway-deployment-canary.yml"},
    ]), encoding="utf-8")

    redis = {"schema_version": "cache-media-redis-current-state.v1", "shared_client": {"result": "ONE_PROCESS_SHARED_ASYNC_CLIENT", "construction": "initialize_replica_state_backends uses redis.asyncio.from_url and module-global _redis_client", "timeouts_seconds": {"connect": 2, "socket": 2}, "retry_on_timeout": True, "evidence": f"{E}:1367-1406"}, "use_cases": [
        {"name": "public catalog", "key": "<prefix>:public-cache:<generation>:<sha256>", "value": "Python object", "codec": "pickle, zlib above 4096 bytes", "ttl_seconds": 300, "identity": "public", "invalidation": "generation increment", "fallback": "per-process OrderedDict", "concern": "unsafe pickle and no max serialized-value guard", "evidence": f"{E}:1508-1969"},
        {"name": "reader access/chapter/manifest", "key": "digest of versioned logical key", "value": "metadata or rendered chapter HTML", "codec": "pickle/zlib", "ttl_seconds": "900/3600/1800", "identity": "public versus admin embedded in logical key", "invalidation": "reader-content generation", "fallback": "database/controlled artifact", "concern": "no singleflight", "evidence": f"{E}:2127-2185, 2880-2971"},
        {"name": "user, session, wallet", "key": "<prefix>:user*:<id>", "value": "user/session dict or integer", "codec": "pickle/zlib for dicts; integer for wallet", "ttl_seconds": "20/20/8", "identity": "user and session id", "invalidation": "_invalidate_user_cache", "fallback": "MongoDB", "concern": "keys rely on opaque ids and no explicit key schema version", "evidence": f"{E}:1999-2124"},
        {"name": "payments and transactions", "key": "digest user-private logical key", "value": "list", "codec": "pickle/zlib", "ttl_seconds": "15/20", "identity": "user id", "invalidation": "wallet/payment mutation calls", "fallback": "MongoDB", "concern": "stale financial metadata if a mutation path misses invalidation", "evidence": f"{E}:7888-7892, 10728-10732"},
        {"name": "rate limits", "key": "<prefix>:rate-limit:*", "value": "sorted-set timestamps", "codec": "Redis native", "ttl_seconds": 120, "identity": "request identity and path scope", "invalidation": "expiry", "fallback": "per-process buckets", "concern": "fallback is per-replica", "evidence": f"{E}:4896-4996"},
        {"name": "startup lock", "key": "<prefix>:startup-maintenance:*", "value": "token", "codec": "Redis native", "ttl_seconds": 180, "identity": "process coordination", "invalidation": "compare-and-delete release", "fallback": "local behavior when Redis unavailable", "concern": "cross-replica coordination unavailable without Redis", "evidence": f"{E}:4109-4355"},
    ], "findings": {"duplicate_pools": "NOT_FOUND_IN_REPOSITORY_SOURCE", "required_for_correctness": "PARTIAL: multi-replica or fail-fast mode aborts startup without Redis; otherwise cache/rate-limit fallbacks continue", "binary_rejection": "bytes, streams, response objects, upload files, and media data URIs are rejected", "max_value_guard": "ABSENT", "unsafe_codec": "PICKLE_PRESENT", "corrupt_value": "decode errors miss/fall back but do not delete corrupt entry", "stampede": "POSSIBLE: no cache singleflight lock", "tenant_collision": "LOWERED_BY_USER_ID_AND_DIGESTS_BUT_NO_UNIFORM_KEY_VERSION_SCHEMA", "invalidation": "generation and targeted delete exist; completeness needs mutation-by-mutation implementation audit"}}
    write_json(out / "redis-current-state.json", redis)
    (out / "redis-current-state.md").write_text(md("Redis current state", "Observed current state only. The present decoder uses pickle; that is a high-severity future-remediation target, not a change made by this baseline.", [{"topic": row["name"], "finding": f"TTL {row['ttl_seconds']}; {row['codec']}", "evidence": row["evidence"]} for row in redis["use_cases"]] + [
        {"topic": "Maximum value", "finding": "No hard serialized-value limit found.", "evidence": f"{E}:1508-1572"},
        {"topic": "Stampede", "finding": "No cross-replica singleflight for cache fills found.", "evidence": f"{E}:1537-1572"},
    ]), encoding="utf-8")

    media = {"schema_version": "cache-media-media-lifecycle.v1", "audio": {"classification": "PROTECTED_B2_PROXY_STREAM_WITH_FAIL_CLOSED_RELEASE_GATE", "metadata": "controlled publication artifact and MongoDB; reader manifest deliberately contains no playable URL", "authorization": "reader audio endpoints authorize an active Reading Pass lease before asset lookup", "storage": "configured B2 S3-compatible stores; Cloudinary remains relevant to cover images", "browser_route": "/api/reader/book/{slug}/audiobook or package segment route", "delivery": "B2 object HEAD/GET through StreamingResponse; 1 MiB generator reads; raw B2 URL fails closed when store config is unmatched", "range": "GET and HEAD; single range including suffix; 206 and 416 supported", "conditional": "ETag and 304 supported; Last-Modified not set", "headers": {"cache_control": "private max-age 600 for mp3; 3600 for sidecars", "accept_ranges": "bytes", "content_disposition": "not set"}, "cancellation": "iterator finally closes B2 body; direct client disconnect handling is not explicit", "memory": "not complete-file buffered in application code; synchronous boto3 read may block event loop", "evidence": [f"{E}:8217-8675", f"{E}:8688-8939", "backend/tests/test_zero_public_audio_contract.py"]}, "pdf": {"classification": "EXISTING_INTERNAL_OR_REPORT_PDF_ONLY", "finding": "No customer PDF route, object-storage delivery endpoint, or frontend viewer was found. PDFs are generated reports/export tooling and a scanned-PDF ingestion placeholder.", "evidence": ["backend/source_ingestion.py:333-334", "scripts/bulk_publishing_pipeline.py:171-198", "scripts/prepare_technical_book.py"]}, "images": {"classification": "CLOUDINARY_CDN_DIRECT_IMAGE_URLS", "scope": "covers only; no change proposed", "evidence": ["backend/config/cloudinary.py", "backend/server.py:6786-7587"]}}
    write_json(out / "media-lifecycle-map.json", media)
    (out / "media-lifecycle-map.md").write_text(md("Media lifecycle map", "Audio is a protected proxy/stream contract. PDF is not an active customer product delivery path.", [
        {"topic": "Audio release truth", "finding": "Manifest returns empty assets/URL; playback is resolved only after authorization.", "evidence": f"{E}:2780-2878; backend/tests/test_zero_public_audio_contract.py"},
        {"topic": "Audio delivery", "finding": "B2 HEAD/GET streamed through a 1 MiB iterator with Range validation.", "evidence": f"{E}:8217-8675"},
        {"topic": "PDF", "finding": media["pdf"]["classification"], "evidence": "backend/source_ingestion.py; scripts/bulk_publishing_pipeline.py"},
    ]), encoding="utf-8")

    requests = {"schema_version": "cache-media-request-authorization-map.v1", "routes": [
        {"route": "/api/home, /api/books, /api/books/{slug}", "method": "GET", "class": "public", "authority": "controlled artifacts/Mongo", "redis": "public cache", "storage": "cover URLs only", "mutation": False, "range": "none", "evidence": f"{E}:5275-5879"},
        {"route": "/api/reader/book/{slug}/manifest and chapters", "method": "GET", "class": "public reader metadata/content", "authority": "controlled artifacts/Mongo", "redis": "reader manifest/content cache", "storage": "none", "mutation": False, "range": "none", "evidence": f"{E}:2127-2185, 2880-2971, 5700-5799"},
        {"route": "/api/reader/book/{slug}/audiobook and package segments", "method": "GET, HEAD", "class": "protected", "identity": "Reading Pass principal/lease", "authority": "approved audiobook evidence + B2", "redis": "manifest metadata cache", "storage": "B2 object metadata/body", "mutation": False, "range": "single bytes range", "evidence": f"{E}:8431-8939; backend/tests/test_zero_public_audio_contract.py"},
        {"route": "/api/reading-pass/*", "method": "GET, POST, PUT, DELETE", "class": "protected", "identity": "session/device/user", "authority": "Mongo ledger/session", "redis": "user/session/wallet cache", "storage": "none", "mutation": True, "range": "audio authorization only", "evidence": f"{E}:9391-9600"},
        {"route": "/api/admin/books/*", "method": "POST, PUT, PATCH, DELETE", "class": "admin", "identity": "admin JWT/session", "authority": "Mongo and controlled artifacts", "redis": "public generation invalidation", "storage": "Cloudinary/B2 admin upload paths", "mutation": True, "range": "none", "evidence": f"{E}:5880-7600"},
        {"route": "/api/payments/* and wallet admin", "method": "GET, POST", "class": "protected/admin/webhook", "identity": "user/admin/provider signature", "authority": "Mongo ledger", "redis": "wallet/payment state cache", "storage": "none", "mutation": True, "range": "none", "evidence": f"{E}:10145-10791"},
    ], "leakage_risks": ["No uniform cache-key schema version could make future migrations ambiguous.", "Raw non-B2 asset URL redirects exist; controlled B2 assets fail closed but future provider allowlisting should be explicit.", "Stale authorization/cache metadata is constrained by short user TTLs but requires event coverage proof before expansion."]}
    write_json(out / "request-authorization-map.json", requests)
    (out / "request-authorization-map.md").write_text(md("Request, authorization, and tenant boundary map", "No identities, tokens, private object keys, or signed URLs are recorded.", [{"topic": row["route"], "finding": f"{row['class']}; Redis: {row['redis']}", "evidence": row["evidence"]} for row in requests["routes"]]), encoding="utf-8")

    invalidation = {"schema_version": "cache-media-invalidation-event-map.v1", "events": [
        {"event": "book create/update/delete/publication/rights/cover/audio release", "authority": "admin book mutation routes", "current": "_public_cache_clear generation increment on observed catalog mutations", "gap": "route-by-route proof and audio-object replacement invalidation needs extraction", "future": "resource-version key plus precise catalog/manifest invalidation", "evidence": f"{E}:5880-6262, 6903, 7600"},
        {"event": "chapter create/update/delete/reorder", "authority": "admin chapter mutation routes", "current": "public generation invalidation present around admin mutations; reader-content generation exists", "gap": "precise per-slug/chapter invalidation not uniformly demonstrated", "future": "versioned chapter and manifest keys", "evidence": f"{E}:6703-6766, 1963-1969"},
        {"event": "session revocation/account permission", "authority": "login/refresh/logout/admin status", "current": "_invalidate_user_cache deletes user, wallet, session, transaction, and payment keys", "gap": "multi-device path needs regression coverage", "future": "event-linked session key delete", "evidence": f"{E}:944-1122, 2115-2124, 10308-10327"},
        {"event": "wallet/payment transaction", "authority": "payments and wallet routes", "current": "_invalidate_user_cache after observed writes", "gap": "webhook/reconcile coverage should be enumerated before cache extraction", "future": "user-scoped cache version or deletes", "evidence": f"{E}:10439-10674"},
        {"event": "Reading Pass configuration", "authority": "reading-pass admin/session routes", "current": "user invalidation on session changes; no dedicated entitlement cache discovered", "gap": "policy configuration cache semantics undocumented", "future": "entitlement versioning", "evidence": f"{E}:9419-9563"},
        {"event": "PDF replacement", "authority": "no active customer route", "current": "not applicable", "gap": "no product contract", "future": "define only if PDF product is approved", "evidence": "media-lifecycle-map.json"},
    ]}
    write_json(out / "invalidation-event-map.json", invalidation)
    (out / "invalidation-event-map.md").write_text(md("Mutation and invalidation map", "This maps observed current controls and identifies missing proof; it makes no invalidation change.", [{"topic": row["event"], "finding": row["current"], "evidence": row["evidence"]} for row in invalidation["events"]]), encoding="utf-8")

    production = {"schema_version": "cache-media-production-baseline-redacted.v1", "classification": "READ_ONLY_PRODUCTION_METRICS_UNAVAILABLE", "available": [{"metric": "checked-in Railway contract", "value": "Dockerfile builder; sfo/1 replica in config", "source": "backend/railway.json", "live": False}], "unavailable": [
        {"metric": "deployed backend SHA, service health, region, replicas, CPU/RSS, latency, 5xx", "reason": "Railway CLI returned no linked project", "read_only_action": "authorized Railway project service/deployment/metrics view", "owner_login_required": True, "implementation_dependency": False},
        {"metric": "Redis INFO, DBSIZE, config, hit/miss, evictions", "reason": "no repository-sanctioned live Redis connection was available", "read_only_action": "authorized PING/INFO/DBSIZE/CONFIG GET through approved layer", "owner_login_required": True, "implementation_dependency": True},
        {"metric": "object count/size/MIME/ETag distribution", "reason": "no safe object-store metadata authorization available", "read_only_action": "authorized bounded HEAD/listing metadata report", "owner_login_required": True, "implementation_dependency": True},
    ]}
    write_json(out / "production-baseline-redacted.json", production)
    (out / "production-baseline-redacted.md").write_text(md("Read-only production baseline", "No credential values, object URLs, user identity, or protected-media URLs were accessed or recorded.", [{"topic": row["metric"], "finding": row["reason"], "evidence": "production-baseline-redacted.json"} for row in production["unavailable"]]), encoding="utf-8")

    candidates = [
        ("public catalog", "CACHE", "public-cache:v1:<generation>:<digest>", "public catalog response", 256000, 300, "catalog mutation", 200, 200, "Observed public cache implementation"),
        ("home/public shelf", "CACHE", "public-cache:v1:<generation>:<digest>", "curated composition", 128000, 300, "catalog or curation mutation", 50, 50, "Observed public cache implementation"),
        ("book metadata", "CACHE", "public-cache:v1:<generation>:<digest>", "book projection", 64000, 300, "book mutation", 500, 500, "Observed public cache implementation"),
        ("chapter metadata", "CACHE", "reader-content:v1:<generation>:<digest>", "chapter metadata", 64000, 900, "chapter mutation", 5000, 5000, "Observed reader cache implementation"),
        ("Reader content", "CONDITIONAL", "reader-content:v1:<generation>:<digest>", "rendered chapter HTML", 262144, 3600, "chapter/publication mutation", 10000, 10000, "Current implementation lacks max-size guard"),
        ("Listener manifest", "CACHE", "reader-manifest:v1:<generation>:<digest>", "release-safe metadata", 131072, 1800, "audio release or book mutation", 500, 500, "Observed metadata cache"),
        ("audio object metadata", "CONDITIONAL", "media-meta:v1:<object-version>", "ETag/length/content type", 8192, 600, "object replacement", 1000, 1000, "Requires production measurements"),
        ("signed URL/delivery manifest", "CONDITIONAL", "delivery-manifest:v1:<user>:<resource>", "short-lived authorization-safe route metadata", 8192, 60, "lease/revocation", 10000, 10000, "No signed URL cache currently"),
        ("article/journal metadata", "CACHE", "public-cache:v1:<generation>:<digest>", "public metadata", 65536, 300, "editorial mutation", 2000, 2000, "Observed public cache pattern"),
        ("entitlement lookup", "CONDITIONAL", "entitlement:v1:<user>:<resource>", "allow/deny state", 2048, 8, "lease/session/revocation", 100000, 100000, "Sensitive; cache only with exact invalidation"),
        ("session/user lookup", "CACHE", "user-session:v1:<session>", "session document", 8192, 20, "session revoke/refresh", 100000, 100000, "Observed current cache"),
        ("processing/transcode state", "CONDITIONAL", "processing:v1:<asset>", "job state", 8192, 30, "job state transition", 10000, 10000, "No stable current contract"),
        ("waveform/page-count metadata", "CONDITIONAL", "media-derived:v1:<object-version>", "small derived metadata", 65536, 3600, "object replacement", 10000, 10000, "No active product path for waveform/PDF"),
        ("negative not-found", "CONDITIONAL", "negative:v1:<public-resource>", "not found marker", 256, 30, "create/publish", 50000, 50000, "Avoid caching protected authorization denials"),
        ("request coalescing locks", "CONDITIONAL", "singleflight:v1:<resource>", "short lock token", 256, 10, "operation completion", 10000, 10000, "No cache-fill singleflight currently"),
        ("idempotency state", "CONDITIONAL", "idempotency:v1:<user>:<operation>", "response hash/status", 16384, 86400, "operation resolution", 10000, 10000, "Route-specific design needed"),
        ("complete PDF binary", "DO_NOT_CACHE", "N/A", "large binary", 0, 0, "N/A", 0, 0, "No active PDF route; Redis unsuitable for large bytes"),
        ("complete audio binary", "DO_NOT_CACHE", "N/A", "large binary", 0, 0, "N/A", 0, 0, "Repository policy rejects audiobook binaries"),
        ("arbitrary Range fragments", "DO_NOT_CACHE", "N/A", "large binary fragments", 0, 0, "N/A", 0, 0, "B2 range streaming is durable-storage concern"),
    ]
    policy_rows = []
    for use_case, decision, key, value, max_bytes, ttl, invalidation_trigger, cardinality, total, reason in candidates:
        estimated = (len(key) + min(max_bytes, 65536) + 128) * total if decision != "DO_NOT_CACHE" else 0
        policy_rows.append({"use_case": use_case, "decision": decision, "key_namespace": key.split(":")[0], "key_version": "v1", "key_format": key, "tenant_resource_identity": "public or explicit user/resource scope as shown in key", "cached_value": value, "source_of_truth": "MongoDB/controlled artifact/B2 metadata as applicable", "codec": "CURRENT: pickle/zlib; TARGET: bounded JSON", "maximum_serialized_bytes": max_bytes, "expected_cardinality": cardinality, "ttl_seconds": ttl, "jitter_seconds": "CURRENT 0-30; target bounded", "negative_cache_ttl_seconds": 30 if use_case == "negative not-found" else 0, "invalidation_trigger": invalidation_trigger, "request_coalescing": "CURRENT absent; target selected singleflight" if decision != "DO_NOT_CACHE" else "N/A", "redis_outage_fallback": "source-of-truth or per-process cache", "expected_latency_benefit": "ASSUMPTION_REQUIRES_POST_RELEASE_MEASUREMENT", "expected_source_cost_reduction": "ASSUMPTION_REQUIRES_POST_RELEASE_MEASUREMENT", "estimated_bytes_per_entry": min(max_bytes, 65536) + len(key) + 128 if decision != "DO_NOT_CACHE" else 0, "estimated_total_redis_memory": estimated, "replication_persistence_multiplier": 1.5 if decision != "DO_NOT_CACHE" else 0, "confidence": "MEDIUM" if "Observed" in reason else "LOW", "evidence_source": reason, "reason": reason})
    write_json(out / "cache-policy-matrix.json", {"schema_version": "cache-media-cache-policy.v1", "assumption": "memory = cardinality * (key bytes + bounded value bytes + 128-byte object overhead) * 1.5 replication/persistence multiplier; estimates are not observed Redis measurements", "rows": policy_rows})
    with (out / "cache-policy-matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(policy_rows[0]))
        writer.writeheader(); writer.writerows(policy_rows)
    (out / "cache-policy-matrix.md").write_text(md("Cache policy and capacity matrix", "Default direction: durable object storage/CDN for large bytes; Redis only for bounded metadata/state. Every estimate is an assumption requiring post-release measurement.", [{"topic": r["use_case"], "finding": f"{r['decision']}; max {r['maximum_serialized_bytes']} bytes", "evidence": r["reason"]} for r in policy_rows]), encoding="utf-8")

    target = {"schema_version": "cache-media-target-architecture.v1", "status": "PROPOSAL_ONLY_NO_IMPLEMENTATION", "redis": ["one lifecycle-owned shared async client", "short timeouts and bounded retry", "cache-aside, graceful source fallback", "versioned namespaced user/resource keys", "bounded safe JSON codec; migrate away from pickle", "maximum serialized-value guard", "TTL jitter, precise invalidation, conservative negative cache", "cross-replica singleflight", "hit/miss/bypass/error/latency/value-size/invalidation metrics", "no correctness dependency and no large binary values"], "media": ["durable B2/object storage remains source of truth", "protected media stays same-origin authorized proxy; any signed URL decision requires explicit authorization class", "stream without complete buffering", "maintain Range, ETag, conditional semantics and private cache controls", "close upstream body on completion/error/cancellation"], "pdf": "No customer PDF subsystem until a product path exists.", "failure_modes": ["Redis unavailable/slow/corrupt: bypass and source fallback; delete corrupt value in future", "object storage unavailable/partial stream: bounded 5xx and closed body", "stale authorization/replacement/range changes: short sensitive TTLs plus resource version", "expired signed URL and rollback: route-generated short lived metadata and old key-version compatibility"]}
    write_json(out / "target-architecture.json", target)
    (out / "target-architecture.md").write_text("# Target architecture decision record\n\nProposal only. No production behavior changed in this checkpoint.\n\n## Redis\n\n" + "\n".join(f"- {x}" for x in target["redis"]) + "\n\n## Media\n\n" + "\n".join(f"- {x}" for x in target["media"]) + "\n\n## PDF\n\n" + target["pdf"] + "\n", encoding="utf-8")

    score = {"schema_version": "cache-media-requirements-coverage.v1", "score_type": "REQUIREMENTS_COVERAGE_NOT_PERFORMANCE", "total": 58, "maximum": 100, "categories": [
        {"category": "repository/infrastructure discovery", "awarded": 9, "maximum": 10, "evidence": "checked-in config and workflows", "missing": "live service authority", "confidence": "HIGH"},
        {"category": "durable media-storage topology", "awarded": 8, "maximum": 10, "evidence": "B2 streaming/config paths", "missing": "live object metadata", "confidence": "MEDIUM"},
        {"category": "large-audio delivery", "awarded": 12, "maximum": 15, "evidence": "range/ETag/protected streaming code", "missing": "production HTTP proof and cancellation measurement", "confidence": "MEDIUM"},
        {"category": "large-PDF delivery", "awarded": 1, "maximum": 10, "evidence": "no active customer path", "missing": "product requirement", "confidence": "HIGH"},
        {"category": "Redis cache foundation", "awarded": 7, "maximum": 15, "evidence": "shared client/TTLs/fallback", "missing": "safe codec and size guard", "confidence": "HIGH"},
        {"category": "invalidation/isolation/resilience/stampede", "awarded": 6, "maximum": 10, "evidence": "generations and targeted user invalidation", "missing": "singleflight and complete event coverage", "confidence": "MEDIUM"},
        {"category": "observability/capacity/cache economics", "awarded": 4, "maximum": 10, "evidence": "admin status and local policy", "missing": "live metrics and measured economics", "confidence": "LOW"},
        {"category": "frontend media lifecycle", "awarded": 4, "maximum": 5, "evidence": "same-origin audio preload metadata/none; AbortController for data fetches", "missing": "explicit media cancellation instrumentation", "confidence": "MEDIUM"},
        {"category": "tests and before/after benchmarks", "awarded": 7, "maximum": 10, "evidence": "existing range/auth tests and new local baseline", "missing": "after implementation result", "confidence": "MEDIUM"},
        {"category": "task-specific PR/staging/release/post-release proof", "awarded": 0, "maximum": 5, "evidence": "checkpoint intentionally stops before release", "missing": "all release proof", "confidence": "HIGH"},
    ], "subscores": {"audio_delivery": "12/15", "redis_foundation": "7/15", "pdf_delivery": "1/10", "observability_economics": "4/10", "release_completion": "0/5"}}
    write_json(out / "requirements-coverage-score.json", score)
    (out / "requirements-coverage-score.md").write_text(md("Requirements coverage score", "58/100 is a current requirements-coverage score. It is not latency improvement, cost reduction, performance gain, or production-ready percentage.", [{"topic": r["category"], "finding": f"{r['awarded']}/{r['maximum']}; missing: {r['missing']}", "evidence": r["evidence"]} for r in score["categories"]]), encoding="utf-8")

    lanes = {"schema_version": "cache-media-parallel-lanes.v1", "foundation": {"branch": "codex/cache-media-foundation-extraction", "owned_files": ["backend/cache/**", "backend/media/**", "backend/services/**", "backend/tests/cache_media/**"], "prohibited": ["backend/server.py concurrent edits by more than one lane", "frontend UI until PR #344 merges"], "move_after_characterization": ["_cache_payload_*", "_redis_cache_*", "_public_cache_*", "_streaming_body_iterator", "_parse_byte_range", "_stream_audiobook_asset_url"], "rollback": "single behavior-preserving extraction PR"}, "lanes": [
        {"name": "A Redis abstraction", "branch": "codex/cache-media-redis-codec", "owns": ["backend/cache/**"], "depends_on": "foundation", "tests": "cache_media codec/lifecycle", "rollback": "feature flag/key version", "expected_pr": "safe codec and guard"},
        {"name": "B Audio hardening", "branch": "codex/cache-media-audio-streaming", "owns": ["backend/media/**"], "depends_on": "foundation", "tests": "range/auth/stream tests", "rollback": "old proxy path", "expected_pr": "audio delivery contract"},
        {"name": "C PDF", "branch": "codex/cache-media-pdf-discovery", "owns": ["docs/architecture/cache-media/pdf/**"], "depends_on": "explicit product approval", "tests": "discovery only unless active route", "rollback": "no runtime change", "expected_pr": "only if customer path exists"},
        {"name": "D Metrics", "branch": "codex/cache-media-metrics", "owns": ["backend/cache/**", "scripts/cache_media/**"], "depends_on": "foundation interfaces", "tests": "local benchmark", "rollback": "instrumentation removal", "expected_pr": "metrics/capacity"},
        {"name": "E Frontend lifecycle", "branch": "codex/cache-media-frontend-lifecycle", "owns": ["frontend/src/experiences-v2/**", "frontend/src/components/**"], "depends_on": "PR #344 merged and audio contract", "tests": "frontend media lifecycle", "rollback": "previous UI source handling", "expected_pr": "post-344 frontend"},
        {"name": "F CI/release", "branch": "codex/cache-media-ci-release", "owns": [".github/workflows/**"], "depends_on": "A/B/D merged", "tests": "CI canary", "rollback": "workflow revert", "expected_pr": "serial integration"},
    ]}
    write_json(out / "parallel-lane-plan.json", lanes)
    (out / "parallel-lane-plan.md").write_text("# Parallel implementation plan\n\nFoundation extraction is serial first. No two lanes edit `backend/server.py` before the named interfaces are extracted. Frontend work waits for PR #344.\n\n" + "\n".join(f"- **{lane['name']}** — `{lane['branch']}`; depends on {lane['depends_on']}; owns {', '.join(lane['owns'])}." for lane in lanes["lanes"]) + "\n", encoding="utf-8")

    risks = {"schema_version": "cache-media-risk-register.v1", "risks": [
        {"risk": "unsafe pickle deserialization", "severity": "HIGH", "likelihood": "MEDIUM", "current_control": "only internally written entries; decode errors fall back", "planned_mitigation": "safe codec/key-version migration", "owner_approval_required": False, "release_blocker": True},
        {"risk": "stale authorization", "severity": "HIGH", "likelihood": "MEDIUM", "current_control": "lease authorization before stream; short user TTLs", "planned_mitigation": "precise entitlement invalidation", "owner_approval_required": False, "release_blocker": True},
        {"risk": "cache stampede", "severity": "HIGH", "likelihood": "MEDIUM", "current_control": "TTL jitter only", "planned_mitigation": "selected cross-replica singleflight", "owner_approval_required": False, "release_blocker": True},
        {"risk": "large-file memory/event-loop pressure", "severity": "HIGH", "likelihood": "MEDIUM", "current_control": "1 MiB iterator", "planned_mitigation": "measure and ensure upstream async/cancellation behavior", "owner_approval_required": False, "release_blocker": True},
        {"risk": "Redis memory/eviction mismatch", "severity": "HIGH", "likelihood": "MEDIUM", "current_control": "finite TTL/jitter; checked-in volatile-lfu target", "planned_mitigation": "live capacity baseline", "owner_approval_required": True, "release_blocker": True},
        {"risk": "cross-tenant key collision", "severity": "MEDIUM", "likelihood": "LOW", "current_control": "user/session ids and hashes", "planned_mitigation": "uniform schema version and identity contract", "owner_approval_required": False, "release_blocker": False},
        {"risk": "Range/signed URL/object outage/PDF uncertainty/workflow conflict/metrics gap", "severity": "MEDIUM", "likelihood": "MEDIUM", "current_control": "current range validation, fail-closed B2 configuration, no PDF product, PR overlap exclusion", "planned_mitigation": "characterization tests and serial release", "owner_approval_required": "provider/topology changes only", "release_blocker": True},
    ]}
    write_json(out / "risk-register.json", risks)
    (out / "risk-register.md").write_text(md("Risk register and approval boundaries", "Redis plan, eviction policy, replica count, region, Railway topology, storage provider, and billing tier remain owner-only decisions.", [{"topic": r["risk"], "finding": f"{r['severity']}; mitigation: {r['planned_mitigation']}", "evidence": "risk-register.json"} for r in risks["risks"]]), encoding="utf-8")

    sequence = """# Implementation sequence and acceptance gates

All checkpoints require a clean worktree, regression relevant to their owned paths, `git diff --check`, no secret exposure, and a rollback note.

| Checkpoint | Permitted files | Gate | Approval boundary | Stop condition |
|---|---|---|---|---|
| A1 extraction | `backend/cache/**`, `backend/media/**`, tests | characterization parity | none | behavior differs |
| A2 codec | `backend/cache/**` | safe codec/migration tests | cache key migration review | corrupt/legacy incompatibility |
| A3 limits/metrics | cache and benchmark files | size guard/metrics | capacity threshold approval | no capacity evidence |
| A4 invalidation/singleflight | cache/services files | mutation and concurrent-miss tests | authorization semantics review | stale authorization risk |
| A5 audio hardening | `backend/media/**` | Range/HEAD/ETag/auth tests | protected delivery contract | memory/stream regression |
| A6 PDF | only after product exists | customer route tests | product approval | no active PDF product |
| A7 frontend | frontend after PR #344 | lifecycle/browser tests | PR #344 integrated | overlap/contract mismatch |
| A8 local benchmark | scripts/docs | repeatable local baseline | none | harness failure |
| A9 preview/staging | deployment config only after lanes converge | smoke/canary | deployment approval | staging unavailable |
| A10 production | merged main only | canary and metrics | explicit owner release approval | any release gate fails |
"""
    (out / "implementation-sequence.md").write_text(sequence, encoding="utf-8")
    (out / "self-review.md").write_text("""# Strict self-review

| Classification | Finding |
|---|---|
| REQUIRED_BEFORE_IMPLEMENTATION | Replace pickle decoder with bounded safe codec and a versioned migration. |
| REQUIRED_BEFORE_IMPLEMENTATION | Define a hard serialized-value ceiling and singleflight policy. |
| REQUIRED_BEFORE_IMPLEMENTATION | Prove every mutation event invalidates any affected sensitive cache. |
| REQUIRED_BEFORE_RELEASE | Obtain redacted Railway/Redis/object-store metrics and verify stream cancellation under an authorized staging path. |
| REQUIRED_BEFORE_RELEASE | Keep protected audio authorization ahead of all object reads; no raw provider URL leak. |
| POST_RELEASE_MONITORING | Cache hit/miss/bypass/error/value-size, B2 bytes/range failures, latency/RSS, and eviction behavior. |
| OPTIONAL | Customer PDF delivery remains out of scope until an active product requirement exists. |

Self-review result: no production source, workflow, deployment, secret, or PR #344 file is changed by this checkpoint.
""", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
