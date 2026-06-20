#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.audiobook_generation.model_adapters import ADAPTERS
from scripts.bengali_audiobook_chunker import DEFAULT_OUTPUT_DIR, SAMPLE_TEXT, chunk_text, write_outputs

SHORTLIST_PATH = ROOT / "data/audiobook_models/model_shortlist.json"
VOICE_PROFILE_PATH = ROOT / "data/audiobook_voice_profiles/bengali-gothic-premium-v1.json"
CONFIG_DIR = ROOT / "data/audiobook_generation/model_configs"
APPROVAL_PATH = ROOT / "data/audiobook_governance/kshudhita-pashan.local_generation_approval.json"
OUTPUT_ROOT = ROOT / "output/audiobook_bakeoff/kshudhita-pashan"
SELECTION_REPORT = ROOT / "AUDIOBOOK_MODEL_SELECTION_REPORT.md"

REPRESENTATIVE_EMOTIONS = [
    "neutral_literary",
    "eerie",
    "suspense",
    "dialogue",
    "sorrow",
    "fear",
    "anger_restrained",
    "whispered_tension",
]

CONFIG_BY_MODEL = {
    "svara-tts-v1": "svara_bengali_gothic_v1.json",
    "mahatts-v2": "mahatts_bengali_gothic_v1.json",
    "ai4bharat-indic-tts": "ai4bharat_bengali_baseline_v1.json",
    "f5-tts": "f5tts_bengali_research_v1.json",
}


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_chunks() -> list[dict[str, Any]]:
    chunks_path = DEFAULT_OUTPUT_DIR / "chunks.json"
    if not chunks_path.exists():
        chunks = chunk_text("kshudhita-pashan", SAMPLE_TEXT)
        write_outputs(chunks, DEFAULT_OUTPUT_DIR)
        return chunks
    payload = read_json(chunks_path, {})
    chunks = payload.get("chunks") if isinstance(payload, dict) else []
    if not chunks:
        chunks = chunk_text("kshudhita-pashan", SAMPLE_TEXT)
        write_outputs(chunks, DEFAULT_OUTPUT_DIR)
    return chunks


def select_representative_chunks(chunks: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for emotion in REPRESENTATIVE_EMOTIONS:
        match = next((chunk for chunk in chunks if chunk.get("expected_emotion") == emotion), None)
        if match and match["chunk_id"] not in seen_ids:
            selected.append(match)
            seen_ids.add(match["chunk_id"])
    for chunk in chunks:
        if len(selected) >= limit:
            break
        if chunk["chunk_id"] not in seen_ids:
            selected.append(chunk)
            seen_ids.add(chunk["chunk_id"])
    return selected[:limit]


def owner_approval_loaded() -> bool:
    payload = read_json(APPROVAL_PATH, {})
    return bool(
        isinstance(payload, dict)
        and payload.get("book_slug") == "kshudhita-pashan"
        and payload.get("owner_approved_local_generation") is True
        and payload.get("internal_review_only") is True
    )


def load_config(model_id: str) -> dict[str, Any]:
    filename = CONFIG_BY_MODEL.get(model_id)
    if not filename:
        return {}
    return read_json(CONFIG_DIR / filename, {})


def benchmark_model(model: dict[str, Any], chunks: list[dict[str, Any]], mode: str, allow_local: bool) -> dict[str, Any]:
    model_id = model["model_id"]
    adapter_class = ADAPTERS.get(model_id)
    if not adapter_class:
        return {
            "model_id": model_id,
            "status": "NO_ADAPTER_RESEARCH_ONLY",
            "audio_generated": False,
            "public_audio_urls_created": False,
            "chunks": [],
            "license_status": "NOT_EVALUATED_BY_ADAPTER",
        }
    adapter = adapter_class(OUTPUT_ROOT / model_id)
    environment = adapter.check_environment()
    license_result = adapter.validate_license()
    config = load_config(model_id)
    chunk_results: list[dict[str, Any]] = []
    audio_generated = False
    for chunk in chunks:
        if mode == "local":
            result = adapter.generate_chunk_local(
                chunk,
                OUTPUT_ROOT / model_id / f"{chunk['chunk_id']}.wav",
                owner_approved=allow_local,
                config=config,
            )
            audio_generated = audio_generated or result.status == "LOCAL_GENERATION_READY"
        else:
            result = adapter.generate_chunk_dry_run(chunk, config=config)
        chunk_results.append(
            {
                "chunk_id": chunk["chunk_id"],
                "expected_emotion": chunk["expected_emotion"],
                "status": result.status,
                "message": result.message,
                "metadata": result.metadata,
            }
        )
    model_dir = OUTPUT_ROOT / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "model_id": model_id,
        "mode": mode,
        "scope": "INTERNAL_REVIEW_ONLY",
        "environment": asdict(environment),
        "license": license_result.metadata,
        "license_status": license_result.status,
        "resource_estimate": adapter.estimate_resources(),
        "config": config,
        "audio_generated": audio_generated,
        "public_audio_urls_created": False,
        "chunks": chunk_results,
    }
    write_json(model_dir / "generation_manifest.json", manifest)
    return manifest


