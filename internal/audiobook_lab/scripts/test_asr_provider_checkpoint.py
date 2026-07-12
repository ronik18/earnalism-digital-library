#!/usr/bin/env python3
"""No-provider regression tests for hash-bound ASR checkpoints."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPTS_DIR / "factory_hooks"
sys.path[:0] = [str(SCRIPTS_DIR), str(HOOK_DIR)]

import asr_sync_hook as hook  # noqa: E402


class Args:
    slug = "a-ghost-story"
    language = "eng"


def checkpoint_payload(audio: Path, manuscript: str) -> dict:
    return {
        "checkpoint_version": hook.ASR_CHECKPOINT_VERSION,
        "slug": Args.slug,
        "audio_hash": hook.sha256_file(audio),
        "source_text_hash": hook.sha256_text(manuscript),
        "provider": "openai",
        "model": hook.ASR_MODEL,
        "language": "en",
        "transcript": "the complete transcript",
        "words": [{"word": "the", "start": 0.0, "end": 0.2}],
        "asr_chunks": [{"index": 0}],
        "split_report": {"status": "NOT_RUN"},
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        run_dir = Path(raw)
        audio = run_dir / "audio.mp3"
        audio.write_bytes(b"private-audio")
        manuscript = "the complete manuscript"
        payload = checkpoint_payload(audio, manuscript)
        (run_dir / "asr_provider_checkpoint.json").write_text(json.dumps(payload), encoding="utf-8")
        assert hook.load_asr_checkpoint(run_dir, audio, manuscript, Args()) == payload
        assert hook.load_asr_checkpoint(run_dir, audio, manuscript + " changed", Args()) is None
        payload["words"] = []
        (run_dir / "asr_provider_checkpoint.json").write_text(json.dumps(payload), encoding="utf-8")
        assert hook.load_asr_checkpoint(run_dir, audio, manuscript, Args()) is None
    windows = hook.listening_sample_windows(
        839.256,
        {
            "asr_chunks": [
                {"offset_seconds": value}
                for value in (0.0, 169.968, 331.776, 505.392, 645.6, 808.152)
            ]
        },
    )
    assert len(windows) == 6, windows
    assert windows[0]["sample_label"] == "first_60s", windows
    assert windows[2]["sample_label"] == "middle_60s", windows
    assert windows[-1]["sample_label"] == "final_60s", windows
    assert all(item["selection_method"] == "tts_chunk_boundary" for item in windows), windows
    nine_chunk_windows = hook.listening_sample_windows(
        900.0,
        {"asr_chunks": [{"offset_seconds": float(index * 100)} for index in range(9)]},
    )
    assert len(nine_chunk_windows) == 6, nine_chunk_windows
    assert nine_chunk_windows[0]["start_time"] == 0.0, nine_chunk_windows
    assert nine_chunk_windows[-1]["start_time"] == 800.0, nine_chunk_windows
    print("ASR provider checkpoint regression checks PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
