#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bengali_text_normalizer import normalize_bengali_text, punctuation_profile

DEFAULT_BOOK_SLUG = "kshudhita-pashan"
DEFAULT_OUTPUT_DIR = ROOT / "data/audiobook_generation/kshudhita-pashan"
SOURCE_METADATA_PATH = ROOT / "data/publication_candidates/kshudhita-pashan.source.json"
APPROVED_SOURCE_TEXT_PATH = ROOT / "data/audiobook_generation/kshudhita-pashan/approved_source_text.txt"

SAMPLE_TEXT = """ক্ষুধিত পাষাণ।

সন্ধ্যার আকাশে আরাবল্লীর পাথর যেন স্তব্ধ হয়ে দাঁড়াইয়া আছে। বাতাস নাই; কেবল দূরের নদীর ধ্বনি কানে আসে।

"তুমি কি শুনিতে পাও?" সে মৃদুস্বরে বলিল। আমি উত্তর দিলাম না। সেই পুরাতন প্রাসাদের দেওয়াল যেন অদৃশ্য অতীতের শ্বাস ফেলিতে লাগিল।

রাত্রি আরও গভীর হইল। মনে হইল, পাষাণের ভিতর জমিয়া থাকা বহু দিনের ক্ষুধা নিঃশব্দে জাগিয়া উঠিতেছে।

দীর্ঘ বারান্দায় একবার পায়ের শব্দ উঠিল, আবার থামিয়া গেল। অন্ধকারের মধ্যে যেন কারও গোপন দৃষ্টি আমার মুখের উপর স্থির হইয়া রহিল।

আমি মনে মনে বলিলাম, এ কেবল কল্পনা। কিন্তু কল্পনারও একটি ভার আছে; সে ভার বুকের ভিতর জমিয়া উঠিলে মানুষ সহজে নিশ্বাস ফেলিতে পারে না।

"ফিরিয়া চলুন," সহচর কহিল, "এই প্রাসাদে রাত্রি কাটানো ভালো নহে।" তাহার কণ্ঠে ভয় ছিল, কিন্তু সে ভয় লজ্জায় ঢাকা পড়িয়াছিল।

দূরে যেন মৃদু হাসির মতো একটি শব্দ উঠিল, অথচ হাসি বলিতে তাহা লজ্জা পায়। সেই শব্দের মধ্যে আশ্চর্য দুঃখ ও অচেনা উষ্ণতা মিশিয়া ছিল।

হঠাৎ আমার মনে রাগ জাগিল। আমি উচ্চস্বরে বলিলাম না, কেবল দ্রুত পায়ে অন্ধকার ঘরের দিকে অগ্রসর হইলাম।

প্রাসাদের জানালার কাছে দাঁড়াইয়া দেখি, চাঁদের আলো পাথরের গায়ে পড়িয়া এক অদ্ভুত শুভ্রতা আনিয়াছে। সে শুভ্রতা শান্ত নহে; তাহার ভিতরে ক্ষুধা আছে।

তারপর সব নীরব। শুধু মনে হইল, বহু কালের অব্যক্ত কথা পাষাণের অন্তরে চাপা পড়িয়া আছে...

সেই মুহূর্তে বিস্ময়ে আমার হৃদয় থমকিয়া গেল। ভয়ের সঙ্গে এক অপূর্ব সৌন্দর্য জড়াইয়া উঠিল; আমি আর ফিরিতে পারিলাম না।
"""

EMOTION_KEYWORDS = [
    ("ভয়", "fear"),
    ("আতঙ্ক", "fear"),
    ("নীরব", "eerie"),
    ("রাত্রি", "suspense"),
    ("দুঃখ", "sorrow"),
    ("ক্রোধ", "anger_restrained"),
    ("মৃদু", "warmth"),
    ("অদ্ভুত", "wonder"),
]


def deterministic_chunk_id(book_slug: str, chapter_id: str, index: int, text: str) -> str:
    digest = hashlib.sha1(f"{book_slug}:{chapter_id}:{index}:{text}".encode("utf-8")).hexdigest()[:10]
    return f"{book_slug}-{chapter_id}-{index:03d}-{digest}"


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    buffer: list[str] = []
    in_quote = False
    quote_marks = {'"', "“", "”", "‘", "’"}
    for char in text:
        buffer.append(char)
        if char in quote_marks:
            was_in_quote = in_quote
            in_quote = not in_quote
            if was_in_quote and len(buffer) >= 2 and buffer[-2] in {"।", "?", "!"}:
                candidate = "".join(buffer).strip()
                if candidate:
                    sentences.append(candidate)
                buffer = []
                continue
        if char in {"।", "?", "!"} and not in_quote:
            candidate = "".join(buffer).strip()
            if candidate:
                sentences.append(candidate)
            buffer = []
    tail = "".join(buffer).strip()
    if tail:
        sentences.append(tail)
    return sentences