def write_selection_report(payload: dict[str, Any]) -> None:
    lines = [
        "# Audiobook Model Selection Report",
        "",
        "Final status: `NO_MODEL_APPROVED_YET`",
        "",
        "No model is approved for public preview or full audiobook release. This bake-off is internal-review-only and dry-run by default.",
        "",
        "## Current Recommendation",
        "",
        "- Best Bengali pronunciation: `AI4Bharat Indic-TTS` as baseline only.",
        "- Best literary naturalness candidate: `Svara-TTS v1` pending local sample and license review.",
        "- Best emotion/style candidate: `Svara-TTS v1` pending documentation-confirmed style tags.",
        "- Best commercial/license readiness candidate: `MahaTTS/MahaTTSv2` pending exact license verification.",
        "- Best local generation cost candidate: `AI4Bharat Indic-TTS` or `MahaTTS` after installation/resource check.",
        "- Final recommended model: `NO_MODEL_APPROVED_YET`.",
        "- Required next step: generate owner-approved internal samples, complete license review, then complete human listening review.",
        "",
        "## Safety",
        "",
        "- Kshudhita Pashan remains pipeline-only.",
        "- Dracula remains the only live approved reading title.",
        "- No public audio URL was created.",
        "- No Listen Now CTA was added.",
        "- No paid or cloud provider API was called.",
        "",
        "## Model Statuses",
        "",
        "| Model | Status | License status | Audio generated |",
        "| --- | --- | --- | --- |",
    ]
    for model in payload["models"]:
        lines.append(
            f"| {model['model_id']} | {model.get('recommended_status', model.get('status'))} | "
            f"{model.get('license_status', 'N/A')} | {model.get('audio_generated', False)} |"
        )
    SELECTION_REPORT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_summary(payload: dict[str, Any]) -> None:
    write_json(OUTPUT_ROOT / "benchmark_summary.json", payload)
    csv_path = OUTPUT_ROOT / "benchmark_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "model_id",
                "status",
                "recommended_status",
                "license_status",
                "audio_generated",
                "public_audio_urls_created",
                "chunk_count",
            ],
        )
        writer.writeheader()
        for model in payload["models"]:
            writer.writerow(
                {
                    "model_id": model["model_id"],
                    "status": model.get("status", ""),
                    "recommended_status": model.get("recommended_status", ""),
                    "license_status": model.get("license_status", ""),
                    "audio_generated": model.get("audio_generated", False),
                    "public_audio_urls_created": model.get("public_audio_urls_created", False),
                    "chunk_count": len(model.get("chunks", [])),
                }
            )


def run_benchmark(book_slug: str, mode: str, require_owner_approval: bool) -> dict[str, Any]:
    if book_slug != "kshudhita-pashan":
        raise ValueError("This bake-off is scoped only to kshudhita-pashan.")
    if mode not in {"plan", "dry-run", "local"}:
        raise ValueError("mode must be plan, dry-run, or local.")
    approval = owner_approval_loaded()
    if mode == "local" and (require_owner_approval and not approval):
        raise PermissionError(f"Local generation blocked. Approval file required: {APPROVAL_PATH}")

    shortlist = read_json(SHORTLIST_PATH, {"models": []})
    voice_profile = read_json(VOICE_PROFILE_PATH, {})
    chunks = select_representative_chunks(load_chunks())
    models: list[dict[str, Any]] = []
    for model in shortlist.get("models", []):
        if mode == "plan":
            model_result = {
                **model,
                "status": "PLANNED_INTERNAL_REVIEW_ONLY",
                "audio_generated": False,
                "public_audio_urls_created": False,
                "chunks": [{"chunk_id": chunk["chunk_id"], "planned": True} for chunk in chunks],
            }
        else:
            model_result = {**model, **benchmark_model(model, chunks, mode, approval)}
        models.append(model_result)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "book_slug": book_slug,
        "mode": mode,
        "scope": "INTERNAL_REVIEW_ONLY",
        "dracula_only_live": True,
        "kshudhita_pipeline_only": True,
        "public_audio_urls_created": False,
        "audio_generated": any(model.get("audio_generated") for model in models),
        "owner_approval_loaded": approval,
        "voice_profile": voice_profile,
        "representative_chunk_count": len(chunks),
        "models": models,
        "final_status": "NO_MODEL_APPROVED_YET",
    }
    write_summary(payload)
    write_selection_report(payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan or dry-run Bengali audiobook model bake-off.")
    parser.add_argument("--book-slug", default="kshudhita-pashan")
    parser.add_argument("--mode", choices=["plan", "dry-run", "local"], default="plan")
    parser.add_argument("--require-owner-approval", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = run_benchmark(args.book_slug, args.mode, args.require_owner_approval)
    except PermissionError as exc:
        print(str(exc))
        return 2
    print(
        f"Bengali audiobook model bake-off {payload['mode']} complete: "
        f"{len(payload['models'])} models, {payload['representative_chunk_count']} chunks."
    )
    print(f"Output: {OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
