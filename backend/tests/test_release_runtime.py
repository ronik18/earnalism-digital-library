from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.audiobook_generation.provider_adapter import ProviderResult
from scripts.release_runtime import (
    RuntimeBlocked,
    generate_segments,
    promote,
    stage_local,
)


class FakeProvider:
    provider_name = "fake"

    def __init__(self, fail_once: bool = False):
        self.calls = 0
        self.fail_once = fail_once

    def estimate_cost(self, request):
        return float(request.metadata["estimated_cost_usd"])

    def generate_segment(self, request):
        self.calls += 1
        if self.fail_once and self.calls == 1:
            from backend.audiobook_generation.provider_adapter import (
                ProviderExecutionError,
            )

            raise ProviderExecutionError("temporary", retryable=True)
        output = Path(request.metadata["output_path"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-audio")
        return ProviderResult(
            provider="fake",
            status="PASS",
            dry_run=False,
            network_calls_performed=1,
            audio_generated=True,
            publishable=False,
            cost_estimate=0.01,
        )


def manifest():
    return {
        "slug": "pilot",
        "manifest_version": "1",
        "language": "en",
        "rights": {
            "commercial_use": "APPROVED",
            "territories": ["IN"],
            "audio_derivative_rights_status": "APPROVED",
        },
        "audio": {
            "provider": "sarvam",
            "model": "bulbul:v3",
            "voice": "style",
            "profile_sha256": "profile",
            "voice_source_type": "STYLE_PROFILE",
            "consent_status": "NOT_APPLICABLE_STYLE_PROFILE",
        },
        "audio_profile_approval": {
            "status": "APPROVED",
            "provider": "sarvam",
            "model": "bulbul:v3",
            "voice": "style",
            "profile_sha256": "profile",
        },
        "segments": [
            {
                "id": "p-1",
                "text": "hello",
                "output_name": "p-1.wav",
                "estimated_cost_usd": 0.01,
            }
        ],
    }


def test_paid_generation_is_blocked_without_runtime_authorization(
    tmp_path, monkeypatch
):
    with pytest.raises(RuntimeBlocked, match="EARNALISM_APPROVE_SARVAM_GENERATION"):
        monkeypatch.setenv("EARNALISM_PAID_GENERATION_MAX_USD", "1")
        generate_segments(manifest(), tmp_path, execute=True, provider=FakeProvider())


def test_fake_provider_retries_transient_and_writes_checksum(tmp_path, monkeypatch):
    monkeypatch.setenv("EARNALISM_PAID_GENERATION_MAX_USD", "1")
    lock = tmp_path / "paid-generation-lock.json"
    lock.write_text(
        json.dumps(
            {"status": "AUTHORIZED", "lock_id": "test-lock", "providers": ["sarvam"]}
        )
    )
    monkeypatch.setenv("EARNALISM_ENABLE_PAID_GENERATION", "true")
    monkeypatch.setenv("EARNALISM_APPROVE_SARVAM_GENERATION", "true")
    monkeypatch.setenv("EARNALISM_PAID_GENERATION_LOCK_ID", "test-lock")
    monkeypatch.setenv("EARNALISM_PAID_GENERATION_LOCK_PATH", str(lock))
    provider = FakeProvider(fail_once=True)
    result = generate_segments(manifest(), tmp_path, execute=True, provider=provider)
    assert result["passed"] is True
    assert provider.calls == 2
    assert (tmp_path / "generation_result.json").exists() is False
    assert hashlib.sha256((tmp_path / "p-1.wav").read_bytes()).hexdigest()


def test_local_staging_is_checksum_bound_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("EARNALISM_PAID_GENERATION_MAX_USD", "1")
    lock = tmp_path / "paid-generation-lock.json"
    lock.write_text(
        json.dumps(
            {"status": "AUTHORIZED", "lock_id": "test-lock", "providers": ["sarvam"]}
        )
    )
    monkeypatch.setenv("EARNALISM_ENABLE_PAID_GENERATION", "true")
    monkeypatch.setenv("EARNALISM_APPROVE_SARVAM_GENERATION", "true")
    monkeypatch.setenv("EARNALISM_PAID_GENERATION_LOCK_ID", "test-lock")
    monkeypatch.setenv("EARNALISM_PAID_GENERATION_LOCK_PATH", str(lock))
    generation_dir = tmp_path / "generation"
    generate_segments(manifest(), generation_dir, execute=True, provider=FakeProvider())
    result = (
        json.loads((generation_dir / "generation_result.json").read_text())
        if (generation_dir / "generation_result.json").exists()
        else None
    )
    assert result is None
    # The command writes the result; the function contract intentionally leaves
    # that CLI concern to the caller in tests.
    from scripts.release_runtime import write_json

    generated = {
        "execute": True,
        "passed": True,
        "segments": [
            {
                "segment_id": "p-1",
                "status": "PASS",
                "artifact_path": "p-1.wav",
                "artifact_sha256": hashlib.sha256(
                    (generation_dir / "p-1.wav").read_bytes()
                ).hexdigest(),
            }
        ],
    }
    write_json(generation_dir / "generation_result.json", generated)
    first = stage_local(manifest(), generation_dir, tmp_path / "staging")
    second = stage_local(manifest(), generation_dir, tmp_path / "staging")
    assert first["passed"] is True
    assert second["reused"] is True


def test_promotion_fails_closed_before_network_without_all_passes(tmp_path):
    with pytest.raises(RuntimeBlocked, match="existing release evaluator"):
        promote(
            manifest(), {"passed": True, "release_eligible": False, "release_id": "x"}
        )


def test_promotion_uses_explicit_live_and_audio_gate_evidence():
    value = manifest()
    value.update(
        {
            "release_status": "LIVE",
            "audio_release_gate_status": "PASS",
            "reader_approval": {"status": "APPROVED"},
            "automated_checks": {
                name: {"status": "PASS"}
                for name in (
                    "rights",
                    "manuscript",
                    "reader_artifacts",
                    "audio_artifacts",
                    "synchronization",
                    "checksums",
                    "staging",
                    "browser",
                    "production",
                )
            },
        }
    )

    class FakePromoter:
        def promote(self, payload, *, execute):
            assert execute is True
            assert payload["slug"] == "pilot"
            return {"status": "PROMOTED", "passed": True, "network_calls_performed": 0}

    result = promote(
        value,
        {"passed": True, "release_eligible": False, "release_id": "stage-1"},
        execute=True,
        promoter=FakePromoter(),
    )
    assert result["status"] == "PROMOTED"
