#!/usr/bin/env python3
"""Benchmark the retained Call of the Wild Edge candidate, privately.

This is a reuse-first, evidence-only lane.  It binds the retained audio and
word sidecar to the canonical controlled publication, extracts four bounded
private samples, and runs local Whisper ASR.  It cannot upload, publish, alter
release truth, or approve the recording/voice rights that remain unresolved.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[3]
SLUG = "the-call-of-the-wild"
TITLE = "The Call of the Wild"
AUTHOR = "Jack London"
SOURCE_SHA256 = "36bf2714954e352c1c6a5fbbe65af1e77ab622e709e42907cd9451eda0982916"
SOURCE_CHARACTERS = 177_305
CHAPTER_COUNT = 7
FRONT_COVER_URL = (
    "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779568766/"
    "earnalism/covers/front/cover_32a20edc-5097-4d64-98d0-fb3d29487a9d.png"
)
BACK_COVER_URL = (
    "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779568843/"
    "earnalism/covers/back/back_cover_32a20edc-5097-4d64-98d0-fb3d29487a9d.png"
)
AUDIO_SHA256 = "1da9fb1eafcfd35b62865251e4807b8e5bc7fffcd3d04dfc8491605d9d1d3b63"
AUDIO_SIZE_BYTES = 110_863_090
AUDIO_DURATION_MS = 13_857_792
SIDECAR_WORD_COUNT = 32_374
VOICE = "en-IN-NeerjaNeural"
PROVIDER = "edge"
WHISPER_MODEL = "medium.en"
WHISPER_SHA256 = "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"
BENCHMARK_FINGERPRINT = "5cc0e9048d63631aa43dd21819334b44c62a495bbb27823bdbc519549352ce76"
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
SAMPLE_SPECS = (
    ("opening_exposition", 19, 220, "opening_exposition_and_long_sentence_pacing"),
    ("trail_action", 4_357, 220, "sled_action_names_and_command_cadence"),
    ("thornton_bond", 21_880, 220, "restrained_emotion_and_human_animal_bond"),
    ("closing_call", 32_154, 220, "yeehaat_names_reflection_and_final_words"),
)
ASR_PROMPT = (
    "The Call of the Wild by Jack London. Canonical names: Buck, John Thornton, "
    "Yeehats, St Bernard, Perrault, Francois, Spitz, Dave, Sol-leks."
)
DEFAULT_BUNDLE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/output/"
    "english_audiobook_polish/english-polish-edge-queue-v1/bundles/en/"
    "the-call-of-the-wild"
)
DEFAULT_PRIVATE_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/reuse/the-call-of-the-wild/"
    "edge-neerja-representative-v1"
)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_edge_neerja_reuse_benchmark_v1.json"
)
PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)


class BenchmarkError(RuntimeError):
    """Raised when a fail-closed invariant changes."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise BenchmarkError(f"{label} changed: expected {expected!r}, observed {observed!r}")


def lexical_tokens(value: str) -> list[str]:
    prepared = re.sub(r"[’'\-]", " ", value.lower())
    return re.findall(r"[a-z0-9]+", prepared)


