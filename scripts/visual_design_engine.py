#!/usr/bin/env python3
"""Generate deterministic visual/study asset dry-run reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.source_ingestion import hash_source  # noqa: E402
from backend.visual_design_engine import (  # noqa: E402
    VisualGenerationInput,
    generate_visual_assets,
    visual_report_csv,
    visual_report_json,
    visual_report_markdown,
)


SAMPLE_TEXT = """Chapter 1

Alice was beginning to get very tired of sitting by her sister on the bank.
The White Rabbit ran close by her, looked at a watch, and hurried on.
Alice followed the Rabbit and began a strange journey full of curiosity, questions, and choices.

Chapter 2

Alice wondered about identity, size, courage, and what it means to keep learning in a confusing world.
"""


def sample_payload() -> dict[str, Any]:
    source_hash = hash_source(SAMPLE_TEXT)
    return {
        "source_work": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "cleaned_text": SAMPLE_TEXT,
        "source_hash": source_hash,
    }


def load_payload(path: Path | None, *, sample: bool) -> dict[str, Any]:
    if sample:
        return sample_payload()
    if path is None:
        raise ValueError("--input is required unless --sample is used.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--input must be a JSON object.")
    if not payload.get("cleaned_text") and payload.get("cleaned_text_preview"):
        raise ValueError("Phase 6 requires cleaned_text; rerun Phase 4 with --include-text for local dry-run visual assets.")
    return payload


def write_reports(
    result,
    output_dir: Path,
    *,
    include_content: bool = False,
    content_preview_chars: int = 1200,
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "visual_design_report.json"
    csv_path = output_dir / "visual_design_report.csv"
    md_path = output_dir / "visual_design_report.md"
    json_path.write_text(
        json.dumps(
            visual_report_json(result, include_content=include_content, content_preview_chars=content_preview_chars),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    csv_path.write_text(visual_report_csv(result), encoding="utf-8")
    md_path.write_text(
        visual_report_markdown(result, include_content=include_content, content_preview_chars=content_preview_chars),
        encoding="utf-8",
    )
    return json_path, csv_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Local JSON payload with cleaned_text and source_hash.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/visual_design"))
    parser.add_argument("--asset", action="append", default=[], help="Specific asset type to generate. Repeatable.")
    parser.add_argument("--max-assets-per-run", type=int, default=8)
    parser.add_argument("--include-content", action="store_true", help="Include full deterministic asset content in JSON/Markdown.")
    parser.add_argument("--content-preview-chars", type=int, default=1200)
    parser.add_argument("--sample", action="store_true", help="Run a deterministic local fixture.")
    parser.add_argument("--commit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--publish", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--write", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.commit or args.publish or args.write:
        parser.error("Phase 6 visual design generation is dry-run only; commit/publish/write options are not supported.")

    payload = load_payload(args.input, sample=args.sample)
    text = str(payload.get("cleaned_text") or "")
    result = generate_visual_assets(
        VisualGenerationInput(
            source_work=str(payload.get("source_work") or payload.get("title") or payload.get("work_title") or "Untitled"),
            author=str(payload.get("author") or payload.get("author_name") or ""),
            cleaned_text=text,
            source_hash=str(payload.get("source_hash") or hash_source(text)),
            requested_assets=args.asset,
            max_assets_per_run=args.max_assets_per_run,
            dry_run=True,
        )
    )
    json_path, csv_path, md_path = write_reports(
        result,
        args.output_dir,
        include_content=args.include_content,
        content_preview_chars=args.content_preview_chars,
    )
    print(
        "Visual design dry-run complete: "
        f"status={result.generation_status} "
        f"qa={result.qa.get('qa_status')} "
        f"json={json_path} csv={csv_path} markdown={md_path}"
    )
    return 0 if result.qa.get("qa_status") != "BLOCKED_QA" else 2


if __name__ == "__main__":
    raise SystemExit(main())
