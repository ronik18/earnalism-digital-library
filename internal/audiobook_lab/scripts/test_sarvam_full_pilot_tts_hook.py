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
            "MAX_TTS_BUDGET_USD": None,
            "SARVAM_API_KEY": None,
        }
    ):
        preflight = tts_hook.sarvam_full_pilot_preflight(args(), "বাংলা পাঠ")
    blockers = " ".join(preflight["blockers"])
    assert_false(preflight["passes"], "preflight must block without explicit approval")
    assert_true("EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS" in blockers, blockers)
    assert_true("EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD" in blockers, blockers)
    assert_true("MAX_TTS_BUDGET_USD" in blockers, blockers)
    assert_true("SARVAM_API_KEY" in blockers, blockers)


def test_sarvam_full_pilot_is_limited_to_frozen_bengali_slug() -> None:
    with patched_env(
        {
            "EARNALISM_BENGALI_TTS_PROVIDER": "sarvam",
            "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
            "EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD": "25",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "MAX_TTS_BUDGET_USD": "25",
            "SARVAM_API_KEY": "redacted-test-key",
        }
    ):
        preflight = tts_hook.sarvam_full_pilot_preflight(args(slug="book-ac5a71075e"), "বাংলা পাঠ")
    blockers = " ".join(preflight["blockers"])
    assert_false(preflight["passes"], "non-pilot slug must not run through the frozen full-pilot hook")
    assert_true("limited to book-2b9853ec52" in blockers, blockers)


