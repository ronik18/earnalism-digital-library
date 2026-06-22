#!/usr/bin/env python3
"""Internal audiobook generation and text-sync pipeline prototype.

The pipeline is intentionally local and dry-run first. It does not publish
audio, expose public audio URLs, call providers, download models, or write audio
files into public frontend directories.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTERNAL_ROOT = ROOT / "internal" / "audiobook_lab"
MODEL_CONFIG_PATH = ROOT / "audiobook" / "models" / "tts_model_candidates.yml"

PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
READY_FOR_INTERNAL_REVIEW = "READY_FOR_INTERNAL_REVIEW"
BLOCKED_GENERATE_INTERNAL = "BLOCKED_GENERATE_INTERNAL"
DRY_RUN_COMPLETE = "DRY_RUN_COMPLETE"
SYNC_LEVEL = "sentence"
SUPPORTED_LANGUAGES = {"en", "bn"}
AUDIO_FILE_EXTENSIONS = {".aac", ".m4a", ".mp3", ".ogg", ".wav"}

MODEL_CANDIDATES = {
    "kokoro": {
        "display_name": "Kokoro",
        "languages": ["en"],
        "license_status": "HOLD_LICENSE_REVIEW",
        "license_note": "Evaluate only after local commercial-use and model-card review.",
    },
    "melotts": {
        "display_name": "MeloTTS",
        "languages": ["en"],
        "license_status": "HOLD_LICENSE_REVIEW",
        "license_note": "Evaluate only after model, voice, and dependency license review.",
    },
    "piper": {
        "display_name": "Piper",
        "languages": ["en"],
        "license_status": "HOLD_GPL_CAUTION",
        "license_note": "GPL/license obligations require manual legal review before production use.",
    },
    "indic-parler-tts": {
        "display_name": "Indic Parler-TTS",
        "languages": ["bn", "en"],
        "license_status": "HOLD_LICENSE_REVIEW",
        "license_note": "Candidate for Bengali/English evaluation only after license and voice rights review.",
    },
    "styletts2": {
        "display_name": "StyleTTS2",
        "languages": ["en"],
        "license_status": "HOLD_LICENSE_REVIEW_ONLY",
        "license_note": "License-review candidate only; not approved for generation.",
    },
}


@dataclass(frozen=True)
class PipelineBlocker:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class PipelineResult:
    book_slug: str
    chapter: str
    language: str
    model_candidate: str
    mode: str
    status: str
    output_dir: Path
    generated_at: str
    source_hash: str
    sync_manifest_path: Path
    qa_packet_path: Path
    model_decision_path: Path
    release_gate_report_path: Path
    blockers: list[PipelineBlocker] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sync_items: list[dict[str, Any]] = field(default_factory=list)


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "unknown"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def html_to_text(value: str) -> str:
    text = re.sub(r"(?i)<br\\s*/?>", "\n", value)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chapter_path(book_slug: str, chapter: str) -> Path:
    chapter_number = int(str(chapter).strip())
    return ROOT / "data" / "controlled_publications" / book_slug / "chapters" / f"chapter-{chapter_number:03d}.json"


def load_source_text(book_slug: str, chapter: str, language: str) -> tuple[str, str, str]:
    if book_slug == "dracula" and language == "en":
        path = chapter_path(book_slug, chapter)
        payload = json.loads(path.read_text(encoding="utf-8"))
        chapter_id = str(payload.get("id") or f"chapter-{int(chapter):03d}")
        title = str(payload.get("title") or chapter_id)
        return chapter_id, title, html_to_text(str(payload.get("content", "")))
    if language == "bn":
        chapter_id = f"chapter-{int(chapter):03d}"
        title = "Internal Bengali audiobook planning sample"
        text = (
            "এটি একটি অভ্যন্তরীণ পরিকল্পনা নমুনা। "
            "জনসমক্ষে অডিও প্রকাশ করা হয়নি। "
            "মানব শ্রবণ পরীক্ষা, অধিকার যাচাই, এবং মালিক অনুমোদন ছাড়া প্রকাশ বন্ধ থাকবে।"
        )
        return chapter_id, title, text
    chapter_id = f"chapter-{int(chapter):03d}"
    return (
        chapter_id,
        "Internal English audiobook planning sample",
        "This is an internal audiobook synchronization planning sample. Public audio remains blocked.",
    )


def split_sentences(text: str, *, limit: int = 16) -> list[tuple[int, int, str]]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    fragments: list[tuple[int, int, str]] = []
    for paragraph_index, paragraph in enumerate(paragraphs):
        sentences = re.split(r"(?<=[.!?।])\s+", paragraph)
        for sentence_index, sentence in enumerate(sentences):
            cleaned = sentence.strip()
            if cleaned:
                fragments.append((paragraph_index, sentence_index, cleaned))
            if len(fragments) >= limit:
                return fragments
    return fragments


def deterministic_timing_ms(text: str) -> int:
    words = max(1, len(re.findall(r"\w+|[\u0980-\u09FF]+", text)))
    return max(900, min(9000, words * 420))


def build_sync_manifest(
    *,
    book_slug: str,
    chapter_id: str,
    language: str,
    model_candidate: str,
    source_hash: str,
    text: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    cursor_ms = 0
    for index, (paragraph_index, sentence_index, sentence) in enumerate(split_sentences(text), start=1):
        duration = deterministic_timing_ms(sentence)
        start_ms = cursor_ms
        end_ms = start_ms + duration
        cursor_ms = end_ms + 220
        items.append(
            {
                "text_fragment_id": f"{book_slug}-{chapter_id}-s{index:03d}",
                "chapter_id": chapter_id,
                "paragraph_index": paragraph_index,
                "sentence_index": sentence_index,
                "text": sentence,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "confidence": 0.72,
                "sync_level": SYNC_LEVEL,
                "source_hash": source_hash,
                "audio_hash": "sha256:placeholder-no-audio-generated",
                "generated_by": f"internal-dry-run:{model_candidate}:{language}",
                "review_status": "HOLD_HUMAN_SYNC_REVIEW_REQUIRED",
                "public": False,
            }
        )
    return items


def model_candidate_status(candidate: str, language: str) -> dict[str, Any]:
    normalized = safe_slug(candidate)
    info = MODEL_CANDIDATES.get(normalized)
    if not info:
        return {
            "display_name": candidate,
            "languages": [language],
            "license_status": "HOLD_UNKNOWN_LICENSE",
            "license_note": "Unknown model candidates are HOLD until manual license review.",
        }
    return info


def path_present(path_value: str | None) -> bool:
    if not path_value:
        return False
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path.exists() and path.is_file()


def scan_public_audio_files() -> list[str]:
    matches: list[str] = []
    for relative in ("frontend/public", "frontend/build"):
        root = ROOT / relative
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS:
                matches.append(str(path.relative_to(ROOT)))
    return sorted(matches)


def public_text_surface() -> str:
    paths = [
        ROOT / "frontend" / "public" / "index.html",
        ROOT / "frontend" / "build" / "index.html",
        ROOT / "frontend" / "build" / "book" / "dracula" / "index.html",
        ROOT / "frontend" / "build" / "library" / "index.html",
        ROOT / "frontend" / "src" / "pages" / "Home.jsx",
        ROOT / "frontend" / "src" / "pages" / "BookDetail.jsx",
        ROOT / "frontend" / "src" / "pages" / "Library.jsx",
    ]
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in paths if path.exists())


def strip_negated_audio_safety_copy(text: str) -> str:
    patterns = [
        r"No unapproved title offers Start Reading, Read Preview, or Listen Now\.",
        r"No `Listen Now` CTA or public audiobook metadata was added\.",
        r"Listen Now CTAs? remain blocked",
        r"Audio is not available yet\.",
        r"Dracula audiobook is not available yet\.",
        r"no listening CTA is shown",
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned


def evaluate_release_gates(
    *,
    mode: str,
    model_info: dict[str, Any],
    sync_items: list[dict[str, Any]],
    local_internal_generation_ok: bool,
    model_license_evidence: str | None,
    source_rights_evidence: str | None,
    derivative_rights_evidence: str | None,
    voice_rights_evidence: str | None,
    human_qa_evidence: str | None,
    accessibility_qa_evidence: str | None,
) -> list[PipelineBlocker]:
    blockers: list[PipelineBlocker] = []

    def block(code: str, severity: str, message: str) -> None:
        blockers.append(PipelineBlocker(code, severity, message))

    public_audio_files = scan_public_audio_files()
    if public_audio_files:
        block("PUBLIC_AUDIO_FILE_DETECTED", "CRITICAL", f"Public audio-like files found: {', '.join(public_audio_files)}")

    public_text = public_text_surface()
    positive_text = strip_negated_audio_safety_copy(public_text)
    if re.search(r"\bListen Now\b", positive_text, re.IGNORECASE):
        block("PUBLIC_LISTEN_NOW_CTA", "CRITICAL", "Public Listen Now CTA detected.")
    if re.search(r"AudioObject", public_text, re.IGNORECASE):
        block("PUBLIC_AUDIOOBJECT_METADATA", "CRITICAL", "Public AudioObject metadata detected.")

    if any(item.get("public") is True for item in sync_items):
        block("SYNC_MANIFEST_PUBLIC_WITHOUT_APPROVAL", "CRITICAL", "Sync manifest fragments cannot be public without release approval.")

    license_status = str(model_info.get("license_status", "HOLD_UNKNOWN_LICENSE"))
    if "HOLD" in license_status or "UNKNOWN" in license_status:
        block("MODEL_LICENSE_HOLD", "HIGH", f"Model license status is not approved: {license_status}.")

    required_evidence = {
        "SOURCE_RIGHTS_EVIDENCE_MISSING": source_rights_evidence,
        "DERIVATIVE_AUDIOBOOK_RIGHTS_MISSING": derivative_rights_evidence,
        "VOICE_RIGHTS_MISSING": voice_rights_evidence,
        "TEXT_FIDELITY_EVIDENCE_MISSING": human_qa_evidence,
        "HUMAN_LISTENING_QA_MISSING": human_qa_evidence,
        "ACCESSIBILITY_LISTENING_QA_MISSING": accessibility_qa_evidence,
    }
    for code, evidence_path in required_evidence.items():
        if not path_present(evidence_path):
            block(code, "HIGH", f"{code.lower()} is required before internal generation or release.")

    if mode == "generate-internal":
        if not local_internal_generation_ok:
            block("LOCAL_INTERNAL_GENERATION_FLAG_MISSING", "CRITICAL", "generate-internal requires --local-internal-generation-ok.")
        if not path_present(model_license_evidence):
            block("MODEL_LICENSE_EVIDENCE_MISSING", "CRITICAL", "generate-internal requires model license evidence.")

    return blockers


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def result_json(result: PipelineResult) -> dict[str, Any]:
    return {
        "book_slug": result.book_slug,
        "chapter": result.chapter,
        "language": result.language,
        "model_candidate": result.model_candidate,
        "mode": result.mode,
        "status": result.status,
        "generated_at": result.generated_at,
        "output_dir": str(result.output_dir),
        "source_hash": result.source_hash,
        "sync_manifest_path": str(result.sync_manifest_path),
        "qa_packet_path": str(result.qa_packet_path),
        "model_decision_path": str(result.model_decision_path),
        "release_gate_report_path": str(result.release_gate_report_path),
        "blockers": [blocker.__dict__ for blocker in result.blockers],
        "warnings": result.warnings,
        "sync_item_count": len(result.sync_items),
        "public_audio_release_status": PUBLIC_AUDIO_RELEASE_BLOCKED,
    }


def report_markdown(result: PipelineResult) -> str:
    blocker_lines = "\n".join(f"- `{blocker.code}` ({blocker.severity}): {blocker.message}" for blocker in result.blockers)
    if not blocker_lines:
        blocker_lines = "- No blockers for internal dry-run review. Public release remains blocked."
    return f"""# Audiobook Generation Sync Pipeline Report

