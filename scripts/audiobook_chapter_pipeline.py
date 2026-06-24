#!/usr/bin/env python3
"""Reusable internal audiobook chapter pipeline.

Pipeline stages:
LOAD_CHAPTER_SOURCE -> SANITIZE_NARRATION_TEXT -> VALIDATE_NARRATION_TEXT ->
BUILD_SENTENCE_MAP -> BUILD_CHUNK_MANIFEST -> COST_ESTIMATE_AND_BUDGET_GATE ->
PROVIDER_EVIDENCE_GATE -> ELEVENLABS_GENERATION_DRY_RUN_OR_EXECUTE ->
IMPORT_AND_HASH_AUDIO -> BUILD_SYNC_MANIFEST -> BUILD_QA_PACKETS ->
PUBLIC_RELEASE_BLOCK_GATE.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.elevenlabs_tts_client import (  # noqa: E402
    ElevenLabsSafetyError,
    ElevenLabsSettings,
    dry_run_generation_record,
    generate_tts_audio,
)
from scripts.tts_provider_internal_eval_review import (  # noqa: E402
    selected_provider_decision,
    review_provider_candidates,
)
from scripts.validate_elevenlabs_narration_text import validate_sample_dir  # noqa: E402


INTERNAL_AUDIOBOOK_ROOT = ROOT / "internal" / "audiobook_lab"
PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
PRODUCTION_BLOCKED = "PRODUCTION_BLOCKED"
HOLD_SYNC_QA_REQUIRED = "HOLD_SYNC_QA_REQUIRED"
DRY_RUN_READY = "DRY_RUN_READY"
BLOCKED_REAL_GENERATION = "BLOCKED_UNTIL_EXPLICIT_EXECUTE_AND_PROVIDER_EVIDENCE"
ELIGIBLE_INTERNAL_EVAL_ONLY = "ELIGIBLE_INTERNAL_EVAL_ONLY"
AUDIO_FILE_EXTENSIONS = {".aac", ".m4a", ".mp3", ".ogg", ".wav"}
NARRATION_MODE_PREMIUM = "premium_audiobook"
NARRATION_MODE_FULL_FIDELITY = "full_fidelity"
NARRATION_DECISIONS = {"speak", "transform", "metadata_only", "silence_pause"}

STAGES = (
    "LOAD_CHAPTER_SOURCE",
    "SANITIZE_NARRATION_TEXT",
    "VALIDATE_NARRATION_TEXT",
    "BUILD_SENTENCE_MAP",
    "BUILD_CHUNK_MANIFEST",
    "COST_ESTIMATE_AND_BUDGET_GATE",
    "PROVIDER_EVIDENCE_GATE",
    "ELEVENLABS_GENERATION_DRY_RUN_OR_EXECUTE",
    "IMPORT_AND_HASH_AUDIO",
    "BUILD_SYNC_MANIFEST",
    "BUILD_QA_PACKETS",
    "PUBLIC_RELEASE_BLOCK_GATE",
)

DRACULA_TERMS = [
    "Harker",
    "Bistritz",
    "Buda-Pesth",
    "Klausenburgh",
    "paprika hendl",
    "Carpathians",
    "Transylvania",
    "Moldavia",
    "Bukovina",
    "Borgo Pass",
    "Mina",
    "Dracula",
    "slivovitz",
    "calèche",
]


@dataclass
class StageRecord:
    name: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)


@dataclass
class ChapterPipelineResult:
    book_slug: str
    language: str
    chapter: int
    provider: str
    voice_id: str
    voice_name: str
    mode: str
    execute: bool
    status: str
    output_dir: Path
    generated_at: str
    stages: list[StageRecord]
    files: dict[str, str]
    cost_estimate: dict[str, Any]
    provider_gate: dict[str, Any]
    generation: dict[str, Any]
    public_release: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "unknown"


def chapter_dir(book_slug: str, language: str, chapter: int) -> Path:
    return INTERNAL_AUDIOBOOK_ROOT / safe_slug(book_slug) / language.lower() / f"chapter-{chapter}"


def legacy_full_dir(book_slug: str, language: str, chapter: int) -> Path:
    return INTERNAL_AUDIOBOOK_ROOT / safe_slug(book_slug) / language.lower() / f"chapter-{chapter}-elevenlabs-full"


def html_to_text(value: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>", "\n", value)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def controlled_chapter_path(book_slug: str, chapter: int) -> Path:
    return ROOT / "data" / "controlled_publications" / safe_slug(book_slug) / "chapters" / f"chapter-{chapter:03d}.json"


def load_chapter_source(book_slug: str, language: str, chapter: int) -> tuple[str, str, str]:
    existing_sync = legacy_full_dir(book_slug, language, chapter) / "full_chapter_sync_source_with_ids.txt"
    if existing_sync.exists():
        return "legacy_sync_source", "Existing internal sync source", existing_sync.read_text(encoding="utf-8")

    chapter_path = controlled_chapter_path(book_slug, chapter)
    if chapter_path.exists():
        payload = json.loads(chapter_path.read_text(encoding="utf-8"))
        title = str(payload.get("title") or f"Chapter {chapter}")
        content = html_to_text(str(payload.get("content") or ""))
        return "controlled_publication_chapter", title, "\n\n".join([title, content]).strip()

    sample_path = ROOT / "onboarding" / "books" / f"{safe_slug(book_slug)}-source-sample.txt"
    if sample_path.exists():
        return "onboarding_source_sample", f"Chapter {chapter}", sample_path.read_text(encoding="utf-8")

    return (
        "fallback_placeholder",
        f"Chapter {chapter}",
        f"Chapter {chapter}.\nThe chapter source is pending owner review.",
    )


def roman_to_words(value: str) -> str:
    mapping = {
        "I": "One",
        "II": "Two",
        "III": "Three",
        "IV": "Four",
        "V": "Five",
        "VI": "Six",
        "VII": "Seven",
        "VIII": "Eight",
        "IX": "Nine",
        "X": "Ten",
    }
    return mapping.get(value.upper(), value.title())


def ordinal_day(value: str) -> str:
    mapping = {
        "1": "first",
        "2": "second",
        "3": "third",
        "4": "fourth",
        "5": "fifth",
        "6": "sixth",
        "7": "seventh",
        "8": "eighth",
        "9": "ninth",
        "10": "tenth",
        "11": "eleventh",
        "12": "twelfth",
        "13": "thirteenth",
        "14": "fourteenth",
        "15": "fifteenth",
        "16": "sixteenth",
        "17": "seventeenth",
        "18": "eighteenth",
        "19": "nineteenth",
        "20": "twentieth",
        "21": "twenty-first",
        "22": "twenty-second",
        "23": "twenty-third",
        "24": "twenty-fourth",
        "25": "twenty-fifth",
        "26": "twenty-sixth",
        "27": "twenty-seventh",
        "28": "twenty-eighth",
        "29": "twenty-ninth",
        "30": "thirtieth",
        "31": "thirty-first",
    }
    return mapping.get(value, value)


def normalize_title(text: str) -> str:
    match = re.match(r"^CHAPTER\s+([IVXLCDM]+)\.\s*(.+)$", text.strip(), flags=re.IGNORECASE)
    if match:
        subtitle = match.group(2).strip().rstrip(".").replace("’", "'")
        subtitle = " ".join(word[:1].upper() + word[1:] for word in subtitle.lower().split())
        return f"Chapter {roman_to_words(match.group(1))}. {subtitle}."
    return text


def normalize_date_markers(text: str) -> str:
    months = "January|February|March|April|May|June|July|August|September|October|November|December"

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(2)} the {ordinal_day(match.group(1))}."

    return re.sub(rf"\b(\d{{1,2}})\s+({months})\.", repl, text)


def clean_narration_sentence(
    source_text: str,
    narration_mode: str = NARRATION_MODE_PREMIUM,
) -> tuple[str, dict[str, Any]]:
    original_text = source_text.strip()
    text = original_text
    metadata: dict[str, Any] = {
        "sync_action": "narrate",
        "narration_decision": "speak",
        "narration_mode": narration_mode,
    }
    if not text:
        return "", metadata
    if re.fullmatch(r"\*\s+\*\s+\*\s+\*\s+\*", text):
        return "", {
            "sync_action": "pause_only",
            "narration_decision": "silence_pause",
            "narration_mode": narration_mode,
            "silence_ms": 750,
            "reason": "section_break",
        }
    if re.search(r"Do not narrate|Internal-only|Public audio release|NOT FOR ELEVENLABS", text, re.IGNORECASE):
        return "", {
            "sync_action": "metadata_only",
            "narration_decision": "metadata_only",
            "narration_mode": narration_mode,
            "reason": "internal_instruction",
        }
    if (
        narration_mode == NARRATION_MODE_PREMIUM
        and re.fullmatch(r"\(_Kept in shorthand\._\)", text, flags=re.IGNORECASE)
    ):
        return "", {
            "sync_action": "metadata_only",
            "narration_decision": "metadata_only",
            "narration_mode": narration_mode,
            "reason": "metadata_only_paratext_shorthand_note",
            "source_role": "paratext",
        }

    text = normalize_title(text)
    if narration_mode == NARRATION_MODE_FULL_FIDELITY:
        text = text.replace("(_Kept in shorthand._)", "Kept in shorthand.")
    text = re.sub(r"\(_Mem\._,\s*([^)]+)\)", r"Memorandum: \1", text)
    text = re.sub(r"\(Mem\.,\s*([^)]+)\)", r"Memorandum: \1", text)
    text = text.replace("_", "")
    text = normalize_date_markers(text)
    if narration_mode == NARRATION_MODE_PREMIUM and original_text == "_3 May.":
        text = "May the third. Bistritz."
    if narration_mode == NARRATION_MODE_PREMIUM:
        text = re.sub(r"^Bistritz\.\s*--\s*", "", text)
    text = re.sub(r":--", ":", text)
    text = re.sub(r"\.--", ". ", text)
    text = re.sub(r",--", ", ", text)
    text = re.sub(r";--", "; ", text)
    text = re.sub(r"\s*--\s*", " — ", text)
    text = re.sub(r"\b([AP])\.\s*M\.", r"\1.M.", text)
    if narration_mode == NARRATION_MODE_PREMIUM:
        text = re.sub(r"\bon 1st May\b", "on the first of May", text)
        text = re.sub(r"\bbut train was an hour late\b", "but the train was an hour late", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = text.strip()
    if text != original_text:
        metadata["narration_decision"] = "transform"
    return text, metadata


def split_plain_source_into_sentences(raw_source: str) -> list[str]:
    text = html_to_text(raw_source)
    text = re.sub(r"(?m)^\s*#.*$", "", text)
    text = re.sub(r"\[s\d{3}\]\s*", "", text)
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    sentences: list[str] = []
    for paragraph in paragraphs:
        parts = re.split(r"(?<=[.!?])\s+(?=[“\"A-Z0-9])", paragraph)
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                sentences.append(cleaned)
    return sentences


def source_items(raw_source: str, title: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_line in raw_source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^\[(s\d{3})\]\s*(.+)$", line)
        if match:
            items.append({"sentence_id": match.group(1), "source_text": match.group(2).strip()})
    if items:
        return items

    candidates = split_plain_source_into_sentences(raw_source)
    if title and (not candidates or candidates[0].strip() != title.strip()):
        candidates.insert(0, title.strip())
    return [
        {"sentence_id": f"s{index:03d}", "source_text": source_text}
        for index, source_text in enumerate(candidates, start=1)
    ]


def build_sentence_map(
    items: list[dict[str, Any]],
    narration_mode: str = NARRATION_MODE_PREMIUM,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        narration_text, metadata = clean_narration_sentence(str(item["source_text"]), narration_mode=narration_mode)
        entry = {
            "source_text": item["source_text"],
            "narration_text": narration_text,
            "sync_action": metadata.get("sync_action", "narrate"),
            "narration_decision": metadata.get("narration_decision", "speak"),
            "narration_mode": metadata.get("narration_mode", narration_mode),
        }
        if metadata.get("silence_ms"):
            entry["silence_ms"] = metadata["silence_ms"]
        if metadata.get("reason"):
            entry["reason"] = metadata["reason"]
        if metadata.get("source_role"):
            entry["source_role"] = metadata["source_role"]
        result[str(item["sentence_id"])] = entry
    return result


def narration_lines(sentence_map: dict[str, dict[str, Any]], ids: list[str] | None = None) -> list[str]:
    selected_ids = ids or list(sentence_map)
    return [
        str(sentence_map[sentence_id].get("narration_text") or "").strip()
        for sentence_id in selected_ids
        if str(sentence_map.get(sentence_id, {}).get("narration_text") or "").strip()
    ]


def estimate_duration_seconds(text: str) -> float:
    words = len(re.findall(r"\b[\w’'-]+\b", text))
    return round(max(3.0, words * 0.39), 1)


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text))


def build_chunks_from_existing(
    legacy_manifest_path: Path,
    sentence_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]] | None:
    if not legacy_manifest_path.exists():
        return None
    legacy = json.loads(legacy_manifest_path.read_text(encoding="utf-8"))
    chunks: list[dict[str, Any]] = []
    for legacy_chunk in legacy.get("chunks", []):
        sentence_ids = list(legacy_chunk.get("sentence_ids") or [])
        if not sentence_ids:
            start = int(str(legacy_chunk.get("sentence_start", "s000"))[1:])
            end = int(str(legacy_chunk.get("sentence_end", "s000"))[1:])
            sentence_ids = [f"s{index:03d}" for index in range(start, end + 1)]
        text = "\n".join(narration_lines(sentence_map, sentence_ids))
        chunk = {
            "chunk_id": legacy_chunk.get("chunk_id"),
            "chapter": legacy_chunk.get("chapter", 1),
            "sentence_start": sentence_ids[0],
            "sentence_end": sentence_ids[-1],
            "sentence_ids": sentence_ids,
            "sentence_count": len(sentence_ids),
            "word_count": word_count(text),
            "recommended_seconds_min": 45,
            "recommended_seconds_max": 120,
            "preserve_paragraph_boundaries": bool(legacy_chunk.get("preserve_paragraph_boundaries", True)),
            "audio_filename": legacy_chunk.get(
                "audio_filename",
                f"chapter-{legacy_chunk.get('chunk_id', 'c000')}.mp3",
            ),
            "narration_text": text,
            "text_hash": sha256_text(text),
            "settings_hash": legacy_chunk.get("settings_hash", ""),
            "estimated_duration_seconds": estimate_duration_seconds(text),
            "generation_status": "NOT_GENERATED",
        }
        if "s084" in sentence_ids and sentence_map.get("s084", {}).get("narration_decision") == "silence_pause":
            chunk["silence_markers"] = [
                {
                    "sentence_id": "s084",
                    "marker_type": "section_break",
                    "silence_ms": sentence_map["s084"].get("silence_ms", 750),
                    "placement": "between s083 and s085",
                }
            ]
        chunks.append(chunk)
    return chunks


def build_chunks(
    *,
    book_slug: str,
    language: str,
    chapter: int,
    sentence_map: dict[str, dict[str, Any]],
    target_seconds: int,
) -> list[dict[str, Any]]:
    legacy_chunks = build_chunks_from_existing(
        legacy_full_dir(book_slug, language, chapter) / "chunk_manifest.json",
        sentence_map,
    )
    if legacy_chunks:
        return legacy_chunks

    chunks: list[dict[str, Any]] = []
    current_ids: list[str] = []
    current_lines: list[str] = []
    for sentence_id, entry in sentence_map.items():
        current_ids.append(sentence_id)
        narration_text = str(entry.get("narration_text") or "").strip()
        if narration_text:
            current_lines.append(narration_text)
        text = "\n".join(current_lines)
        if current_lines and estimate_duration_seconds(text) >= target_seconds:
            chunks.append(make_chunk(chapter, len(chunks) + 1, current_ids, text))
            current_ids = []
            current_lines = []
    if current_ids:
        chunks.append(make_chunk(chapter, len(chunks) + 1, current_ids, "\n".join(current_lines)))
    return chunks


def make_chunk(chapter: int, index: int, sentence_ids: list[str], text: str) -> dict[str, Any]:
    chunk_id = f"c{index:03d}"
    return {
        "chunk_id": chunk_id,
        "chapter": chapter,
        "sentence_start": sentence_ids[0],
        "sentence_end": sentence_ids[-1],
        "sentence_ids": sentence_ids,
        "sentence_count": len(sentence_ids),
        "word_count": word_count(text),
        "recommended_seconds_min": 45,
        "recommended_seconds_max": 120,
        "preserve_paragraph_boundaries": True,
        "audio_filename": f"chapter-{chapter:03d}-{chunk_id}.mp3",
        "narration_text": text,
        "text_hash": sha256_text(text),
        "settings_hash": "",
        "estimated_duration_seconds": estimate_duration_seconds(text),
        "generation_status": "NOT_GENERATED",
    }


def config_defaults(
    *,
    book_slug: str,
    language: str,
    chapter: int,
    provider: str,
    voice_id: str,
    voice_name: str,
    max_cost_inr: float | None,
    max_chunks: int | None,
    narration_mode: str,
) -> dict[str, Any]:
    return {
        "book_slug": safe_slug(book_slug),
        "language": language,
        "chapter": chapter,
        "narration_mode": narration_mode,
        "provider": provider,
        "voice_id": voice_id,
        "voice_name": voice_name,
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128",
        "speed": 1.0,
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style_exaggeration": 0.0,
        "speaker_boost": True,
        "max_cost_inr": max_cost_inr,
        "max_chunks": max_chunks,
        "chunk_duration_target_seconds": 90,
        "beta_services_allowed": False,
        "voice_cloning_allowed": False,
        "elevenreader_allowed": False,
        "public_release_target": False,
    }


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if re.search(r"[:#\n]", text):
        return json.dumps(text, ensure_ascii=False)
    return text


def write_simple_yaml(path: Path, payload: dict[str, Any]) -> None:
    lines = [f"{key}: {yaml_scalar(value)}" for key, value in payload.items()]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_pronunciation_dictionary(path: Path, book_slug: str) -> list[dict[str, str]]:
    terms = DRACULA_TERMS if safe_slug(book_slug) == "dracula" else []
    entries = [{"term": term, "note": "owner_review_required"} for term in terms]
    lines = [
        "provider: elevenlabs",
        "external_dictionary_required_now: false",
        "pronunciation_dictionary_locators: []",
        "terms:",
    ]
    if entries:
        for entry in entries:
            lines.append(f"  - term: {entry['term']}")
            lines.append(f"    note: {entry['note']}")
    else:
        lines.append("  []")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return entries


def cost_estimate(chunks: list[dict[str, Any]], max_cost_inr: float | None, max_chunks: int | None) -> dict[str, Any]:
    selected = chunks[: max_chunks or len(chunks)]
    characters = sum(len(chunk["narration_text"]) for chunk in selected)
    estimated_cost = round((characters / 1000.0) * 2.0, 2)
    return {
        "currency": "INR",
        "estimated_character_count": characters,
        "estimated_cost_inr": estimated_cost,
        "estimate_basis": "conservative_internal_planning_rate_inr_2_per_1000_chars",
        "max_cost_inr": max_cost_inr,
        "max_chunks": max_chunks,
        "selected_chunk_count": len(selected),
        "within_budget": bool(max_cost_inr is not None and estimated_cost <= max_cost_inr),
        "budget_cap_present": max_cost_inr is not None,
        "max_chunks_cap_present": max_chunks is not None,
    }


def provider_gate(provider: str) -> dict[str, Any]:
    if provider.lower() != "elevenlabs":
        return {
            "provider": provider,
            "status": "UNSUPPORTED_PROVIDER",
            "internal_generation_status": "BLOCKED",
            "eligible_for_execute": False,
            "blockers": ["only elevenlabs is currently wired for provider automation"],
        }
    selected = selected_provider_decision("elevenlabs", review_provider_candidates())
    return {
        "provider": "elevenlabs",
        "status": selected.internal_eval_status,
        "decision": selected.decision_status,
        "internal_generation_status": selected.internal_generation_status,
        "production_status": selected.public_production_status,
        "eligible_for_execute": selected.internal_generation_status == ELIGIBLE_INTERNAL_EVAL_ONLY,
        "blockers": selected.issues,
        "warnings": selected.warnings,
    }


def public_audio_files() -> list[str]:
    matches: list[str] = []
    for relative in ("frontend/public", "frontend/build"):
        root = ROOT / relative
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS:
                matches.append(str(path.relative_to(ROOT)))
    return sorted(matches)


def build_sync_manifest(
    *,
    book_slug: str,
    language: str,
    chapter: int,
    sentence_map: dict[str, dict[str, Any]],
    chunks: list[dict[str, Any]],
    generated_audio: dict[str, Any],
) -> dict[str, Any]:
    chunk_audio_hash = {
        item.get("chunk_id"): item.get("audio_hash") or "sha256:placeholder-no-audio-generated"
        for item in generated_audio.get("chunks", [])
    }
    sentence_to_chunk = {
        sentence_id: chunk["chunk_id"]
        for chunk in chunks
        for sentence_id in chunk.get("sentence_ids", [])
    }
    items: list[dict[str, Any]] = []
    for sentence_id, entry in sentence_map.items():
        chunk_id = sentence_to_chunk.get(sentence_id, "")
        items.append(
            {
                "text_fragment_id": f"{safe_slug(book_slug)}-chapter-{chapter:03d}-{sentence_id}",
                "sentence_id": sentence_id,
                "chapter": chapter,
                "language": language,
                "text": entry.get("narration_text") or entry.get("source_text"),
                "source_text": entry.get("source_text"),
                "narration_decision": entry.get("narration_decision", "speak"),
                "narration_mode": entry.get("narration_mode", NARRATION_MODE_PREMIUM),
                "chunk_id": chunk_id,
                "start_ms": None,
                "end_ms": None,
                "timing_source": "placeholder_manual_alignment_required",
                "sync_level": "sentence",
                "sync_status": HOLD_SYNC_QA_REQUIRED,
                "audio_hash": chunk_audio_hash.get(chunk_id, "sha256:placeholder-no-audio-generated"),
                "public": False,
            }
        )
    return {
        "generated_by": "scripts/audiobook_chapter_pipeline.py",
        "generated_at": utc_now(),
        "book_slug": safe_slug(book_slug),
        "chapter": chapter,
        "language": language,
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "items": items,
        "chunks": [
            {
                "chunk_id": chunk["chunk_id"],
                "sentence_start": chunk["sentence_start"],
                "sentence_end": chunk["sentence_end"],
                "audio_hash": chunk_audio_hash.get(chunk["chunk_id"], ""),
                "public": False,
            }
            for chunk in chunks
        ],
    }


def result_payload(result: ChapterPipelineResult) -> dict[str, Any]:
    return {
        "book_slug": result.book_slug,
        "language": result.language,
        "chapter": result.chapter,
        "provider": result.provider,
        "voice_id": result.voice_id,
        "voice_name": result.voice_name,
        "mode": result.mode,
        "execute": result.execute,
        "status": result.status,
        "output_dir": str(result.output_dir.relative_to(ROOT)),
        "generated_at": result.generated_at,
        "stages": [
            {
                "name": stage.name,
                "status": stage.status,
                "details": stage.details,
                "blockers": stage.blockers,
            }
            for stage in result.stages
        ],
        "files": result.files,
        "cost_estimate": result.cost_estimate,
        "provider_gate": result.provider_gate,
        "generation": result.generation,
        "public_release": result.public_release,
    }


def markdown_reports(result: ChapterPipelineResult) -> dict[str, str]:
    payload = result_payload(result)
    stage_rows = "\n".join(
        f"| {stage['name']} | {stage['status']} | {'; '.join(stage['blockers'][:2]) if stage['blockers'] else 'No blocker.'} |"
        for stage in payload["stages"]
    )
    pipeline_report = "\n".join(
        [
            "# Audiobook Chapter Pipeline Report",
            "",
            f"- Book: `{result.book_slug}`",
            f"- Language: `{result.language}`",
            f"- Chapter: `{result.chapter}`",
            f"- Status: `{result.status}`",
            f"- Mode: `{result.mode}`",
            f"- Execute: `{str(result.execute).lower()}`",
            f"- Public audio: `{PUBLIC_AUDIO_RELEASE_BLOCKED}`",
            f"- Production: `{PRODUCTION_BLOCKED}`",
            "",
            "| Stage | Status | Notes |",
            "| --- | --- | --- |",
            stage_rows,
            "",
        ]
    )
    sanitation_report = "\n".join(
        [
            "# Audiobook Narration Sanitization Report",
            "",
            f"- Clean narration file: `{result.files.get('narration_text')}`",
            f"- Sync/source file: `{result.files.get('sync_source')}`",
            f"- Sentence map: `{result.files.get('sentence_map')}`",
            f"- Sentence count: `{payload['stages'][3]['details'].get('sentence_count')}`",
            "- Sentence IDs are retained only in sync/source and sentence-map artifacts.",
            "- Generation input is clean narration text only.",
            "",
        ]
    )
    chunk_report = "\n".join(
        [
            "# Audiobook Chunk Generation Plan",
            "",
            f"- Chunk manifest: `{result.files.get('chunk_manifest')}`",
            f"- Chunk count: `{payload['generation'].get('chunk_count')}`",
            f"- Selected chunks for execute mode: `{payload['cost_estimate'].get('selected_chunk_count')}`",
            "- Generation status defaults to dry-run/not generated.",
            "- Full-book generation remains blocked.",
            "",
        ]
    )
    cost_report = "\n".join(
        [
            "# Audiobook Cost Control Report",
            "",
            f"- Estimated characters: `{result.cost_estimate.get('estimated_character_count')}`",
            f"- Estimated cost INR: `{result.cost_estimate.get('estimated_cost_inr')}`",
            f"- Max cost INR: `{result.cost_estimate.get('max_cost_inr')}`",
            f"- Max chunks: `{result.cost_estimate.get('max_chunks')}`",
            f"- Within budget: `{str(result.cost_estimate.get('within_budget')).lower()}`",
            "- Real generation requires explicit execute, eligible provider evidence, owner approval, and budget caps.",
            "",
        ]
    )
    return {
        "AUDIOBOOK_CHAPTER_PIPELINE_REPORT.md": pipeline_report,
        "AUDIOBOOK_NARRATION_SANITIZATION_REPORT.md": sanitation_report,
        "AUDIOBOOK_CHUNK_GENERATION_PLAN.md": chunk_report,
        "AUDIOBOOK_COST_CONTROL_REPORT.md": cost_report,
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_chapter_pipeline(
    *,
    book_slug: str,
    language: str,
    chapter: int | str,
    provider: str,
    voice_id: str,
    voice_name: str,
    mode: str = "dry-run",
    execute: bool = False,
    max_cost_inr: float | None = None,
    max_chunks: int | None = None,
    narration_mode: str = NARRATION_MODE_PREMIUM,
    write_root_reports: bool = True,
) -> ChapterPipelineResult:
    if narration_mode not in {NARRATION_MODE_PREMIUM, NARRATION_MODE_FULL_FIDELITY}:
        raise ValueError(f"unsupported narration_mode: {narration_mode}")
    chapter_number = int(chapter)
    output_dir = chapter_dir(book_slug, language, chapter_number)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_audio_dir = output_dir / "generated_audio"
    stage_records: list[StageRecord] = []

    source_method, title, raw_source = load_chapter_source(book_slug, language, chapter_number)
    source_hash = sha256_text(raw_source)
    stage_records.append(
        StageRecord(
            "LOAD_CHAPTER_SOURCE",
            "PASS",
            {"source_method": source_method, "source_hash": source_hash, "raw_characters": len(raw_source)},
        )
    )

    items = source_items(raw_source, title)
    sentence_map = build_sentence_map(items, narration_mode=narration_mode)
    sync_source_text = "\n".join(
        [
            f"# {safe_slug(book_slug)} chapter {chapter_number} sync/source with IDs",
            "# NOT FOR ELEVENLABS GENERATION.",
            "# Use full_chapter_narration_text.txt or chunk_manifest.json narration_text only.",
            "",
            *[f"[{item['sentence_id']}] {item['source_text']}" for item in items],
        ]
    ).rstrip() + "\n"
    narration_text = "\n".join(narration_lines(sentence_map)).rstrip() + "\n"
    stage_records.append(
        StageRecord(
            "SANITIZE_NARRATION_TEXT",
            "PASS",
            {
                "source_sentence_count": len(items),
                "narration_line_count": len([line for line in narration_text.splitlines() if line.strip()]),
                "clean_narration_hash": sha256_text(narration_text),
                "narration_mode": narration_mode,
            },
        )
    )

    config = config_defaults(
        book_slug=book_slug,
        language=language,
        chapter=chapter_number,
        provider=provider,
        voice_id=voice_id,
        voice_name=voice_name,
        max_cost_inr=max_cost_inr,
        max_chunks=max_chunks,
        narration_mode=narration_mode,
    )
    pipeline_config_path = output_dir / "pipeline_config.yml"
    sync_source_path = output_dir / "full_chapter_sync_source_with_ids.txt"
    narration_path = output_dir / "full_chapter_narration_text.txt"
    sentence_map_path = output_dir / "sentence_map.json"
    chunk_manifest_path = output_dir / "chunk_manifest.json"
    pronunciation_path = output_dir / "pronunciation_dictionary.yml"
    generated_manifest_path = output_dir / "generated_audio_manifest.json"
    sync_manifest_path = output_dir / "sync_manifest.json"
    qa_packet_path = output_dir / "qa_packet.json"

    sync_source_path.write_text(sync_source_text, encoding="utf-8")
    narration_path.write_text(narration_text, encoding="utf-8")
    write_json(sentence_map_path, sentence_map)
    write_simple_yaml(pipeline_config_path, config)
    pronunciation_entries = write_pronunciation_dictionary(pronunciation_path, book_slug)

    stage_records.append(
        StageRecord("BUILD_SENTENCE_MAP", "PASS", {"sentence_count": len(sentence_map), "sentence_map_path": str(sentence_map_path.relative_to(ROOT))})
    )

    chunks = build_chunks(
        book_slug=book_slug,
        language=language,
        chapter=chapter_number,
        sentence_map=sentence_map,
        target_seconds=int(config["chunk_duration_target_seconds"]),
    )
    settings = ElevenLabsSettings(
        provider=provider,
        voice_id=voice_id,
        voice_name=voice_name,
        model_id=str(config["model_id"]),
        output_format=str(config["output_format"]),
        speed=float(config["speed"]),
        stability=float(config["stability"]),
        similarity_boost=float(config["similarity_boost"]),
        style_exaggeration=float(config["style_exaggeration"]),
        speaker_boost=bool(config["speaker_boost"]),
        beta_services_allowed=bool(config["beta_services_allowed"]),
        voice_cloning_allowed=bool(config["voice_cloning_allowed"]),
        elevenreader_allowed=bool(config["elevenreader_allowed"]),
    )
    for chunk in chunks:
        chunk["settings_hash"] = settings.settings_hash()
    non_narrated_markers = [
        {
            "sentence_id": sentence_id,
            "chunk_id": next((chunk["chunk_id"] for chunk in chunks if sentence_id in chunk["sentence_ids"]), ""),
            "marker_type": "section_break" if entry.get("narration_decision") == "silence_pause" else "metadata_only_paratext",
            "silence_ms": entry.get("silence_ms", 750),
            "placement": "metadata_only",
            "reason": entry.get("reason", ""),
        }
        for sentence_id, entry in sentence_map.items()
        if entry.get("narration_decision") in {"metadata_only", "silence_pause"}
    ]
    chunk_manifest = {
        "generated_by": "scripts/audiobook_chapter_pipeline.py",
        "generated_at": utc_now(),
        "book_slug": safe_slug(book_slug),
        "language": language,
        "chapter": chapter_number,
        "narration_mode": narration_mode,
        "provider": "ElevenLabs" if provider.lower() == "elevenlabs" else provider,
        "voice_name": voice_name,
        "voice_id": voice_id,
        "model_id": config["model_id"],
        "audio_status": "INTERNAL_CHAPTER_ONLY_NOT_GENERATED",
        "generation_status": "NOT_GENERATED",
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_approved": False,
        "listen_now_cta_allowed": False,
        "audio_object_metadata_allowed": False,
        "full_book_generation_allowed": False,
        "source_sync_file": sync_source_path.name,
        "narration_text_file": narration_path.name,
        "sentence_map_file": sentence_map_path.name,
        "chapter_text_hash": source_hash,
        "chapter_narration_text_hash": sha256_text(narration_text),
        "sentence_count": len(sentence_map),
        "spoken_sentence_count": len(
            [entry for entry in sentence_map.values() if str(entry.get("narration_text") or "").strip()]
        ),
        "metadata_only_count": len(
            [entry for entry in sentence_map.values() if entry.get("narration_decision") == "metadata_only"]
        ),
        "silence_pause_count": len(
            [entry for entry in sentence_map.values() if entry.get("narration_decision") == "silence_pause"]
        ),
        "chunk_count": len(chunks),
        "non_narrated_markers": non_narrated_markers,
        "chunks": chunks,
    }
    write_json(chunk_manifest_path, chunk_manifest)
    stage_records.append(
        StageRecord("BUILD_CHUNK_MANIFEST", "PASS", {"chunk_count": len(chunks), "chunk_manifest_path": str(chunk_manifest_path.relative_to(ROOT))})
    )

    validation_summary = validate_sample_dir(output_dir)
    stage_records.insert(2, StageRecord("VALIDATE_NARRATION_TEXT", "PASS", validation_summary))

    estimate = cost_estimate(chunks, max_cost_inr, max_chunks)
    cost_blockers: list[str] = []
    if mode == "generate-internal" and not estimate["budget_cap_present"]:
        cost_blockers.append("max-cost-inr is required for generate-internal")
    if mode == "generate-internal" and not estimate["max_chunks_cap_present"]:
        cost_blockers.append("max-chunks is required for generate-internal")
    if mode == "generate-internal" and estimate["budget_cap_present"] and not estimate["within_budget"]:
        cost_blockers.append("estimated cost exceeds max-cost-inr")
    stage_records.append(
        StageRecord(
            "COST_ESTIMATE_AND_BUDGET_GATE",
            "PASS" if not cost_blockers else "BLOCKED",
            estimate,
            cost_blockers,
        )
    )

    provider_result = provider_gate(provider)
    provider_blockers = [] if provider_result["eligible_for_execute"] or mode == "dry-run" else list(provider_result["blockers"])
    stage_records.append(
        StageRecord(
            "PROVIDER_EVIDENCE_GATE",
            "PASS" if provider_result["eligible_for_execute"] else ("DRY_RUN_HOLD" if mode == "dry-run" else "BLOCKED"),
            provider_result,
            provider_blockers,
        )
    )

    execute_blockers: list[str] = []
    if mode == "generate-internal":
        if not execute:
            execute_blockers.append("generate-internal requires --execute")
        if "ELEVENLABS_API_KEY" not in os.environ or not os.environ.get("ELEVENLABS_API_KEY", "").strip():
            execute_blockers.append("ELEVENLABS_API_KEY is required for execute mode")
        if not provider_result["eligible_for_execute"]:
            execute_blockers.append("provider evidence status must be ELIGIBLE_INTERNAL_EVAL_ONLY")
        owner_approval_path = output_dir / "owner_generation_approval.md"
        if not owner_approval_path.exists():
            execute_blockers.append("owner approval file is required: owner_generation_approval.md")
        if not estimate["budget_cap_present"]:
            execute_blockers.append("budget cap is required")
        if not estimate["max_chunks_cap_present"]:
            execute_blockers.append("max chunks cap is required")
        if bool(config["beta_services_allowed"]) or bool(config["voice_cloning_allowed"]) or bool(config["elevenreader_allowed"]):
            execute_blockers.append("beta services, voice cloning, and ElevenReader must remain disabled")
        if bool(config["public_release_target"]):
            execute_blockers.append("public_release_target must be false")

    generation_records: list[dict[str, Any]] = []
    selected_chunks = chunks[: max_chunks or len(chunks)]
    for chunk in selected_chunks:
        output_path = generated_audio_dir / str(chunk["audio_filename"])
        if mode == "generate-internal" and execute and not execute_blockers:
            try:
                record = generate_tts_audio(
                    chunk_id=str(chunk["chunk_id"]),
                    text=str(chunk["narration_text"]),
                    settings=settings,
                    output_path=output_path,
                    execute=True,
                )
            except ElevenLabsSafetyError as exc:
                execute_blockers.append(str(exc))
                record = dry_run_generation_record(
                    chunk_id=str(chunk["chunk_id"]),
                    text=str(chunk["narration_text"]),
                    settings=settings,
                    output_path=output_path,
                )
        else:
            record = dry_run_generation_record(
                chunk_id=str(chunk["chunk_id"]),
                text=str(chunk["narration_text"]),
                settings=settings,
                output_path=output_path,
            )
        generation_records.append(record)

    generation_status = (
        "DRY_RUN_ONLY"
        if mode == "dry-run"
        else ("GENERATED_INTERNAL_ONLY" if not execute_blockers else BLOCKED_REAL_GENERATION)
    )
    generation_manifest = {
        "generated_by": "scripts/audiobook_chapter_pipeline.py",
        "generated_at": utc_now(),
        "book_slug": safe_slug(book_slug),
        "chapter": chapter_number,
        "provider": "ElevenLabs",
        "voice_name": voice_name,
        "voice_id": voice_id,
        "mode": mode,
        "execute": execute,
        "generation_status": generation_status,
        "provider_api_called": any(record.get("provider_api_called") for record in generation_records),
        "audio_generated_by_repo": any(record.get("generation_status") == "GENERATED_INTERNAL_ONLY" for record in generation_records),
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "chunks": generation_records,
        "blockers": execute_blockers,
    }
    write_json(generated_manifest_path, generation_manifest)
    stage_records.append(
        StageRecord(
            "ELEVENLABS_GENERATION_DRY_RUN_OR_EXECUTE",
            "PASS" if not execute_blockers else "BLOCKED",
            {
                "generation_status": generation_status,
                "provider_api_called": generation_manifest["provider_api_called"],
                "selected_chunk_count": len(selected_chunks),
            },
            execute_blockers,
        )
    )

    imported_audio = []
    for record in generation_records:
        output_path_text = str(record.get("output_path") or "")
        output_path = ROOT / output_path_text if output_path_text else None
        if output_path and output_path.exists() and output_path.suffix.lower() in AUDIO_FILE_EXTENSIONS:
            imported_audio.append(
                {
                    "chunk_id": record.get("chunk_id"),
                    "audio_path": output_path_text,
                    "audio_hash": sha256_file(output_path),
                    "public": False,
                }
            )
    stage_records.append(
        StageRecord(
            "IMPORT_AND_HASH_AUDIO",
            "DRY_RUN_NO_AUDIO" if not imported_audio else "PASS",
            {"imported_audio_count": len(imported_audio), "audio_hashes": imported_audio},
        )
    )

    sync_manifest = build_sync_manifest(
        book_slug=book_slug,
        language=language,
        chapter=chapter_number,
        sentence_map=sentence_map,
        chunks=chunks,
        generated_audio=generation_manifest,
    )
    write_json(sync_manifest_path, sync_manifest)
    stage_records.append(
        StageRecord("BUILD_SYNC_MANIFEST", "PASS", {"sync_status": HOLD_SYNC_QA_REQUIRED, "sync_manifest_path": str(sync_manifest_path.relative_to(ROOT))})
    )

    qa_packet = {
        "generated_by": "scripts/audiobook_chapter_pipeline.py",
        "generated_at": utc_now(),
        "book_slug": safe_slug(book_slug),
        "chapter": chapter_number,
        "decision": "DRY_RUN_READY" if mode == "dry-run" else generation_status,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "production_status": PRODUCTION_BLOCKED,
        "listen_now_cta_allowed": False,
        "audio_object_metadata_allowed": False,
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "qa_required": [
            "human_listening_qa",
            "text_fidelity_qa",
            "sentence_sync_qa",
            "accessibility_listening_qa",
        ],
        "pronunciation_dictionary_terms": pronunciation_entries,
    }
    write_json(qa_packet_path, qa_packet)
    stage_records.append(StageRecord("BUILD_QA_PACKETS", "PASS", {"qa_packet_path": str(qa_packet_path.relative_to(ROOT))}))

    public_audio = public_audio_files()
    public_release = {
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "production_status": PRODUCTION_BLOCKED,
        "public_audio_allowed": False,
        "listen_now_cta_allowed": False,
        "audio_object_metadata_allowed": False,
        "frontend_public_audio_files": public_audio,
        "frontend_build_audio_files": [path for path in public_audio if path.startswith("frontend/build/")],
    }
    stage_records.append(
        StageRecord(
            "PUBLIC_RELEASE_BLOCK_GATE",
            "PASS" if not public_audio else "BLOCKED",
            public_release,
            ["audio-like files are present in public/build"] if public_audio else [],
        )
    )

    status = DRY_RUN_READY if mode == "dry-run" else (generation_status if not execute_blockers else BLOCKED_REAL_GENERATION)
    files = {
        "pipeline_config": str(pipeline_config_path.relative_to(ROOT)),
        "pronunciation_dictionary": str(pronunciation_path.relative_to(ROOT)),
        "sync_source": str(sync_source_path.relative_to(ROOT)),
        "narration_text": str(narration_path.relative_to(ROOT)),
        "sentence_map": str(sentence_map_path.relative_to(ROOT)),
        "chunk_manifest": str(chunk_manifest_path.relative_to(ROOT)),
        "generated_audio_manifest": str(generated_manifest_path.relative_to(ROOT)),
        "sync_manifest": str(sync_manifest_path.relative_to(ROOT)),
        "qa_packet": str(qa_packet_path.relative_to(ROOT)),
    }
    result = ChapterPipelineResult(
        book_slug=safe_slug(book_slug),
        language=language,
        chapter=chapter_number,
        provider=provider,
        voice_id=voice_id,
        voice_name=voice_name,
        mode=mode,
        execute=execute,
        status=status,
        output_dir=output_dir,
        generated_at=utc_now(),
        stages=stage_records,
        files=files,
        cost_estimate=estimate,
        provider_gate=provider_result,
        generation={
            "generation_status": generation_status,
            "chunk_count": len(chunks),
            "selected_chunk_count": len(selected_chunks),
            "provider_api_called": generation_manifest["provider_api_called"],
            "audio_generated_by_repo": generation_manifest["audio_generated_by_repo"],
            "blockers": execute_blockers,
        },
        public_release=public_release,
    )

    reports = markdown_reports(result)
    for filename, text in reports.items():
        (output_dir / filename).write_text(text, encoding="utf-8")
        files[filename] = str((output_dir / filename).relative_to(ROOT))
        if write_root_reports:
            (ROOT / filename).write_text(text, encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--voice-id", required=True)
    parser.add_argument("--voice-name", required=True)
    parser.add_argument("--mode", choices=["dry-run", "generate-internal"], default="dry-run")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-cost-inr", type=float)
    parser.add_argument("--max-chunks", type=int)
    parser.add_argument(
        "--narration-mode",
        choices=[NARRATION_MODE_PREMIUM, NARRATION_MODE_FULL_FIDELITY],
        default=NARRATION_MODE_PREMIUM,
    )
    args = parser.parse_args()

    result = run_chapter_pipeline(
        book_slug=args.book_slug,
        language=args.language,
        chapter=args.chapter,
        provider=args.provider,
        voice_id=args.voice_id,
        voice_name=args.voice_name,
        mode=args.mode,
        execute=args.execute,
        max_cost_inr=args.max_cost_inr,
        max_chunks=args.max_chunks,
        narration_mode=args.narration_mode,
        write_root_reports=True,
    )
    print(
        "Audiobook chapter pipeline complete: "
        f"status={result.status} mode={result.mode} "
        f"public_audio={PUBLIC_AUDIO_RELEASE_BLOCKED} "
        f"output_dir={result.output_dir.relative_to(ROOT)}"
    )
    if result.generation.get("blockers"):
        for blocker in result.generation["blockers"]:
            print(f"BLOCKED: {blocker}", file=sys.stderr)
    return 2 if args.mode == "generate-internal" and result.status == BLOCKED_REAL_GENERATION else 0


if __name__ == "__main__":
    raise SystemExit(main())
