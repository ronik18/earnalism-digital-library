"""Controller regressions. Synthetic adapters/audio never qualify production."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts import earnalism_orchestrator as engine


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.source = self.put("software-source.txt", "Synthetic control fixture source.")
        self.history = self.put("history.json", {})
        self.project = {"id": "story", "kind": "book", "title": "The Selfish Giant", "language": "en",
                        "history": self.history,
                        "stages": {s: {"kind": "software-only-test"} for s in engine.STAGES}}
        self.save_registry([self.project])
        self.instruction = "Build the GO LIVE ready output for the audiovisual cinematic version for the book - The Selfish Giant"
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, value):
        path = self.workspace / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value,
                        encoding="utf-8")
        return {"path": str(path), "sha256": engine._sha(path)}

    def save_registry(self, projects):
        self.put("projects.json", {"schema": engine.REGISTRY_SCHEMA, "projects": projects})

    def adapter(self, stage, spec, context):
        self.calls.append(stage)
        output = Path(context["output_dir"])
        output.mkdir(parents=True, exist_ok=False)
        path = output / "software-only.txt"
        path.write_text("SYNTHETIC CONTROL TEST; NO MODEL, MEDIA, RIGHTS OR QUALITY ACCEPTANCE\n" + stage)
        return {"status": "COMPLETE", "artifacts": [{"path": str(path), "sha256": engine._sha(path)}],
                "blockers": [], "acceptance": {"release_approved": False},
                "details": {"scope": "Synthetic fixed-dispatch control test only",
                            "bindings": {"manuscript": self.source} if stage == "source" else {}}}

    def run_fixture(self, **kwargs):
        with patch.object(engine, "_dispatch", side_effect=self.adapter), \
             patch("scripts.earnalism_voice.validate_job", side_effect=lambda path: {"job": engine._load(Path(path))}):
            return engine.run(self.instruction, self.workspace, execute=True, **kwargs)

    def test_owner_instruction_examples_and_exact_bengali_identity(self):
        self.assertEqual(engine.parse_instruction(self.instruction)["title"], "The Selfish Giant")
        bn = engine.parse_instruction("Build the GO LIVE ready output for the audiovisual cinematic version for the Bengali book - Bicharak")
        self.assertEqual((bn["title"], bn["language"]), ("Bicharak", "bn"))
        science = engine.parse_instruction("Build the next audiovisual for the EverydayScience topic for theearnalism social media platform")
        self.assertTrue(science["next"])
        self.assertEqual(science["series"], "EverydayScience")
        self.assertFalse(science["publication_requested"])
        with self.assertRaises(ValueError):
            engine.parse_instruction("make something beautiful")

    def test_dry_plan_has_no_runtime_or_workspace_writes(self):
        before = sorted(str(p) for p in self.workspace.rglob("*"))
        report = engine.run(self.instruction, self.workspace)
        self.assertEqual(report["state"], "PRIVATE_EXECUTION_PREPARED")
        self.assertFalse(report["production_ready"])
        self.assertEqual(before, sorted(str(p) for p in self.workspace.rglob("*")))

    def test_natural_bengali_instruction_keeps_exact_title_and_known_voice_direction(self):
        examples = (
            "Build the GO LIVE ready audiovisual for Bengali book Bicharak using The Earnalism Voice",
            "Build the GO LIVE ready audiovisual for Bengali book - Bicharak using The Earnalism Voice",
            "Build the GO LIVE ready output for the audiovisual cinematic version for the Bengali book - Bicharak using The Earnalism Voice",
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with patch.object(engine, "_dispatch") as dispatch, patch.object(engine, "_runtime") as runtime:
                for instruction in examples:
                    result = engine.plan(instruction, workspace)
                    self.assertEqual(result["request"]["title"], "Bicharak")
                    self.assertEqual(result["request"]["language"], "bn")
                    self.assertEqual(result["request"]["requested_voice"], "TheEarnalismVoice")
                    self.assertEqual(result["state"], "MISSING_INPUT")
                    self.assertIsNone(result["project"])
                    self.assertFalse(result["publication_performed"])
                    self.assertFalse(result["model_weights_trained"])
                    self.assertEqual(list(workspace.iterdir()), [])
                dispatch.assert_not_called()
                runtime.assert_not_called()

    def test_instruction_does_not_guess_multiple_editions_or_arbitrary_prose(self):
        for instruction in (
            "Something I read mentions Bengali book Bicharak",
            "Build audiovisual for Bengali and English book - Bicharak",
            "Build Bengali book Bicharak and English book The Selfish Giant",
            "Build book - Bicharak; book - The Selfish Giant",
            "Build Bengali book using The Earnalism Voice",
        ):
            with self.subTest(instruction=instruction), self.assertRaises(ValueError):
                engine.parse_instruction(instruction)
        # A different trailing instruction is never silently removed or mapped
        # to the known branded voice; it cannot select Bicharak by accident.
        different = engine.parse_instruction("Build Bengali book Bicharak using voice B")
        self.assertEqual(different["title"], "Bicharak using voice B")
        self.assertNotIn("requested_voice", different)

    def test_shared_science_branding_and_runtime_changes_invalidate_visuals(self):
        root = self.workspace/"maintained-source-fixture"
        files = ["scripts/earnalism_orchestrator.py", "scripts/earnalism_media_adapters.py",
                 "skills/earnalism-video/software/thermal_touch/index.tsx"]
        shared = ["src/BrandWatermark.tsx", "src/branding.mjs", "src/social-safe-area.mjs",
                  "src/render-browser.mjs", "src/render-runtime.mjs", "src/prepare-render-runtime.mjs",
                  "package.json", "package-lock.json"]
        files += ["skills/earnalism-video/software/"+name for name in shared]
        for name in files:
            path = root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("source-only dependency fixture\n")
        with patch.object(engine, "ROOT", root):
            spec = {"kind":"science-animation","science":"thermal-touch"}
            before = engine._software("visuals", spec)
            narration_before = engine._software("narration", {})
            for name in shared:
                key = "skills/earnalism-video/software/"+name
                self.assertIn(key, before)
                (root/key).write_text("changed shared dependency: "+name)
                after = engine._software("visuals", spec)
                self.assertNotEqual(before[key], after[key])
            self.assertEqual(narration_before, engine._software("narration", {}))

    def test_missing_registry_and_ambiguous_language_are_concrete_holds(self):
        (self.workspace / "projects.json").unlink()
        report = engine.plan(self.instruction, self.workspace)
        self.assertEqual(report["state"], "MISSING_INPUT")
        self.assertIsNone(report["project"])
        other = copy.deepcopy(self.project)
        other.update(id="bengali", language="bn")
        self.save_registry([self.project, other])
        self.assertEqual(engine.plan(self.instruction, self.workspace)["state"], "EDITION_REQUIRED")
        self.assertEqual(engine.plan("Build English book - The Selfish Giant", self.workspace)["project"]["id"], "story")

    def test_next_science_uses_explicit_ready_order_and_completed_preparation(self):
        projects = []
        for i in (19, 17):
            item = copy.deepcopy(self.project)
            item.update(id=f"science-{i}", kind="science", title=f"Known topic {i}", series="EverydayScience",
                        queue_status="ready", queue_order=i)
            projects.append(item)
        self.save_registry(projects)
        text = "Build next audiovisual for EverydayScience topic"
        self.assertEqual(engine.plan(text, self.workspace)["project"]["id"], "science-17")
        engine._write(engine._state_path(self.workspace, "science-17"), {"queue_consumed": True})
        self.assertEqual(engine.plan(text, self.workspace)["project"]["id"], "science-19")
        projects[0].pop("queue_order")
        self.save_registry(projects)
        with self.assertRaisesRegex(ValueError, "queue_order"):
            engine.plan(text, self.workspace)

    def test_actual_source_adapter_runs_without_extra_compute_approval(self):
        source = self.put("manuscript.txt", "SOFTWARE TEST ONLY: an independently written test sentence.")
        manifest = self.put("source-manifest.json", {
            "manuscript": {**source, "language": "en"},
            "rights": {"source_url": "https://example.invalid/software-fixture", "source_license": "test assertion",
                       "commercial_use": "APPROVED", "territories": ["IN"], "source_sha256": source["sha256"]}})
        self.project["stages"] = {"source": {"kind": "book-source", "manifest": manifest}}
        self.save_registry([self.project])
        report = engine.run(self.instruction, self.workspace, execute=True)
        self.assertEqual(report["executed_stages"], ["source"])
        self.assertEqual(report["stages"]["source"]["details"]["bindings"]["manuscript"]["sha256"], source["sha256"])
        self.assertFalse(report["production_ready"])
        self.assertIn("missing stage input: narration", report["blockers"])

    def test_resume_verifies_actual_outputs_and_never_infers_quality(self):
        first = self.run_fixture()
        self.assertEqual(first["executed_stages"], list(engine.STAGES))
        self.assertFalse(first["production_ready"])
        self.assertFalse(first["publication_performed"])
        self.calls.clear()
        second = self.run_fixture()
        self.assertEqual(second["reused_stages"], list(engine.STAGES))
        self.assertEqual(self.calls, [])
        output = Path(second["stages"]["source"]["artifacts"][0]["path"])
        output.write_text("CHANGED OUTSIDE THE VERIFIED CHECKPOINT")
        third = self.run_fixture()
        self.assertEqual(self.calls, [])
        self.assertIn("changed input", third["blockers"][0])

    def test_transitive_input_mutation_blocks_cache_reuse(self):
        nested = self.put("nested.txt", "before")
        job = self.put("job.json", {"file": nested})
        self.project["stages"]["source"]["job"] = job
        self.save_registry([self.project])
        self.run_fixture()
        Path(nested["path"]).write_text("after")
        self.calls.clear()
        report = self.run_fixture()
        self.assertEqual(self.calls, [])
        self.assertIn("changed input", report["blockers"][0])

    def test_unknown_partial_attempt_cannot_be_replayed(self):
        def fail(stage, spec, context):
            if stage == "narration":
                raise RuntimeError("Interrupted after entering the fixed stage; output status unknown")
            return self.adapter(stage, spec, context)
        with patch.object(engine, "_dispatch", side_effect=fail):
            first = engine.run(self.instruction, self.workspace, execute=True)
        self.assertIn("unknown", first["blockers"][0])
        self.calls.clear()
        second = self.run_fixture()
        self.assertEqual(self.calls, [])
        self.assertIn("FAILED_OR_UNKNOWN_NO_REPLAY", second["blockers"][0])

    def test_feedback_requires_changed_recipe_and_preserves_unaffected_visuals(self):
        direction = self.put("direction.json", {"recipe": "calm", "scope": "synthetic test"})
        self.project["stages"]["score"]["direction"] = direction
        self.save_registry([self.project])
        first = self.run_fixture()
        candidate = first["stages"]["compose"]["artifacts"][0]["sha256"]
        note = self.put("note.json", {"project_id": "story", "candidate_sha256": candidate,
            "source": "automatic", "source_ref": "software test, not listening", "scope": "test interval",
            "area": "score", "finding": "Test policy requested changed recipe", "fix": "Change source-bound direction",
            "preserve": "Narration and visual source bytes"})
        event = engine.feedback(note["path"], self.workspace)
        self.assertFalse(event["acceptance_created"])
        self.assertFalse(event["model_weights_trained"])
        self.calls.clear()
        identical = self.run_fixture()
        self.assertIn("changed inputs", identical["blockers"][0])
        self.assertEqual(self.calls, [])
        self.project["stages"]["score"]["direction"] = self.put("direction.json", {"recipe": "tense", "scope": "synthetic test"})
        self.save_registry([self.project])
        corrected = self.run_fixture()
        self.assertIn("visuals", corrected["reused_stages"])
        self.assertIn("narration", corrected["reused_stages"])
        self.assertIn("score", corrected["executed_stages"])
        self.assertIn("compose", corrected["executed_stages"])
        duplicate = engine.feedback(note["path"], self.workspace)
        # The original exact event remains; correction does not turn feedback into acceptance.
        self.assertFalse(duplicate["acceptance_created"])
        self.assertTrue(duplicate["duplicate_reused"])

    def test_feedback_other_project_does_not_invalidate_current_project(self):
        self.run_fixture()
        other = copy.deepcopy(self.project)
        other.update(id="other", title="Another Book")
        self.save_registry([self.project, other])
        with patch.object(engine, "_dispatch", side_effect=self.adapter):
            report = engine.run("Build book - Another Book", self.workspace, execute=True)
        candidate = report["stages"]["compose"]["artifacts"][0]["sha256"]
        note = self.put("other-note.json", {"project_id": "other", "candidate_sha256": candidate,
            "source": "human", "source_ref": "isolated software fixture", "scope": "other test",
            "area": "visual", "finding": "Test-only visual finding", "fix": "Change test input", "preserve": "Test sound"})
        engine.feedback(note["path"], self.workspace)
        self.calls.clear()
        current = self.run_fixture()
        self.assertEqual(current["reused_stages"], list(engine.STAGES))
        self.assertEqual(self.calls, [])

    def test_owner_narration_hold_cannot_resurrect_retained_audio(self):
        self.history = self.put("history.json", {"title": "The Selfish Giant", "language": "en",
            "owner_revision": {"schema": "earnalism.book_av_owner_revision.v1", "source": "human", "status": "ACTIVE",
                "language": "en", "source_ref": "actual owner fixture for parser test", "required_changes": ["narration"]}})
        self.project["history"] = self.history
        self.project["stages"]["narration"] = {"kind": "retained-narration"}
        self.save_registry([self.project])
        report = self.run_fixture()
        self.assertEqual(self.calls, ["source"])
        self.assertFalse(report["production_ready"])
        self.assertIn("owner revision", " ".join(report["blockers"]))

    def owner_record(self, *, status="ACTIVE", areas=("narration", "visual"),
                     at="2026-11-14T10:00:00+00:00", language="en", title="The Selfish Giant"):
        return {"title": title, "language": language, "at": at,
                "owner_revision": {"schema": "earnalism.book_av_owner_revision.v1", "source": "human",
                    "status": status, "language": language, "source_ref": "SOFTWARE FIXTURE: " + status + at,
                    "required_changes": list(areas)}}

    def pinned_history(self):
        root = self.workspace / "pinned-source"
        path = root / "internal/earnalism_intelligence/title_decision_history.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"baseline": self.owner_record()}))
        return root

    def test_empty_private_history_cannot_clear_canonical_active_owner_hold(self):
        root = self.pinned_history()
        self.project["stages"]["narration"] = {"kind": "retained-narration"}
        self.save_registry([self.project])
        with patch.object(engine, "ROOT", root):
            plan = engine.plan(self.instruction, self.workspace)
            report = self.run_fixture()
        revision = plan["discovery"]["current_owner_revision"]
        self.assertEqual(revision["status"], "ACTIVE")
        self.assertEqual(set(revision["required_changes"]), {"narration", "visual"})
        self.assertEqual(len(plan["discovery"]["history_sources"]), 2)
        self.assertIsNone(plan["discovery"]["preferred_retained_candidate"])
        self.assertTrue(plan["owner_revision_active"])
        self.assertEqual(self.calls, ["source"])
        self.assertFalse(report["production_ready"])

    def test_private_resolution_needs_later_time_and_same_title_language(self):
        root = self.pinned_history()
        cases = [
            self.owner_record(status="RESOLVED", at="2026-11-13T11:00:00+00:00"),
            self.owner_record(status="RESOLVED", at="2026-11-14T10:00:00+00:00"),
            self.owner_record(status="RESOLVED", at=""),
            self.owner_record(status="RESOLVED", at="2026-11-14T12:00:00+00:00", language="bn"),
            self.owner_record(status="RESOLVED", at="2026-11-14T12:00:00+00:00", title="Another Book"),
        ]
        for record in cases:
            with self.subTest(record=record):
                self.project["history"] = self.put("history.json", {"private": record})
                self.save_registry([self.project])
                with patch.object(engine, "ROOT", root):
                    plan = engine.plan(self.instruction, self.workspace)
                self.assertTrue(plan["owner_revision_active"])
                self.assertEqual(set(plan["discovery"]["current_owner_revision"]["required_changes"]), {"narration", "visual"})

    def test_later_explicit_same_edition_resolution_can_clear_matching_hold(self):
        root = self.pinned_history()
        self.project["history"] = self.put("history.json", {"resolved": self.owner_record(
            status="RESOLVED", at="2026-11-14T12:00:00+00:00")})
        self.save_registry([self.project])
        with patch.object(engine, "ROOT", root):
            plan = engine.plan(self.instruction, self.workspace)
        self.assertFalse(plan["owner_revision_active"])
        self.assertEqual(plan["discovery"]["current_owner_revision"]["status"], "RESOLVED")
        self.assertEqual(plan["discovery"]["state"], "PRIVATE_PREPARATION_REQUIRED")
        self.assertEqual(len(plan["discovery"]["owner_revision_sources"]), 2)

    def test_partial_resolution_and_new_findings_preserve_unresolved_areas(self):
        root = self.pinned_history()
        self.project["history"] = self.put("history.json", {"partial": self.owner_record(
            status="RESOLVED", areas=("visual",), at="2026-11-14T12:00:00+00:00")})
        self.save_registry([self.project])
        with patch.object(engine, "ROOT", root):
            plan = engine.plan(self.instruction, self.workspace)
        self.assertTrue(plan["owner_revision_active"])
        self.assertEqual(plan["discovery"]["current_owner_revision"]["required_changes"], ["narration"])
        self.project["history"] = self.put("history.json", {"new": self.owner_record(
            areas=("rights",), at="2026-11-14T12:00:00+00:00")})
        self.save_registry([self.project])
        with patch.object(engine, "ROOT", root):
            plan = engine.plan(self.instruction, self.workspace)
        self.assertEqual(set(plan["discovery"]["current_owner_revision"]["required_changes"]), {"narration", "visual", "rights"})

    def test_history_metadata_does_not_require_unrelated_historical_media(self):
        root = self.pinned_history()
        self.project["history"] = self.put("history.json", {"unrelated": {"title": "Unrelated old book",
            "result": {"path": "/unavailable-old-device/private-media.json", "sha256": "f" * 64}}})
        self.save_registry([self.project])
        with patch.object(engine, "ROOT", root):
            plan = engine.plan(self.instruction, self.workspace)
        self.assertTrue(plan["owner_revision_active"])
        self.assertEqual(plan["discovery"]["current_owner_revision"]["status"], "ACTIVE")

    def test_manifest_commands_and_completion_labels_cannot_create_pass(self):
        self.project["stages"]["source"]["command"] = "do arbitrary work"
        self.save_registry([self.project])
        with self.assertRaisesRegex(ValueError, "commands"):
            engine.plan(self.instruction, self.workspace)
        self.project["stages"]["source"].pop("command")
        self.save_registry([self.project])
        with patch.object(engine, "_dispatch", return_value={"status": "PASS", "artifacts": [], "acceptance": {"release_approved": True}}):
            report = engine.run(self.instruction, self.workspace, execute=True)
        self.assertFalse(report["production_ready"])
        self.assertIn("unknown status", report["blockers"][0])

    def runtime(self):
        started = time.time() - 10
        deadline = started + 2700
        outer = {"schema": engine.RUNTIME_SCHEMA, "owner_authorized": True, "project_id": "story",
                 "scope_ref": "software-runtime-fixture-only", "evidence_ref": "not actual spending approval",
                 "allocation_started_at": started, "original_deadline_epoch": deadline,
                 "observed_units_per_hour": 1, "approved_compute_units": 2,
                 "free_runtime_confirmed": False, "max_model_stage_starts": 1,
                 "purchases_allowed": False, "publication_allowed": False}
        ref = self.put("runtime.json", outer)
        child = self.put("worker-authority.json", {"allocation_started_at": started, "original_deadline_epoch": deadline})
        self.project["stages"]["narration"]["job"] = self.put("control-voice-job.json", {
            "purpose": self.project.get("purpose", "production"), "language": "en", "source": self.source})
        observations = {"shutdown_guard_armed": True, "allocation_started_at": started, "original_deadline_epoch": deadline}
        return outer, ref, child, observations

    def test_original_clock_guard_and_shared_reserved_start_cannot_reset(self):
        outer, authority, child, observations = self.runtime()
        self.project["stages"]["narration"].update(kind="trained-voice", authority=child)
        self.project["stages"]["visuals"].update(kind="wan-batch", authority=child)
        self.save_registry([self.project])
        no_guard = dict(observations, shutdown_guard_armed=False)
        with self.assertRaisesRegex(ValueError, "timer"):
            self.run_fixture(authority_path=authority["path"], runtime_context=no_guard)
        first = self.run_fixture(authority_path=authority["path"], runtime_context=observations)
        self.assertEqual(first["model_stage_dispatch_reservations_total"], 1)
        self.assertIn("allowance spent", first["blockers"][0])
        # An updated authority carrying the SAME scope cannot reset its counter.
        outer["max_model_stage_starts"] = 2
        authority = self.put("runtime.json", outer)
        again = self.run_fixture(authority_path=authority["path"], runtime_context=observations)
        self.assertIn("cannot reset", again["blockers"][0])
        self.assertFalse(again["production_ready"])

    def test_unused_other_stage_budget_is_not_a_failed_voice_retry(self):
        outer, authority, child, observations = self.runtime()
        outer["max_model_stage_starts"] = 2
        authority = self.put("runtime.json", outer)
        self.project["stages"]["narration"].update(kind="trained-voice", authority=child)
        self.save_registry([self.project])
        def fail(stage, spec, context):
            if stage == "narration":
                raise RuntimeError("unknown model outcome; synthetic control test only")
            return self.adapter(stage, spec, context)
        with patch.object(engine, "_dispatch", side_effect=fail), \
             patch("scripts.earnalism_voice.validate_job", side_effect=lambda path: {"job": engine._load(Path(path))}):
            engine.run(self.instruction, self.workspace, execute=True,
                       authority_path=authority["path"], runtime_context=observations)
        self.project["stages"]["narration"]["job"] = self.put("changed-voice-job.json", {
            "changed": "test settings", "purpose": "production", "language": "en", "source": self.source})
        self.save_registry([self.project])
        self.calls.clear()
        retry = self.run_fixture(authority_path=authority["path"], runtime_context=observations)
        self.assertEqual(self.calls, [])
        self.assertIn("unused other-stage allowance is not a retry", retry["blockers"][0])

    def test_new_scope_reuses_verified_voice_instead_of_regenerating_it(self):
        outer, authority, child, observations = self.runtime()
        self.project["stages"]["narration"].update(kind="trained-voice", authority=child)
        self.project["stages"]["visuals"].update(kind="wan-batch", authority=child)
        self.save_registry([self.project])
        self.run_fixture(authority_path=authority["path"], runtime_context=observations)
        outer["scope_ref"] = "new-software-test-grant-no-real-spending-authority"
        authority = self.put("runtime-next.json", outer)
        self.calls.clear()
        result = self.run_fixture(authority_path=authority["path"], runtime_context=observations)
        self.assertIn("narration", result["reused_stages"])
        self.assertNotIn("narration", self.calls)
        self.assertIn("visuals", result["executed_stages"])

    def test_expired_allocation_cannot_enter_any_execution_stage(self):
        outer, authority, child, observations = self.runtime()
        outer["allocation_started_at"] = time.time() - 3000
        outer["original_deadline_epoch"] = outer["allocation_started_at"] + 2700
        authority = self.put("runtime.json", outer)
        observations.update(allocation_started_at=outer["allocation_started_at"],
                            original_deadline_epoch=outer["original_deadline_epoch"])
        with self.assertRaisesRegex(ValueError, "expired"):
            self.run_fixture(authority_path=authority["path"], runtime_context=observations)
        self.assertEqual(self.calls, [])

    def test_production_cannot_dispatch_a_partial_qualification_job(self):
        outer, authority, child, observations = self.runtime()
        self.project["stages"]["narration"].update(kind="trained-voice", authority=child,
            job=self.put("audition-job.json", {"purpose": "qualification", "language": "en", "source": self.source}))
        self.save_registry([self.project])
        with patch.object(engine, "_dispatch", side_effect=self.adapter), \
             patch("scripts.earnalism_voice.validate_job", side_effect=AssertionError("Purpose mismatch must stop first")) as validate:
            report = engine.run(self.instruction, self.workspace, execute=True,
                                authority_path=authority["path"], runtime_context=observations)
        validate.assert_not_called()
        self.assertEqual(self.calls, ["source"])
        self.assertEqual(report["model_stage_dispatch_reservations_total"], 0)
        self.assertIn("purpose/language", report["blockers"][0])
        self.assertFalse(report["production_ready"])

    def test_full_source_voice_validation_precedes_any_model_reservation(self):
        outer, authority, child, observations = self.runtime()
        self.project["stages"]["narration"].update(kind="trained-voice", authority=child)
        self.save_registry([self.project])
        with patch.object(engine, "_dispatch", side_effect=self.adapter), \
             patch("scripts.earnalism_voice.validate_job", side_effect=ValueError("Full source coverage missing")) as validate:
            report = engine.run(self.instruction, self.workspace, execute=True,
                                authority_path=authority["path"], runtime_context=observations)
        validate.assert_called_once()
        self.assertEqual(self.calls, ["source"])
        self.assertEqual(report["model_stage_dispatch_reservations_total"], 0)
        self.assertIn("Full source coverage", report["blockers"][0])

    def test_qualification_project_stops_at_voice_without_fullbook_timing(self):
        self.project["purpose"] = "qualification"
        outer, authority, child, observations = self.runtime()
        self.project["stages"]["narration"].update(kind="trained-voice", authority=child)
        self.project["stages"] = {k: v for k, v in self.project["stages"].items() if k in {"source", "narration"}}
        self.save_registry([self.project])
        self.assertEqual(engine.plan(self.instruction, self.workspace)["state"], "PRIVATE_EXECUTION_PREPARED")
        report = self.run_fixture(authority_path=authority["path"], runtime_context=observations)
        self.assertEqual(report["executed_stages"], ["source", "narration"])
        self.assertEqual(report["state"], "QUALIFICATION_READY_FURTHER_QA")
        self.assertFalse(report["production_ready"])
        self.assertNotIn("timing", self.calls)

    def test_qualified_profile_cannot_launder_audition_as_retained_fullbook(self):
        audio = self.put("audition.wav", "OPAQUE SOFTWARE FIXTURE; rejection precedes audio decoding")
        profile = self.put("profile.json", {"identity": "TheEarnalismVoice"})
        receipt = self.put("audition-result.json", {"purpose": "qualification",
            "source_coverage": "SELECTED_EXACT_SOURCE_SPANS_NOT_FULL_TITLE",
            "profile_sha256": profile["sha256"], "checkpoint_sha256": "3" * 64,
            "source_sha256": self.source["sha256"], "outputs": [audio]})
        context = {"workspace": str(self.workspace.resolve()), "language": "en",
                   "upstream": {"source": {"details": {"bindings": {"manuscript": self.source}}}}}
        with patch("scripts.earnalism_voice.inspect_profile", return_value={"status": "QUALIFIED",
                   "production_accepted": True, "checkpoint_sha256": "3" * 64}), \
             patch("scripts.earnalism_voice.render", side_effect=AssertionError("No model operation")):
            with self.assertRaisesRegex(ValueError, "lineage"):
                engine._narration({"kind": "retained-narration", "audio": audio, "profile": profile,
                                   "provenance": receipt}, context)

    def test_lossless_native_master_keeps_every_unit_and_source_order(self):
        output = self.workspace / "voice"
        output.mkdir()
        outputs = []
        expected = b""
        for i, values in enumerate(((0.0, .1, -.1), (.2, 0.0))):
            data = struct.pack("<" + "f" * len(values), *values)
            path = output / f"u{i}.wav"
            header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
            header += struct.pack("<IHHIIHH", 16, 3, 1, 44100, 176400, 4, 32)
            path.write_bytes(header + b"data" + struct.pack("<I", len(data)) + data)
            outputs.append({"unit": f"u{i}", "path": path.name, "sha256": engine._sha(path),
                            "bytes": path.stat().st_size, "frames": len(values), "token_cap_reached": False,
                            "source_start": i, "source_end": i + 1})
            expected += data
        result = {"source_sha256": "1" * 64, "profile_sha256": "2" * 64,
                  "checkpoint_sha256": "3" * 64, "outputs": outputs}
        master, artifacts = engine._voice_master(result, output, self.workspace)
        self.assertEqual(Path(master["path"]).read_bytes()[44:], expected)
        trace = engine._load(output / "narration-master-provenance.json")
        self.assertEqual(trace["unit_order"], ["u0", "u1"])
        self.assertEqual(trace["join_naturalness"], "UNPERFORMED")
        self.assertFalse(trace["production_accepted"])
        self.assertGreater(len(artifacts), 2)

    def test_completed_native_voice_recovers_only_local_master_after_scope_closes(self):
        output = self.workspace / "completed-native"
        output.mkdir()
        samples = struct.pack("<ff", .1, -.1)
        native = output / "unit.wav"
        header = b"RIFF" + struct.pack("<I", 36 + len(samples)) + b"WAVEfmt "
        header += struct.pack("<IHHIIHH", 16, 3, 1, 44100, 176400, 4, 32)
        native.write_bytes(header + b"data" + struct.pack("<I", len(samples)) + samples)
        # A prior controller derivative is incomplete; preserve it unchanged.
        partial = output / "narration-master.wav"
        partial.write_bytes(b"INTERRUPTED LOCAL COPY; NOT NATIVE MODEL OUTPUT")
        source = self.put("recovery-source.txt", "Synthetic source")
        job = self.put("recovery-job.json", {"source": source})
        result = {"source_sha256": source["sha256"], "profile_sha256": "2" * 64,
                  "checkpoint_sha256": "3" * 64, "outputs": [{"unit": "unit", "path": native.name,
                  "sha256": engine._sha(native), "frames": 2, "token_cap_reached": False,
                  "source_start": 0, "source_end": 16}]}
        (output / "RESULT.json").write_text(json.dumps(result))
        state = {"attempts": [{"stage": "narration", "output_dir": str(output),
                               "status": "FAILED_OR_UNKNOWN_NO_REPLAY"}]}
        context = {"workspace": str(self.workspace.resolve()), "run_root": str(self.workspace / "runs/story"),
                   "upstream": {"source": {"details": {"bindings": {"manuscript": source}}}},
                   "owner_narration_hold": False}
        with patch("scripts.earnalism_voice.verify_retained", return_value=result) as verify, \
             patch("subprocess.Popen", side_effect=AssertionError("No model or setup during local recovery")):
            recovered = engine._recover_voice({"job": job}, state, context, "f" * 64)
        verify.assert_called_once()
        self.assertEqual(recovered["details"]["new_model_calls"], 0)
        master = Path(recovered["details"]["bindings"]["narration"]["path"])
        self.assertEqual(master.read_bytes()[44:], samples)
        self.assertEqual(partial.read_bytes(), b"INTERRUPTED LOCAL COPY; NOT NATIVE MODEL OUTPUT")


if __name__ == "__main__":
    unittest.main()