- Book slug: `{result.book_slug}`
- Chapter: `{result.chapter}`
- Language: `{result.language}`
- Model candidate: `{result.model_candidate}`
- Mode: `{result.mode}`
- Status: `{result.status}`
- Public audio release: `{PUBLIC_AUDIO_RELEASE_BLOCKED}`
- Output directory: `{result.output_dir.relative_to(ROOT)}`
- Sync manifest: `{result.sync_manifest_path.relative_to(ROOT)}`

## Blockers

{blocker_lines}

## Safety

- No public audio was generated.
- No audio file was written to `frontend/public` or `frontend/build`.
- No Listen Now CTA or AudioObject metadata was added.
- No book was published.
- No payment behavior was changed.
"""


def sync_qa_rubric_markdown() -> str:
    return """# Audiobook Highlight Sync QA Rubric

This rubric is internal only. It does not approve public audio.

Required before release:

- Text fidelity review against the approved source text.
- Sentence/phrase highlight timing review by a human listener.
- Accessibility listening QA for blind, low-vision, dyslexic, elderly, and non-reading users.
- Long-silence, repeated-line, clipping, and missing-paragraph checks.
- Owner approval and rollback approval.

Current release status: `PUBLIC_AUDIO_RELEASE_BLOCKED`.
"""


def model_bakeoff_markdown() -> str:
    rows = ["| Candidate | Languages | License status | Notes |", "| --- | --- | --- | --- |"]
    for info in MODEL_CANDIDATES.values():
        rows.append(
            f"| {info['display_name']} | {', '.join(info['languages'])} | {info['license_status']} | {info['license_note']} |"
        )
    return "# Audiobook Model Bakeoff Plan\n\n" + "\n".join(rows) + "\n\nUnknown-license candidates remain HOLD.\n"


def sample_review_packet_markdown(result: PipelineResult) -> str:
    return f"""# Audiobook Internal Sample Review Packet

