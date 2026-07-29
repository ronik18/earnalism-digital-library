#!/usr/bin/env python3
"""Generate one source-bound Muchiram ElevenLabs preview for private comparison."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.lib.elevenlabs_tts_client import (  # noqa: E402
    ElevenLabsSettings,
    generate_tts_audio,
    sha256_file,
    sha256_text,
)


SLUG = "muchiram-gurer-jibanchorit"
TEXT_SHA256 = "1ebd84cd348bb47004917e3efa98b812f64dc62693eb18f0b728e86f1c341f16"
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
VOICE_NAME = "Rachel"
MODEL_ID = "eleven_v3"
PASSAGES_PATH = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs"
    / "muchiram_sarvam_segmented_representative/bakeoff_passages.json"
)
OUTPUT_DIR = (
    ROOT
    / "internal/audiobook_lab/preview_comparisons/muchiram_20260729"
)
OUTPUT_PATH = OUTPUT_DIR / "muchiram_elevenlabs_v3_rachel_opening.mp3"
MANIFEST_PATH = OUTPUT_DIR / "muchiram_elevenlabs_v3_rachel_opening.json"


def main() -> int:
    if os.environ.get("EARNALISM_APPROVE_ELEVENLABS_MUCHIRAM_PREVIEW") != "true":
        raise RuntimeError(
            "EARNALISM_APPROVE_ELEVENLABS_MUCHIRAM_PREVIEW=true is required"
        )
    if OUTPUT_PATH.exists() or MANIFEST_PATH.exists():
        raise RuntimeError("Muchiram ElevenLabs preview fingerprint already exists")

    payload = json.loads(PASSAGES_PATH.read_text(encoding="utf-8"))
    opening = next(
        row
        for row in payload["passages"]
        if row["slug"] == SLUG and row["passage_id"] == "opening"
    )
    text = opening["text"]
    if sha256_text(text) != TEXT_SHA256 or opening["text_hash"] != TEXT_SHA256:
        raise RuntimeError("Muchiram opening text hash does not match the approved scope")

    settings = ElevenLabsSettings(
        provider="elevenlabs",
        voice_id=VOICE_ID,
        voice_name=VOICE_NAME,
        model_id=MODEL_ID,
        output_format="mp3_44100_128",
        stability=0.5,
        similarity_boost=0.75,
        style_exaggeration=0.0,
        speaker_boost=True,
        beta_services_allowed=False,
        voice_cloning_allowed=False,
        elevenreader_allowed=False,
    )
    result = generate_tts_audio(
        chunk_id="muchiram-opening-elevenlabs-v3-rachel",
        text=text,
        settings=settings,
        output_path=OUTPUT_PATH,
        execute=True,
        timeout_seconds=120,
    )
    manifest = {
        **result,
        "slug": SLUG,
        "text": text,
        "text_length": len(text),
        "approved_text_sha256": TEXT_SHA256,
        "audio_size_bytes": OUTPUT_PATH.stat().st_size,
        "audio_sha256_verified": sha256_file(OUTPUT_PATH),
        "owner_authorization": "AUTHORIZE_ONE_ELEVENLABS_MUCHIRAM_INTERNAL_PREVIEW",
        "internal_preview_only": True,
        "public_release_allowed": False,
        "upload_performed": False,
        "publication_performed": False,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["generation_status"],
                "output_path": result["output_path"],
                "audio_hash": result["audio_hash"],
                "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
