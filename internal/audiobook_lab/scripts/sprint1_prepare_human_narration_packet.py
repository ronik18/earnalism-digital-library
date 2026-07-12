#!/usr/bin/env python3
"""Create a source-bound, non-provider human narration packet for a Sprint 1 title."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def create_packet(*, slug: str, asset_root: Path, output_root: Path) -> dict:
    publication = asset_root / "data/controlled_publications" / slug
    public_book = load_json(publication / "public_book.json")
    source_evidence = load_json(publication / "source_evidence.json")

    if public_book.get("verification_status") != "approved" or public_book.get("qa_status") != "QA_PASSED":
        raise RuntimeError("controlled publication is not approved and QA-passed")
    if not source_evidence.get("rights_basis") or not source_evidence.get("source_hash"):
        raise RuntimeError("source rights evidence is incomplete")

    chapter_paths = sorted((publication / "chapters").glob("chapter-*.json"))
    if not chapter_paths:
        raise RuntimeError("controlled publication has no chapters")

    chapter_texts: list[str] = []
    chapter_hashes: list[dict] = []
    for chapter_path in chapter_paths:
        chapter = load_json(chapter_path)
        if chapter.get("processing_status") != "ready" or chapter.get("processing_warnings") != []:
            raise RuntimeError(f"chapter is not clean and ready: {chapter_path.name}")
        content = str(chapter.get("content") or "").strip()
        if not content:
            raise RuntimeError(f"chapter content is empty: {chapter_path.name}")
        recorded_hash = str(chapter.get("sanitizedSha256") or "")
        computed_hash = sha256_text(content)
        if recorded_hash and recorded_hash != computed_hash:
            raise RuntimeError(f"chapter sanitized hash changed: {chapter_path.name}")
        chapter_texts.append(content)
        chapter_hashes.append(
            {
                "chapter": chapter_path.name,
                "characters": len(content),
                "sanitized_sha256": computed_hash,
            }
        )

    manuscript = "\n\n".join(chapter_texts) + "\n"
    packet_dir = output_root / slug
    packet_dir.mkdir(parents=True, exist_ok=True)
    manuscript_path = packet_dir / "clean_manuscript.txt"
    brief_path = packet_dir / "narrator_brief.md"
    metadata_path = packet_dir / "metadata.json"

    manuscript_path.write_text(manuscript, encoding="utf-8")
    brief_path.write_text(
        "\n".join(
            [
                f"# Human Narration Brief: {public_book.get('title') or slug}",
                "",
                f"Author: {public_book.get('author') or ''}",
                f"Language: {public_book.get('language') or 'English'}",
                "",
                "Use only `clean_manuscript.txt`. Preserve every word and paragraph in order.",
                "Do not add music, sound effects, source boilerplate, page numbers, or narration credits.",
                "Deliver clean WAV or high-bitrate MP3 with calm literary pacing and natural dialogue.",
                "",
                "Release QA remains mandatory:",
                "- ASR/source score >= 9.7",
                "- first and last words match",
                "- every listening sample >= 9.4 with confidence >= 0.90",
                "- no robotic texture, mechanical cadence, list reading, choppy joins, or fallback TTS",
                "- manifest, endpoint, frontend, and production gates pass before Listen is exposed",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    metadata = {
        "schema_version": 1,
        "slug": slug,
        "title": public_book.get("title") or slug,
        "author": public_book.get("author") or "",
        "language": public_book.get("language") or "English",
        "rights_basis": source_evidence["rights_basis"],
        "source_hash": source_evidence["source_hash"],
        "provenance_hash": source_evidence.get("provenance_hash"),
        "manuscript_sha256": sha256_text(manuscript.rstrip()),
        "chapters": chapter_hashes,
        "provider_calls_ran": False,
        "audio_generated": False,
        "public_audio_status": "AUDIO_HIDDEN_PENDING_FULL_RELEASE_GATES",
        "release_gate_mutated": False,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "HUMAN_NARRATION_PACKET_READY",
        "packet_dir": str(packet_dir),
        "manuscript": str(manuscript_path),
        "brief": str(brief_path),
        "metadata": str(metadata_path),
        "provider_calls_ran": False,
        "release_gate_mutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--asset-root", default=str(ROOT))
    parser.add_argument(
        "--output-root",
        default=str(ROOT / "internal/audiobook_lab/sprint1_publication/human_narration_packets"),
    )
    args = parser.parse_args()
    result = create_packet(
        slug=args.slug,
        asset_root=Path(args.asset_root).expanduser().resolve(),
        output_root=Path(args.output_root).expanduser().resolve(),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