- Book slug: `{result.book_slug}`
- Chapter: `{result.chapter}`
- Language: `{result.language}`
- Model candidate: `{result.model_candidate}`
- Public audio release: `{PUBLIC_AUDIO_RELEASE_BLOCKED}`
- Human listening QA: HOLD
- Accessibility listening QA: HOLD
- Derivative rights: HOLD unless separate evidence is attached
- Voice/model license: HOLD unless separate evidence is attached

No public sample URL exists. No public audio file was created.
"""


def write_pipeline_outputs(result: PipelineResult, *, write_root_reports: bool = True) -> None:
    write_json(
        result.sync_manifest_path,
        {
            "book_slug": result.book_slug,
            "chapter": result.chapter,
            "language": result.language,
            "sync_level": SYNC_LEVEL,
            "public": False,
            "review_status": "HOLD_HUMAN_SYNC_REVIEW_REQUIRED",
            "items": result.sync_items,
        },
    )
    write_json(result.qa_packet_path, result_json(result))
    write_json(
        result.model_decision_path,
        {
            "book_slug": result.book_slug,
            "model_candidate": result.model_candidate,
            "decision": "HOLD_LICENSE_AND_HUMAN_QA_REQUIRED",
            "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "candidates": MODEL_CANDIDATES,
        },
    )
    write_json(
        result.release_gate_report_path,
        {
            "status": result.status,
            "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "blockers": [blocker.__dict__ for blocker in result.blockers],
        },
    )
    if write_root_reports:
        write_markdown(ROOT / "AUDIOBOOK_GENERATION_SYNC_PIPELINE_REPORT.md", report_markdown(result))
        write_markdown(ROOT / "AUDIOBOOK_HIGHLIGHT_SYNC_QA_RUBRIC.md", sync_qa_rubric_markdown())
        write_markdown(ROOT / "AUDIOBOOK_MODEL_BAKEOFF_PLAN.md", model_bakeoff_markdown())
        write_markdown(ROOT / "AUDIOBOOK_INTERNAL_SAMPLE_REVIEW_PACKET.md", sample_review_packet_markdown(result))


def run_pipeline(
    *,
    book_slug: str,
    chapter: str,
    language: str,
    model_candidate: str,
    mode: str,
    output_dir: Path | None = None,
    no_network: bool = True,
    local_internal_generation_ok: bool = False,
    model_license_evidence: str | None = None,
    source_rights_evidence: str | None = None,
    derivative_rights_evidence: str | None = None,
    voice_rights_evidence: str | None = None,
    human_qa_evidence: str | None = None,
    accessibility_qa_evidence: str | None = None,
    write_root_reports: bool = True,
) -> PipelineResult:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("--language must be en or bn.")
    if mode not in {"dry-run", "generate-internal"}:
        raise ValueError("--mode must be dry-run or generate-internal.")
    if no_network is not True:
        raise ValueError("Network access is not supported by this prototype.")

    normalized_slug = safe_slug(book_slug)
    normalized_chapter = str(int(str(chapter).strip()))
    target_dir = output_dir or DEFAULT_INTERNAL_ROOT / normalized_slug / language / normalized_chapter
    target_dir = target_dir.resolve()
    try:
        target_dir.relative_to(ROOT / "internal" / "audiobook_lab")
    except ValueError as exc:
        raise ValueError("output-dir must stay under internal/audiobook_lab/.") from exc

    chapter_id, _title, source_text = load_source_text(normalized_slug, normalized_chapter, language)
    source_hash = sha256_text(source_text)
    model_info = model_candidate_status(model_candidate, language)
    sync_items = build_sync_manifest(
        book_slug=normalized_slug,
        chapter_id=chapter_id,
        language=language,
        model_candidate=safe_slug(model_candidate),
        source_hash=source_hash,
        text=source_text,
    )
    blockers = evaluate_release_gates(
        mode=mode,
        model_info=model_info,
        sync_items=sync_items,
        local_internal_generation_ok=local_internal_generation_ok,
        model_license_evidence=model_license_evidence,
        source_rights_evidence=source_rights_evidence,
        derivative_rights_evidence=derivative_rights_evidence,
        voice_rights_evidence=voice_rights_evidence,
        human_qa_evidence=human_qa_evidence,
        accessibility_qa_evidence=accessibility_qa_evidence,
    )
    if mode == "generate-internal" and blockers:
        status = BLOCKED_GENERATE_INTERNAL
    elif mode == "dry-run":
        status = DRY_RUN_COMPLETE
    else:
        status = READY_FOR_INTERNAL_REVIEW

    result = PipelineResult(
        book_slug=normalized_slug,
        chapter=normalized_chapter,
        language=language,
        model_candidate=safe_slug(model_candidate),
        mode=mode,
        status=status,
        output_dir=target_dir,
        generated_at=utc_now(),
        source_hash=source_hash,
        sync_manifest_path=target_dir / "sync_manifest.json",
        qa_packet_path=target_dir / "qa_packet.json",
        model_decision_path=target_dir / "model_decision_template.json",
        release_gate_report_path=target_dir / "release_gate_report.json",
        blockers=blockers,
        warnings=["No real audio generated.", "Public audiobook release remains blocked."],
        sync_items=sync_items,
    )
    write_pipeline_outputs(result, write_root_reports=write_root_reports)
    return result


def write_model_config() -> None:
    MODEL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Internal TTS model candidate bakeoff config.",
        "# No model is production-approved by this file.",
        "candidates:",
    ]
    for key, info in MODEL_CANDIDATES.items():
        lines.extend(
            [
                f"  - id: {key}",
                f"    name: {info['display_name']}",
                f"    languages: [{', '.join(info['languages'])}]",
                f"    license_status: {info['license_status']}",
                f"    note: {info['license_note']}",
            ]
        )
    MODEL_CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--language", choices=sorted(SUPPORTED_LANGUAGES), required=True)
    parser.add_argument("--model-candidate", required=True)
    parser.add_argument("--mode", choices=("dry-run", "generate-internal"), default="dry-run")
    parser.add_argument("--no-network", action="store_true", default=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--local-internal-generation-ok", action="store_true")
    parser.add_argument("--model-license-evidence")
    parser.add_argument("--source-rights-evidence")
    parser.add_argument("--derivative-rights-evidence")
    parser.add_argument("--voice-rights-evidence")
    parser.add_argument("--human-qa-evidence")
    parser.add_argument("--accessibility-qa-evidence")
    args = parser.parse_args()

    write_model_config()
    result = run_pipeline(
        book_slug=args.book_slug,
        chapter=args.chapter,
        language=args.language,
        model_candidate=args.model_candidate,
        mode=args.mode,
        output_dir=args.output_dir,
        no_network=args.no_network,
        local_internal_generation_ok=args.local_internal_generation_ok,
        model_license_evidence=args.model_license_evidence,
        source_rights_evidence=args.source_rights_evidence,
        derivative_rights_evidence=args.derivative_rights_evidence,
        voice_rights_evidence=args.voice_rights_evidence,
        human_qa_evidence=args.human_qa_evidence,
        accessibility_qa_evidence=args.accessibility_qa_evidence,
    )
    print(
        "Audiobook sync pipeline complete: "
        f"status={result.status} "
        f"book={result.book_slug} "
        f"language={result.language} "
        f"chapter={result.chapter} "
        f"sync_manifest={result.sync_manifest_path.relative_to(ROOT)} "
        f"public_audio={PUBLIC_AUDIO_RELEASE_BLOCKED} "
        f"blockers={len(result.blockers)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
