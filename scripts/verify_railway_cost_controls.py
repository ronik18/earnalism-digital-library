#!/usr/bin/env python3
"""Verify Railway production cost-control guardrails without importing the app.

This is intentionally static: importing backend/server.py would require live
production secrets and Mongo connectivity. The checks prove the deploy command
and source-level guards are present before a Railway redeploy.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def main() -> int:
    railway = json.loads(_read("backend/railway.json"))
    procfile = _read("backend/Procfile")
    dockerfile = _read("backend/Dockerfile")
    start_prod = _read("backend/start_prod.sh")
    server = _read("backend/server.py")
    package_json = json.loads(_read("package.json"))

    deploy_start = railway.get("deploy", {}).get("startCommand", "")
    unsafe_start_surfaces = "\n".join([deploy_start, procfile, dockerfile, start_prod])
    heavy_tokens = [
        "audiobook_production_pipeline",
        "release_catalog_factory",
        "open_source_audiobook_onboarding.py generate",
        "audiobook_release_gate.py",
        "cloudinary bulk",
        "--reload",
        "watchfiles",
    ]

    checks = [
        _check(
            "railway_start_uses_low_memory_wrapper",
            deploy_start.strip() == "sh ./start_prod.sh",
            f"startCommand={deploy_start!r}",
        ),
        _check(
            "procfile_uses_low_memory_wrapper",
            procfile.strip() == "web: sh ./start_prod.sh",
            procfile.strip(),
        ),
        _check(
            "docker_uses_low_memory_wrapper",
            'CMD ["sh", "./start_prod.sh"]' in dockerfile,
            "Docker CMD delegates to backend/start_prod.sh",
        ),
        _check(
            "single_worker_default",
            'WEB_CONCURRENCY:-1' in start_prod and 'WEB_CONCURRENCY:-2' not in unsafe_start_surfaces,
            "WEB_CONCURRENCY defaults to 1",
        ),
        _check(
            "no_reload_or_heavy_pipeline_in_start",
            not any(token in unsafe_start_surfaces for token in heavy_tokens),
            "start surfaces contain no reload/watch/pipeline command",
        ),
        _check(
            "cost_flags_default_false",
            all(
                f'export {flag}="${{{flag}:-false}}"' in start_prod
                for flag in [
                    "ENABLE_BACKGROUND_WORKERS",
                    "ENABLE_AUDIOBOOK_PIPELINE",
                    "ENABLE_BOOK_RENDERING_JOBS",
                    "ENABLE_COVER_GENERATION",
                    "ENABLE_SCHEDULED_JOBS",
                    "ENABLE_QUEUE_CONSUMER",
                    "ENABLE_ADMIN_MEDIA_UPLOADS",
                    "ENABLE_STARTUP_DB_MAINTENANCE",
                ]
            ),
            "heavy ENABLE_* flags default false",
        ),
        _check(
            "memory_allocator_and_caps_present",
            "MALLOC_ARENA_MAX" in start_prod
            and "MONGODB_MAX_POOL_SIZE" in start_prod
            and "PUBLIC_CACHE_MAX_ENTRIES" in start_prod
            and "MAX_CONCURRENT_JOBS" in start_prod,
            "allocator, Mongo, cache, and concurrency caps are exported",
        ),
        _check(
            "server_has_cost_control_config",
            all(
                token in server
                for token in [
                    "COST_CONTROL_MODE",
                    "ENABLE_AUDIOBOOK_PIPELINE",
                    "ENABLE_BOOK_RENDERING_JOBS",
                    "ENABLE_COVER_GENERATION",
                    "ENABLE_QUEUE_CONSUMER",
                    "REQUEST_BODY_LIMIT_BYTES",
                    "DOCX_UPLOAD_MAX_BYTES",
                ]
            ),
            "server defines cost-control flags and limits",
        ),
        _check(
            "server_blocks_expensive_admin_jobs",
            server.count("_require_expensive_job_enabled(") >= 5
            and "confirm_expensive_job" in server
            and "_expensive_job_slot" in server,
            "admin processing routes require flags, confirmation, and a job slot",
        ),
        _check(
            "startup_maintenance_gated",
            "ENABLE_STARTUP_DB_MAINTENANCE" in server
            and re.search(r"if ENABLE_STARTUP_DB_MAINTENANCE:\s+await _run_startup_database_maintenance", server),
            "startup DB maintenance is explicitly gated",
        ),
        _check(
            "admin_diagnostic_endpoint_present",
            '@api.get("/admin/system/cost-control")' in server
            and "_process_memory_snapshot" in server
            and "runtime_keys_detected" in server,
            "admin-only cost-control diagnostics route is present",
        ),
        _check(
            "request_body_limit_middleware_present",
            "Request body too large for production cost-control limits" in server,
            "middleware rejects oversized requests before endpoint processing",
        ),
        _check(
            "package_cost_audit_script_present",
            package_json.get("scripts", {}).get("cost:audit") == "python3 scripts/verify_railway_cost_controls.py",
            "npm run cost:audit is wired",
        ),
    ]

    passed = all(check["passed"] for check in checks)
    result = {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "next_runtime_probe": "GET /api/admin/system/cost-control with an admin session after Railway redeploy",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
