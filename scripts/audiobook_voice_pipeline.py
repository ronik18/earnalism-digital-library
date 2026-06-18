#!/usr/bin/env python3
"""Create deterministic dry-run audiobook voice pipeline reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.audiobook_voice_pipeline import (  # noqa: E402
    AudiobookPipelineInput,
    AudioQAMetrics,
    audiobook_report_csv,
    audiobook_report_json,
    audiobook_report_markdown,
    plan_audiobook_pipeline,
)


SAMPLE_TEXT = """Chapter 1

Alice was beginning to get very tired of sitting by her sister on the bank.
"Oh dear! Oh dear!" said the Rabbit, and hurried close by her.

Chapter 2

Alice wondered about courage, curiosity, and learning.
Where Learning Becomes Earning.
"""


def sample_payload() -> dict[str, Any]:
    return {
        "book_slug": "alice-in-wonderland",
        "title": "Alice's Adventures in Wonderland",
        "source_text": SAMPLE_TEXT,
        "language": "en",
        "generation_mode": "preview_90s",
        "provider": "manual_audio_upload",
        "linked_approved_book": True,
        "rights_tier": "A",
        "verification_status": "approved",
        "blocked_reason": "",
        "pronunciation_dictionary": {
            "Earnalism": "urn-uh-lizm",
            "Reo Enterprise": "Ray-oh Enterprise",
        },
    }


def load_payload(path: Path | None, *, sample: bool) -> dict[str, Any]:
    if sample:
        return sample_payload()
    if path is None:
        raise ValueError("--input is required unless --sample is used.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--input must be a JSON object.")
    return payload


def parse_qa_metrics(payload: dict[str, Any]) -> AudioQAMetrics | None:
    raw = payload.get("qa_metrics")
    if not isinstance(raw, dict):
        return None
    return AudioQAMetrics(
        stt_transcript_comparison=str(raw.get("stt_transcript_comparison") or "HOOK_NOT_RUN"),
        word_error_rate=raw.get("word_error_rate"),
        missing_paragraph_count=int(raw.get("missing_paragraph_count") or 0),
        repeated_line_count=int(raw.get("repeated_line_count") or 0),
        clipping_detected=bool(raw.get("clipping_detected")),
        long_silence_detected=bool(raw.get("long_silence_detected")),
        file_size_bytes=int(raw.get("file_size_bytes") or 0),
    )


def write_reports(
    result,
    output_dir: Path,
    *,
    include_text: bool = False,
    text_preview_chars: int = 320,
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "audiobook_voice_report.json"
    csv_path = output_dir / "audiobook_voice_report.csv"
    md_path = output_dir / "audiobook_voice_report.md"
    json_path.write_text(
        json.dumps(
            audiobook_report_json(result, include_text=include_text, text_preview_chars=text_preview_chars),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    csv_path.write_text(audiobook_report_csv(result), encoding="utf-8")
    md_path.write_text(
        audiobook_report_markdown(result, include_text=include_text, text_preview_chars=text_preview_chars),
        encoding="utf-8",
    )
    return json_path, csv_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Local JSON payload for dry-run planning.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/audiobook_voice"))
    parser.add_argument("--mode", choices=["preview_30s", "preview_90s", "preview_3m", "chapter_audio", "full_audiobook_playlist"])
    parser.add_argument("--provider", choices=["openai_tts", "ai4bharat_indic_tts", "piper_local_tts", "manual_audio_upload"])
    parser.add_argument("--include-text", action="store_true", help="Include full narration chunk text in JSON/Markdown.")
    parser.add_argument("--text-preview-chars", type=int, default=320)
    parser.add_argument("--sample", action="store_true", help="Run a deterministic local fixture.")
    parser.add_argument("--commit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--publish", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--write", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.commit or args.publish or args.write:
        parser.error("Phase 7 audiobook voice pipeline is dry-run only; commit/publish/write options are not supported.")

    payload = load_payload(args.input, sample=args.sample)
    result = plan_audiobook_pipeline(
        AudiobookPipelineInput(
            book_slug=str(payload.get("book_slug") or payload.get("slug") or ""),
            title=str(payload.get("title") or payload.get("work_title") or "Untitled"),
            source_text=str(payload.get("source_text") or payload.get("cleaned_text") or ""),
            language=str(payload.get("language") or ""),
            generation_mode=args.mode or str(payload.get("generation_mode") or "preview_90s"),
            provider=args.provider or str(payload.get("provider") or "manual_audio_upload"),
            dry_run=True,
            linked_approved_book=bool(payload.get("linked_approved_book")),
            rights_tier=str(payload.get("rights_tier") or ""),
            verification_status=str(payload.get("verification_status") or ""),
            blocked_reason=str(payload.get("blocked_reason") or ""),
            qa_metrics=parse_qa_metrics(payload),
            pronunciation_dictionary=dict(payload.get("pronunciation_dictionary") or {}),
            max_chunk_chars=int(payload.get("max_chunk_chars") or 900),
        )
    )
    json_path, csv_path, md_path = write_reports(
        result,
        args.output_dir,
        include_text=args.include_text,
        text_preview_chars=args.text_preview_chars,
    )
    print(
        "Audiobook voice dry-run complete: "
        f"status={result.generation_status} "
        f"gate={result.publish_gate_status} "
        f"qa={result.qa.qa_status} "
        f"json={json_path} csv={csv_path} markdown={md_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
