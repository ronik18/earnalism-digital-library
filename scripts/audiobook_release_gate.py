#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "output/audiobook_bakeoff/kshudhita-pashan/release_gate.json"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def run_release_gate() -> dict[str, object]:
    controlled_launch = read_text(ROOT / "frontend/src/lib/controlledLaunch.js")
    home = read_text(ROOT / "frontend/src/pages/Home.jsx")
    library = read_text(ROOT / "frontend/src/pages/Library.jsx")
    benchmark_summary = read_text(ROOT / "output/audiobook_bakeoff/kshudhita-pashan/benchmark_summary.json")
    lowered_public_sources = "\n".join([controlled_launch, home, library]).lower()
    blockers: list[str] = []
    if "kshudhita-pashan" not in controlled_launch:
        blockers.append("Kshudhita Pashan pipeline slug missing from controlled launch config.")
    if "listen now" in lowered_public_sources or "full audiobook" in lowered_public_sources:
        blockers.append("Public UI contains prohibited audio CTA text.")
    if "audiobook_enabled: true" in controlled_launch:
        blockers.append("Controlled launch config enables audiobook.")
    if "\"public_audio_urls_created\": true" in benchmark_summary:
        blockers.append("Benchmark summary created public audio URLs.")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not blockers else "BLOCKED",
        "blockers": blockers,
        "dracula_only_live": True,
        "dracula_audio_disabled": "audiobook_enabled: false" in controlled_launch,
        "kshudhita_pipeline_only": "PIPELINE_ONLY" in controlled_launch,
        "public_audio_urls_created": False,
        "listen_now_cta_allowed": False,
        "full_audiobook_public_allowed": False,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = run_release_gate()
    print(f"Audiobook release gate {payload['status']}. Report: {OUTPUT_PATH}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
