#!/usr/bin/env python3
"""Run a private, source-bound Kokoro voice audition from a local #269 source.

This opt-in command needs a CUDA runtime and an already cached immutable model
snapshot. It never downloads models, invokes remote providers, uploads audio,
or grants full-generation/publication authority.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from io import BytesIO
from pathlib import Path

from audiobook_provenance import (
    DEFAULT_VOICES,
    capture_runtime,
    find_hf_model_snapshot,
    normalize_gutenberg_story,
    OPEN_WINDOW_MANUSCRIPT_SHA256,
    OPEN_WINDOW_SOURCE_SHA256,
    require_source_binding,
    run_auditions,
    sha256_bytes,
    snapshot_voice_inventory,
    source_binding,
)

EXPECTED_SOURCE_SHA256 = OPEN_WINDOW_SOURCE_SHA256
EXPECTED_MANUSCRIPT_SHA256 = OPEN_WINDOW_MANUSCRIPT_SHA256
SOURCE_URL = "https://www.gutenberg.org/cache/epub/269/pg269.txt"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Previously acquired, legally cleared Gutenberg #269 UTF-8 text file")
    parser.add_argument("--output-dir", required=True, help="Private output directory for audition WAVs and manifest")
    parser.add_argument("--voice", action="append", dest="voices", help="Audition voice; pass two or three times (default: af_heart, af_bella, af_nicole)")
    parser.add_argument("--run-private-audition", action="store_true", help="Explicitly synthesize the private samples")
    parser.add_argument("--speed", type=float, default=0.92)
    parser.add_argument("--sample-rate", type=int, default=24000)
    args = parser.parse_args()
    if not args.run_private_audition:
        parser.error("audio synthesis requires --run-private-audition")

    voices = args.voices or list(DEFAULT_VOICES)
    source_bytes = Path(args.source).read_bytes()
    text = normalize_gutenberg_story(source_bytes)
    binding = source_binding(source_bytes, text, SOURCE_URL)
    try:
        require_source_binding(binding, expected_source_sha256=EXPECTED_SOURCE_SHA256,
                               expected_manuscript_sha256=EXPECTED_MANUSCRIPT_SHA256)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    revision, snapshot = find_hf_model_snapshot()
    runtime = capture_runtime(model_revision=revision, model_path=snapshot)
    if not runtime["pytorch"]["cuda_available"]:
        raise SystemExit("A CUDA-enabled PyTorch runtime is required for Kokoro voice audition")
    if not runtime["model"]["pinning_ready"] or not snapshot:
        raise SystemExit("An immutable local Kokoro snapshot and its artifact hash are required; no model download was attempted")

    os.environ["HF_HUB_OFFLINE"] = "1"
    from kokoro import KPipeline

    inventory = snapshot_voice_inventory(snapshot, "en")
    available_voice_ids = [row["voice_id"] for row in inventory]
    if any(voice not in available_voice_ids for voice in voices):
        raise SystemExit("One or more requested audition voices are absent from the pinned snapshot")

    pipeline = KPipeline(lang_code="a", repo_id=str(snapshot), device="cuda")

    def synthesize(sample: str, voice: str, settings: dict) -> bytes:
        import numpy as np
        import soundfile as sf

        chunks = []
        for result in pipeline(sample, voice=voice, speed=float(settings["speed"])):
            output = getattr(result, "output", None)
            audio = output.audio if output is not None and hasattr(output, "audio") else result[2]
            if hasattr(audio, "detach"):
                audio = audio.detach().cpu().numpy()
            chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            raise RuntimeError(f"Kokoro returned no audio for voice {voice}")
        buffer = BytesIO()
        sf.write(buffer, np.concatenate(chunks), args.sample_rate, format="WAV", subtype="PCM_16")
        return buffer.getvalue()

    manifest = run_auditions(
        text=" ".join(text.split()[:100]), voices=voices, language="en",
        output_dir=args.output_dir, source_binding_data=binding,
        model_revision=revision, settings={"speed": args.speed, "sample_rate": args.sample_rate},
        synthesize=synthesize, runtime_provenance=runtime,
        available_voices=available_voice_ids,
    )
    print(json.dumps({"result": "PRIVATE_AUDITION_COMPLETE", "voices": len(manifest["voices"]),
                      "source_sha256": binding["source_sha256"],
                      "manuscript_sha256": binding["manuscript_sha256"],
                      "model_revision": revision, "model_artifact_sha256": runtime["model"]["artifact_sha256"],
                      "manifest": str(Path(args.output_dir) / "audition_manifest.json"),
                      "full_generation_authorized": False, "public_release_ready": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
