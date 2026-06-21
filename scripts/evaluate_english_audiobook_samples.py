#!/usr/bin/env python3
"""Evaluate English audiobook bake-off manifests without claiming audio quality."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "output" / "audiobook_bakeoff" / "dracula"
LICENSE_EVIDENCE_DIR = ROOT_DIR / "data" / "audiobook_models" / "license_evidence"
COVERAGE_REPORT = ROOT_DIR / "ENGLISH_AUDIOBOOK_CHUNK_COVERAGE_REPORT.md"


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_manifest(path: Path) -> dict[str, Any]:
    payload = load_manifest(path)
    model_id = str(payload.get("model_id") or path.parent.name)
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    public_urls = [row.get("public_audio_url") for row in results if row.get("public_audio_url")]
    audio_outputs = [row.get("output_path") for row in results if str(row.get("output_path") or "").endswith((".mp3", ".wav"))]
    return {
        "model_id": model_id,
        "manifest_path": str(path),
        "qa_status": "PENDING_HUMAN_AUDIO_REVIEW",
        "asr_word_error_rate": None,
        "mos_score": None,
        "human_review_required": True,
        "public_audio_url_count": len(public_urls),
        "audio_output_count": len(audio_outputs),
        "recommended_release_action": "DO_NOT_PUBLISH_AUDIO",
        "notes": [
            "No audio quality score is claimed without generated samples and human listening review.",
            "No ASR/STT comparison was run in this dry-run PR.",
        ],
    }


def write_reports(evaluations: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "book_slug": "dracula",
        "internal_review_only": True,
        "selection_status": "NO_MODEL_APPROVED_YET",
        "public_audio_published": False,
        "evaluations": evaluations,
    }
    (output_dir / "english_audio_qa_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    qa_lines = [
        "# English Audiobook Model Bake-Off Audio QA Report",
        "",
        "Status: PENDING_HUMAN_AUDIO_REVIEW.",
        "",
        "No audio was published, no public audiobook URL exists, and no model is approved yet.",
        "",
        "| Model | QA status | ASR WER | MOS | Release action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in evaluations:
        qa_lines.append(
            f"| {row['model_id']} | {row['qa_status']} | {row['asr_word_error_rate']} | {row['mos_score']} | {row['recommended_release_action']} |"
        )
    qa_lines.extend(
        [
            "",
            "## Required Human Review",
            "",
            "- Naturalness",
            "- Dracula/Gothic emotional restraint",
            "- Dialogue handling",
            "- Pronunciation",
            "- Punctuation and pauses",
            "- Fatigue across multi-chapter listening",
            "",
        ]
    )
    (ROOT_DIR / "AUDIOBOOK_ENGLISH_MODEL_BAKEOFF_AUDIO_QA_REPORT.md").write_text("\n".join(qa_lines), encoding="utf-8")

    form = [
        "# English Audiobook Model Bake-Off Human Review Form",
        "",
        "Book: Dracula",
        "",
        "Review status: INTERNAL_REVIEW_ONLY",
        "",
        "For each model, score 1-5:",
        "",
        "- Narration warmth:",
        "- Emotional restraint:",
        "- Gothic atmosphere:",
        "- Dialogue clarity:",
        "- Pronunciation accuracy:",
        "- Long-form listenability:",
        "- Any real-person/celebrity imitation concern:",
        "- Publish recommendation: DO_NOT_PUBLISH / RETEST / APPROVE_FOR_INTERNAL_NEXT_STEP",
        "",
        "No model may be approved for public audio without this review, release gate pass, and explicit owner approval.",
        "",
    ]
    (ROOT_DIR / "AUDIOBOOK_ENGLISH_MODEL_BAKEOFF_HUMAN_REVIEW_FORM.md").write_text("\n".join(form), encoding="utf-8")

    selection = [
        "# English Audiobook Model Selection Report",
        "",
        "Selection status: NO_MODEL_APPROVED_YET",
        "",
        "Current recommendation: keep Dracula audio disabled and continue internal-only bake-off.",
        "",
        "Shortlist posture:",
        "",
    ]
    for row in evaluations:
        selection.append(f"- {row['model_id']}: {row['qa_status']}; {row['recommended_release_action']}")
    selection.extend(
        [
            "",
            "A model can move forward only after license clearance, approved reference/style voice governance, human listening review, and release gate pass.",
            "",
        ]
    )
    (ROOT_DIR / "AUDIOBOOK_ENGLISH_MODEL_SELECTION_REPORT.md").write_text("\n".join(selection), encoding="utf-8")
    write_scorecard(evaluations, output_dir)


def license_snapshots_present() -> bool:
    required = {"chatterbox.json", "dia.json", "kokoro.json", "f5-tts.json", "xtts-v2.json"}
    return required.issubset({path.name for path in LICENSE_EVIDENCE_DIR.glob("*.json")})


def compute_scorecard(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    generated_samples = any(row.get("audio_output_count", 0) > 0 for row in evaluations)
    human_review_approved = any(row.get("human_review_approved") is True for row in evaluations)
    license_present = license_snapshots_present()
    coverage_present = COVERAGE_REPORT.exists()
    public_audio_enabled = any(row.get("public_audio_url_count", 0) > 0 for row in evaluations)
    score = 9.7
    caps: list[str] = []
    if not generated_samples:
        score = min(score, 9.0)
        caps.append("no generated samples = max 9.0")
    if not human_review_approved:
        score = min(score, 9.0)
        caps.append("no human review = max 9.0")
    if not license_present:
        score = min(score, 8.8)
        caps.append("no license snapshot = max 8.8")
    if not coverage_present:
        score = min(score, 9.2)
        caps.append("no full-chapter coverage report = max 9.2")
    if public_audio_enabled:
        score = min(score, 5.0)
        caps.append("public audio enabled = max 5.0")
    return {
        "book_slug": "dracula",
        "score": round(score, 2),
        "score_status": "NO_MODEL_APPROVED_YET",
        "generated_samples_present": generated_samples,
        "human_review_approved": human_review_approved,
        "license_snapshots_present": license_present,
        "chapter_coverage_report_present": coverage_present,
        "public_audio_enabled": public_audio_enabled,
        "caps_applied": caps,
        "final_public_audio_status": "BLOCKED",
    }


def write_scorecard(evaluations: list[dict[str, Any]], output_dir: Path) -> None:
    scorecard = compute_scorecard(evaluations)
    (ROOT_DIR / "AUDIOBOOK_ENGLISH_SAMPLE_SCORECARD.json").write_text(
        json.dumps(scorecard, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# English Audiobook Sample Scorecard",
        "",
        f"Score: {scorecard['score']}/10",
        "",
        f"Status: {scorecard['score_status']}",
        "",
        "Final public audio status: BLOCKED",
        "",
        "## Caps Applied",
        "",
    ]
    if scorecard["caps_applied"]:
        for cap in scorecard["caps_applied"]:
            lines.append(f"- {cap}")
    else:
        lines.append("- No caps applied.")
    lines.extend(
        [
            "",
            "A 9.9 score requires generated internal samples, human listening review, license clearance, full coverage evidence, and owner approval.",
            "",
            f"Local evaluation output: `{output_dir}`",
            "",
        ]
    )
    (ROOT_DIR / "AUDIOBOOK_ENGLISH_SAMPLE_SCORECARD.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", default="dracula")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    if args.book_slug != "dracula":
        parser.error("Only Dracula is in scope for this English audio bake-off.")
    manifests = sorted(args.output_dir.glob("*/generation_manifest.json"))
    if not manifests:
        # Evaluation can still run before local benchmark output exists.
        manifests = sorted((ROOT_DIR / "data" / "audiobook_generation" / "english_model_configs").glob("*.json"))
        evaluations = [
            {
                "model_id": json.loads(path.read_text(encoding="utf-8")).get("model_id", path.stem),
                "manifest_path": str(path),
                "qa_status": "PENDING_BENCHMARK_RUN",
                "asr_word_error_rate": None,
                "mos_score": None,
                "human_review_required": True,
                "public_audio_url_count": 0,
                "audio_output_count": 0,
                "recommended_release_action": "DO_NOT_PUBLISH_AUDIO",
                "notes": ["Run audiobook:english-model-bakeoff:dry-run before sample review."],
            }
            for path in manifests
        ]
    else:
        evaluations = [evaluate_manifest(path) for path in manifests]
    write_reports(evaluations, args.output_dir)
    print(f"English audiobook sample evaluation complete: models={len(evaluations)} output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
