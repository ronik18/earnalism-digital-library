#!/usr/bin/env python3
"""Plan dry-run English audiobook model bake-offs for Dracula."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.audiobook_generation.english_model_adapters import ADAPTER_REGISTRY, adapter_for_model  # noqa: E402


SHORTLIST_PATH = ROOT_DIR / "data" / "audiobook_models" / "english_model_shortlist.json"
CHUNKS_PATH = ROOT_DIR / "data" / "audiobook_generation" / "dracula" / "chunks.json"
CONFIG_DIR = ROOT_DIR / "data" / "audiobook_generation" / "english_model_configs"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "output" / "audiobook_bakeoff" / "dracula"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_chunks() -> list[dict[str, Any]]:
    payload = load_json(CHUNKS_PATH)
    chunks = payload.get("chunks")
    if not isinstance(chunks, list) or len(chunks) < 10:
        raise ValueError("Dracula chunk fixture must contain at least 10 representative chunks.")
    return chunks


def load_shortlist() -> list[dict[str, Any]]:
    payload = load_json(SHORTLIST_PATH)
    models = payload.get("models")
    if not isinstance(models, list):
        raise ValueError("English model shortlist must contain a models array.")
    return models


def load_config(model_id: str) -> dict[str, Any]:
    mapping = {
        "chatterbox-tts": "chatterbox_english_gothic_v1.json",
        "dia": "dia_english_dialogue_v1.json",
        "kokoro-82m": "kokoro_english_baseline_v1.json",
        "f5-tts": "f5tts_english_research_v1.json",
        "xtts-v2": "xttsv2_english_research_v1.json",
    }
    path = CONFIG_DIR / mapping[model_id]
    return load_json(path)


def write_manifest(model_id: str, output_dir: Path, results: list[dict[str, Any]], summary: dict[str, Any]) -> Path:
    model_dir = output_dir / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / "generation_manifest.json"
    path.write_text(
        json.dumps(
            {
                "model_id": model_id,
                "book_slug": "dracula",
                "status": summary["status"],
                "internal_review_only": True,
                "public_audio_url": "",
                "audio_published": False,
                "results": results,
                "summary": summary,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def csv_text(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    fields = [
        "model_id",
        "status",
        "benchmark_status",
        "license_name",
        "production_allowed",
        "chunk_count",
        "planned_audio_outputs",
        "owner_approval_status",
        "public_audio_url",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return output.getvalue()


def markdown_summary(rows: list[dict[str, Any]], mode: str) -> str:
    lines = [
        "# English Audiobook Model Bake-Off Summary",
        "",
        f"Mode: {mode}",
        "",
        "Scope: Dracula internal review only. No audio is public and no provider API was called.",
        "",
        "| Model | Status | License gate | Owner approval | Public URL |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {model_id} | {status} | {production_allowed} | {owner_approval_status} | {public_audio_url} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Release decision: NO_MODEL_APPROVED_YET.",
            "",
        ]
    )
    return "\n".join(lines)


def run_benchmark(mode: str, output_dir: Path, *, require_owner_approval: bool) -> dict[str, Any]:
    if mode not in {"plan", "dry-run", "local"}:
        raise ValueError("mode must be plan, dry-run, or local")
    chunks = load_chunks()
    rows: list[dict[str, Any]] = []
    manifest_paths: list[str] = []
    for model in load_shortlist():
        model_id = str(model["model_id"])
        adapter_class = adapter_for_model(model_id)
        adapter = adapter_class()
        config = load_config(model_id)
        environment = adapter.check_environment(book_slug="dracula", require_owner_approval=require_owner_approval)
        license_gate = adapter.validate_license()
        resources = adapter.estimate_resources(len(chunks))
        chunk_results = []
        if mode == "plan":
            status = "PLAN_READY"
        else:
            for chunk in chunks:
                if mode == "local":
                    result = adapter.generate_chunk_local(
                        chunk,
                        output_dir=output_dir,
                        book_slug="dracula",
                        require_owner_approval=require_owner_approval,
                    )
                else:
                    result = adapter.generate_chunk_dry_run(chunk, output_dir=output_dir)
                chunk_results.append(result.as_dict())
            statuses = {result["status"] for result in chunk_results}
            status = "DRY_RUN_PLANNED" if mode == "dry-run" else sorted(statuses)[0]
            if len(statuses) > 1:
                status = "MIXED_LOCAL_GATE_STATUS"
        summary = {
            "model_id": model_id,
            "status": status,
            "benchmark_status": model.get("benchmark_status", ""),
            "license_name": license_gate["license_name"],
            "production_allowed": str(license_gate["production_allowed"]).lower(),
            "chunk_count": len(chunks),
            "planned_audio_outputs": 0,
            "owner_approval_status": environment.owner_approval_status,
            "public_audio_url": "",
            "config": config,
            "environment": environment.as_dict(),
            "license": license_gate,
            "resources": resources,
        }
        manifest_paths.append(str(write_manifest(model_id, output_dir, chunk_results, summary)))
        rows.append(summary)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "english_model_bakeoff_summary.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "book_slug": "dracula",
                "mode": mode,
                "internal_review_only": True,
                "public_audio_created": False,
                "paid_provider_calls": 0,
                "model_count": len(rows),
                "manifest_paths": manifest_paths,
                "models": rows,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "english_model_bakeoff_summary.csv").write_text(csv_text(rows), encoding="utf-8")
    (output_dir / "english_model_bakeoff_summary.md").write_text(markdown_summary(rows, mode), encoding="utf-8")
    return {"rows": rows, "output_dir": str(output_dir)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", default="dracula")
    parser.add_argument("--mode", choices=["plan", "dry-run", "local"], default="plan")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--require-owner-approval", action="store_true")
    args = parser.parse_args()
    if args.book_slug != "dracula":
        parser.error("Only Dracula is approved for this internal English benchmark.")
    result = run_benchmark(args.mode, args.output_dir, require_owner_approval=args.require_owner_approval)
    print(
        "English audiobook model bake-off complete: "
        f"mode={args.mode} models={len(result['rows'])} output={result['output_dir']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

