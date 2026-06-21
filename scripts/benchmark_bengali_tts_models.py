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
from scripts.bengali_audiobook_chunker import DEFAULT_OUTPUT_DIR, approved_source_status, chunk_text, write_outputs

SHORTLIST_PATH = ROOT / "data/audiobook_models/model_shortlist.json"
LICENSE_EVIDENCE_DIR = ROOT / "data/audiobook_models/license_evidence"
VOICE_PROFILE_PATH = ROOT / "data/audiobook_voice_profiles/bengali-gothic-premium-v1.json"
CONFIG_DIR = ROOT / "data/audiobook_generation/model_configs"
APPROVAL_PATH = ROOT / "data/audiobook_governance/kshudhita-pashan.local_generation_approval.json"
HUMAN_REVIEW_PATH = ROOT / "data/audiobook_governance/kshudhita-pashan.bengali_human_listening_review.json"
OUTPUT_ROOT = ROOT / "output/audiobook_bakeoff/kshudhita-pashan"
SELECTION_REPORT = ROOT / "AUDIOBOOK_MODEL_SELECTION_REPORT.md"
SCORECARD_JSON = ROOT / "AUDIOBOOK_BENGALI_MODEL_BAKEOFF_SCORECARD.json"
SCORECARD_MD = ROOT / "AUDIOBOOK_BENGALI_MODEL_BAKEOFF_SCORECARD.md"

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
    source_status = approved_source_status()
    if source_status["status"] != "READY":
        write_outputs([], DEFAULT_OUTPUT_DIR)
        return []
    chunks_path = DEFAULT_OUTPUT_DIR / "chunks.json"
    if not chunks_path.exists():
        raise RuntimeError("Approved Kshudhita source text is ready, but chunks.json has not been generated.")
    payload = read_json(chunks_path, {})
    chunks = payload.get("chunks") if isinstance(payload, dict) else []
    if not chunks:
        raise RuntimeError("Approved Kshudhita source text is ready, but chunk output is empty.")
    return chunks


def load_license_evidence(model_id: str) -> dict[str, Any]:
    filename_by_id = {
        "chatterbox-multilingual-v3": "chatterbox.json",
    }
    path = LICENSE_EVIDENCE_DIR / filename_by_id.get(model_id, f"{model_id}.json")
    if not path.exists():
        return {
            "model_id": model_id,
            "present": False,
            "commercial_allowed": False,
            "verified_by": "missing",
            "production_candidate_allowed": False,
            "blocking_reason": "License evidence snapshot is missing.",
        }
    payload = read_json(path, {})
    payload["present"] = True
    payload["production_candidate_allowed"] = (
        payload.get("commercial_allowed") is True
        and payload.get("verified_by") not in {"", "operator_required", "missing"}
        and payload.get("human_license_review_approved") is True
    )
    if not payload["production_candidate_allowed"]:
        payload["blocking_reason"] = payload.get("blocking_reason") or "Human license review is required."
    return payload


def recommended_status_for_model(model: dict[str, Any], evidence: dict[str, Any]) -> str:
    if not model.get("bengali_supported"):
        return "RESEARCH_ONLY_UNSUPPORTED_BENGALI"
    if evidence.get("production_candidate_allowed") is not True:
        return "LICENSE_REVIEW_REQUIRED"
    if model.get("commercial_allowed") is not True:
        return "LICENSE_REVIEW_REQUIRED"
    return str(model.get("recommended_status") or "INTERNAL_REVIEW_ONLY")


def operator_required_payload(book_slug: str, mode: str, source_status: dict[str, Any]) -> dict[str, Any]:
    shortlist = read_json(SHORTLIST_PATH, {"models": []})
    models: list[dict[str, Any]] = []
    for model in shortlist.get("models", []):
        evidence = load_license_evidence(str(model["model_id"]))
        models.append(
            {
                **model,
                "status": "OPERATOR_REQUIRED",
                "recommended_status": recommended_status_for_model(model, evidence),
                "license_evidence": evidence,
                "audio_generated": False,
                "public_audio_urls_created": False,
                "chunks": [],
            }
        )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "book_slug": book_slug,
        "mode": mode,
        "scope": "INTERNAL_REVIEW_ONLY",
        "source_status": source_status,
        "dracula_only_live": True,
        "kshudhita_pipeline_only": True,
        "public_audio_urls_created": False,
        "audio_generated": False,
        "owner_approval_loaded": owner_approval_loaded(),
        "bengali_human_listening_review": load_human_listening_review(),
        "voice_profile": read_json(VOICE_PROFILE_PATH, {}),
        "representative_chunk_count": 0,
        "models": models,
        "final_status": "OPERATOR_REQUIRED",
        "blocking_reason": source_status["blocking_reason"],
    }
    write_summary(payload)
    write_selection_report(payload)
    write_bakeoff_scorecard(payload)
    return payload


def select_representative_chunks(chunks: list[dict[str, Any]], limit: int = 32) -> list[dict[str, Any]]:
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


def load_human_listening_review() -> dict[str, Any]:
    payload = read_json(HUMAN_REVIEW_PATH, {})
    score = payload.get("bengali_human_review_score")
    approved = (
        payload.get("approved") is True
        and isinstance(score, (int, float))
        and score >= 9.5
        and payload.get("public_preview_approved") is True
        and payload.get("full_audiobook_approved") is True
    )
    return {
        "review_file": str(HUMAN_REVIEW_PATH.relative_to(ROOT)),
        "present": HUMAN_REVIEW_PATH.exists(),
        "approved": approved,
        "bengali_human_review_score": score if isinstance(score, (int, float)) else None,
        "minimum_score_for_9_9": 9.5,
        "public_preview_approved": payload.get("public_preview_approved") is True,
        "full_audiobook_approved": payload.get("full_audiobook_approved") is True,
        "blocking_reason": ""
        if approved
        else "Bengali human listening review >= 9.5 with public-preview and full-audiobook approvals is required.",
    }


