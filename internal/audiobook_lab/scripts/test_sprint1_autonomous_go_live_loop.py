import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest


MODULE_PATH = Path(__file__).with_name("sprint1_autonomous_go_live_loop.py")
SPEC = importlib.util.spec_from_file_location("sprint1_autonomous_go_live_loop", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(slug, language="English", **overrides):
    payload = {
        "slug": slug,
        "title": slug,
        "language": language,
        "publicly_rendered_book": "Yes",
        "publicly_available_audiobook": "No",
        "public_audio_status": "AUDIO_HIDDEN",
        "final_status": "SPRINT_TARGET_INCOMPLETE",
        "sprint1_audio_target": True,
        "rights_status": "PASS",
        "sanitation_status": "PASS",
        "estimated_incremental_cost_usd": 0.2,
        "exact_blocker": "TITLE_AUDIO_RELEASE_GATES_INCOMPLETE",
    }
    payload.update(overrides)
    return payload


class AutonomousGoLiveLoopTests(unittest.TestCase):
    def setUp(self):
        self.runtime = {
            "bengali_campaign_paid_gates": {"ready": False, "missing": ["gate"]},
            "providers": {"google": True, "openai_qa": True, "sarvam": True},
        }

    def test_fixed_caps_are_child_bound_and_secrets_are_not_exposed(self):
        snapshot = MODULE.runtime_snapshot({"OPENAI_API_KEY": "secret"})
        self.assertEqual(snapshot["fixed_caps"]["SPRINT1_TOTAL_AUDIO_BUDGET_USD"], "175")
        self.assertEqual(snapshot["credentials"]["OPENAI_API_KEY"], "SET")
        self.assertNotIn('"OPENAI_API_KEY": "secret"', json.dumps(snapshot))
        self.assertFalse(snapshot["secrets_printed"])

    def test_google_adc_probe_is_bounded_and_discards_all_output(self):
        observed = {}

        def runner(command, **kwargs):
            observed["command"] = command
            observed["kwargs"] = kwargs
            return SimpleNamespace(returncode=1)

        result = MODULE.google_adc_probe(
            {"PATH": "/usr/bin:/bin"}, timeout_seconds=1.25, runner=runner
        )
        self.assertEqual(result["status"], "GOOGLE_ADC_REAUTH_REQUIRED")
        self.assertFalse(result["ready"])
        self.assertEqual(observed["kwargs"]["timeout"], 1.25)
        self.assertEqual(observed["kwargs"]["stdin"], subprocess.DEVNULL)
        self.assertEqual(observed["kwargs"]["stdout"], subprocess.DEVNULL)
        self.assertEqual(observed["kwargs"]["stderr"], subprocess.DEVNULL)
        self.assertNotIn("stdout", result)
        self.assertNotIn("stderr", result)
        self.assertNotIn("access_token", result)
        self.assertFalse(result["token_output_exposed"])

    def test_google_credential_file_alone_never_marks_provider_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "application_default_credentials.json"
            credential.write_text("{}", encoding="utf-8")

            def failed_probe(_env):
                return {
                    "ready": False,
                    "outcome": "NONZERO_EXIT",
                    "timeout_seconds": 1.0,
                    "access_token": "must-not-leak",
                }

            snapshot = MODULE.runtime_snapshot(
                {
                    "GOOGLE_APPLICATION_CREDENTIALS": str(credential),
                    "GOOGLE_CLOUD_PROJECT": "earnalism-test",
                },
                adc_probe=failed_probe,
            )
            self.assertEqual(
                snapshot["credentials"]["GOOGLE_APPLICATION_CREDENTIALS"],
                "SET_AND_READABLE",
            )
            self.assertFalse(snapshot["providers"]["google"])
            self.assertEqual(
                snapshot["provider_readiness"]["google"]["blocker"],
                "GOOGLE_ADC_REAUTH_REQUIRED",
            )
            self.assertNotIn("must-not-leak", json.dumps(snapshot))

    def test_repository_lock_requires_active_empty_fail_closed_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paid_tts.lock"
            path.write_text(
                json.dumps(
                    {
                        "status": "active",
                        "current_holder": "none",
                        "allowed_next_holders": [],
                        "allowed_slugs": ["bn-066"],
                    }
                ),
                encoding="utf-8",
            )
            snapshot = MODULE.lock_snapshot(path)
            self.assertTrue(snapshot["available"])
            self.assertEqual(snapshot["allowed_slugs"], ["bn-066"])

    def test_held_lock_is_not_available(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paid_tts.lock"
            path.write_text(
                json.dumps(
                    {"status": "active", "current_holder": "worker", "allowed_next_holders": []}
                ),
                encoding="utf-8",
            )
            self.assertFalse(MODULE.lock_snapshot(path)["available"])

    def test_failure_registry_deduplicates_attempt_fingerprints(self):
        with tempfile.TemporaryDirectory() as directory:
            packets = Path(directory)
            packet = packets / "story"
            packet.mkdir()
            attempt = {
                "provider": "google",
                "voice": "studio-c",
                "failed": True,
                "minimum_observed_score": 8.4,
            }
            (packet / "metadata.json").write_text(
                json.dumps(
                    {
                        "prior_provider_evidence": {
                            "provider_attempts": [attempt, attempt],
                            "failed_attempts": [],
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry = MODULE.build_failure_registry([row("story")], packets)
            title = registry["titles"]["story"]
            self.assertEqual(len(title["attempts"]), 1)
            self.assertEqual(title["blocked_attempt_fingerprints"], [])
            self.assertEqual(len(title["blocked_registry_identities"]), 1)
            self.assertNotIn("attempt_fingerprint", title["attempts"][0])
            self.assertFalse(
                title["attempts"][0]["fingerprint_provenance"]["synthetic"]
            )
            self.assertEqual(
                title["attempts"][0]["fingerprint_provenance"]["source"], "none"
            )

    def test_d19_decision_history_marks_external_audio_exhaustion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets = root / "publication" / "human_narration_packets"
            title_runs = root / "publication" / "title_runs"
            packets.mkdir(parents=True)
            title_runs.mkdir()
            (title_runs / "book-d19e96859f_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "book-d19e96859f",
                        "title": "Canonical D19",
                        "classification": "ASR_SOURCE_MISMATCH",
                        "status": "FULL_TTS_PASS_RELEASE_QA_FAILED_AUDIO_HIDDEN",
                        "provider": "sarvam",
                        "model": "bulbul:v3",
                        "voice": "pooja",
                        "style": "dialogue_human_touch",
                        "source": {"prepared_text_sha256": "a" * 64},
                        "exact_blocker": "CANONICAL_D19_BLOCKER",
                    }
                ),
                encoding="utf-8",
            )
            history = {
                "titles": {
                    "book-d19e96859f": {
                        "latest_decision": "ASR_SOURCE_MISMATCH_HUMAN_NARRATION_REQUIRED",
                        "selected_provider": "sarvam",
                        "selected_model": "bulbul:v3",
                        "selected_voice": "pooja",
                        "selected_style": "dialogue_human_touch",
                        "prepared_text_sha256": "a" * 64,
                    }
                }
            }
            title = MODULE.build_failure_registry(
                [row("book-d19e96859f", language="Bengali")],
                packets,
                title_runs_root=title_runs,
                title_decision_history=history,
                budget_ledger={},
                asset_root=root,
            )["titles"]["book-d19e96859f"]
            self.assertEqual(title["classification"], "ASR_SOURCE_MISMATCH")
            self.assertEqual(title["exact_blocker"], "CANONICAL_D19_BLOCKER")
            self.assertTrue(title["automated_tts_exhausted"])
            self.assertTrue(title["exhaustion_evidence"]["external_audio_terminal_state"])
            self.assertEqual(title["attempts"][0]["provider"], "sarvam")
            self.assertEqual(title["attempts"][0]["prepared_text_sha256"], "a" * 64)
            self.assertEqual(
                title["attempts"][0]["style_profile"], "dialogue_human_touch"
            )

    def test_legacy_synthetic_registry_fingerprint_is_not_reingested(self):
        with tempfile.TemporaryDirectory() as directory:
            packets = Path(directory)
            previous = {
                "schema_version": 1,
                "titles": {
                    "story": {
                        "attempts": [
                            {
                                "provider": "google",
                                "voice": "studio-c",
                                "attempt_fingerprint": "a" * 64,
                                "failed": True,
                            }
                        ]
                    }
                },
            }
            title = MODULE.build_failure_registry(
                [row("story")], packets, previous=previous
            )["titles"]["story"]
            self.assertEqual(title["attempts"], [])
            self.assertEqual(title["blocked_attempt_fingerprints"], [])

    def test_fresh_canonical_evidence_discards_stale_registry_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets = root / "publication" / "human_narration_packets"
            title_runs = root / "publication" / "title_runs"
            packets.mkdir(parents=True)
            title_runs.mkdir()
            (title_runs / "story_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "story",
                        "classification": (
                            "HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED"
                        ),
                        "provider_attempts": [],
                    }
                ),
                encoding="utf-8",
            )
            previous = {
                "schema_version": 2,
                "titles": {
                    "story": {
                        "attempts": [
                            {
                                "provider": "unknown",
                                "attempt_fingerprint": "a" * 64,
                                "fingerprint_is_evidence_native": True,
                                "evidence_kind": "prior_registry",
                                "evidence_kinds": ["packet_metadata"],
                                "failed": True,
                            }
                        ]
                    }
                },
            }
            title = MODULE.build_failure_registry(
                [row("story")],
                packets,
                previous=previous,
                title_runs_root=title_runs,
                title_decision_history={},
                budget_ledger={},
                asset_root=root,
            )["titles"]["story"]
            self.assertEqual(title["attempts"], [])

    def test_empty_attempt_external_audio_title_is_exhausted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets = root / "publication" / "human_narration_packets"
            title_runs = root / "publication" / "title_runs"
            packets.mkdir(parents=True)
            title_runs.mkdir()
            (title_runs / "story_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "story",
                        "release_gate_state": (
                            "HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED_FAIL_CLOSED"
                        ),
                        "provider_attempts": [],
                        "exact_blocker": "CANONICAL_EMPTY_ATTEMPT_BLOCKER",
                    }
                ),
                encoding="utf-8",
            )
            title = MODULE.build_failure_registry(
                [row("story")],
                packets,
                title_runs_root=title_runs,
                title_decision_history={},
                budget_ledger={},
                asset_root=root,
            )["titles"]["story"]
            self.assertEqual(title["attempts"], [])
            self.assertTrue(title["automated_tts_exhausted"])
            self.assertEqual(title["distinct_failed_family_count"], 0)

    def test_tell_tale_canonical_labels_override_conflicting_budget_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets = root / "publication" / "human_narration_packets"
            title_runs = root / "publication" / "title_runs"
            packets.mkdir(parents=True)
            title_runs.mkdir()
            first = "1" * 64
            second = "2" * 64
            (title_runs / "the-tell-tale-heart_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "the-tell-tale-heart",
                        "title": "The Tell-Tale Heart",
                        "classification": (
                            "HUMAN_NARRATION_OR_LICENSED_ALTERNATE_PROVIDER_REQUIRED"
                        ),
                        "release_gate_state": (
                            "HUMAN_NARRATION_OR_LICENSED_ALTERNATE_PROVIDER_REQUIRED"
                        ),
                        "exact_blocker": "CANONICAL_TELL_TALE_BLOCKER",
                        "provider_attempts": [
                            {
                                "provider": "google",
                                "voice": "en-GB-Studio-C",
                                "scope": "contextual_representative_audition",
                                "attempt_fingerprint": first,
                                "status": "BLOCKED_LISTENING_QA",
                            },
                            {
                                "provider": "google",
                                "voice": "en-GB-Studio-C",
                                "scope": "final_slow_contextual_representative_audition",
                                "attempt_fingerprint": second,
                                "status": "BLOCKED_LISTENING_QA",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            budget = {
                "checkpoint_chain_tail": [
                    {
                        "stage": "tell_tale_studio_c_slow_contextual_private_tts_audition",
                        "result": "AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED",
                        "evidence": (
                            "internal/the-tell-tale-heart/audition/"
                            f"{first[:16]}/audition_manifest.json"
                        ),
                    },
                    {
                        "stage": "tell_tale_studio_c_contextual_private_tts_audition",
                        "result": "AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED",
                        "evidence": (
                            "internal/the-tell-tale-heart/audition/"
                            f"{second[:16]}/audition_manifest.json"
                        ),
                    },
                ]
            }
            title = MODULE.build_failure_registry(
                [row("the-tell-tale-heart", exact_blocker="CONFLICTING_MATRIX_BLOCKER")],
                packets,
                title_runs_root=title_runs,
                title_decision_history={},
                budget_ledger=budget,
                asset_root=root,
            )["titles"]["the-tell-tale-heart"]
            attempts = {item["attempt_fingerprint"]: item for item in title["attempts"]}
            self.assertEqual(
                title["classification"],
                "HUMAN_NARRATION_OR_LICENSED_ALTERNATE_PROVIDER_REQUIRED",
            )
            self.assertEqual(title["exact_blocker"], "CANONICAL_TELL_TALE_BLOCKER")
            self.assertEqual(attempts[first]["scope"], "contextual_representative_audition")
            self.assertEqual(attempts[first]["provider"], "google")
            self.assertEqual(attempts[first]["voice"], "en-GB-Studio-C")
            self.assertEqual(
                attempts[first]["fingerprint_provenance"]["source"],
                "canonical_title_release_evidence",
            )
            self.assertEqual(
                attempts[second]["scope"],
                "final_slow_contextual_representative_audition",
            )

    def test_attempt_identity_preserves_style_text_source_prep_and_postprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets = root / "publication" / "human_narration_packets"
            title_runs = root / "publication" / "title_runs"
            packets.mkdir(parents=True)
            title_runs.mkdir()
            (title_runs / "story_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "story",
                        "provider_attempts": [
                            {
                                "provider": "sarvam",
                                "model": "bulbul:v3",
                                "voice": "pooja",
                                "style_profile": "literary_warm_pacing",
                                "text_sha256": "1" * 64,
                                "source_sha256": "2" * 64,
                                "prep_identity": "punctuation-normalizer-v1",
                                "prep_variant": "punctuation_normalized",
                                "postprocess_identity": "breath-trimmer-v2",
                                "postprocess_variant": "breath_trim_v2",
                                "status": "BLOCKED_LISTENING_QA",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            attempt = MODULE.build_failure_registry(
                [row("story")],
                packets,
                title_runs_root=title_runs,
                title_decision_history={},
                budget_ledger={},
                asset_root=root,
            )["titles"]["story"]["attempts"][0]
            self.assertEqual(attempt["style_profile"], "literary_warm_pacing")
            self.assertEqual(attempt["text_sha256"], "1" * 64)
            self.assertEqual(attempt["source_sha256"], "2" * 64)
            self.assertEqual(attempt["prep_identity"], "punctuation-normalizer-v1")
            self.assertEqual(attempt["text_prep_variant"], "punctuation_normalized")
            self.assertEqual(attempt["postprocess_identity"], "breath-trimmer-v2")
            self.assertEqual(attempt["postprocess_variant"], "breath_trim_v2")

    def test_fingerprint_type_and_provenance_are_not_synthesized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets = root / "publication" / "human_narration_packets"
            title_runs = root / "publication" / "title_runs"
            packets.mkdir(parents=True)
            title_runs.mkdir()
            full = "a" * 64
            prefix = "b" * 16
            (title_runs / "story_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "story",
                        "provider_attempts": [
                            {
                                "provider": "google",
                                "voice": "full",
                                "attempt_fingerprint": full,
                                "status": "BLOCKED",
                            },
                            {
                                "provider": "google",
                                "voice": "prefix",
                                "fingerprint": prefix,
                                "status": "BLOCKED",
                            },
                            {
                                "provider": "google",
                                "voice": "no-native-fingerprint",
                                "status": "BLOCKED",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            title = MODULE.build_failure_registry(
                [row("story")],
                packets,
                title_runs_root=title_runs,
                title_decision_history={},
                budget_ledger={},
                asset_root=root,
            )["titles"]["story"]
            attempts = {item["voice"]: item for item in title["attempts"]}
            self.assertEqual(attempts["full"]["fingerprint_type"], "full_sha256")
            self.assertEqual(attempts["prefix"]["fingerprint_type"], "prefix16")
            self.assertTrue(attempts["full"]["fingerprint_is_evidence_native"])
            self.assertTrue(attempts["prefix"]["fingerprint_is_evidence_native"])
            self.assertFalse(attempts["full"]["fingerprint_is_provider_native"])
            self.assertFalse(attempts["prefix"]["fingerprint_is_provider_native"])
            self.assertEqual(
                attempts["full"]["fingerprint_provenance"]["source"],
                "canonical_title_release_evidence",
            )
            self.assertNotIn("attempt_fingerprint", attempts["no-native-fingerprint"])
            self.assertEqual(attempts["no-native-fingerprint"]["fingerprint_type"], "none")
            self.assertFalse(
                attempts["no-native-fingerprint"]["fingerprint_is_provider_native"]
            )
            self.assertEqual(
                attempts["no-native-fingerprint"]["fingerprint_provenance"]["source"],
                "none",
            )
            self.assertFalse(
                attempts["no-native-fingerprint"]["fingerprint_provenance"]["synthetic"]
            )
            self.assertEqual(
                attempts["no-native-fingerprint"]["registry_identity_provenance"],
                "DERIVED_FOR_REGISTRY_DEDUPLICATION_NOT_PROVIDER_NATIVE",
            )
            self.assertEqual(title["blocked_attempt_fingerprints"], [full, prefix])

    def test_prior_registry_fingerprint_is_only_a_non_native_matching_hint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets = root / "publication" / "human_narration_packets"
            title_runs = root / "publication" / "title_runs"
            packets.mkdir(parents=True)
            title_runs.mkdir()
            fingerprint = "c" * 64
            (title_runs / "story_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "story",
                        "provider_attempts": [
                            {
                                "provider": "google",
                                "voice": "canonical-voice",
                                "attempt_fingerprint": fingerprint,
                                "status": "BLOCKED",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            previous = {
                "titles": {
                    "story": {
                        "attempts": [
                            {
                                "provider": "google",
                                "voice": "stale-voice",
                                "attempt_fingerprint": fingerprint,
                                "fingerprint_is_provider_native": True,
                                "status": "BLOCKED",
                            }
                        ]
                    }
                }
            }
            attempt = MODULE.build_failure_registry(
                [row("story")],
                packets,
                previous,
                title_runs_root=title_runs,
                title_decision_history={},
                budget_ledger={},
                asset_root=root,
            )["titles"]["story"]["attempts"][0]
            self.assertEqual(attempt["voice"], "canonical-voice")
            self.assertEqual(attempt["fingerprint_type"], "full_sha256")
            self.assertTrue(attempt["fingerprint_is_evidence_native"])
            self.assertFalse(attempt["fingerprint_is_provider_native"])
            self.assertEqual(
                attempt["fingerprint_provenance"]["source"],
                "canonical_title_release_evidence",
            )
            self.assertNotIn("reported_non_native_fingerprint", attempt)

    def test_approved_history_keeps_failed_forensics_separate_from_passing_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets = root / "publication" / "human_narration_packets"
            title_runs = root / "publication" / "title_runs"
            packets.mkdir(parents=True)
            title_runs.mkdir()
            (title_runs / "book-2b9853ec52_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "book-2b9853ec52",
                        "release_gate_state": "APPROVED_EXISTING_PUBLIC_AUDIO",
                        "exact_blocker": "NONE",
                    }
                ),
                encoding="utf-8",
            )
            history = {
                "titles": {
                    "book-2b9853ec52": {
                        "latest_decision": "BENGALI_AUDIOBOOK_LIVE_STABILIZATION_SOURCE_PATCH_READY",
                        "bengali_audiobook_release_gate": "APPROVED_AND_LIVE",
                        "provider": "sarvam",
                        "model": "bulbul:v3",
                        "voice": "ratan",
                        "style": "literary_warm_pacing",
                        "listening_score": 9.4,
                        "listening_confidence": 0.95,
                        "bengali_audiobook_forensics": {
                            "representative_score": 9.3,
                            "asr_score": 7.0199,
                            "tts_by_construction_verified": False,
                        },
                        "bengali_audiobook_repair": {
                            "tts_input_clean": True,
                            "tts_by_construction_verified_for_planned_sequence": True,
                        },
                    }
                }
            }
            title = MODULE.build_failure_registry(
                [
                    row(
                        "book-2b9853ec52",
                        language="Bengali",
                        publicly_available_audiobook="Yes",
                        exact_blocker="NONE",
                    )
                ],
                packets,
                title_runs_root=title_runs,
                title_decision_history=history,
                budget_ledger={},
                asset_root=root,
            )["titles"]["book-2b9853ec52"]
            failed = [item for item in title["attempts"] if item["failed"]]
            passing = [item for item in title["attempts"] if not item["failed"]]
            self.assertEqual(len(failed), 1)
            self.assertEqual(len(passing), 1)
            self.assertNotEqual(
                failed[0]["registry_identity_sha256"],
                passing[0]["registry_identity_sha256"],
            )
            self.assertFalse(title["automated_tts_exhausted"])
            self.assertNotIn(
                passing[0]["registry_identity_sha256"],
                title["blocked_registry_identities"],
            )

    def test_approved_title_retains_failed_history_without_exhaustion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets = root / "publication" / "human_narration_packets"
            title_runs = root / "publication" / "title_runs"
            packets.mkdir(parents=True)
            title_runs.mkdir()
            failed_fingerprint = "f" * 64
            (title_runs / "story_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "story",
                        "title": "Approved Story",
                        "final_status": "YES_PLUS_YES_PRODUCTION_VALIDATED",
                        "can_publish_audio_now": True,
                        "provider": "google",
                        "model": "google-cloud-texttospeech",
                        "voice": "en-GB-Studio-C",
                        "text_prep_variant": "source_preserving_ssml_88_percent",
                    }
                ),
                encoding="utf-8",
            )
            (title_runs / "story_failed_baseline.json").write_text(
                json.dumps(
                    {
                        "slug": "story",
                        "status": "AUDITION_REPAIR_REQUIRED",
                        "provider": "google",
                        "model": "google-cloud-texttospeech",
                        "voice": "en-GB-Studio-C",
                        "text_prep_variant": "baseline",
                        "attempt_fingerprint": failed_fingerprint,
                    }
                ),
                encoding="utf-8",
            )
            title = MODULE.build_failure_registry(
                [
                    row(
                        "story",
                        publicly_available_audiobook="Yes",
                        exact_blocker="NONE",
                        final_status=(
                            "Yes, publicly rendered book + Yes, publicly available audiobook"
                        ),
                    )
                ],
                packets,
                title_runs_root=title_runs,
                title_decision_history={},
                budget_ledger={},
                asset_root=root,
            )["titles"]["story"]
            self.assertIn(failed_fingerprint, title["blocked_attempt_fingerprints"])
            self.assertTrue(any(not item["failed"] for item in title["attempts"]))
            self.assertFalse(title["automated_tts_exhausted"])
            self.assertTrue(title["exhaustion_evidence"]["approved_release_override"])

    def test_two_failed_families_exhaust_automated_tts(self):
        with tempfile.TemporaryDirectory() as directory:
            packets = Path(directory)
            packet = packets / "story"
            packet.mkdir()
            (packet / "metadata.json").write_text(
                json.dumps(
                    {
                        "prior_provider_evidence": {
                            "provider_attempts": [
                                {"provider": "google", "voice": "studio-c", "failed": True},
                                {"provider": "google", "voice": "chirp-achird", "failed": True},
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            title = MODULE.build_failure_registry([row("story")], packets)["titles"]["story"]
            self.assertEqual(title["distinct_failed_family_count"], 2)
            self.assertTrue(title["automated_tts_exhausted"])

    def test_intake_layout_detects_received_audio_without_approving_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = root / "packets" / "story"
            packet.mkdir(parents=True)
            for name in MODULE.REQUIRED_PACKET_FILES:
                (packet / name).write_text("{}" if name.endswith(".json") else "x", encoding="utf-8")
            received = root / "intake" / "story" / "received_audio"
            received.mkdir(parents=True)
            (received / "story.wav").write_bytes(b"candidate")
            board = MODULE.build_intake_board(
                [row("story", final_status="HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED")],
                root / "packets",
                root / "intake",
                create_layout=True,
            )
            title = board["titles"]["story"]
            self.assertEqual(title["status"], "RECEIVED_AUDIO_PREFLIGHT_REQUIRED")
            self.assertEqual(title["received_file_count"], 1)
            self.assertFalse(title["public_audio_allowed_now"])

    def test_packet_integrity_rejects_empty_or_unbound_files(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory)
            for name in MODULE.REQUIRED_PACKET_FILES:
                (packet / name).write_text("x", encoding="utf-8")
            self.assertFalse(MODULE.packet_is_complete(packet))

    def test_human_track_waits_for_external_source_bound_audio(self):
        decision = MODULE.title_decision(
            row("story", final_status="HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED"),
            {"automated_tts_exhausted": True},
            {"received_file_count": 0, "next_command": "import", "packet_path": "packet"},
            self.runtime,
            Path("/repo"),
            0,
        )
        self.assertEqual(
            decision["state"], "WAITING_EXTERNAL_SOURCE_BOUND_NARRATION_OR_LICENSED_AUDIO"
        )
        self.assertFalse(decision["public_audio_allowed_now"])

    def test_existing_source_bound_packet_prevents_further_tts_spend(self):
        decision = MODULE.title_decision(
            row("story"),
            {"packet_exists": True, "automated_tts_exhausted": False},
            {"received_file_count": 0, "next_command": "import", "packet_path": "packet"},
            self.runtime,
            Path("/repo"),
            0,
        )
        self.assertEqual(
            decision["state"], "WAITING_EXTERNAL_SOURCE_BOUND_NARRATION_OR_LICENSED_AUDIO"
        )

    def test_received_audio_ranks_before_every_other_action(self):
        decision = MODULE.title_decision(
            row("story", final_status="HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED"),
            {"automated_tts_exhausted": True},
            {"received_file_count": 1, "status": "RECEIVED_AUDIO_PREFLIGHT_REQUIRED", "next_command": "validate"},
            self.runtime,
            Path("/repo"),
            0,
        )
        self.assertEqual(decision["priority"], 0)
        self.assertEqual(decision["state"], "RECEIVED_AUDIO_PREFLIGHT_REQUIRED")

    def test_owner_document_title_never_enters_paid_queue(self):
        decision = MODULE.title_decision(
            row("pather-panchali", language="Bengali"),
            {},
            None,
            self.runtime,
            Path("/repo"),
            0,
        )
        self.assertEqual(decision["state"], "OWNER_DOCUMENT_REQUIRED")
        self.assertFalse(decision["release_gate_mutation_allowed"])

    def test_reconciled_nonpaid_preflight_overrides_stale_matrix_states(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "sprint1_v3_nonpaid_preflight_results.json"
            expected = {
                "jekyll-and-hyde": (
                    "READY_FOR_REPRESENTATIVE_AUDITION_GOOGLE_ADC_REAUTH_REQUIRED"
                ),
                "radharani": (
                    "READY_FOR_REPRESENTATIVE_AUDITION_CAMPAIGN_SCALE_GATE_BLOCKED"
                ),
                "bn-066": (
                    "PRIVATE_ARTIFACT_TRACKING_AND_LOCK_SAFE_ASR_CALIBRATION_REQUIRED"
                ),
                "pather-panchali": "OWNER_DOCUMENT_REQUIRED",
            }
            path.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-07-13T07:30:39Z",
                        "provider_calls_ran": False,
                        "results": [
                            {
                                "slug": slug,
                                "state": state,
                                "blocker": f"canonical blocker for {slug}",
                                "evidence": f"evidence/{slug}.json",
                                "next_command": f"inspect {slug}",
                                "public_audio_allowed_now": False,
                            }
                            for slug, state in expected.items()
                        ],
                    }
                ),
                encoding="utf-8",
            )
            reconciled = MODULE.load_nonpaid_preflight_results(path)
            runtime = {
                **self.runtime,
                "providers": {**self.runtime["providers"], "google": False},
            }
            rows = [
                row("jekyll-and-hyde", exact_blocker="STALE_MATRIX_BLOCKER"),
                row("radharani", language="Bengali", exact_blocker="STALE_MATRIX_BLOCKER"),
                row("bn-066", language="Bengali", exact_blocker="STALE_MATRIX_BLOCKER"),
                row("pather-panchali", language="Bengali", exact_blocker="STALE_MATRIX_BLOCKER"),
            ]
            board = MODULE.build_execution_board(
                rows,
                {"titles": {}},
                {"titles": {}},
                runtime,
                {"available": False},
                {"accounting": {}},
                root,
                reconciled,
            )
            decisions = {item["slug"]: item for item in board["title_decisions"]}
            for slug, state in expected.items():
                self.assertEqual(decisions[slug]["state"], state)
                self.assertEqual(
                    decisions[slug]["decision_source"],
                    "sprint1_v3_nonpaid_preflight_results",
                )
                self.assertFalse(decisions[slug]["paid_execution_allowed"])
            self.assertEqual(
                decisions["jekyll-and-hyde"]["paid_execution_blocker"],
                "GOOGLE_ADC_REAUTH_REQUIRED",
            )
            self.assertEqual(
                board["reconciled_nonpaid_preflight"]["matched_title_count"], 4
            )

    def test_bengali_paid_work_requires_campaign_specific_gates(self):
        decision = MODULE.title_decision(
            row("radharani", language="Bengali", next_command="dry-run"),
            {},
            None,
            self.runtime,
            Path("/repo"),
            0,
        )
        self.assertEqual(decision["state"], "NON_PAID_BENGALI_PREFLIGHT_READY")
        self.assertFalse(decision["paid_execution_allowed"])
        self.assertEqual(decision["paid_execution_blocker"], "BENGALI_CAMPAIGN_PAID_GATES_MISSING")

    def test_long_titles_wait_for_five_additional_short_yes_yes(self):
        decision = MODULE.title_decision(
            row("dracula"), {}, None, self.runtime, Path("/repo"), 4
        )
        self.assertEqual(decision["state"], "LONG_TITLE_SEQUENCE_HOLD")

    def test_approved_title_is_validation_only(self):
        decision = MODULE.title_decision(
            row(
                "a-ghost-story",
                publicly_available_audiobook="Yes",
                exact_blocker="NONE",
                final_status="Yes, publicly rendered book + Yes, publicly available audiobook",
            ),
            {},
            None,
            self.runtime,
            Path("/repo"),
            0,
        )
        self.assertEqual(decision["state"], "YES_YES_PRODUCTION_REVALIDATION")
        self.assertTrue(decision["public_audio_allowed_now"])

    def test_execution_board_has_no_implicit_paid_action(self):
        rows = [row("radharani", language="Bengali", next_command="dry-run")]
        registry = {"titles": {"radharani": {}}}
        intake = {"titles": {}}
        ledger = {"accounting": {"cumulative_conservative_estimated_spend_usd": 14.0}}
        board = MODULE.build_execution_board(
            rows,
            registry,
            intake,
            self.runtime,
            {"available": True},
            ledger,
            Path("/repo"),
        )
        self.assertIsNone(board["next_paid_action"])
        self.assertEqual(board["budget"]["estimated_remaining_usd"], 161.0)
        self.assertFalse(board["safety"]["free_form_evidence_commands_executed"])

    def test_external_audio_decision_reconciles_both_matrix_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            matrix_path = root / "matrix.json"
            final_path = root / "final.json"
            ledger_path = root / "ledger.json"
            matrix_path.write_text(
                json.dumps({"titles": [row("story", final_status="ASR_SOURCE_MISMATCH")]}),
                encoding="utf-8",
            )
            final_path.write_text(
                json.dumps({"titles": [row("story", final_status="ASR_SOURCE_MISMATCH")]}),
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps({"entries": []}),
                encoding="utf-8",
            )
            board = {
                "generated_at": "2026-07-13T00:00:00Z",
                "loop_state": "WAITING_EXTERNAL_SOURCE_BOUND_INPUT",
                "summary": {"active_titles": 1, "yes_yes": 0},
                "title_decisions": [
                    {
                        "slug": "story",
                        "state": MODULE.WAITING_EXTERNAL_AUDIO_STATE,
                        "next_command": "validate-received-audio",
                        "public_audio_allowed_now": False,
                    }
                ],
            }

            MODULE.update_evidence_files(
                matrix_path,
                final_path,
                ledger_path,
                board,
                execution=None,
            )

            matrix_row = json.loads(matrix_path.read_text(encoding="utf-8"))["titles"][0]
            final_row = json.loads(final_path.read_text(encoding="utf-8"))["titles"][0]
            self.assertEqual(matrix_row["final_status"], MODULE.EXTERNAL_AUDIO_FINAL_STATUS)
            self.assertEqual(final_row["final_status"], MODULE.EXTERNAL_AUDIO_FINAL_STATUS)
            self.assertEqual(matrix_row["next_command"], "validate-received-audio")
            self.assertEqual(final_row["next_command"], "validate-received-audio")


if __name__ == "__main__":
    unittest.main()