def expected_emotion(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("\"") or stripped.startswith("“"):
        return "dialogue"
    for keyword, emotion in EMOTION_KEYWORDS:
        if keyword in stripped:
            return emotion
    if "..." in stripped:
        return "whispered_tension"
    return "neutral_literary"


def expected_pause_profile(text: str, emotion: str) -> dict[str, int]:
    profile = punctuation_profile(text)
    return {
        "short_pause_ms": 250,
        "medium_pause_ms": 550 if profile["comma"] or profile["dash"] else 0,
        "long_pause_ms": 900 if profile["danda"] or profile["question"] or profile["exclamation"] else 0,
        "suspense_pause_ms": 1200 if emotion in {"eerie", "suspense", "whispered_tension"} else 0,
    }


def intensity_for_emotion(emotion: str) -> float:
    if emotion in {"fear", "anger_restrained", "whispered_tension"}:
        return 0.5
    if emotion in {"eerie", "suspense", "sorrow", "wonder"}:
        return 0.4
    if emotion == "dialogue":
        return 0.35
    return 0.2


def speaker_style_for_emotion(emotion: str) -> str:
    if emotion == "dialogue":
        return "gentle_dialogue_distinction"
    if emotion in {"eerie", "suspense", "whispered_tension"}:
        return "quiet_gothic_tension"
    return "literary_narration"


def chunk_paragraph(
    book_slug: str,
    chapter_id: str,
    paragraph_id: str,
    paragraph: str,
    *,
    start_index: int,
    target_min_chars: int = 80,
    target_max_chars: int = 220,
) -> list[dict[str, Any]]:
    sentences = split_sentences(paragraph)
    chunks: list[dict[str, Any]] = []
    current: list[str] = []
    index = start_index

    def flush() -> None:
        nonlocal current, index
        text = " ".join(current).strip()
        if not text:
            current = []
            return
        normalized = normalize_bengali_text(text)
        emotion = expected_emotion(normalized)
        chunk = {
            "chunk_id": deterministic_chunk_id(book_slug, chapter_id, index, normalized),
            "chapter_id": chapter_id,
            "paragraph_ids": [paragraph_id],
            "text": text,
            "text_normalized": normalized,
            "punctuation_profile": punctuation_profile(normalized),
            "expected_pause_profile": expected_pause_profile(normalized, emotion),
            "expected_emotion": emotion,
            "intensity": intensity_for_emotion(emotion),
            "speaker_style": speaker_style_for_emotion(emotion),
            "pronunciation_notes": [],
            "context_before": "",
            "context_after": "",
            "regeneration_status": "INTERNAL_REVIEW_ONLY_NOT_GENERATED",
        }
        chunks.append(chunk)
        index += 1
        current = []

    for sentence in sentences:
        candidate = " ".join([*current, sentence]).strip()
        if current and len(candidate) > target_max_chars and len(" ".join(current)) >= target_min_chars:
            flush()
        current.append(sentence)
    flush()

    for offset, chunk in enumerate(chunks):
        if offset > 0:
            chunk["context_before"] = chunks[offset - 1]["text_normalized"][-96:]
        if offset + 1 < len(chunks):
            chunk["context_after"] = chunks[offset + 1]["text_normalized"][:96]
    return chunks


def chunk_text(book_slug: str, text: str) -> list[dict[str, Any]]:
    normalized = normalize_bengali_text(text)
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", normalized) if paragraph.strip()]
    chunks: list[dict[str, Any]] = []
    chunk_index = 1
    for paragraph_index, paragraph in enumerate(paragraphs, start=1):
        if paragraph_index == 1 and len(paragraph) <= 80:
            chapter_id = "chapter-001"
        else:
            chapter_id = "chapter-001"
        paragraph_id = f"p-{paragraph_index:03d}"
        paragraph_chunks = chunk_paragraph(
            book_slug,
            chapter_id,
            paragraph_id,
            paragraph,
            start_index=chunk_index,
        )
        chunks.extend(paragraph_chunks)
        chunk_index += len(paragraph_chunks)
    return chunks


def approved_source_status(input_path: Path | None = None) -> dict[str, Any]:
    metadata = {}
    if SOURCE_METADATA_PATH.exists():
        metadata = json.loads(SOURCE_METADATA_PATH.read_text(encoding="utf-8"))
    source_path = input_path or APPROVED_SOURCE_TEXT_PATH
    ready = (
        source_path.exists()
        and metadata.get("rights_tier") == "A"
        and metadata.get("verification_status") == "approved"
        and metadata.get("qa_status") == "QA_PASSED"
        and metadata.get("full_source_text_committed") is True
    )
    display_source_path = str(source_path)
    display_metadata_path = str(SOURCE_METADATA_PATH)
    try:
        display_source_path = str(source_path.relative_to(ROOT))
    except ValueError:
        pass
    try:
        display_metadata_path = str(SOURCE_METADATA_PATH.relative_to(ROOT))
    except ValueError:
        pass
    return {
        "status": "READY" if ready else "OPERATOR_REQUIRED",
        "source_path": display_source_path,
        "source_file_exists": source_path.exists(),
        "source_metadata_path": display_metadata_path,
        "source_hash": metadata.get("source_hash", ""),
        "content_hash": metadata.get("content_hash", ""),
        "provenance_hash": metadata.get("provenance_hash", ""),
        "full_source_text_committed": metadata.get("full_source_text_committed") is True,
        "rights_tier": metadata.get("rights_tier", ""),
        "verification_status": metadata.get("verification_status", ""),
        "qa_status": metadata.get("qa_status", ""),
        "blocking_reason": ""
        if ready
        else "Approved Kshudhita Pashan full source text is not committed; official bake-off chunks cannot be generated.",
    }


def load_text(input_path: Path | None, *, allow_sample_fixture: bool = False) -> str:
    if input_path and input_path.exists():
        return input_path.read_text(encoding="utf-8")
    if allow_sample_fixture:
        return SAMPLE_TEXT
    return ""


def write_outputs(chunks: list[dict[str, Any]], output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_status = approved_source_status()
    json_payload = {
        "book_slug": DEFAULT_BOOK_SLUG,
        "scope": "INTERNAL_REVIEW_ONLY",
        "source_status": source_status["status"],
        "blocking_reason": source_status["blocking_reason"],
        "chunk_count": len(chunks),
        "chunks": chunks,
        "public_audio_urls_created": false_value(),
    }
    (output_dir / "chunks.json").write_text(json.dumps(json_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Kshudhita Pashan Audiobook Chunks",
        "",
        "Scope: `INTERNAL_REVIEW_ONLY`. No audio was generated or published.",
        "",
    ]
    if not chunks:
        lines.extend(
            [
                "Status: `OPERATOR_REQUIRED`.",
                "",
                source_status["blocking_reason"],
                "",
            ]
        )
    for chunk in chunks:
        lines.extend(
            [
                f"## {chunk['chunk_id']}",
                "",
                f"- Emotion: `{chunk['expected_emotion']}`",
                f"- Intensity: `{chunk['intensity']}`",
                f"- Speaker style: `{chunk['speaker_style']}`",
                "",
                chunk["text_normalized"],
                "",
            ]
        )
    (output_dir / "chunks.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    write_coverage_report(chunks, output_dir, source_status)


def write_coverage_report(chunks: list[dict[str, Any]], output_dir: Path, source_status: dict[str, Any]) -> None:
    emotion_distribution: dict[str, int] = {}
    punctuation_distribution = {"danda": 0, "comma": 0, "question": 0, "exclamation": 0, "ellipsis": 0, "dash": 0}
    for chunk in chunks:
        emotion = str(chunk.get("expected_emotion") or "unknown")
        emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + 1
        profile = chunk.get("punctuation_profile") or {}
        for key in punctuation_distribution:
            punctuation_distribution[key] += int(profile.get(key) or 0)
    lines = [
        "# Bengali Audiobook Chunk Coverage Report",
        "",
        "Book: Kshudhita Pashan / Hungry Stones",
        "",
        f"Source file: `{source_status['source_path']}`",
        f"Source hash: `{source_status['source_hash']}`",
        f"Source status: `{source_status['status']}`",
        f"Selected chunk count: `{len(chunks)}`",
        "",
    ]
    if source_status["status"] != "READY":
        lines.extend(
            [
                "## Operator Required",
                "",
                source_status["blocking_reason"],
                "",
                "No official Bengali model bake-off score may use synthetic sample text.",
                "",
            ]
        )
    lines.extend(["## Emotion Distribution", ""])
    if emotion_distribution:
        for key, value in sorted(emotion_distribution.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- OPERATOR_REQUIRED: 0")
    lines.extend(["", "## Punctuation Distribution", ""])
    for key, value in sorted(punctuation_distribution.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Skipped Sections", ""])
    if not chunks:
        lines.append("- All sections skipped because approved full source text is unavailable.")
    else:
        lines.append("- Full-source section accounting is pending approved source ingestion.")
    lines.append("")
    (ROOT / "BENGALI_AUDIOBOOK_CHUNK_COVERAGE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def false_value() -> bool:
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunk Bengali source text for internal audiobook bake-off.")
    parser.add_argument("--book-slug", default=DEFAULT_BOOK_SLUG)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-sample-fixture", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status = approved_source_status(args.input)
    text = load_text(args.input, allow_sample_fixture=args.allow_sample_fixture)
    if status["status"] != "READY" and not args.allow_sample_fixture:
        write_outputs([], args.output_dir)
        print(status["blocking_reason"])
        return 0
    chunks = chunk_text(args.book_slug, text)
    write_outputs(chunks, args.output_dir)
    print(f"Wrote {len(chunks)} internal-review chunks to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
