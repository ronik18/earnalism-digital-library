"""Small offline contracts; all synthetic files/audio are TEST FIXTURES, never media QA.

No installation, model import, network, inference, training or cloud operation.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
from unittest import TestCase, main, mock

from scripts import earnalism_voice as voice


def sha(data):
    return hashlib.sha256(data).hexdigest()


class VoiceContracts(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        stop = mock.patch.object(voice.os,"killpg");stop.start();self.addCleanup(stop.stop)
        self.base = b"TEST ONLY BASE"; self.trained = b"TEST ONLY TRAINED"
        for name, value in [("BASE_SHA256", sha(self.base)), ("TRAINED_SHA256", sha(self.trained)),
                            ("TRAINED_BYTES", len(self.trained))]:
            patch = mock.patch.object(voice, name, value); patch.start(); self.addCleanup(patch.stop)
        for folder in ["model", "tokenizer", "packages"]:
            (self.root / folder).mkdir()
        self.put("model/model.safetensors", self.base)
        self.put("trained.pt", self.trained)
        self.put("rights.json", b'{"TEST_FIXTURE_ONLY":true}')
        self.source = "First sentence.\r\nSecond thought!"
        self.put("source.txt", self.source.encode())
        self.profile = {
            "schema": "earnalism.voice_profile.v1", "identity": voice.IDENTITY, "backend": voice.BACKEND,
            "base": {"model_id": voice.BASE_ID, "revision": voice.BASE_REVISION, "sha256": sha(self.base)},
            "checkpoint": {**self.ref("trained.pt"), "format": "EARNALISM_PARLER_LAST_BLOCK_V1",
                "bindings_sha256": voice.TRAINED_BINDINGS_SHA256, "training_updates": 130,
                "tensor_sha256": voice.TRAINED_TENSOR_SHA256},
            "assets": {"model_dir": "model", "description_tokenizer_dir": "tokenizer", "source_root": "packages",
                       "files": [self.ref("model/model.safetensors")]},
            "runtime": {"python": "3.12", "packages": voice.MIN_PACKAGES},
            "rights": {"status": "CLEARED", "evidence": self.ref("rights.json")}, "qualification": {},
        }
        self.save_profile()
        self.job = {"schema": "earnalism.voice_job.v1", "source": self.ref("source.txt"),
            "profile": self.ref("profile.json"), "language": "en", "purpose": "qualification", "device": "cpu",
            "units": [{"id": "opening", "start": 0, "end": len(self.source), "spoken_text": self.source,
                       "caption_unspoken": "Unspoken fixture direction", "context": "Fixture meaning", "seed": 7}],
            "generation": {"do_sample": True, "temperature": 1.0, "top_k": 50, "top_p": 1.0, "max_new_tokens": 30},
            "limits": {"max_audio_seconds": 2, "max_output_bytes": 4096}}
        self.save_job()

    def put(self, path, data):
        (self.root / path).write_bytes(data)

    def ref(self, path):
        data = (self.root / path).read_bytes()
        return {"path": path, "bytes": len(data), "sha256": sha(data)}

    def dump(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def save_profile(self):
        self.dump("profile.json", self.profile)

    def save_job(self):
        self.dump("job.json", self.job)

    def authority(self):
        plan = voice.validate_job(self.root / "job.json")
        now = time.time()
        result = {"schema": "earnalism.voice_execution.v1", "approved": True, "actual_scope_ref": "TEST FIXTURE ONLY",
            "job_sha256": plan["job_sha256"], "profile_sha256": plan["binding"]["profile_sha256"],
            "code_sha256": voice.digest(voice.__file__), "runtime_code_sha256": voice.digest(voice.RUNTIME),
            "purpose": "qualification", "allocation_started_at": now - 1, "original_deadline_epoch": now + 60,
            "max_units": 1, "journal_path": str(self.root / "journal.jsonl"),
            "allowed_unit_fingerprints": plan["unit_fingerprints"],
            "publication_allowed": False, "training_allowed": False, "network_allowed": False}
        self.dump("authority.json", result)
        return result

    def test_imports_and_qualification_inspection_do_not_load_models(self):
        before = {name for name in sys.modules if name.split(".")[0] in {"torch", "parler_tts", "transformers"}}
        with mock.patch.object(voice.subprocess, "Popen", side_effect=AssertionError("No subprocess allowed")):
            result = voice.inspect_profile(self.root / "profile.json", "en")
        self.assertEqual(result["status"], "UNQUALIFIED")
        self.assertEqual(result["blockers"], ["VOICE_LANGUAGE_NOT_PRODUCTION_ACCEPTED"])
        self.assertFalse(result["model_loaded"])
        self.assertEqual(before, {n for n in sys.modules if n.split(".")[0] in {"torch", "parler_tts", "transformers"}})

    def test_qualification_does_not_fabricate_production_acceptance(self):
        result = voice.inspect_profile(self.root / "profile.json", "en", "qualification")
        self.assertEqual(result["status"], "UNQUALIFIED"); self.assertEqual(result["blockers"], [])
        self.assertFalse(result["production_accepted"])
        voice.validate_job(self.root / "job.json")
        self.job["purpose"] = "production"; self.save_job()
        with self.assertRaisesRegex(voice.VoiceBlocked, "NOT_PRODUCTION_ACCEPTED"):
            voice.validate_job(self.root / "job.json")

    def test_stock_or_different_checkpoint_cannot_masquerade_as_trained_brand(self):
        self.profile["checkpoint"]["sha256"] = sha(self.base); self.save_profile()
        self.job["profile"] = self.ref("profile.json"); self.save_job()
        self.assertEqual(voice.inspect_profile(self.root / "profile.json", "en")["status"], "INVALID")
        with self.assertRaisesRegex(voice.VoiceBlocked, "trained checkpoint"):
            voice.validate_job(self.root / "job.json")  # descriptor itself drifted

    def test_exact_source_and_unspoken_direction_are_separate(self):
        result = voice.validate_job(self.root / "job.json")
        self.assertEqual(result["job"]["units"][0]["spoken_text"], self.source)
        self.assertIn("\r\n", result["job"]["units"][0]["spoken_text"])
        self.job["units"][0]["spoken_text"] += " Direction leaked into speech."
        self.save_job()
        with self.assertRaisesRegex(voice.VoiceBlocked, "Exact ordered source"):
            voice.validate_job(self.root / "job.json")

    def test_source_hash_drift_and_split_word_rejected(self):
        self.put("source.txt", b"Changed original")
        with self.assertRaises(voice.VoiceBlocked): voice.validate_job(self.root / "job.json")
        self.put("source.txt", self.source.encode())
        self.job["units"][0].update(start=1, spoken_text=self.source[1:]); self.save_job()
        with self.assertRaisesRegex(voice.VoiceBlocked, "splits"):
            voice.validate_job(self.root / "job.json")

    def test_bengali_vowel_virama_and_joiners_cannot_start_a_split_unit(self):
        for text, offset in [("বাংলা",1), ("ক্ষতি",1), ("ক\u200dষ",1)]:
            self.put("source.txt",text.encode()); self.job["source"]=self.ref("source.txt")
            self.job["language"]="bn"
            self.job["units"]=[{"id":"broken", "start":offset,"end":len(text),"spoken_text":text[offset:],
                "caption_unspoken":"Fixture", "context":"Fixture", "seed":1}]
            self.save_job()
            with self.assertRaisesRegex(voice.VoiceBlocked,"splits"):
                voice.validate_job(self.root/"job.json")

    def test_acceptance_evidence_must_bind_exact_language_and_checkpoint(self):
        receipt = {"status": "ACCEPTED", "identity": voice.IDENTITY, "language": "bn",
                   "base_sha256": sha(self.base), "checkpoint_sha256": sha(self.trained)}
        self.dump("acceptance.json", receipt)
        self.profile["qualification"]["en"] = {"status": "ACCEPTED", "evidence": self.ref("acceptance.json")}
        self.save_profile()
        self.assertEqual(voice.inspect_profile(self.root / "profile.json", "en")["status"], "INVALID")

    def test_checkpoint_parts_stream_verified_without_whole_materialization(self):
        self.put("part1", self.trained[:5]); self.put("part2", self.trained[5:])
        checkpoint = {**self.profile["checkpoint"], "parts": [self.ref("part1"), self.ref("part2")]}
        del checkpoint["path"]
        before = set(self.root.iterdir())
        self.assertIsNone(voice._checkpoint(self.root, checkpoint))
        self.assertEqual(before, set(self.root.iterdir()))
        self.put("part2", b"x" * len(self.trained[5:]))
        with self.assertRaisesRegex(voice.VoiceBlocked, "part checksum"):
            voice._checkpoint(self.root, checkpoint)

    def test_no_authority_expired_or_changed_hash_causes_zero_calls_and_zero_intents(self):
        for mutation in [lambda a: a.update(approved=False), lambda a: a.update(original_deadline_epoch=time.time()-1),
                         lambda a: a.update(job_sha256="0"*64)]:
            auth = self.authority(); mutation(auth); self.dump("authority.json", auth)
            with mock.patch.object(voice.subprocess, "Popen") as launch:
                with self.assertRaises(voice.VoiceBlocked):
                    voice.render(self.root/"job.json", self.root/"output", self.root/"authority.json")
                launch.assert_not_called()
            self.assertFalse((self.root/"journal.jsonl").exists())

    def test_unknown_child_failure_is_consumed_and_not_replayed_under_new_output_name(self):
        self.authority()
        child = mock.Mock(); child.wait.return_value = 1; child.poll.return_value = 1
        with mock.patch.object(voice.subprocess, "Popen", return_value=child) as launch:
            with self.assertRaisesRegex(voice.VoiceBlocked, "failed or unknown"):
                voice.render(self.root/"job.json", self.root/"failed", self.root/"authority.json")
            with self.assertRaisesRegex(voice.VoiceBlocked, "no replay"):
                voice.render(self.root/"job.json", self.root/"renamed", self.root/"authority.json")
            self.assertEqual(launch.call_count, 1)
        self.assertTrue((self.root/"failed/FAILURE.json").is_file())

    def test_partial_success_manifest_does_not_clear_completion(self):
        self.authority(); plan = voice.validate_job(self.root/"job.json")
        def launch(*args, **kwargs):
            result = {"schema": "earnalism.voice_render_result.v1", "status": "PRIVATE_GENERATED_REQUIRES_QA",
                "job_sha256": plan["job_sha256"], "source_sha256": self.job["source"]["sha256"],
                "profile_sha256": self.job["profile"]["sha256"], "checkpoint_sha256": sha(self.trained), "outputs": []}
            self.dump("partial/RESULT.json", result)
            child = mock.Mock(); child.wait.return_value=0; child.poll.return_value=0
            return child
        with mock.patch.object(voice.subprocess, "Popen", side_effect=launch):
            with self.assertRaisesRegex(voice.VoiceBlocked, "Partial or unknown"):
                voice.render(self.root/"job.json", self.root/"partial", self.root/"authority.json")

    def test_deadline_timeout_stops_owned_process_group_and_preserves_unknown(self):
        self.authority()
        child=mock.Mock(); child.pid=987654
        child.wait.side_effect=[subprocess.TimeoutExpired("TEST FIXTURE", 60), 0]
        child.poll.return_value=None
        with mock.patch.object(voice.subprocess, "Popen", return_value=child), \
             mock.patch.object(voice.os, "killpg") as stop:
            with self.assertRaises(subprocess.TimeoutExpired):
                voice.render(self.root/"job.json", self.root/"timeout", self.root/"authority.json")
            self.assertEqual(stop.call_args_list,[mock.call(child.pid,voice.signal.SIGTERM),
                                                mock.call(child.pid,voice.signal.SIGKILL)])
        self.assertEqual(json.loads((self.root/"timeout/FAILURE.json").read_text())["status"], "FAILED_OR_UNKNOWN_NO_REPLAY")

    def setup_authority(self):
        self.put("fixture-python", b"NOT AN EXECUTABLE; TEST METADATA ONLY")
        self.dump("wheels.json", {"wheels": []})
        self.dump("bootstrap-wheels.json", {"wheels": []})
        self.profile["runtime"]["bootstrap"]={"runtime_dir": "private-runtime",
            "python_executable": self.ref("fixture-python"), "wheel_manifest": self.ref("wheels.json"),
            "bootstrap_wheel_manifest":self.ref("bootstrap-wheels.json")}
        self.save_profile(); self.job["profile"]=self.ref("profile.json"); self.save_job()
        auth=self.authority()
        auth.update(package_setup_allowed=True, package_network_allowed=True,
                    setup_code_sha256=voice.digest(voice.SETUP), runtime_dir=str(self.root/"private-runtime"))
        self.dump("authority.json", auth)
        return auth

    def test_missing_runtime_interpreter_fails_before_install_or_setup_intent(self):
        self.setup_authority(); (self.root/"fixture-python").unlink()
        with mock.patch.object(voice.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(voice.VoiceBlocked, "Missing"):
                voice.ensure_runtime(self.root/"profile.json", self.root/"private-runtime", self.root/"authority.json")
            launch.assert_not_called()
        self.assertFalse((self.root/"journal.jsonl").exists())

    def test_setup_failure_is_durable_and_same_scope_cannot_replay(self):
        self.setup_authority()
        child=mock.Mock(); child.wait.return_value=1; child.poll.return_value=1
        with mock.patch.object(voice.subprocess, "Popen", return_value=child) as launch:
            with self.assertRaisesRegex(voice.VoiceBlocked, "Package setup failed"):
                voice.ensure_runtime(self.root/"profile.json", self.root/"private-runtime", self.root/"authority.json")
            with self.assertRaisesRegex(voice.VoiceBlocked, "Consumed package setup"):
                voice.ensure_runtime(self.root/"profile.json", self.root/"private-runtime", self.root/"authority.json")
            self.assertEqual(launch.call_count, 1)
            self.assertNotIn("OPENAI_API_KEY", launch.call_args.kwargs["env"])
            self.assertNotIn("HF_TOKEN", launch.call_args.kwargs["env"])
        self.assertTrue((self.root/"private-runtime.setup-process.log").is_file())

    def test_cached_runtime_cannot_select_another_or_missing_interpreter(self):
        self.setup_authority(); evidence=self.root/"private-runtime.setup"; evidence.mkdir()
        result={"status":"LOCAL_PACKAGES_READY_NOT_MODEL_QUALIFIED",
                "profile_sha256":voice.digest(self.root/"profile.json"),"python":"/unrelated/python"}
        self.dump("private-runtime.setup/RESULT.json", result)
        with mock.patch.object(voice.subprocess,"run") as probe, mock.patch.object(voice.subprocess,"Popen") as install:
            with self.assertRaisesRegex(voice.VoiceBlocked,"incompatible runtime"):
                voice.ensure_runtime(self.root/"profile.json",self.root/"private-runtime",self.root/"authority.json")
            result["python"]=str(self.root/"private-runtime/bin/python");self.dump("private-runtime.setup/RESULT.json",result)
            with self.assertRaisesRegex(voice.VoiceBlocked,"incompatible runtime"):
                voice.ensure_runtime(self.root/"profile.json",self.root/"private-runtime",self.root/"authority.json")
            probe.assert_not_called();install.assert_not_called()

    def test_cached_runtime_current_package_drift_blocks_without_install(self):
        self.setup_authority(); (self.root/"private-runtime.setup").mkdir()
        (self.root/"private-runtime/bin").mkdir(parents=True)
        self.put("private-runtime/bin/python",(self.root/"fixture-python").read_bytes())
        self.dump("private-runtime.setup/RESULT.json", {"status":"LOCAL_PACKAGES_READY_NOT_MODEL_QUALIFIED",
            "profile_sha256":voice.digest(self.root/"profile.json"),"python":str(self.root/"private-runtime/bin/python")})
        wrong=mock.Mock(stdout=json.dumps({"python":"3.13","packages":{}}))
        with mock.patch.object(voice.subprocess,"run",return_value=wrong) as probe, \
             mock.patch.object(voice.subprocess,"Popen") as install:
            with self.assertRaisesRegex(voice.VoiceBlocked,"metadata drifted"):
                voice.ensure_runtime(self.root/"profile.json",self.root/"private-runtime",self.root/"authority.json")
            self.assertEqual(probe.call_args.args[0][0],str(self.root/"private-runtime/bin/python"))
            install.assert_not_called()

    def test_unofficial_wheel_lock_rejected_before_any_download_or_install(self):
        self.setup_authority()
        self.dump("wheels.json", {"wheels":[{"name":"torch", "version":"2.6.0", "filename":"torch-2.6.0.whl",
            "bytes":3, "sha256":"1"*64, "url":"https://example.invalid/not-official.whl"}]})
        self.profile["runtime"]["bootstrap"]["wheel_manifest"]=self.ref("wheels.json")
        self.save_profile()
        auth=json.loads((self.root/"authority.json").read_text()); auth["profile_sha256"]=voice.digest(self.root/"profile.json")
        self.dump("authority.json", auth)
        spec=importlib.util.spec_from_file_location("fixture_voice_setup", voice.SETUP)
        setup=importlib.util.module_from_spec(spec); spec.loader.exec_module(setup); setup.voice=voice
        with mock.patch.object(setup.platform,"system",return_value="Linux"), \
             mock.patch.object(setup.platform,"machine",return_value="x86_64"), \
             mock.patch.object(voice,"_arm_child_containment"), \
             mock.patch.object(setup,"build_opener") as fetch, mock.patch.object(setup.subprocess,"run") as install:
            with self.assertRaisesRegex(voice.VoiceBlocked,"official immutable"):
                setup.execute(self.root/"profile.json", self.root/"private-runtime", self.root/"authority.json")
            fetch.assert_not_called(); install.assert_not_called()

    def test_bootstrap_uses_its_complete_hashed_offline_manifest(self):
        # Tiny fake wheel files + mocked installers; this verifies no live setup.
        self.setup_authority()
        def wheel(name, version):
            filename=name.replace("-","_")+"-"+version+"-py3-none-any.whl"
            self.put(filename,b"SOURCE-ONLY FAKE WHEEL "+name.encode())
            return {"name":name,"version":version,"filename":filename,**self.ref(filename)}
        runtime_rows=[wheel(k,v) for k,v in voice.MIN_PACKAGES.items()]
        boot_rows=[wheel("virtualenv","20.35.4"),wheel("fixture-bootstrap-dependency","0.0.0")]
        self.dump("wheels.json",{"wheels":runtime_rows});self.dump("bootstrap-wheels.json",{"wheels":boot_rows})
        self.profile["runtime"]["bootstrap"].update(wheel_manifest=self.ref("wheels.json"),
            bootstrap_wheel_manifest=self.ref("bootstrap-wheels.json"))
        self.save_profile();auth=json.loads((self.root/"authority.json").read_text())
        auth["profile_sha256"]=voice.digest(self.root/"profile.json");self.dump("authority.json",auth)
        spec=importlib.util.spec_from_file_location("fixture_locked_setup",voice.SETUP)
        setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup);setup.voice=voice
        def package_fixture(command,**kwargs):
            if command[-1].startswith("import sys;print"):
                return mock.Mock(stdout="3.12\n")
            return mock.Mock(stdout=json.dumps(voice.MIN_PACKAGES))
        with mock.patch.object(setup.platform,"system",return_value="Linux"), \
             mock.patch.object(setup.platform,"machine",return_value="x86_64"), \
             mock.patch.object(voice,"_arm_child_containment"), \
             mock.patch.object(setup.shutil,"disk_usage",return_value=mock.Mock(free=10**12)), \
             mock.patch.object(setup.subprocess,"run",side_effect=package_fixture) as commands:
            setup.execute(self.root/"profile.json",self.root/"private-runtime",self.root/"authority.json")
        installers=[c.args[0] for c in commands.call_args_list if "install" in c.args[0]]
        self.assertEqual(len(installers),2)
        for command in installers:
            self.assertIn("--require-hashes",command);self.assertIn("--no-index",command)
            self.assertNotIn("--no-deps",command);self.assertNotIn("--index-url",command)
        virtualenv=[c.args[0] for c in commands.call_args_list if "--no-download" in c.args[0]][0]
        self.assertIn("--no-periodic-update",virtualenv)
        self.assertEqual(virtualenv[virtualenv.index("--app-data")+1],str(self.root/"private-runtime.setup/virtualenv-appdata"))
        lock=(self.root/"private-runtime.setup/bootstrap.requirements.lock.txt").read_text()
        self.assertIn("virtualenv==20.35.4 --hash=sha256:",lock)
        self.assertIn("fixture-bootstrap-dependency==0.0.0 --hash=sha256:",lock)

    def test_real_export_loop_uses_fixture_samples_and_retains_pcm_provenance(self):
        # Actual export/control code, fake acoustic backend; never a production take.
        spec = importlib.util.spec_from_file_location("fixture_parler_runtime", voice.RUNTIME)
        runtime = importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
        self.authority(); plan = voice.validate_job(self.root/"job.json")
        auth = voice._authority(self.root/"authority.json", plan)
        output=self.root/"fixture-audio"; output.mkdir()
        with mock.patch.object(runtime, "_load_bundle", return_value=({"loading_report": {"TEST_FIXTURE_ONLY": True}}, object())), \
             mock.patch.object(runtime, "BundleSampler") as sampler:
            sampler.return_value.generate.return_value=([0.0, 0.125, -0.125], False)
            result=runtime.run(plan, self.profile, auth, output, checkpoint_loader=voice._checkpoint,
                               append_event=voice._append, write_json=voice._write)
        voice._verify_result(plan, output, result)
        with mock.patch.object(voice.subprocess,"Popen",side_effect=AssertionError("Recovery must be read-only")):
            self.assertEqual(voice.verify_retained(self.root/"job.json",output),result)
        raw=(output/"opening.wav").read_bytes()
        self.assertEqual(raw[:4], b"RIFF"); self.assertEqual(struct.unpack_from("<H", raw, 20)[0], 3)
        self.assertEqual(struct.unpack_from("<3f", raw, 44), (0.0, 0.125, -0.125))
        self.assertEqual(result["checkpoint_sha256"], sha(self.trained))
        self.assertEqual(result["source_sha256"], self.job["source"]["sha256"])
        self.assertEqual(result["training_updates_in_this_run"], 0)
        self.assertEqual(result["fidelity_naturalness_accent_and_mix"], "UNPERFORMED")
        self.assertIn('"event": "unit_intent"', (self.root/"journal.jsonl").read_text())


if __name__ == "__main__":
    main()
