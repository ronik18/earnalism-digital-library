#!/usr/bin/env python3
"""Regression checks for guarded Sarvam Bengali full-pilot TTS."""

from __future__ import annotations

import os
import sys
import tempfile
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


HOOK_DIR = Path(__file__).resolve().parent / "factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

import asr_sync_hook  # noqa: E402
import metadata_hook  # noqa: E402
import tts_hook  # noqa: E402


@contextmanager
def patched_env(values: dict[str, str | None]):
    original = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def args(slug: str = "book-2b9853ec52", language: str = "ben") -> SimpleNamespace:
    return SimpleNamespace(slug=slug, language=language, title="দুই বিঘা জমি", author="রবীন্দ্রনাথ ঠাকুর")


def assert_true(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def assert_false(value: bool, message: str) -> None:
    if value:
        raise AssertionError(message)


def test_sarvam_full_pilot_requires_explicit_approval_and_budget() -> None:
    with patched_env(
        {
            "EARNALISM_BENGALI_TTS_PROVIDER": "sarvam",
            "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": None,
            "EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD": None,
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": None,
            "SARVAM_API_KEY": None,
        }
    ):
        preflight = tts_hook.sarvam_full_pilot_preflight(args(), "বাংলা পাঠ")
    blockers = " ".join(preflight["blockers"])
    assert_false(preflight["passes"], "preflight must block without explicit approval")
    assert_true("EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS" in blockers, blockers)
    assert_true("EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD" in blockers, blockers)
    assert_true("SARVAM_API_KEY" in blockers, blockers)


def test_sarvam_full_pilot_is_limited_to_frozen_bengali_slug() -> None:
    with patched_env(
        {
            "EARNALISM_BENGALI_TTS_PROVIDER": "sarvam",
            "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
            "EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD": "25",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "SARVAM_API_KEY": "redacted-test-key",
        }
    ):
        preflight = tts_hook.sarvam_full_pilot_preflight(args(slug="book-ac5a71075e"), "বাংলা পাঠ")
    blockers = " ".join(preflight["blockers"])
    assert_false(preflight["passes"], "non-pilot slug must not run through the frozen full-pilot hook")
    assert_true("limited to book-2b9853ec52" in blockers, blockers)


def test_asr_listening_report_uses_requested_bengali_policy() -> None:
    with patched_env({"EARNALISM_LISTENING_POLICY_VERSION": "bengali_audiobook_acceptance_v2_92"}):
        report = asr_sync_hook.base_listening_report(
            args(),
            Path("/tmp/nonexistent.mp3"),
            "abc123",
            [],
            status="BLOCKED",
            blockers=[],
            model_or_judge="test",
        )
    assert_true(report["release_policy"] == "bengali_audiobook_acceptance_v2_92", report)
    assert_true(report["listening_quality"]["release_policy"] == "bengali_audiobook_acceptance_v2_92", report)


def test_metadata_hook_preserves_sarvam_provenance() -> None:
    with patched_env(
        {
            "EARNALISM_BENGALI_TTS_PROVIDER": "sarvam",
            "EARNALISM_BENGALI_TTS_MODEL": "bulbul:v3",
            "EARNALISM_BENGALI_TTS_VOICE": "ratan",
            "EARNALISM_BENGALI_TTS_STYLE": "literary_warm_pacing",
        }
    ):
        provenance = metadata_hook.audiobook_provenance(
            {
                "provider": "sarvam",
                "model": "bulbul:v3",
                "voice": "ratan",
                "profile": "literary_warm_pacing",
            }
        )
    assert_true(provenance["provider"] == "sarvam", str(provenance))
    assert_true(provenance["model"] == "bulbul:v3", str(provenance))
    assert_true(provenance["voice"] == "ratan", str(provenance))
    assert_true(provenance["style"] == "literary_warm_pacing", str(provenance))


def test_metadata_hook_resets_partial_audiobook_state() -> None:
    assert_true(
        metadata_hook.audiobook_reset_required(
            {
                "audiobook_enabled": True,
                "generate_audiobook": False,
                "audiobook_assets": {"mp3": "https://example.test/audio.mp3"},
            }
        ),
        "partial audiobook state must be reset before the book-rights PUT",
    )
    assert_false(
        metadata_hook.audiobook_reset_required(
            {
                "audiobook_enabled": False,
                "generate_audiobook": False,
                "audiobook_assets": {},
            }
        ),
        "clean reader-only state should not force an audiobook reset",
    )


def test_bengali_tts_preparation_strips_source_frontmatter() -> None:
    manuscript = """রবীন্দ্রনাথ ঠাকুর

চিত্রা

১৮৯৫ (পৃ. ৬৫-৬৯)

দুই বিঘা জমি।

শুধু বিঘে দুই ছিল মোর ভুঁই।
"""
    prepared = tts_hook.prepare_bengali_tts_text(manuscript)
    assert_true(prepared.startswith("শুধু বিঘে দুই ছিল মোর ভুঁই।"), prepared)
    assert_false("দুই বিঘা জমি" in prepared, prepared)
    assert_false("চিত্রা" in prepared, prepared)
    assert_false("পৃ." in prepared, prepared)
    assert_false("রবীন্দ্রনাথ ঠাকুর" in prepared, prepared)


def test_sarvam_group_repair_regenerates_only_contaminated_groups() -> None:
    manuscript = """রবীন্দ্রনাথ ঠাকুর

চিত্রা

১৮৯৫ (পৃ. ৬৫-৬৯)

দুই বিঘা জমি।

শুধু বিঘে দুই ছিল মোর ভুঁই।

শেষ পঙক্তি থাকে।
"""
    contaminated_group = """রবীন্দ্রনাথ ঠাকুর

চিত্রা

১৮৯৫ (পৃ. ৬৫-৬৯)

দুই বিঘা জমি।

শুধু বিঘে দুই ছিল মোর ভুঁই।"""
    clean_group = "শেষ পঙক্তি থাকে।"
    prepared = tts_hook.prepare_bengali_tts_text(manuscript)
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = Path(tmp) / "tts_chunk_manifest.json"
        manifest_path.write_text(
            """
{
  "slug": "book-2b9853ec52",
  "provider": "sarvam",
  "model": "bulbul:v3",
  "voice": "ratan",
  "profile": "literary_warm_pacing",
  "chunks": [
    {"index": 0, "text": "CONTAMINATED", "path": "/tmp/group0.wav", "sha256": "old0", "duration_seconds": 1.0},
    {"index": 1, "text": "CLEAN", "path": "/tmp/group1.wav", "sha256": "old1", "duration_seconds": 1.0}
  ]
}
""".replace("CONTAMINATED", contaminated_group.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))
            .replace("CLEAN", clean_group.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")),
            encoding="utf-8",
        )
        plan = tts_hook.build_sarvam_group_repair_groups(args(), prepared, manifest_path)
    assert_true(plan["status"] == "PASS", str(plan))
    assert_true(plan["regenerated_group_ids"] == [0], str(plan))
    assert_true(plan["reused_group_ids"] == [1], str(plan))
    assert_true(plan["groups"][0]["text"].startswith("শুধু বিঘে দুই ছিল মোর ভুঁই।"), str(plan))
    assert_false("রবীন্দ্রনাথ ঠাকুর" in plan["groups"][0]["text"], str(plan))


class FakeTranscriptions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("response_format") == "verbose_json":
            raise Exception("response_format 'verbose_json' is not compatible with model")
        return {"text": "বাংলা পাঠ"}


class FakeAudio:
    def __init__(self) -> None:
        self.transcriptions = FakeTranscriptions()


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.audio = FakeAudio()


def test_asr_transcription_retries_json_when_verbose_json_unsupported() -> None:
    client = FakeOpenAIClient()
    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        tmp.write(b"not-real-audio-for-unit-test")
        tmp.flush()
        payload = asr_sync_hook.transcribe_file(client, Path(tmp.name), args())
    assert_true(payload["text"] == "বাংলা পাঠ", payload)
    formats = [call.get("response_format") for call in client.audio.transcriptions.calls]
    assert_true(formats == ["verbose_json", "json"], str(formats))


def test_bengali_tts_by_construction_blocks_frontmatter_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        final_audio = run_dir / "final.mp3"
        chunk_audio = run_dir / "group0.wav"
        final_audio.write_bytes(b"final-audio")
        chunk_audio.write_bytes(b"chunk-audio")
        contaminated = "রবীন্দ্রনাথ ঠাকুর\n\nচিত্রা\n\n১৮৯৫ (পৃ. ৬৫-৬৯)\n\nশুধু বিঘে দুই ছিল মোর ভুঁই।"
        manifest = {
            "final_audio_hash": asr_sync_hook.sha256_file(final_audio),
            "tts_source_sanitization": {
                "frontmatter_stripped": False,
                "forbidden_source_terms_in_prepared_text": ["পৃ."],
            },
            "chunks": [
                {
                    "index": 0,
                    "text": contaminated,
                    "path": str(chunk_audio),
                    "sha256": asr_sync_hook.sha256_file(chunk_audio),
                    "duration_seconds": 1.0,
                }
            ],
        }
        report = asr_sync_hook.bengali_tts_by_construction_verification(
            args(),
            run_dir,
            "শুধু বিঘে দুই ছিল মোর ভুঁই।",
            final_audio,
            manifest,
            {"metrics": {"fallback_tts_used": False, "local_audio_reused": False, "stale_audio_reused": False}},
        )
    assert_false(report["tts_by_construction_verified"], str(report))
    assert_true("frontmatter" in " ".join(report["blockers"]).lower(), str(report))


def test_bengali_tts_by_construction_writes_measured_group_sync() -> None:
    manuscript = "শুধু বিঘে দুই ছিল মোর ভুঁই।\n\nশেষ পঙক্তি থাকে।"
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        final_audio = run_dir / "final.mp3"
        group0 = run_dir / "group0.wav"
        group1 = run_dir / "group1.wav"
        final_audio.write_bytes(b"final-audio")
        group0.write_bytes(b"group0-audio")
        group1.write_bytes(b"group1-audio")
        chunks = [
            {
                "index": 0,
                "text": "শুধু বিঘে দুই ছিল মোর ভুঁই।",
                "path": str(group0),
                "sha256": asr_sync_hook.sha256_file(group0),
                "duration_seconds": 2.0,
            },
            {
                "index": 1,
                "text": "শেষ পঙক্তি থাকে।",
                "path": str(group1),
                "sha256": asr_sync_hook.sha256_file(group1),
                "duration_seconds": 1.5,
            },
        ]
        joined = "\n\n".join(chunk["text"] for chunk in chunks)
        manifest = {
            "final_audio_hash": asr_sync_hook.sha256_file(final_audio),
            "tts_source_sanitization": {"frontmatter_stripped": True, "forbidden_source_terms_in_prepared_text": []},
            "group_repair": {"status": "PASS", "repaired_group_sequence_hash": asr_sync_hook.sha256_text(joined)},
            "chunks": chunks,
        }
        report = asr_sync_hook.bengali_tts_by_construction_verification(
            args(),
            run_dir,
            manuscript,
            final_audio,
            manifest,
            {"metrics": {"fallback_tts_used": False, "local_audio_reused": False, "stale_audio_reused": False}},
        )
        assert_true(report["tts_by_construction_verified"], str(report))
        sidecars = asr_sync_hook.write_measured_group_sidecars(
            args(),
            run_dir,
            manuscript,
            final_audio,
            manifest,
            report,
            {"score": 1.0},
        )
        meta = json.loads(Path(sidecars["meta"]).read_text(encoding="utf-8"))
        timestamps = json.loads(Path(sidecars["timestamps"]).read_text(encoding="utf-8"))
    assert_true(meta["sync_release_tier"] == "PARAGRAPH_OR_STANZA_SYNC_PREMIUM", meta)
    assert_true(meta["auto_estimated_sync"] is False, meta)
    assert_true(meta["tts_by_construction_verified"] is True, meta)
    assert_true(timestamps["cue_coverage_percent"] == 100.0, timestamps)


def main() -> int:
    tests = [
        test_sarvam_full_pilot_requires_explicit_approval_and_budget,
        test_sarvam_full_pilot_is_limited_to_frozen_bengali_slug,
        test_asr_listening_report_uses_requested_bengali_policy,
        test_metadata_hook_preserves_sarvam_provenance,
        test_metadata_hook_resets_partial_audiobook_state,
        test_bengali_tts_preparation_strips_source_frontmatter,
        test_sarvam_group_repair_regenerates_only_contaminated_groups,
        test_asr_transcription_retries_json_when_verbose_json_unsupported,
        test_bengali_tts_by_construction_blocks_frontmatter_manifest,
        test_bengali_tts_by_construction_writes_measured_group_sync,
    ]
    for test in tests:
        test()
    print(f"PASS {len(tests)} guarded Sarvam full-pilot TTS tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