def source_and_metadata() -> tuple[list[str], dict[str, Any]]:
    root = ROOT / "data/controlled_publications" / SLUG
    backend = ROOT / "backend/data/controlled_publications" / SLUG
    book = read_json(root / "public_book.json")
    approval = read_json(root / "approval_evidence.json")
    source_evidence = read_json(root / "source_evidence.json")
    for name in ("public_book.json", "approval_evidence.json", "source_evidence.json"):
        if (root / name).read_bytes() != (backend / name).read_bytes():
            raise BenchmarkError(f"root/backend controlled metadata differs: {name}")
    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "isLive": True,
        "isPublic": True,
        "audio_enabled": False,
        "audiobook_enabled": False,
    }.items():
        require(book.get(key), expected, f"public_book.{key}")
    require(book.get("cover_url"), FRONT_COVER_URL, "front cover")
    require(book.get("back_cover_url"), BACK_COVER_URL, "back cover")
    require(
        approval.get("audio_public_release"),
        "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        "public audio release",
    )
    require(approval.get("audiobook_enabled"), False, "approval audiobook state")
    require(source_evidence.get("source_hash"), book.get("source_hash"), "source evidence hash")
    require(book.get("rights_tier"), "A", "rights tier")
    require(book.get("verification_status"), "approved", "reader rights verification")

    chapter_paths = sorted((root / "chapters").glob("chapter-*.json"))
    require(len(chapter_paths), CHAPTER_COUNT, "chapter count")
    manuscript_parts: list[str] = []
    token_parts: list[str] = []
    for path in chapter_paths:
        if path.read_bytes() != (backend / "chapters" / path.name).read_bytes():
            raise BenchmarkError(f"root/backend chapter differs: {path.name}")
        chapter = read_json(path)
        require(chapter.get("processing_status"), "ready", f"{path.name} status")
        require(chapter.get("processing_warnings"), [], f"{path.name} warnings")
        content = str(chapter.get("content") or "")
        manuscript_parts.append(content)
        token_parts.extend((str(chapter.get("title") or ""), content))
    manuscript = "\n\n".join(manuscript_parts) + "\n"
    require(len(manuscript), SOURCE_CHARACTERS, "canonical source characters")
    require(sha256_text(manuscript), SOURCE_SHA256, "canonical source SHA-256")
    return lexical_tokens("\n".join(token_parts)), {
        "source_path": str(root / "chapters"),
        "source_sha256": SOURCE_SHA256,
        "source_characters": SOURCE_CHARACTERS,
        "chapter_count": CHAPTER_COUNT,
        "front_cover_url": FRONT_COVER_URL,
        "back_cover_url": BACK_COVER_URL,
        "reader_rights_status": "PASS",
        "recording_voice_rights_status": "UNRESOLVED_FOR_PUBLICATION",
    }


def validate_candidate(bundle: Path, source_tokens: Sequence[str]) -> tuple[Path, list[dict[str, Any]], dict[str, Any]]:
    audio = bundle / f"{SLUG}.mp3"
    metadata = read_json(bundle / f"{SLUG}_meta.json")
    sidecar = read_json(bundle / f"{SLUG}_timestamps.json")
    require(metadata.get("slug"), SLUG, "candidate slug")
    require(metadata.get("provider_used"), PROVIDER, "candidate provider")
    require(metadata.get("voice"), VOICE, "candidate voice")
    require(metadata.get("duration_ms"), AUDIO_DURATION_MS, "candidate duration")
    require(audio.stat().st_size, AUDIO_SIZE_BYTES, "candidate size")
    require(sha256_file(audio), AUDIO_SHA256, "candidate SHA-256")
    require(len(sidecar), SIDECAR_WORD_COUNT, "sidecar word count")
    if len(source_tokens) != len(sidecar):
        raise BenchmarkError("canonical and sidecar token counts differ")

    prior_end = 0
    equivalent_expansions: list[dict[str, Any]] = []
    exact_count = 0
    for index, (source_word, timing) in enumerate(zip(source_tokens, sidecar)):
        side_word = "".join(lexical_tokens(str(timing.get("word") or "")))
        start = int(timing.get("start_ms"))
        end = int(timing.get("end_ms"))
        if start < prior_end or end <= start:
            raise BenchmarkError(f"non-monotonic sidecar timing at token {index}")
        prior_end = end
        if source_word == side_word:
            exact_count += 1
            continue
        if source_word == "st" and side_word == "saint" and index + 1 < len(source_tokens) and source_tokens[index + 1] == "bernard":
            equivalent_expansions.append({"index": index, "source": "st", "spoken": "saint"})
            continue
        raise BenchmarkError(
            f"unexpected canonical/sidecar mismatch at {index}: {source_word!r} != {side_word!r}"
        )
    require(prior_end, AUDIO_DURATION_MS, "sidecar final timestamp")
    require(len(equivalent_expansions), 3, "St Bernard expansion count")
    return audio, sidecar, {
        "source_token_count": len(source_tokens),
        "sidecar_word_count": len(sidecar),
        "exact_token_count": exact_count,
        "approved_abbreviation_expansions": equivalent_expansions,
        "coverage": 1.0,
        "score": round(10 * exact_count / len(source_tokens), 4),
        "first_words_match": True,
        "last_words_match": True,
        "timeline_monotonic": True,
        "timeline_end_matches_audio_metadata": True,
    }


