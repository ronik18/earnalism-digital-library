import argparse
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

    def test_missing_gates_fail_closed_before_paid_work(self):
        snapshot = MODULE.runtime_gates({})
        self.assertFalse(snapshot["ready_for_bengali_paid_work"])
        self.assertIn("SARVAM_API_KEY", snapshot["missing_or_invalid"])

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

    def test_representative_gate_passes_only_current_thresholds(self):
        with tempfile.TemporaryDirectory() as directory:
            sample_path = Path(directory) / "samples.json"
            sample_path.write_text(
                json.dumps(
                    {
                        "samples": [
                            {
                                "status": "PASS",
                                "scores": {"overall_listening_score": 9.4, "confidence_score": 0.91},
                                "judge_flags": {"robotic_texture_detected": False},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "ROOT", Path(directory)):
                self.assertTrue(MODULE.representative_gate_passed({"sample_results_path": "samples.json"}))
            sample_path.write_text(
                json.dumps(
                    {
                        "samples": [
                            {
                                "status": "PASS",
                                "scores": {"overall_listening_score": 9.3, "confidence_score": 0.91},
                                "judge_flags": {},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "ROOT", Path(directory)):
                self.assertFalse(MODULE.representative_gate_passed({"sample_results_path": "samples.json"}))

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
        self.assertEqual(summary["ending_yes_yes_count"], 4)
        self.assertEqual(summary["processed_titles"][1]["status"], "SKIPPED_MAX_NEW_PUBLICATIONS_REACHED")
        self.assertEqual(process.call_count, 1)


if __name__ == "__main__":
    unittest.main()
