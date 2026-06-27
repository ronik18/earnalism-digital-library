#!/usr/bin/env python3
"""Guarded Book Factory orchestration for Earnalism book/audiobook prep.

The factory is intentionally conservative: dry-run/status modes are the
default, paid provider generation is delegated to the existing ElevenLabs
pipeline with its env gates, and public audio remains blocked unless a future
release gate explicitly approves it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.elevenlabs_full_chapter_generate import (  # noqa: E402
    DEFAULT_CONCURRENCY,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BASE_SECONDS,
    DEFAULT_RETRY_MAX_SECONDS,
    GenerationSafetyError,
    run_generation as run_elevenlabs_generation,
)


PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
PRODUCTION_BLOCKED = "PRODUCTION_BLOCKED"
HOLD_SYNC_QA_REQUIRED = "HOLD_SYNC_QA_REQUIRED"
INTERNAL_AUDIOBOOK_ROOT = ROOT / "internal" / "audiobook_lab"
DEFAULT_OUTPUT_ROOT = ROOT / "output" / "onboarding"
DEFAULT_CONFIG_PATH = ROOT / "onboarding" / "books" / "dracula.yml"
PUBLIC_PATHS = (ROOT / "frontend" / "public", ROOT / "frontend" / "build")
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}

BOOK_FACTORY_AUDIOBOOK_STAGES = (
    "AUDIOBOOK_CHUNK_HASHING",
    "AUDIOBOOK_CACHE_LOOKUP",
    "AUDIOBOOK_TTS_GENERATION",
    "AUDIOBOOK_ALIGNMENT_IMPORT",
    "AUDIOBOOK_SYNC_MANIFEST",
    "AUDIOBOOK_INTERNAL_PLAYER_PREP",
    "AUDIOBOOK_QA_GATE",
)


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FactoryResult:
    config_path: str
    mode: str
    book_slug: str
    generated_at: str
    audiobook: dict[str, Any]
    stages: list[StageResult]
    reports: dict[str, str]
    final_gate: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "unknown-book"


def scalar_value(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    lowered = value.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered in {"null", "none"}:
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def load_yaml_like_config(path: Path) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]
    lines = path.read_text(encoding="utf-8").splitlines()

    def next_meaningful_line(start_index: int) -> tuple[int, str] | None:
        for candidate in lines[start_index + 1 :]:
            if not candidate.strip() or candidate.lstrip().startswith("#"):
                continue
            return len(candidate) - len(candidate.lstrip(" ")), candidate.strip()
        return None

    for index, raw_line in enumerate(lines):
        line_number = index + 1
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            raise ValueError(f"{path}:{line_number}: tabs are not supported.")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        text = raw_line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"{path}:{line_number}: list item has no list parent.")
            parent.append(scalar_value(text[2:]))
            continue
        if ":" not in text:
            raise ValueError(f"{path}:{line_number}: expected key: value syntax.")
        key, raw_value = text.split(":", 1)
        key = key.strip()
        if not isinstance(parent, dict):
            raise ValueError(f"{path}:{line_number}: mapping key cannot be nested inside a scalar list.")
        if raw_value.strip():
            parent[key] = scalar_value(raw_value)
            continue
        next_line = next_meaningful_line(index)
        if next_line and next_line[0] > indent and next_line[1].startswith("- "):
            child_list: list[Any] = []
            parent[key] = child_list
            stack.append((indent, child_list))
        elif next_line and next_line[0] > indent:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = ""
    return root


def read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Book factory config not found: {path}")
    data = load_yaml_like_config(path)
    if not isinstance(data, dict):
        raise ValueError("Book factory config must be a mapping.")
    return data


def ensure_internal_path(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(INTERNAL_AUDIOBOOK_ROOT.resolve())
    except ValueError as exc:
        raise GenerationSafetyError(f"{label} must stay under internal/audiobook_lab") from exc
    for public_path in PUBLIC_PATHS:
        try:
            resolved.relative_to(public_path.resolve())
        except ValueError:
            continue
        raise GenerationSafetyError(f"{label} must never point to frontend/public or frontend/build")
    return resolved


def reject_public_audio_files() -> list[str]:
    found: list[str] = []
    for root in PUBLIC_PATHS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                found.append(str(path.relative_to(ROOT)))
    return found


def normalize_audiobook_config(config: dict[str, Any], *, mode: str, scope_override: str | None) -> dict[str, Any]:
    raw = config.get("audiobook") if isinstance(config.get("audiobook"), dict) else {}
    retry_policy = raw.get("retry_policy") if isinstance(raw.get("retry_policy"), dict) else {}
    provider = str(raw.get("provider") or raw.get("audiobook_provider") or "elevenlabs").strip().lower()
    scope = str(scope_override or raw.get("scope") or raw.get("audiobook_scope") or "chapter_1").strip()
    selected_chapters = raw.get("selected_chapters")
    if selected_chapters is None or selected_chapters == "":
        selected_chapters = [1]
    if not isinstance(selected_chapters, list):
        selected_chapters = [selected_chapters]
    generation_mode = str(raw.get("generation_mode") or mode).replace("-", "_")
    if mode == "generate":
        generation_mode = "generate"
    if mode == "dry-run":
        generation_mode = "dry_run"
    return {
        "provider": provider,
        "voice_id": str(raw.get("voice_id") or raw.get("selected_voice_id") or "21m00Tcm4TlvDq8ikWAM"),
        "voice_name": str(raw.get("voice_name") or raw.get("selected_voice_display_name") or "Rachel"),
        "model_id": str(raw.get("model_id") or "eleven_multilingual_v2"),
        "output_format": str(raw.get("output_format") or "mp3_44100_192"),
        "generation_mode": generation_mode,
        "scope": scope,
        "selected_chapters": [int(chapter) for chapter in selected_chapters if str(chapter).strip()],
        "concurrency": int(raw.get("concurrency") or DEFAULT_CONCURRENCY),
        "max_concurrency": int(raw.get("max_concurrency") or DEFAULT_MAX_CONCURRENCY),
        "retry_policy": {
            "max_retries": int(retry_policy.get("max_retries") or DEFAULT_MAX_RETRIES),
            "retry_base_seconds": float(retry_policy.get("retry_base_seconds") or DEFAULT_RETRY_BASE_SECONDS),
            "retry_max_seconds": float(retry_policy.get("retry_max_seconds") or DEFAULT_RETRY_MAX_SECONDS),
        },
        "cache_enabled": bool(raw.get("cache_enabled", True)),
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
    }


def generation_selector(audiobook: dict[str, Any]) -> tuple[int, str, int | None]:
    scope = audiobook["scope"]
    chapters = audiobook.get("selected_chapters") or [1]
    chapter = int(chapters[0])
    if scope == "none":
        return chapter, "one", 0
    if scope in {"chapter_1", "selected_chapters"}:
        return chapter, "all", None
    if scope == "full_book":
        return chapter, "all", None
    raise GenerationSafetyError(f"Unsupported audiobook scope: {scope}")


def result_stage_details(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_count": result.get("chunk_count", 0),
        "total_characters": result.get("total_characters", 0),
        "generated_chunk_count": result.get("generated_chunk_count", 0),
        "skipped_cached_chunk_count": result.get("skipped_cached_chunk_count", 0),
        "cache_hit_count": result.get("cache_hit_count", 0),
        "cache_miss_count": result.get("cache_miss_count", 0),
        "cache_stale_count": result.get("cache_stale_count", 0),
        "failed_chunk_count": result.get("failed_chunk_count", 0),
        "retry_count": result.get("retry_count", 0),
        "concurrency": result.get("concurrency", 1),
        "elapsed_seconds": result.get("elapsed_seconds", 0),
        "chunk_generation_manifest_path": result.get("chunk_generation_manifest_path", ""),
        "cache_manifest_path": result.get("cache_manifest_path", ""),
        "sync_manifest_path": result.get("sync_manifest_path", ""),
        "full_chapter_audio_manifest_path": result.get("full_chapter_audio_manifest_path", ""),
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
    }


def build_stages_from_generation(
    *,
    audiobook: dict[str, Any],
    result: dict[str, Any] | None,
    generation_status: str,
    blockers: list[str] | None = None,
) -> list[StageResult]:
    blockers = blockers or []
    details = result_stage_details(result or {})
    details.update(
        {
            "provider": audiobook["provider"],
            "voice_id": audiobook["voice_id"],
            "voice_name": audiobook["voice_name"],
            "model_id": audiobook["model_id"],
            "output_format": audiobook["output_format"],
            "generation_mode": audiobook["generation_mode"],
            "scope": audiobook["scope"],
            "cache_enabled": audiobook["cache_enabled"],
        }
    )
    hash_status = "PASS" if result else ("SKIPPED" if audiobook["scope"] == "none" else "BLOCKED")
    cache_status = "PASS" if result else ("SKIPPED" if audiobook["scope"] == "none" else "BLOCKED")
    tts_status = generation_status if not blockers else "BLOCKED"
    failed = int(details.get("failed_chunk_count") or 0)
    generated_or_reused = int(details.get("generated_chunk_count") or 0) + int(details.get("skipped_cached_chunk_count") or 0)
    sync_status = HOLD_SYNC_QA_REQUIRED
    return [
        StageResult("AUDIOBOOK_CHUNK_HASHING", hash_status, blockers if hash_status == "BLOCKED" else [], details=details),
        StageResult("AUDIOBOOK_CACHE_LOOKUP", cache_status, blockers if cache_status == "BLOCKED" else [], details=details),
        StageResult(
            "AUDIOBOOK_TTS_GENERATION",
            tts_status,
            blockers,
            details={**details, "provider_api_called": int(details.get("generated_chunk_count") or 0) > 0},
        ),
        StageResult("AUDIOBOOK_ALIGNMENT_IMPORT", "HOLD_SYNC_QA_REQUIRED", details=details),
        StageResult("AUDIOBOOK_SYNC_MANIFEST", sync_status, details=details),
        StageResult(
            "AUDIOBOOK_INTERNAL_PLAYER_PREP",
            "READY_INTERNAL_PLAYER_TEST" if result and generated_or_reused and not failed else "HOLD_INTERNAL_PLAYER_PREP",
            details=details,
        ),
        StageResult(
            "AUDIOBOOK_QA_GATE",
            "HOLD_AUDIO_QA" if failed else "HOLD_SYNC_QA",
            ["owner listening QA and sync QA are required before public release."],
            details={**details, "listen_now_cta_allowed": False, "audio_object_metadata_allowed": False},
        ),
    ]


def run_factory(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    mode: str = "dry-run",
    scope: str | None = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    generator_fn: Callable[..., dict[str, Any]] = run_elevenlabs_generation,
) -> FactoryResult:
    config = read_config(config_path)
    slug = safe_slug(config.get("book_slug") or config.get("slug"))
    audiobook = normalize_audiobook_config(config, mode=mode, scope_override=scope)
    public_audio = reject_public_audio_files()
    result: dict[str, Any] | None = None
    generation_status = "SKIPPED"
    blockers: list[str] = []
    if public_audio:
        blockers.append("public audio files are present under frontend/public or frontend/build.")
    if audiobook["provider"] != "elevenlabs" and audiobook["scope"] != "none":
        blockers.append("book factory audiobook automation currently supports elevenlabs only.")
    if audiobook["scope"] != "none" and not blockers and mode != "status":
        chapter, chunks, max_chunks = generation_selector(audiobook)
        if chunks == "all":
            expected_dir = INTERNAL_AUDIOBOOK_ROOT / slug / "en" / f"chapter-{chapter}" / "manual_elevenlabs_chunks"
            if expected_dir.exists():
                try:
                    expected = json.loads((expected_dir / "expected_audio_filenames.json").read_text(encoding="utf-8"))
                    max_chunks = len(expected.get("chunks", [])) or max_chunks
                except (OSError, json.JSONDecodeError):
                    max_chunks = max_chunks
        output_dir = ensure_internal_path(
            INTERNAL_AUDIOBOOK_ROOT / slug / "en" / f"chapter-{chapter}" / "generated_audio",
            "book factory generated audio output",
        )
        config_file = ensure_internal_path(
            INTERNAL_AUDIOBOOK_ROOT / slug / "en" / f"chapter-{chapter}" / "elevenlabs_api_generation_config.json",
            "book factory ElevenLabs config",
        )
        try:
            result = generator_fn(
                book_slug=slug,
                language="en",
                chapter=chapter,
                mode="generate" if audiobook["generation_mode"] == "generate" else "dry-run",
                chunks=chunks,
                max_chunks=max_chunks,
                force=audiobook["generation_mode"] == "generate" and chunks == "all",
                output_dir=output_dir,
                config_path=config_file,
                concurrency=audiobook["concurrency"],
                max_concurrency=audiobook["max_concurrency"],
                max_retries=audiobook["retry_policy"]["max_retries"],
                retry_base_seconds=audiobook["retry_policy"]["retry_base_seconds"],
                retry_max_seconds=audiobook["retry_policy"]["retry_max_seconds"],
                resume_failed=mode == "generate",
            )
            generation_status = str(result.get("status") or "DRY_RUN_READY")
        except GenerationSafetyError as exc:
            blockers.append(str(exc))
            generation_status = "BLOCKED"
    elif mode == "status":
        generation_status = "STATUS_ONLY"

    stages = build_stages_from_generation(
        audiobook=audiobook,
        result=result,
        generation_status=generation_status,
        blockers=blockers,
    )
    final_gate = {
        "status": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "listen_now_cta_allowed": False,
        "audio_object_metadata_allowed": False,
        "public_audio_publish_allowed": False,
        "release_gate": "HOLD_AUDIO_QA" if blockers else "HOLD_SYNC_QA",
        "blockers": blockers + ["owner listening QA, sync QA, accessibility QA, legal review, and release approval are required."],
    }
    result_obj = FactoryResult(
        config_path=str(config_path.relative_to(ROOT) if config_path.is_relative_to(ROOT) else config_path),
        mode=mode,
        book_slug=slug,
        generated_at=utc_now(),
        audiobook=audiobook,
        stages=stages,
        reports={},
        final_gate=final_gate,
    )
    reports = write_reports(result_obj, output_root)
    return FactoryResult(
        config_path=result_obj.config_path,
        mode=result_obj.mode,
        book_slug=result_obj.book_slug,
        generated_at=result_obj.generated_at,
        audiobook=result_obj.audiobook,
        stages=result_obj.stages,
        reports=reports,
        final_gate=result_obj.final_gate,
    )


def stage_payload(stage: StageResult) -> dict[str, Any]:
    return {
        "name": stage.name,
        "status": stage.status,
        "blockers": stage.blockers,
        "warnings": stage.warnings,
        "details": stage.details,
    }


def result_payload(result: FactoryResult) -> dict[str, Any]:
    return {
        "generated_by": "scripts/orchestrate_book_factory.py",
        "generated_at": result.generated_at,
        "config_path": result.config_path,
        "mode": result.mode,
        "book_slug": result.book_slug,
        "audiobook": result.audiobook,
        "stages": [stage_payload(stage) for stage in result.stages],
        "final_gate": result.final_gate,
        "reports": result.reports,
    }


def markdown_stage_table(result: FactoryResult) -> str:
    lines = ["| Stage | Status | Blockers |", "| --- | --- | --- |"]
    for stage in result.stages:
        blocker_text = "; ".join(stage.blockers) if stage.blockers else "none"
        lines.append(f"| `{stage.name}` | `{stage.status}` | {blocker_text} |")
    return "\n".join(lines)


def write_reports(result: FactoryResult, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, str]:
    output_dir = output_root / result.book_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = result_payload(result)
    report_paths = {
        "BOOK_FACTORY_AUDIOBOOK_STAGE_REPORT.md": output_dir / "BOOK_FACTORY_AUDIOBOOK_STAGE_REPORT.md",
        "BOOK_FACTORY_AUDIOBOOK_CACHE_REPORT.md": output_dir / "BOOK_FACTORY_AUDIOBOOK_CACHE_REPORT.md",
        "BOOK_FACTORY_AUDIOBOOK_GENERATION_REPORT.md": output_dir / "BOOK_FACTORY_AUDIOBOOK_GENERATION_REPORT.md",
        "BOOK_FACTORY_AUDIOBOOK_RELEASE_GATE_REPORT.md": output_dir / "BOOK_FACTORY_AUDIOBOOK_RELEASE_GATE_REPORT.md",
        "book_factory_audiobook_report.json": output_dir / "book_factory_audiobook_report.json",
    }
    report_paths["book_factory_audiobook_report.json"].write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    stage_report = "\n".join(
        [
            "# Book Factory Audiobook Stage Report",
            "",
            f"- Book slug: `{result.book_slug}`",
            f"- Mode: `{result.mode}`",
            f"- Provider: `{result.audiobook['provider']}`",
            f"- Scope: `{result.audiobook['scope']}`",
            "",
            markdown_stage_table(result),
            "",
            "- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
            "- Production: `PRODUCTION_BLOCKED`",
            "- Listen Now CTA allowed: `false`",
            "- AudioObject metadata allowed: `false`",
            "",
        ]
    )
    cache_stage = next(stage for stage in result.stages if stage.name == "AUDIOBOOK_CACHE_LOOKUP")
    cache_report = "\n".join(
        [
            "# Book Factory Audiobook Cache Report",
            "",
            f"- Cache enabled: `{str(result.audiobook['cache_enabled']).lower()}`",
            f"- Cache manifest: `{cache_stage.details.get('cache_manifest_path', '')}`",
            f"- Cache hits: `{cache_stage.details.get('cache_hit_count', 0)}`",
            f"- Cache misses: `{cache_stage.details.get('cache_miss_count', 0)}`",
            f"- Cache stale entries: `{cache_stage.details.get('cache_stale_count', 0)}`",
            "- Cache audio remains internal under `internal/audiobook_lab/`.",
            "",
        ]
    )
    generation_stage = next(stage for stage in result.stages if stage.name == "AUDIOBOOK_TTS_GENERATION")
    generation_report = "\n".join(
        [
            "# Book Factory Audiobook Generation Report",
            "",
            f"- Generation mode: `{result.audiobook['generation_mode']}`",
            f"- Voice: `{result.audiobook['voice_name']} / {result.audiobook['voice_id']}`",
            f"- Model: `{result.audiobook['model_id']}`",
            f"- Output format: `{result.audiobook['output_format']}`",
            f"- Concurrency: `{generation_stage.details.get('concurrency', result.audiobook['concurrency'])}`",
            f"- Max retries: `{result.audiobook['retry_policy']['max_retries']}`",
            f"- Generated chunks: `{generation_stage.details.get('generated_chunk_count', 0)}`",
            f"- Skipped cached chunks: `{generation_stage.details.get('skipped_cached_chunk_count', 0)}`",
            f"- Failed chunks: `{generation_stage.details.get('failed_chunk_count', 0)}`",
            f"- Retry count: `{generation_stage.details.get('retry_count', 0)}`",
            f"- Provider API called: `{str(generation_stage.details.get('provider_api_called', False)).lower()}`",
            "- API key persisted: `false`",
            "",
        ]
    )
    release_report = "\n".join(
        [
            "# Book Factory Audiobook Release Gate Report",
            "",
            f"- Final status: `{result.final_gate['status']}`",
            "- Public audio allowed: `false`",
            "- Public audio publish allowed: `false`",
            "- Production status: `PRODUCTION_BLOCKED`",
            "- Listen Now CTA allowed: `false`",
            "- AudioObject metadata allowed: `false`",
            "",
            "## Blockers",
            "",
            *[f"- {blocker}" for blocker in result.final_gate["blockers"]],
            "",
        ]
    )
    report_paths["BOOK_FACTORY_AUDIOBOOK_STAGE_REPORT.md"].write_text(stage_report, encoding="utf-8")
    report_paths["BOOK_FACTORY_AUDIOBOOK_CACHE_REPORT.md"].write_text(cache_report, encoding="utf-8")
    report_paths["BOOK_FACTORY_AUDIOBOOK_GENERATION_REPORT.md"].write_text(generation_report, encoding="utf-8")
    report_paths["BOOK_FACTORY_AUDIOBOOK_RELEASE_GATE_REPORT.md"].write_text(release_report, encoding="utf-8")
    if output_root == DEFAULT_OUTPUT_ROOT:
        for name, path in report_paths.items():
            if name.endswith(".md"):
                (ROOT / name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return {str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path): str(path) for path in report_paths.values()}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--mode", choices=("dry-run", "generate", "status"), default="dry-run")
    parser.add_argument("--scope", choices=("none", "chapter_1", "selected_chapters", "full_book"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = ROOT / args.config if not args.config.is_absolute() else args.config
    output_root = ROOT / args.output_root if not args.output_root.is_absolute() else args.output_root
    try:
        result = run_factory(
            config_path=config_path,
            mode=args.mode,
            scope=args.scope,
            output_root=output_root,
        )
    except GenerationSafetyError as exc:
        print(f"BOOK_FACTORY_AUDIOBOOK_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(
        "BOOK_FACTORY_AUDIOBOOK "
        f"status={result.final_gate['status']} mode={result.mode} slug={result.book_slug} "
        f"stages={len(result.stages)} public_audio_allowed=false production_status={PRODUCTION_BLOCKED}"
    )
    for stage in result.stages:
        print(f"stage {stage.name} status={stage.status}")
    print(f"stage_report={result.reports.get('output/onboarding/' + result.book_slug + '/BOOK_FACTORY_AUDIOBOOK_STAGE_REPORT.md', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
