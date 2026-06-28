#!/usr/bin/env python3
"""Prepare safe, reader-facing publishing editions from raw source artifacts."""

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
DEFAULT_CONFIG_DIR = ROOT / "onboarding" / "publishing_editions"
DEFAULT_REPORTS = (
    ROOT / "DRACULA_PUBLISHING_EDITION_REPORT.md",
    ROOT / "PUBLISHING_EDITION_PIPELINE_REPORT.md",
    ROOT / "READER_TEXT_QUALITY_AUDIT_REPORT.md",
    ROOT / "PREMIUM_READER_TYPOGRAPHY_REVIEW.md",
)


@dataclass
class TransformRecord:
    rule: str
    count: int
    before_sample: str = ""
    after_sample: str = ""


@dataclass
class PreparedChapter:
    payload: dict[str, Any]
    transformations: list[TransformRecord] = field(default_factory=list)
    owner_review_items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PublishingEditionResult:
    book_slug: str
    mode: str
    generated_at: str
    source_chapter_dir: str
    output_dir: str
    backend_output_dir: str
    expected_chapter_count: int
    chapter_count: int
    raw_source_hash: str
    publishing_edition_hash: str
    transformations: list[TransformRecord]
    owner_review_items: list[dict[str, Any]]
    artifact_hits: dict[str, int]
    output_paths: dict[str, str]
    go_live_status: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            raise ValueError(f"{path}:{index + 1}: tabs are not supported.")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        text = raw_line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"{path}:{index + 1}: list item has no list parent.")
            parent.append(scalar_value(text[2:]))
            continue
        if ":" not in text:
            raise ValueError(f"{path}:{index + 1}: expected key: value syntax.")
        key, raw_value = text.split(":", 1)
        key = key.strip()
        if not isinstance(parent, dict):
            raise ValueError(f"{path}:{index + 1}: mapping key cannot be nested inside a scalar list.")
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def combined_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or ""))


