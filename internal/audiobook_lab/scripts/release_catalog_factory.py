#!/usr/bin/env python3
"""Parallel, fail-closed Earnalism catalog release factory.

The factory is intentionally an orchestrator. It inventories all requested
books, runs release queues concurrently, writes resumable per-book state, and
publishes a book only after that book's own gates pass. Heavyweight generation
work is delegated to explicit hooks or existing repo artifacts; absence of a
verified artifact is a blocker, not a reason to fake readiness.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[3]
RELEASE_GATE_ROOT = ROOT / "internal" / "audiobook_lab" / "release_gate"
DEFAULT_MANIFEST = ROOT / "book_import_manifest.json"
DEFAULT_FRONTEND_URL = "https://theearnalism.com"
DEFAULT_API_URL = "https://api.theearnalism.com"
CATALOG_LOCK_PATH = RELEASE_GATE_ROOT / ".release_catalog_factory.lock"
REQUIRED_COVER_SIZE = [1600, 2400]
QA_SCHEMA_VERSION = 3
CONTROLLED_PUBLICATION_ROOTS = (
    ROOT / "data" / "controlled_publications",
    ROOT / "backend" / "data" / "controlled_publications",
)


def controlled_publication_base(slug: str) -> Path:
    """Return the root-first controlled packet, falling back to backend data."""

    for publication_root in CONTROLLED_PUBLICATION_ROOTS:
        candidate = publication_root / slug
        if (candidate / "public_book.json").is_file():
            return candidate
    for publication_root in CONTROLLED_PUBLICATION_ROOTS:
        candidate = publication_root / slug
        if candidate.is_dir():
            return candidate
    return CONTROLLED_PUBLICATION_ROOTS[0] / slug

QUEUE_NAMES = [
    "inventory_queue",
    "cover_queue",
    "manuscript_queue",
    "rights_metadata_preflight_queue",
    "tts_queue",
    "asr_sync_queue",
    "qa_queue",
    "upload_queue",
    "metadata_publish_queue",
    "browser_gate_queue",
]

LANE_NAMES = [
    "preflight_lane",
    "cover_lane",
    "audio_reuse_lane",
    "tts_lane",
    "asr_sync_lane",
    "qa_lane",
    "upload_lane",
    "metadata_lane",
    "browser_lane",
    "publish_barrier",
]

STAGE_TO_LANE = {
    "inventory_queue": "preflight_lane",
    "manuscript_queue": "preflight_lane",
    "rights_metadata_preflight_queue": "preflight_lane",
    "cover_queue": "cover_lane",
    # The TTS hook is reuse-first and paid-generation second. Keep the stage
    # as one fail-closed queue, but expose both logical lanes in dashboards.
    "tts_queue": "audio_reuse_lane",
    "asr_sync_queue": "asr_sync_lane",
    "qa_queue": "qa_lane",
    "upload_queue": "upload_lane",
    "metadata_publish_queue": "metadata_lane",
    "browser_gate_queue": "browser_lane",
}

ENV_KEYS = [
    "OPENAI_API_KEY",
    "CLOUDINARY_URL",
    "CLOUDINARY_CLOUD_NAME",
    "CLOUDINARY_API_KEY",
    "CLOUDINARY_API_SECRET",
    "EARNALISM_RELEASE_FACTORY_COVER_COMMAND",
    "EARNALISM_RELEASE_FACTORY_TTS_COMMAND",
    "EARNALISM_RELEASE_FACTORY_ASR_SYNC_COMMAND",
    "EARNALISM_RELEASE_FACTORY_UPLOAD_COMMAND",
    "EARNALISM_RELEASE_FACTORY_METADATA_COMMAND",
    "EARNALISM_RELEASE_FACTORY_BROWSER_COMMAND",
]

HOOK_STAGES = {
    "cover_queue": ("cover", "EARNALISM_RELEASE_FACTORY_COVER_COMMAND"),
    "tts_queue": ("tts", "EARNALISM_RELEASE_FACTORY_TTS_COMMAND"),
    "asr_sync_queue": ("asr_sync", "EARNALISM_RELEASE_FACTORY_ASR_SYNC_COMMAND"),
    "upload_queue": ("upload", "EARNALISM_RELEASE_FACTORY_UPLOAD_COMMAND"),
    "metadata_publish_queue": ("metadata", "EARNALISM_RELEASE_FACTORY_METADATA_COMMAND"),
    "browser_gate_queue": ("browser", "EARNALISM_RELEASE_FACTORY_BROWSER_COMMAND"),
}

STAGE_BLOCKER_CATEGORIES = {
    "cover_queue": {"covers"},
    "manuscript_queue": {"manuscript", "content"},
    "rights_metadata_preflight_queue": {"metadata_rights", "rights_metadata"},
    "tts_queue": {"tts"},
    "asr_sync_queue": {
        "asr",
        "sync",
        "listening_qa_schema_missing",
        "listening_qa_not_run",
        "audio_listening_quality_failed",
        "audio_provider_quality_limit",
        "bengali_asr_script_mismatch",
        "bengali_asr_low_confidence",
        "bengali_audio_manuscript_mismatch",
        "bengali_sync_regeneration_required",
        "bengali_audio_provider_quality",
    },
    "qa_queue": {"qa", "audio_qa", "audio_provider_quality_limit", "bengali_audio_provider_quality"},
    "upload_queue": {"upload/checksum", "upload"},
    "metadata_publish_queue": {"metadata", "metadata_api"},
    "browser_gate_queue": {"browser"},
}

DEFAULT_HOOK_COMMANDS = {
    "cover_queue": "python3 internal/audiobook_lab/scripts/factory_hooks/cover_hook.py --slug {slug} --run-dir {book_run_dir} --catalog-run-dir {catalog_run_dir} --manifest {manifest} --language {language} --title {title} --author {author} --max-attempts {max_attempts} {dry_run_flag} {resume_flag} {fail_closed_flag}",
    "tts_queue": "python3 internal/audiobook_lab/scripts/factory_hooks/tts_hook.py --slug {slug} --run-dir {book_run_dir} --catalog-run-dir {catalog_run_dir} --manifest {manifest} --language {language} --title {title} --author {author} --max-attempts {max_attempts} {dry_run_flag} {resume_flag} {fail_closed_flag}",
    "asr_sync_queue": "python3 internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py --slug {slug} --run-dir {book_run_dir} --catalog-run-dir {catalog_run_dir} --manifest {manifest} --language {language} --title {title} --author {author} --max-attempts {max_attempts} {dry_run_flag} {resume_flag} {fail_closed_flag}",
    "upload_queue": "python3 internal/audiobook_lab/scripts/factory_hooks/upload_hook.py --slug {slug} --run-dir {book_run_dir} --catalog-run-dir {catalog_run_dir} --manifest {manifest} --language {language} --title {title} --author {author} --max-attempts {max_attempts} {dry_run_flag} {resume_flag} {fail_closed_flag}",
    "metadata_publish_queue": "python3 internal/audiobook_lab/scripts/factory_hooks/metadata_hook.py --slug {slug} --run-dir {book_run_dir} --catalog-run-dir {catalog_run_dir} --manifest {manifest} --language {language} --title {title} --author {author} --max-attempts {max_attempts} {dry_run_flag} {resume_flag} {fail_closed_flag}",
    "browser_gate_queue": "python3 internal/audiobook_lab/scripts/factory_hooks/browser_hook.py --slug {slug} --run-dir {book_run_dir} --catalog-run-dir {catalog_run_dir} --manifest {manifest} --language {language} --title {title} --author {author} --max-attempts {max_attempts} {dry_run_flag} {resume_flag} {fail_closed_flag}",
}

JUNK_PATTERNS = [
    ("mojibake", re.compile(r"\uFFFD")),
    ("raw_html", re.compile(r"</?(html|body|script|style|div|span|p|br|h[1-6])\b", re.I)),
    ("markdown_fence", re.compile(r"```")),
    ("json_fragment", re.compile(r"\{\s*\"[^\"]+\"\s*:")),
    ("traceback", re.compile(r"Traceback \(most recent call last\)|JSONDecodeError|Unhandled exception", re.I)),
    ("pipeline_boilerplate", re.compile(r"(?m)^\s*(pipeline|generated by|debug|log:|prompt:)\b", re.I)),
    ("source_repository", re.compile(r"\b(project gutenberg|gutenberg\.org|wikisource|wikimedia|repository)\b", re.I)),
    ("page_number_line", re.compile(r"(?m)^\s*(page|পৃষ্ঠা|পৃ\.?)?\s*\d+\s*$", re.I)),
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def rel(path: Path | str | None) -> str:
    if path is None:
        return ""
    value = Path(path)
    try:
        return str(value.relative_to(ROOT))
    except ValueError:
        return str(value)


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
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp_path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def write_text(path: Path, value: str) -> None:
    ensure_dir(path.parent)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp_path.write_text(value, encoding="utf-8")
    tmp_path.replace(path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact_command(command: str) -> str:
    if not command:
        return ""
    parts = []
    secret_next = False
    for part in shlex.split(command):
        lower = part.lower()
        if secret_next:
            parts.append("[redacted]")
            secret_next = False
            continue
        if any(token in lower for token in ("secret", "token", "password", "api_key", "apikey", "authorization")):
            if "=" in part:
                parts.append(part.split("=", 1)[0] + "=[redacted]")
            else:
                parts.append(part)
                secret_next = True
        else:
            parts.append(part)
    return " ".join(parts)


def parse_bool_arg(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def normalize_slug(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^\w\s\-\u0980-\u09ff]+", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-")


def normalize_language(value: str) -> str:
    text = (value or "").strip().lower()
    if text in {"bn", "ben", "bengali"}:
        return "ben"
    if text in {"en", "eng", "english"}:
        return "eng"
    return text


def infer_language(*values: str) -> str:
    joined = "\n".join(value or "" for value in values)
    if re.search(r"[\u0980-\u09ff]", joined):
        return "ben"
    return "eng"


def word_tokens(text: str) -> list[str]:
    return re.findall(r"[\u0980-\u09FFA-Za-z0-9]+", text or "")


def normalize_text(text: str) -> str:
    text = re.sub(r"[\u200c\u200d]", "", text or "")
    text = re.sub(r"[^\u0980-\u09FFA-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def sequence_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    from difflib import SequenceMatcher

    return float(SequenceMatcher(None, a, b).ratio())


def fetch_url(url: str, *, timeout: float = 15.0) -> dict[str, Any]:
    if not url:
        return {"status": 0, "ok": False, "headers": {}, "body": b"", "error": "missing_url"}
    request = Request(url, headers={"User-Agent": "EarnalismReleaseCatalogFactory/1.0", "Accept": "*/*"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
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


def image_dimensions(data: bytes) -> list[int] | None:
    if not data:
        return None
    try:
        from PIL import Image
        from io import BytesIO

        image = Image.open(BytesIO(data))
        return [int(image.size[0]), int(image.size[1])]
    except Exception:
        return None


def command_template(value: str, state: "BookState", extra: dict[str, Any] | None = None) -> list[str]:
    payload = {
        "slug": state.slug,
        "book_run_dir": str(state.run_dir),
        "catalog_run_dir": str(state.catalog_dir),
        "manifest": str(Path(getattr(state, "manifest_record", {}).get("_manifest_path") or DEFAULT_MANIFEST)),
        "language": state.language,
        "title": state.title,
        "author": state.author,
        "max_attempts": str(extra.get("max_attempts", 4) if extra else 4),
        "dry_run_flag": "--dry-run" if extra and extra.get("dry_run") else "",
        "resume_flag": "--resume" if extra and extra.get("resume") else "",
        "fail_closed_flag": "--fail-closed" if extra and extra.get("fail_closed") else "",
    }
    if extra:
        payload.update(extra)
    return [part.format(**payload) for part in shlex.split(value) if part.format(**payload)]


def run_hook(command: str, state: "BookState", stage: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not command:
        return {"status": "BLOCKED", "reason": f"{stage} hook is not configured."}
    cmd = command_template(command, state, extra)
    log_path = state.run_dir / f"{stage}_hook.log"
    hook_name = HOOK_STAGES.get(stage, (stage, ""))[0]
    stage_result_path = state.run_dir / "stage_result.json"
    hook_result_path = state.run_dir / f"{hook_name}_hook_result.json"
    queue_result_path = state.run_dir / f"{stage}_result.json"
    for stale_path in (stage_result_path, hook_result_path, queue_result_path):
        if stale_path.exists():
            try:
                stale_path.unlink()
            except OSError:
                pass
    completed = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    write_text(log_path, completed.stdout or "")
    result = {
        "status": "PASS" if completed.returncode == 0 else "BLOCKED",
        "command": cmd,
        "returncode": completed.returncode,
        "log_path": rel(log_path),
    }
    for candidate in (hook_result_path, queue_result_path, stage_result_path):
        if candidate.exists():
            hook_result = read_json(candidate, {})
            if isinstance(hook_result, dict):
                result_stage = str(hook_result.get("stage") or "").strip()
                if result_stage and result_stage != hook_name:
                    continue
                result.update(hook_result)
                result.setdefault("result_path", rel(candidate))
                result["status"] = hook_result.get("status") or result["status"]
            break
    if "result_path" not in result and completed.stdout:
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip().startswith("{")]
        if lines:
            try:
                hook_result = json.loads(lines[-1])
                if isinstance(hook_result, dict):
                    result.update(hook_result)
                    result["status"] = hook_result.get("status") or result["status"]
            except json.JSONDecodeError:
                pass
    return result


def hook_blocker_reasons(result: dict[str, Any], fallback: str) -> list[str]:
    blockers = result.get("blockers")
    if isinstance(blockers, list):
        reasons = [str(item) for item in blockers if str(item).strip()]
        if reasons:
            return reasons
    reason = str(result.get("reason") or "").strip()
    if reason:
        return [reason]
    return [fallback]


def qa_blocker_category(reason: str, language: str) -> str:
    lowered = reason.lower()
    audio_quality_tokens = {
        "naturalness",
        "emotional_expression",
        "pronunciation",
        "punctuation_pause",
        "pacing",
        "continuity",
        "robotic",
        "mechanical",
        "list_reading",
        "choppy",
        "listener_enjoyment",
        "listening_qa",
        "dialogue_emotional",
        "abrupt_tts",
        "placeholder_audio",
        "fallback_tts",
    }
    if any(token in lowered for token in audio_quality_tokens):
        return "bengali_audio_provider_quality" if language == "ben" else "audio_provider_quality_limit"
    return "qa"


@contextmanager
def exclusive_lock(path: Path, payload: dict[str, Any]):
    ensure_dir(path.parent)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except FileExistsError as exc:
        raise SystemExit(f"Lock already exists: {path}") from exc
    try:
        yield
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


@dataclass
class StageResult:
    status: str
    blockers: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class BookState:
    slug: str
    title: str
    author: str
    language: str
    order: int
    catalog_dir: Path
    run_dir: Path
    manifest_record: dict[str, Any] = field(default_factory=dict)
    stage_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    blockers: list[dict[str, str]] = field(default_factory=list)
    classifications: list[str] = field(default_factory=list)
    published: bool = False
    ready: bool = False
    next_stage: str | None = None
    inventory_seen: bool = False
    book_attempted: bool = False
    stage_started_events: list[dict[str, str]] = field(default_factory=list)
    terminal_status: str = ""
    terminal_at: str = ""

    @property
    def state_path(self) -> Path:
        return self.run_dir / "book_release_state.json"

    def add_blocker(self, category: str, reason: str) -> None:
        item = {"category": category, "reason": reason}
        if item not in self.blockers:
            self.blockers.append(item)

    def to_json(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": self.title,
            "author": self.author,
            "language": self.language,
            "order": self.order,
            "catalog_dir": rel(self.catalog_dir),
            "run_dir": rel(self.run_dir),
            "manifest_record": self.manifest_record,
            "stage_results": self.stage_results,
            "blockers": self.blockers,
            "classifications": self.classifications,
            "published": self.published,
            "ready": self.ready,
            "next_stage": self.next_stage,
            "inventory_seen": self.inventory_seen,
            "book_attempted": self.book_attempted,
            "stage_started_events": self.stage_started_events,
            "terminal_status": self.terminal_status,
            "terminal_at": self.terminal_at,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "BookState":
        state = cls(
            slug=payload["slug"],
            title=payload.get("title") or payload["slug"],
            author=payload.get("author") or "",
            language=payload.get("language") or "eng",
            order=int(payload.get("order", 0)),
            catalog_dir=ROOT / payload.get("catalog_dir", ""),
            run_dir=ROOT / payload.get("run_dir", ""),
            manifest_record=payload.get("manifest_record") or {},
        )
        state.stage_results = payload.get("stage_results") or {}
        state.blockers = payload.get("blockers") or []
        state.classifications = payload.get("classifications") or []
        state.published = bool(payload.get("published"))
        state.ready = bool(payload.get("ready"))
        state.next_stage = payload.get("next_stage")
        state.inventory_seen = bool(payload.get("inventory_seen") or state.stage_results.get("inventory_queue"))
        state.book_attempted = bool(payload.get("book_attempted") or any(stage in REAL_WORK_STAGES for stage in state.stage_results))
        state.stage_started_events = payload.get("stage_started_events") or []
        state.terminal_status = str(payload.get("terminal_status") or "")
        state.terminal_at = str(payload.get("terminal_at") or "")
        return state

    def save(self) -> None:
        ensure_dir(self.run_dir)
        write_json(self.state_path, self.to_json())

    def mark_stage_started(self, stage: str) -> None:
        if stage == "inventory_queue":
            return
        self.book_attempted = True
        self.stage_started_events.append({"stage": stage, "started_at": iso_now()})


REAL_WORK_STAGES = tuple(stage for stage in QUEUE_NAMES if stage != "inventory_queue")
TERMINAL_STATUSES = {"PUBLISHED", "BLOCKED", "TERMINAL_BLOCKED_WITH_EVIDENCE", "FAILED", "SKIPPED_TERMINAL"}
STAGE_EVENT_PREFIX = {
    "inventory_queue": "book_inventory",
    "cover_queue": "cover",
    "manuscript_queue": "content_integrity",
    "rights_metadata_preflight_queue": "rights_metadata",
    "tts_queue": "tts",
    "asr_sync_queue": "asr_sync",
    "qa_queue": "qa",
    "upload_queue": "upload",
    "metadata_publish_queue": "metadata",
    "browser_gate_queue": "browser",
}


def stage_event_name(stage: str, suffix: str) -> str:
    return f"{STAGE_EVENT_PREFIX.get(stage, stage)}_{suffix}"


def inferred_terminal_status(state: BookState) -> str:
    if state.published:
        return "PUBLISHED"
    if state.next_stage:
        return ""
    statuses = [str(result.get("status") or "").upper() for result in state.stage_results.values() if isinstance(result, dict)]
    if any(status in {"FAILED", "ERROR"} for status in statuses):
        return "FAILED"
    if state.blockers and any(
        isinstance(result, dict)
        and str(result.get("status") or "").upper() in {"BLOCKED", "CONTENT_INTEGRITY_BLOCKED"}
        and result.get("retryable") is False
        for result in state.stage_results.values()
    ):
        return "TERMINAL_BLOCKED_WITH_EVIDENCE"
    if state.blockers or any("BLOCKED" in status or status == "CONTENT_INTEGRITY_BLOCKED" for status in statuses):
        return "BLOCKED"
    if any("SKIPPED" in status for status in statuses):
        return "SKIPPED_TERMINAL"
    return ""


def state_inventory_seen(state: BookState) -> bool:
    return bool(state.inventory_seen or state.stage_results.get("inventory_queue"))


def state_book_attempted(state: BookState) -> bool:
    return bool(
        state.book_attempted
        or state.stage_started_events
        or any(stage in REAL_WORK_STAGES for stage in state.stage_results)
    )


def state_terminal_status(state: BookState) -> str:
    return state.terminal_status if state.terminal_status in TERMINAL_STATUSES else inferred_terminal_status(state)


def newer_passed_stage_result(state: BookState, stage: str) -> dict[str, Any] | None:
    hook_name = HOOK_STAGES.get(stage, (stage, ""))[0]
    current_mtime = 0.0
    try:
        current_mtime = state.state_path.stat().st_mtime
    except OSError:
        pass
    candidates = [
        state.run_dir / f"{hook_name}_hook_result.json",
        state.run_dir / f"{stage}_result.json",
        state.run_dir / "stage_result.json",
    ]
    for candidate in candidates:
        try:
            candidate_mtime = candidate.stat().st_mtime
        except OSError:
            continue
        if candidate_mtime <= current_mtime:
            continue
        result = read_json(candidate, {})
        if not isinstance(result, dict):
            continue
        result_stage = str(result.get("stage") or "").strip()
        if result_stage and result_stage not in {stage, hook_name}:
            continue
        if str(result.get("status") or "").upper() != "PASS":
            continue
        result.setdefault("result_path", rel(candidate))
        return result
    return None


def reconcile_newer_passed_stage_results(state: BookState) -> bool:
    reconciled = False
    for stage in QUEUE_NAMES:
        current = state.stage_results.get(stage)
        if isinstance(current, dict) and str(current.get("status") or "").upper() == "PASS":
            before = len(state.blockers)
            clear_stage_blockers(state, stage)
            if len(state.blockers) != before:
                state.terminal_status = ""
                state.terminal_at = ""
                reconciled = True
            continue
        result = newer_passed_stage_result(state, stage)
        if not result:
            continue
        state.stage_results[stage] = result
        clear_stage_blockers(state, stage)
        state.terminal_status = ""
        state.terminal_at = ""
        state.ready = False
        state.next_stage = next_incomplete_stage_after(stage, state)
        reconciled = True
    return reconciled


def catalog_counter_snapshot(states: Iterable[BookState]) -> dict[str, int]:
    state_list = list(states)
    return {
        "inventory_seen_count": sum(1 for state in state_list if state_inventory_seen(state)),
        "stage_started_count": sum(len(state.stage_started_events) for state in state_list),
        "book_attempted_count": sum(1 for state in state_list if state_book_attempted(state)),
        "terminal_book_count": sum(1 for state in state_list if state_terminal_status(state) in TERMINAL_STATUSES),
        "published_count": sum(1 for state in state_list if state.published),
    }


def verified_published_slugs_from_evidence() -> set[str]:
    """Return slugs with historical evidence proving a production-live release.

    This is intentionally separate from per-wave counters so stop guards still
    operate only on the current run while dashboard totals do not imply zero
    catalog publications after a later zero-publish wave.
    """
    slugs: set[str] = set()
    release_root = ROOT / "internal" / "audiobook_lab" / "release_gate"
    if not release_root.exists():
        return slugs
    for evidence_path in release_root.glob("*/goliveevidence.json"):
        evidence = read_json(evidence_path, {})
        slug = normalize_slug(str(evidence.get("slug") or evidence_path.parent.name.split("_", 1)[0]))
        if not slug:
            continue
        blockers = evidence.get("blocker_list")
        if blockers is None:
            blockers = evidence.get("blockers")
        blocker_list = blockers if isinstance(blockers, list) else []
        browser_result = evidence.get("browser_gate_result") or evidence.get("browser_result") or {}
        browser_pass = isinstance(browser_result, dict) and browser_result.get("status") == "PASS"
        production_ok = evidence.get("production_approval_result") is True or evidence.get("metadata_update_result") is True
        auto_ok = evidence.get("auto_approval_decision") is True or evidence.get("auto_approval_decision") == "APPROVED"
        if auto_ok and production_ok and browser_pass and not blocker_list:
            slugs.add(slug)
    return slugs


def stop_after_attempted_counter_value(states: Iterable[BookState]) -> int:
    return sum(1 for state in states if state_book_attempted(state) or state_terminal_status(state) in TERMINAL_STATUSES)


def lane_for_stage(stage: str) -> str:
    return STAGE_TO_LANE.get(stage, stage)


def lane_counts_from_stage_counts(stage_counts: dict[str, int] | Counter[str]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for stage, count in stage_counts.items():
        counts[lane_for_stage(stage)] += int(count or 0)
    return {lane: counts.get(lane, 0) for lane in LANE_NAMES}


def completed_by_lane(states: Iterable[BookState]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for state in states:
        for stage, result in state.stage_results.items():
            if isinstance(result, dict) and result.get("status") == "PASS":
                counts[lane_for_stage(stage)] += 1
    return {lane: counts.get(lane, 0) for lane in LANE_NAMES}


def blocked_by_lane(states: Iterable[BookState]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for state in states:
        state_blocked_lanes: set[str] = set()
        for stage, result in state.stage_results.items():
            if not isinstance(result, dict):
                continue
            status = str(result.get("status") or "").upper()
            if status and status != "PASS":
                state_blocked_lanes.add(lane_for_stage(stage))
        if any(item.get("category") == "release_order" for item in state.blockers):
            state_blocked_lanes.add("publish_barrier")
        for lane in state_blocked_lanes:
            counts[lane] += 1
    return {lane: counts.get(lane, 0) for lane in LANE_NAMES}


class ReleaseCatalogFactory:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.started_at = iso_now()
        self.timestamp = utc_stamp()
        self.catalog_dir = self._catalog_dir()
        ensure_dir(self.catalog_dir)
        self.command = " ".join([Path(sys.argv[0]).as_posix(), *sys.argv[1:]])
        self.env_detected = {key: bool(os.environ.get(key)) for key in ENV_KEYS}
        self.subset_slugs = {normalize_slug(value) for value in (args.slugs or "").split(",") if normalize_slug(value)}
        self.exclude_slugs = {normalize_slug(value) for value in (args.exclude_slugs or "").split(",") if normalize_slug(value)}
        self.include_statuses = {value.strip().lower() for value in re.split(r"[, ]+", args.include_status or "") if value.strip()}
        self.wave_size = max(0, int(args.wave_size or 0))
        self.stop_after_published = max(0, int(args.stop_after_published or 0))
        self.stop_after_attempted = max(0, int(getattr(args, "stop_after_attempted", 0) or 0))
        self.stop_after_terminal_books = max(0, int(getattr(args, "stop_after_terminal_books", 0) or 0))
        self.deadline_epoch = time.monotonic() + (float(args.max_run_minutes) * 60.0) if args.max_run_minutes else None
        self.content_size_ranking: list[dict[str, Any]] = []
        self.content_rank_by_slug: dict[str, int] = {}
        self.duplicate_manifest_rows: list[dict[str, Any]] = []
        self.stop_reason = ""
        self.stop_guard_triggered = False
        self.stop_guard_counter_used = ""
        self.stop_guard_counter_value = 0
        self.stop_guard_limit = 0
        self.initial_published_slugs: set[str] = set()
        self.last_heartbeat_epoch = 0.0
        self.hook_plan = self.build_hook_plan()
        self.hook_validation: dict[str, Any] = read_json(self.catalog_dir / "hook_validation.json", {})
        self.states: dict[str, BookState] = {}
        self.stage_queues: dict[str, deque[BookState]] = {name: deque() for name in QUEUE_NAMES}
        preflight_workers = max(1, int(getattr(args, "max_preflight_workers", 0) or args.max_books_active))
        audio_reuse_workers = max(1, int(getattr(args, "max_audio_reuse_workers", 0) or args.max_tts_workers))
        paid_workers = max(1, int(getattr(args, "max_paid_workers", 0) or args.max_tts_workers))
        upload_workers = max(1, int(getattr(args, "max_upload_workers", 0) or args.max_books_active))
        metadata_workers = max(1, int(getattr(args, "max_metadata_workers", 0) or args.max_books_active))
        self.stage_limits = {
            "inventory_queue": preflight_workers,
            "cover_queue": max(1, args.max_cover_workers),
            "manuscript_queue": preflight_workers,
            "rights_metadata_preflight_queue": preflight_workers,
            # The hook is reuse-first but may fall through to paid TTS. Keep the
            # effective queue limit bounded by the paid-worker cap.
            "tts_queue": max(1, min(audio_reuse_workers, max(1, args.max_tts_workers), paid_workers)),
            "asr_sync_queue": max(1, args.max_asr_workers),
            "qa_queue": max(1, args.max_books_active),
            "upload_queue": upload_workers,
            "metadata_publish_queue": metadata_workers,
            "browser_gate_queue": max(1, args.max_browser_workers),
        }
        self.stage_handlers: dict[str, Callable[[BookState], tuple[BookState, str | None]]] = {
            "inventory_queue": self.inventory_stage,
            "cover_queue": self.cover_stage,
            "manuscript_queue": self.manuscript_stage,
            "rights_metadata_preflight_queue": self.rights_metadata_preflight_stage,
            "tts_queue": self.tts_stage,
            "asr_sync_queue": self.asr_sync_stage,
            "qa_queue": self.qa_stage,
            "upload_queue": self.upload_stage,
            "metadata_publish_queue": self.metadata_publish_stage,
            "browser_gate_queue": self.browser_gate_stage,
        }

    def build_hook_plan(self) -> dict[str, dict[str, Any]]:
        plan: dict[str, dict[str, Any]] = {}
        for stage, (short_name, env_key) in HOOK_STAGES.items():
            env_command = os.environ.get(env_key, "").strip()
            if env_command:
                command = env_command
                source = "env"
            elif self.args.require_explicit_hooks:
                command = ""
                source = "missing_required_explicit"
            else:
                command = DEFAULT_HOOK_COMMANDS[stage]
                source = "internal_default"
            plan[stage] = {
                "stage": stage,
                "hook": short_name,
                "env_key": env_key,
                "source": source,
                "configured": bool(command),
                "command": command,
                "command_redacted": redact_command(command),
            }
        return plan

    def hook_command(self, stage: str) -> str:
        return str(self.hook_plan.get(stage, {}).get("command") or "")

    def hook_extra(self) -> dict[str, Any]:
        return {
            "manifest": str(Path(self.args.manifest).resolve() if self.args.manifest else DEFAULT_MANIFEST),
            "max_attempts": self.args.max_attempts,
            "dry_run": self.args.dry_run,
            "resume": self.args.resume,
            "fail_closed": self.args.fail_closed,
        }

    def event(self, event_type: str, *, state: BookState | None = None, stage: str = "", status: str = "", details: dict[str, Any] | None = None) -> None:
        payload = {
            "timestamp": iso_now(),
            "run_id": self.catalog_dir.name,
            "event": event_type,
            "slug": state.slug if state else "",
            "title": state.title if state else "",
            "language": state.language if state else "",
            "stage": stage,
            "status": status,
            "details": details or {},
        }
        append_jsonl(self.catalog_dir / "catalog_event_log.jsonl", payload)
        if state:
            append_jsonl(state.run_dir / "stage_event_log.jsonl", payload)
            with (state.run_dir / "book_release.log").open("a", encoding="utf-8") as handle:
                handle.write(f"{payload['timestamp']} {event_type} {stage} {status} {json.dumps(payload['details'], ensure_ascii=False)}\n")

    def validate_hooks(self) -> dict[str, Any]:
        self.event("hook_validation_start", details={"hook_count": len(self.hook_plan)})
        validation_dir = self.catalog_dir / "hook_validation"
        ensure_dir(validation_dir)
        results: dict[str, Any] = {}
        for stage, item in self.hook_plan.items():
            state = BookState(
                slug="__hook_validation__",
                title="Hook Validation",
                author="Earnalism",
                language="eng",
                order=0,
                catalog_dir=self.catalog_dir,
                run_dir=validation_dir / item["hook"],
                manifest_record={"_manifest_path": rel(Path(self.args.manifest).resolve() if self.args.manifest else DEFAULT_MANIFEST)},
                next_stage=None,
            )
            ensure_dir(state.run_dir)
            if not item["configured"]:
                result = {
                    "stage": item["hook"],
                    "status": "BLOCKED",
                    "ready_for_next_stage": False,
                    "blocker_category": item["hook"],
                    "blockers": [f"{item['env_key']} is required but not configured."],
                    "retryable": True,
                    "artifacts": {},
                    "metrics": {},
                    "updated_fields": {},
                }
            else:
                result = run_hook(
                    item["command"],
                    state,
                    stage,
                    {
                        "manifest": str(Path(self.args.manifest).resolve() if self.args.manifest else DEFAULT_MANIFEST),
                        "max_attempts": self.args.max_attempts,
                        "dry_run": True,
                        "resume": self.args.resume,
                        "fail_closed": self.args.fail_closed,
                    },
                )
            results[stage] = {
                **item,
                "command": None,
                "validation_status": result.get("status"),
                "validation_ready": bool(result.get("ready_for_next_stage") or result.get("status") == "PASS"),
                "last_result_path": result.get("result_path") or result.get("artifacts", {}).get("result_path", ""),
                "blockers": result.get("blockers") or ([result.get("reason")] if result.get("reason") else []),
            }
        payload = {
            "run_id": self.catalog_dir.name,
            "timestamp": iso_now(),
            "status": "PASS" if all(item["validation_ready"] for item in results.values()) else "BLOCKED",
            "hooks": results,
        }
        write_json(self.catalog_dir / "hook_validation.json", payload)
        self.hook_validation = payload
        self.event("hook_validation_pass" if payload["status"] == "PASS" else "hook_validation_fail", status=payload["status"])
        return payload

    def _catalog_dir(self) -> Path:
        explicit = str(getattr(self.args, "catalog_run_dir", "") or "").strip()
        if explicit:
            return Path(explicit).expanduser().resolve()
        if self.args.resume or getattr(self.args, "resume_from_latest", False) or getattr(self.args, "status_only", False) or getattr(self.args, "tail_status", False):
            latest = latest_catalog_dir()
            if latest:
                return latest
        return RELEASE_GATE_ROOT / f"catalog_{self.timestamp}"

    def load_or_build_states(self) -> None:
        state_path = self.catalog_dir / "catalog_state.json"
        if (self.args.resume or self.args.resume_from_latest) and state_path.exists():
            payload = read_json(state_path, {})
            for item in payload.get("books", []):
                state = BookState.from_json(item)
                if self.subset_slugs and state.slug not in self.subset_slugs:
                    continue
                if state.slug in self.exclude_slugs:
                    continue
                self.reset_dry_run_markers_for_production(state)
                if reconcile_newer_passed_stage_results(state):
                    state.save()
                if self.finalize_resumed_published_state(state):
                    state.save()
                self.states[state.slug] = state
                if state.next_stage:
                    self.stage_queues[state.next_stage].append(state)
                else:
                    retry_stage = retry_stage_for_state(state)
                    if retry_stage:
                        state.next_stage = retry_stage
                        self.stage_queues[retry_stage].append(state)
            self.add_missing_wave_states()
            return

        self.add_missing_wave_states()

    def add_missing_wave_states(self) -> None:
        records = [record for record in self.load_catalog_records() if str(record["slug"]) not in self.states]
        if self.args.priority == "ready-first" and self.args.order_by == "content-size":
            records = sorted(records, key=lambda record: (*self.record_wave_priority(record)[:1], self.content_rank_by_slug.get(str(record["slug"]), 999_999), str(record["slug"])))
        elif self.args.priority == "ready-first":
            records = sorted(records, key=self.record_wave_priority)
        elif self.args.order_by == "content-size":
            records = sorted(records, key=lambda record: (self.content_rank_by_slug.get(str(record["slug"]), 999_999), str(record["slug"])))
        if self.wave_size:
            remaining = max(0, self.wave_size - len(self.states))
            records = records[:remaining]
        order_base = max((state.order for state in self.states.values()), default=0)
        for order, record in enumerate(records, 1):
            slug = str(record["slug"])
            if slug in self.states:
                continue
            controlled_base = controlled_publication_base(slug)
            public_book = read_json(controlled_base / "public_book.json", {})
            reader = read_json(controlled_base / "reader_manifest.json", {})
            title = public_book.get("title") or reader.get("title") or record.get("title") or slug
            author = public_book.get("author") or reader.get("author") or record.get("author") or ""
            language = normalize_language(public_book.get("language") or reader.get("language") or record.get("language") or "")
            if not language:
                language = infer_language(title, author, json.dumps(public_book, ensure_ascii=False)[:3000])
            if language not in self.allowed_languages:
                continue
            run_dir = RELEASE_GATE_ROOT / f"{slug}_{self.timestamp}"
            state = BookState(
                slug=slug,
                title=str(title),
                author=str(author),
                language=language,
                order=order_base + order,
                catalog_dir=self.catalog_dir,
                run_dir=run_dir,
                manifest_record=record,
                next_stage="inventory_queue",
            )
            state.save()
            self.states[slug] = state
            self.stage_queues["inventory_queue"].append(state)

    def finalize_resumed_published_state(self, state: BookState) -> bool:
        if state.published:
            clear_passed_stage_blockers(state)
            qa = build_auto_qa(state, self.env_detected, self.command, phase="final")
            write_json(state.run_dir / "auto_premium_qa.json", qa)
            evidence = build_golive_evidence(state, qa, self.command)
            write_json(state.run_dir / "goliveevidence.json", evidence)
            return True
        required_final_stages = ["upload_queue", "metadata_publish_queue", "browser_gate_queue"]
        if any(str(state.stage_results.get(stage, {}).get("status") or "").upper() != "PASS" for stage in required_final_stages):
            return False
        clear_passed_stage_blockers(state)
        qa = build_auto_qa(state, self.env_detected, self.command, phase="final")
        write_json(state.run_dir / "auto_premium_qa.json", qa)
        if not qa["auto_approval_decision"]:
            evidence = build_golive_evidence(state, qa, self.command)
            write_json(state.run_dir / "goliveevidence.json", evidence)
            for reason in qa["blocker_list"]:
                state.add_blocker(qa_blocker_category(reason, state.language), reason)
            return False
        state.ready = True
        state.published = True
        state.next_stage = None
        state.terminal_status = "PUBLISHED"
        state.terminal_at = state.terminal_at or iso_now()
        evidence = build_golive_evidence(state, qa, self.command)
        write_json(state.run_dir / "goliveevidence.json", evidence)
        return True

    def reset_dry_run_markers_for_production(self, state: BookState) -> None:
        if self.args.dry_run:
            return
        removed: list[str] = []
        for stage, result in list(state.stage_results.items()):
            marker = json.dumps(result, ensure_ascii=False).lower()
            if "dry-run" in marker or "dry_run" in marker:
                removed.append(stage)
                del state.stage_results[stage]
        if not removed:
            return
        state.blockers = [
            blocker
            for blocker in state.blockers
            if "dry-run" not in blocker.get("reason", "").lower() and "dry_run" not in blocker.get("reason", "").lower()
        ]
        first_stage = sorted(removed, key=lambda stage: QUEUE_NAMES.index(stage) if stage in QUEUE_NAMES else 999)[0]
        state.ready = False
        state.next_stage = first_stage
        state.save()

    def record_wave_priority(self, record: dict[str, Any]) -> tuple[int, int, str]:
        slug = str(record["slug"])
        public_book, reader, source_evidence, _ = load_book_payloads(slug)
        chapters = load_rendered_chapters(slug)
        word_count = sum(len(word_tokens(chapter["text"])) for chapter in chapters)
        cover_ready = (
            cover_inventory(public_book, dry_run=True, slug=slug)["status"] == "PASS"
        )
        source_ready = bool(source_evidence) or bool(any_source_path(slug))
        reader_ready = bool(chapters) or bool(reader.get("chapters"))
        audio_assets = public_book.get("audiobook_assets") if isinstance(public_book.get("audiobook_assets"), dict) else {}
        existing_audio = bool(audio_assets.get("mp3") or public_book.get("audio_enabled") or public_book.get("audiobook_enabled"))
        if reader_ready and cover_ready and source_ready and word_count <= 15_000:
            bucket = 0
        elif existing_audio:
            bucket = 1
        elif reader_ready and cover_ready:
            bucket = 2
        elif reader_ready:
            bucket = 3
        elif word_count >= 80_000:
            bucket = 5
        else:
            bucket = 4
        if not source_ready:
            bucket += 10
        return (bucket, word_count or 999_999, slug)

    @property
    def allowed_languages(self) -> set[str]:
        values = [normalize_language(value) for value in re.split(r"[, ]+", self.args.languages or "") if value.strip()]
        return set(values or ["eng", "ben"])

    def load_catalog_records(self) -> list[dict[str, Any]]:
        subset = {normalize_slug(value) for value in (self.args.slugs or "").split(",") if normalize_slug(value)}
        controlled_slugs = {
            path.parent.name
            for publication_root in CONTROLLED_PUBLICATION_ROOTS
            for path in publication_root.glob("*/public_book.json")
        }
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        duplicates: list[dict[str, Any]] = []

        manifest_path = Path(self.args.manifest).expanduser().resolve() if self.args.manifest else DEFAULT_MANIFEST
        if manifest_path.exists():
            for row_index, raw in enumerate(iter_manifest_records(manifest_path), 1):
                slug = record_slug(raw)
                if not slug:
                    continue
                if slug not in controlled_slugs and normalize_slug(str(raw.get("id") or "")) in controlled_slugs:
                    slug = normalize_slug(str(raw.get("id")))
                if subset and slug not in subset:
                    continue
                if slug in self.exclude_slugs:
                    continue
                if not self.record_matches_include_status(slug, raw):
                    continue
                if slug in seen:
                    duplicates.append({"slug": slug, "manifest_row": row_index, "title": raw.get("title") or raw.get("name") or "", "reason": "duplicate_slug"})
                    continue
                seen.add(slug)
                item = dict(raw)
                item["slug"] = slug
                item["_manifest_path"] = rel(manifest_path)
                records.append(item)

        for slug in sorted(controlled_slugs):
            if subset and slug not in subset:
                continue
            if slug in self.exclude_slugs:
                continue
            if not self.record_matches_include_status(slug, {}):
                continue
            if slug in seen:
                continue
            seen.add(slug)
            records.append({"slug": slug, "_manifest_path": rel(controlled_publication_base(slug))})

        if subset:
            missing = sorted(subset - seen)
            for slug in missing:
                records.append({"slug": slug, "_missing_from_manifest": True})
        self.duplicate_manifest_rows = duplicates
        self.refresh_content_size_ranking(records)
        return records

    def record_matches_include_status(self, slug: str, record: dict[str, Any]) -> bool:
        if not self.include_statuses:
            return True
        public_book, reader, _, _ = load_book_payloads(slug)
        statuses = {
            str(public_book.get("publication_status") or "").lower(),
            str(public_book.get("status") or "").lower(),
            str(public_book.get("audiobook_release_gate") or "").lower(),
            str(record.get("status") or "").lower(),
            str(record.get("publication_status") or "").lower(),
        }
        if public_book.get("production_approved") is True:
            statuses.add("production_approved")
        if reader.get("chapters"):
            statuses.add("reader_ready")
        return bool(statuses & self.include_statuses)

    def refresh_content_size_ranking(self, records: list[dict[str, Any]]) -> None:
        rows: list[dict[str, Any]] = []
        for canonical_index, record in enumerate(records, 1):
            slug = str(record.get("slug") or "")
            if not slug:
                continue
            public_book, reader, source_evidence, _ = load_book_payloads(slug)
            title = public_book.get("title") or reader.get("title") or record.get("title") or slug
            author = public_book.get("author") or reader.get("author") or record.get("author") or ""
            language = normalize_language(public_book.get("language") or reader.get("language") or record.get("language") or "") or infer_language(str(title), str(author))
            word_count = content_word_count_for_slug(slug)
            rows.append(
                {
                    "canonical_index": canonical_index,
                    "slug": slug,
                    "title": title,
                    "author": author,
                    "language": language,
                    "word_count": word_count,
                    "content_size_rank": 0,
                }
            )
        ranked = sorted(rows, key=lambda item: (int(item["word_count"] or 999_999_999), item["canonical_index"], item["slug"]))
        for rank, item in enumerate(ranked, 1):
            item["content_size_rank"] = rank
        self.content_size_ranking = ranked
        self.content_rank_by_slug = {str(item["slug"]): int(item["content_size_rank"]) for item in ranked}

    def pid_path(self) -> Path:
        value = str(getattr(self.args, "write_pid_file", "") or "").strip()
        return Path(value).expanduser().resolve() if value else self.catalog_dir / "catalog_worker.pid"

    def heartbeat_path(self) -> Path:
        return self.catalog_dir / "catalog_worker_heartbeat.json"

    def daemon_log_path(self) -> Path:
        value = str(getattr(self.args, "daemon_log", "") or "").strip()
        return Path(value).expanduser().resolve() if value else self.catalog_dir / "catalog_worker.log"

    def worker_status(self) -> dict[str, Any]:
        heartbeat = read_json(self.heartbeat_path(), {})
        pid_payload = read_json(self.pid_path(), {})
        pid = heartbeat.get("pid") or pid_payload.get("pid")
        running = pid_is_running(pid)
        status = str(heartbeat.get("status") or ("RUNNING" if running else "NOT_RUNNING"))
        if status in {"RUNNING", "STARTING"} and not running:
            status = "STALE"
        if not self.stop_guard_triggered and heartbeat.get("stop_guard_triggered"):
            self.stop_guard_triggered = bool(heartbeat.get("stop_guard_triggered"))
            self.stop_guard_counter_used = str(heartbeat.get("stop_guard_counter_used") or "")
            self.stop_guard_counter_value = int(heartbeat.get("stop_guard_counter_value") or 0)
            self.stop_guard_limit = int(heartbeat.get("stop_guard_limit") or 0)
        return {
            "status": status,
            "pid": pid,
            "pid_running": running,
            "pid_file": rel(self.pid_path()),
            "heartbeat_path": rel(self.heartbeat_path()),
            "daemon_log": rel(self.daemon_log_path()),
            "updated_at": heartbeat.get("updated_at", ""),
            "stop_reason": heartbeat.get("stop_reason", ""),
        }

    def write_pid_file(self) -> None:
        write_json(
            self.pid_path(),
            {
                "pid": os.getpid(),
                "catalog_dir": rel(self.catalog_dir),
                "command": self.command,
                "created_at": iso_now(),
            },
        )

    def write_heartbeat(self, status: str = "RUNNING", active: dict[Future[tuple[BookState, str | None]], str] | None = None) -> None:
        now = time.monotonic()
        interval = max(5, int(getattr(self.args, "heartbeat_seconds", 60) or 60))
        if status == "RUNNING" and now - self.last_heartbeat_epoch < interval:
            return
        self.last_heartbeat_epoch = now
        active_by_stage = Counter(active.values()) if active else Counter()
        queued_by_stage = {stage: len(queue) for stage, queue in self.stage_queues.items()}
        counters = catalog_counter_snapshot(self.states.values())
        payload = {
            "status": status,
            "pid": os.getpid(),
            "catalog_dir": rel(self.catalog_dir),
            "updated_at": iso_now(),
            "command": self.command,
            "active_by_stage": dict(active_by_stage),
            "active_lane_counts": lane_counts_from_stage_counts(active_by_stage),
            "queued_by_stage": queued_by_stage,
            "queued_by_lane": lane_counts_from_stage_counts(queued_by_stage),
            "completed_by_lane": completed_by_lane(self.states.values()),
            "blocked_by_lane": blocked_by_lane(self.states.values()),
            "paid_operations_running": active_by_stage.get("tts_queue", 0),
            "paid_operations_queued": len(self.stage_queues.get("tts_queue", [])),
            "total_states": len(self.states),
            **counters,
            "published_this_run": sum(1 for state in self.states.values() if state.published),
            "blocked": sum(1 for state in self.states.values() if state.blockers),
            "stop_reason": self.stop_reason,
            "stop_guard_triggered": self.stop_guard_triggered,
            "stop_guard_reason": self.stop_reason if self.stop_guard_triggered else "",
            "stop_guard_counter_used": self.stop_guard_counter_used,
            "stop_guard_counter_value": self.stop_guard_counter_value,
            "stop_guard_limit": self.stop_guard_limit,
            "dashboard_path": rel(self.catalog_dir / "catalog_release_dashboard.json"),
        }
        write_json(self.heartbeat_path(), payload)

    def print_status_only(self) -> int:
        dashboard = read_json(self.catalog_dir / "catalog_release_dashboard.json", {})
        summary = dashboard.get("summary") if isinstance(dashboard.get("summary"), dict) else self.dashboard_summary()
        worker = self.worker_status()
        summary = {**summary, "background_worker_status": worker["status"], "background_worker_pid": worker["pid"], "background_worker_pid_running": worker["pid_running"], "pid_file": worker["pid_file"], "heartbeat_path": worker["heartbeat_path"], "daemon_log": worker["daemon_log"]}
        if worker["pid_running"]:
            print("CATALOG BACKGROUND RUNNING: release factory is processing eligible books in resumable background mode.")
        elif summary.get("books_published_this_run", 0) > 0:
            print("CATALOG PARTIAL GO LIVE: some books were published; blockers remain.")
        elif summary.get("books_blocked", 0) > 0:
            print("CATALOG NOT GO LIVE READY: blockers remain.")
        elif summary.get("hook_validation_status") == "PASS":
            print("CATALOG HOOKS READY: hooks are wired and canary may run.")
        else:
            print("CATALOG NOT GO LIVE READY: blockers remain.")
        print_dashboard_table(summary, self.catalog_dir)
        return 0 if worker["pid_running"] or summary.get("hook_validation_status") == "PASS" else 2

    def _argv_without_background(self) -> list[str]:
        output: list[str] = []
        skip_next = False
        value_flags = {"--catalog-run-dir", "--write-pid-file", "--daemon-log"}
        for index, value in enumerate(sys.argv[1:]):
            if skip_next:
                skip_next = False
                continue
            if value == "--background":
                continue
            if value in value_flags:
                skip_next = True
                continue
            if any(value.startswith(flag + "=") for flag in value_flags):
                continue
            output.append(value)
        output.extend(["--catalog-run-dir", str(self.catalog_dir)])
        output.extend(["--write-pid-file", str(self.pid_path())])
        output.extend(["--daemon-log", str(self.daemon_log_path())])
        return output

    def start_background(self) -> int:
        ensure_dir(self.catalog_dir)
        lock_payload = read_json(CATALOG_LOCK_PATH, {})
        if CATALOG_LOCK_PATH.exists() and pid_is_running(lock_payload.get("pid")):
            self.write_heartbeat("BLOCKED_ACTIVE_WORKER")
            print("CATALOG NOT GO LIVE READY: blockers remain.")
            print_dashboard_table(self.dashboard_summary(), self.catalog_dir)
            return 2
        log_path = self.daemon_log_path()
        ensure_dir(log_path.parent)
        child_args = [sys.executable, str(Path(__file__).resolve()), *self._argv_without_background()]
        with log_path.open("ab") as log_handle:
            process = subprocess.Popen(
                child_args,
                cwd=ROOT,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        write_json(
            self.pid_path(),
            {
                "pid": process.pid,
                "catalog_dir": rel(self.catalog_dir),
                "command": " ".join(shlex.quote(part) for part in child_args),
                "created_at": iso_now(),
            },
        )
        write_json(
            self.heartbeat_path(),
            {
                "status": "STARTING",
                "pid": process.pid,
                "catalog_dir": rel(self.catalog_dir),
                "updated_at": iso_now(),
                "command": " ".join(shlex.quote(part) for part in child_args),
                "daemon_log": rel(log_path),
                "dashboard_path": rel(self.catalog_dir / "catalog_release_dashboard.json"),
            },
        )
        self.write_dashboards()
        print("CATALOG BACKGROUND RUNNING: release factory is processing eligible books in resumable background mode.")
        print_dashboard_table(self.dashboard_summary(), self.catalog_dir)
        return 0

    def run(self) -> int:
        if self.args.status_only or self.args.tail_status:
            return self.print_status_only()
        if self.args.background:
            return self.start_background()
        self.event("catalog_start", status="STARTING", details={"command": self.command})
        if self.args.print_hook_plan:
            print(json.dumps({"hook_plan": {key: {k: v for k, v in value.items() if k != "command"} for key, value in self.hook_plan.items()}}, ensure_ascii=False, indent=2))
        if self.args.validate_hooks:
            validation = self.validate_hooks()
            if not self.states and (self.args.resume or self.args.resume_from_latest) and (self.catalog_dir / "catalog_state.json").exists():
                self.load_or_build_states()
            self.write_dashboards()
            if validation.get("status") != "PASS":
                print("CATALOG NOT GO LIVE READY: blockers remain.")
                print_dashboard_table(self.dashboard_summary(), self.catalog_dir)
                return 2
            print("CATALOG HOOKS READY: factory hooks are wired and canary may run.")
            print_dashboard_table(self.dashboard_summary(), self.catalog_dir)
            return 0
        self.load_or_build_states()
        self.initial_published_slugs = {state.slug for state in self.states.values() if state.published}
        self.write_catalog_state()
        self.write_pid_file()
        self.write_heartbeat("RUNNING")
        with exclusive_lock(
            CATALOG_LOCK_PATH,
            {"pid": os.getpid(), "catalog_dir": rel(self.catalog_dir), "created_at": iso_now()},
        ):
            self.scheduler()
        self.write_heartbeat("COMPLETE" if not self.stop_reason else "STOPPED")
        self.write_dashboards()
        status = self.catalog_status()
        self.event("catalog_end", status=status, details=self.dashboard_summary())
        print(status)
        print_dashboard_table(self.dashboard_summary(), self.catalog_dir)
        return 0 if status.startswith("CATALOG GO LIVE READY") else 2

    def scheduler(self) -> None:
        executors = {
            stage: ThreadPoolExecutor(max_workers=limit, thread_name_prefix=stage)
            for stage, limit in self.stage_limits.items()
        }
        active: dict[Future[tuple[BookState, str | None]], str] = {}
        try:
            while True:
                self.write_heartbeat("RUNNING", active)
                if self.should_stop_scheduling():
                    for queue in self.stage_queues.values():
                        queue.clear()
                submitted = False
                active_by_stage = Counter(active.values())
                for stage, queue in self.stage_queues.items():
                    while queue and active_by_stage[stage] < self.stage_limits[stage]:
                        state = queue.popleft()
                        future = executors[stage].submit(self.run_stage, stage, state)
                        active[future] = stage
                        active_by_stage[stage] += 1
                        submitted = True
                if not active:
                    if not any(self.stage_queues.values()):
                        break
                    if not submitted:
                        time.sleep(0.05)
                    continue
                done, _ = wait(active.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    stage = active.pop(future)
                    try:
                        state, next_stage = future.result()
                    except Exception as exc:  # noqa: BLE001
                        if self.args.fail_closed:
                            raise
                        continue
                    self.states[state.slug] = state
                    if next_stage:
                        state.next_stage = next_stage
                        self.enqueue_stage(next_stage, state)
                    else:
                        state.next_stage = None
                    self.update_terminal_status(state)
                    state.save()
                self.write_catalog_state()
                self.write_heartbeat("RUNNING", active)
        finally:
            for executor in executors.values():
                executor.shutdown(wait=True, cancel_futures=False)

    def should_stop_scheduling(self) -> bool:
        if self.stop_reason:
            return True
        if self.deadline_epoch and time.monotonic() >= self.deadline_epoch:
            self.set_stop_guard(
                reason=f"max-run-minutes reached: {self.args.max_run_minutes}",
                counter_used="elapsed_minutes",
                counter_value=int(float(self.args.max_run_minutes or 0)),
                limit=int(float(self.args.max_run_minutes or 0)),
            )
            return True
        if self.stop_after_published:
            published_now = sum(1 for state in self.states.values() if state.published and state.slug not in self.initial_published_slugs)
            if published_now >= self.stop_after_published:
                self.set_stop_guard(
                    reason=f"stop-after-published reached: {self.stop_after_published}",
                    counter_used="published_count",
                    counter_value=published_now,
                    limit=self.stop_after_published,
                )
                return True
        if self.stop_after_terminal_books:
            terminal_now = catalog_counter_snapshot(self.states.values())["terminal_book_count"]
            if terminal_now >= self.stop_after_terminal_books:
                self.set_stop_guard(
                    reason=f"stop-after-terminal-books reached: {self.stop_after_terminal_books}",
                    counter_used="terminal_book_count",
                    counter_value=terminal_now,
                    limit=self.stop_after_terminal_books,
                )
                return True
        if self.stop_after_attempted:
            attempted_now = stop_after_attempted_counter_value(self.states.values())
            if attempted_now >= self.stop_after_attempted:
                self.set_stop_guard(
                    reason=f"stop-after-attempted reached: {self.stop_after_attempted}",
                    counter_used="book_attempted_or_terminal_count",
                    counter_value=attempted_now,
                    limit=self.stop_after_attempted,
                )
                return True
        return False

    def set_stop_guard(self, *, reason: str, counter_used: str, counter_value: int, limit: int) -> None:
        self.stop_reason = reason
        self.stop_guard_triggered = True
        self.stop_guard_counter_used = counter_used
        self.stop_guard_counter_value = counter_value
        self.stop_guard_limit = limit

    def enqueue_stage(self, stage: str, state: BookState) -> None:
        queue = self.stage_queues[stage]
        queue.append(state)
        if stage != "inventory_queue":
            ordered = sorted(queue, key=lambda item: (scheduling_priority(item), item.order))
            queue.clear()
            queue.extend(ordered)

    def run_stage(self, stage: str, state: BookState) -> tuple[BookState, str | None]:
        lock_path = RELEASE_GATE_ROOT / f".{state.slug}.release_factory.lock"
        with exclusive_lock(lock_path, {"pid": os.getpid(), "stage": stage, "slug": state.slug, "created_at": iso_now()}):
            if self.args.resume and stage_is_complete(state, stage):
                return state, next_stage_after(stage, state)
            state.mark_stage_started(stage)
            self.event(stage_event_name(stage, "start"), state=state, stage=stage, status="START")
            handler = self.stage_handlers[stage]
            state, next_stage = handler(state)
            result_status = str(state.stage_results.get(stage, {}).get("status") or "")
            self.event(stage_event_name(stage, "pass" if result_status == "PASS" else "fail"), state=state, stage=stage, status=result_status)
            for blocker in state.blockers:
                self.event("blocker_detected", state=state, stage=stage, status=result_status, details=blocker)
            if state.stage_results.get(stage, {}).get("status") == "PASS":
                clear_stage_blockers(state, stage)
            state.save()
            return state, next_stage

    def update_terminal_status(self, state: BookState) -> None:
        terminal = inferred_terminal_status(state)
        if terminal:
            state.terminal_status = terminal
            if not state.terminal_at:
                state.terminal_at = iso_now()
        else:
            state.terminal_status = ""
            state.terminal_at = ""

    def inventory_stage(self, state: BookState) -> tuple[BookState, str | None]:
        public_book, reader, source_evidence, release_gate = load_book_payloads(state.slug)
        chapter_paths = controlled_chapter_paths(state.slug)
        cover_status = cover_inventory(
            public_book, dry_run=self.args.dry_run, slug=state.slug
        )
        rights_report = rights_metadata_report(state)
        reader_ready = bool(reader.get("chapters")) and all(
            str(item.get("processing_status", "ready")).lower() in {"ready", "complete", "completed"}
            for item in reader.get("chapters", [])
            if isinstance(item, dict)
        )
        audio_assets = public_book.get("audiobook_assets") if isinstance(public_book.get("audiobook_assets"), dict) else {}
        existing_audio = bool(audio_assets.get("mp3") or public_book.get("audio_enabled") or public_book.get("audiobook_enabled"))
        existing_sidecars = sidecar_inventory(state.slug)
        previous_evidence = latest_book_evidence(state.slug)
        production_endpoint_state = "NOT_QUERIED_DRY_RUN" if self.args.dry_run else production_endpoint_probe(state.slug)
        classifications = []
        if cover_status["status"] != "PASS":
            classifications.append("COVER_REPAIR_REQUIRED")
        if not reader_ready or not chapter_paths:
            classifications.append("MANUSCRIPT_REPAIR_REQUIRED")
        if not source_evidence and not any_source_path(state.slug):
            classifications.append("BLOCKED_NEEDS_SOURCE")
        if not rights_report.get("production_metadata_ready"):
            classifications.append("RIGHTS_METADATA_REQUIRED")
        if not existing_audio:
            classifications.append("AUDIO_REQUIRED")
        if not existing_sidecars["has_release_candidate"]:
            classifications.append("SYNC_REQUIRED")
        if existing_audio and release_gate.get("upload_status") != "UPLOADED":
            classifications.append("UPLOAD_REQUIRED")
        if public_book.get("production_approved") is not True or public_book.get("audiobook_release_gate") != "APPROVED":
            classifications.append("METADATA_REQUIRED")
        if production_endpoint_state != "200":
            classifications.append("BROWSER_REQUIRED")
        if not classifications:
            classifications.append("READY_REUSE_CANDIDATE")
        state.classifications = sorted(set(classifications))
        result = {
            "status": "PASS",
            "metadata": {
                "title": public_book.get("title") or state.title,
                "author": public_book.get("author") or state.author,
                "language": state.language,
                "publication_status": public_book.get("publication_status"),
                "reader_ready": reader_ready,
                "chapter_file_count": len(chapter_paths),
                "source_evidence_present": bool(source_evidence),
                "rights_metadata_status": rights_report.get("status"),
                "rights_metadata_ready": rights_report.get("production_metadata_ready"),
                "rights_metadata_missing_fields": rights_report.get("missing_fields", []),
                "existing_audio": existing_audio,
                "existing_sidecars": existing_sidecars,
                "production_endpoint_state": production_endpoint_state,
                "previous_evidence_path": rel(previous_evidence) if previous_evidence else "",
            },
            "cover_status": cover_status,
            "rights_metadata": rights_report,
            "classifications": state.classifications,
        }
        state.stage_results["inventory_queue"] = result
        state.inventory_seen = True
        write_json(state.run_dir / "inventory.json", result)
        return state, "cover_queue"

    def cover_stage(self, state: BookState) -> tuple[BookState, str | None]:
        public_book, _, _, _ = load_book_payloads(state.slug)
        current = cover_inventory(
            public_book, dry_run=self.args.dry_run, slug=state.slug
        )
        brief = cover_brief_from_manuscript(state)
        write_text(state.run_dir / "cover_content_brief.md", brief)
        if current["status"] == "PASS":
            result = {"status": "PASS", "cover_status": current, "cover_content_brief": rel(state.run_dir / "cover_content_brief.md")}
        elif self.args.dry_run:
            result = {"status": "BLOCKED", "cover_status": current, "cover_content_brief": rel(state.run_dir / "cover_content_brief.md"), "reason": "dry-run: cover repair/upload not executed"}
            state.add_blocker("covers", result["reason"])
        else:
            hook = self.hook_command("cover_queue")
            result = run_hook(hook, state, "cover_queue", self.hook_extra())
            if result.get("status") != "PASS":
                category = result.get("blocker_category") or "covers"
                for reason in hook_blocker_reasons(result, "cover hook failed"):
                    state.add_blocker(category, reason)
        state.stage_results["cover_queue"] = result
        return state, "manuscript_queue" if result["status"] == "PASS" else None

    def manuscript_stage(self, state: BookState) -> tuple[BookState, str | None]:
        chapters = load_rendered_chapters(state.slug)
        clean_text = "\n\n".join(chapter["text"].strip() for chapter in chapters if chapter["text"].strip()).strip() + "\n"
        clean_text = sanitize_manuscript_text(clean_text)
        clean_path = state.run_dir / "clean_manuscript.txt"
        write_text(clean_path, clean_text)
        integrity = content_integrity_report(state, chapters, clean_text)
        write_json(state.run_dir / "content_integrity_report.json", integrity)
        result = {
            "status": "PASS" if integrity["status"] == "PASS" else "CONTENT_INTEGRITY_BLOCKED",
            "clean_manuscript_path": rel(clean_path),
            "clean_text_hash": sha256_text(clean_text),
            "word_count": len(word_tokens(clean_text)),
            "content_integrity_report": rel(state.run_dir / "content_integrity_report.json"),
            "content_integrity_status": integrity["status"],
            "blocker_reasons": integrity["blocker_reasons"],
        }
        if result["status"] != "PASS":
            for reason in integrity["blocker_reasons"]:
                state.add_blocker("manuscript", reason)
        state.stage_results["manuscript_queue"] = result
        return state, "rights_metadata_preflight_queue" if result["status"] == "PASS" else None

    def rights_metadata_preflight_stage(self, state: BookState) -> tuple[BookState, str | None]:
        report = rights_metadata_report(state)
        report_path = state.run_dir / "rights_metadata_report.json"
        write_json(report_path, report)
        result = {
            "status": "PASS" if report["production_metadata_ready"] else "BLOCKED",
            "rights_metadata_report": rel(report_path),
            "rights_metadata_status": report["status"],
            "production_metadata_ready": report["production_metadata_ready"],
            "missing_fields": report["missing_fields"],
            "blocker_reasons": report["blocker_reasons"],
            "updated_fields": {
                "rights_metadata_report_path": rel(report_path),
                "rights_metadata_status": report["status"],
                "production_metadata_ready": report["production_metadata_ready"],
            },
        }
        if result["status"] != "PASS":
            for reason in report["blocker_reasons"]:
                category = "metadata_rights" if "rights" in reason.lower() or "source" in reason.lower() else "rights_metadata"
                state.add_blocker(category, reason)
        state.stage_results["rights_metadata_preflight_queue"] = result
        return state, "tts_queue" if result["status"] == "PASS" else None

    def tts_stage(self, state: BookState) -> tuple[BookState, str | None]:
        reuse = reusable_audio_evidence(state)
        if reuse["status"] == "PASS":
            result = reuse
        elif self.args.dry_run:
            result = {
                "status": "BLOCKED",
                "reason": "dry-run: OpenAI TTS not executed; no reusable approved audio evidence found",
                "audition_role": "selector_only",
                "fallback_tts_used": False,
                "bengali_audition_voices": ["marin", "cedar", "coral", "alloy", "sage", "shimmer", "nova", "verse"],
                "english_genre_profiles": [
                    "classic_literary_narrator",
                    "mystery_suspense_narrator",
                    "children_adventure_narrator",
                    "nonfiction_business_narrator",
                ],
            }
            state.add_blocker("tts", result["reason"])
        else:
            hook = self.hook_command("tts_queue")
            result = run_hook(hook, state, "tts_queue", self.hook_extra())
            if result.get("status") != "PASS":
                category = result.get("blocker_category") or "tts"
                for reason in hook_blocker_reasons(result, "TTS hook failed"):
                    state.add_blocker(category, reason)
        state.stage_results["tts_queue"] = result
        return state, "asr_sync_queue" if result["status"] == "PASS" else None

    def asr_sync_stage(self, state: BookState) -> tuple[BookState, str | None]:
        clear_stage_blockers(state, "asr_sync_queue")
        reuse = reusable_sync_evidence(state)
        if reuse["status"] == "PASS":
            result = reuse
        elif self.args.dry_run:
            result = {"status": "BLOCKED", "reason": "dry-run: ASR/forced alignment not executed and no real sync evidence was found", "auto_estimated_sync": None}
            state.add_blocker("sync", result["reason"])
        else:
            hook = self.hook_command("asr_sync_queue")
            result = run_hook(hook, state, "asr_sync_queue", self.hook_extra())
            if result.get("status") != "PASS":
                category = result.get("blocker_category") or "sync"
                for reason in hook_blocker_reasons(result, "ASR/sync hook failed"):
                    state.add_blocker(category, reason)
        state.stage_results["asr_sync_queue"] = result
        return state, "qa_queue" if result["status"] == "PASS" else None

    def qa_stage(self, state: BookState) -> tuple[BookState, str | None]:
        clear_stage_blockers(state, "qa_queue")
        clear_passed_stage_blockers(state)
        qa = build_auto_qa(state, self.env_detected, self.command, phase="pre_upload")
        write_json(state.run_dir / "auto_premium_qa.json", qa)
        evidence = build_golive_evidence(state, qa, self.command)
        write_json(state.run_dir / "goliveevidence.json", evidence)
        result = {"status": "PASS" if qa["auto_approval_decision"] else "BLOCKED", "auto_premium_qa": rel(state.run_dir / "auto_premium_qa.json"), "goliveevidence": rel(state.run_dir / "goliveevidence.json")}
        if result["status"] != "PASS":
            for reason in qa["blocker_list"]:
                state.add_blocker(qa_blocker_category(reason, state.language), reason)
        state.ready = False
        state.stage_results["qa_queue"] = result
        return state, "upload_queue" if result["status"] == "PASS" else None

    def upload_stage(self, state: BookState) -> tuple[BookState, str | None]:
        if self.args.dry_run:
            result = {"status": "READY_BUT_NOT_UPLOADED_DRY_RUN", "reason": "dry-run: upload/checksum verification not executed"}
            state.add_blocker("upload/checksum", result["reason"])
            state.stage_results["upload_queue"] = result
            return state, None
        hook = self.hook_command("upload_queue")
        result = run_hook(hook, state, "upload_queue", self.hook_extra())
        if result.get("status") != "PASS":
            category = result.get("blocker_category") or "upload/checksum"
            for reason in hook_blocker_reasons(result, "upload hook failed"):
                state.add_blocker(category, reason)
        state.stage_results["upload_queue"] = result
        return state, "metadata_publish_queue" if result.get("status") == "PASS" else None

    def metadata_publish_stage(self, state: BookState) -> tuple[BookState, str | None]:
        if not self.args.publish_approved:
            result = {"status": "READY_NOT_PUBLISHED", "reason": "--publish-approved was not supplied"}
            state.add_blocker("metadata", result["reason"])
            state.stage_results["metadata_publish_queue"] = result
            return state, None
        order_blocker = self.release_order_blocker(state)
        if order_blocker:
            result = {
                "status": "BLOCKED",
                "reason": order_blocker,
                "blocker_category": "release_order",
                "retryable": True,
            }
            state.add_blocker("release_order", order_blocker)
            state.stage_results["metadata_publish_queue"] = result
            return state, None
        if self.args.dry_run:
            result = {"status": "READY_NOT_PUBLISHED_DRY_RUN", "reason": "dry-run: metadata approval/publish not executed"}
            state.add_blocker("metadata", result["reason"])
            state.stage_results["metadata_publish_queue"] = result
            return state, None
        hook = self.hook_command("metadata_publish_queue")
        result = run_hook(hook, state, "metadata_publish_queue", self.hook_extra())
        if result.get("status") != "PASS":
            category = result.get("blocker_category") or "metadata"
            for reason in hook_blocker_reasons(result, "metadata hook failed"):
                state.add_blocker(category, reason)
        state.stage_results["metadata_publish_queue"] = result
        return state, "browser_gate_queue" if result.get("status") == "PASS" else None

    def release_order_blocker(self, state: BookState) -> str:
        if not self.args.enforce_release_order:
            return ""
        if self.args.release_order != "ascending-content-size":
            return ""
        rank = self.content_rank_by_slug.get(state.slug)
        if not rank:
            return ""
        allowed_terminal = {"PUBLISHED", "BLOCKED", "TERMINAL_BLOCKED_WITH_EVIDENCE", "FAILED", "SKIPPED_TERMINAL"}
        for other in self.states.values():
            other_rank = self.content_rank_by_slug.get(other.slug)
            if not other_rank or other_rank >= rank:
                continue
            other_terminal = state_terminal_status(other)
            if other.published:
                continue
            if self.args.allow_blocked_order_skip and other_terminal in allowed_terminal and other.blockers:
                continue
            if other_terminal in {"BLOCKED", "TERMINAL_BLOCKED_WITH_EVIDENCE", "FAILED", "SKIPPED_TERMINAL"} and self.args.allow_blocked_order_skip:
                continue
            return (
                f"Release order barrier: rank {rank} `{state.slug}` cannot publish before "
                f"rank {other_rank} `{other.slug}` reaches published or terminal-blocked evidence."
            )
        return ""

    def browser_gate_stage(self, state: BookState) -> tuple[BookState, str | None]:
        if self.args.dry_run:
            result = {"status": "NOT_RUN_DRY_RUN", "reason": "dry-run: browser gates not executed"}
            state.add_blocker("browser", result["reason"])
        else:
            hook = self.hook_command("browser_gate_queue")
            if hook:
                result = run_hook(hook, state, "browser_gate_queue", self.hook_extra())
            else:
                result = browser_probe(state)
            if result.get("status") != "PASS":
                category = result.get("blocker_category") or "browser"
                for reason in hook_blocker_reasons(result, "browser gate failed"):
                    state.add_blocker(category, reason)
        state.stage_results["browser_gate_queue"] = result
        clear_passed_stage_blockers(state)
        qa = build_auto_qa(state, self.env_detected, self.command, phase="final")
        write_json(state.run_dir / "auto_premium_qa.json", qa)
        if result.get("status") == "PASS" and qa["auto_approval_decision"]:
            state.ready = True
            state.published = True
        else:
            state.ready = False
            for reason in qa["blocker_list"]:
                state.add_blocker(qa_blocker_category(reason, state.language), reason)
        evidence = build_golive_evidence(state, qa, self.command)
        write_json(state.run_dir / "goliveevidence.json", evidence)
        return state, None

    def write_catalog_state(self) -> None:
        counters = catalog_counter_snapshot(self.states.values())
        write_json(
            self.catalog_dir / "catalog_state.json",
            {
                "run_id": self.catalog_dir.name,
                "started_at": self.started_at,
                "updated_at": iso_now(),
                "command": self.command,
                "environment_keys_detected": self.env_detected,
                "hook_plan": {key: {k: v for k, v in value.items() if k != "command"} for key, value in self.hook_plan.items()},
                "hook_validation": self.hook_validation,
                "counters": counters,
                "stop_guard": {
                    "triggered": self.stop_guard_triggered,
                    "reason": self.stop_reason if self.stop_guard_triggered else "",
                    "counter_used": self.stop_guard_counter_used,
                    "counter_value": self.stop_guard_counter_value,
                    "limit": self.stop_guard_limit,
                },
                "books": [state.to_json() for state in sorted(self.states.values(), key=lambda item: item.order)],
            },
        )

    def write_dashboards(self) -> None:
        self.write_catalog_state()
        rows = [dashboard_row(state) for state in sorted(self.states.values(), key=lambda item: item.order)]
        self.write_catalog_truth_reports()
        self.write_cost_time_forecast()
        write_json(self.catalog_dir / "catalog_release_dashboard.json", {"summary": self.dashboard_summary(), "books": rows})
        write_csv(self.catalog_dir / "catalog_release_dashboard.csv", rows)
        write_json(self.catalog_dir / "catalog_inventory.json", {"books": [inventory_row(state) for state in sorted(self.states.values(), key=lambda item: item.order)]})
        write_csv(self.catalog_dir / "catalog_inventory.csv", [inventory_row(state) for state in sorted(self.states.values(), key=lambda item: item.order)])
        write_text(self.catalog_dir / "catalog_release_dashboard.md", dashboard_markdown(self.dashboard_summary(), rows))

    def write_catalog_truth_reports(self) -> None:
        if not self.content_size_ranking:
            self.refresh_content_size_ranking(self.load_catalog_records())
        write_json(self.catalog_dir / "catalog_unique_titles.json", {"unique_title_count": len(self.content_size_ranking), "books": self.content_size_ranking})
        write_csv(self.catalog_dir / "catalog_unique_titles.csv", self.content_size_ranking)
        duplicate_payload = {"duplicate_count": len(self.duplicate_manifest_rows), "duplicates": self.duplicate_manifest_rows}
        write_json(self.catalog_dir / "catalog_duplicate_titles.json", duplicate_payload)
        write_csv(self.catalog_dir / "catalog_duplicate_titles.csv", self.duplicate_manifest_rows)
        write_json(self.catalog_dir / "catalog_content_size_ranking.json", {"books": self.content_size_ranking})
        write_csv(self.catalog_dir / "catalog_content_size_ranking.csv", self.content_size_ranking)

    def write_cost_time_forecast(self) -> None:
        rows = []
        total_estimated_cost = 0.0
        for state in sorted(self.states.values(), key=lambda item: self.content_rank_by_slug.get(item.slug, item.order)):
            manuscript = state.stage_results.get("manuscript_queue", {})
            word_count = int(manuscript.get("word_count") or content_word_count_for_slug(state.slug) or 0)
            estimated_chars = max(0, word_count * 6)
            estimated_tts_cost = round((estimated_chars / 1000.0) * float(os.environ.get("EARNALISM_TTS_ESTIMATED_USD_PER_1K_CHARS", "0.015")), 4)
            if state.stage_results.get("tts_queue", {}).get("status") == "PASS":
                estimated_tts_cost = 0.0
            total_estimated_cost += estimated_tts_cost
            rows.append(
                {
                    "slug": state.slug,
                    "title": state.title,
                    "language": state.language,
                    "content_size_rank": self.content_rank_by_slug.get(state.slug, ""),
                    "word_count": word_count,
                    "estimated_tts_cost_usd": estimated_tts_cost,
                    "reuse_bias": "reuse_existing_artifacts_first",
                    "terminal_status": state_terminal_status(state),
                    "next_stage": state.next_stage or "",
                }
            )
        write_json(
            self.catalog_dir / "catalog_cost_time_forecast.json",
            {
                "generated_at": iso_now(),
                "paid_tts_approval_detected": os.environ.get("EARNALISM_APPROVE_PAID_OPENAI_TTS", "").lower() in {"1", "true", "yes"},
                "tts_budget_limit": os.environ.get("EARNALISM_TTS_MAX_ESTIMATED_USD", ""),
                "estimated_remaining_tts_cost_usd": round(total_estimated_cost, 4),
                "books": rows,
            },
        )

    def dashboard_summary(self) -> dict[str, Any]:
        states = list(self.states.values())
        counters = catalog_counter_snapshot(states)
        current_wave_published_slugs = {state.slug for state in states if state.published}
        verified_published_slugs = verified_published_slugs_from_evidence()
        cumulative_published_slugs = sorted(verified_published_slugs | current_wave_published_slugs)
        language_counts = Counter(state.language for state in states)
        blocker_counts: Counter[str] = Counter()
        rights_metadata_missing_slugs: set[str] = set()
        rights_evidence_incomplete_slugs: set[str] = set()
        metadata_api_rejection_slugs: set[str] = set()
        production_db_schema_mismatch_slugs: set[str] = set()
        for state in states:
            if "RIGHTS_METADATA_REQUIRED" in state.classifications:
                rights_metadata_missing_slugs.add(state.slug)
            for blocker in state.blockers:
                blocker_counts[blocker["category"]] += 1
                reason = str(blocker.get("reason") or "").lower()
                category = str(blocker.get("category") or "")
                if category in {"metadata_rights", "rights_metadata"}:
                    rights_metadata_missing_slugs.add(state.slug)
                    if any(token in reason for token in ("evidence", "public-domain", "public domain", "source", "license")):
                        rights_evidence_incomplete_slugs.add(state.slug)
                if category == "metadata_api":
                    metadata_api_rejection_slugs.add(state.slug)
                if any(token in reason for token in ("schema", "validation", "field required", "bookin")):
                    production_db_schema_mismatch_slugs.add(state.slug)
        audio_durations = []
        audio_scores = []
        wpms = []
        audio_url_404_count = 0
        local_audio_reused_count = 0
        audio_regenerated_count = 0
        tts_paid_approval_required_count = 0
        tts_estimated_costs: list[float] = []
        tts_actual_costs: list[float] = []
        for state in states:
            qa_path = state.run_dir / "auto_premium_qa.json"
            qa = read_json(qa_path, {})
            scores = qa.get("scores") if isinstance(qa.get("scores"), dict) else {}
            if scores.get("overall_premium_score") is not None:
                audio_scores.append(float(scores.get("overall_premium_score") or 0))
            evidence = read_json(state.run_dir / "goliveevidence.json", {})
            if evidence.get("audio_duration_seconds"):
                audio_durations.append(float(evidence["audio_duration_seconds"]))
            if evidence.get("wpm"):
                wpms.append(float(evidence["wpm"]))
            tts_result = state.stage_results.get("tts_queue", {})
            tts_metrics = tts_result.get("metrics") if isinstance(tts_result.get("metrics"), dict) else {}
            tts_artifacts = tts_result.get("artifacts") if isinstance(tts_result.get("artifacts"), dict) else {}
            stale_remote = tts_artifacts.get("stale_remote_audio") if isinstance(tts_artifacts.get("stale_remote_audio"), dict) else {}
            stale_metrics = stale_remote.get("metrics") if isinstance(stale_remote.get("metrics"), dict) else {}
            if tts_metrics.get("audio_url_404") or stale_metrics.get("audio_url_404"):
                audio_url_404_count += 1
            if tts_metrics.get("local_audio_reused") or tts_artifacts.get("local_audio_reused"):
                local_audio_reused_count += 1
            if tts_metrics.get("audio_regenerated"):
                audio_regenerated_count += 1
            if tts_result.get("blocker_category") == "tts_paid_approval_required" or any(item.get("category") == "tts_paid_approval_required" for item in state.blockers):
                tts_paid_approval_required_count += 1
            if tts_metrics.get("tts_estimated_cost") is not None:
                try:
                    tts_estimated_costs.append(float(tts_metrics["tts_estimated_cost"]))
                except (TypeError, ValueError):
                    pass
            if tts_metrics.get("tts_actual_cost_if_available") is not None:
                try:
                    tts_actual_costs.append(float(tts_metrics["tts_actual_cost_if_available"]))
                except (TypeError, ValueError):
                    pass
        hooks_configured = all(item.get("configured") for item in self.hook_plan.values())
        hook_sources = sorted({str(item.get("source")) for item in self.hook_plan.values()})
        hook_last_paths = {
            stage: item.get("last_result_path", "")
            for stage, item in (self.hook_validation.get("hooks") or {}).items()
            if isinstance(item, dict)
        }
        worker = self.worker_status()
        next_publishable = next_publishable_slug(states, self.content_rank_by_slug)
        smallest_10 = self.content_size_ranking[:10]
        queued_by_stage = {stage: len(queue) for stage, queue in self.stage_queues.items()}
        queued_by_lane = lane_counts_from_stage_counts(queued_by_stage)
        completed_lanes = completed_by_lane(states)
        blocked_lanes = blocked_by_lane(states)
        heartbeat = read_json(self.heartbeat_path(), {})
        active_lane_counts = heartbeat.get("active_lane_counts") if isinstance(heartbeat.get("active_lane_counts"), dict) else {lane: 0 for lane in LANE_NAMES}
        paid_operations_running = int(heartbeat.get("paid_operations_running") or 0) if isinstance(heartbeat, dict) else 0
        paid_operations_queued = queued_by_stage.get("tts_queue", 0)
        current_bottleneck_lane = ""
        active_or_queued = Counter({lane: int(active_lane_counts.get(lane, 0)) + int(queued_by_lane.get(lane, 0)) for lane in LANE_NAMES})
        if any(active_or_queued.values()):
            current_bottleneck_lane = active_or_queued.most_common(1)[0][0]
        elif any(blocked_lanes.values()):
            current_bottleneck_lane = Counter(blocked_lanes).most_common(1)[0][0]
        ready_waiting_publish_barrier = sum(1 for state in states if any(item.get("category") == "release_order" for item in state.blockers))
        terminal_skipped_by_order_policy = sum(
            1
            for state in states
            if self.args.allow_blocked_order_skip
            and not state.published
            and state_terminal_status(state) in {"BLOCKED", "TERMINAL_BLOCKED_WITH_EVIDENCE", "FAILED", "SKIPPED_TERMINAL"}
            and bool(state.blockers)
        )
        prepared_not_published = sum(
            1
            for state in states
            if not state.published
            and (
                state.stage_results.get("upload_queue", {}).get("status") == "PASS"
                or state.stage_results.get("metadata_publish_queue", {}).get("status") == "PASS"
                or state.ready
            )
        )
        return {
            "run_id": self.catalog_dir.name,
            "total_unique_books": len(states),
            "exact_unique_title_count": len(self.content_size_ranking) or len(states),
            "content_size_ordering_status": "enabled" if self.args.order_by == "content-size" or self.args.release_order == "ascending-content-size" else "canonical",
            "release_order": self.args.release_order,
            "enforce_release_order": self.args.enforce_release_order,
            "allow_blocked_order_skip": self.args.allow_blocked_order_skip,
            "next_publishable_slug": next_publishable,
            "next_publishable_content_size_rank": self.content_rank_by_slug.get(next_publishable, "") if next_publishable else "",
            "smallest_10_books_by_rank": smallest_10,
            "catalog_unique_titles_path": rel(self.catalog_dir / "catalog_unique_titles.json"),
            "catalog_duplicate_titles_path": rel(self.catalog_dir / "catalog_duplicate_titles.json"),
            "ranking_path": rel(self.catalog_dir / "catalog_content_size_ranking.json"),
            "cost_forecast_path": rel(self.catalog_dir / "catalog_cost_time_forecast.json"),
            **counters,
            "processed_this_wave": len(states),
            "books_by_language": dict(language_counts),
            "books_reader_live": sum(1 for state in states if "LIVE_APPROVED" in json.dumps(state.stage_results.get("inventory_queue", {}))),
            "books_cover_ready": sum(1 for state in states if state.stage_results.get("cover_queue", {}).get("status") == "PASS"),
            "books_audio_ready": sum(1 for state in states if state.stage_results.get("tts_queue", {}).get("status") == "PASS"),
            "books_fully_go_live_ready": sum(1 for state in states if state.ready),
            "books_published_this_run": sum(1 for state in states if state.published),
            "published_this_wave": sum(1 for state in states if state.published),
            "published_titles": cumulative_published_slugs,
            "verified_historical_published_count": len(verified_published_slugs),
            "total_published": len(cumulative_published_slugs),
            "ready_but_not_published": sum(1 for state in states if state.ready and not state.published),
            "books_blocked": sum(1 for state in states if state.blockers),
            "blockers_by_category": dict(blocker_counts),
            "blocked_by_rights_metadata_missing": len(rights_metadata_missing_slugs),
            "blocked_by_rights_evidence_incomplete": len(rights_evidence_incomplete_slugs),
            "blocked_by_metadata_api_rejection": len(metadata_api_rejection_slugs),
            "blocked_by_production_db_schema_mismatch": len(production_db_schema_mismatch_slugs),
            "blocked_by_stale_audio_url": blocker_counts.get("stale_audio_url", 0),
            "blocked_by_missing_local_audio": blocker_counts.get("missing_local_audio", 0),
            "blocked_by_paid_tts_approval_required": blocker_counts.get("tts_paid_approval_required", 0),
            "blocked_by_tts_generation_failure": blocker_counts.get("tts_generation_failed", 0),
            "blocked_by_audio_qa_failure": blocker_counts.get("audio_qa", 0),
            "blocked_by_audio_provider_quality_limit": blocker_counts.get("audio_provider_quality_limit", 0),
            "blocked_by_listening_qa_schema_missing": blocker_counts.get("listening_qa_schema_missing", 0),
            "blocked_by_listening_qa_not_run": blocker_counts.get("listening_qa_not_run", 0),
            "blocked_by_audio_listening_quality_failed": blocker_counts.get("audio_listening_quality_failed", 0),
            "blocked_by_stale_sidecars": blocker_counts.get("stale_sidecars", 0),
            "blocked_by_asr_transcript": blocker_counts.get("asr", 0),
            "blocked_by_sync": blocker_counts.get("sync", 0),
            "blocked_by_bengali_asr_script_mismatch": blocker_counts.get("bengali_asr_script_mismatch", 0),
            "blocked_by_bengali_asr_low_confidence": blocker_counts.get("bengali_asr_low_confidence", 0),
            "blocked_by_bengali_audio_manuscript_mismatch": blocker_counts.get("bengali_audio_manuscript_mismatch", 0),
            "blocked_by_bengali_sync_regeneration_required": blocker_counts.get("bengali_sync_regeneration_required", 0),
            "blocked_by_bengali_audio_provider_quality": blocker_counts.get("bengali_audio_provider_quality", 0),
            "blocked_by_qa": blocker_counts.get("qa", 0),
            "retry_counts": {},
            "current_concurrency_settings": {
                "max_books_active": self.args.max_books_active,
                "max_preflight_workers": getattr(self.args, "max_preflight_workers", self.args.max_books_active),
                "max_audio_reuse_workers": getattr(self.args, "max_audio_reuse_workers", self.args.max_tts_workers),
                "max_tts_workers": self.args.max_tts_workers,
                "max_paid_workers": getattr(self.args, "max_paid_workers", self.args.max_tts_workers),
                "max_asr_workers": self.args.max_asr_workers,
                "max_cover_workers": self.args.max_cover_workers,
                "max_upload_workers": getattr(self.args, "max_upload_workers", self.args.max_books_active),
                "max_metadata_workers": getattr(self.args, "max_metadata_workers", self.args.max_books_active),
                "max_browser_workers": self.args.max_browser_workers,
            },
            "active_lane_counts": active_lane_counts,
            "queued_by_lane": queued_by_lane,
            "completed_by_lane": completed_lanes,
            "blocked_by_lane": blocked_lanes,
            "paid_operations_queued": paid_operations_queued,
            "paid_operations_running": paid_operations_running,
            "estimated_cost_by_lane": {"tts_lane": round(sum(tts_estimated_costs), 4) if tts_estimated_costs else 0},
            "actual_cost_by_lane": {"tts_lane": round(sum(tts_actual_costs), 4) if tts_actual_costs else "not_available"},
            "ready_waiting_on_publish_barrier": ready_waiting_publish_barrier,
            "ready_but_waiting_on_publish_barrier": ready_waiting_publish_barrier,
            "terminal_blockers_skipped_by_order_policy": terminal_skipped_by_order_policy,
            "books_prepared_but_not_published": prepared_not_published,
            "current_bottleneck_lane": current_bottleneck_lane,
            "wave_size": self.wave_size or "unlimited",
            "priority": self.args.priority,
            "stop_reason": self.stop_reason,
            "stop_guard_triggered": self.stop_guard_triggered,
            "stop_guard_reason": self.stop_reason if self.stop_guard_triggered else "",
            "stop_guard_counter_used": self.stop_guard_counter_used,
            "stop_guard_counter_value": self.stop_guard_counter_value,
            "stop_guard_limit": self.stop_guard_limit,
            "rate_limit_or_cost_warnings": [],
            "hook_config_status": "configured" if hooks_configured else "missing",
            "hook_source": "|".join(hook_sources),
            "hook_command_redacted": {stage: item.get("command_redacted", "") for stage, item in self.hook_plan.items()},
            "hook_validation_status": self.hook_validation.get("status", "NOT_RUN"),
            "hook_last_result_path": hook_last_paths,
            "background_worker_status": worker["status"],
            "background_worker_pid": worker["pid"],
            "background_worker_pid_running": worker["pid_running"],
            "pid_file": worker["pid_file"],
            "heartbeat_path": worker["heartbeat_path"],
            "daemon_log": worker["daemon_log"],
            "storage_backend_detected": storage_backend_detected(),
            "metadata_backend_detected": metadata_backend_detected(),
            "browser_tooling_detected": browser_tooling_detected(),
            "average_wpm": round(sum(wpms) / len(wpms), 2) if wpms else None,
            "average_audio_score": round(sum(audio_scores) / len(audio_scores), 2) if audio_scores else None,
            "total_generated_audio_duration_seconds": round(sum(audio_durations), 2),
            "total_estimated_cost": round(sum(tts_estimated_costs), 4) if tts_estimated_costs else "not_available",
            "openai_usage": "not_available",
            "paid_tts_approval_detected": os.environ.get("EARNALISM_APPROVE_PAID_OPENAI_TTS", "").lower() in {"1", "true", "yes"},
            "tts_budget_limit": os.environ.get("EARNALISM_TTS_MAX_ESTIMATED_USD", ""),
            "tts_estimated_cost": round(sum(tts_estimated_costs), 4) if tts_estimated_costs else 0,
            "tts_actual_cost_if_available": round(sum(tts_actual_costs), 4) if tts_actual_costs else "not_available",
            "audio_url_404_count": audio_url_404_count,
            "local_audio_reused_count": local_audio_reused_count,
            "audio_regenerated_count": audio_regenerated_count,
            "tts_paid_approval_required_count": tts_paid_approval_required_count,
            "cloudinary_uploads": sum(1 for state in states if state.stage_results.get("upload_queue", {}).get("status") == "PASS"),
            "failed_uploads": sum(1 for state in states if state.stage_results.get("upload_queue", {}).get("status") not in {None, "PASS"}),
            "browser_failures": sum(1 for state in states if state.stage_results.get("browser_gate_queue", {}).get("status") not in {None, "PASS"}),
            "exact_command_used": self.command,
            "next_recommended_resume_command": f"python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest {rel(DEFAULT_MANIFEST)} --languages eng,ben --max-books-active {self.args.max_books_active} --max-preflight-workers {getattr(self.args, 'max_preflight_workers', 0)} --max-audio-reuse-workers {getattr(self.args, 'max_audio_reuse_workers', 0)} --max-tts-workers {self.args.max_tts_workers} --max-paid-workers {getattr(self.args, 'max_paid_workers', 0)} --max-asr-workers {self.args.max_asr_workers} --max-cover-workers {self.args.max_cover_workers} --max-upload-workers {getattr(self.args, 'max_upload_workers', 0)} --max-metadata-workers {getattr(self.args, 'max_metadata_workers', 0)} --max-browser-workers {self.args.max_browser_workers} --max-attempts {self.args.max_attempts} --wave-size {self.wave_size or 40} --priority {self.args.priority} --order-by {self.args.order_by} --release-order {self.args.release_order}{' --enforce-release-order' if self.args.enforce_release_order else ''}{' --allow-blocked-order-skip' if self.args.allow_blocked_order_skip else ''} --exclude-slugs book-63afd5e9be --publish-approved --resume-from-latest --fail-closed",
            "git_diff_summary": git_diff_summary(),
        }

    def catalog_status(self) -> str:
        summary = self.dashboard_summary()
        if summary["total_unique_books"] and summary["books_published_this_run"] == summary["total_unique_books"] and summary["books_blocked"] == 0:
            return "CATALOG GO LIVE READY: all eligible books passed release gates and were published."
        if summary["books_published_this_run"] > 0:
            return "CATALOG PARTIAL GO LIVE: some books were published; blockers remain."
        return "CATALOG NOT GO LIVE READY: no books could be safely published."


def iter_manifest_records(path: Path) -> list[dict[str, Any]]:
    data = read_json(path, [])
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("books", "candidates", "items", "records"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
        candidates = data.get("candidates")
        if isinstance(candidates, dict):
            return [item for item in candidates.values() if isinstance(item, dict)]
    return []


def record_slug(record: dict[str, Any]) -> str:
    for key in ("slug", "book_slug", "bookSlug", "candidate_slug"):
        if record.get(key):
            return normalize_slug(str(record[key]))
    identifier = normalize_slug(str(record.get("id") or ""))
    if identifier.startswith("bn-") or identifier.startswith("book-"):
        return identifier
    title = record.get("title") or record.get("name") or ""
    return normalize_slug(str(title))


def latest_catalog_dir() -> Path | None:
    candidates = sorted(path for path in RELEASE_GATE_ROOT.glob("catalog_*") if path.is_dir())
    return candidates[-1] if candidates else None


def pid_is_running(pid: int | str | None) -> bool:
    try:
        parsed = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if parsed <= 0:
        return False
    try:
        os.kill(parsed, 0)
    except OSError:
        return False
    return True


def latest_book_evidence(slug: str) -> Path | None:
    candidates = sorted(RELEASE_GATE_ROOT.glob(f"{slug}_*/goliveevidence.json"))
    return candidates[-1] if candidates else None


def load_book_payloads(slug: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = controlled_publication_base(slug)
    candidate = ROOT / "internal" / "audiobook_lab" / "bengali_store_candidates" / slug
    return (
        read_json(base / "public_book.json", {}),
        read_json(base / "reader_manifest.json", {}),
        read_json(base / "source_evidence.json", {}),
        read_json(candidate / "release_gate_report.json", {}),
    )


def controlled_chapter_paths(slug: str) -> list[Path]:
    return sorted((controlled_publication_base(slug) / "chapters").glob("*.json"))


def load_rendered_chapters(slug: str) -> list[dict[str, Any]]:
    chapters = []
    for path in controlled_chapter_paths(slug):
        payload = read_json(path, {})
        text = str(payload.get("content") or payload.get("text") or payload.get("body") or "")
        title = str(payload.get("title") or payload.get("name") or path.stem)
        chapters.append({"id": payload.get("id") or path.stem, "title": title, "path": path, "text": text})
    return chapters


def content_word_count_for_slug(slug: str) -> int:
    chapters = load_rendered_chapters(slug)
    if chapters:
        return sum(len(word_tokens(chapter["text"])) for chapter in chapters)
    content_chapters = sorted((ROOT / "content" / "books" / slug / "chapters").glob("*.json"))
    total = 0
    for path in content_chapters:
        payload = read_json(path, {})
        total += len(word_tokens(str(payload.get("content") or payload.get("text") or payload.get("body") or "")))
    if total:
        return total
    raw = ROOT / "content" / "books" / slug / "raw" / "source.txt"
    if raw.exists():
        return len(word_tokens(raw.read_text(encoding="utf-8", errors="ignore")))
    return 0


def any_source_path(slug: str) -> Path | None:
    candidates = [
        ROOT / "content" / "books" / slug / "raw" / "source.txt",
        ROOT / "content" / "books" / slug / "raw" / "source.md",
        ROOT / "content" / "books" / slug / "raw" / "source.html",
        ROOT / "content" / "books" / slug / "source-rights.md",
    ]
    for path in candidates:
        if path.exists():
            return path
    chapter_dir = ROOT / "content" / "books" / slug / "chapters"
    if chapter_dir.exists() and any(chapter_dir.glob("*.json")):
        return chapter_dir
    return None


def source_of_truth(slug: str, rendered: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]], str]:
    content_chapters = sorted((ROOT / "content" / "books" / slug / "chapters").glob("*.json"))
    if content_chapters:
        chapters = []
        for path in content_chapters:
            payload = read_json(path, {})
            text = sanitize_manuscript_text(str(payload.get("content") or payload.get("text") or payload.get("body") or ""))
            chapters.append({"id": payload.get("id") or path.stem, "title": str(payload.get("title") or path.stem), "text": text})
        return "curated_repo_chapter_files", rel(content_chapters[0].parent), chapters, "\n\n".join(item["text"] for item in chapters)
    raw_path = ROOT / "content" / "books" / slug / "raw" / "source.txt"
    if raw_path.exists():
        text = sanitize_manuscript_text(raw_path.read_text(encoding="utf-8", errors="ignore"))
        return "curated_raw_source_file", rel(raw_path), [{"id": "source", "title": "Source", "text": text}], text
    controlled_base = controlled_publication_base(slug)
    source_evidence = controlled_base / "source_evidence.json"
    checksum = controlled_base / "checksum_manifest.json"
    if source_evidence.exists() or checksum.exists():
        return "controlled_publication_with_evidence", rel(source_evidence if source_evidence.exists() else checksum), rendered, "\n\n".join(item["text"] for item in rendered)
    return "missing_reliable_source_of_truth", "", [], ""


def audited_graphical_cover_fallback(slug: str) -> dict[str, Any] | None:
    """Return the accepted runtime cover pair from the canonical cover audit."""

    report = read_json(ROOT / "book_cover_audit_report.json", {})
    for item in report.get("covers", []):
        if not isinstance(item, dict) or item.get("slug") != slug:
            continue
        accepted = (
            item.get("front_back_pair_exists") is True
            and item.get("front_cover_status") == "GRAPHICAL_COVER_APPROVED"
            and item.get("back_cover_status") == "GRAPHICAL_COVER_APPROVED"
            and item.get("cover_is_graphical_content_themed") is True
            and item.get("cover_is_typography_only_plain") is False
            and item.get("cover_broken_or_404") is False
        )
        return item if accepted else None
    return None


def cover_inventory(
    public_book: dict[str, Any], *, dry_run: bool, slug: str = ""
) -> dict[str, Any]:
    front = str(public_book.get("cover_url") or public_book.get("cover_image_url") or public_book.get("coverImage") or "")
    back = str(public_book.get("back_cover_url") or public_book.get("back_cover_image_url") or public_book.get("backCoverImage") or "")
    dimensions = public_book.get("cover_dimensions") if isinstance(public_book.get("cover_dimensions"), dict) else {}
    front_dim = dimensions.get("front")
    back_dim = dimensions.get("back")
    placeholder = bool(re.search(r"placeholder|cover-in-curation|missing", front + " " + back, re.I))
    direct_pair_passes = bool(
        front
        and back
        and "res.cloudinary.com" in front
        and "res.cloudinary.com" in back
        and not placeholder
        and (front_dim in (REQUIRED_COVER_SIZE, tuple(REQUIRED_COVER_SIZE), None))
        and (back_dim in (REQUIRED_COVER_SIZE, tuple(REQUIRED_COVER_SIZE), None))
    )
    graphical_fallback = audited_graphical_cover_fallback(slug) if slug else None
    status = "PASS" if direct_pair_passes or graphical_fallback else "FAIL"
    remote = {}
    if not dry_run and front and back:
        for side, url in [("front", front), ("back", back)]:
            fetched = fetch_url(url)
            remote[side] = {
                "http_status": fetched["status"],
                "resolves": fetched["ok"],
                "dimensions": image_dimensions(fetched["body"]),
                "sha256": hashlib.sha256(fetched["body"]).hexdigest() if fetched["body"] else None,
            }
        if any(remote[side].get("dimensions") != REQUIRED_COVER_SIZE for side in ("front", "back")):
            status = "PASS" if graphical_fallback else "FAIL"
    return {
        "status": status,
        "front_url": front,
        "back_url": back,
        "front_dimensions": front_dim,
        "back_dimensions": back_dim,
        "placeholder_detected": placeholder,
        "effective_source": (
            "DIRECT_FRONT_BACK"
            if direct_pair_passes
            else "GRAPHICAL_RUNTIME_FALLBACK"
            if graphical_fallback
            else "MISSING_OR_UNAPPROVED"
        ),
        "graphical_fallback_evidence": graphical_fallback or {},
        "remote": remote,
    }


def sidecar_inventory(slug: str) -> dict[str, Any]:
    sync_dir = RELEASE_GATE_ROOT / "sync_manifests" / slug
    files = sorted(sync_dir.glob("*.json")) if sync_dir.exists() else []
    enhanced = [path for path in files if "enhanced" in path.name]
    has_real_sync = False
    for path in enhanced:
        payload = read_json(path, {})
        if payload.get("auto_estimated_sync") is False or payload.get("sync_score", 0) >= 9.7:
            has_real_sync = True
    return {
        "sync_manifest_dir": rel(sync_dir),
        "sync_manifest_count": len(files),
        "enhanced_manifest_count": len(enhanced),
        "has_release_candidate": has_real_sync,
    }


def production_endpoint_probe(slug: str) -> str:
    url = f"{DEFAULT_API_URL}/api/reader/book/{slug}/audiobook"
    result = fetch_url(url, timeout=10)
    return str(result["status"])


def cover_brief_from_manuscript(state: BookState) -> str:
    chapters = load_rendered_chapters(state.slug)
    sample = "\n\n".join(chapter["text"][:600] for chapter in chapters[:2])
    return (
        f"# Cover Content Brief: {state.title}\n\n"
        f"- Slug: `{state.slug}`\n"
        f"- Author: `{state.author}`\n"
        f"- Language: `{state.language}`\n"
        f"- Required dimensions: 1600x2400 front and back.\n"
        f"- Typography must be deterministic code overlay; do not trust image-model rendered text.\n"
        f"- Bottom imprint: `Earnalism - A Reo Enterprise Venture`.\n\n"
        "## Manuscript-Derived Sample\n\n"
        f"{sample.strip()[:1800]}\n"
    )


def sanitize_manuscript_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    text = re.sub(r"(?m)^\s*(Project Gutenberg|Gutenberg|Wikisource|source:|retrieved from).*$", "", text, flags=re.I)
    text = re.sub(r"(?m)^\s*(পৃষ্ঠা|পৃ\.?|page)\s*\d+\s*$", "", text, flags=re.I)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip() + "\n"


def content_integrity_report(state: BookState, rendered_chapters: list[dict[str, Any]], clean_text: str) -> dict[str, Any]:
    source_type, source_ref, source_chapters, source_text = source_of_truth(state.slug, rendered_chapters)
    rendered_word_count = len(word_tokens(clean_text))
    source_word_count = len(word_tokens(source_text))
    source_titles = [item["title"] for item in source_chapters]
    rendered_titles = [item["title"] for item in rendered_chapters]
    duplicate_chapters = [title for title, count in Counter(rendered_titles).items() if count > 1]
    missing_chapters = [title for title in source_titles if title not in rendered_titles] if source_titles and source_type != "curated_raw_source_file" else []
    extra_chapters = [title for title in rendered_titles if source_titles and title not in source_titles] if source_type != "curated_raw_source_file" else []
    source_norm = normalize_text(source_text)
    rendered_norm = normalize_text(clean_text)
    similarity = 10.0 if source_type in {"controlled_publication_with_evidence", "curated_repo_chapter_files"} and source_text == clean_text else round(sequence_similarity(source_norm, rendered_norm) * 10, 4)
    body_junk = []
    for name, pattern in JUNK_PATTERNS:
        if pattern.search(clean_text):
            body_junk.append(name)
    toc_exists = bool(rendered_chapters)
    toc_entry_count = len(rendered_chapters)
    chapter_order_match = not missing_chapters and not extra_chapters
    chapter_title_match = not missing_chapters and not extra_chapters
    controlled_base = controlled_publication_base(state.slug)
    toc_links_valid = all((controlled_base / "chapters" / f"{chapter['id']}.json").exists() or chapter.get("path") for chapter in rendered_chapters)
    orphan_chapters: list[str] = []
    duplicate_anchor_ids = [chapter_id for chapter_id, count in Counter(str(item["id"]) for item in rendered_chapters).items() if count > 1]
    blockers = []
    if source_type == "missing_reliable_source_of_truth":
        blockers.append("No reliable source of truth exists for completeness validation.")
    if not rendered_chapters:
        blockers.append("Rendered reader chapters are missing.")
    if missing_chapters:
        blockers.append(f"Missing chapters: {', '.join(missing_chapters[:8])}")
    if duplicate_chapters:
        blockers.append(f"Duplicate chapters: {', '.join(duplicate_chapters[:8])}")
    if not chapter_order_match:
        blockers.append("Chapter order does not match source of truth.")
    if not toc_exists:
        blockers.append("TOC/index entries are missing.")
    if not toc_links_valid:
        blockers.append("Reader TOC contains broken chapter links.")
    if duplicate_anchor_ids:
        blockers.append(f"Duplicate anchor IDs: {', '.join(duplicate_anchor_ids[:8])}")
    if body_junk:
        blockers.append(f"Body junk detected: {', '.join(body_junk)}")
    if similarity < 9.7:
        blockers.append(f"Source vs rendered similarity below threshold: {similarity} < 9.7")
    completeness_score = 10.0 if not blockers else max(0.0, 10.0 - min(10, len(blockers)) * 1.5)
    index_integrity_score = 10.0 if toc_exists and toc_links_valid and not orphan_chapters and not duplicate_anchor_ids else 0.0
    chapter_consistency_score = 10.0 if chapter_order_match and chapter_title_match and not duplicate_chapters else 0.0
    pass_status = (
        completeness_score >= 9.8
        and index_integrity_score == 10.0
        and chapter_consistency_score >= 9.8
        and similarity >= 9.7
        and toc_links_valid
        and chapter_order_match
        and not missing_chapters
        and not duplicate_chapters
        and not orphan_chapters
        and not duplicate_anchor_ids
        and not body_junk
    )
    return {
        "slug": state.slug,
        "title": state.title,
        "author": state.author,
        "language": state.language,
        "source_of_truth_type": source_type,
        "source_of_truth_path_or_reference": source_ref,
        "source_chapter_count": len(source_chapters),
        "rendered_chapter_count": len(rendered_chapters),
        "source_word_count": source_word_count,
        "rendered_word_count": rendered_word_count,
        "word_count_delta_percent": round(((rendered_word_count - source_word_count) / source_word_count * 100), 4) if source_word_count else None,
        "missing_chapters": missing_chapters,
        "extra_chapters": extra_chapters,
        "duplicate_chapters": duplicate_chapters,
        "chapter_order_match": chapter_order_match,
        "chapter_title_match": chapter_title_match,
        "toc_exists": toc_exists,
        "toc_entry_count": toc_entry_count,
        "toc_links_valid": toc_links_valid,
        "broken_toc_links": [] if toc_links_valid else ["chapter file missing"],
        "orphan_chapters": orphan_chapters,
        "duplicate_anchor_ids": duplicate_anchor_ids,
        "body_junk_detected": body_junk,
        "frontmatter_in_body_detected": "source_repository" in body_junk,
        "page_number_artifacts_detected": "page_number_line" in body_junk,
        "source_vs_rendered_similarity_score": similarity,
        "completeness_score": completeness_score,
        "index_integrity_score": index_integrity_score,
        "chapter_consistency_score": chapter_consistency_score,
        "content_integrity_score": min(completeness_score, index_integrity_score, chapter_consistency_score, similarity),
        "status": "PASS" if pass_status else "FAIL",
        "blocker_reasons": blockers,
    }


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return ""


def manifest_value(record: dict[str, Any], *keys: str) -> Any:
    normalized = {re.sub(r"[^a-z0-9]", "", key.lower()): value for key, value in record.items()}
    for key in keys:
        compact = re.sub(r"[^a-z0-9]", "", key.lower())
        if compact in normalized and normalized[compact] not in (None, ""):
            return normalized[compact]
    return ""


def int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def infer_year_from_text(text: str, *patterns: str) -> int | None:
    for pattern in patterns:
        match = re.search(pattern, text or "", re.I)
        if match:
            return int_or_none(match.group(1))
    return None


def rights_metadata_report(state: BookState) -> dict[str, Any]:
    public_book, _, source_evidence, _ = load_book_payloads(state.slug)
    controlled_base = controlled_publication_base(state.slug)
    approval_evidence = read_json(controlled_base / "approval_evidence.json", {})
    checksum = read_json(controlled_base / "checksum_manifest.json", {})
    manifest = state.manifest_record or {}
    source_url = str(
        first_present(
            source_evidence.get("source_url") if isinstance(source_evidence, dict) else "",
            public_book.get("source_url"),
            manifest_value(manifest, "source_url", "sourceurl"),
        )
    ).strip()
    source_name = str(
        first_present(
            source_evidence.get("source_name") if isinstance(source_evidence, dict) else "",
            public_book.get("source_name"),
            manifest_value(manifest, "source_name", "sourcename"),
            "Project Gutenberg" if "gutenberg.org" in source_url else "",
        )
    ).strip()
    source_license = str(
        first_present(
            source_evidence.get("source_license") if isinstance(source_evidence, dict) else "",
            public_book.get("source_license"),
            manifest_value(manifest, "source_license", "sourcelicense"),
        )
    ).strip()
    rights_basis = str(
        first_present(
            source_evidence.get("rights_basis") if isinstance(source_evidence, dict) else "",
            public_book.get("rights_basis"),
            manifest_value(manifest, "rights_basis", "rightsbasis"),
        )
    ).strip()
    author_death_year = int_or_none(
        first_present(
            public_book.get("author_death_year"),
            manifest_value(manifest, "author_death_year", "authordeathyear"),
        )
    )
    if author_death_year is None:
        author_death_year = infer_year_from_text(rights_basis, r"(?:died|death|author died)\D{0,20}(\d{4})", r"(\d{4})\s*death")
    original_publication_year = int_or_none(
        first_present(
            public_book.get("original_publication_year"),
            manifest_value(manifest, "original_publication_year", "originalpublicationyear"),
        )
    )
    if original_publication_year is None:
        original_publication_year = infer_year_from_text(rights_basis, r"(?:first\s+)?published\D{0,20}(\d{4})", r"publication\D{0,20}(\d{4})")
    rights_tier = str(first_present(approval_evidence.get("rights_tier"), public_book.get("rights_tier"), "A")).strip().upper()
    verification_status = str(first_present(approval_evidence.get("verification_status"), public_book.get("verification_status"))).strip().lower()
    public_domain = bool(
        re.search(r"public\s*domain|gutenberg|wikisource", f"{source_name} {source_license} {rights_basis}", re.I)
        and author_death_year
        and original_publication_year
    )
    verified_at = str(
        first_present(
            approval_evidence.get("approved_at"),
            approval_evidence.get("verified_at"),
            source_evidence.get("downloaded_at") if isinstance(source_evidence, dict) else "",
            checksum.get("generated_at") if isinstance(checksum, dict) else "",
        )
    ).strip()
    source_hash = str(
        first_present(
            source_evidence.get("source_hash") if isinstance(source_evidence, dict) else "",
            source_evidence.get("content_hash") if isinstance(source_evidence, dict) else "",
            checksum.get("files", [{}])[0].get("sha256") if isinstance(checksum.get("files"), list) and checksum.get("files") else "",
        )
    ).strip()
    rights_metadata = {
        "work_title": state.title,
        "work_slug": state.slug,
        "author_name": state.author,
        "author_death_year": author_death_year,
        "original_publication_year": original_publication_year,
        "country_of_origin": "United States" if state.language == "eng" else "India",
        "source_url": source_url,
        "source_name": source_name,
        "source_license": source_license,
        "translator_name": "",
        "translator_death_year": "",
        "illustrator_name": "",
        "illustrator_death_year": "",
        "editor_name": "",
        "edition_publication_year": "",
        "rights_tier": rights_tier,
        "verification_status": verification_status,
        "blocked_reason": "",
        "publication_region": "global",
        "verified_at": verified_at,
    }
    required = {
        "source_url": source_url,
        "source_name": source_name,
        "source_license": source_license,
        "author_death_year": author_death_year,
        "original_publication_year": original_publication_year,
        "rights_tier": rights_tier,
        "verification_status": verification_status,
        "verified_at": verified_at,
    }
    missing_fields = [key for key, value in required.items() if value in (None, "")]
    blockers: list[str] = []
    if missing_fields:
        blockers.append(f"Required rights metadata fields are missing: {', '.join(missing_fields)}")
    if rights_tier not in {"A", "B", "C"}:
        blockers.append("rights_tier must be A, B, or C.")
    if verification_status not in {"approved", "verified"}:
        blockers.append("verification_status must be approved before publishing.")
    if rights_tier == "C":
        blockers.append("Tier C rights block publishing.")
    if not public_domain:
        blockers.append("Public-domain evidence is incomplete or not deterministic.")
    content_use_approved = not blockers and rights_tier == "A" and verification_status in {"approved", "verified"}
    explicit_audiobook_use = approval_evidence.get("audiobook_use_approved")
    if isinstance(explicit_audiobook_use, bool):
        audiobook_use_approved = content_use_approved and explicit_audiobook_use
        audiobook_use_approval_source = "approval_evidence.audiobook_use_approved"
    else:
        # Preserve legacy packets while new packets keep derivative-use approval
        # separate from the public release gate.
        audiobook_use_approved = content_use_approved and bool(
            approval_evidence.get("audiobook_enabled")
            or approval_evidence.get("audio_public_release")
            == "PUBLIC_AUDIO_RELEASE_APPROVED"
            or manifest_value(manifest, "audioallowed") is True
        )
        audiobook_use_approval_source = "legacy_release_or_manifest_evidence"
    if content_use_approved and not audiobook_use_approved:
        blockers.append("Audiobook use approval is missing from approval evidence or manifest.")
    production_metadata_ready = not blockers
    return {
        "slug": state.slug,
        "title": state.title,
        "author": state.author,
        "language": state.language,
        "source_of_truth_path_or_reference": rel(any_source_path(state.slug)) or rel(controlled_publication_base(state.slug) / "source_evidence.json"),
        "source_type": str(first_present(source_evidence.get("source_format") if isinstance(source_evidence, dict) else "", manifest_value(manifest, "sourcetype"), "controlled_publication_evidence")),
        "source_url": source_url,
        "source_hash": source_hash,
        "copyright_status": "public_domain" if public_domain else "unknown",
        "rights_basis": rights_basis,
        "license": source_license,
        "public_domain": public_domain,
        "public_domain_jurisdiction": "India and United States" if public_domain else "unknown",
        "original_publication_year": original_publication_year,
        "author_death_year": author_death_year,
        "rights_evidence": {
            "source_evidence_path": rel(controlled_publication_base(state.slug) / "source_evidence.json"),
            "approval_evidence_path": rel(controlled_publication_base(state.slug) / "approval_evidence.json"),
            "checksum_manifest_path": rel(controlled_publication_base(state.slug) / "checksum_manifest.json"),
        },
        "attribution_text": str(first_present(public_book.get("attribution_notice"), manifest_value(manifest, "attributionnotice"))),
        "content_use_approved": content_use_approved,
        "audiobook_use_approved": audiobook_use_approved,
        "audiobook_use_approval_source": audiobook_use_approval_source,
        "production_metadata_ready": production_metadata_ready,
        "rights_metadata": rights_metadata,
        "missing_fields": missing_fields,
        "blocker_reasons": blockers,
        "status": "PASS" if production_metadata_ready else "BLOCKED",
    }


def reusable_audio_evidence(state: BookState) -> dict[str, Any]:
    evidence_path = latest_book_evidence(state.slug)
    if evidence_path:
        evidence = read_json(evidence_path, {})
        if evidence.get("fallback_tts_used") is False and evidence.get("final_audio_local_path"):
            score = float(evidence.get("overall_premium_score") or 0)
            if score >= 9.7 and evidence.get("auto_approval_decision") is True:
                return {"status": "PASS", "reuse_evidence_path": rel(evidence_path), "overall_premium_score": score}
    public_book, _, _, _ = load_book_payloads(state.slug)
    if public_book.get("production_approved") is True and public_book.get("audiobook_release_gate") == "APPROVED":
        return {"status": "PASS", "reuse_source": "production_metadata_approved", "assets": public_book.get("audiobook_assets") or {}}
    return {"status": "BLOCKED", "reason": "No approved non-fallback OpenAI TTS release artifact found."}


def reusable_sync_evidence(state: BookState) -> dict[str, Any]:
    evidence_path = latest_book_evidence(state.slug)
    if evidence_path:
        evidence = read_json(evidence_path, {})
        if evidence.get("auto_estimated_sync") is False and float(evidence.get("sync_score") or 0) >= 9.7:
            return {"status": "PASS", "reuse_evidence_path": rel(evidence_path), "sync_score": evidence.get("sync_score")}
    inventory = sidecar_inventory(state.slug)
    if inventory["has_release_candidate"]:
        return {"status": "PASS", "reuse_source": "sync_manifests", **inventory}
    return {"status": "BLOCKED", "reason": "No real release-grade sync evidence found."}


def build_auto_qa(state: BookState, env_detected: dict[str, bool], command: str, *, phase: str = "final") -> dict[str, Any]:
    manuscript = state.stage_results.get("manuscript_queue", {})
    rights = state.stage_results.get("rights_metadata_preflight_queue", {})
    rights_report = read_json(state.run_dir / "rights_metadata_report.json", {})
    integrity = read_json(state.run_dir / "content_integrity_report.json", {})
    tts_result = state.stage_results.get("tts_queue", {})
    sync_result = state.stage_results.get("asr_sync_queue", {})
    tts_metrics = tts_result.get("metrics") if isinstance(tts_result.get("metrics"), dict) else {}
    tts_updated = tts_result.get("updated_fields") if isinstance(tts_result.get("updated_fields"), dict) else {}
    sync_metrics = sync_result.get("metrics") if isinstance(sync_result.get("metrics"), dict) else {}
    sync_updated = sync_result.get("updated_fields") if isinstance(sync_result.get("updated_fields"), dict) else {}
    audio_quality = {}
    for source in (tts_result, tts_metrics, sync_result, sync_metrics):
        candidate = source.get("audio_quality_scores") if isinstance(source, dict) else None
        if isinstance(candidate, dict):
            audio_quality.update(candidate)

    def audio_score(*names: str, default: float = 0.0) -> float:
        for name in names:
            if audio_quality.get(name) is not None:
                try:
                    return float(audio_quality[name])
                except (TypeError, ValueError):
                    return default
        return default

    def explicit_audio_flag(*names: str, expected: bool) -> bool:
        for name in names:
            if name not in audio_quality:
                continue
            value = audio_quality.get(name)
            if isinstance(value, bool):
                return value is expected
            lowered = str(value).strip().lower()
            if lowered in {"true", "yes", "1", "pass", "passed"}:
                return expected is True
            if lowered in {"false", "no", "0", "fail", "failed"}:
                return expected is False
        return False

    def audio_evidence_present(*names: str) -> bool:
        return any(audio_quality.get(name) is not None for name in names)

    transcript_match_score = float(sync_result.get("transcript_match_score") or sync_metrics.get("transcript_match_score") or sync_updated.get("transcript_match_score") or 0)
    sync_score = float(sync_result.get("sync_score") or sync_metrics.get("sync_score") or sync_updated.get("sync_score") or 0)
    vtt_alignment_score = float(sync_result.get("vtt_alignment_score") or sync_metrics.get("vtt_alignment_score") or sync_updated.get("vtt_alignment_score") or 0)
    auto_estimated_sync = (
        sync_result.get("auto_estimated_sync")
        if "auto_estimated_sync" in sync_result
        else sync_metrics.get("auto_estimated_sync")
        if "auto_estimated_sync" in sync_metrics
        else sync_updated.get("auto_estimated_sync")
    )
    fallback_tts_used = (
        tts_result.get("fallback_tts_used")
        if "fallback_tts_used" in tts_result
        else tts_metrics.get("fallback_tts_used")
        if "fallback_tts_used" in tts_metrics
        else tts_updated.get("fallback_tts_used")
    )
    rights_metadata_ready = (
        rights.get("production_metadata_ready") is True
        or rights_report.get("production_metadata_ready") is True
        or state.stage_results.get("metadata_publish_queue", {}).get("updated_fields", {}).get("rights_metadata_status") == "PASS"
    )
    scores = {
        "cover_semantic_match_score": 9.8 if state.stage_results.get("cover_queue", {}).get("status") == "PASS" else 0.0,
        "manuscript_scope_score": 10.0 if manuscript.get("status") == "PASS" else 0.0,
        "content_sanitation_score": 10.0 if manuscript.get("status") == "PASS" and not integrity.get("body_junk_detected") else 0.0,
        "frontmatter_removal_score": 10.0 if manuscript.get("status") == "PASS" and not integrity.get("frontmatter_in_body_detected") else 0.0,
        "content_integrity_score": float(integrity.get("content_integrity_score") or 0),
        "source_completeness_score": float(integrity.get("completeness_score") or 0),
        "index_integrity_score": float(integrity.get("index_integrity_score") or 0),
        "chapter_consistency_score": float(integrity.get("chapter_consistency_score") or 0),
        "rights_metadata_score": 10.0 if rights_metadata_ready else 0.0,
        "naturalness_score": audio_score("naturalness_score", "narration_naturalness_score", "naturalness"),
        "narration_naturalness_score": audio_score("narration_naturalness_score", "naturalness"),
        "pronunciation_score": audio_score("pronunciation_score", "bengali_pronunciation_score", "english_pronunciation_score", "pronunciation"),
        "bengali_pronunciation_score": audio_score("bengali_pronunciation_score", "english_pronunciation_score", "pronunciation_score", "pronunciation"),
        "emotional_expression_score": audio_score("emotional_expression_score", "expression"),
        "punctuation_pause_score": audio_score("punctuation_pause_score", "pauses"),
        "pacing_score": audio_score("pacing_score", "pacing"),
        "continuity_score": audio_score("continuity_score", "paragraph_continuity_score", "sentence_continuity_score", "continuity"),
        "anti_robotic_texture_score": audio_score("anti_robotic_texture_score", "mechanical_texture_absence_score", "robotic_cadence_absence_score"),
        "robotic_cadence_absence_score": audio_score("robotic_cadence_absence_score", "no_robotic_cadence_score", "robotic_absence_score"),
        "mechanical_texture_absence_score": audio_score("mechanical_texture_absence_score", "no_mechanical_texture_score"),
        "list_reading_absence_score": audio_score("list_reading_absence_score", "no_list_reading_rhythm_score"),
        "anti_choppy_join_score": audio_score("anti_choppy_join_score", "choppy_join_absence_score", "no_choppy_joins_score"),
        "choppy_join_absence_score": audio_score("choppy_join_absence_score", "no_choppy_joins_score"),
        "listener_enjoyment_score": audio_score("listener_enjoyment_score", "pleasantness_score", "listener_enjoyment"),
        "overall_listening_score": audio_score("overall_listening_score", "listener_enjoyment_score", "pleasantness_score"),
        "listening_confidence_score": audio_score("listening_confidence_score", "listening_qa_confidence_score", "judge_confidence_score"),
        "silence_clipping_score": audio_score("silence_clipping_score", "silence_clipping", default=10.0 if sync_result.get("status") == "PASS" else 0.0),
        "truncation_score": audio_score("truncation_score", "truncation", default=10.0 if sync_result.get("status") == "PASS" else 0.0),
        "duplicate_segment_score": audio_score("duplicate_segment_score", "duplicate_segments", default=10.0 if sync_result.get("status") == "PASS" else 0.0),
        "transcript_match_score": transcript_match_score,
        "sync_score": sync_score,
        "vtt_alignment_score": vtt_alignment_score,
        "upload_checksum_score": 10.0 if state.stage_results.get("upload_queue", {}).get("status") == "PASS" else 0.0,
        "metadata_integrity_score": 9.8 if state.stage_results.get("metadata_publish_queue", {}).get("status") == "PASS" else 0.0,
        "browser_audio_start_score": 9.8 if state.stage_results.get("browser_gate_queue", {}).get("status") == "PASS" else 0.0,
    }
    pre_upload_fields = [
        "cover_semantic_match_score",
        "manuscript_scope_score",
        "content_sanitation_score",
        "frontmatter_removal_score",
        "content_integrity_score",
        "source_completeness_score",
        "index_integrity_score",
        "chapter_consistency_score",
        "rights_metadata_score",
        "naturalness_score",
        "narration_naturalness_score",
        "pronunciation_score",
        "bengali_pronunciation_score",
        "emotional_expression_score",
        "punctuation_pause_score",
        "pacing_score",
        "continuity_score",
        "anti_robotic_texture_score",
        "robotic_cadence_absence_score",
        "mechanical_texture_absence_score",
        "list_reading_absence_score",
        "anti_choppy_join_score",
        "choppy_join_absence_score",
        "listener_enjoyment_score",
        "overall_listening_score",
        "listening_confidence_score",
        "silence_clipping_score",
        "truncation_score",
        "duplicate_segment_score",
        "transcript_match_score",
        "sync_score",
        "vtt_alignment_score",
    ]
    final_only_fields = [
        "upload_checksum_score",
        "metadata_integrity_score",
        "browser_audio_start_score",
    ]
    release_fields = pre_upload_fields + (final_only_fields if phase == "final" else [])
    confidence_fields = {"listening_confidence_score"}
    release_score_fields = [field for field in release_fields if field not in confidence_fields]
    scores["overall_premium_score"] = min(scores[field] for field in release_score_fields)
    scores["confidence_score"] = scores["listening_confidence_score"] or round(
        sum(
            1
            for field in release_score_fields
            if scores[field] >= (10.0 if field in {"frontmatter_removal_score", "index_integrity_score", "upload_checksum_score"} else 9.7)
        )
        / len(release_score_fields),
        4,
    )
    tts_reuse_ok = bool(tts_result.get("reuse_evidence_path") or tts_result.get("reuse_source"))
    hard_flags = {
        "fallback_tts_used_false": fallback_tts_used is False or tts_reuse_ok,
        "auto_estimated_sync_false": auto_estimated_sync is False,
        "listening_qa_samples_present": audio_evidence_present("listening_sample_count", "audio_judge_samples", "sample_results")
        and int(audio_quality.get("listening_sample_count") or len(audio_quality.get("audio_judge_samples") or audio_quality.get("sample_results") or [])) >= 6,
        "dialogue_emotional_sections_judged": explicit_audio_flag("dialogue_emotional_sections_judged", "all_dialogue_emotional_sections_judged", expected=True),
        "no_robotic_cadence": explicit_audio_flag("no_robotic_cadence", "robotic_cadence_absent", expected=True)
        or explicit_audio_flag("robotic_cadence_detected", "has_robotic_cadence", expected=False),
        "no_mechanical_texture": explicit_audio_flag("no_mechanical_texture", "mechanical_texture_absent", expected=True)
        or explicit_audio_flag("mechanical_texture_detected", expected=False),
        "no_list_reading_rhythm": explicit_audio_flag("no_list_reading_rhythm", "list_reading_rhythm_absent", expected=True)
        or explicit_audio_flag("list_reading_rhythm_detected", expected=False),
        "no_choppy_joins": explicit_audio_flag("no_choppy_joins", "choppy_joins_absent", expected=True)
        or explicit_audio_flag("choppy_joins_detected", expected=False),
        "no_repeated_identical_sentence_endings": explicit_audio_flag("no_repeated_identical_sentence_endings", "repeated_identical_sentence_endings_absent", expected=True)
        or explicit_audio_flag("repeated_identical_sentence_endings_detected", expected=False),
        "no_abrupt_tts_resets": explicit_audio_flag("no_abrupt_tts_resets", "abrupt_tts_resets_absent", expected=True)
        or explicit_audio_flag("abrupt_tts_resets_detected", expected=False),
        "no_placeholder_audio": explicit_audio_flag("no_placeholder_audio", "placeholder_audio_absent", expected=True)
        or explicit_audio_flag("placeholder_audio_used", expected=False),
        "toc_links_valid": integrity.get("toc_links_valid") is True,
        "no_missing_chapters": not integrity.get("missing_chapters"),
        "no_duplicate_chapters": not integrity.get("duplicate_chapters"),
        "no_broken_internal_links": not integrity.get("broken_toc_links"),
        "rights_metadata_ready": rights_metadata_ready,
    }
    if phase == "final":
        hard_flags["production_metadata_approved"] = state.stage_results.get("metadata_publish_queue", {}).get("status") == "PASS"
    blockers = []
    thresholds = {
        "cover_semantic_match_score": 9.7,
        "manuscript_scope_score": 9.8,
        "content_sanitation_score": 9.8,
        "frontmatter_removal_score": 10.0,
        "content_integrity_score": 9.8,
        "source_completeness_score": 9.8,
        "index_integrity_score": 10.0,
        "chapter_consistency_score": 9.8,
        "rights_metadata_score": 10.0,
        "naturalness_score": 9.7,
        "narration_naturalness_score": 9.7,
        "pronunciation_score": 9.7,
        "bengali_pronunciation_score": 9.7,
        "emotional_expression_score": 9.7,
        "punctuation_pause_score": 9.7,
        "pacing_score": 9.7,
        "continuity_score": 9.7,
        "anti_robotic_texture_score": 9.7,
        "robotic_cadence_absence_score": 9.7,
        "mechanical_texture_absence_score": 9.7,
        "list_reading_absence_score": 9.7,
        "anti_choppy_join_score": 9.7,
        "choppy_join_absence_score": 9.7,
        "listener_enjoyment_score": 9.7,
        "overall_listening_score": 9.7,
        "listening_confidence_score": 0.95,
        "silence_clipping_score": 9.8,
        "truncation_score": 10.0,
        "duplicate_segment_score": 10.0,
        "transcript_match_score": 9.7,
        "sync_score": 9.7,
        "vtt_alignment_score": 9.7,
        "upload_checksum_score": 10.0,
        "metadata_integrity_score": 9.7,
        "browser_audio_start_score": 9.7,
        "overall_premium_score": 9.7,
        "confidence_score": 0.95,
    }
    bengali_release_policy = state.language == "ben" or os.getenv("EARNALISM_LISTENING_POLICY_VERSION") == "bengali_audiobook_acceptance_v2_92"
    if bengali_release_policy:
        for field in [
            "naturalness_score",
            "narration_naturalness_score",
            "pronunciation_score",
            "bengali_pronunciation_score",
            "emotional_expression_score",
            "punctuation_pause_score",
            "pacing_score",
            "continuity_score",
            "anti_robotic_texture_score",
            "robotic_cadence_absence_score",
            "mechanical_texture_absence_score",
            "list_reading_absence_score",
            "anti_choppy_join_score",
            "choppy_join_absence_score",
            "listener_enjoyment_score",
        ]:
            thresholds[field] = 8.9
        thresholds["overall_listening_score"] = 9.2
        thresholds["listening_confidence_score"] = 0.90
        thresholds["overall_premium_score"] = 9.2
        thresholds["confidence_score"] = 0.90
    for field, threshold in thresholds.items():
        if field in final_only_fields and phase != "final":
            continue
        if scores.get(field, 0) < threshold:
            blockers.append(f"{field} below threshold: {scores.get(field, 0)} < {threshold}")
    for name, passed in hard_flags.items():
        if not passed:
            blockers.append(f"{name} failed")
    for blocker in state.blockers:
        blockers.append(f"{blocker['category']}: {blocker['reason']}")
    return {
        "qa_schema_version": QA_SCHEMA_VERSION,
        "phase": phase,
        "slug": state.slug,
        "title": state.title,
        "author": state.author,
        "language": state.language,
        "timestamp": iso_now(),
        "command": command,
        "environment_keys_detected": env_detected,
        "scores": scores,
        "hard_flags": hard_flags,
        "auto_approval_decision": not blockers,
        "blocker_list": blockers,
        "stage_results": state.stage_results,
    }


def build_golive_evidence(state: BookState, qa: dict[str, Any], command: str) -> dict[str, Any]:
    manuscript = state.stage_results.get("manuscript_queue", {})
    return {
        "qa_schema_version": QA_SCHEMA_VERSION,
        "slug": state.slug,
        "title": state.title,
        "author": state.author,
        "language": state.language,
        "run_id": state.run_dir.name,
        "timestamp": iso_now(),
        "exact_command_used": command,
        "git_commit": git_commit(),
        "clean_manuscript_path": manuscript.get("clean_manuscript_path"),
        "clean_manuscript_hash": manuscript.get("clean_text_hash"),
        "content_integrity_report": manuscript.get("content_integrity_report"),
        "scores": qa["scores"],
        "overall_premium_score": qa["scores"]["overall_premium_score"],
        "confidence_score": qa["scores"]["confidence_score"],
        "auto_approval_decision": qa["auto_approval_decision"],
        "blocker_list": qa["blocker_list"],
        "stage_results": state.stage_results,
        "published": state.published,
    }


def browser_probe(state: BookState) -> dict[str, Any]:
    routes = {
        "detail": fetch_url(f"{DEFAULT_FRONTEND_URL}/book/{state.slug}", timeout=15),
        "reader": fetch_url(f"{DEFAULT_FRONTEND_URL}/reader/{state.slug}", timeout=15),
        "audiobook": fetch_url(f"{DEFAULT_API_URL}/api/reader/book/{state.slug}/audiobook", timeout=15),
    }
    passed = all(routes[name]["ok"] for name in routes)
    return {
        "status": "PASS" if passed else "BLOCKED",
        "routes": {name: {"status": result["status"], "ok": result["ok"], "error": result["error"]} for name, result in routes.items()},
        "reason": "" if passed else "One or more production/browser routes failed.",
    }


def scheduling_priority(state: BookState) -> int:
    classes = set(state.classifications)
    manuscript = state.stage_results.get("manuscript_queue", {})
    word_count = int(manuscript.get("word_count") or 0)
    if "BLOCKED_NEEDS_SOURCE" in classes or "MANUSCRIPT_REPAIR_REQUIRED" in classes:
        return 6
    if "RIGHTS_METADATA_REQUIRED" in classes and not classes <= {
        "RIGHTS_METADATA_REQUIRED",
        "UPLOAD_REQUIRED",
        "METADATA_REQUIRED",
        "BROWSER_REQUIRED",
        "READY_REUSE_CANDIDATE",
        "SYNC_REQUIRED",
    }:
        return 6
    if word_count >= 80_000:
        return 5
    if "COVER_REPAIR_REQUIRED" in classes and "AUDIO_REQUIRED" in classes:
        return 4
    if "AUDIO_REQUIRED" in classes:
        return 2 if 0 < word_count <= 15_000 and "COVER_REPAIR_REQUIRED" not in classes else 3
    if classes and classes <= {"UPLOAD_REQUIRED", "METADATA_REQUIRED", "BROWSER_REQUIRED", "READY_REUSE_CANDIDATE", "SYNC_REQUIRED"}:
        return 1
    return 2


def next_publishable_slug(states: Iterable[BookState], ranks: dict[str, int]) -> str:
    candidates = []
    for state in states:
        if state.published or state.blockers:
            continue
        if state.stage_results.get("upload_queue", {}).get("status") == "PASS" and state.stage_results.get("metadata_publish_queue", {}).get("status") != "PASS":
            candidates.append(state)
    if not candidates:
        return ""
    return sorted(candidates, key=lambda item: (ranks.get(item.slug, item.order), item.slug))[0].slug


def stage_is_complete(state: BookState, stage: str) -> bool:
    return state.stage_results.get(stage, {}).get("status") == "PASS"


def tts_stage_requires_provenance_recheck(state: BookState) -> bool:
    """Return true when a previous TTS pass reused legacy non-release audio.

    Retryable ASR failures should not keep reusing an old offline/synthetic
    audiobook candidate. Sending the book back through TTS lets the hook apply
    its current provenance gate and regenerate with approved OpenAI TTS when
    the paid budget gate is present.
    """

    tts_result = state.stage_results.get("tts_queue", {})
    asr_result = state.stage_results.get("asr_sync_queue", {})
    if tts_result.get("status") != "PASS" or asr_result.get("status") != "BLOCKED":
        return False
    if asr_result.get("retryable") is False:
        return False
    artifacts = tts_result.get("artifacts") if isinstance(tts_result.get("artifacts"), dict) else {}
    reuse_source = str(artifacts.get("reuse_source") or artifacts.get("reuse", {}).get("reuse_source") or "").lower()
    meta = read_json(state.run_dir / "reused_meta.json", {})
    provider = str(meta.get("provider_used") or meta.get("provider") or artifacts.get("model") or "").lower()
    voice = str(meta.get("voice") or "").lower()
    alignment_modes = meta.get("alignment_modes") or []
    if isinstance(alignment_modes, str):
        alignment_modes = [alignment_modes]
    alignment_values = {str(item).strip().lower() for item in alignment_modes}
    disallowed_provider_tokens = {"piper", "offline", "browser", "system", "fallback", "placeholder"}
    disallowed_alignment_modes = {"synthetic", "estimated", "deterministic"}
    provider_text = " ".join([provider, voice, reuse_source])
    if any(token in provider_text for token in disallowed_provider_tokens):
        return True
    if alignment_values & disallowed_alignment_modes:
        return True
    if meta.get("auto_estimated_sync") is True:
        return True
    # A resolving legacy/local audio URL is still not release-usable if ASR
    # proves it does not match the canonical manuscript. Route back through TTS
    # so the hook can bypass the failed reused asset and generate approved audio.
    if "existing" in reuse_source or "local" in reuse_source:
        metrics = asr_result.get("metrics") if isinstance(asr_result.get("metrics"), dict) else {}
        blockers = " ".join(str(item) for item in (asr_result.get("blockers") or []))
        try:
            score = float(metrics.get("score") or metrics.get("transcript_match_score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        source_mismatch = (
            asr_result.get("blocker_category") == "asr"
            and (
                score < 9.7
                or metrics.get("first_words_match") is False
                or metrics.get("last_words_match") is False
                or "first narrated words" in blockers.lower()
                or "last narrated words" in blockers.lower()
            )
        )
        if source_mismatch:
            return True
    return False


def retry_stage_for_state(state: BookState) -> str | None:
    if state.published:
        return None
    if tts_stage_requires_provenance_recheck(state):
        return "tts_queue"
    for stage in QUEUE_NAMES:
        result = state.stage_results.get(stage)
        if not result:
            continue
        if result.get("status") == "PASS":
            continue
        if result.get("retryable", True) is False:
            return None
        return stage
    return None


def clear_stage_blockers(state: BookState, stage: str) -> None:
    categories = STAGE_BLOCKER_CATEGORIES.get(stage, set())
    if not categories:
        return
    state.blockers = [blocker for blocker in state.blockers if blocker.get("category") not in categories]


def clear_passed_stage_blockers(state: BookState) -> None:
    """Drop stale blockers from stages that now have current PASS evidence."""
    for stage, result in state.stage_results.items():
        if isinstance(result, dict) and str(result.get("status") or "").upper() == "PASS":
            clear_stage_blockers(state, stage)


def next_stage_after(stage: str, state: BookState) -> str | None:
    try:
        index = QUEUE_NAMES.index(stage)
    except ValueError:
        return None
    if index + 1 >= len(QUEUE_NAMES):
        return None
    return QUEUE_NAMES[index + 1]


def next_incomplete_stage_after(stage: str, state: BookState) -> str | None:
    try:
        index = QUEUE_NAMES.index(stage)
    except ValueError:
        return None
    for next_stage in QUEUE_NAMES[index + 1 :]:
        result = state.stage_results.get(next_stage)
        if not isinstance(result, dict) or str(result.get("status") or "").upper() != "PASS":
            return next_stage
    return None


def git_commit() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def git_diff_summary() -> str:
    completed = subprocess.run(["git", "diff", "--stat", "--", "internal/audiobook_lab/scripts/release_catalog_factory.py"], cwd=ROOT, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def storage_backend_detected() -> dict[str, bool]:
    return {
        "cloudinary": bool(
            os.environ.get("CLOUDINARY_URL")
            or (
                os.environ.get("CLOUDINARY_CLOUD_NAME")
                and os.environ.get("CLOUDINARY_API_KEY")
                and os.environ.get("CLOUDINARY_API_SECRET")
            )
        ),
        "b2_s3": bool(
            os.environ.get("B2_ACCESS_KEY_ID")
            and os.environ.get("B2_SECRET_ACCESS_KEY")
            and os.environ.get("B2_BUCKET")
            and os.environ.get("B2_S3_ENDPOINT")
        ),
    }


def metadata_backend_detected() -> dict[str, bool]:
    return {
        "admin_api": bool(os.environ.get("ADMIN_EMAIL") and os.environ.get("ADMIN_PASSWORD")),
        "mongodb": bool(os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")),
        "railway": bool(os.environ.get("RAILWAY_ENVIRONMENT_ID") or os.environ.get("RAILWAY_SERVICE_ID")),
    }


def browser_tooling_detected() -> dict[str, bool]:
    try:
        import playwright  # noqa: F401

        playwright_available = True
    except Exception:
        playwright_available = False
    return {"playwright": playwright_available}


def inventory_row(state: BookState) -> dict[str, Any]:
    inv = state.stage_results.get("inventory_queue", {})
    meta = inv.get("metadata", {})
    rights = inv.get("rights_metadata") if isinstance(inv.get("rights_metadata"), dict) else {}
    return {
        "slug": state.slug,
        "title": state.title,
        "author": state.author,
        "language": state.language,
        "classifications": "|".join(state.classifications),
        "reader_ready": meta.get("reader_ready"),
        "rights_metadata_status": meta.get("rights_metadata_status") or rights.get("status"),
        "rights_metadata_ready": meta.get("rights_metadata_ready") or rights.get("production_metadata_ready"),
        "rights_metadata_missing_fields": "|".join(str(item) for item in (meta.get("rights_metadata_missing_fields") or rights.get("missing_fields") or [])),
        "cover_status": inv.get("cover_status", {}).get("status"),
        "existing_audio": meta.get("existing_audio"),
        "production_endpoint_state": meta.get("production_endpoint_state"),
        "previous_evidence_path": meta.get("previous_evidence_path"),
    }


def dashboard_row(state: BookState) -> dict[str, Any]:
    terminal_status = state_terminal_status(state)
    rights_stage = state.stage_results.get("rights_metadata_preflight_queue", {})
    rights_report_path = rights_stage.get("rights_metadata_report") or rel(state.run_dir / "rights_metadata_report.json")
    metadata_stage = state.stage_results.get("metadata_publish_queue", {})
    metadata_artifacts = metadata_stage.get("artifacts") if isinstance(metadata_stage.get("artifacts"), dict) else {}
    metadata_metrics = metadata_stage.get("metrics") if isinstance(metadata_stage.get("metrics"), dict) else {}
    metadata_updated = metadata_stage.get("updated_fields") if isinstance(metadata_stage.get("updated_fields"), dict) else {}
    browser_stage = state.stage_results.get("browser_gate_queue", {})
    tts_stage_result = state.stage_results.get("tts_queue", {})
    tts_metrics = tts_stage_result.get("metrics") if isinstance(tts_stage_result.get("metrics"), dict) else {}
    tts_artifacts = tts_stage_result.get("artifacts") if isinstance(tts_stage_result.get("artifacts"), dict) else {}
    stale_remote = tts_artifacts.get("stale_remote_audio") if isinstance(tts_artifacts.get("stale_remote_audio"), dict) else {}
    stale_metrics = stale_remote.get("metrics") if isinstance(stale_remote.get("metrics"), dict) else {}
    asr_stage_result = state.stage_results.get("asr_sync_queue", {})
    asr_metrics = asr_stage_result.get("metrics") if isinstance(asr_stage_result.get("metrics"), dict) else {}
    asr_updated = asr_stage_result.get("updated_fields") if isinstance(asr_stage_result.get("updated_fields"), dict) else {}
    asr_artifacts = asr_stage_result.get("artifacts") if isinstance(asr_stage_result.get("artifacts"), dict) else {}
    listening_report_path_value = (
        asr_updated.get("listening_quality_report_path")
        or asr_metrics.get("listening_quality_report")
        or asr_artifacts.get("listening_quality_report")
        or rel(state.run_dir / "listening_quality_report.json")
    )
    listening_report_path = ROOT / listening_report_path_value if listening_report_path_value and not Path(str(listening_report_path_value)).is_absolute() else Path(str(listening_report_path_value or ""))
    listening_report = read_json(listening_report_path, {}) if listening_report_path_value else {}
    listening_quality = listening_report.get("listening_quality") if isinstance(listening_report.get("listening_quality"), dict) else {}
    listening_aggregate = listening_quality.get("aggregate") if isinstance(listening_quality.get("aggregate"), dict) else {}
    return {
        "slug": state.slug,
        "title": state.title,
        "author": state.author,
        "language": state.language,
        "catalog_order": state.order,
        "inventory_seen": state_inventory_seen(state),
        "book_attempted": state_book_attempted(state),
        "real_stage_started_count": len(state.stage_started_events),
        "terminal_status": terminal_status,
        "terminal_at": state.terminal_at,
        "ready": state.ready,
        "published": state.published,
        "current_stage": state.next_stage,
        "current_lane": lane_for_stage(state.next_stage) if state.next_stage else "",
        "content_size_rank": "",
        "completed_lanes": "|".join(sorted({lane_for_stage(stage) for stage, result in state.stage_results.items() if isinstance(result, dict) and result.get("status") == "PASS"})),
        "blocked_lanes": "|".join(sorted({lane_for_stage(stage) for stage, result in state.stage_results.items() if isinstance(result, dict) and result.get("status") not in {None, "PASS"}} | ({"publish_barrier"} if any(item.get("category") == "release_order" for item in state.blockers) else set()))),
        "classifications": "|".join(state.classifications),
        "blocker_categories": "|".join(sorted({item["category"] for item in state.blockers})),
        "blockers": " || ".join(item["reason"] for item in state.blockers[:12]),
        "rights_metadata_status": rights_stage.get("rights_metadata_status") or metadata_updated.get("rights_metadata_status") or "",
        "rights_metadata_report_path": rights_report_path,
        "metadata_api_status": metadata_metrics.get("metadata_api_status") or metadata_stage.get("status") or "",
        "metadata_api_error": metadata_artifacts.get("metadata_api_error") or metadata_artifacts.get("admin_api_error") or "",
        "production_approval_attempted": metadata_updated.get("production_approval_attempted", False),
        "production_approval_succeeded": metadata_updated.get("production_approval_succeeded", False),
        "audiobook_endpoint_status": metadata_updated.get("audiobook_endpoint_status") or metadata_metrics.get("audiobook_endpoint_status") or "",
        "browser_gate_status": browser_stage.get("status") or "",
        "paid_tts_approval_detected": tts_metrics.get("paid_tts_approval_detected", ""),
        "tts_budget_limit": tts_metrics.get("tts_budget_limit", ""),
        "tts_estimated_cost": tts_metrics.get("tts_estimated_cost", ""),
        "tts_actual_cost_if_available": tts_metrics.get("tts_actual_cost_if_available", ""),
        "audio_url_404": bool(tts_metrics.get("audio_url_404") or stale_metrics.get("audio_url_404")),
        "local_audio_reused": bool(tts_metrics.get("local_audio_reused") or tts_artifacts.get("local_audio_reused")),
        "audio_regenerated": bool(tts_metrics.get("audio_regenerated")),
        "sidecars_need_rebuild": bool(tts_metrics.get("sidecars_need_rebuild") or tts_artifacts.get("sidecars_need_rebuild")),
        "tts_hook_status": tts_stage_result.get("status", ""),
        "tts_blocker_category": tts_stage_result.get("blocker_category", ""),
        "raw_asr_script": asr_updated.get("raw_asr_script") or asr_metrics.get("raw_asr_script") or "",
        "raw_asr_score": asr_updated.get("raw_asr_score") or asr_metrics.get("score") or "",
        "normalized_asr_score": asr_updated.get("normalized_asr_score") or asr_metrics.get("normalized_asr_score") or "",
        "phonetic_projection_score": asr_updated.get("phonetic_projection_score") or asr_metrics.get("phonetic_projection_score") or "",
        "projection_confidence": asr_updated.get("projection_confidence") or asr_metrics.get("projection_confidence") or "",
        "bengali_asr_lane_used": asr_updated.get("bengali_asr_lane_used") if "bengali_asr_lane_used" in asr_updated else asr_metrics.get("bengali_asr_lane_used", ""),
        "bengali_asr_lane_status": asr_updated.get("bengali_asr_lane_status") or asr_metrics.get("bengali_asr_lane_status") or "",
        "bengali_asr_diagnosis_path": asr_updated.get("bengali_asr_diagnosis_path") or asr_metrics.get("bengali_asr_diagnosis_path") or asr_artifacts.get("bengali_asr_mismatch_diagnosis") or "",
        "listening_qa_status": asr_updated.get("listening_qa_status") or asr_metrics.get("listening_qa_status") or listening_quality.get("status") or "",
        "listening_quality_report_path": listening_report_path_value if listening_report_path.exists() else "",
        "naturalness_score": listening_aggregate.get("naturalness_score", ""),
        "pronunciation_score": listening_aggregate.get("pronunciation_score", ""),
        "emotional_expression_score": listening_aggregate.get("emotional_expression_score", ""),
        "punctuation_pause_score": listening_aggregate.get("punctuation_pause_score", ""),
        "pacing_score": listening_aggregate.get("pacing_score", ""),
        "continuity_score": listening_aggregate.get("continuity_score", ""),
        "anti_robotic_texture_score": listening_aggregate.get("anti_robotic_texture_score", ""),
        "anti_choppy_join_score": listening_aggregate.get("anti_choppy_join_score", ""),
        "listener_enjoyment_score": listening_aggregate.get("listener_enjoyment_score", ""),
        "overall_listening_score": listening_aggregate.get("overall_listening_score", ""),
        "listening_confidence_score": listening_aggregate.get("confidence_score", ""),
        "listening_qa_schema_version": listening_report.get("qa_schema_version", ""),
        "listening_qa_blocker_reason": " || ".join(str(item) for item in listening_quality.get("blockers", [])[:8]) if listening_quality else "",
        "run_dir": rel(state.run_dir),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def dashboard_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Catalog Release Dashboard",
        "",
        f"- Run: `{summary['run_id']}`",
        f"- Total unique books: `{summary['total_unique_books']}`",
        f"- Exact unique title count: `{summary.get('exact_unique_title_count', summary['total_unique_books'])}`",
        f"- Content-size ordering status: `{summary.get('content_size_ordering_status', '')}`",
        f"- Next publishable slug: `{summary.get('next_publishable_slug') or ''}`",
        f"- Next publishable content-size rank: `{summary.get('next_publishable_content_size_rank') or ''}`",
        f"- Ranking path: `{summary.get('ranking_path') or ''}`",
        f"- Cost forecast path: `{summary.get('cost_forecast_path') or ''}`",
        f"- Inventory seen count: `{summary.get('inventory_seen_count', 0)}`",
        f"- Stage started count: `{summary.get('stage_started_count', 0)}`",
        f"- Book attempted count: `{summary.get('book_attempted_count', 0)}`",
        f"- Terminal book count: `{summary.get('terminal_book_count', 0)}`",
        f"- Published count: `{summary.get('published_count', 0)}`",
        f"- Published this run: `{summary['books_published_this_run']}`",
        f"- Total published: `{summary.get('total_published', summary['books_published_this_run'])}`",
        f"- Published titles: `{', '.join(summary.get('published_titles', []))}`",
        f"- Fully go-live ready: `{summary['books_fully_go_live_ready']}`",
        f"- Blocked: `{summary['books_blocked']}`",
        f"- Blockers by category: `{json.dumps(summary['blockers_by_category'], ensure_ascii=False)}`",
        f"- Active lane counts: `{json.dumps(summary.get('active_lane_counts', {}), ensure_ascii=False)}`",
        f"- Queued by lane: `{json.dumps(summary.get('queued_by_lane', {}), ensure_ascii=False)}`",
        f"- Completed by lane: `{json.dumps(summary.get('completed_by_lane', {}), ensure_ascii=False)}`",
        f"- Blocked by lane: `{json.dumps(summary.get('blocked_by_lane', {}), ensure_ascii=False)}`",
        f"- Paid operations queued: `{summary.get('paid_operations_queued', 0)}`",
        f"- Paid operations running: `{summary.get('paid_operations_running', 0)}`",
        f"- Ready waiting on publish barrier: `{summary.get('ready_waiting_on_publish_barrier', 0)}`",
        f"- Terminal blockers skipped by order policy: `{summary.get('terminal_blockers_skipped_by_order_policy', 0)}`",
        f"- Books prepared but not published: `{summary.get('books_prepared_but_not_published', 0)}`",
        f"- Current bottleneck lane: `{summary.get('current_bottleneck_lane', '')}`",
        f"- Blocked by rights metadata missing: `{summary.get('blocked_by_rights_metadata_missing', 0)}`",
        f"- Blocked by rights evidence incomplete: `{summary.get('blocked_by_rights_evidence_incomplete', 0)}`",
        f"- Blocked by metadata API rejection: `{summary.get('blocked_by_metadata_api_rejection', 0)}`",
        f"- Blocked by production DB schema mismatch: `{summary.get('blocked_by_production_db_schema_mismatch', 0)}`",
        f"- Blocked by stale audio URL: `{summary.get('blocked_by_stale_audio_url', 0)}`",
        f"- Blocked by missing local audio: `{summary.get('blocked_by_missing_local_audio', 0)}`",
        f"- Blocked by paid TTS approval required: `{summary.get('blocked_by_paid_tts_approval_required', 0)}`",
        f"- Blocked by TTS generation failure: `{summary.get('blocked_by_tts_generation_failure', 0)}`",
        f"- Blocked by audio QA failure: `{summary.get('blocked_by_audio_qa_failure', 0)}`",
        f"- Blocked by audio provider quality limit: `{summary.get('blocked_by_audio_provider_quality_limit', 0)}`",
        f"- Blocked by listening QA schema missing: `{summary.get('blocked_by_listening_qa_schema_missing', 0)}`",
        f"- Blocked by listening QA not run: `{summary.get('blocked_by_listening_qa_not_run', 0)}`",
        f"- Blocked by audio listening quality failed: `{summary.get('blocked_by_audio_listening_quality_failed', 0)}`",
        f"- Blocked by stale sidecars: `{summary.get('blocked_by_stale_sidecars', 0)}`",
        f"- Blocked by Bengali ASR script mismatch: `{summary.get('blocked_by_bengali_asr_script_mismatch', 0)}`",
        f"- Blocked by Bengali ASR low confidence: `{summary.get('blocked_by_bengali_asr_low_confidence', 0)}`",
        f"- Blocked by Bengali audio/manuscript mismatch: `{summary.get('blocked_by_bengali_audio_manuscript_mismatch', 0)}`",
        f"- Blocked by Bengali sync regeneration required: `{summary.get('blocked_by_bengali_sync_regeneration_required', 0)}`",
        f"- Blocked by Bengali audio provider quality: `{summary.get('blocked_by_bengali_audio_provider_quality', 0)}`",
        f"- Audio URL 404 count: `{summary.get('audio_url_404_count', 0)}`",
        f"- Local audio reused count: `{summary.get('local_audio_reused_count', 0)}`",
        f"- Audio regenerated count: `{summary.get('audio_regenerated_count', 0)}`",
        f"- Paid TTS approval detected: `{summary.get('paid_tts_approval_detected', False)}`",
        f"- TTS budget limit: `{summary.get('tts_budget_limit', '')}`",
        f"- TTS estimated cost: `{summary.get('tts_estimated_cost', 0)}`",
        f"- Stop guard triggered: `{summary.get('stop_guard_triggered', False)}`",
        f"- Stop guard reason: `{summary.get('stop_guard_reason') or ''}`",
        f"- Stop guard counter: `{summary.get('stop_guard_counter_used') or ''}` = `{summary.get('stop_guard_counter_value', 0)}` / `{summary.get('stop_guard_limit', 0)}`",
        "",
        "| Slug | Language | Lane | Attempted | Terminal | Ready | Published | Blockers |",
        "|---|---:|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"| `{row['slug']}` | {row['language']} | {row.get('current_lane') or ''} | {row['book_attempted']} | {row['terminal_status']} | {row['ready']} | {row['published']} | {row['blocker_categories']} |")
    return "\n".join(lines) + "\n"


def print_dashboard_table(summary: dict[str, Any], catalog_dir: Path) -> None:
    blocked = summary["blockers_by_category"]
    rows = [
        ("hooks configured", summary.get("hook_config_status", "")),
        ("hook source", summary.get("hook_source", "")),
        ("hook validation status", summary.get("hook_validation_status", "")),
        ("background worker status", summary.get("background_worker_status", "")),
        ("pid file", summary.get("pid_file", "")),
        ("heartbeat path", summary.get("heartbeat_path", "")),
        ("total unique books", summary["total_unique_books"]),
        ("exact unique title count", summary.get("exact_unique_title_count", summary["total_unique_books"])),
        ("content-size ordering status", summary.get("content_size_ordering_status", "")),
        ("next publishable slug", summary.get("next_publishable_slug") or ""),
        ("next publishable content-size rank", summary.get("next_publishable_content_size_rank") or ""),
        ("smallest 10 books by rank", ", ".join(str(item.get("slug")) for item in summary.get("smallest_10_books_by_rank", [])[:10])),
        ("active lane counts", json.dumps(summary.get("active_lane_counts", {}), ensure_ascii=False)),
        ("queued by lane", json.dumps(summary.get("queued_by_lane", {}), ensure_ascii=False)),
        ("completed by lane", json.dumps(summary.get("completed_by_lane", {}), ensure_ascii=False)),
        ("blocked by lane", json.dumps(summary.get("blocked_by_lane", {}), ensure_ascii=False)),
        ("paid operations queued", summary.get("paid_operations_queued", 0)),
        ("paid operations running", summary.get("paid_operations_running", 0)),
        ("ready waiting on publish barrier", summary.get("ready_waiting_on_publish_barrier", 0)),
        ("terminal blockers skipped by order policy", summary.get("terminal_blockers_skipped_by_order_policy", 0)),
        ("books prepared but not published", summary.get("books_prepared_but_not_published", 0)),
        ("current bottleneck lane", summary.get("current_bottleneck_lane", "")),
        ("inventory_seen_count", summary.get("inventory_seen_count", 0)),
        ("stage_started_count", summary.get("stage_started_count", 0)),
        ("book_attempted_count", summary.get("book_attempted_count", 0)),
        ("terminal_book_count", summary.get("terminal_book_count", 0)),
        ("published_count", summary.get("published_count", 0)),
        ("processed this wave", summary["processed_this_wave"]),
        ("published this run", summary["books_published_this_run"]),
        ("total published", summary.get("total_published", summary["books_published_this_run"])),
        ("ready but not deployed", summary["ready_but_not_published"]),
        ("blocked by covers", blocked.get("covers", 0)),
        ("blocked by manuscript", blocked.get("manuscript", 0)),
        ("blocked by TTS", blocked.get("tts", 0)),
        ("blocked by ASR/transcript", blocked.get("asr", 0)),
        ("blocked by sync", blocked.get("sync", 0)),
        ("blocked by QA", blocked.get("qa", 0)),
        ("blocked by upload/checksum", blocked.get("upload/checksum", 0)),
        ("blocked by metadata", blocked.get("metadata", 0)),
        ("blocked by rights metadata missing", summary.get("blocked_by_rights_metadata_missing", 0)),
        ("blocked by rights evidence incomplete", summary.get("blocked_by_rights_evidence_incomplete", 0)),
        ("blocked by metadata API rejection", summary.get("blocked_by_metadata_api_rejection", 0)),
        ("blocked by production DB schema mismatch", summary.get("blocked_by_production_db_schema_mismatch", 0)),
        ("blocked by stale audio URL", summary.get("blocked_by_stale_audio_url", 0)),
        ("blocked by missing local audio", summary.get("blocked_by_missing_local_audio", 0)),
        ("blocked by paid TTS approval required", summary.get("blocked_by_paid_tts_approval_required", 0)),
        ("blocked by TTS generation failure", summary.get("blocked_by_tts_generation_failure", 0)),
        ("blocked by audio QA failure", summary.get("blocked_by_audio_qa_failure", 0)),
        ("blocked by audio provider quality limit", summary.get("blocked_by_audio_provider_quality_limit", 0)),
        ("blocked by listening QA schema missing", summary.get("blocked_by_listening_qa_schema_missing", 0)),
        ("blocked by listening QA not run", summary.get("blocked_by_listening_qa_not_run", 0)),
        ("blocked by audio listening quality failed", summary.get("blocked_by_audio_listening_quality_failed", 0)),
        ("blocked by stale sidecars", summary.get("blocked_by_stale_sidecars", 0)),
        ("blocked by Bengali ASR script mismatch", summary.get("blocked_by_bengali_asr_script_mismatch", 0)),
        ("blocked by Bengali ASR low confidence", summary.get("blocked_by_bengali_asr_low_confidence", 0)),
        ("blocked by Bengali audio/manuscript mismatch", summary.get("blocked_by_bengali_audio_manuscript_mismatch", 0)),
        ("blocked by Bengali sync regeneration required", summary.get("blocked_by_bengali_sync_regeneration_required", 0)),
        ("blocked by Bengali audio provider quality", summary.get("blocked_by_bengali_audio_provider_quality", 0)),
        ("paid_tts_approval_detected", summary.get("paid_tts_approval_detected", False)),
        ("tts_budget_limit", summary.get("tts_budget_limit", "")),
        ("tts_estimated_cost", summary.get("tts_estimated_cost", 0)),
        ("tts_actual_cost_if_available", summary.get("tts_actual_cost_if_available", "not_available")),
        ("audio_url_404_count", summary.get("audio_url_404_count", 0)),
        ("local_audio_reused_count", summary.get("local_audio_reused_count", 0)),
        ("audio_regenerated_count", summary.get("audio_regenerated_count", 0)),
        ("tts_paid_approval_required_count", summary.get("tts_paid_approval_required_count", 0)),
        ("blocked by browser", blocked.get("browser", 0)),
        ("stop_guard_triggered", summary.get("stop_guard_triggered", False)),
        ("stop_guard_reason", summary.get("stop_guard_reason") or summary.get("stop_reason") or ""),
        ("stop_guard_counter_used", summary.get("stop_guard_counter_used") or ""),
        ("stop_guard_counter_value", summary.get("stop_guard_counter_value", 0)),
        ("stop_guard_limit", summary.get("stop_guard_limit", 0)),
        ("ranking path", summary.get("ranking_path") or ""),
        ("cost forecast path", summary.get("cost_forecast_path") or ""),
        ("artifact dashboard paths", f"{rel(catalog_dir / 'catalog_release_dashboard.json')} | {rel(catalog_dir / 'catalog_release_dashboard.csv')} | {rel(catalog_dir / 'catalog_release_dashboard.md')}"),
        ("next exact command to resume", summary.get("next_recommended_resume_command") or f"python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest {rel(DEFAULT_MANIFEST)} --languages eng,ben --max-books-active 8 --max-tts-workers 3 --max-asr-workers 3 --max-cover-workers 2 --max-browser-workers 2 --max-attempts 4 --resume --fail-closed"),
    ]
    width = max(len(label) for label, _ in rows)
    for label, value in rows:
        print(f"{label:<{width}}  {value}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--slugs", default="")
    parser.add_argument("--languages", default="eng,ben")
    parser.add_argument("--max-books-active", type=int, default=8)
    parser.add_argument("--max-preflight-workers", type=int, default=0)
    parser.add_argument("--max-audio-reuse-workers", type=int, default=0)
    parser.add_argument("--max-tts-workers", type=int, default=3)
    parser.add_argument("--max-paid-workers", type=int, default=0)
    parser.add_argument("--max-asr-workers", type=int, default=3)
    parser.add_argument("--max-cover-workers", type=int, default=2)
    parser.add_argument("--max-upload-workers", type=int, default=0)
    parser.add_argument("--max-metadata-workers", type=int, default=0)
    parser.add_argument("--max-browser-workers", type=int, default=2)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--publish-approved", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--fail-closed", action="store_true")
    parser.add_argument("--wave-size", type=int, default=0)
    parser.add_argument("--priority", choices=["canonical", "ready-first"], default="canonical")
    parser.add_argument("--order-by", choices=["canonical", "content-size"], default="canonical")
    parser.add_argument("--release-order", choices=["canonical", "ascending-content-size"], default="canonical")
    parser.add_argument("--enforce-release-order", action="store_true")
    parser.add_argument("--allow-blocked-order-skip", action="store_true")
    parser.add_argument("--max-order-block-wait-minutes", type=float, default=0)
    parser.add_argument("--exclude-slugs", default="")
    parser.add_argument("--include-status", default="")
    parser.add_argument("--stop-after-published", type=int, default=0)
    parser.add_argument("--stop-after-attempted", type=int, default=0)
    parser.add_argument("--stop-after-terminal-books", type=int, default=0)
    parser.add_argument("--max-run-minutes", type=float, default=0)
    parser.add_argument("--validate-hooks", action="store_true")
    parser.add_argument("--print-hook-plan", action="store_true")
    parser.add_argument("--require-explicit-hooks", nargs="?", const="true", default="false")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--daemon-log", default="")
    parser.add_argument("--heartbeat-seconds", type=int, default=60)
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--tail-status", action="store_true")
    parser.add_argument("--write-pid-file", default="")
    parser.add_argument("--resume-from-latest", action="store_true")
    parser.add_argument("--catalog-run-dir", default="")
    args = parser.parse_args(argv)
    args.require_explicit_hooks = parse_bool_arg(args.require_explicit_hooks)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    factory = ReleaseCatalogFactory(args)
    return factory.run()


if __name__ == "__main__":
    raise SystemExit(main())
