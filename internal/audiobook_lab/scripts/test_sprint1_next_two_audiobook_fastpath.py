import argparse
import contextlib
import io
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("sprint1_next_two_audiobook_fastpath.py")
SPEC = importlib.util.spec_from_file_location("sprint1_next_two_audiobook_fastpath", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NextTwoFastPathTests(unittest.TestCase):
    def test_parses_candidate_slugs_deduplicated(self):
        self.assertEqual(
            MODULE.parse_candidate_slugs(" radharani,nishkriti,radharani, "),
            ["radharani", "nishkriti"],
        )

    def test_rejects_deferred_titles(self):
        with self.assertRaises(MODULE.FastPathError):
            MODULE.reject_deferred_slugs(["radharani", "pather-panchali"])

    def test_runtime_gates_hide_secrets_and_require_keys(self):
        env = {
            **MODULE.PAID_ENV,
            "SARVAM_API_KEY": "sarvam-real-value",
            "OPENAI_API_KEY": "openai-real-value",
        }
        snapshot = MODULE.runtime_gates(env)
        self.assertTrue(snapshot["ready_for_bengali_paid_work"])
        self.assertEqual(snapshot["credentials"]["SARVAM_API_KEY"], "SET")
        self.assertNotIn("sarvam-real-value", json.dumps(snapshot))
        self.assertNotIn("openai-real-value", json.dumps(snapshot))

    def test_runtime_gates_enforce_owner_campaign_and_per_title_caps(self):
        self.assertEqual(MODULE.PAID_ENV["SPRINT1_TOTAL_AUDIO_BUDGET_USD"], "75")
        self.assertEqual(MODULE.PAID_ENV["SPRINT1_MAX_USD_PER_TITLE"], "8")
        self.assertEqual(MODULE.PAID_ENV["EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD"], "5")
        self.assertEqual(MODULE.PAID_ENV["EARNALISM_FULL_TITLE_CUMULATIVE_MAX_ESTIMATED_USD"], "5")
        self.assertEqual(MODULE.PAID_ENV["EARNALISM_REQUIRE_AUDIO_DERIVED_ASR_9_7"], "true")

    def test_missing_gates_fail_closed_before_paid_work(self):
        snapshot = MODULE.runtime_gates({})
        self.assertFalse(snapshot["ready_for_bengali_paid_work"])
        self.assertIn("SARVAM_API_KEY", snapshot["missing_or_invalid"])

    def test_paid_env_does_not_synthesize_approval_or_budget_gates(self):
        child = MODULE.paid_env({"SARVAM_API_KEY": "secret"}, slug="radharani")
        self.assertNotIn("EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS", child)
        self.assertNotIn("EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN", child)
        self.assertNotIn("EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD", child)
        self.assertEqual(child["EARNALISM_BENGALI_FULL_PILOT_SLUG"], "radharani")

    def test_lock_snapshot_requires_empty_active_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paid_tts.lock"
            path.write_text(
                json.dumps({"status": "active", "current_holder": "none", "allowed_next_holders": []}),
                encoding="utf-8",
            )
            self.assertTrue(MODULE.lock_snapshot(path)["available"])
            path.write_text(
                json.dumps({"status": "active", "current_holder": "worker", "allowed_next_holders": []}),
                encoding="utf-8",
            )
            self.assertFalse(MODULE.lock_snapshot(path)["available"])

    def test_lock_snapshot_rejects_stale_slug_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paid_tts.lock"
            path.write_text(
                json.dumps(
                    {
                        "status": "active",
                        "current_holder": "none",
                        "allowed_next_holders": [],
                        "approved_scope": "Nishkriti only",
                        "allowed_slugs": ["nishkriti"],
                    }
                ),
                encoding="utf-8",
            )
            snapshot = MODULE.lock_snapshot(path, slug="radharani")
        self.assertFalse(snapshot["available"])
        self.assertIn("PAID_TTS_LOCK_SLUG_MISMATCH", snapshot["blocker"])

    def test_lock_snapshot_rejects_unscoped_paid_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paid_tts.lock"
            path.write_text(
                json.dumps(
                    {
                        "status": "active",
                        "current_holder": "none",
                        "allowed_next_holders": [],
                        "allowed_slugs": [],
                    }
                ),
                encoding="utf-8",
            )
            snapshot = MODULE.lock_snapshot(path, slug="radharani")
        self.assertFalse(snapshot["available"])
        self.assertIn("PAID_TTS_LOCK_SLUG_MISMATCH", snapshot["blocker"])

    def test_representative_gate_enforces_policy_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            sample_path = Path(directory) / "samples.json"

            def passes(score=9.2, confidence=0.90, flags=None):
                sample_path.write_text(
                    json.dumps(
                        {
                            "samples": [
                                {
                                    "status": "PASS",
                                    "scores": {
                                        "overall_listening_score": score,
                                        "confidence_score": confidence,
                                    },
                                    "judge_flags": flags or {},
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                with mock.patch.object(MODULE, "ROOT", Path(directory)):
                    return MODULE.representative_gate_passed({"sample_results_path": "samples.json"})

            self.assertTrue(passes(score=9.2, confidence=0.90))
            self.assertFalse(passes(score=9.19, confidence=0.90))
            self.assertFalse(passes(score=9.2, confidence=0.89))
            fatal_flags = (
                "robotic_texture_detected",
                "mechanical_cadence_detected",
                "list_reading_rhythm_detected",
                "choppy_joins_detected",
                "fallback_tts_detected",
            )
            for flag in fatal_flags:
                with self.subTest(flag=flag):
                    self.assertFalse(passes(score=9.2, confidence=0.90, flags={flag: True}))

    def test_release_evidence_reports_policy_listening_minimum(self):
        with tempfile.TemporaryDirectory() as directory:
            title_runs = Path(directory) / "title-runs"
            with mock.patch.object(MODULE, "TITLE_RUNS_DIR", title_runs):
                MODULE.write_title_reports(
                    {
                        "slug": "radharani",
                        "status": "PAID_GATES_MISSING",
                        "blocker": "PAID_RUNTIME_GATES_MISSING",
                        "new_public_audiobook": False,
                    }
                )
            evidence = json.loads((title_runs / "radharani_release_gate_evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["release_gate"]["listening_sample_minimum"], 9.2)

    def test_existing_representative_audition_reuses_passing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fastpath = root / "fastpath"
            run_dir = fastpath / "radharani_representative_audition"
            run_dir.mkdir(parents=True)
            sample_path = root / "samples.json"
            sample_path.write_text(
                json.dumps(
                    {
                        "samples": [
                            {
                                "status": "PASS",
                                "scores": {"overall_listening_score": 9.4, "confidence_score": 0.95},
                                "judge_flags": {"list_reading_rhythm_detected": False},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "bengali_tts_provider_bakeoff_report.json").write_text(
                json.dumps({"sample_results_path": "samples.json"}),
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "ROOT", root), mock.patch.object(MODULE, "FASTPATH_DIR", fastpath):
                result = MODULE.existing_representative_audition("radharani")
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["representative_passed"])
        self.assertTrue(result["reused_existing_evidence"])

    def test_nishkriti_preflight_uses_backend_source_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = root / "backend/data/controlled_publications/nishkriti"
            (backend / "chapters").mkdir(parents=True)
            (backend / "public_book.json").write_text(
                json.dumps({"cover_url": "front", "back_cover_url": "back"}),
                encoding="utf-8",
            )
            (backend / "chapters/0001.json").write_text(json.dumps({"text": "chapter"}), encoding="utf-8")
            release_row = {
                "slug": "nishkriti",
                "title": "Nishkriti",
                "language": "Bengali",
                "public_reader_status": "PUBLIC_READER",
                "gates": {
                    "source_rights": "PASS",
                    "text_sanitation": "PASS",
                    "text_normalization": "PASS",
                },
            }
            result = MODULE.local_candidate_preflight(root, "nishkriti", release_row)
        self.assertTrue(result["clean_for_paid_work"])
        self.assertNotIn("PIPELINE_SOURCE_OVERRIDE_REQUIRED", result["blockers"])

    def test_honors_max_publications_by_skipping_after_limit(self):
        args = argparse.Namespace(
            asset_root=Path("/tmp/asset-root"),
            lock_path=Path("/tmp/paid_tts.lock"),
            candidate_slugs="a,b",
            max_new_publications=1,
            reuse_first=True,
            publish_if_pass=True,
            execute=False,
            fail_closed=True,
        )
        rows = {
            "a": {"slug": "a", "title": "A", "language": "Bengali", "public_reader_status": "PUBLIC_READER", "gates": {"source_rights": "PASS", "text_sanitation": "PASS", "text_normalization": "PASS"}},
            "b": {"slug": "b", "title": "B", "language": "Bengali", "public_reader_status": "PUBLIC_READER", "gates": {"source_rights": "PASS", "text_sanitation": "PASS", "text_normalization": "PASS"}},
        }
        first = {"slug": "a", "status": "PUBLISHED", "new_public_audiobook": True}
        with mock.patch.object(MODULE, "matrix_rows", return_value=rows), \
            mock.patch.object(MODULE, "controlled_book", return_value={"cover_url": "x"}), \
            mock.patch.object(MODULE, "process_candidate", side_effect=[first]) as process, \
            mock.patch.object(MODULE, "atomic_write_json"), \
            mock.patch.object(MODULE, "atomic_write_text"), \
            mock.patch.object(MODULE, "lock_snapshot", return_value={"available": True}), \
            mock.patch.object(MODULE, "production_controls", return_value={"ok": True, "approved": [], "hidden": [], "blockers": []}):
            summary = MODULE.run(args, env={**MODULE.PAID_ENV, "SARVAM_API_KEY": "x", "OPENAI_API_KEY": "y"})
        self.assertEqual(summary["ending_yes_yes_count"], 5)
        self.assertEqual(summary["processed_titles"][1]["status"], "SKIPPED_MAX_NEW_PUBLICATIONS_REACHED")
        self.assertEqual(process.call_count, 1)

    def test_dry_run_reusing_audition_never_starts_full_factory(self):
        args = argparse.Namespace(execute=False, publish_if_pass=False, reuse_first=True)
        release_row = {
            "slug": "radharani",
            "title": "Radharani",
            "language": "Bengali",
            "public_reader_status": "PUBLIC_READER",
            "gates": {"source_rights": "PASS", "text_sanitation": "PASS", "text_normalization": "PASS"},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book_dir = root / "backend/data/controlled_publications/radharani"
            (book_dir / "chapters").mkdir(parents=True)
            (book_dir / "public_book.json").write_text(json.dumps({"cover_url": "front"}), encoding="utf-8")
            (book_dir / "chapters/chapter-001.json").write_text(json.dumps({"content": "text"}), encoding="utf-8")
            with mock.patch.object(MODULE, "TITLE_RUNS_DIR", root / "title-runs"), \
                mock.patch.object(MODULE, "runtime_gates", return_value={"ready_for_bengali_paid_work": True}), \
                mock.patch.object(MODULE, "lock_snapshot", return_value={"available": True}), \
                mock.patch.object(MODULE, "existing_representative_audition", return_value={
                    "status": "PASS", "representative_passed": True, "reused_existing_evidence": True,
                }), \
                mock.patch.object(MODULE, "run_full_factory_if_allowed") as full_factory:
                result = MODULE.process_candidate(
                    slug="radharani",
                    asset_root=root,
                    lock_path=root / "paid_tts.lock",
                    release_row=release_row,
                    env={**MODULE.PAID_ENV, "SARVAM_API_KEY": "x", "OPENAI_API_KEY": "y"},
                    args=args,
                )
        self.assertEqual(result["status"], "DRY_RUN_FULL_PIPELINE_NOT_EXECUTED")
        self.assertFalse(result["full_pipeline"]["provider_call_started"])
        full_factory.assert_not_called()

    def test_publish_command_enables_only_serial_downstream_workers(self):
        command = MODULE.full_factory_command("radharani", publish=True)

        def value_after(flag):
            return command[command.index(flag) + 1]

        self.assertEqual(value_after("--max-books-active"), "1")
        self.assertEqual(value_after("--max-tts-workers"), "1")
        self.assertEqual(value_after("--max-paid-workers"), "1")
        self.assertEqual(value_after("--max-asr-workers"), "1")
        self.assertEqual(value_after("--max-upload-workers"), "1")
        self.assertEqual(value_after("--max-metadata-workers"), "1")
        self.assertEqual(value_after("--max-browser-workers"), "1")
        self.assertIn("--publish-approved", command)

    def test_main_returns_nonzero_when_fail_closed_title_pipeline_fails(self):
        summary = {
            "ending_yes_yes_count": 4,
            "newly_public_audiobooks": [],
            "processed_titles": [
                {
                    "slug": "radharani",
                    "status": "FULL_PIPELINE_FAILED",
                    "blocker": "AUDIO_DERIVED_ASR_GATE_FAILED",
                }
            ],
        }
        with mock.patch.object(MODULE, "run", return_value=summary), io.StringIO() as output, contextlib.redirect_stdout(output):
            result = MODULE.main(
                [
                    "--candidate-slugs",
                    "radharani",
                    "--max-new-publications",
                    "1",
                    "--execute",
                    "--fail-closed",
                ]
            )
            payload = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertEqual(payload["status"], "FAIL_CLOSED")
        self.assertEqual(payload["failed_titles"][0]["slug"], "radharani")


if __name__ == "__main__":
    unittest.main()
