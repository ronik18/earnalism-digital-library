#!/usr/bin/env python3
"""Build representative Dracula chunks for English audiobook model bake-offs."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.english_text_normalizer import (
    normalize_english_text,
    pronunciation_notes_for_text,
    write_normalization_report,
)


DRACULA_DIR = ROOT_DIR / "data" / "controlled_publications" / "dracula"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "audiobook_generation" / "dracula"


@dataclass(frozen=True)
class EnglishAudiobookChunk:
    chunk_id: str
    order: int
    source_chapter_id: str
    source_chapter_title: str
    original_text: str
    normalized_text: str
    emotion_label: str
    segment_type: str
    pace_hint: str
    style_prompt: str
    pronunciation_terms: list[str]
    estimated_seconds: int
    word_count: int
    internal_review_only: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "order": self.order,
            "source_chapter_id": self.source_chapter_id,
            "source_chapter_title": self.source_chapter_title,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "emotion_label": self.emotion_label,
            "segment_type": self.segment_type,
            "pace_hint": self.pace_hint,
            "style_prompt": self.style_prompt,
            "pronunciation_terms": self.pronunciation_terms,
            "estimated_seconds": self.estimated_seconds,
            "word_count": self.word_count,
            "internal_review_only": self.internal_review_only,
        }


def html_to_plain_text(markup: str) -> str:
    text = markup or ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>\s*<p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?p[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_chapter(chapter_path: Path) -> dict[str, Any]:
    data = json.loads(chapter_path.read_text(encoding="utf-8"))
    return {
        "id": data.get("id") or chapter_path.stem,
        "title": data.get("title") or chapter_path.stem,
        "text": html_to_plain_text(str(data.get("content") or "")),
    }


def paragraphs_from_text(text: str) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    merged: list[str] = []
    pending_heading = ""
    for paragraph in paragraphs:
        if re.match(r"^_[0-9]{1,2}\s+\w+\.", paragraph):
            pending_heading = paragraph
            continue
        if pending_heading:
            paragraph = f"{pending_heading} {paragraph}"
            pending_heading = ""
        merged.append(paragraph)
    if pending_heading:
        merged.append(pending_heading)
    return merged


def classify_emotion(text: str) -> tuple[str, str, str]:
    lowered = text.lower()
    if re.search(r"^_?\d{1,2}\s+(may|june|july|august|september|october|november|december)\b", lowered):
        return (
            "intimate_diary",
            "measured",
            "Read like a private diary entry: restrained, observant, and close to the page.",
        )
    if '"' in text or "“" in text or "”" in text:
        return (
            "dialogue",
            "natural",
            "Keep dialogue distinct but avoid theatrical caricature.",
        )
    if any(term in lowered for term in ["wolf", "howl", "fear", "fright", "dread"]):
        return (
            "quiet_fear",
            "slow",
            "Let the unease rise quietly; keep the narrator calm and intelligent.",
        )
    if any(term in lowered for term in ["castle", "dark", "mountain", "carpathian", "night"]):
        return (
            "gothic_suspense",
            "unhurried",
            "Give the setting a shadowed, premium Gothic atmosphere without overacting.",
        )
    if any(term in lowered for term in ["wonderful", "beautiful", "strange", "curious"]):
        return (
            "wonder",
            "measured",
            "Maintain restrained curiosity and literary warmth.",
        )
    if any(term in lowered for term in ["hurry", "must", "quick", "urgent"]):
        return (
            "urgency",
            "slightly brisk",
            "Increase urgency gently while preserving clarity.",
        )
    if any(term in lowered for term in ["dead", "death", "blood"]):
        return (
            "dread",
            "slow",
            "Use contained dread; no horror-movie exaggeration.",
        )
    return (
        "narration",
        "measured",
        "Read as premium literary narration: warm, clear, and emotionally restrained.",
    )


def classify_segment(text: str) -> str:
    if re.match(r"^_?[0-9]{1,2}\s+\w+\.", text):
        return "diary_heading_with_entry"
    if '"' in text or "“" in text or "”" in text:
        return "dialogue"
    return "narration"


def chunk_id_for(chapter_id: str, order: int, normalized_text: str) -> str:
    digest = hashlib.sha256(f"{chapter_id}:{order}:{normalized_text}".encode("utf-8")).hexdigest()[:12]
    return f"dracula-en-{order:02d}-{digest}"


def terms_in_text(text: str, notes: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for note in notes:
        term = str(note["term"])
        if re.search(re.escape(term), text, re.IGNORECASE):
            found.append(term)
    return found


def build_representative_chunks(
    *,
    chapter_paths: list[Path],
    target_count: int = 12,
) -> tuple[list[EnglishAudiobookChunk], list[dict[str, Any]]]:
    selected_paragraphs: list[tuple[dict[str, Any], str]] = []
    for chapter_path in chapter_paths:
        chapter = load_chapter(chapter_path)
        chapter_candidates = 0
        for paragraph in paragraphs_from_text(chapter["text"]):
            word_count = len(paragraph.split())
            if 35 <= word_count <= 220:
                selected_paragraphs.append((chapter, paragraph))
                chapter_candidates += 1
            if chapter_candidates >= 8:
                break

    notes = pronunciation_notes_for_text(" ".join(paragraph for _chapter, paragraph in selected_paragraphs))
    chunks: list[EnglishAudiobookChunk] = []
    seen_emotions: set[str] = set()

    def append_chunk(chapter: dict[str, Any], paragraph: str) -> None:
        normalized = normalize_english_text(paragraph)
        emotion_label, pace_hint, style_prompt = classify_emotion(paragraph)
        order = len(chunks) + 1
        chunks.append(
            EnglishAudiobookChunk(
                chunk_id=chunk_id_for(str(chapter["id"]), order, normalized.normalized_text),
                order=order,
                source_chapter_id=str(chapter["id"]),
                source_chapter_title=str(chapter["title"]),
                original_text=paragraph,
                normalized_text=normalized.normalized_text,
                emotion_label=emotion_label,
                segment_type=classify_segment(paragraph),
                pace_hint=pace_hint,
                style_prompt=style_prompt,
                pronunciation_terms=terms_in_text(paragraph, notes),
                estimated_seconds=max(8, round(len(normalized.normalized_text.split()) / 2.5)),
                word_count=len(normalized.normalized_text.split()),
            )
        )
        seen_emotions.add(emotion_label)

    used_indexes: set[int] = set()
    for index, (chapter, paragraph) in enumerate(selected_paragraphs):
        emotion_label, _pace_hint, _style_prompt = classify_emotion(paragraph)
        if emotion_label in seen_emotions:
            continue
        append_chunk(chapter, paragraph)
        used_indexes.add(index)
        if len(chunks) >= target_count:
            break

    for chapter, paragraph in selected_paragraphs:
        index = selected_paragraphs.index((chapter, paragraph))
        if index in used_indexes:
            continue
        if len(chunks) >= target_count:
            break
        normalized = normalize_english_text(paragraph)
        emotion_label, pace_hint, style_prompt = classify_emotion(paragraph)
        order = len(chunks) + 1
        chunks.append(
            EnglishAudiobookChunk(
                chunk_id=chunk_id_for(str(chapter["id"]), order, normalized.normalized_text),
                order=order,
                source_chapter_id=str(chapter["id"]),
                source_chapter_title=str(chapter["title"]),
                original_text=paragraph,
                normalized_text=normalized.normalized_text,
                emotion_label=emotion_label,
                segment_type=classify_segment(paragraph),
                pace_hint=pace_hint,
                style_prompt=style_prompt,
                pronunciation_terms=terms_in_text(paragraph, notes),
                estimated_seconds=max(8, round(len(normalized.normalized_text.split()) / 2.5)),
                word_count=len(normalized.normalized_text.split()),
            )
        )
        seen_emotions.add(emotion_label)

    return chunks, notes


def chunk_markdown(chunks: list[EnglishAudiobookChunk]) -> str:
    lines = [
        "# Dracula English Audiobook Bake-Off Chunks",
        "",
        "Status: INTERNAL_REVIEW_ONLY. These chunks are for local model benchmarking only.",
        "",
        "No audiobook is public. Dracula audio remains disabled.",
        "",
    ]
    for chunk in chunks:
        lines.extend(
            [
                f"## {chunk.order}. {chunk.emotion_label} ({chunk.chunk_id})",
                "",
                f"- Chapter: {chunk.source_chapter_title}",
                f"- Segment type: {chunk.segment_type}",
                f"- Pace hint: {chunk.pace_hint}",
                f"- Word count: {chunk.word_count}",
                "",
                "Original:",
                "",
                f"> {chunk.original_text[:700]}",
                "",
                "Normalized:",
                "",
                f"> {chunk.normalized_text[:700]}",
                "",
            ]
        )
    return "\n".join(lines)


def write_chunk_artifacts(chunks: list[EnglishAudiobookChunk], notes: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "book_slug": "dracula",
        "title": "Dracula",
        "author": "Bram Stoker",
        "status": "INTERNAL_REVIEW_ONLY",
        "audio_enabled": False,
        "chunk_count": len(chunks),
        "chunks": [chunk.as_dict() for chunk in chunks],
    }
    (output_dir / "chunks.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "chunks.md").write_text(chunk_markdown(chunks), encoding="utf-8")
    (output_dir / "pronunciation_notes.json").write_text(
        json.dumps({"book_slug": "dracula", "notes": notes}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    normalizations = [normalize_english_text(chunk.original_text) for chunk in chunks]
    write_normalization_report(normalizations, ROOT_DIR / "ENGLISH_TEXT_NORMALIZATION_REPORT.md")
    write_chunk_coverage_report(chunks, ROOT_DIR / "ENGLISH_AUDIOBOOK_CHUNK_COVERAGE_REPORT.md")


def write_chunk_coverage_report(chunks: list[EnglishAudiobookChunk], output_path: Path) -> None:
    manifest = json.loads((DRACULA_DIR / "reader_manifest.json").read_text(encoding="utf-8"))
    chapters = manifest.get("chapters") if isinstance(manifest.get("chapters"), list) else []
    chapter_ids = [str(chapter.get("id") or "") for chapter in chapters]
    sampled_ids = sorted({chunk.source_chapter_id for chunk in chunks})
    emotion_distribution: dict[str, int] = {}
    segment_distribution: dict[str, int] = {}
    punctuation_distribution = {
        "dialogue_quotes": 0,
        "dash_pause": 0,
        "ellipsis": 0,
        "comma": 0,
        "question": 0,
        "exclamation": 0,
    }
    for chunk in chunks:
        emotion_distribution[chunk.emotion_label] = emotion_distribution.get(chunk.emotion_label, 0) + 1
        segment_distribution[chunk.segment_type] = segment_distribution.get(chunk.segment_type, 0) + 1
        punctuation_distribution["dialogue_quotes"] += chunk.original_text.count('"') + chunk.original_text.count("“")
        punctuation_distribution["dash_pause"] += chunk.original_text.count("--") + chunk.original_text.count("—")
        punctuation_distribution["ellipsis"] += chunk.original_text.count("...")
        punctuation_distribution["comma"] += chunk.original_text.count(",")
        punctuation_distribution["question"] += chunk.original_text.count("?")
        punctuation_distribution["exclamation"] += chunk.original_text.count("!")

    skipped = [
        {
            "chapter_id": chapter_id,
            "reason": "Not selected for this 12-chunk dry-run sample; available for future full-chapter internal benchmark.",
        }
        for chapter_id in chapter_ids
        if chapter_id and chapter_id not in sampled_ids
    ]
    lines = [
        "# English Audiobook Chunk Coverage Report",
        "",
        "Book: Dracula by Bram Stoker",
        "",
        "Status: INTERNAL_REVIEW_ONLY. Dracula audio remains disabled.",
        "",
        f"- Total Dracula chapters: {manifest.get('chapter_count')}",
        f"- Selected chunk count: {len(chunks)}",
        f"- Chapters sampled: {', '.join(sampled_ids)}",
        f"- Skipped chapter count: {len(skipped)}",
        "",
        "## Emotion Distribution",
        "",
    ]
    for key, value in sorted(emotion_distribution.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Dialogue / Diary / Letter Coverage", ""])
    for key, value in sorted(segment_distribution.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Punctuation Distribution", ""])
    for key, value in sorted(punctuation_distribution.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Skipped Chapters", ""])
    for row in skipped:
        lines.append(f"- {row['chapter_id']}: {row['reason']}")
    lines.extend(
        [
            "",
            "## Readiness Note",
            "",
            "This report proves coverage accounting across all 27 chapters, but it does not claim full-chapter audio coverage. A 9.9+ audiobook score still requires generated internal samples, human listening review, license clearance, and owner approval.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", default="dracula")
    parser.add_argument("--target-count", type=int, default=12)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    if args.book_slug != "dracula":
        parser.error("Only Dracula is approved for this English model bake-off.")

    chapter_paths = [
        DRACULA_DIR / "chapters" / "chapter-001.json",
        DRACULA_DIR / "chapters" / "chapter-002.json",
        DRACULA_DIR / "chapters" / "chapter-007.json",
        DRACULA_DIR / "chapters" / "chapter-012.json",
    ]
    chunks, notes = build_representative_chunks(chapter_paths=chapter_paths, target_count=args.target_count)
    write_chunk_artifacts(chunks, notes, args.output_dir)
    print(f"Wrote {len(chunks)} Dracula English bake-off chunks to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