def test_sarvam_full_pilot_accepts_bn066_pooja_with_matching_representative_evidence() -> None:
    original_root = tts_hook.ROOT
    original_values = {
        "SARVAM_FULL_PILOT_SLUG": tts_hook.SARVAM_FULL_PILOT_SLUG,
        "SARVAM_FULL_PILOT_MODEL": tts_hook.SARVAM_FULL_PILOT_MODEL,
        "SARVAM_FULL_PILOT_VOICE": tts_hook.SARVAM_FULL_PILOT_VOICE,
        "SARVAM_FULL_PILOT_STYLE": tts_hook.SARVAM_FULL_PILOT_STYLE,
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "bengali_representative_audition_report.json").write_text(
            json.dumps(
                {
                    "pilot_candidate_selected": "bn-066",
                    "provider": "sarvam",
                    "model": "bulbul:v3",
                    "voice": "pooja",
                    "best_style_profile": "literary_warm_pacing",
                    "representative_passed_9_2": True,
                    "representative_score": 9.3,
                    "confidence": 0.95,
                    "fatal_flags_required": {
                        "robotic_texture_detected": False,
                        "mechanical_cadence_detected": False,
                        "list_reading_rhythm_detected": False,
                        "choppy_joins_detected": False,
                        "fallback_tts_detected": False,
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        try:
            tts_hook.ROOT = root
            tts_hook.SARVAM_FULL_PILOT_SLUG = "bn-066"
            tts_hook.SARVAM_FULL_PILOT_MODEL = "bulbul:v3"
            tts_hook.SARVAM_FULL_PILOT_VOICE = "pooja"
            tts_hook.SARVAM_FULL_PILOT_STYLE = "literary_warm_pacing"
            with patched_env(
                {
                    "EARNALISM_BENGALI_TTS_PROVIDER": "sarvam",
                    "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
                    "EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD": "25",
                    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
                    "MAX_TTS_BUDGET_USD": "25",
                    "SARVAM_API_KEY": "redacted-test-key",
                }
            ):
                preflight = tts_hook.sarvam_full_pilot_preflight(
                    args(slug="bn-066", language="ben"),
                    "বাংলা পাঠ",
                )
        finally:
            tts_hook.ROOT = original_root
            for name, value in original_values.items():
                setattr(tts_hook, name, value)
    assert_true(preflight["passes"], str(preflight))
    assert_true(preflight["representative_evidence"]["score"] == 9.3, str(preflight))


def test_sarvam_full_pilot_blocks_bn066_pooja_without_matching_representative_evidence() -> None:
    original_root = tts_hook.ROOT
    original_values = {
        "SARVAM_FULL_PILOT_SLUG": tts_hook.SARVAM_FULL_PILOT_SLUG,
        "SARVAM_FULL_PILOT_MODEL": tts_hook.SARVAM_FULL_PILOT_MODEL,
        "SARVAM_FULL_PILOT_VOICE": tts_hook.SARVAM_FULL_PILOT_VOICE,
        "SARVAM_FULL_PILOT_STYLE": tts_hook.SARVAM_FULL_PILOT_STYLE,
    }
    with tempfile.TemporaryDirectory() as tmp:
        try:
            tts_hook.ROOT = Path(tmp)
            tts_hook.SARVAM_FULL_PILOT_SLUG = "bn-066"
            tts_hook.SARVAM_FULL_PILOT_MODEL = "bulbul:v3"
            tts_hook.SARVAM_FULL_PILOT_VOICE = "pooja"
            tts_hook.SARVAM_FULL_PILOT_STYLE = "literary_warm_pacing"
            with patched_env(
                {
                    "EARNALISM_BENGALI_TTS_PROVIDER": "sarvam",
                    "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
                    "EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD": "25",
                    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
                    "MAX_TTS_BUDGET_USD": "25",
                    "SARVAM_API_KEY": "redacted-test-key",
                }
            ):
                preflight = tts_hook.sarvam_full_pilot_preflight(
                    args(slug="bn-066", language="ben"),
                    "বাংলা পাঠ",
                )
        finally:
            tts_hook.ROOT = original_root
            for name, value in original_values.items():
                setattr(tts_hook, name, value)
    blockers = " ".join(preflight["blockers"])
    assert_false(preflight["passes"], "missing representative evidence must block full-book TTS")
    assert_true("bn-066 + Sarvam bulbul:v3 + pooja + literary_warm_pacing" in blockers, blockers)


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


def test_bengali_tts_preparation_strips_trailing_source_year_without_rejecting_literary_words() -> None:
    manuscript = """গিন্নি

পৃথিবীর সমস্ত মাধ্যাকর্ষণশক্তি সবলে বালককে নীচের দিকে টানিতে লাগিল।

পৃথগন্ন ছিলেন তথাপি এই আশায় নবদ্বীপের মা নবদ্বীপকে কিছুতেই চাকরি করিতে দেন নাই।

১২৯৮?
"""
    prepared = tts_hook.prepare_bengali_tts_text(manuscript)
    assert_true("পৃথিবীর সমস্ত মাধ্যাকর্ষণশক্তি" in prepared, prepared)
    assert_true("পৃথগন্ন ছিলেন" in prepared, prepared)
    assert_false("১২৯৮" in prepared, prepared)
    assert_true(asr_sync_hook.frontmatter_absent(prepared), prepared)
    assert_false(asr_sync_hook.frontmatter_absent("১৮৯৫ (পৃ. ৬৫-৬৯)\n\nশুধু বিঘে দুই ছিল মোর ভুঁই।"), "page reference must block")


def test_bengali_tts_preparation_strips_midbook_page_reference_lines() -> None:
    manuscript = """অতি বিস্তৃত অরণ্য।

১৮৮৩ (পৃ. ১০২-১০৬)

কাল ৭৬ সাল ঈশ্বর কৃপায় শেষ হইল।
"""
    prepared = tts_hook.prepare_bengali_tts_text(manuscript)
    assert_true("অতি বিস্তৃত অরণ্য" in prepared, prepared)
    assert_true("কাল ৭৬ সাল" in prepared, prepared)
    assert_false("পৃ." in prepared, prepared)
    assert_false("১৮৮৩" in prepared, prepared)
    assert_false(tts_hook.prepared_text_source_terms(prepared), prepared)


def test_bengali_tts_integrity_recovery_only_allows_cleaned_page_number_artifacts() -> None:
    integrity = {
        "blocker_reasons": ["Body junk detected: page_number_line"],
        "chapter_order_match": True,
        "chapter_title_match": True,
        "toc_links_valid": True,
        "missing_chapters": [],
        "duplicate_chapters": [],
    }
    assert_true(
        tts_hook.bengali_tts_integrity_recoverable(integrity, "অতি বিস্তৃত অরণ্য।\n"),
        str(integrity),
    )
    assert_false(
        tts_hook.bengali_tts_integrity_recoverable(integrity, "১৮৮৩ (পৃ. ১০২-১০৬)\n"),
        "prepared text with page references must not be recoverable",
    )
    blocked_integrity = {**integrity, "blocker_reasons": ["Missing chapters: chapter-002"]}
    assert_false(
        tts_hook.bengali_tts_integrity_recoverable(blocked_integrity, "অতি বিস্তৃত অরণ্য।\n"),
        str(blocked_integrity),
    )


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


def test_sarvam_group_repair_regenerates_only_trailing_source_year_group() -> None:
    manuscript = """গিন্নি

পৃথিবীর সমস্ত মাধ্যাকর্ষণশক্তি সবলে বালককে নীচের দিকে টানিতে লাগিল।

শেষ পঙক্তি থাকে।
"""
    clean_group = "গিন্নি\n\nপৃথিবীর সমস্ত মাধ্যাকর্ষণশক্তি সবলে বালককে নীচের দিকে টানিতে লাগিল।"
    contaminated_final_group = "শেষ পঙক্তি থাকে।\n\n১২৯৮?"
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
    {"index": 0, "text": "CLEAN", "path": "/tmp/group0.wav", "sha256": "old0", "duration_seconds": 1.0},
    {"index": 1, "text": "CONTAMINATED_FINAL", "path": "/tmp/group1.wav", "sha256": "old1", "duration_seconds": 1.0}
  ]
}
""".replace("CLEAN", clean_group.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))
            .replace("CONTAMINATED_FINAL", contaminated_final_group.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")),
            encoding="utf-8",
        )
        plan = tts_hook.build_sarvam_group_repair_groups(args(), prepared, manifest_path)
    assert_true(plan["status"] == "PASS", str(plan))
    assert_true(plan["regenerated_group_ids"] == [1], str(plan))
    assert_true(plan["reused_group_ids"] == [0], str(plan))
    assert_false("১২৯৮" in plan["groups"][1]["text"], str(plan))


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


def test_fresh_generation_group_repair_state_is_not_needed() -> None:
    state = tts_hook.sarvam_group_repair_state(None)
    assert_true(state["status"] == "NOT_NEEDED", str(state))
    assert_false(state["repair_requested"], str(state))


def test_legacy_not_requested_is_accepted_only_with_complete_construction_evidence() -> None:
    accepted = asr_sync_hook.group_repair_semantics(
        {"status": "NOT_REQUESTED"},
        construction_evidence_pass=True,
    )
    incomplete = asr_sync_hook.group_repair_semantics(
        {"status": "NOT_REQUESTED"},
        construction_evidence_pass=False,
    )
    required = asr_sync_hook.group_repair_semantics(
        {"status": "NOT_REQUESTED", "repair_required": True},
        construction_evidence_pass=True,
    )
    assert_true(accepted["accepted"], str(accepted))
    assert_false(incomplete["accepted"], str(incomplete))
    assert_false(required["accepted"], str(required))


def main() -> int:
    tests = [
        test_sarvam_full_pilot_requires_explicit_approval_and_budget,
        test_sarvam_full_pilot_is_limited_to_frozen_bengali_slug,
        test_sarvam_full_pilot_accepts_bn066_pooja_with_matching_representative_evidence,
        test_sarvam_full_pilot_blocks_bn066_pooja_without_matching_representative_evidence,
        test_asr_listening_report_uses_requested_bengali_policy,
        test_metadata_hook_preserves_sarvam_provenance,
        test_metadata_hook_resets_partial_audiobook_state,
        test_bengali_tts_preparation_strips_source_frontmatter,
        test_sarvam_group_repair_regenerates_only_contaminated_groups,
        test_bengali_tts_preparation_strips_midbook_page_reference_lines,
        test_bengali_tts_integrity_recovery_only_allows_cleaned_page_number_artifacts,
        test_asr_transcription_retries_json_when_verbose_json_unsupported,
        test_bengali_tts_by_construction_blocks_frontmatter_manifest,
        test_bengali_tts_by_construction_writes_measured_group_sync,
        test_fresh_generation_group_repair_state_is_not_needed,
        test_legacy_not_requested_is_accepted_only_with_complete_construction_evidence,
    ]
    for test in tests:
        test()
    print(f"PASS {len(tests)} guarded Sarvam full-pilot TTS tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