def ordered_metrics(source: str, transcript: str) -> dict[str, Any]:
    source_tokens = lexical_tokens(source)
    transcript_tokens = lexical_tokens(transcript)
    matcher = SequenceMatcher(None, source_tokens, transcript_tokens, autojunk=False)
    equal = sum(block.size for block in matcher.get_matching_blocks())
    coverage = equal / len(source_tokens) if source_tokens else 0.0
    precision = equal / len(transcript_tokens) if transcript_tokens else 0.0
    harmonic = 2 * coverage * precision / (coverage + precision) if coverage + precision else 0.0
    source_count = Counter(source_tokens)
    transcript_count = Counter(transcript_tokens)
    first = min(5, len(source_tokens), len(transcript_tokens))
    last = min(5, len(source_tokens), len(transcript_tokens))
    return {
        "score": round(10 * harmonic, 4),
        "coverage": round(coverage, 4),
        "precision": round(precision, 4),
        "source_token_count": len(source_tokens),
        "transcript_token_count": len(transcript_tokens),
        "equal_token_count": equal,
        "first_words_match": bool(first and source_tokens[:first] == transcript_tokens[:first]),
        "last_words_match": bool(last and source_tokens[-last:] == transcript_tokens[-last:]),
        "no_missing_content": all(transcript_count[token] >= count for token, count in source_count.items()),
        "no_duplicate_content": all(transcript_count[token] <= count for token, count in source_count.items()),
        "asr_gate_pass": (
            10 * harmonic >= ASR_SCORE_MIN
            and coverage >= ASR_COVERAGE_MIN
            and bool(first and source_tokens[:first] == transcript_tokens[:first])
            and bool(last and source_tokens[-last:] == transcript_tokens[-last:])
        ),
    }


def extract_samples(audio: Path, sidecar: Sequence[dict[str, Any]], private_dir: Path) -> list[dict[str, Any]]:
    private_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for passage_id, start_index, word_count, risk in SAMPLE_SPECS:
        words = list(sidecar[start_index : start_index + word_count])
        require(len(words), word_count, f"{passage_id} word count")
        start_ms = int(words[0]["start_ms"])
        end_ms = int(words[-1]["end_ms"])
        target = private_dir / f"{passage_id}.wav"
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{start_ms / 1000:.3f}", "-i", str(audio),
                "-t", f"{(end_ms - start_ms) / 1000:.3f}",
                "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target),
            ],
            check=True,
        )
        source = " ".join(str(item["word"]) for item in words)
        results.append(
            {
                "passage_id": passage_id,
                "risk": risk,
                "source_text": source,
                "source_text_sha256": sha256_text(source),
                "source_word_count": word_count,
                "source_sidecar_range": [start_index, start_index + word_count],
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_seconds": round((end_ms - start_ms) / 1000, 3),
                "audio_path": str(target),
                "audio_sha256": sha256_file(target),
                "audio_size_bytes": target.stat().st_size,
            }
        )
    return results


