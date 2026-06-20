from __future__ import annotations

from scripts.audiobook_release_gate import run_release_gate


def test_audiobook_release_gate_keeps_kshudhita_pipeline_only():
    payload = run_release_gate()

    assert payload["status"] == "PASS"
    assert payload["kshudhita_pipeline_only"] is True
    assert payload["public_audio_urls_created"] is False
    assert payload["listen_now_cta_allowed"] is False
    assert payload["full_audiobook_public_allowed"] is False


def test_audiobook_release_gate_keeps_dracula_audio_disabled():
    payload = run_release_gate()

    assert payload["dracula_only_live"] is True
    assert payload["dracula_audio_disabled"] is True
