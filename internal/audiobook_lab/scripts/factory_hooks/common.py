#!/usr/bin/env python3
"""Shared helpers for release-factory hook adapters."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[4]
REQUIRED_COVER_SIZE = (1600, 2400)


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    ensure_dir(path.parent)
    path.write_text(value, encoding="utf-8")


def rel(path: Path | str | None) -> str:
    if path is None:
        return ""
    value = Path(path)
    try:
        return str(value.relative_to(ROOT))
    except ValueError:
        return str(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fetch_url(url: str, *, timeout: float = 20.0, max_bytes: int | None = None) -> dict[str, Any]:
    if not url:
        return {"status": 0, "ok": False, "headers": {}, "body": b"", "error": "missing_url"}
    request = Request(url, headers={"User-Agent": "EarnalismFactoryHook/1.0", "Accept": "*/*"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes) if max_bytes else response.read()
            return {
                "status": int(response.status),
                "ok": 200 <= int(response.status) < 300,
                "headers": dict(response.headers),
                "body": body,
                "error": "",
            }
    except HTTPError as exc:
        return {"status": int(exc.code), "ok": False, "headers": dict(exc.headers), "body": exc.read(512), "error": str(exc.reason or "")}
    except (URLError, TimeoutError, OSError) as exc:
        return {"status": 0, "ok": False, "headers": {}, "body": b"", "error": str(exc)}


def download_url(url: str, path: Path) -> dict[str, Any]:
    fetched = fetch_url(url, timeout=60)
    if not fetched["ok"]:
        return {"ok": False, "status": fetched["status"], "error": fetched["error"]}
    ensure_dir(path.parent)
    path.write_bytes(fetched["body"])
    return {"ok": True, "status": fetched["status"], "sha256": sha256_file(path), "size": path.stat().st_size}


def image_dimensions(path_or_bytes: Path | bytes) -> list[int] | None:
    try:
        from io import BytesIO
        from PIL import Image

        image = Image.open(path_or_bytes if isinstance(path_or_bytes, Path) else BytesIO(path_or_bytes))
        return [int(image.size[0]), int(image.size[1])]
    except Exception:
        return None


def normalize_text(text: str) -> str:
    text = re.sub(r"[\u200c\u200d]", "", text or "")
    text = re.sub(r"[^\u0980-\u09FFA-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def word_tokens(text: str) -> list[str]:
    return re.findall(r"[\u0980-\u09FFA-Za-z0-9]+", text or "")


def controlled_dir(slug: str) -> Path:
    return ROOT / "data" / "controlled_publications" / slug


def public_book_path(slug: str) -> Path:
    return controlled_dir(slug) / "public_book.json"


def load_public_book(slug: str) -> dict[str, Any]:
    return read_json(public_book_path(slug), {})


def load_clean_manuscript(args: argparse.Namespace) -> str:
    path = Path(args.run_dir) / "clean_manuscript.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    chapters_dir = controlled_dir(args.slug) / "chapters"
    parts: list[str] = []
    for chapter_path in sorted(chapters_dir.glob("*.json")):
        payload = read_json(chapter_path, {})
        text = str(payload.get("content") or payload.get("text") or payload.get("body") or "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip() + ("\n" if parts else "")


def write_clean_manuscript_if_missing(args: argparse.Namespace) -> Path:
    path = Path(args.run_dir) / "clean_manuscript.txt"
    if not path.exists():
        write_text(path, load_clean_manuscript(args))
    return path


def has_cloudinary_credentials() -> bool:
    return bool(
        os.environ.get("CLOUDINARY_URL")
        or (
            os.environ.get("CLOUDINARY_CLOUD_NAME")
            and os.environ.get("CLOUDINARY_API_KEY")
            and os.environ.get("CLOUDINARY_API_SECRET")
        )
    )


def cloudinary_configure() -> None:
    import cloudinary

    if os.environ.get("CLOUDINARY_URL"):
        cloudinary.config(secure=True)
        return
    cloudinary.config(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
        secure=True,
    )


def verify_remote_checksum(url: str, local_path: Path) -> dict[str, Any]:
    fetched = fetch_url(url, timeout=90)
    remote_hash = hashlib.sha256(fetched["body"]).hexdigest() if fetched["body"] else ""
    local_hash = sha256_file(local_path) if local_path.exists() else ""
    return {
        "url": url,
        "status": fetched["status"],
        "resolves": fetched["ok"],
        "local_sha256": local_hash,
        "remote_sha256": remote_hash,
        "match": bool(local_hash and remote_hash and local_hash == remote_hash),
        "local_size": local_path.stat().st_size if local_path.exists() else 0,
        "remote_size": len(fetched["body"]) if fetched["body"] else 0,
        "content_type": fetched["headers"].get("Content-Type", ""),
    }


def run_cmd(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 300) -> dict[str, Any]:
    started = time.time()
    completed = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, check=False)
    return {
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "duration_seconds": round(time.time() - started, 3),
    }


def ffprobe_duration(path: Path) -> float | None:
    if not shutil.which("ffprobe"):
        return None
    result = run_cmd(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        timeout=60,
    )
    if result["returncode"] != 0:
        return None
    try:
        return float(result["stdout"].strip())
    except ValueError:
        return None


def upload_cloudinary(path: Path, *, folder: str, resource_type: str, public_id: str | None = None) -> dict[str, Any]:
    cloudinary_configure()
    import cloudinary.uploader

    options = {"resource_type": resource_type, "folder": folder, "overwrite": True, "use_filename": False, "unique_filename": False}
    if public_id:
        options["public_id"] = public_id
    result = cloudinary.uploader.upload(str(path), **options)
    return {
        "secure_url": result.get("secure_url") or result.get("url"),
        "public_id": result.get("public_id"),
        "resource_type": result.get("resource_type"),
        "bytes": result.get("bytes"),
        "format": result.get("format"),
    }


def parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--slug", required=True)
    arg_parser.add_argument("--run-dir", required=True)
    arg_parser.add_argument("--manifest", required=True)
    arg_parser.add_argument("--language", required=True)
    arg_parser.add_argument("--title", required=True)
    arg_parser.add_argument("--author", required=True)
    arg_parser.add_argument("--max-attempts", type=int, default=4)
    arg_parser.add_argument("--fail-closed", action="store_true")
    arg_parser.add_argument("--dry-run", action="store_true")
    arg_parser.add_argument("--resume", action="store_true")
    arg_parser.add_argument("--previous-evidence", default="")
    arg_parser.add_argument("--catalog-run-dir", default="")
    return arg_parser


def base_result(args: argparse.Namespace, stage: str, started_at: str) -> dict[str, Any]:
    return {
        "slug": args.slug,
        "stage": stage,
        "status": "BLOCKED",
        "ready_for_next_stage": False,
        "blocker_category": stage,
        "blockers": [],
        "retryable": True,
        "artifacts": {},
        "metrics": {},
        "updated_fields": {},
        "command_used": " ".join(sys.argv),
        "started_at": started_at,
        "finished_at": iso_now(),
    }


def finish(args: argparse.Namespace, stage: str, started_at: str, **updates: Any) -> int:
    result = base_result(args, stage, started_at)
    result.update(updates)
    result["finished_at"] = iso_now()
    run_dir = Path(args.run_dir)
    write_json(run_dir / "stage_result.json", result)
    write_json(run_dir / f"{stage}_hook_result.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"PASS", "BLOCKED", "SKIPPED"} else 1


def validation_pass(args: argparse.Namespace, stage: str, started_at: str, metrics: dict[str, Any] | None = None) -> int:
    return finish(
        args,
        stage,
        started_at,
        status="PASS",
        ready_for_next_stage=True,
        blocker_category="none",
        blockers=[],
        retryable=False,
        metrics=metrics or {},
    )


def mime_type(path: Path) -> str:
    return mimetypes.guess_type(str(path))[0] or "application/octet-stream"
