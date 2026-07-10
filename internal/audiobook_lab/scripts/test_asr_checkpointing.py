#!/usr/bin/env python3
"""Regression checks for resumable ASR checkpointing."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPTS_DIR / "factory_hooks"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(HOOK_DIR))

from asr_sync_hook import (  # noqa: E402
    asr_checkpoint_path,
    asr_sync_budget_guard,
    transcribe_chunk_with_checkpoint,
)


class temporary_env:
    def __init__(self, **values: str | None) -> None:
        self.values = values
        self.previous: dict[str, str | None] = {}

    def __enter__(self):
        for key, value in self.values.items():
            self.previous[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return self

    def __exit__(self, exc_type, exc, tb):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class Args:
    slug = "bn-066"
    language = "Bengali"
    title = "Anandamath"
    author = "Bankim Chandra Chattopadhyay"
    force = False


class FakeTranscriptions:
    def __init__(self, outcomes: list[dict | Exception]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if not self.outcomes:
            raise AssertionError("unexpected provider call")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeAudio:
    def __init__(self, outcomes: list[dict | Exception]) -> None:
        self.transcriptions = FakeTranscriptions(outcomes)


class FakeClient:
    def __init__(self, outcomes: list[dict | Exception]) -> None:
        self.audio = FakeAudio(outcomes)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def chunk_fixture(tmp: Path) -> tuple[Path, dict]:
    audio = tmp / "chunk.mp3"
    audio.write_bytes(b"fake-audio")
    return audio, {"index": 0, "path": str(audio), "duration_seconds": 10.0, "offset_seconds": 0.0}


def assert_completed_checkpoint_is_skipped_on_resume() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        audio, chunk = chunk_fixture(tmp)
        checkpoint_path = asr_checkpoint_path(tmp, chunk)
        write_json(
            checkpoint_path,
            {
                "slug": "bn-066",
                "chunk_id": "group_0000",
                "chunk_audio_path": str(audio),
                "status": "PASS",
                "attempts": 1,
                "transcript_text": "আনন্দমঠ",
                "transcript_chars": 7,
                "duration_seconds": 10.0,
                "provider": "openai",
                "model": "whisper-1",
                "started_at": "2026-07-10T00:00:00Z",
                "completed_at": "2026-07-10T00:00:01Z",
                "error": None,
                "estimated_cost_usd": 0.0013,
                "words": [{"word": "আনন্দমঠ", "start": 0.0, "end": 1.0}],
            },
        )
        client = FakeClient([AssertionError("provider call should be skipped")])
        result = transcribe_chunk_with_checkpoint(client, audio, Args(), chunk, tmp, resume=True, force=False)
    assert result["status"] == "SKIPPED_EXISTING", result
    assert client.audio.transcriptions.calls == 0, client.audio.transcriptions.calls
    assert result["payload"]["text"] == "আনন্দমঠ", result


def assert_timeout_writes_provider_timeout_checkpoint() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        audio, chunk = chunk_fixture(tmp)
        client = FakeClient([TimeoutError("provider timed out")])
        result = transcribe_chunk_with_checkpoint(client, audio, Args(), chunk, tmp, resume=False, force=False, max_retries=3)
        checkpoint = json.loads(asr_checkpoint_path(tmp, chunk).read_text(encoding="utf-8"))
    assert result["status"] == "PROVIDER_TIMEOUT", result
    assert client.audio.transcriptions.calls == 1, client.audio.transcriptions.calls
    assert checkpoint["status"] == "PROVIDER_TIMEOUT", checkpoint
    assert checkpoint["attempts"] == 1, checkpoint


def assert_retry_count_is_bounded() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        audio, chunk = chunk_fixture(tmp)
        client = FakeClient([RuntimeError("temporary failure"), RuntimeError("still failing")])
        result = transcribe_chunk_with_checkpoint(client, audio, Args(), chunk, tmp, resume=False, force=False, max_retries=1)
        checkpoint = json.loads(asr_checkpoint_path(tmp, chunk).read_text(encoding="utf-8"))
    assert result["status"] == "FAILED", result
    assert client.audio.transcriptions.calls == 2, client.audio.transcriptions.calls
    assert checkpoint["attempts"] == 2, checkpoint


def assert_budget_estimate_uses_remaining_duration() -> None:
    with temporary_env(
        EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD="1",
        EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE="0.6",
        MAX_TTS_BUDGET_USD="2",
    ):
        guard = asr_sync_budget_guard(
            duration_seconds=100,
            completed_duration_seconds=40,
            prior_estimated_usd=1.0,
            prior_asr_estimated_usd=0.1,
            completed_chunk_count=4,
            remaining_chunk_count=6,
            total_chunk_count=10,
        )
    assert guard["ok"], guard
    assert guard["estimated_asr_cost_usd"] == 0.6, guard
    assert guard["remaining_duration_seconds"] == 60, guard
    assert guard["total_estimated_usd"] == 1.7, guard


def assert_missing_asr_cap_blocks_before_provider_call() -> None:
    with temporary_env(
        EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD=None,
        EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD=None,
        MAX_TTS_BUDGET_USD="5",
    ):
        guard = asr_sync_budget_guard(duration_seconds=60, completed_duration_seconds=0, prior_estimated_usd=1.0)
    assert not guard["ok"], guard
    assert guard["code"] == "ASR_SYNC_BUDGET_GATE_MISSING", guard


def main() -> int:
    assert_completed_checkpoint_is_skipped_on_resume()
    assert_timeout_writes_provider_timeout_checkpoint()
    assert_retry_count_is_bounded()
    assert_budget_estimate_uses_remaining_duration()
    assert_missing_asr_cap_blocks_before_provider_call()
    print("ASR checkpointing regression checks PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
