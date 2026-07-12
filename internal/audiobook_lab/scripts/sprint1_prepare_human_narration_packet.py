#!/usr/bin/env python3
"""Create a source-bound, non-provider human narration packet for a Sprint 1 title."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def portable_path(path: Path, *roots: Path) -> str:
    resolved = path.resolve()
    for root in roots:
        try:
            return str(resolved.relative_to(root.resolve()))
        except ValueError:
            continue
    return str(resolved)


def prior_failure_evidence(slug: str, asset_root: Path) -> dict:
    relative = Path("internal/audiobook_lab/sprint1_publication/title_runs") / f"{slug}_release_gate_evidence.json"
    for base in (ROOT, asset_root):
        path = base / relative
        if path.exists():
            payload = load_json(path)
            return {
                "path": portable_path(path, ROOT, asset_root),
                "classification": payload.get("classification") or payload.get("final_status") or "",
                "stage2d": payload.get("stage2d_replacement_auditions") or {},
                "stage2e": payload.get("stage2e_studio_b_final_audition") or {},
            }
    return {"path": "", "classification": "NO_PRIOR_FAILURE_EVIDENCE_FOUND", "stage2d": {}, "stage2e": {}}


def validation_command(*, slug: str, asset_root: Path, output_root: Path) -> str:
    output_arg = portable_path(output_root, asset_root, ROOT)
    return (
        "PYTHONDONTWRITEBYTECODE=1 python3 "
        "internal/audiobook_lab/scripts/sprint1_prepare_human_narration_packet.py "
        f"--slug {slug} --asset-root {asset_root} --output-root {output_arg} "
        "--received-audio /absolute/path/to/received_narration.wav"
    )


def validate_received_audio(*, audio_path: Path, packet_dir: Path) -> dict:
    if not audio_path.exists() or not audio_path.is_file() or audio_path.stat().st_size <= 0:
        raise RuntimeError("received narration is missing or empty")
    if audio_path.suffix.lower() not in {".wav", ".mp3"}:
        raise RuntimeError("received narration must be WAV or MP3")
    metadata_path = packet_dir / "metadata.json"
    if not metadata_path.exists():
        raise RuntimeError("human narration packet metadata is missing")
    metadata = load_json(metadata_path)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,bit_rate:stream=codec_name,sample_rate,channels",
            "-of",
            "json",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    details = json.loads(probe.stdout)
    streams = details.get("streams") or []
    if not streams:
        raise RuntimeError("received narration has no audio stream")
    stream = streams[0]
    duration = float((details.get("format") or {}).get("duration") or 0)
    sample_rate = int(stream.get("sample_rate") or 0)
    channels = int(stream.get("channels") or 0)
    if duration <= 0 or sample_rate < 44100 or channels not in {1, 2}:
        raise RuntimeError("received narration does not meet duration/sample-rate/channel requirements")
    result = {
        "schema_version": 1,
        "status": "RECEIVED_AUDIO_PREFLIGHT_PASS_FULL_RELEASE_QA_REQUIRED",
        "slug": metadata.get("slug"),
        "packet_manuscript_sha256": metadata.get("manuscript_sha256"),
        "received_audio_path": str(audio_path.resolve()),
        "received_audio_sha256": hashlib.sha256(audio_path.read_bytes()).hexdigest(),
        "received_audio_bytes": audio_path.stat().st_size,
        "duration_seconds": round(duration, 3),
        "codec": stream.get("codec_name"),
        "sample_rate": sample_rate,
        "channels": channels,
        "provider_calls_ran": False,
        "release_gate_mutated": False,
        "next_status": "ASR_LISTENING_MANIFEST_ENDPOINT_FRONTEND_PRODUCTION_QA_REQUIRED",
    }
    report_path = packet_dir / "received_audio_preflight.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["report"] = str(report_path)
    return result


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
    failure = prior_failure_evidence(slug, asset_root)
    packet_dir = output_root / slug
    packet_dir.mkdir(parents=True, exist_ok=True)
    manuscript_path = packet_dir / "clean_manuscript.txt"
    brief_path = packet_dir / "narrator_brief.md"
    failure_path = packet_dir / "failed_tts_evidence_summary.md"
    delivery_path = packet_dir / "delivery_checklist.md"
    qa_path = packet_dir / "qa_release_checklist.md"
    metadata_path = packet_dir / "metadata.json"
    next_command = validation_command(slug=slug, asset_root=asset_root, output_root=output_root)

    manuscript_path.write_text(manuscript, encoding="utf-8")
    brief_path.write_text(
        "\n".join(
            [
                f"# Human Narration Brief: {public_book.get('title') or slug}",
                "",
                f"Author: {public_book.get('author') or ''}",
                f"Language: {public_book.get('language') or 'English'}",
                "",
                "## Pronunciation And Style Notes",
                "- Calm, intimate classic-story narration with understated tension and dry wit.",
                "- Keep Vera poised and controlled; do not overact the ghost-story reveal.",
                "- Avoid list-reading rhythm, mechanical cadence, rushed twilight transitions, and synthetic resets.",
                "- Preserve names and quoted dialogue exactly as written.",
                "",
                "## Target Narration Style",
                "Natural literary pacing, restrained emotional expression, clear dialogue changes, and deliberate punctuation pauses.",
                "",
                "Use only `clean_manuscript.txt`. Preserve every word and paragraph in order.",
                "Do not add music, sound effects, source boilerplate, page numbers, or narration credits.",
                "",
                "## Required Audio Format",
                "Deliver one clean WAV (PCM, 44.1/48 kHz, mono or stereo) or high-bitrate MP3 (44.1/48 kHz).",
                "No normalization clipping, denoising artifacts, music, room tone jumps, or lossy re-encoding chains.",
                "",
                "## Chapter And Section Boundaries",
                "This controlled edition has one chapter. Preserve paragraph boundaries and leave natural silence at scene/paragraph transitions.",
                "Do not insert spoken chapter numbers, credits, source notices, or any text absent from the manuscript.",
                "",
                "See `failed_tts_evidence_summary.md`, `delivery_checklist.md`, and `qa_release_checklist.md`.",
                "",
                "## Exact Validation Command After Delivery",
                f"`{next_command}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    stage2d = failure.get("stage2d") or {}
    stage2e = failure.get("stage2e") or {}
    failure_path.write_text(
        "\n".join(
            [
                f"# Failed TTS Evidence: {public_book.get('title') or slug}",
                "",
                f"- Current classification: `{failure.get('classification')}`",
                f"- Evidence source: `{failure.get('path') or 'not found'}`",
                f"- Studio-C baseline: `{((stage2d.get('baseline') or {}).get('scores') or [])}`",
                f"- Studio-C prosody retry: `{((stage2d.get('single_prosody_retry') or {}).get('scores') or [])}`",
                f"- Studio-B final audition: `{stage2e.get('scores') or []}`",
                f"- Studio-B fatal flags: `{stage2e.get('fatal_flags') or []}`",
                "",
                "Do not reuse the Piper, failed Studio-C, or failed Studio-B audio. The twilight transition must be delivered naturally without robotic texture or mechanical cadence.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    delivery_path.write_text(
        "\n".join(
            [
                "# Delivery Checklist",
                "",
                "- [ ] Complete narration matches `clean_manuscript.txt` word-for-word.",
                "- [ ] WAV or MP3, 44.1/48 kHz, mono or stereo, non-empty and playable.",
                "- [ ] No music, sound effects, clipping, duplicate paragraphs, omissions, or unrelated speech.",
                "- [ ] Paragraph and dialogue boundaries remain audible and natural.",
                "- [ ] File name identifies slug and version without public-release claims.",
                "- [ ] Rights/provenance for the delivered performance are documented.",
                "- [ ] Run the exact received-audio validation command from `narrator_brief.md`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    qa_path.write_text(
        "\n".join(
            [
                "# QA And Release-Gate Checklist",
                "",
                "- [ ] Received-audio format/checksum preflight PASS.",
                "- [ ] ASR/source score >= 9.7.",
                "- [ ] First and last words match.",
                "- [ ] No missing, duplicated, reordered, or unrelated content.",
                "- [ ] Every listening sample >= 9.4 with confidence >= 0.90.",
                "- [ ] No robotic texture, mechanical cadence, list reading, choppy joins, or fallback TTS.",
                "- [ ] Measured section-following sync; no word-level or estimated-sync claim.",
                "- [ ] Manifest and checksum validation PASS.",
                "- [ ] Audio endpoint and range request PASS.",
                "- [ ] Frontend release-state and production route validation PASS.",
                "- [ ] Owner release approval recorded before Listen or AudioObject exposure.",
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
        "failed_tts_evidence": failure,
        "target_narration_style": "calm_literary_understated_tension_natural_dialogue",
        "required_audio_format": "WAV or high-bitrate MP3; 44.1/48 kHz; mono or stereo",
        "validate_received_audio_command": next_command,
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
        "failed_tts_evidence": str(failure_path),
        "delivery_checklist": str(delivery_path),
        "qa_release_checklist": str(qa_path),
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
    parser.add_argument("--received-audio", help="Validate a delivered WAV/MP3 against the generated packet")
    args = parser.parse_args()
    result = create_packet(
        slug=args.slug,
        asset_root=Path(args.asset_root).expanduser().resolve(),
        output_root=Path(args.output_root).expanduser().resolve(),
    )
    if args.received_audio:
        result["received_audio_preflight"] = validate_received_audio(
            audio_path=Path(args.received_audio).expanduser().resolve(),
            packet_dir=Path(result["packet_dir"]),
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