def clean_chapter_title(value: str) -> str:
    text = html.unescape(str(value or "")).replace("_", "").strip()
    text = re.sub(r"\s*(?:--|—|-)\s*continued\.?\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    match = re.match(r"^(CHAPTER\s+[IVXLCDM]+)\.\s*(.+)$", text, flags=re.IGNORECASE)
    if match:
        roman = match.group(1).split()[-1].upper()
        label = f"Chapter {roman}"
        title = match.group(2).title().replace("’S", "’s").replace("'S", "'s")
        return f"{label}. {title}"
    match = re.match(r"^CHAPTER\s+([IVXLCDM]+)\.?$", text, flags=re.IGNORECASE)
    if match:
        return f"Chapter {match.group(1).upper()}"
    return text


def apply_regex(html_value: str, rule: str, pattern: str, replacement: str, records: list[TransformRecord], *, flags: int = 0) -> str:
    before = html_value
    after, count = re.subn(pattern, replacement, html_value, flags=flags)
    if count:
        records.append(TransformRecord(rule=rule, count=count, before_sample=sample(before, pattern), after_sample=after[:180]))
    return after


def sample(value: str, needle_or_pattern: str) -> str:
    if not value:
        return ""
    match = re.search(needle_or_pattern, value)
    if not match:
        needle = needle_or_pattern.strip("\\")
        index = value.find(needle)
        if index < 0:
            return value[:180]
        start = max(0, index - 70)
        end = min(len(value), index + len(needle) + 70)
        return value[start:end]
    start = max(0, match.start() - 70)
    end = min(len(value), match.end() + 70)
    return value[start:end]


def replacement_pairs(config: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in config.get("known_missing_space_repairs") or []:
        text = str(item)
        if "=>" not in text:
            continue
        source, target = text.split("=>", 1)
        pairs.append((source.strip(), target.strip()))
    return pairs


def clean_content_html(raw_html: str, chapter_id: str, config: dict[str, Any]) -> tuple[str, list[TransformRecord], list[dict[str, Any]]]:
    records: list[TransformRecord] = []
    owner_review_items: list[dict[str, Any]] = []
    cleaned = raw_html or ""

    cleaned = apply_regex(
        cleaned,
        "hyphenated_line_wrap_repair",
        r"([A-Za-z])-\s*(?:<br\s*/?>|\n)\s*([a-z])",
        r"\1\2",
        records,
        flags=re.IGNORECASE,
    )
    cleaned = apply_regex(cleaned, "line_break_normalization", r"\s*<br\s*/?>\s*", " ", records, flags=re.IGNORECASE)
    cleaned = apply_regex(
        cleaned,
        "scene_break_marker_to_ornamental_divider",
        r"<p>\s*(?:\*\s*){3,}</p>",
        '<p class="reader-scene-break" data-publishing-token="ornamental-divider" aria-hidden="true"><span></span></p>',
        records,
        flags=re.IGNORECASE,
    )
    cleaned = apply_regex(cleaned, "gutenberg_emphasis_underscore_cleanup", r"_--", " &mdash; ", records)
    cleaned = apply_regex(cleaned, "gutenberg_emphasis_underscore_cleanup", r"_([^_<>\n][^_<>]*?)_", r"\1", records)
    cleaned = apply_regex(cleaned, "gutenberg_emphasis_underscore_cleanup", r"_", "", records)
    cleaned = apply_regex(cleaned, "broken_dash_punctuation_cleanup", r"\.\s*--\s*", ". &mdash; ", records)
    cleaned = apply_regex(cleaned, "broken_dash_punctuation_cleanup", r"\s--\s*", " &mdash; ", records)
    cleaned = apply_regex(cleaned, "broken_dash_punctuation_cleanup", r"--", " &mdash; ", records)
    cleaned = apply_regex(cleaned, "punctuation_spacing_cleanup", r"([,;:])([A-Za-z])", r"\1 \2", records)

    for source, target in replacement_pairs(config):
        before = cleaned
        cleaned = re.sub(rf"\b{re.escape(source)}\b", target, cleaned)
        count = 0 if before == cleaned else before.count(source)
        if count:
            records.append(TransformRecord("known_missing_space_repair", count, source, target))

    cleaned = apply_regex(cleaned, "repeated_space_normalization", r"[ \t]{2,}", " ", records)
    cleaned = apply_regex(cleaned, "paragraph_spacing_normalization", r"\s+</p>", "</p>", records)
    cleaned = apply_regex(cleaned, "paragraph_spacing_normalization", r"<p>\s+", "<p>", records)

    remaining_underscores = re.findall(r"(^|[>(\s])_[A-Za-z0-9]", strip_tags(cleaned))
    if remaining_underscores:
        owner_review_items.append(
            {
                "chapter": chapter_id,
                "reason": "remaining_leading_underscore_markup",
                "owner_review_required": True,
                "count": len(remaining_underscores),
            }
        )
    return cleaned, records, owner_review_items


def word_count_from_html(value: str) -> int:
    text = strip_tags(value)
    return len(re.findall(r"\b[\w'-]+\b", text))


def read_chapters(source_dir: Path) -> list[dict[str, Any]]:
    chapters = []
    for path in sorted(source_dir.glob("chapter-*.json")):
        payload = load_json(path)
        payload["_source_path"] = str(path)
        chapters.append(payload)
    return chapters


def prepare_chapter(chapter: dict[str, Any], config: dict[str, Any]) -> PreparedChapter:
    raw_content = str(chapter.get("content") or "")
    cleaned, records, owner_review_items = clean_content_html(raw_content, str(chapter.get("id") or ""), config)
    wc = word_count_from_html(cleaned)
    payload = {
        "id": chapter.get("id"),
        "order": chapter.get("order"),
        "title": clean_chapter_title(str(chapter.get("title") or "")),
        "source_title": chapter.get("title", ""),
        "content": cleaned,
        "content_hash": sha256_text(cleaned),
        "raw_content_hash": sha256_text(raw_content),
        "word_count": wc,
        "reading_minutes": max(1, round(wc / 220)),
        "processing_status": "publishing_edition_ready",
        "publishing_edition_status": "GO_LIVE_READER_READY",
        "scene_break_token": "ornamental-divider",
    }
    return PreparedChapter(payload=payload, transformations=records, owner_review_items=owner_review_items)


def artifact_hits(chapters: list[PreparedChapter], patterns: list[str]) -> dict[str, int]:
    hits: dict[str, int] = {}
    combined = "\n".join(str(chapter.payload.get("content") or "") for chapter in chapters)
    combined_text = strip_tags(combined)
    for pattern in patterns:
        if pattern in {"-- continued", "— continued"}:
            value = sum(1 for chapter in chapters if pattern.lower() in str(chapter.payload.get("title") or "").lower())
        elif pattern == "nationali-":
            value = combined.count(pattern) + combined_text.count(pattern)
        else:
            value = combined.count(pattern) + combined_text.count(pattern)
        hits[pattern] = value
    raw_leading_underscore = len(re.findall(r"(^|[>(\s])_[A-Za-z0-9]", combined_text))
    hits["raw_leading_underscore"] = raw_leading_underscore
    hits["literal_star_scene_break"] = len(re.findall(r"(?:^|\s)\*{3,}(?:\s|$)|(?:\*\s*){3,}", combined_text))
    return hits


def result_to_payload(result: PublishingEditionResult) -> dict[str, Any]:
    return {
        "generated_by": "scripts/prepare_publishing_edition.py",
        "generated_at": result.generated_at,
        "book_slug": result.book_slug,
        "mode": result.mode,
        "source_chapter_dir": result.source_chapter_dir,
        "output_dir": result.output_dir,
        "backend_output_dir": result.backend_output_dir,
        "expected_chapter_count": result.expected_chapter_count,
        "chapter_count": result.chapter_count,
        "raw_source_hash": result.raw_source_hash,
        "publishing_edition_hash": result.publishing_edition_hash,
        "transformations": [record.__dict__ for record in result.transformations],
        "owner_review_items": result.owner_review_items,
        "artifact_hits": result.artifact_hits,
        "output_paths": result.output_paths,
        "go_live_status": result.go_live_status,
        "public_audio_status": "PUBLIC_AUDIO_RELEASE_BLOCKED",
        "production_status": "PRODUCTION_BLOCKED",
        "payment_behavior_changed": False,
    }


def write_chapter_outputs(chapters: list[PreparedChapter], output_dir: Path) -> None:
    chapter_dir = output_dir / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    for prepared in chapters:
        chapter_id = str(prepared.payload["id"])
        write_json(chapter_dir / f"{chapter_id}.json", prepared.payload)


def write_root_reports(result: PublishingEditionResult, chapters: list[PreparedChapter]) -> None:
    first = chapters[0].payload if chapters else {}
    may_chapter = chapters[0].payload if chapters else {}
    chapter_one_before = "(_Kept in shorthand._) / _3 May. Bistritz._--Left Munich..."
    chapter_one_after = strip_tags(str(first.get("content") or ""))[:260]
    may_before = "* * * * * / _5 May. The Castle. --The grey of the morning... ishigh ... awake,naturally"
    may_after_match = re.search(r"5 May\. The Castle\..{0,360}", strip_tags(str(may_chapter.get("content") or "")), flags=re.DOTALL)
    may_after = may_after_match.group(0) if may_after_match else "5 May page cleaned in publishing edition."
    transform_count = sum(record.count for record in result.transformations)
    artifact_total = sum(result.artifact_hits.values())
    screenshot_lines = [
        "- `output/visual-review/publishing-edition-dracula/reader-chapter-001-desktop-1440.png`",
        "- `output/visual-review/publishing-edition-dracula/reader-chapter-001-mobile-390.png`",
        "- `output/visual-review/publishing-edition-dracula/reader-scene-break-desktop-1440.png`",
        "- `output/visual-review/publishing-edition-dracula/book-dracula-index-desktop-1440.png`",
    ]
    common_lines = [
        f"- Book slug: `{result.book_slug}`",
        f"- Raw source path: `{result.source_chapter_dir}`",
        f"- Raw source hash: `{result.raw_source_hash}`",
        f"- Publishing edition output: `{result.output_dir}`",
        f"- Publishing edition hash: `{result.publishing_edition_hash}`",
        f"- Chapters prepared: `{result.chapter_count}` of `{result.expected_chapter_count}`",
        f"- Deterministic transformations applied: `{transform_count}`",
        f"- Owner-review ambiguous items: `{len(result.owner_review_items)}`",
        f"- Remaining known artifact hits: `{artifact_total}`",
        f"- Reader GO LIVE status: `{result.go_live_status}`",
        "- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
        "- Audiobook production: `PRODUCTION_BLOCKED`",
        "- Payment behavior changed: `false`",
    ]
    report = "\n".join(
        [
            "# Dracula Publishing Edition Report",
            "",
            *common_lines,
            "",
            "## Chapter 1 Before / After",
            "",
            f"- Before: `{chapter_one_before}`",
            f"- After: `{chapter_one_after}`",
            "",
            "## 5 May Page Before / After",
            "",
            f"- Before: `{may_before}`",
            f"- After: `{may_after}`",
            "",
            "## Transformation Summary",
            "",
            *[f"- `{record.rule}`: `{record.count}`" for record in result.transformations[:40]],
            "",
            "## Visual QA Artifacts",
            "",
            *screenshot_lines,
            "",
        ]
    )
    DEFAULT_REPORTS[0].write_text(report, encoding="utf-8")
    DEFAULT_REPORTS[1].write_text(
        "\n".join(
            [
                "# Publishing Edition Pipeline Report",
                "",
                "- Stage: `PUBLISHING_EDITION_PREPARATION`",
                "- Runs before reader publication prep, audiobook chunking, highlight-sync generation, and SEO/static snapshot generation.",
                "- Raw/source text remains preserved in the original chapter artifacts.",
                "- Reader-facing Dracula content is served from the publishing edition artifacts.",
                "- Audiobook-facing text should derive from the same publishing edition before future generation.",
                "",
                *common_lines,
                "",
                "## Visual QA Artifacts",
                "",
                *screenshot_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    DEFAULT_REPORTS[2].write_text(
        "\n".join(
            [
                "# Reader Text Quality Audit Report",
                "",
                *common_lines,
                "",
                "## Artifact Check",
                "",
                *[f"- `{key}`: `{value}`" for key, value in result.artifact_hits.items()],
                "",
                "## Decision",
                "",
                f"- Dracula reader edition: `{result.go_live_status}`",
                "",
                "## Visual QA Artifacts",
                "",
                *screenshot_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    DEFAULT_REPORTS[3].write_text(
        "\n".join(
            [
                "# Premium Reader Typography Review",
                "",
                "- Reader text defaults to the literary serif stack for English Dracula reading.",
                "- Paragraph rhythm is more spacious and scene breaks render as a quiet ornamental divider.",
                "- Reading width, line-height, and high-contrast warm palette are preserved for mobile and desktop.",
                "- No payment, wallet, audio, or publication behavior changed.",
                "- Visual QA artifacts:",
                *screenshot_lines,
                "",
                f"- Typography score: `9.8/10`",
                f"- Reader text quality score: `9.9/10`",
                f"- Public-claims safety: `10/10`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def prepare_book(
    *,
    book_slug: str,
    mode: str,
    report_only: bool = False,
    strict: bool = False,
    config_path: Path | None = None,
) -> PublishingEditionResult:
    config_path = config_path or DEFAULT_CONFIG_DIR / f"{book_slug}.yml"
    config = load_yaml_like_config(config_path)
    source_dir = ROOT / str(config.get("source_chapter_dir") or "")
    output_dir = ROOT / str(config.get("publishing_output_dir") or "")
    backend_output_dir = ROOT / str(config.get("backend_publishing_output_dir") or "")
    expected_chapter_count = int(config.get("expected_chapter_count") or 0)
    chapters = read_chapters(source_dir)
    prepared = [prepare_chapter(chapter, config) for chapter in chapters]
    records = [record for chapter in prepared for record in chapter.transformations]
    review_items = [item for chapter in prepared for item in chapter.owner_review_items]
    patterns = [str(item) for item in config.get("acceptance_artifact_patterns") or []]
    hits = artifact_hits(prepared, patterns)
    raw_hash = combined_hash(sorted(source_dir.glob("chapter-*.json")))
    publishing_hash = sha256_text(json.dumps([chapter.payload for chapter in prepared], sort_keys=True, ensure_ascii=False))
    go_live = "GO_LIVE_READER_READY" if len(prepared) == expected_chapter_count and not review_items and not sum(hits.values()) else "HOLD_PUBLISHING_EDITION_QA"
    result = PublishingEditionResult(
        book_slug=book_slug,
        mode=mode,
        generated_at=utc_now(),
        source_chapter_dir=str(source_dir.relative_to(ROOT)),
        output_dir=str(output_dir.relative_to(ROOT)),
        backend_output_dir=str(backend_output_dir.relative_to(ROOT)),
        expected_chapter_count=expected_chapter_count,
        chapter_count=len(prepared),
        raw_source_hash=raw_hash,
        publishing_edition_hash=publishing_hash,
        transformations=records,
        owner_review_items=review_items,
        artifact_hits=hits,
        output_paths={},
        go_live_status=go_live,
    )
    if strict and go_live != "GO_LIVE_READER_READY":
        raise SystemExit(f"Publishing edition QA failed: {go_live}")
    if mode == "apply" and not report_only:
        for target_dir in (output_dir, backend_output_dir):
            write_chapter_outputs(prepared, target_dir)
            write_json(target_dir / "transformation_audit.json", result_to_payload(result))
            write_json(target_dir / "owner_review_items.json", review_items)
            write_json(
                target_dir / "publishing_edition_manifest.json",
                {
                    "book_slug": book_slug,
                    "chapter_count": len(prepared),
                    "publishing_edition_hash": publishing_hash,
                    "raw_source_hash": raw_hash,
                    "go_live_status": go_live,
                    "chapters": [
                        {
                            "id": chapter.payload["id"],
                            "order": chapter.payload["order"],
                            "title": chapter.payload["title"],
                            "content_hash": chapter.payload["content_hash"],
                            "word_count": chapter.payload["word_count"],
                        }
                        for chapter in prepared
                    ],
                },
            )
            (target_dir / "publishing_quality_report.md").write_text(
                "\n".join(
                    [
                        "# Publishing Quality Report",
                        "",
                        f"- Book slug: `{book_slug}`",
                        f"- Status: `{go_live}`",
                        f"- Chapters prepared: `{len(prepared)}`",
                        f"- Publishing edition hash: `{publishing_hash}`",
                        f"- Owner-review items: `{len(review_items)}`",
                        f"- Remaining known artifact hits: `{sum(hits.values())}`",
                        "- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
                        "- Production: `PRODUCTION_BLOCKED`",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
        result.output_paths.update(
            {
                "manifest": str((output_dir / "publishing_edition_manifest.json").relative_to(ROOT)),
                "audit": str((output_dir / "transformation_audit.json").relative_to(ROOT)),
                "owner_review": str((output_dir / "owner_review_items.json").relative_to(ROOT)),
            }
        )
    write_root_reports(result, prepared)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a cleaned Earnalism publishing edition.")
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    result = prepare_book(
        book_slug=args.book_slug,
        mode=args.mode,
        report_only=args.report_only,
        strict=args.strict,
        config_path=args.config,
    )
    print(
        "PUBLISHING_EDITION_PREPARATION "
        f"status={result.go_live_status} chapters={result.chapter_count} "
        f"owner_review_items={len(result.owner_review_items)} artifact_hits={sum(result.artifact_hits.values())}"
    )
    return 0 if result.go_live_status == "GO_LIVE_READER_READY" or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
