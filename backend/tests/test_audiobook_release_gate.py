from __future__ import annotations

import json
from pathlib import Path

from scripts.audiobook_release_gate import run_release_gate


def test_audiobook_release_gate_passes_with_dracula_audio_disabled():
    result = run_release_gate()

    assert result["status"] == "PASS"
    assert result["dracula_audio_enabled"] is False
    assert result["dracula_audiobook_enabled"] is False
    assert result["chapter_count"] == 27
    assert result["public_audio_exposed"] is False


def test_reader_manifest_keeps_audio_disabled():
    payload = json.loads(Path("data/controlled_publications/dracula/reader_manifest.json").read_text(encoding="utf-8"))

    assert payload["slug"] == "dracula"
    assert payload["audio_enabled"] is False
    assert payload["audiobook_enabled"] is False
    assert payload["audio_status"] == "NOT_AVAILABLE"


def test_release_gate_output_contains_no_public_audio_url(tmp_path: Path):
    from scripts import audiobook_release_gate

    result = audiobook_release_gate.run_release_gate()
    output = tmp_path / "release_gate.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    assert "https://theearnalism.com/audio" not in output.read_text(encoding="utf-8")

