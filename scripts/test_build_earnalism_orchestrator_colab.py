"""Source-distribution checks; no Colab, model or provider is exercised."""
import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
import subprocess

from scripts import build_earnalism_orchestrator_colab as builder


class NotebookSourceTests(unittest.TestCase):
    def test_default_image_pins_cp312_without_execution_or_gpu_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            receipt = builder.build(notebook, root=root, base_revision="a"*40)
            value = json.loads(notebook.read_text())
            self.assertEqual(value["metadata"]["colab"]["runtime_attributes"],
                             {"runtime_version": "2026.07"})
            self.assertNotIn("accelerator", value["metadata"])
            self.assertFalse(receipt["execution_default"])
            self.assertIn("EXECUTE = False", "".join(value["cells"][1]["source"]))
            self.assertIn("def qualify_pre_storage_driver()", "".join(value["cells"][5]["source"]))

    def test_batch_notebook_uses_parallel_preparation_without_single_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="a"*40)
            workspace = root/"private"
            workspace.mkdir()
            calls = []
            engine = types.ModuleType("scripts.earnalism_orchestrator")
            engine.run = mock.Mock(side_effect=AssertionError("single run must not replace batch"))
            engine.feedback = mock.Mock()
            def batch(path, selected, **kwargs):
                calls.append((path, selected, kwargs))
                return {"state":"PRIVATE_PREPARATION_OR_REVIEW_REQUIRED", "production_ready":False}
            engine.batch = batch
            namespace = {"pathlib":__import__("pathlib"), "json":json, "time":__import__("time"),
                         "PRIVATE_WORKSPACE":str(workspace), "EXECUTE":False,
                         "BATCH_PATH":str(workspace/"batch.json"), "PREPARATION_WORKERS":3,
                         "BATCH_AUTHORITIES_PATH":"", "runtime_context":{}, "FEEDBACK_PATH":"",
                         "AUTO_DISCONNECT_OWN_RUNTIME":True,
                         "connect_private_workspace":lambda:(workspace, workspace/"projects.json"),
                         "prepare_reviewed_software":lambda:root}
            code = "".join(json.loads(notebook.read_text())["cells"][-1]["source"])
            with mock.patch.dict("sys.modules", {"scripts.earnalism_orchestrator":engine}), redirect_stdout(io.StringIO()):
                exec(compile(code, "batch-notebook-fixture", "exec"), namespace)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][2]["workers"], 3)
            self.assertFalse(calls[0][2]["execute"])
            self.assertIsNone(calls[0][2]["authorities_path"])
            self.assertFalse(namespace["result"]["production_ready"])
            engine.run.assert_not_called()

    def test_rust_and_source_context_are_in_reviewed_capsule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            receipt = builder.build(root/"production.ipynb", root=root, base_revision="b"*40)
            self.assertIn("scripts/earnalism_content_context.py", receipt["files"])
            self.assertIn("skills/earnalism-video/software/metal_rust/contract.json", receipt["files"])
            self.assertIn("skills/earnalism-video/software/metal_rust/index.tsx", receipt["files"])

    def fixture(self, root):
        for name in builder.FILES:
            path = root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# public source fixture\n")
        runtime = root/"scripts/earnalism_voice_runtime/inference.py"
        runtime.parent.mkdir(parents=True, exist_ok=True)
        runtime.write_text("# inference fixture\n")
        (runtime.parent/"pre_drive_loader_entry.py").write_text(
            "def run(scope, output):\n"
            "    return {\"state\": \"FRESH_MINIMALENV_DRIVER_LOOKUP_PASS_NOT_TORCH_OR_TTS_QUALIFICATION\", \"scope\": scope}\n")
        (root/"private-voice-weights.bin").write_bytes(b"PRIVATE_MUST_NOT_EMBED")

    def test_deterministic_capsule_and_no_private_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            one, two = root/"one.ipynb", root/"two.ipynb"
            first = builder.build(one, root=root, base_revision="a"*40)
            second = builder.build(two, root=root, base_revision="a"*40)
            self.assertEqual(one.read_bytes(), two.read_bytes())
            self.assertEqual(first["capsule_sha256"], second["capsule_sha256"])
            self.assertNotIn("private-voice-weights.bin", first["files"])
            self.assertEqual(builder.verify_notebook(one, root=root), first)
            for cell in json.loads(one.read_text())["cells"]:
                if cell["cell_type"] == "code":
                    ast.parse("".join(cell["source"]))
                    self.assertEqual(cell["outputs"], [])

    def test_modified_runtime_is_rejected_without_rebuilding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="b"*40)
            (root/"scripts/earnalism_voice_runtime/inference.py").write_text("# changed\n")
            with self.assertRaisesRegex(ValueError, "stale"):
                builder.verify_notebook(notebook, root=root)

    def test_expired_scope_stops_before_colab_or_source_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="c"*40)
            cells = json.loads(notebook.read_text())["cells"]
            scope = root/"expired.json"
            scope.write_text(json.dumps({"schema":"earnalism.orchestrator_runtime.v1",
                                         "owner_authorized":True,"allocation_started_at":1,
                                         "original_deadline_epoch":2}))
            namespace = {"EXECUTE":True,"RUNTIME_AUTHORITY_PATH":str(scope)}
            guard = "".join(cells[3]["source"])
            with self.assertRaisesRegex(RuntimeError, "exhausted"):
                exec(compile(guard, "guard-fixture", "exec"), namespace)
            self.assertNotIn("google.colab", namespace)

    def test_invalid_source_base_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            with self.assertRaises(ValueError):
                builder.build(root/"bad.ipynb", root=root, base_revision="main")
            path = root/builder.FILES[0]
            path.unlink()
            path.symlink_to(root/builder.FILES[1])
            with self.assertRaisesRegex(ValueError, "regular source"):
                builder.build(root/"bad.ipynb", root=root, base_revision="d"*40)

    def test_existing_authority_bytes_are_admitted_inside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="e"*40)
            workspace = root/"private"
            workspace.mkdir()
            raw = b'{"schema":"existing-owner-authority","fixed-clock":123}\n'
            calls = []
            def run(instruction, selected_workspace, **kwargs):
                admission = kwargs["authority_path"]
                self.assertTrue(admission.is_relative_to(workspace))
                self.assertEqual(admission.read_bytes(), raw)
                calls.append(instruction)
                return {"state":"SOURCE_FIXTURE_ONLY", "production_ready":False}
            engine = types.ModuleType("scripts.earnalism_orchestrator")
            engine.run, engine.feedback = run, lambda *args: None
            namespace = {"pathlib":__import__("pathlib"),"json":json,"time":__import__("time"),
                         "PRIVATE_WORKSPACE":str(workspace), "EXECUTE":True,
                         "runtime_authority_raw":raw, "runtime_context":{"original_deadline_epoch":123},
                         "INSTRUCTION":"book - Fixture", "FEEDBACK_PATH":"",
                         "AUTO_DISCONNECT_OWN_RUNTIME":False,
                         "connect_private_workspace":lambda:(workspace, workspace/"projects.json"),
                         "prepare_reviewed_software":lambda:root}
            source = "".join(json.loads(notebook.read_text())["cells"][-1]["source"])
            with mock.patch.dict("sys.modules", {"scripts.earnalism_orchestrator":engine}), redirect_stdout(io.StringIO()):
                exec(compile(source, "notebook-wiring-fixture", "exec"), namespace)
            self.assertEqual(calls, ["book - Fixture"])

    def test_setup_failure_requests_owned_shutdown_and_keeps_failure_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="f"*40)
            workspace = root/"private"
            workspace.mkdir()
            stopped = []
            colab = types.ModuleType("google.colab")
            colab.runtime = types.SimpleNamespace(unassign=lambda:stopped.append(True))
            namespace = {"pathlib":__import__("pathlib"),"json":json,"time":__import__("time"),
                         "PRIVATE_WORKSPACE":str(workspace),"EXECUTE":True,
                         "runtime_authority_raw":b"{}", "runtime_context":{"original_deadline_epoch":123},
                         "AUTO_DISCONNECT_OWN_RUNTIME":True,
                         "connect_private_workspace":lambda:(workspace, workspace/"projects.json"),
                         "prepare_reviewed_software":mock.Mock(side_effect=RuntimeError("source setup failed"))}
            source = "".join(json.loads(notebook.read_text())["cells"][-1]["source"])
            with mock.patch.dict("sys.modules", {"google.colab":colab}), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "setup failed"):
                    exec(compile(source, "notebook-failure-fixture", "exec"), namespace)
            self.assertEqual(stopped, [True])
            self.assertEqual(json.loads((workspace/"last-orchestrator-error.json").read_text())["state"], "FAILED_OR_UNKNOWN")
            self.assertFalse(json.loads((workspace/"last-shutdown-request.json").read_text())["provider_closure_observed"])
            first_events = set((workspace/".orchestrator/notebook-events").glob("*.json"))
            self.assertEqual(len(first_events), 2)
            with mock.patch.dict("sys.modules", {"google.colab":colab}), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "setup failed"):
                    exec(compile(source, "notebook-repeated-failure-fixture", "exec"), namespace)
            later_events = set((workspace/".orchestrator/notebook-events").glob("*.json"))
            self.assertEqual(len(later_events), 4)
            self.assertTrue(first_events.issubset(later_events))

    def test_changed_base_dependency_and_unknown_source_are_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/"base.py").write_text("# fixed base\n")
            (root/"overlay.py").write_text("# old overlay\n")
            subprocess.run(["git","init","-q",str(root)], check=True)
            subprocess.run(["git","-C",str(root),"add","."], check=True)
            subprocess.run(["git","-C",str(root),"-c","user.name=Fixture","-c","user.email=fixture@example.invalid",
                            "commit","-qm","source fixture"], check=True)
            (root/"overlay.py").write_text("# reviewed overlay\n")
            builder.check_base_source(root, {"overlay.py":"unused"})
            (root/"base.py").write_text("# preserve this modified base\n")
            with self.assertRaisesRegex(RuntimeError, "base.py"):
                builder.check_base_source(root, {"overlay.py":"unused"})
            self.assertEqual((root/"base.py").read_text(), "# preserve this modified base\n")
            (root/"base.py").write_text("# fixed base\n")
            (root/"foreign.py").write_text("# unowned\n")
            with self.assertRaisesRegex(RuntimeError, "foreign.py"):
                builder.check_base_source(root, {"overlay.py":"unused"})

    def test_pre_storage_hook_is_inert_without_execution_and_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="a"*40)
            source = "".join(json.loads(notebook.read_text())["cells"][5]["source"])
            for execute, opt_in in [(False, False), (False, True), (True, False)]:
                namespace = {"EXECUTE":execute, "QUALIFY_PRE_STORAGE_DRIVER":opt_in}
                exec(compile(source, "pre-storage-definitions", "exec"), namespace)
                self.assertIsNone(namespace["qualify_pre_storage_driver"]())

    def test_pre_storage_hook_binds_actual_clock_and_live_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="a"*40)
            source = "".join(json.loads(notebook.read_text())["cells"][5]["source"])
            clock = {"allocation_started_at":1, "original_deadline_epoch":2}
            authority = {"owner_authorized":True, **clock, "pre_storage_driver_scope":{
                "approved":True, "actual_scope_ref":"SOURCE_FIXTURE_ONLY",
                "observed_units_per_hour":1, "approved_compute_units":3}}
            guard = mock.Mock(); guard.is_alive.return_value = True
            namespace = {"EXECUTE":True, "QUALIFY_PRE_STORAGE_DRIVER":True,
                         "runtime_authority":authority, "runtime_context":clock,
                         "runtime_guard":guard, "pathlib":__import__("pathlib"), "time":__import__("time")}
            exec(compile(source, "pre-storage-definitions", "exec"), namespace)
            receipt = namespace["qualify_pre_storage_driver"]()
            self.assertEqual(receipt["scope"]["allocation_started_at"], 1)
            self.assertEqual(receipt["scope"]["original_deadline_epoch"], 2)
            self.assertTrue(receipt["scope"]["shutdown_guard_armed"])
            authority["pre_storage_driver_scope"]["original_deadline_epoch"] = 3
            with self.assertRaisesRegex(RuntimeError, "original allocation clock"):
                namespace["qualify_pre_storage_driver"]()
            guard.is_alive.return_value = False
            with self.assertRaisesRegex(RuntimeError, "shutdown guard"):
                namespace["qualify_pre_storage_driver"]()

    def test_pre_storage_failed_receipt_blocks_continuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            (root/"scripts/earnalism_voice_runtime/pre_drive_loader_entry.py").write_text(
                "def run(scope, output):\n    return {'state':'PRE_STORAGE_DRIVER_LOOKUP_FAILED_NO_RETRY'}\n")
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="a"*40)
            source = "".join(json.loads(notebook.read_text())["cells"][5]["source"])
            clock = {"allocation_started_at":1, "original_deadline_epoch":2}
            guard = mock.Mock(); guard.is_alive.return_value = True
            namespace = {"EXECUTE":True, "QUALIFY_PRE_STORAGE_DRIVER":True,
                         "runtime_authority":{"owner_authorized":True, **clock,
                                              "pre_storage_driver_scope":{"approved":True}},
                         "runtime_context":clock, "runtime_guard":guard,
                         "pathlib":__import__("pathlib"), "time":__import__("time")}
            exec(compile(source, "pre-storage-definitions", "exec"), namespace)
            with self.assertRaisesRegex(RuntimeError, "Driver lookup failed"):
                namespace["qualify_pre_storage_driver"]()

    def test_pre_storage_failure_stops_before_mount_and_requests_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="a"*40)
            workspace = root/"unmounted-private-workspace"
            stopped = []
            colab = types.ModuleType("google.colab")
            colab.runtime = types.SimpleNamespace(unassign=lambda:stopped.append(True))
            mount = mock.Mock(side_effect=AssertionError("Drive connection must not begin"))
            namespace = {"pathlib":__import__("pathlib"), "json":json, "time":__import__("time"),
                         "PRIVATE_WORKSPACE":str(workspace), "EXECUTE":True,
                         "QUALIFY_PRE_STORAGE_DRIVER":True,
                         "AUTO_DISCONNECT_OWN_RUNTIME":True,
                         "runtime_context":{"original_deadline_epoch":123},
                         "connect_private_workspace":mount,
                         "qualify_pre_storage_driver":mock.Mock(side_effect=RuntimeError("lookup failed"))}
            source = "".join(json.loads(notebook.read_text())["cells"][-1]["source"])
            with mock.patch.dict("sys.modules", {"google.colab":colab}), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "lookup failed"):
                    exec(compile(source, "pre-storage-failure", "exec"), namespace)
            mount.assert_not_called()
            self.assertEqual(stopped, [True])
            self.assertFalse(workspace.exists())

    def test_foreign_import_cache_is_refused_without_resetting_it(self):
        builder.check_import_namespace(builder.ROOT)
        old = types.ModuleType("scripts.old_capsule")
        old.__file__ = "/content/earnalism-orchestrator-old/scripts/old_capsule.py"
        with mock.patch.dict("sys.modules", {"scripts.old_capsule":old}):
            with self.assertRaisesRegex(RuntimeError, "scripts.old_capsule"):
                builder.check_import_namespace(builder.ROOT)
            import sys
            self.assertIs(sys.modules["scripts.old_capsule"], old)


if __name__ == "__main__":
    unittest.main()
