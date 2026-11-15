"""CPU controller contracts with fixture files and fake process/resource calls.

No real interpreter, fork, process, model, allocation or inference is started.
"""
import copy
import json
import importlib.util
from pathlib import Path
import time
from unittest import TestCase, main, mock

from scripts import earnalism_voice as voice
from scripts import test_earnalism_voice as fixtures

sha = fixtures.sha


class CPUController(TestCase):
    # Reuse the fixture builder, without inheriting/re-running the legacy suite.
    put = fixtures.VoiceContracts.put
    ref = fixtures.VoiceContracts.ref
    dump = fixtures.VoiceContracts.dump
    save_profile = fixtures.VoiceContracts.save_profile
    save_job = fixtures.VoiceContracts.save_job

    def setUp(self):
        fixtures.VoiceContracts.setUp(self)
        balanced = {**voice.BALANCED_CHECKPOINT, "sha256": sha(self.trained), "bytes": len(self.trained)}
        patch = mock.patch.object(voice, "BALANCED_CHECKPOINT", balanced)
        patch.start(); self.addCleanup(patch.stop)
        packages = dict(voice.MIN_PACKAGES)
        patch = mock.patch.object(voice, "CPU100_PACKAGES_SHA256", voice.object_sha(packages))
        patch.start(); self.addCleanup(patch.stop)
        self.put("fixture-python", b"TEST INTERPRETER NEVER EXECUTED")
        self.put("imports.json", b'{"TEST_FIXTURE_ONLY":true,"model_loaded":false}')
        executable = self.ref("fixture-python")
        executable.update(path=str(self.root / "fixture-python"), resolved_path=str(self.root / "fixture-python"))
        self.profile["checkpoint"] = {**balanced, "path": "trained.pt"}
        self.profile["runtime"] = {"python": "3.11", "packages": packages,
            "local_cpu": {"system": "Darwin", "machine": "arm64", "executable": executable,
                          "import_evidence": self.ref("imports.json")}}
        self.save_profile()
        self.source = "দরজা খুলতেই, মীরা থমকে দাঁড়াল। তুমি সত্যিই এসেছ? কী আশ্চর্য!"
        self.put("source.txt", self.source.encode())
        self.job.update(source=self.ref("source.txt"), profile=self.ref("profile.json"), language="bn",
                        request_id=voice.CPU_REQUEST, amendment_id=voice.CPU_AMENDMENT)
        self.job["units"][0].update(start=0, end=len(self.source), spoken_text=self.source, seed=20261114,
            caption_unspoken="Aditi speaks Bengali in a natural female storytelling voice, with clear diction, moderate pace, close dry sound and restrained suspense.")
        self.job["generation"]["max_new_tokens"] = 2601
        self.job["limits"] = {"max_audio_seconds": 30, "max_output_bytes": 16 * 1024**2}
        self.save_job()
        self.put("journal.jsonl", b'{"event":"historical_counters","TEST_FIXTURE_ONLY":true,"updates":128,"takes":24}\n')
        self.history = (self.root / "journal.jsonl").read_bytes()
        self.helper = mock.Mock()
        self.helper.observe_resources.return_value = {"available_memory_bytes": 2**33, "disk_free_bytes": 2**33,
                                                       "model_memory_fit": "UNPERFORMED"}
        for name, replacement in (("_cpu_interpreter", mock.Mock(return_value="TEST-NEVER-EXECUTE")),
                                   ("_darwin_helper", mock.Mock(return_value=self.helper))):
            patch = mock.patch.object(voice, name, replacement)
            patch.start(); self.addCleanup(patch.stop)

    def authority(self):
        plan = voice.validate_job(self.root / "job.json")
        authority = {"schema": "earnalism.voice_execution.v1", "approved": True,
            "actual_scope_ref": "TEST FIXTURE ONLY - NOT OWNER AUTHORITY",
            "job_sha256": plan["job_sha256"], "profile_sha256": plan["binding"]["profile_sha256"],
            "code_sha256": voice.digest(voice.__file__), "runtime_code_sha256": voice.digest(voice.RUNTIME),
            "darwin_code_sha256": voice.digest(voice.DARWIN), "purpose": "qualification",
            "execution_mode": "local_cpu", "execution_started_at": time.time() - 1,
            "request_id": voice.CPU_REQUEST, "amendment_id": voice.CPU_AMENDMENT,
            "max_units": 1, "max_model_loads": 1, "max_restores": 1, "max_generate_calls": 1,
            "journal_path": str(self.root / "journal.jsonl"),
            "prior_journal": {"path": str(self.root / "journal.jsonl"), "bytes": len(self.history), "sha256": sha(self.history)},
            "allowed_unit_fingerprints": plan["unit_fingerprints"], "publication_allowed": False,
            "training_allowed": False, "network_allowed": False, "allocation_allowed": False,
            "package_setup_allowed": False}
        self.dump("authority.json", authority)
        return authority

    def test_balanced_profile_and_exact_case_validate_without_execution(self):
        plan = voice.validate_job(self.root / "job.json")
        self.assertEqual(plan["binding"]["status"], "UNQUALIFIED")
        self.assertFalse(plan["binding"]["production_accepted"])
        self.assertFalse(plan["binding"]["model_loaded"])
        self.assertEqual(len(plan["unit_fingerprints"]), 1)
        self.assertEqual(self.job["source"]["sha256"], voice.CPU_SOURCE_SHA256)
        self.assertEqual(sha(self.job["units"][0]["caption_unspoken"].encode()), voice.CPU_CAPTION_SHA256)

    def test_cpu_authority_has_real_execution_start_without_fabricated_allocation(self):
        self.authority()
        authority = voice._authority(self.root / "authority.json", voice.validate_job(self.root / "job.json"))
        self.assertIsNone(authority["absolute_deadline_epoch"])
        self.assertNotIn("allocation_started_at", authority)
        self.assertEqual((self.root / "journal.jsonl").read_bytes(), self.history)

    def test_changed_bindings_flags_or_limits_make_no_intent_or_process(self):
        original = self.authority()
        changes = {"approved": False, "code_sha256": "0"*64, "runtime_code_sha256": "0"*64,
            "darwin_code_sha256": "0"*64, "request_id": "OTHER", "amendment_id": "OTHER",
            "max_units": 2, "max_model_loads": 2, "max_restores": 2, "max_generate_calls": 2,
            "allocation_allowed": True, "package_setup_allowed": True, "training_allowed": True,
            "network_allowed": True, "publication_allowed": True, "actual_scope_ref": "",
            "execution_started_at": time.time() + 600, "allocation_started_at": time.time() - 1,
            "absolute_deadline_epoch": time.time() + 60, "execution_mode": "allocation"}
        for key, value in changes.items():
            with self.subTest(key=key):
                authority = {**original, key: value}; self.dump("authority.json", authority)
                with mock.patch.object(voice.subprocess, "Popen") as launch:
                    with self.assertRaises(voice.VoiceBlocked):
                        voice.render(self.root / "job.json", self.root / "output", self.root / "authority.json")
                    launch.assert_not_called()
                self.assertFalse((self.root / "output").exists())
                self.assertEqual((self.root / "journal.jsonl").read_bytes(), self.history)
        voice._cpu_interpreter.assert_not_called()
        self.helper.observe_resources.assert_not_called()

    def test_missing_or_changed_carried_history_cannot_create_empty_counter_pool(self):
        original = self.authority()
        for prior in ({}, {**original["prior_journal"], "bytes": 0},
                      {**original["prior_journal"], "sha256": "0"*64},
                      {**original["prior_journal"], "path": str(self.root / "empty.jsonl")}):
            self.dump("authority.json", {**original, "prior_journal": prior})
            with mock.patch.object(voice.subprocess, "Popen") as launch:
                with self.assertRaises(voice.VoiceBlocked):
                    voice.render(self.root / "job.json", self.root / "output", self.root / "authority.json")
                launch.assert_not_called()
        self.assertEqual((self.root / "journal.jsonl").read_bytes(), self.history)

    def test_resource_admission_failure_consumes_no_case_or_model(self):
        self.authority()
        self.helper.observe_resources.side_effect = RuntimeError("SHARED_AVAILABLE_MEMORY_FLOOR_NOT_MET")
        with mock.patch.object(voice.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(RuntimeError, "MEMORY_FLOOR"):
                voice.render(self.root / "job.json", self.root / "output", self.root / "authority.json")
            launch.assert_not_called()
        self.assertFalse((self.root / "output").exists())
        self.assertEqual((self.root / "journal.jsonl").read_bytes(), self.history)

    def test_disk_admission_failure_creates_no_intent(self):
        self.authority()
        self.helper.observe_resources.return_value["disk_free_bytes"] = 1
        with mock.patch.object(voice.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(voice.VoiceBlocked, "space"):
                voice.render(self.root / "job.json", self.root / "output", self.root / "authority.json")
            launch.assert_not_called()
        self.assertEqual((self.root / "journal.jsonl").read_bytes(), self.history)

    def test_unknown_case_is_reserved_before_launch_and_cannot_replay_renamed_job(self):
        self.authority()
        calls = []
        child = mock.Mock()
        child.wait.return_value = 7
        def launch(*args, **kwargs):
            events = [json.loads(line) for line in (self.root / "journal.jsonl").read_text().splitlines()]
            self.assertEqual(events[-1]["event"], "render_intent")
            self.assertEqual(events[-1]["unit_fingerprints"], voice.validate_job(self.root / "job.json")["unit_fingerprints"])
            self.assertEqual(events[-1]["request_id"], voice.CPU_REQUEST)
            self.assertEqual(kwargs["pass_fds"], (101,))
            self.assertNotIn(102, kwargs["pass_fds"])
            self.assertIn("--lifeline-fd", args[0])
            calls.append("launch")
            return child
        with mock.patch.object(voice.os, "pipe", return_value=(101, 102)), \
                mock.patch.object(voice.os, "set_inheritable") as inherit, \
                mock.patch.object(voice.os, "close", side_effect=lambda fd: calls.append(("close", fd))), \
                mock.patch.object(voice, "_stop_owned_group", side_effect=lambda process: calls.append("stop")), \
                mock.patch.object(voice.subprocess, "Popen", side_effect=launch) as process:
            with self.assertRaisesRegex(voice.VoiceBlocked, "failed or unknown"):
                voice.render(self.root / "job.json", self.root / "output", self.root / "authority.json")
            inherit.assert_called_once_with(102, False)
            child.wait.assert_called_once_with(timeout=None)
            self.assertLess(calls.index("stop"), calls.index(("close", 102)))
            self.assertLess(calls.index(("close", 101)), calls.index("stop"))
            self.job["units"][0]["id"] = "renamed"
            self.save_job()
            self.authority()
            with self.assertRaisesRegex(voice.VoiceBlocked, "no replay"):
                voice.render(self.root / "job.json", self.root / "renamed-output", self.root / "authority.json")
            process.assert_called_once()
        self.assertTrue((self.root / "journal.jsonl").read_bytes().startswith(self.history))
        self.assertTrue((self.root / "output/FAILURE.json").is_file())
        self.assertFalse((self.root / "renamed-output").exists())

    def test_launch_failure_consumes_case_and_closes_both_fake_descriptors(self):
        self.authority()
        calls = []
        with mock.patch.object(voice.os, "pipe", return_value=(101, 102)), \
                mock.patch.object(voice.os, "set_inheritable"), \
                mock.patch.object(voice.os, "close", side_effect=lambda fd: calls.append(("close", fd))), \
                mock.patch.object(voice, "_stop_owned_group", side_effect=lambda process: calls.append("stop")), \
                mock.patch.object(voice.subprocess, "Popen", side_effect=OSError("TEST SPAWN UNKNOWN")):
            with self.assertRaises(OSError):
                voice.render(self.root / "job.json", self.root / "output", self.root / "authority.json")
        self.assertLess(calls.index("stop"), calls.index(("close", 102)))
        self.assertIn(("close", 101), calls)
        self.assertIn('"event": "render_intent"', (self.root / "journal.jsonl").read_text())

    def test_source_or_caption_and_cpu_profile_drift_fail_before_execution(self):
        mutations = [lambda: self.job["units"][0].update(caption_unspoken="Changed direction"),
                     lambda: self.job["units"][0].update(seed=20261115),
                     lambda: self.job["generation"].update(max_new_tokens=2602),
                     lambda: self.job.update(device="cuda:0"),
                     lambda: self.job.update(amendment_id="OTHER")]
        original = copy.deepcopy(self.job)
        for change in mutations:
            self.job = copy.deepcopy(original); change(); self.save_job()
            with self.assertRaises(voice.VoiceBlocked):
                voice.validate_job(self.root / "job.json")
        self.job = copy.deepcopy(original)
        self.source += " আরও কথা।"
        self.put("source.txt", self.source.encode())
        self.job["source"] = self.ref("source.txt")
        self.job["units"][0].update(end=len(self.source), spoken_text=self.source)
        self.save_job()
        with self.assertRaises(voice.VoiceBlocked):
            voice.validate_job(self.root / "job.json")
        self.job = original
        self.put("source.txt", original["units"][0]["spoken_text"].encode())
        self.profile["runtime"]["packages"]["torch"] = "0.0.TEST"
        self.save_profile(); self.job["profile"] = self.ref("profile.json"); self.save_job()
        with self.assertRaises(voice.VoiceBlocked):
            voice.validate_job(self.root / "job.json")

    def test_local_cpu_mode_cannot_route_a_legacy_checkpoint_under_case_name(self):
        self.profile["checkpoint"] = {**self.ref("trained.pt"), "format": "EARNALISM_PARLER_LAST_BLOCK_V1",
            "bindings_sha256": voice.TRAINED_BINDINGS_SHA256, "training_updates": 130,
            "tensor_sha256": voice.TRAINED_TENSOR_SHA256}
        self.profile["runtime"] = {"python": "3.12", "packages": dict(voice.MIN_PACKAGES)}
        self.save_profile(); self.job["profile"] = self.ref("profile.json"); self.save_job()
        self.authority()
        with mock.patch.object(voice.subprocess, "Popen") as launch:
            with self.assertRaises(voice.VoiceBlocked):
                voice.render(self.root / "job.json", self.root / "output", self.root / "authority.json")
            launch.assert_not_called()
        self.assertEqual((self.root / "journal.jsonl").read_bytes(), self.history)

    def test_direct_worker_replay_and_copied_output_block_before_runtime(self):
        self.authority()
        plan = voice.validate_job(self.root / "job.json")
        output = self.root / "original-output"; output.mkdir()
        intent = {"job_sha256": plan["job_sha256"], "authority_sha256": voice.digest(self.root / "authority.json"),
                  "parent_pid": 999}
        voice._write(output / "INTENT.json", intent)
        voice._append(self.root / "journal.jsonl", {"event": "render_intent", **intent,
                                                   "output": str(output)})
        fake_runtime = mock.Mock()
        def run(*args, **kwargs):
            kwargs["check_authority"]()
            voice._write(output / "WORKER-INTENT.json", {"TEST_FIXTURE_ONLY": True})
            return {"TEST_FIXTURE_ONLY": True}
        fake_runtime.run.side_effect = run
        spec = mock.Mock()
        with mock.patch.object(voice, "_arm_child_containment") as containment, \
                mock.patch.object(importlib.util, "spec_from_file_location", return_value=spec), \
                mock.patch.object(importlib.util, "module_from_spec", return_value=fake_runtime):
            self.assertEqual(voice._worker(self.root / "job.json", output, self.root / "authority.json", 77),
                             {"TEST_FIXTURE_ONLY": True})
            containment.assert_called_once_with(None, lifeline_fd=77, expected_parent_pid=999, local_cpu=True)
            with self.assertRaisesRegex(voice.VoiceBlocked, "no direct worker replay"):
                voice._worker(self.root / "job.json", output, self.root / "authority.json", 77)
            copied = self.root / "copied-output"; copied.mkdir()
            voice._write(copied / "INTENT.json", intent)
            with self.assertRaisesRegex(voice.VoiceBlocked, "no direct worker replay"):
                voice._worker(self.root / "job.json", copied, self.root / "authority.json", 77)
            fake_runtime.run.assert_called_once()
            containment.assert_called_once()
        self.assertTrue((self.root / "journal.jsonl").read_bytes().startswith(self.history))

    def test_balanced_production_is_held_even_with_acceptance_receipt(self):
        self.dump("acceptance.json", {"status": "ACCEPTED", "identity": voice.IDENTITY, "language": "bn",
            "base_sha256": voice.BASE_SHA256, "checkpoint_sha256": voice.BALANCED_CHECKPOINT["sha256"]})
        self.profile["qualification"]["bn"] = {"status": "ACCEPTED", "evidence": self.ref("acceptance.json")}
        self.save_profile(); self.job["profile"] = self.ref("profile.json"); self.job["purpose"] = "production"
        self.save_job()
        with self.assertRaisesRegex(voice.VoiceBlocked, "production remains held"):
            voice.validate_job(self.root / "job.json")


if __name__ == "__main__":
    main()
