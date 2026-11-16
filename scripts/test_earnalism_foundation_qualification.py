"""Software/fixture qualification tests only; no actual native or model operation."""
import builtins
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import earnalism_voice as voice, earnalism_orchestrator as engine
from scripts import earnalism_foundation_qualification as q


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name).resolve()
        self.python = self.workspace / "provider-python"
        self.python.write_bytes(b"software fixture, not an interpreter"); self.python.chmod(0o700)
        self.library = self.workspace / "libcuda.so.fixture"
        self.library.write_bytes(b"software fixture, not a shared library")
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(q, "software", return_value={"fixture": "a" * 64}))
        self.stack.enter_context(patch.object(q, "PRE_STORAGE_ROOT", self.workspace / "pre-storage"))
        self.stack.enter_context(patch.object(q, "LOCAL_RUNTIME_ROOT", self.workspace / "local-runtime"))
        self.stack.enter_context(patch.object(sys, "executable", str(self.python)))
        self.stack.enter_context(patch.object(sys, "platform", "linux"))
        self.stack.enter_context(patch.object(sys, "version_info", (3, 12, 0)))
        self.stack.enter_context(patch.object(q.platform, "machine", return_value="x86_64"))
        started = time.time() - 1; deadline = started + 120
        self.context = {"shutdown_guard_armed": True, "allocation_started_at": started,
                        "original_deadline_epoch": deadline}
        provider = {**q.descriptor(self.python), "resolved_path": str(self.python)}
        self.capability = {"operation": q.OPERATION, "purpose": "private-environment-qualification",
            "request_sha256": "b" * 64, "experiment_sha256": q.EXPERIMENT_SHA256,
            "recipe_sha256": q.RECIPE_SHA256, "wheel_manifest_sha256": q.WHEELS_SHA256,
            "software": q.software(), "provider_runtime_id": "FIXTURE_NOT_ACTUAL_RUNTIME",
            "provider_python": provider, "wheelhouse": str(self.workspace / "wheelhouse"),
            "assets_root": str(self.workspace / "assets"),
            "venv": str(q.LOCAL_RUNTIME_ROOT / q.EXPERIMENT_SHA256 / "venv"),
            "preserved_media": [], **q.COUNTS}
        self.raw = {"schema": engine.RUNTIME_SCHEMA, "owner_authorized": True,
            "project_id": "fixture-project", "scope_ref": "fixture-scope", "evidence_ref": "fixture-only",
            "purchases_allowed": False, "publication_allowed": False,
            "allocation_started_at": started, "original_deadline_epoch": deadline,
            "observed_units_per_hour": 1, "approved_compute_units": 1, "free_runtime_confirmed": False,
            "max_model_stage_starts": 1, "stage_attempt_limits": {"foundation-diagnostic": 1},
            "foundation_qualification": self.capability}
        self.authority_path = self.workspace / "authority.json"
        self.save_authority()
        self.plan = {"experiment_sha256": q.EXPERIMENT_SHA256, "request_sha256": "b" * 64,
            "request_path": str(self.workspace / "request.json"),
            "frozen": {"proposal": {"id": "fixture-project"}}, "packages": {"fixture": "1"},
            "wheels": [{"bytes": 1}], "requirements": "fixture==1\n"}
        self.binding = {"schema": "earnalism.provider_driver_binding.v1",
            "state": "ACTUAL_PROVIDER_LIBRARY_RESOLVED_NOT_CUDA_QUALIFIED",
            "library_family": "CUDA_DRIVER", "soname": "libcuda.so.1",
            "library": q.descriptor(self.library), "fresh_minimalenv_GPU_qualification": False}

    def save_authority(self):
        self.authority_path.write_text(json.dumps(self.raw))
        self.runtime = {**self.raw, "path": str(self.authority_path), "sha256": q.sha(self.authority_path)}

    def pre_storage(self):
        helper = Mock()
        helper.resolve_provider_driver.return_value = self.binding
        with patch.object(voice, "_owned_provider_helper", return_value=helper):
            ref = q.pre_storage(self.runtime, self.context, q.PRE_STORAGE_ROOT)
        self.context["foundation_qualification_pre_storage"] = ref
        return helper

    def test_dry_summary_has_no_native_or_qualification_claim(self):
        with patch.object(subprocess, "Popen", side_effect=AssertionError("native call forbidden")):
            result = q.summary(self.plan)
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["runtime_qualified"])
        self.assertIsNone(result["runtime_authority"])
        self.assertEqual(result["proposed_counts"]["model_loads"], 0)

    def test_disabled_capability_denied_before_native_effect(self):
        self.raw["owner_authorized"] = False; self.save_authority()
        with patch.object(voice, "_owned_provider_helper", side_effect=AssertionError("driver forbidden")):
            with self.assertRaises(ValueError):
                q.pre_storage(self.runtime, self.context, q.PRE_STORAGE_ROOT)
        self.assertFalse(q.PRE_STORAGE_ROOT.exists())

    def test_diagnostic_marker_presence_denied_even_null(self):
        self.raw["foundation_diagnostic"] = None; self.save_authority()
        with self.assertRaises(ValueError):
            q._common(self.runtime, self.context)

    def test_boolean_count_denied(self):
        self.capability["minimal_cuda_calls"] = True; self.save_authority()
        with self.assertRaises(ValueError):
            q._common(self.runtime, self.context)

    def test_untyped_or_invalid_request_hash_denied_before_driver_lookup(self):
        for invalid in [None, 3, "not-a-hash"]:
            self.capability["request_sha256"] = invalid; self.save_authority()
            with patch.object(voice, "_owned_provider_helper", side_effect=AssertionError("driver forbidden")):
                with self.assertRaises(ValueError):
                    q.pre_storage(self.runtime, self.context, q.PRE_STORAGE_ROOT)
        self.assertFalse(q.PRE_STORAGE_ROOT.exists())

    def test_raw_original_authority_cannot_be_substituted_in_memory(self):
        self.runtime["scope_ref"] = "invented"
        with self.assertRaises(ValueError):
            q._common(self.runtime, self.context)

    def test_expired_guard_denied_before_directory(self):
        self.context["original_deadline_epoch"] = time.time() - 1
        with self.assertRaises(ValueError):
            q.pre_storage(self.runtime, self.context, q.PRE_STORAGE_ROOT)
        self.assertFalse(q.PRE_STORAGE_ROOT.exists())

    def test_prestorage_exact_status_reuses_without_driver(self):
        self.pre_storage()
        with patch.object(voice, "_owned_provider_helper", side_effect=AssertionError("no replay")):
            ref = q.pre_storage(self.runtime, self.context, q.PRE_STORAGE_ROOT)
        self.assertEqual(q.read(ref["path"])["CUDA_probe_calls"], 0)

    def test_prestorage_failure_is_consumed(self):
        helper = Mock(); helper.resolve_provider_driver.side_effect = RuntimeError("fixture failure")
        with patch.object(voice, "_owned_provider_helper", return_value=helper):
            with self.assertRaises(RuntimeError):
                q.pre_storage(self.runtime, self.context, q.PRE_STORAGE_ROOT)
        folder = q.PRE_STORAGE_ROOT / q.EXPERIMENT_SHA256
        self.assertTrue((folder / "INTENT.json").is_file())
        self.assertTrue((folder / "FAILURE.json").is_file())
        with patch.object(voice, "_owned_provider_helper", side_effect=AssertionError("no replay")):
            with self.assertRaises((ValueError, FileNotFoundError)):
                q.pre_storage(self.runtime, self.context, q.PRE_STORAGE_ROOT)

    def test_final_venv_is_fixed_local_and_fresh(self):
        self.pre_storage()
        q.authority(self.runtime, self.plan, self.workspace, self.context)
        self.capability["venv"] = str(self.workspace / "arbitrary-system-target"); self.save_authority()
        with self.assertRaises(ValueError):
            q.authority(self.runtime, self.plan, self.workspace, self.context)

    def test_driver_binding_rehashed_after_storage(self):
        self.pre_storage(); self.library.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            q.authority(self.runtime, self.plan, self.workspace, self.context)

    def test_symlink_input_and_redirected_canonical_output_denied(self):
        alias = self.workspace / "alias-python"; alias.symlink_to(self.python)
        with self.assertRaises(ValueError):
            q.exact_file({**q.descriptor(self.python), "path": str(alias)}, self.workspace)
        folder = self.workspace / ".orchestrator/qualifications"; folder.mkdir(parents=True)
        elsewhere = self.workspace / "elsewhere"; elsewhere.mkdir()
        (folder / q.EXPERIMENT_SHA256).symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaises(ValueError):
            q.result_directory(self.plan, self.workspace)

    def test_fixed_subprocess_environment_and_failed_raw_log(self):
        process = Mock(); process.wait.return_value = 9; process.poll.return_value = 9
        calls = []
        def popen(argv, **kwargs):
            kwargs["stdout"].write(b"fixture primary stderr merged with stdout\n")
            calls.append((argv, kwargs)); return process
        with patch.object(subprocess, "Popen", side_effect=popen), patch.object(voice, "_stop_owned_group"), \
             patch.dict(os.environ, {"HF_TOKEN": "DO_NOT_PASS", "SOME_SECRET": "DO_NOT_PASS"}):
            with self.assertRaises(ValueError):
                q._run([str(self.python), "-I", "-m", "pip", "check"], self.workspace / "step.log",
                       self.runtime, self.context)
        self.assertNotIn("HF_TOKEN", calls[0][1]["env"])
        self.assertNotIn("SOME_SECRET", calls[0][1]["env"])
        self.assertEqual(calls[0][1]["env"]["CUDA_VISIBLE_DEVICES"], "")
        self.assertEqual(calls[0][1]["stdin"], subprocess.DEVNULL)
        self.assertTrue(calls[0][1]["start_new_session"])
        self.assertIn("primary stderr", (self.workspace / "step.log").read_text())
        self.assertEqual(q.read(self.workspace / "step.log.failure.json")["exit_code"], 9)

    def test_subprocess_timeout_retains_primary_log(self):
        process = Mock(); process.wait.side_effect = subprocess.TimeoutExpired(["fixture"], 1)
        process.poll.return_value = None
        def popen(argv, **kwargs):
            kwargs["stdout"].write(b"partial fixture log\n"); return process
        with patch.object(subprocess, "Popen", side_effect=popen), patch.object(voice, "_stop_owned_group"):
            with self.assertRaises(subprocess.TimeoutExpired):
                q._run([str(self.python), "-I"], self.workspace / "timeout.log", self.runtime, self.context)
        self.assertEqual(q.read(self.workspace / "timeout.log.failure.json")["error_type"], "TimeoutExpired")

    def test_mocked_complete_flow_creates_only_evidence_not_authority_or_model(self):
        self.pre_storage(); original_authority = self.authority_path.read_bytes()
        def run(argv, log, runtime, context, **kwargs):
            Path(log).write_text("FIXTURE: no command executed\n")
            if "venv" in argv:
                venv = Path(argv[-1]); (venv / "bin").mkdir(parents=True)
                shutil.copyfile(self.python, venv / "bin/python")
                (venv / "lib/python3.12/site-packages").mkdir(parents=True)
            if "_probe" in argv:
                q.write(Path(argv[-1]).parent / "CUDA-PROBE.json", {
                    "state": "ACTUAL_TINY_CUDA_OPERATION_PASSED_NOT_MODEL_QUALIFIED", "sum": 5.0, "model_loads": 0})
            return {"fixture": True}
        helper = Mock()
        def install(binding, site, output):
            bootstrap = site / "sitecustomize.py"; bootstrap.write_text("# fixture only\n")
            value = {"provider_binding": binding, "bootstrap": q.descriptor(bootstrap)}
            q.write(output / "PROVIDER-DRIVER-PRELOAD.json", value); return value
        helper.install_preload.side_effect = install
        with patch.object(q, "_run", side_effect=run) as runner, \
             patch.object(q, "_verify_inputs", return_value={"fixture": True}), \
             patch.object(q.shutil, "disk_usage", return_value=types.SimpleNamespace(total=10**11, used=0, free=10**11)), \
             patch.object(voice, "_owned_provider_helper", return_value=helper):
            result = q.qualify(self.plan, self.workspace, self.runtime, self.context)
        self.assertEqual(runner.call_count, 5)
        self.assertEqual(self.authority_path.read_bytes(), original_authority)
        self.assertEqual([result[k] for k in ("model_loads", "generation_calls", "training_updates")], [0, 0, 0])
        self.assertFalse(result["authority_created_or_modified"])
        self.assertFalse(result["diagnostic_dispatched"])
        retained = q.verify_result(self.plan, q.result_directory(self.plan, self.workspace))
        self.assertTrue(retained["status_only"])
        self.assertFalse(retained["current_runtime_admitted"])
        artifact = Path(result["actual_artifacts"][0]["path"]); artifact.write_text("tampered")
        with self.assertRaises(ValueError):
            q.verify_result(self.plan, q.result_directory(self.plan, self.workspace))

    def probe_fixture(self):
        self.pre_storage()
        self.plan["packages"] = {"fixture-package-" + str(i): "1" for i in range(111)}
        output = q.result_directory(self.plan, self.workspace); output.mkdir(parents=True)
        venv = Path(self.capability["venv"]); (venv / "bin").mkdir(parents=True)
        launcher = venv / "bin/python"; launcher.symlink_to(self.python)
        bootstrap = venv / "lib/python3.12/site-packages/sitecustomize.py"
        bootstrap.parent.mkdir(parents=True); bootstrap.write_text("# fixture bootstrap only\n")
        preload = {"bootstrap": q.descriptor(bootstrap), "provider_binding": self.binding,
                   "explicit_bootstrap_mode": "FIXTURE", "explicit_module_name": "FIXTURE"}
        probe = {"schema": "earnalism.foundation_CUDA_probe_input.v1", "software": q.software(),
            "experiment_sha256": q.EXPERIMENT_SHA256, "parent_pid": os.getppid(),
            "original_deadline_epoch": self.runtime["original_deadline_epoch"],
            "authority_path": str(self.authority_path), "authority_sha256": self.runtime["sha256"],
            "project_id": "fixture-project", "scope_ref": "fixture-scope", "runtime_context": self.context,
            "request_path": self.plan["request_path"], "workspace": str(self.workspace),
            "runtime_interpreter": {**self.capability["provider_python"], "path": str(launcher)},
            "packages": self.plan["packages"], "provider_runtime_id": self.capability["provider_runtime_id"],
            "provider_preload": preload}
        path = output / "PROBE-INPUT.json"; q.write(path, probe)
        return path, launcher

    def test_isolated_probe_preloads_before_torch_and_executes_only_one_fixture_sum(self):
        path, launcher = self.probe_fixture(); output = path.parent
        events = []
        helper = Mock(EXPLICIT_MODE="FIXTURE", OWNED_MODULE="FIXTURE")
        helper.load_exact_preload.side_effect = lambda *args: events.append("preload")
        tensor = Mock(); tensor.sum.return_value.item.return_value = 5.0
        cuda = Mock(); cuda.is_available.return_value = True; cuda.mem_get_info.return_value = (100, 200)
        cuda.get_device_name.return_value = "FIXTURE_GPU_NOT_REAL"; cuda.get_device_capability.return_value = (8, 9)
        torch = types.SimpleNamespace(cuda=cuda, tensor=Mock(return_value=tensor), float32="fixture-fp32",
            __version__="fixture", version=types.SimpleNamespace(cuda="fixture"))
        original_import = builtins.__import__
        def importer(name, *args, **kwargs):
            if name == "torch":
                self.assertEqual(events, ["preload"]); events.append("torch"); return torch
            return original_import(name, *args, **kwargs)
        with patch.object(voice, "_arm_child_containment"), patch.object(engine, "_runtime", return_value=self.runtime), \
             patch.object(sys, "executable", str(launcher)), \
             patch.object(q, "validate", return_value=self.plan), \
             patch.object(q.importlib.metadata, "version", return_value="1"), \
             patch.object(voice, "_owned_provider_helper", return_value=helper), \
             patch.object(builtins, "__import__", side_effect=importer):
            q._probe(path)
        self.assertEqual(events, ["preload", "torch"])
        torch.tensor.assert_called_once_with([2.0, 3.0], dtype="fixture-fp32", device="cuda:0")
        cuda.synchronize.assert_called_once_with(0)
        result = q.read(output / "CUDA-PROBE.json")
        self.assertEqual(result["model_loads"], 0); self.assertFalse(result["model_ready"])

    def test_probe_changed_deadline_rejected_before_child_alarm_or_ML(self):
        path, launcher = self.probe_fixture(); value = q.read(path)
        value["original_deadline_epoch"] += 60; path.write_text(json.dumps(value))
        with patch.object(voice, "_arm_child_containment") as arm, \
             patch.object(engine, "_runtime", return_value=self.runtime), \
             patch.object(sys, "executable", str(launcher)), \
             patch.object(voice, "_owned_provider_helper", side_effect=AssertionError("no ML/native preload")):
            with self.assertRaises(ValueError):
                q._probe(path)
        arm.assert_not_called()
        self.assertFalse((path.parent / "CUDA-PROBE-CLAIM.json").exists())

    def test_probe_wrong_final_venv_rejected_before_ML(self):
        path, launcher = self.probe_fixture(); value = q.read(path)
        value["runtime_interpreter"]["path"] = str(self.python); path.write_text(json.dumps(value))
        with patch.object(voice, "_arm_child_containment") as arm, \
             patch.object(engine, "_runtime", return_value=self.runtime), \
             patch.object(sys, "executable", str(self.python)), \
             patch.object(voice, "_owned_provider_helper", side_effect=AssertionError("no ML/native preload")):
            with self.assertRaises(ValueError):
                q._probe(path)
        arm.assert_not_called()
        self.assertFalse((path.parent / "CUDA-PROBE-CLAIM.json").exists())


if __name__ == "__main__":
    unittest.main()
