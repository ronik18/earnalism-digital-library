"""CPU-only adapter regressions. All sources/rights/reviews here are TEST fixtures.

No model, network, provider, real approval or publication is exercised. Optional
FFmpeg tests encode/decode actual local fixture media and check its exact lineage.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts import earnalism_media_adapters as media


class MediaAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="earnalism-adapter-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.context = {"workspace": str(self.root), "repo_root": str(media.ROOT), "language": "en"}

    def ref(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes): path.write_bytes(value)
        elif isinstance(value, str): path.write_text(value, encoding="utf-8")
        else: path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return media._bound(path)

    def source(self, language="en"):
        manuscript = {**self.ref("manuscript.txt", "Synthetic source fixture."), "language": language}
        manifest = {"slug": "synthetic-test-only", "manuscript": manuscript, "rights": {
            "source_url": "https://example.invalid/test-only", "source_license": "TEST_ONLY",
            "commercial_use": "APPROVED", "territories": ["IN"], "source_sha256": manuscript["sha256"]}}
        return self.ref("source.json", manifest), manuscript

    def test_real_source_dispatch_is_private_and_language_bound(self):
        for language in ("en", "bn"):
            manifest, manuscript = self.source(language)
            result = media.run_stage("source", {"kind": "book-source", "manifest": manifest},
                                     {**self.context, "language": language})
            self.assertEqual(result["status"], "COMPLETE", result)
            self.assertEqual(result["details"]["bindings"]["manuscript"]["sha256"], manuscript["sha256"])
            self.assertFalse(result["acceptance"]["release_approved"])
            self.assertEqual(result["acceptance"]["listening"], "UNPERFORMED")
        result = media.run_stage("source", {"kind": "book-source", "manifest": manifest}, self.context)
        self.assertEqual(result["status"], "BLOCKED")

    def test_command_injection_and_escape_are_rejected_before_dispatch(self):
        manifest, _ = self.source()
        result = media.run_stage("source", {"kind": "book-source", "manifest": manifest,
                                            "command": "touch /tmp/should-never-run"}, self.context)
        self.assertEqual(result["status"], "BLOCKED")
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external) / "private.txt"
            outside.write_text("outside workspace")
            result = media.run_stage("source", {"kind": "book-source", "manifest": media._bound(outside)}, self.context)
            self.assertEqual(result["status"], "BLOCKED")
        (self.root / "linked.json").symlink_to(self.root / "source.json")
        result = media.run_stage("source", {"kind": "book-source", "manifest": {
            "path": str(self.root / "linked.json"), "sha256": manifest["sha256"]}}, self.context)
        self.assertEqual(result["status"], "BLOCKED")

    def test_unsupported_science_cannot_reach_models_or_renderer(self):
        with patch.object(media, "_run") as command, patch.object(media, "_known_module") as load:
            result = media.run_stage("visuals", {"kind": "science-animation", "science": "arbitrary-renamed-moon",
                                                "project": {}}, self.context)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("Unsupported science", result["blockers"][0])
        command.assert_not_called()
        load.assert_not_called()

    def test_stale_dependency_and_missing_role_are_rejected(self):
        context = {**self.context, "upstream": {"narration": {"artifacts": [{"sha256": "a" * 64}]}}}
        with self.assertRaisesRegex(ValueError, "Stale handoff"):
            media._consume(context, "narration", "narration", "b" * 64)
        with self.assertRaisesRegex(ValueError, "Stale handoff"):
            media._consume(context, "source", "manuscript", "b" * 64)

    def test_fake_declared_passes_do_not_establish_release_readiness(self):
        manifest, manuscript = self.source()
        data = json.loads(Path(manifest["path"]).read_text())
        data["audiovisual"] = {"schema": "earnalism.book_audiovisual.v1", "scope": "full_title",
                               "fixture_mode": False, "files": {}, "outputs": []}
        data["automated_checks"] = {name: {"status": "PASS"} for name in (
            "rights", "content", "metadata", "asr", "synchronization", "browser", "audiovisual")}
        manifest = self.ref("fake-ready.json", data)
        result = media.run_stage("release-ready", {"kind": "book-release", "manifest": manifest,
                                                   "output_dir": str(self.root / "release-check")}, self.context)
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertFalse(result["acceptance"]["release_approved"])
        self.assertEqual(result["details"]["evaluator"], "scripts.produce_release.evaluate")
        self.assertEqual(result["details"]["governor"]["release_status"], "BLOCKED")

    def test_nested_review_manifest_preserves_workspace_relative_report_binding(self):
        from scripts.release_acceptance import _av_ref
        manifest = self.ref("manifests/nested/title.json", {"scope": "PATH_FIXTURE_ONLY"})
        report = self.ref("runs/fixture/compose/render-report.json", {"scope": "PATH_FIXTURE_ONLY"})
        relative_manifest = {**manifest, "path": "manifests/nested/title.json"}
        relative_report = {**report, "path": "runs/fixture/compose/render-report.json"}
        seen = []
        def consume_report(value, manifest_root, descriptor):
            # Exercise the actual existing evaluator's path/hash resolver at
            # this boundary; this fixture supplies no quality acceptance.
            resolved = _av_ref(descriptor, manifest_root, "renderer report")
            seen.append(resolved)
            return {"status": "TEST_ONLY_PATH_BINDING", "render_report": descriptor}
        context = {**self.context, "upstream": {"compose": {"artifacts": [report]}}}
        with patch("scripts.release_acceptance.measure_audiovisual", side_effect=consume_report):
            result = media.run_stage("review", {"kind": "book-av-review",
                "manifest": relative_manifest, "render_report": relative_report,
                "output_dir": "reviews/fixture"}, context)
        self.assertEqual(result["status"], "COMPLETE", result)
        self.assertEqual(seen, [Path(report["path"])])
        stored = json.loads((self.root / "reviews/fixture/technical-review.json").read_text())
        self.assertEqual(Path(stored["render_report"]["path"]), Path(report["path"]))
        self.assertEqual(stored["render_report"]["sha256"], report["sha256"])
        self.assertFalse(result["acceptance"]["release_approved"])

    def test_wan_is_inert_without_actual_runtime_activation(self):
        batch = media._known_module("wan22/batch.py", "earnalism_test_fixed_batch")
        image = self.ref("onset.png", b"SYNTHETIC_TEST_ONLY_NOT_IMAGE")
        profile = batch.w.PROFILES["l4-landscape-v1"]
        scene = {"id": "test-only", "image": "onset.png", "image_sha256": image["sha256"],
                 "profile": "l4-landscape-v1", **{k: profile[k] for k in ("width", "height", "frames", "fps")},
                 "inference_steps": 24, "guidance_scale": 5.0, "seed": 1,
                 "prompt": "Synthetic queue fixture only; this must never reach inference."}
        job = self.ref("job.json", {"schema": batch.SCHEMA, "run_id": "inert-test-only",
            "model": batch.w.MODEL, "model_revision": batch.w.REVISION, "private": True,
            "publication_approved": False, "wall_seconds": 600, "max_attempts": 1,
            "max_output_seconds": 121 / 24, "prior_attempt_evidence": {"scope": "TEST_ONLY"}, "scenes": [scene]})
        auth = self.ref("authority.json", {"schema": batch.AUTHORITY_SCHEMA, "owner_authorized": True,
            "job_sha256": job["sha256"], "evidence_ref": "TEST_ONLY_NOT_ACTUAL_AUTHORITY",
            "free_runtime_confirmed": False, "observed_units_per_hour": 1.94,
            "approved_compute_units": 1, "allocation_started_at": time.time()})
        pack = self.ref("inputs.zip", b"TEST_ONLY_NOT_UNPACKED_WHILE_INERT")
        with patch.object(media, "_run") as command:
            result = media.run_stage("visuals", {"kind": "wan-batch", "job": job, "inputs": pack,
                "authority": auth, "output_dir": str(self.root / "wan")}, self.context)
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertFalse((self.root / "wan").exists())
        command.assert_not_called()

    def score_packet(self):
        from scripts.test_audiobook_score_renderer import fixture
        voice = fixture(self.root / "voice.wav", 8000, voice=True)
        bed = fixture(self.root / "bed.wav", 8000)
        _, manuscript = self.source()
        timing = self.ref("timing.json", {"schema": "earnalism.audiobook_score.timing.v1",
            "manuscript_sha256": manuscript["sha256"], "narration_sha256": voice["sha256"],
            "duration_ms": 8000, "method": "human_verified_audio",
            "provenance": {"tool": "SYNTHETIC LOCAL DISPATCH TEST ONLY", "version": "1", "boundary_validation": "accepted"},
            "cues": [{"id": "c1", "start_ms": 0, "end_ms": 8000, "text_start": 0,
                      "text_end": 25, "text": "Synthetic source fixture."}]})
        rights = self.ref("music-rights.json", {"schema": "earnalism.audiobook_music_rights.v1",
            "asset_sha256": bed["sha256"], "rights_holder": "Synthetic fixture only", "license_id": "TEST_ONLY",
            "scope": "commercial_audiobook", "territories": ["IN"], "commercial_use": True,
            "distribution": True, "derivative_mixing": True, "instrumental": True,
            "approval_status": "APPROVED", "approved_by": "Synthetic test; no actual rights approval",
            "approval_ref": "SYNTHETIC_DISPATCH_TEST_ONLY"})
        score_input = self.ref("score-input.json", {"schema": "earnalism.audiobook_score.input.v1",
            "manuscript": manuscript, "narration": voice, "timing": timing, "territory": "IN",
            "assets": [{"id": "bed", **bed, "moods": ["calm"], "energy": .2,
                        "transition_group": "test-only", "rights": rights}]})
        direction = {"schema": "earnalism.audiobook_score.direction.v1",
            "manuscript_sha256": manuscript["sha256"], "narration_sha256": voice["sha256"],
            "timing_sha256": timing["sha256"], "provenance": {"method": "editor",
                "agent_or_model": "SYNTHETIC TEST ONLY", "assessment_basis": "text_only", "version": "1"},
            "annotations": [{"cue_id": "c1", "emotion": "calm", "narrative_tone": "neutral",
                "speech_act": "narration", "intensity": .2, "confidence": .95, "uncertain": False,
                "score": "music", "transition": "auto", "context_cue_ids": ["c1"], "rationale": "Test-only calm fixture."}]}
        return score_input, direction, manuscript, voice, timing

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "local FFmpeg required")
    def test_current_timing_and_actual_score_handoff_with_unresolved_direction_hold(self):
        score_input, direction, manuscript, voice, timing = self.score_packet()
        context = {**self.context, "upstream": {
            "source": {"details": {"bindings": {"manuscript": manuscript}}},
            "narration": {"details": {"bindings": {"narration": voice}}},
            "timing": {"details": {"bindings": {"timing": timing}}}}}
        timing_result = media.run_stage("timing", {"kind": "measured-timing", "score_input": score_input}, context)
        self.assertEqual(timing_result["status"], "COMPLETE", timing_result)
        bad = deepcopy(context)
        bad["upstream"]["narration"]["details"]["bindings"]["narration"]["sha256"] = "a" * 64
        rejected = media.run_stage("timing", {"kind": "measured-timing", "score_input": score_input}, bad)
        self.assertEqual(rejected["status"], "BLOCKED")
        unresolved = deepcopy(direction)
        unresolved["annotations"][0]["uncertain"] = True
        unresolved_ref = self.ref("unresolved-direction.json", unresolved)
        output = self.root / "held-score"
        held = media.run_stage("score", {"kind": "source-bound-score", "score_input": score_input,
            "direction": unresolved_ref, "output_dir": str(output)}, context)
        self.assertEqual(held["status"], "BLOCKED", held)
        self.assertFalse(output.exists())
        silence = deepcopy(direction)
        silence["annotations"][0]["score"] = "silence"
        silent = media.run_stage("score", {"kind": "source-bound-score", "score_input": score_input,
            "direction": self.ref("silence-direction.json", silence), "continuous_body": True,
            "output_dir": str(self.root / "silent-science")}, context)
        self.assertEqual(silent["status"], "BLOCKED", silent)
        self.assertFalse((self.root / "silent-science").exists())
        result = media.run_stage("score", {"kind": "source-bound-score", "score_input": score_input,
            "direction": self.ref("direction.json", direction), "continuous_body": True,
            "output_dir": str(self.root / "scored")}, context)
        self.assertEqual(result["status"], "COMPLETE", result)
        mixed = result["details"]["bindings"]["scored_audio"]
        self.assertTrue(Path(mixed["path"]).stat().st_size > 1000)
        self.assertEqual(media.sha(mixed["path"]), mixed["sha256"])
        self.assertFalse(result["acceptance"]["release_approved"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "local FFmpeg required")
    def test_actual_local_composition_produces_full_bound_files_and_refuses_reuse(self):
        # Reuse the established tiny real-media fixture. Test-only retained rights
        # assertions below test dispatch, not their legal truth or any acceptance.
        from scripts.test_book_av_render import BookAVRenderTests
        fixture = BookAVRenderTests("test_actual_two_format_render_preserves_soundtrack_and_rejects_reuse")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root.resolve()
        context = {**self.context, "workspace": str(self.root)}
        job = fixture.job
        job["fixture_mode"] = False
        timing_path = Path(job["timing"]["path"])
        timing = json.loads(timing_path.read_text())
        timing["method"] = "human_verified_audio"
        timing["provenance"]["boundary_validation"] = "accepted"
        timing["provenance"]["tool"] = "SYNTHETIC LOCAL DISPATCH TEST ONLY"
        job["timing"] = self.ref("timing.json", timing)
        rights_path = Path(job["assets"][0]["rights"]["path"])
        rights = json.loads(rights_path.read_text())
        rights["approval_status"] = "APPROVED"
        job["assets"][0]["rights"] = self.ref("rights.json", rights)
        job_ref = self.ref("job.json", job)
        spec = {"kind": "book-av", "job": job_ref, "output_dir": str(self.root / "adapter-render")}
        result = media.run_stage("compose", spec, context)
        self.assertEqual(result["status"], "COMPLETE", result)
        self.assertFalse(result["acceptance"]["publication_approved"])
        paths = {Path(r["path"]).name for r in result["artifacts"]}
        self.assertTrue({"landscape.mp4", "portrait.mp4", "soundtrack.wav", "soundtrack.m4a", "render-report.json"} <= paths)
        for ref in result["artifacts"]:
            self.assertEqual(media.sha(ref["path"]), ref["sha256"])
        before = media.sha(self.root / "adapter-render/landscape.mp4")
        repeated = media.run_stage("compose", spec, context)
        self.assertEqual(repeated["status"], "BLOCKED")
        self.assertEqual(media.sha(self.root / "adapter-render/landscape.mp4"), before)


if __name__ == "__main__":
    unittest.main()