def run_asr(samples: Sequence[dict[str, Any]], cache: Path) -> list[dict[str, Any]]:
    import whisper  # noqa: PLC0415

    model_file = cache / f"{WHISPER_MODEL}.pt"
    require(sha256_file(model_file), WHISPER_SHA256, "Whisper model SHA-256")
    model = whisper.load_model(WHISPER_MODEL, download_root=str(cache.resolve()))
    results: list[dict[str, Any]] = []
    for sample in samples:
        result = model.transcribe(
            sample["audio_path"],
            language="en",
            task="transcribe",
            fp16=False,
            temperature=0,
            condition_on_previous_text=False,
            initial_prompt=ASR_PROMPT,
            word_timestamps=True,
        )
        transcript = str(result.get("text") or "").strip()
        results.append(
            {
                "passage_id": sample["passage_id"],
                "source_text_sha256": sample["source_text_sha256"],
                "audio_sha256": sample["audio_sha256"],
                "transcript": transcript,
                "transcript_sha256": sha256_text(transcript),
                "metrics": ordered_metrics(sample["source_text"], transcript),
            }
        )
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--private-dir", type=Path, default=DEFAULT_PRIVATE_DIR)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--execute", action="store_true", help="Extract samples and run local ASR")
    args = parser.parse_args(argv)

    lock_before = PAID_LOCK.read_bytes()
    source_tokens, canonical = source_and_metadata()
    audio, sidecar, alignment = validate_candidate(args.bundle, source_tokens)
    samples: list[dict[str, Any]] = []
    asr_results: list[dict[str, Any]] = []
    if args.execute:
        samples = extract_samples(audio, sidecar, args.private_dir.resolve())
        asr_results = run_asr(samples, args.whisper_cache)
    require(PAID_LOCK.read_bytes(), lock_before, "paid_tts.lock bytes")

    representative_pass = bool(asr_results) and all(
        item["metrics"]["asr_gate_pass"] for item in asr_results
    )
    blockers = [
        "EDGE_RECORDING_VOICE_COMMERCIAL_RIGHTS_UNRESOLVED",
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_MEASURED_SYNC_NOT_RUN",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        "OWNER_10_TARGET_NOT_VERIFIED",
    ]
    if not args.execute:
        blockers.insert(0, "REPRESENTATIVE_ASR_NOT_RUN")
    elif not representative_pass:
        blockers.insert(0, "REPRESENTATIVE_ASR_SOURCE_GATE_FAILED")
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "status": "PRIVATE_BENCHMARK_COMPLETE_NO_GO" if args.execute else "PRIVATE_PREFLIGHT_PASS",
        "go_live_decision": "NO_GO",
        "canonical": canonical,
        "candidate": {
            "provider": PROVIDER,
            "voice": VOICE,
            "audio_path": str(audio),
            "audio_sha256": AUDIO_SHA256,
            "audio_size_bytes": AUDIO_SIZE_BYTES,
            "duration_ms": AUDIO_DURATION_MS,
            "recording_voice_rights_status": "UNRESOLVED_FOR_PUBLICATION",
            "benchmark_fingerprint": BENCHMARK_FINGERPRINT,
        },
        "source_sidecar_alignment": alignment,
        "asr_contract": {
            "model": WHISPER_MODEL,
            "model_sha256": WHISPER_SHA256,
            "source_score_min": ASR_SCORE_MIN,
            "coverage_min": ASR_COVERAGE_MIN,
            "first_last_words_required": True,
        },
        "representative_samples": [
            {key: value for key, value in sample.items() if key != "source_text"}
            for sample in samples
        ],
        "representative_asr": asr_results,
        "representative_asr_pass": representative_pass,
        "safety": {
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock_touched": False,
            "private_output_dir": str(args.private_dir.resolve()),
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
            "browser_or_system_speech_fallback": False,
        },
        "blockers_to_release": blockers,
        "next_action": (
            "Reject this retained Edge recording for public use unless its exact voice-commercial-rights basis is documented; "
            "use its objective score only as a private benchmark against the Apache-2.0 Kokoro title lane."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "status": payload["status"],
        "representative_asr_pass": representative_pass,
        "scores": [item["metrics"]["score"] for item in asr_results],
        "go_live_decision": "NO_GO",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
