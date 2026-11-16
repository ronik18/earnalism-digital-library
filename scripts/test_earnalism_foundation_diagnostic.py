"""Synthetic diagnostic-controller checks; no ML, provider or real authority.

The fixture patches only the frozen packet digests to generated test data. Its
blank PCM is not a human recording, its text is invented and its authorities
are explicitly fake. The native subprocess is replaced before any launch.
"""
import ast
import builtins
from contextlib import ExitStack, redirect_stdout
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch
import wave

from scripts import build_earnalism_orchestrator_colab as builder
from scripts import earnalism_foundation_diagnostic as diagnostic
from scripts import earnalism_orchestrator as engine
from scripts import earnalism_voice as voice


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return path


class FrozenFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="foundation-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.workspace = self.root / "private"
        self.workspace.mkdir()
        self.packet = self.workspace / "synthetic-packet"
        self.inputs = self.packet / "inputs"
        self.inputs.mkdir(parents=True)
        first, second = "First synthetic sentence. ", "Second invented sentence."
        text = first + second
        (self.inputs / "two-scenes.spoken.txt").write_text(text)
        reference = self.inputs / "full-original-clip2.wav"
        with wave.open(str(reference), "wb") as wav:
            wav.setparams((1, 2, 16000, 76800, "NONE", "not compressed"))
            wav.writeframes(b"\0" * (76800 * 2))
        self.units = []
        for number, start, end in [(1, 0, len(first)), (2, len(first), len(text))]:
            self.units.append({"id": "synthetic-scene-" + str(number), "start": start,
                "end": end, "spoken_text": text[start:end],
                "caption_unspoken": "Invented test direction " + str(number),
                "seed": 100 + number})
        self.base = {"model_id": "synthetic-test-only", "revision": "a" * 40,
                     "sha256": "b" * 64}
        self.generation = {"do_sample": True, "temperature": 1.0, "top_k": 50,
                           "top_p": 1.0, "max_new_tokens": 8000}
        self.bounds = {"max_audio_seconds": 180, "max_output_bytes": 33554432}
        job = {"schema": "earnalism.voice_job.v1", "language": "en",
               "purpose": "qualification", "generation": self.generation,
               "limits": self.bounds, "units": [dict(u, context="Unspoken test context")
                                                  for u in self.units]}
        write_json(self.inputs / "adapted-job.original.json", job)
        write_json(self.inputs / "adapted-profile.original.json", {"base": self.base})
        for name in diagnostic.INPUTS:
            target = self.inputs / name
            if not target.exists():
                write_json(target, {"synthetic_test_only": True, "fixture": name})
        planned = [dict(u, planned_binding_sha256=diagnostic.canonical(u)) for u in self.units]
        self.proposal = {"schema": "earnalism.controlled_voice_repair_proposal.v1",
            "id": "synthetic-foundation-fixture", "execution": {"enabled": False,
                "allocation_allowed": False, "model_loading_allowed": False,
                "generation_allowed": False, "training_allowed": False,
                "downloads_allowed": False, "purchases_allowed": False,
                "publication_allowed": False}, "runtime_authority": None,
            "reference": {"path": "inputs/full-original-clip2.wav", "sha256": digest(reference),
                "waveform_conditioning": False, "speaker_transfer": False, "training_input": False},
            "comparison": {"proposed_foundation": {"identity": diagnostic.IDENTITY,
                "base": self.base, "generation": self.generation,
                "native_output_bounds": self.bounds, "units": planned},
                "historical_adapted": {"outputs": []}},
            "future_comparability_requirements": {"synthetic_test_only": True},
            "preservation": {"soundtrack_and_selected_style": []}}
        self.proposal_path = write_json(self.packet / "PROPOSAL.NOT-AUTHORITY.json", self.proposal)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(diagnostic, "PROPOSAL_SHA256", digest(self.proposal_path)))
        self.stack.enter_context(patch.object(diagnostic, "INPUTS",
            {name: digest(self.inputs / name) for name in diagnostic.INPUTS}))
        original_import = builtins.__import__
        def no_model_import(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "parler_tts", "numpy",
                                      "torchaudio", "soundfile"}:
                raise AssertionError("ML import is forbidden in controller fixtures: " + name)
            return original_import(name, *args, **kwargs)
        self.stack.enter_context(patch("builtins.__import__", side_effect=no_model_import))

    def frozen(self):
        return diagnostic.validate(self.proposal_path, self.workspace)

    def authority(self, **changes):
        now = time.time()
        value = {"schema": engine.RUNTIME_SCHEMA, "project_id": self.proposal["id"],
            "owner_authorized": True, "scope_ref": "SYNTHETIC_TEST_ONLY_NOT_AUTHORITY",
            "evidence_ref": "SYNTHETIC_TEST_ONLY", "purchases_allowed": False,
            "publication_allowed": False, "allocation_started_at": now - 1,
            "original_deadline_epoch": now + 60, "observed_units_per_hour": 0,
            "approved_compute_units": 0, "free_runtime_confirmed": True,
            "max_model_stage_starts": 1,
            "stage_attempt_limits": {diagnostic.OPERATION: 1},
            "foundation_diagnostic": {"purpose": "INTENTIONALLY_INVALID_TEST_SCOPE"}}
        value.update(changes)
        path = write_json(self.workspace / ("fake-scope-" + str(time.time_ns()) + ".json"), value)
        context = {"shutdown_guard_armed": True,
            "allocation_started_at": value["allocation_started_at"],
            "original_deadline_epoch": value["original_deadline_epoch"]}
        return path, context

    def fake_native(self, argv, **kwargs):
        """No process exists: write two labelled dummy artifacts in the fixture."""
        output = Path(argv[-1])
        self.assertEqual(argv[1:3], ["-I", "-B"])
        self.assertTrue(kwargs["env"]["HF_HUB_OFFLINE"] == "1")
        frozen = self.frozen()
        artifacts = []
        for unit, fingerprint in zip(self.units, frozen["unit_fingerprints"]):
            audio = output / (unit["id"] + ".wav")
            audio.write_bytes(b"SYNTHETIC ARTIFACT ONLY; NOT SPEECH: " + unit["id"].encode())
            trace = write_json(output / (unit["id"] + ".trace.json"), {"synthetic_test_only": True})
            trace_ref = {"path": trace.name, "bytes": trace.stat().st_size, "sha256": digest(trace)}
            artifacts.append({"unit": unit["id"], "fingerprint": fingerprint,
                "path": audio.name, "bytes": audio.stat().st_size, "sha256": digest(audio),
                "trace": trace_ref})
        write_json(output / "RESULT.json", {"schema": "earnalism.foundation_diagnostic_result.v1",
            "identity": diagnostic.IDENTITY, "experiment_sha256": frozen["experiment_sha256"],
            "state": "SYNTHETIC_TEST_RESULT_NOT_SPEECH", "production_ready": False,
            "qualification_ready": False, "outputs": artifacts})
        return Mock(wait=Mock(return_value=0))

    def fake_execution(self):
        selected = {"runtime_interpreter": {"path": "/SYNTHETIC-NOT-AN-EXECUTABLE/python"}}
        stack = ExitStack()
        stack.enter_context(patch.object(diagnostic, "_authority", return_value=selected))
        process = stack.enter_context(patch.object(diagnostic.subprocess, "Popen", side_effect=self.fake_native))
        # The fake process has no process group; never send a real signal in tests.
        stopped = stack.enter_context(patch.object(voice, "_stop_owned_group"))
        return stack, process, stopped

    def test_dry_route_does_not_touch_native_authority_journals_or_counters(self):
        with patch.object(diagnostic, "render", side_effect=AssertionError("native forbidden")) as native, \
             patch.object(engine, "_runtime", side_effect=AssertionError("authority forbidden")), \
             patch.object(engine, "_reserve_model", side_effect=AssertionError("counter forbidden")):
            result = engine.diagnose_foundation(self.proposal_path, self.workspace)
        native.assert_not_called()
        self.assertFalse((self.workspace / ".orchestrator").exists())
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["qualification_ready"])
        self.assertFalse(result["narration_bindings"])
        self.assertIsNone(result["runtime_authority"])
        self.assertEqual(result["proposed_generation_calls"], 2)

    def test_every_packaged_input_and_proposal_are_frozen(self):
        for target in [self.proposal_path, *sorted(self.inputs.iterdir())]:
            original = target.read_bytes()
            try:
                target.write_bytes(original + b"CHANGED")
                with self.subTest(name=target.name), self.assertRaises(ValueError):
                    self.frozen()
            finally:
                target.write_bytes(original)
        self.frozen()

    def test_scene_seed_caption_source_and_reference_role_cannot_drift(self):
        for field, changed in [("seed", 999), ("caption_unspoken", "Another direction"),
                               ("spoken_text", "Different spoken content"), ("start", 1)]:
            value = copy.deepcopy(self.proposal)
            value["comparison"]["proposed_foundation"]["units"][0][field] = changed
            write_json(self.proposal_path, value)
            with self.subTest(field=field), patch.object(diagnostic, "PROPOSAL_SHA256", digest(self.proposal_path)):
                with self.assertRaisesRegex(ValueError, "source spans|captions|seeds"):
                    self.frozen()
        for field in ("waveform_conditioning", "speaker_transfer", "training_input"):
            value = copy.deepcopy(self.proposal)
            value["reference"][field] = True
            write_json(self.proposal_path, value)
            with self.subTest(field=field), patch.object(diagnostic, "PROPOSAL_SHA256", digest(self.proposal_path)):
                with self.assertRaisesRegex(ValueError, "human comparator"):
                    self.frozen()

    def test_missing_expired_and_wrong_scope_cannot_launch_native(self):
        with patch.object(diagnostic, "render", side_effect=AssertionError("native forbidden")) as native:
            with self.assertRaisesRegex(ValueError, "Fresh guarded"):
                engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True)
            expired, context = self.authority(allocation_started_at=time.time() - 100,
                                              original_deadline_epoch=time.time() - 10)
            with self.assertRaisesRegex(ValueError, "clock|expired"):
                engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True,
                    authority_path=expired, runtime_context=context)
            wrong, context = self.authority()
            with self.assertRaisesRegex(ValueError, "Fresh exact diagnostic scope"):
                engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True,
                    authority_path=wrong, runtime_context=context)
        native.assert_not_called()
        self.assertFalse((self.workspace / ".orchestrator/diagnostics.jsonl").exists())
        self.assertFalse((self.workspace / ".orchestrator/authorities").exists())

    def test_diagnostic_scope_cannot_reserve_a_production_stage(self):
        for marker in [{}, None, {"purpose": "private-diagnostic"}]:
            with self.subTest(marker=marker):
                value = {"foundation_diagnostic": marker}
                for stage in ("narration", "visuals"):
                    with self.assertRaisesRegex(ValueError, "cannot substitute"):
                        engine._reserve_model(value, stage, "f" * 64, self.workspace)
        self.assertFalse((self.workspace / ".orchestrator/authorities").exists())

    def test_production_scope_cannot_reserve_a_diagnostic_operation(self):
        with self.assertRaisesRegex(ValueError, "cannot substitute"):
            engine._reserve_model({}, diagnostic.OPERATION, "f" * 64, self.workspace)
        self.assertFalse((self.workspace / ".orchestrator/authorities").exists())

    def test_two_fake_outputs_use_one_reservation_and_verified_reuse_not_replay(self):
        authority, context = self.authority()
        stack, native, stopped = self.fake_execution()
        with stack:
            result = engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True,
                authority_path=authority, runtime_context=context)
            self.assertEqual(native.call_count, 1)
            self.assertEqual(len(result["outputs"]), 2)
            self.assertFalse(result["production_ready"])
            self.assertFalse(result["qualification_ready"])
            self.assertNotIn("bindings", result)
            renamed = self.packet / "RENAMED-PROPOSAL.json"
            renamed.write_bytes(self.proposal_path.read_bytes())
            fresh, fresh_context = self.authority(scope_ref="SECOND_FAKE_SCOPE_NO_NEW_PERMISSION")
            retained = engine.diagnose_foundation(renamed, self.workspace, execute=True,
                authority_path=fresh, runtime_context=fresh_context)
            self.assertTrue(retained["retained_verified"])
            self.assertEqual(native.call_count, 1)
        self.assertEqual(stopped.call_count, 1)
        ledgers = list((self.workspace / ".orchestrator/authorities").glob("*.json"))
        self.assertEqual(len(ledgers), 1)
        starts = json.loads(ledgers[0].read_text())["starts"]
        self.assertEqual(len(starts), 1)
        self.assertEqual(starts[0]["stage"], diagnostic.OPERATION)
        journal = [json.loads(line) for line in
                   (self.workspace / ".orchestrator/diagnostics.jsonl").read_text().splitlines()]
        self.assertEqual([e["event"] for e in journal], ["foundation_intent", "foundation_completed"])
        self.assertFalse((self.workspace / ".orchestrator/projects").exists())

    def test_unknown_native_attempt_stays_consumed_after_rename_and_fresh_scope(self):
        authority, context = self.authority()
        stack, native, _ = self.fake_execution()
        with stack:
            native.side_effect = RuntimeError("SYNTHETIC UNKNOWN BEFORE RETURN")
            with self.assertRaisesRegex(RuntimeError, "SYNTHETIC UNKNOWN"):
                engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True,
                    authority_path=authority, runtime_context=context)
            renamed = self.packet / "ANOTHER-NAME.json"
            renamed.write_bytes(self.proposal_path.read_bytes())
            fresh, fresh_context = self.authority(scope_ref="FRESH_FAKE_SCOPE_STILL_NO_REPLAY")
            with self.assertRaisesRegex(ValueError, "Consumed or unknown"):
                engine.diagnose_foundation(renamed, self.workspace, execute=True,
                    authority_path=fresh, runtime_context=fresh_context)
            self.assertEqual(native.call_count, 1)
        output = diagnostic.result_directory(self.frozen(), self.workspace)
        self.assertEqual(json.loads((output / "FAILURE.json").read_text())["state"],
                         "FAILED_OR_UNKNOWN_NO_REPLAY")

    def test_mutated_completed_artifact_cannot_be_reused_or_regenerated(self):
        authority, context = self.authority()
        stack, native, _ = self.fake_execution()
        with stack:
            result = engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True,
                authority_path=authority, runtime_context=context)
            output = diagnostic.result_directory(self.frozen(), self.workspace)
            (output / result["outputs"][0]["path"]).write_bytes(b"MUTATED TEST ARTIFACT")
            with self.assertRaisesRegex(ValueError, "artifact changed"):
                engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True)
            self.assertEqual(native.call_count, 1)

    def test_worker_admission_accepts_timestamped_original_intent_but_not_duplicate(self):
        frozen = self.frozen()
        authority, context = self.authority()
        output = diagnostic.result_directory(frozen, self.workspace)
        output.mkdir(parents=True)
        intent = {"proposal_sha256": frozen["proposal_sha256"],
            "experiment_sha256": frozen["experiment_sha256"],
            "authority_sha256": digest(authority), "parent_pid": os.getppid(),
            "runtime_context": context, "original_deadline": context["original_deadline_epoch"]}
        write_json(output / "INTENT.json", intent)
        journal = self.workspace / ".orchestrator/diagnostics.jsonl"
        voice._append(journal, {"event": "foundation_intent", **intent})
        recorded = json.loads(journal.read_text())
        self.assertIn("at_epoch", recorded)
        with patch.object(engine, "_runtime", side_effect=RuntimeError("ADMISSION_REACHED_NO_RUNTIME")) as runtime, \
             patch.object(voice, "_arm_child_containment", side_effect=AssertionError("containment forbidden")):
            with self.assertRaisesRegex(RuntimeError, "ADMISSION_REACHED_NO_RUNTIME"):
                diagnostic._worker(self.proposal_path, self.workspace, authority, output)
            runtime.assert_called_once()
            runtime.reset_mock()
            voice._append(journal, {"event": "foundation_intent", **intent})
            with self.assertRaisesRegex(ValueError, "One original journal"):
                diagnostic._worker(self.proposal_path, self.workspace, authority, output)
            runtime.assert_not_called()
        self.assertFalse((output / "WORKER-INTENT.json").exists())

    def test_diagnostic_output_symlink_escape_stops_before_intent_or_model(self):
        outside = self.root / "outside-private-workspace"
        outside.mkdir()
        (self.workspace / ".orchestrator").mkdir()
        (self.workspace / ".orchestrator/diagnostics").symlink_to(outside, target_is_directory=True)
        with patch.object(diagnostic, "render", side_effect=AssertionError("native forbidden")) as native, \
             patch.object(engine, "_runtime", side_effect=AssertionError("runtime forbidden")) as runtime, \
             patch.object(engine, "_reserve_model", side_effect=AssertionError("reservation forbidden")) as reserve:
            with self.assertRaisesRegex(ValueError, "stay private"):
                engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True)
        native.assert_not_called()
        runtime.assert_not_called()
        reserve.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.workspace / ".orchestrator/diagnostics.jsonl").exists())

    def test_reservation_only_crash_remains_consumed_under_fresh_scope(self):
        authority, context = self.authority()
        with patch.object(diagnostic, "_authority", return_value={}) as admit, \
             patch.object(diagnostic, "render", side_effect=RuntimeError("SYNTHETIC RESERVE-ONLY CRASH")) as native:
            with self.assertRaisesRegex(RuntimeError, "RESERVE-ONLY CRASH"):
                engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True,
                    authority_path=authority, runtime_context=context)
            self.assertFalse((self.workspace / ".orchestrator/diagnostics.jsonl").exists())
            self.assertFalse(diagnostic.result_directory(self.frozen(), self.workspace).exists())
            ledgers = list((self.workspace / ".orchestrator/authorities").glob("*.json"))
            self.assertEqual(len(ledgers), 1)
            before = ledgers[0].read_bytes()
            starts = json.loads(before)["starts"]
            self.assertEqual(len(starts), 1)
            self.assertEqual(starts[0]["fingerprint"], self.frozen()["experiment_sha256"])
            fresh, fresh_context = self.authority(scope_ref="NEW_FAKE_SCOPE_AFTER_RESERVATION_CRASH")
            with self.assertRaisesRegex(ValueError, "Consumed or unknown"):
                engine.diagnose_foundation(self.proposal_path, self.workspace, execute=True,
                    authority_path=fresh, runtime_context=fresh_context)
            self.assertEqual(native.call_count, 1)
            self.assertEqual(admit.call_count, 1)
        self.assertEqual(ledgers[0].read_bytes(), before)
        self.assertEqual(len(list((self.workspace / ".orchestrator/authorities").glob("*.json"))), 1)

    def real_admission_fixture(self):
        """Materialized fake bytes plus pure bootstrap text; never executable code."""
        helper = voice._owned_provider_helper()
        source = self.workspace / "synthetic-source"
        for name in diagnostic.SOFTWARE:
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# synthetic source fixture; not imported\n")
        self.stack.enter_context(patch.object(diagnostic, "ROOT", source))
        binaries = self.workspace / "fake-binaries"
        binaries.mkdir()
        target = binaries / "python3.12"
        target.write_bytes(b"FAKE TEST INTERPRETER BYTES; NEVER EXECUTE\n")
        target.chmod(0o700)
        environment = self.workspace / "fake-runtime"
        launcher = environment / "bin/python"
        launcher.parent.mkdir(parents=True)
        launcher.symlink_to(target)
        library = self.workspace / "fake-provider/libcuda.so.1"
        library.parent.mkdir()
        library.write_bytes(b"FAKE PROVIDER LIBRARY; NEVER DLOPEN\n")
        library_ref = {"path": str(library), "bytes": library.stat().st_size, "sha256": digest(library)}
        bootstrap = environment / "lib/python3.12/site-packages/sitecustomize.py"
        bootstrap.parent.mkdir(parents=True)
        bootstrap.write_text(helper.render_preload_source(library_ref))
        preload = {"synthetic_test_only": True, "explicit_bootstrap_mode": helper.EXPLICIT_MODE,
            "explicit_module_name": helper.OWNED_MODULE, "provider_binding": {
                "library_family": "CUDA_DRIVER", "soname": "libcuda.so.1", "library": library_ref},
            "bootstrap": {"path": str(bootstrap)}}
        preload_path = write_json(self.workspace / "synthetic-provider-preload.json", preload)
        preserved = []
        for number in range(4):
            path = self.workspace / ("synthetic-preserved-" + str(number) + ".bin")
            path.write_bytes(b"INVENTED PRESERVED MEDIA FIXTURE " + str(number).encode())
            preserved.append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)})
        self.proposal["comparison"]["historical_adapted"]["outputs"] = preserved[:2]
        self.proposal["preservation"]["soundtrack_and_selected_style"] = preserved[2:]
        write_json(self.proposal_path, self.proposal)
        self.stack.enter_context(patch.object(diagnostic, "PROPOSAL_SHA256", digest(self.proposal_path)))
        frozen = self.frozen()
        assets = self.workspace / "fake-assets"
        assets.mkdir()
        selected = {"operation": diagnostic.OPERATION, "purpose": "private-diagnostic",
            "proposal_sha256": frozen["proposal_sha256"], "experiment_sha256": frozen["experiment_sha256"],
            "software": diagnostic.software(), "model_loads": 1, "generation_calls": 2,
            "adapted_restores": 0, "training_updates": 0, "assets_root": str(assets),
            "provider_driver_preload": {"path": str(preload_path), "bytes": preload_path.stat().st_size,
                "sha256": digest(preload_path)},
            "runtime_interpreter": {"path": str(launcher), "resolved_path": str(target),
                "bytes": target.stat().st_size, "sha256": digest(target)},
            "preserved_media": preserved}
        envelope = write_json(self.workspace / "fake-real-admission-envelope.json", {"synthetic_test_only": True})
        runtime = {"path": str(envelope), "project_id": frozen["proposal"]["id"],
            "max_model_stage_starts": 1, "stage_attempt_limits": {diagnostic.OPERATION: 1},
            "foundation_diagnostic": selected}
        return runtime, frozen, bootstrap, preload, preload_path

    def test_real_authority_admits_exact_synthetic_scope_and_rejects_drift_without_execution(self):
        runtime, frozen, bootstrap, preload, preload_path = self.real_admission_fixture()
        # Importing the stdlib helper is inert; its renderer produces text only.
        # Even an accidental loader or subprocess call would fail this test.
        with patch("ctypes.CDLL", side_effect=AssertionError("dlopen forbidden")) as loader, \
             patch.object(diagnostic.subprocess, "Popen", side_effect=AssertionError("process forbidden")) as native:
            self.assertIs(diagnostic._authority(runtime, frozen, self.workspace), runtime["foundation_diagnostic"])
            changes = [("operation", "another-operation"), ("purpose", "production"),
                ("proposal_sha256", "c" * 64), ("experiment_sha256", "d" * 64),
                ("software", {}), ("model_loads", True), ("generation_calls", 3),
                ("adapted_restores", 1), ("training_updates", 1),
                ("assets_root", str(self.root / "outside-assets")), ("preserved_media", [])]
            for field, value in changes:
                altered = copy.deepcopy(runtime)
                altered["foundation_diagnostic"][field] = value
                with self.subTest(field=field), self.assertRaises((ValueError, voice.VoiceBlocked)):
                    diagnostic._authority(altered, frozen, self.workspace)
            for field, value in [("project_id", "another-project"), ("max_model_stage_starts", 2),
                                 ("stage_attempt_limits", {diagnostic.OPERATION: 2})]:
                altered = copy.deepcopy(runtime)
                altered[field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    diagnostic._authority(altered, frozen, self.workspace)
            altered = copy.deepcopy(runtime)
            altered["foundation_diagnostic"]["runtime_interpreter"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(voice.VoiceBlocked, "Changed local asset"):
                diagnostic._authority(altered, frozen, self.workspace)
            for kind in ("explicit-mode", "provider-family", "provider-soname"):
                changed = copy.deepcopy(preload)
                if kind == "explicit-mode":
                    changed["explicit_bootstrap_mode"] = "NOT_THE_FIXED_MODE"
                elif kind == "provider-family":
                    changed["provider_binding"]["library_family"] = "NOT_CUDA"
                else:
                    changed["provider_binding"]["soname"] = "another.so"
                path = write_json(self.workspace / ("altered-" + kind + ".json"), changed)
                altered = copy.deepcopy(runtime)
                altered["foundation_diagnostic"]["provider_driver_preload"] = {
                    "path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)}
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "Fixed explicit provider"):
                    diagnostic._authority(altered, frozen, self.workspace)
            original = bootstrap.read_bytes()
            bootstrap.write_bytes(original + b"# changed fixture\n")
            with self.assertRaisesRegex(ValueError, "Exact existing runtime bootstrap"):
                diagnostic._authority(runtime, frozen, self.workspace)
            bootstrap.write_bytes(original)
            preserved = Path(runtime["foundation_diagnostic"]["preserved_media"][3]["path"])
            preserved.write_bytes(b"CHANGED SYNTHETIC MEDIA")
            with self.assertRaisesRegex(ValueError, "Preserved original media changed"):
                diagnostic._authority(runtime, frozen, self.workspace)
        loader.assert_not_called()
        native.assert_not_called()


class DiagnosticNotebookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="foundation-notebook-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.software = self.root / "source"
        self.software.mkdir()
        for name in builder.FILES:
            target = self.software / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# synthetic public source only\n")
        runtime = self.software / "scripts/earnalism_voice_runtime"
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / "foundation.py").write_text("# synthetic diagnostic worker\n")
        (runtime / "pre_drive_loader_entry.py").write_text("def run(*args): raise AssertionError('not called')\n")
        self.notebook_path = self.root / "single-orchestrator.ipynb"
        self.receipt = builder.build(self.notebook_path, root=self.software, base_revision="a" * 40)
        self.notebook = json.loads(self.notebook_path.read_text())
        self.workspace = self.root / "private"
        self.workspace.mkdir()

    def test_existing_notebook_contains_disabled_separate_route_and_verified_source(self):
        values = {}
        for cell in self.notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertFalse(cell["outputs"])
                self.assertIsNone(cell["execution_count"])
                for node in ast.walk(ast.parse("".join(cell["source"]))):
                    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                        if node.targets[0].id in {"EXECUTE", "FOUNDATION_DIAGNOSTIC_PATH"}:
                            values[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(values, {"EXECUTE": False, "FOUNDATION_DIAGNOSTIC_PATH": ""})
        self.assertIn("scripts/earnalism_foundation_diagnostic.py", self.receipt["files"])
        self.assertIn("scripts/earnalism_voice_runtime/foundation.py", self.receipt["files"])
        self.assertEqual(builder.verify_notebook(self.notebook_path, root=self.software), self.receipt)

    def namespace(self, **overrides):
        values = {"pathlib": __import__("pathlib"), "json": json, "time": time,
            "PRIVATE_WORKSPACE": str(self.workspace), "EXECUTE": False,
            "FOUNDATION_DIAGNOSTIC_PATH": str(self.workspace / "synthetic-proposal.json"),
            "BATCH_PATH": "", "BATCH_AUTHORITIES_PATH": "", "PREPARATION_WORKERS": 3,
            "runtime_context": {}, "FEEDBACK_PATH": "", "AUTO_DISCONNECT_OWN_RUNTIME": True,
            "connect_private_workspace": lambda: (self.workspace, self.workspace / "projects.json"),
            "prepare_reviewed_software": lambda: self.software}
        values.update(overrides)
        return values

    def fake_engine(self):
        module = types.ModuleType("scripts.earnalism_orchestrator")
        module.run = Mock(side_effect=AssertionError("production route forbidden"))
        module.batch = Mock(side_effect=AssertionError("batch route forbidden"))
        module.feedback = Mock(side_effect=AssertionError("feedback route forbidden"))
        module.diagnose_foundation = Mock(return_value={"state": "SYNTHETIC_DISABLED_PLAN",
            "execution_enabled": False, "production_ready": False})
        return module

    def test_diagnostic_mode_calls_only_disabled_diagnostic_entrypoint(self):
        module = self.fake_engine()
        values = self.namespace()
        code = "".join(self.notebook["cells"][-1]["source"])
        with patch.dict(sys.modules, {"scripts.earnalism_orchestrator": module}), redirect_stdout(io.StringIO()):
            exec(compile(code, "synthetic-diagnostic-notebook", "exec"), values)
        module.diagnose_foundation.assert_called_once_with(
            Path(values["FOUNDATION_DIAGNOSTIC_PATH"]), self.workspace,
            execute=False, authority_path=None, runtime_context={})
        module.run.assert_not_called()
        module.batch.assert_not_called()
        module.feedback.assert_not_called()

    def test_batch_or_feedback_collision_stops_before_dispatch(self):
        for field in ("BATCH_PATH", "FEEDBACK_PATH"):
            module = self.fake_engine()
            values = self.namespace(**{field: "synthetic-conflicting-input.json"})
            code = "".join(self.notebook["cells"][-1]["source"])
            with self.subTest(field=field), patch.dict(sys.modules,
                    {"scripts.earnalism_orchestrator": module}), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, "Diagnostic mode"):
                    exec(compile(code, "synthetic-conflict-notebook", "exec"), values)
            module.diagnose_foundation.assert_not_called()
            module.run.assert_not_called()
            module.batch.assert_not_called()
            module.feedback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
