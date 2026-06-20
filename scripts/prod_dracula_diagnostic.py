#!/usr/bin/env python3
"""Read-only production diagnostic for the controlled Dracula launch."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog_truth import (  # noqa: E402
    CONTROLLED_LAUNCH_CONFIG_PATH,
    DRACULA_ARTIFACT_DIR,
    dracula_artifact_status,
    load_dracula_artifact_book,
    read_json_file,
)


DEFAULT_API_BASE_URL = "https://api.theearnalism.com/api"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "production" / "dracula_diagnostic"
API_PATHS = (
    "/healthz",
    "/books",
    "/books/dracula",
    "/reader/book/dracula/manifest",
    "/reader/book/dracula/audiobook",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_json(api_base_url: str, path: str, *, timeout_seconds: float = 12.0) -> dict[str, Any]:
    url = urljoin(api_base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "EarnalismDraculaDiagnostic/1.0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - operator-selected production URL.
            body = response.read(256_000).decode("utf-8", errors="replace")
            status = int(response.status)
    except HTTPError as exc:
        body = exc.read(256_000).decode("utf-8", errors="replace")
        status = int(exc.code)
    except URLError as exc:
        return {"status": 0, "ok": False, "error": str(exc), "json": None, "body_preview": ""}
    except TimeoutError as exc:
        return {"status": 0, "ok": False, "error": str(exc), "json": None, "body_preview": ""}

    try:
        payload = json.loads(body) if body else None
    except json.JSONDecodeError:
        payload = None
    return {
        "status": status,
        "ok": 200 <= status < 300,
        "error": "",
        "json": payload,
        "body_preview": body[:400],
    }


def database_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    db_name = parsed.path.lstrip("/").split("/", 1)[0]
    return os.environ.get("DB_NAME") or db_name or "earnalism"


def read_only_db_status() -> dict[str, Any]:
    mongo_url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")
    if not mongo_url:
        return {"configured": False, "ok": False, "error": "MONGODB_URL/MONGO_URL not set"}
    try:
        from pymongo import MongoClient  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency issue is environment-specific.
        return {"configured": True, "ok": False, "error": f"pymongo unavailable: {exc}"}
    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
        db = client[database_name_from_url(mongo_url)]
        client.admin.command("ping")
        count = db.books.count_documents({})
        dracula = db.books.find_one({"slug": "dracula"}, {"_id": 0, "slug": 1, "is_published": 1, "publication_status": 1})
        return {
            "configured": True,
            "ok": True,
            "database": db.name,
            "books_count": count,
            "dracula_present": bool(dracula),
            "dracula_public_fields": dracula or None,
        }
    except Exception as exc:
        return {"configured": True, "ok": False, "error": str(exc)}


def artifact_readiness() -> dict[str, Any]:
    status = dracula_artifact_status()
    book = load_dracula_artifact_book(include_content=True)
    chapters = book.get("chapters") if isinstance(book, dict) else []
    return {
        **status,
        "approved_to_publish_exists": (ROOT / "APPROVED_TO_PUBLISH.md").exists(),
        "controlled_launch_config_exists": CONTROLLED_LAUNCH_CONFIG_PATH.exists(),
        "artifact_dir_exists": DRACULA_ARTIFACT_DIR.exists(),
        "public_metadata_exists": (DRACULA_ARTIFACT_DIR / "public_book.json").exists(),
        "reader_manifest_exists": (DRACULA_ARTIFACT_DIR / "reader_manifest.json").exists(),
        "chapter_files_count": len(list((DRACULA_ARTIFACT_DIR / "chapters").glob("chapter-*.json"))),
        "loaded_chapters_count": len(chapters or []),
        "chapter_text_available": bool(chapters and all(str(chapter.get("content") or "").strip() for chapter in chapters)),
    }


def classify_root_cause(api: dict[str, dict[str, Any]], db_status: dict[str, Any], artifact: dict[str, Any]) -> str:
    health = api.get("/healthz", {})
    books = api.get("/books", {})
    detail = api.get("/books/dracula", {})
    manifest = api.get("/reader/book/dracula/manifest", {})

    if health.get("status") != 200:
        return "BACKEND_DOWN"
    if db_status.get("configured") and not db_status.get("ok"):
        return "DB_UNREACHABLE"
    if db_status.get("ok") and int(db_status.get("books_count") or 0) == 0:
        return "DB_EMPTY"
    if not artifact.get("available"):
        return "DRACULA_ARTIFACTS_MISSING_FROM_DEPLOYMENT"
    if manifest.get("status") == 404 and not artifact.get("reader_manifest_exists"):
        return "READER_MANIFEST_ARTIFACT_MISSING"
    if books.get("status") == 200 and books.get("json") == [] and detail.get("status") == 404:
        return "DRACULA_MISSING_FROM_DB"
    if detail.get("status") == 404 and db_status.get("dracula_present"):
        return "DRACULA_PRESENT_BUT_REJECTED_BY_TRUTH_GATE"
    if detail.get("status") not in {200, 404} or manifest.get("status") not in {200, 404}:
        return "ROUTE_WIRING_ERROR"
    return "UNKNOWN"


def write_reports(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "dracula_production_diagnostic.json"
    md_path = output_dir / "dracula_production_diagnostic.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")


def markdown_report(report: dict[str, Any]) -> str:
    endpoint_lines = [
        f"- `{path}`: `{data.get('status')}`"
        for path, data in report["api_endpoints"].items()
    ]
    artifact = report["artifact"]
    db_status = report["database"]
    return "\n".join(
        [
            "# Dracula Production Diagnostic",
            "",
            f"- Generated At: `{report['generated_at']}`",
            f"- API Base URL: `{report['api_base_url']}`",
            f"- Root Cause Classification: `{report['root_cause']}`",
            f"- Mutation Performed: `{report['mutation_performed']}`",
            "",
            "## API Endpoints",
            *endpoint_lines,
            "",
            "## Local Artifact Readiness",
            f"- Artifact Available: `{artifact.get('available')}`",
            f"- Chapter Count: `{artifact.get('chapter_count')}`",
            f"- Chapter Files: `{artifact.get('chapter_files_count')}`",
            f"- Chapter Text Available: `{artifact.get('chapter_text_available')}`",
            f"- Issues: `{artifact.get('issues')}`",
            "",
            "## Read-Only Database Status",
            f"- Configured: `{db_status.get('configured')}`",
            f"- OK: `{db_status.get('ok')}`",
            f"- Books Count: `{db_status.get('books_count', 'unknown')}`",
            f"- Dracula Present: `{db_status.get('dracula_present', 'unknown')}`",
            "",
            "## Operator Decision",
            "- KEEP_DRACULA_LIVE only after backend catalog truth and post-production canaries pass.",
            "- HOLD_ADS until Dracula API and reader manifest are restored.",
            "- No production data was mutated by this diagnostic.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base-url", default=os.environ.get("API_BASE_URL", DEFAULT_API_BASE_URL))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    api = {path: fetch_json(args.api_base_url, path) for path in API_PATHS}
    artifact = artifact_readiness()
    db_status = read_only_db_status()
    root_cause = classify_root_cause(api, db_status, artifact)
    report = {
        "generated_at": now_iso(),
        "api_base_url": args.api_base_url.rstrip("/"),
        "mutation_performed": False,
        "root_cause": root_cause,
        "api_endpoints": api,
        "controlled_launch_config": read_json_file(CONTROLLED_LAUNCH_CONFIG_PATH),
        "artifact": artifact,
        "database": db_status,
    }
    write_reports(report, Path(args.output_dir))
    print(f"Dracula production diagnostic complete: root_cause={root_cause} output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