def license_manual_review_complete(payload: dict[str, Any]) -> bool:
    models = payload.get("models") if isinstance(payload.get("models"), list) else []
    if not models:
        return False
    for model in models:
        evidence = model.get("license_evidence") if isinstance(model.get("license_evidence"), dict) else {}
        if evidence.get("human_license_review_approved") is not True:
            return False
        if evidence.get("verified_by") in {"", "operator_required", "missing", None}:
            return False
    return True


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
        f"Final status: `{payload.get('final_status', 'NO_MODEL_APPROVED_YET')}`",
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
    ]
    if payload.get("final_status") == "OPERATOR_REQUIRED":
        lines.extend(
            [
                "## Operator Required",
                "",
                payload.get("blocking_reason", "Approved source text is required before official bake-off planning."),
                "",
            ]
        )
    lines.extend(
        [
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
    )
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


def compute_scorecard(payload: dict[str, Any]) -> dict[str, Any]:
    score = 9.6
    caps: list[str] = []
    human_review = payload.get("bengali_human_listening_review") or {}
    if payload.get("source_status", {}).get("status") != "READY":
        score = min(score, 8.6)
        caps.append("approved source text missing = max 8.6")
    if payload.get("representative_chunk_count", 0) < 25:
        score = min(score, 9.0)
        caps.append("fewer than 25 real-source chunks = max 9.0")
    if not any(model.get("audio_generated") for model in payload.get("models", [])):
        score = min(score, 9.0)
        caps.append("no generated internal samples = max 9.0")
    if human_review.get("approved") is not True:
        score = min(score, 9.0)
        caps.append("no Bengali human listening review >= 9.5 = max 9.0")
    if not license_manual_review_complete(payload):
        score = min(score, 9.2)
        caps.append("license evidence not manually reviewed = max 9.2")
    if any(model.get("public_audio_urls_created") for model in payload.get("models", [])):
        score = min(score, 5.0)
        caps.append("public audio URL present = max 5.0")
    return {
        "book_slug": payload.get("book_slug"),
        "score": round(score, 2),
        "status": payload.get("final_status"),
        "final_public_audio_status": "BLOCKED",
        "caps_applied": caps,
        "human_review_approved": human_review.get("approved") is True,
        "bengali_human_review_score": human_review.get("bengali_human_review_score"),
        "license_manual_review_complete": license_manual_review_complete(payload),
    }


def write_bakeoff_scorecard(payload: dict[str, Any]) -> None:
    scorecard = compute_scorecard(payload)
    SCORECARD_JSON.write_text(json.dumps(scorecard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Bengali Audiobook Model Bake-Off Scorecard",
        "",
        f"Score: {scorecard['score']}/10",
        "",
        f"Status: `{scorecard['status']}`",
        "",
        "Final public audio status: `BLOCKED`",
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
            "A 9.9 score requires approved full source text, 25-40 real-source representative chunks, license clearance, generated internal samples, Bengali human listening review, and owner approval.",
            "",
            "Bengali listening review gate: score >= 9.5, public preview approval, and full-audiobook approval are all required before any 9.9 claim.",
            "",
        ]
    )
    SCORECARD_MD.write_text("\n".join(lines), encoding="utf-8")


def run_benchmark(book_slug: str, mode: str, require_owner_approval: bool) -> dict[str, Any]:
    if book_slug != "kshudhita-pashan":
        raise ValueError("This bake-off is scoped only to kshudhita-pashan.")
    if mode not in {"plan", "dry-run", "local"}:
        raise ValueError("mode must be plan, dry-run, or local.")
    source_status = approved_source_status()
    if source_status["status"] != "READY":
        return operator_required_payload(book_slug, mode, source_status)
    approval = owner_approval_loaded()
    if mode == "local" and (require_owner_approval and not approval):
        raise PermissionError(f"Local generation blocked. Approval file required: {APPROVAL_PATH}")

    shortlist = read_json(SHORTLIST_PATH, {"models": []})
    voice_profile = read_json(VOICE_PROFILE_PATH, {})
    chunks = select_representative_chunks(load_chunks())
    models: list[dict[str, Any]] = []
    for model in shortlist.get("models", []):
        evidence = load_license_evidence(str(model["model_id"]))
        if mode == "plan":
            model_result = {
                **model,
                "status": "PLANNED_INTERNAL_REVIEW_ONLY",
                "recommended_status": recommended_status_for_model(model, evidence),
                "license_evidence": evidence,
                "audio_generated": False,
                "public_audio_urls_created": False,
                "chunks": [{"chunk_id": chunk["chunk_id"], "planned": True} for chunk in chunks],
            }
        else:
            model_result = {
                **model,
                **benchmark_model(model, chunks, mode, approval),
                "recommended_status": recommended_status_for_model(model, evidence),
                "license_evidence": evidence,
            }
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
        "bengali_human_listening_review": load_human_listening_review(),
        "source_status": source_status,
        "voice_profile": voice_profile,
        "representative_chunk_count": len(chunks),
        "models": models,
        "final_status": "NO_MODEL_APPROVED_YET",
    }
    write_summary(payload)
    write_selection_report(payload)
    write_bakeoff_scorecard(payload)
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
