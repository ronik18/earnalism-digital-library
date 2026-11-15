"""Offline English qualification regression tests using synthetic inputs only.

No retained narration, private captions, storage IDs, owner approvals, model
weights or publisher records are fixtures. Native tests use a fake sampler;
their tiny WAVs prove preservation and stop semantics, never speech quality.
"""
import array
import builtins
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


def _without_ml_import(name, *args, **kwargs):
    if name.split(".", 1)[0] in {"torch", "transformers", "parler_tts"}:
        raise AssertionError("Metadata validation must not import an ML runtime")
    return _original_import(name, *args, **kwargs)


_original_import = builtins.__import__
with patch("builtins.__import__", side_effect=_without_ml_import):
    from scripts import earnalism_voice as voice
    from scripts.earnalism_voice_runtime import parler as runtime


# Public software versions. No profile assets or private input bindings follow.
LINUX_PACKAGES = {
    "absl-py": "2.5.1",
    "argbind": "0.3.9",
    "asttokens": "3.0.2",
    "audioread": "3.1.0",
    "certifi": "2026.10.23",
    "cffi": "2.1.1",
    "charset-normalizer": "3.5.2",
    "cloudpickle": "3.1.2",
    "contourpy": "1.3.3",
    "cycler": "0.12.1",
    "decorator": "5.3.1",
    "descript-audio-codec": "1.0.0",
    "descript-audiotools": "0.7.4",
    "docstring-parser": "0.18.0",
    "einops": "0.8.1",
    "executing": "2.3.0",
    "ffmpy": "1.0.0",
    "filelock": "4.2.10",
    "fire": "0.7.1",
    "flatten-dict": "0.5.0",
    "fonttools": "4.68.0",
    "fsspec": "2024.3.1",
    "grpcio": "1.85.1",
    "huggingface-hub": "0.29.3",
    "idna": "3.20",
    "importlib-resources": "7.1.0",
    "ipython": "9.18.1",
    "ipython-pygments-lexers": "1.1.1",
    "jedi": "0.20.1",
    "jinja2": "3.1.6",
    "joblib": "1.6.0",
    "julius": "0.2.8",
    "kiwisolver": "1.5.1",
    "lazy-loader": "0.6",
    "librosa": "0.10.2.post1",
    "llvmlite": "0.44.0",
    "markdown": "3.11.3",
    "markdown-it-py": "4.3.0",
    "markdown2": "2.5.5",
    "markupsafe": "3.0.4",
    "matplotlib": "3.11.2",
    "matplotlib-inline": "0.2.2",
    "mdurl": "0.1.2",
    "mpmath": "1.3.0",
    "msgpack": "1.2.4",
    "narwhals": "2.28.0",
    "networkx": "3.6.1",
    "numba": "0.61.0",
    "numpy": "1.26.4",
    "nvidia-cublas-cu12": "12.4.5.8",
    "nvidia-cuda-cupti-cu12": "12.4.127",
    "nvidia-cuda-nvrtc-cu12": "12.4.127",
    "nvidia-cuda-runtime-cu12": "12.4.127",
    "nvidia-cudnn-cu12": "9.1.0.70",
    "nvidia-cufft-cu12": "11.2.1.3",
    "nvidia-curand-cu12": "10.3.5.147",
    "nvidia-cusolver-cu12": "11.6.1.9",
    "nvidia-cusparse-cu12": "12.3.1.170",
    "nvidia-cusparselt-cu12": "0.6.2",
    "nvidia-nccl-cu12": "2.21.5",
    "nvidia-nvjitlink-cu12": "12.4.127",
    "nvidia-nvtx-cu12": "12.4.127",
    "packaging": "26.3",
    "parler-tts": "0.2.2",
    "parso": "0.8.7",
    "pexpect": "4.9.0",
    "pillow": "13.0.0",
    "platformdirs": "4.14.5",
    "pooch": "1.9.0",
    "prompt-toolkit": "3.0.53",
    "protobuf": "4.25.8",
    "psutil": "7.2.2",
    "ptyprocess": "0.7.0",
    "pure-eval": "0.2.4",
    "pycparser": "3.12",
    "pygments": "2.21.0",
    "pyloudnorm": "0.2.0",
    "pyparsing": "3.3.3",
    "pystoi": "0.4.1",
    "python-dateutil": "4.0.0",
    "pyyaml": "6.0.3",
    "randomname": "0.2.1",
    "regex": "2026.11.9",
    "requests": "2.34.2",
    "rich": "15.0.0",
    "safetensors": "0.5.3",
    "scikit-learn": "1.9.1",
    "scipy": "1.15.2",
    "sentencepiece": "0.2.0",
    "setuptools": "75.8.2",
    "soundfile": "0.13.1",
    "soxr": "1.1.0",
    "stack-data": "0.6.3",
    "sympy": "1.13.1",
    "tensorboard": "2.20.0",
    "tensorboard-data-server": "0.7.2",
    "termcolor": "3.3.0",
    "threadpoolctl": "3.8.0",
    "tokenizers": "0.20.3",
    "torch": "2.6.0",
    "torch-stoi": "0.2.3",
    "torchaudio": "2.6.0",
    "tqdm": "4.70.1",
    "traitlets": "5.16.1",
    "transformers": "4.46.1",
    "triton": "3.2.0",
    "typing-extensions": "4.16.0",
    "tzdata": "2026.6",
    "urllib3": "2.8.0",
    "wcwidth": "0.9.4",
    "werkzeug": "3.1.9"
}


class EnglishQualificationContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.profile_path = self.root / "profile.json"
        self.job_path = self.root / "job.json"
        rights = self.root / "synthetic-rights.json"
        rights.write_text('{"fixture":"synthetic test only, no real rights claim"}')
        source = self.root / "synthetic-source.txt"
        source.write_text("Synthetic first sentence.\n\nSynthetic second sentence.")
        self.profile = {
            "schema": "earnalism.voice_profile.v1", "identity": voice.IDENTITY,
            "backend": voice.BACKEND,
            "base": {"model_id": voice.BASE_ID, "revision": voice.BASE_REVISION,
                     "sha256": voice.BASE_SHA256},
            "rights": {"status": "CLEARED", "evidence": self.descriptor(rights)},
            "assets": {"model_dir": "model", "description_tokenizer_dir": "description",
                       "source_root": "source", "files": [
                           {"path": "model/model.safetensors", "bytes": 1,
                            "sha256": voice.BASE_SHA256}]},
            "checkpoint": {**deepcopy(voice.BALANCED_CHECKPOINT),
                           "path": "synthetic-not-materialized-checkpoint.pt"},
            "runtime": {"python": "3.12", "packages": deepcopy(LINUX_PACKAGES),
                        "qualification_platform": {"system": "Linux", "machine": "x86_64",
                                                   "device": "cuda:0"}},
            "qualification_route": deepcopy(voice.EN_ROUTE_BINDING),
            "qualification": {"en": {"status": "UNQUALIFIED"},
                              "bn": {"status": "UNQUALIFIED"}},
        }
        self.write(self.profile_path, self.profile)
        spoken = ["Synthetic first sentence.", "Synthetic second sentence."]
        text = source.read_text()
        units = [{"id": "synthetic-" + str(i), "start": text.index(line),
                  "end": text.index(line) + len(line), "spoken_text": line,
                  "caption_unspoken": "Neutral fixture narration.", "seed": i + 10,
                  "context": "Synthetic fixture context, never a book passage."}
                 for i, line in enumerate(spoken)]
        self.job = {
            "schema": "earnalism.voice_job.v1", "purpose": "qualification",
            "language": "en", "device": "cuda:0", "request_id": voice.EN_REQUEST,
            "source": self.descriptor(source), "profile": self.descriptor(self.profile_path),
            "units": units,
            "generation": {"do_sample": True, "temperature": 1.0, "top_k": 50,
                           "top_p": 1.0, "max_new_tokens": 32},
            "limits": {"max_audio_seconds": 180, "max_output_bytes": 32 * 1024**2},
        }
        self.write(self.job_path, self.job)
        fingerprints = [voice.object_sha({
            "source_sha256": self.job["source"]["sha256"],
            **{key: unit[key] for key in
               ["start", "end", "spoken_text", "caption_unspoken", "seed"]},
            "generation": self.job["generation"],
            "checkpoint_sha256": self.profile["checkpoint"]["sha256"],
        }) for unit in units]
        self.addCleanup(patch.stopall)
        patch.object(voice, "EN_SOURCE_SHA256", self.job["source"]["sha256"]).start()
        patch.object(voice, "EN_UNIT_FINGERPRINTS", fingerprints).start()

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, sort_keys=True))

    @staticmethod
    def descriptor(path):
        value = path.read_bytes()
        return {"path": path.name, "bytes": len(value),
                "sha256": hashlib.sha256(value).hexdigest()}

    def plan(self):
        return voice.validate_job(self.job_path)

    def update_profile(self, profile):
        self.write(self.profile_path, profile)
        self.job["profile"] = self.descriptor(self.profile_path)
        self.write(self.job_path, self.job)

    def authority_fixture(self, plan):
        return {
            "schema": "earnalism.voice_execution.v1", "approved": True,
            "actual_scope_ref": "SYNTHETIC_TEST_ONLY_NOT_AUTHORITY",
            "job_sha256": plan["job_sha256"],
            "profile_sha256": plan["binding"]["profile_sha256"],
            "code_sha256": voice.digest(voice.__file__),
            "runtime_code_sha256": voice.digest(voice.RUNTIME),
            "purpose": "qualification", "training_allowed": False,
            "network_allowed": False, "publication_allowed": False,
            "allowed_unit_fingerprints": plan["unit_fingerprints"],
            "max_units": 2, "journal_path": str(self.root / "synthetic-journal.jsonl"),
            "execution_mode": "allocation", "allocation_started_at": 900,
            "absolute_deadline_epoch": 3595, "allocation_shutdown_deadline_epoch": 3600,
            "request_id": voice.EN_REQUEST, "max_model_loads": 1, "max_restores": 1,
            "max_generate_calls": 2, "package_setup_allowed": False,
            "provider": "google_colab", "device_type": "L4", "purchases_allowed": False,
            "max_existing_compute_units": 3, "provider_runtime_id": "SYNTHETIC_RUNTIME",
        }

    def test_metadata_validation_uses_standard_library_only(self):
        with patch("builtins.__import__", side_effect=_without_ml_import):
            plan = self.plan()
        self.assertEqual(len(LINUX_PACKAGES), 111)
        self.assertEqual(voice.object_sha(LINUX_PACKAGES), voice.EN_PACKAGES_SHA256)
        self.assertEqual(plan["unit_fingerprints"], voice.EN_UNIT_FINGERPRINTS)
        self.assertFalse(plan["binding"]["production_accepted"])
        self.assertFalse(plan["binding"]["model_loaded"])
        self.assertEqual(plan["binding"]["checkpoint_sha256"],
                         voice.BALANCED_CHECKPOINT["sha256"])

    def test_english_route_rejects_bengali_and_production(self):
        for language, purpose in [("bn", "qualification"), ("en", "production")]:
            with self.subTest(language=language, purpose=purpose), \
                    self.assertRaises(voice.VoiceBlocked):
                voice._profile(self.profile_path, language, purpose, verify_assets=None)

    def test_old_male_checkpoint_cannot_be_relabelled(self):
        profile = deepcopy(self.profile)
        profile["checkpoint"] = {
            "format": "EARNALISM_PARLER_LAST_BLOCK_V1", "training_updates": 130,
            "sha256": voice.TRAINED_SHA256, "bytes": voice.TRAINED_BYTES,
            "bindings_sha256": voice.TRAINED_BINDINGS_SHA256,
            "tensor_sha256": voice.TRAINED_TENSOR_SHA256, "path": "old-checkpoint.pt",
        }
        self.update_profile(profile)
        with self.assertRaisesRegex(voice.VoiceBlocked, "balanced128"):
            self.plan()

    def test_runtime_platform_lock_and_reference_claim_cannot_drift(self):
        for change in [
            lambda p: p["runtime"]["packages"].update(torch="2.7.0"),
            lambda p: p["runtime"].update(python="3.11"),
            lambda p: p["runtime"]["qualification_platform"].update(device="cpu"),
            lambda p: p["runtime"].update(local_cpu={"system": "Darwin"}),
            lambda p: p["qualification_route"].update(reference_conditioning=True),
        ]:
            profile = deepcopy(self.profile)
            change(profile)
            self.update_profile(profile)
            with self.subTest(profile=profile["runtime"]["python"]), \
                    self.assertRaises(voice.VoiceBlocked):
                self.plan()

    def test_source_pin_cannot_be_replaced_even_with_updated_descriptor(self):
        path = self.root / "synthetic-source.txt"
        path.write_text(path.read_text() + " Extra synthetic source.")
        self.job["source"] = self.descriptor(path)
        self.write(self.job_path, self.job)
        with self.assertRaises(voice.VoiceBlocked):
            self.plan()

    def test_spoken_caption_seed_or_unit_boundary_mutation_is_rejected(self):
        baseline = deepcopy(self.job)
        changes = [
            lambda j: j["units"][0].update(caption_unspoken="Changed fixture direction."),
            lambda j: j["units"][0].update(seed=99),
            lambda j: j["units"][0].update(spoken_text="Altered fixture words."),
            lambda j: j["units"][0].update(start=1),
            lambda j: j["units"][0].update(reference_audio="synthetic.wav"),
        ]
        for change in changes:
            job = deepcopy(baseline)
            change(job)
            self.write(self.job_path, job)
            with self.subTest(change=change), self.assertRaises(voice.VoiceBlocked):
                self.plan()

    def test_english_job_does_not_reuse_cpu_or_bengali_route(self):
        for change in [
            lambda j: j.update(device="cpu"),
            lambda j: j.update(language="bn"),
            lambda j: j.update(request_id=voice.CPU_REQUEST),
            lambda j: j.update(amendment_id=voice.CPU_AMENDMENT),
        ]:
            job = deepcopy(self.job)
            change(job)
            self.write(self.job_path, job)
            with self.subTest(change=change), self.assertRaises(voice.VoiceBlocked):
                self.plan()

    def test_generation_caps_and_third_take_cannot_expand(self):
        for change in [
            lambda j: j["limits"].update(max_audio_seconds=181),
            lambda j: j["limits"].update(max_output_bytes=32 * 1024**2 + 1),
            lambda j: j["generation"].update(max_new_tokens=33),
            lambda j: j["units"].append(deepcopy(j["units"][0])),
        ]:
            job = deepcopy(self.job)
            change(job)
            self.write(self.job_path, job)
            with self.subTest(change=change), self.assertRaises(voice.VoiceBlocked):
                self.plan()

    def test_exact_authority_preserves_original_clock_and_caps_without_dispatch(self):
        plan = self.plan()
        original = self.authority_fixture(plan)
        path = self.root / "synthetic-authority.json"
        self.write(path, original)
        with patch.object(voice.time, "time", return_value=1000):
            self.assertEqual(voice._authority(path, plan)["max_generate_calls"], 2)
            for changes in [
                {"approved": False}, {"max_generate_calls": 3},
                {"absolute_deadline_epoch": 3596},
                {"allocation_shutdown_deadline_epoch": 3601},
                {"request_id": voice.CPU_REQUEST}, {"execution_mode": "local_cpu"},
                {"publication_allowed": True}, {"training_allowed": True},
            ]:
                self.write(path, {**original, **changes})
                with self.subTest(changes=changes), self.assertRaises(voice.VoiceBlocked):
                    voice._authority(path, plan)
        self.assertFalse((self.root / "synthetic-journal.jsonl").exists())

    def fake_run(self, output, sampler, check=lambda: None):
        plan = self.plan()
        output.mkdir()
        bundle = {"model": object(), "loading_report": {"synthetic": True}}
        journal = self.root / "synthetic-native-journal.jsonl"
        with patch.object(runtime, "_load_bundle", return_value=(bundle, object())) as load, \
                patch.object(runtime, "BundleSampler", sampler), \
                patch.object(runtime, "_verify_en_state") as frozen, \
                patch.dict(runtime.os.environ, {}, clear=True), \
                patch("builtins.__import__", side_effect=_without_ml_import):
            result = runtime.run(
                plan, self.profile,
                {"absolute_deadline_epoch": 10**12, "journal_path": str(journal)}, output,
                checkpoint_loader=lambda *a, **k: Path("SYNTHETIC_NOT_LOADED"),
                append_event=voice._append, write_json=self.write, check_authority=check,
            )
        return result, load, frozen, journal

    def test_two_native_takes_preserve_float_bytes_receipts_and_journal_order(self):
        calls = []
        samples = [[0.0, -0.0, 0.25, -0.5], [0.125, 0.0, -0.25]]
        class Sampler:
            def __init__(self, *args): pass
            def generate(self, unit, generation):
                calls.append(unit["id"])
                return samples[len(calls) - 1], False
        output = self.root / "synthetic-native"
        result, load, frozen, journal = self.fake_run(output, Sampler)
        self.assertEqual(load.call_count, 1)
        self.assertEqual(frozen.call_count, 2)
        self.assertEqual(calls, [u["id"] for u in self.job["units"]])
        self.assertEqual(result["training_updates_in_this_run"], 0)
        self.assertEqual(result["network_calls"], 0)
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(result["fidelity_naturalness_accent_and_mix"], "UNPERFORMED")
        for receipt, values in zip(result["outputs"], samples):
            raw = (output / receipt["path"]).read_bytes()
            expected = array.array("f", values)
            if sys.byteorder != "little": expected.byteswap()
            self.assertEqual(raw[44:], expected.tobytes())
            self.assertEqual(receipt["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(receipt["frames"], len(values))
            self.assertEqual(receipt["gain"], 1.0)
            self.assertFalse(receipt["trimmed"] or receipt["regenerated"])
        events = [json.loads(line) for line in journal.read_text().splitlines()]
        self.assertEqual([event["event"] for event in events],
                         ["unit_intent", "unit_completed", "unit_intent", "unit_completed"])
        self.assertEqual([event["fingerprint"] for event in events],
                         [fingerprint for fingerprint in voice.EN_UNIT_FINGERPRINTS for _ in range(2)])

    def test_token_cap_keeps_returned_raw_take_and_prevents_second_generation(self):
        calls = []
        class Sampler:
            def __init__(self, *args): pass
            def generate(self, unit, generation):
                calls.append(unit["id"])
                return [0.125, -0.125], True
        output = self.root / "synthetic-cap"
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_NO_RETRY"):
            self.fake_run(output, Sampler)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(list(output.glob("*.wav"))), 1)
        self.assertFalse((output / "RESULT.json").exists())
        receipt = json.loads((output / (calls[0] + ".json")).read_text())
        self.assertTrue(receipt["token_cap_reached"])
        events = [json.loads(line) for line in
                  (self.root / "synthetic-native-journal.jsonl").read_text().splitlines()]
        self.assertEqual([event["event"] for event in events], ["unit_intent", "unit_completed"])
        self.assertTrue(events[-1]["token_cap_reached"])

    def test_late_authority_failure_keeps_first_take_without_replaying_it(self):
        calls = []
        output = self.root / "synthetic-late-failure"
        class Sampler:
            def __init__(self, *args): pass
            def generate(self, unit, generation):
                calls.append(unit["id"])
                return [0.25, -0.25], False
        def check():
            if output.exists() and list(output.glob("*.wav")):
                raise TimeoutError("SYNTHETIC_LATE_DEADLINE")
        with self.assertRaisesRegex(TimeoutError, "SYNTHETIC_LATE_DEADLINE"):
            self.fake_run(output, Sampler, check)
        self.assertEqual(len(calls), 1)
        wavs = list(output.glob("*.wav"))
        self.assertEqual(len(wavs), 1)
        self.assertEqual(len(wavs[0].read_bytes()), 44 + 2 * 4)
        self.assertTrue((output / (calls[0] + ".json")).is_file())
        self.assertFalse((output / "RESULT.json").exists())
        events = [json.loads(line) for line in
                  (self.root / "synthetic-native-journal.jsonl").read_text().splitlines()]
        self.assertEqual([event["event"] for event in events], ["unit_intent"])

    @staticmethod
    def absolute_descriptor(path):
        return {"path": str(path), "bytes": path.stat().st_size,
                "sha256": voice.digest(path)}

    def bridge_fixture(self):
        plan = self.plan()
        authority = self.authority_fixture(plan)
        directory = self.root / "synthetic-owned-runtime"
        (directory / "bin").mkdir(parents=True)
        base = self.root / "synthetic-owned-cp312"
        base.write_text("SYNTHETIC_FILE_NOT_AN_INTERPRETER")
        base.chmod(0o700)
        python = directory / "bin/python"
        python.symlink_to(base)
        wheel_lock = self.root / "synthetic-wheel-lock.json"
        wheel_lock.write_text('{"fixture":"not an installable wheel lock"}')
        patch.object(voice, "EN_WHEELS_LOCK_SHA256", voice.digest(wheel_lock)).start()
        bootstrap = {
            "runtime_dir": str(directory),
            "python_executable": self.absolute_descriptor(base),
            "wheel_manifest": self.absolute_descriptor(wheel_lock),
        }
        setup = {**authority, "package_setup_allowed": True,
                 "package_network_allowed": False,
                 "setup_code_sha256": voice.digest(voice.SETUP),
                 "runtime_dir": str(directory), "runtime_bootstrap": bootstrap}
        setup_path = self.root / "synthetic-setup-authority.json"
        self.write(setup_path, setup)
        result_path = self.root / "synthetic-owned-runtime.setup/RESULT.json"
        result_path.parent.mkdir()
        result = {
            "status": "LOCAL_PACKAGES_READY_NOT_MODEL_QUALIFIED",
            "profile_sha256": plan["binding"]["profile_sha256"],
            "python": str(python), "package_versions": deepcopy(LINUX_PACKAGES),
            "original_deadline": authority["absolute_deadline_epoch"],
            "model_loading": False, "training": False,
            "setup_authority_sha256": voice.digest(setup_path),
            "actual_scope_ref": authority["actual_scope_ref"],
            "provider_runtime_id": authority["provider_runtime_id"],
            "allocation_started_at": authority["allocation_started_at"],
            "journal_path": authority["journal_path"], "request_id": voice.EN_REQUEST,
            "job_sha256": plan["job_sha256"], "runtime_bootstrap": bootstrap,
        }
        self.write(result_path, result)
        fingerprint = voice.object_sha({
            "profile_sha256": plan["binding"]["profile_sha256"],
            "runtime_dir": str(directory),
        })
        journal = Path(authority["journal_path"])
        journal.write_text(
            json.dumps({"event": "package_setup_intent", "fingerprint": fingerprint}) + "\n" +
            json.dumps({"event": "package_setup_completed", "fingerprint": fingerprint,
                        "result_sha256": voice.digest(result_path)}) + "\n")
        library = self.root / "libcuda.so.1"
        library.write_text("SYNTHETIC_FILE_NOT_A_SHARED_LIBRARY")
        spec = importlib.util.spec_from_file_location("_synthetic_provider_renderer", voice.PROVIDER_DRIVER)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        startup = directory / "lib/python3.12/site-packages/sitecustomize.py"
        startup.parent.mkdir(parents=True)
        startup.write_text(helper.render_preload_source(self.absolute_descriptor(library)))
        preload = {
            "schema": "earnalism.provider_driver_preload.v1",
            "state": "EXACT_PROVIDER_DRIVER_PRELOAD_INSTALLED_NOT_CUDA_QUALIFIED",
            "credential_stripped_worker_env": "UNCHANGED",
            "bootstrap": self.absolute_descriptor(startup),
            "provider_binding": {
                "schema": "earnalism.provider_driver_binding.v1",
                "state": "ACTUAL_PROVIDER_LIBRARY_RESOLVED_NOT_CUDA_QUALIFIED",
                "library_family": "CUDA_DRIVER", "soname": "libcuda.so.1",
                "library": self.absolute_descriptor(library),
            },
        }
        preload_path = self.root / "synthetic-preload-receipt.json"
        self.write(preload_path, preload)
        authority.update(
            runtime_bootstrap=bootstrap,
            runtime_setup_authority=self.absolute_descriptor(setup_path),
            runtime_setup_receipt=self.absolute_descriptor(result_path),
            provider_driver_preload=self.absolute_descriptor(preload_path),
            runtime_interpreter={**self.absolute_descriptor(base), "path": str(python),
                                 "resolved_path": str(base)},
        )
        authority_path = self.root / "synthetic-native-authority.json"
        self.write(authority_path, authority)
        current = {"python": "3.12", "packages": deepcopy(LINUX_PACKAGES),
                   "sitecustomize": str(startup), "provider_preloaded": True}
        return SimpleNamespace(plan=plan, authority=authority, authority_path=authority_path,
                               directory=directory, python=python, current=current,
                               result_path=result_path, setup_path=setup_path, journal=journal)

    def test_bridge_selects_owned_cp312_using_only_mocked_metadata_probe(self):
        fixture = self.bridge_fixture()
        with patch.object(voice.sys, "platform", "linux"), \
                patch.object(voice.platform, "machine", return_value="x86_64"), \
                patch.object(voice.time, "time", return_value=1000), \
                patch.object(voice.subprocess, "run",
                             return_value=SimpleNamespace(stdout=json.dumps(fixture.current))) as probe, \
                patch.object(voice.subprocess, "Popen") as native:
            selected = voice._linux_interpreter(
                self.profile, fixture.plan, fixture.authority, self.root)
        self.assertEqual(selected, str(fixture.python))
        self.assertEqual(probe.call_args.args[0][:4], [str(fixture.python), "-I", "-B", "-c"])
        self.assertEqual(probe.call_args.kwargs["env"], {
            "PATH": voice.os.defpath, "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(probe.call_args.kwargs["timeout"], 20)
        native.assert_not_called()

    def test_render_launches_owned_interpreter_instead_of_notebook_kernel(self):
        fixture = self.bridge_fixture()
        process = SimpleNamespace(wait=lambda **kwargs: 1, poll=lambda: 1, pid=999999999)
        output = self.root / "synthetic-dispatch-output"
        with patch.object(voice.sys, "platform", "linux"), \
                patch.object(voice.platform, "machine", return_value="x86_64"), \
                patch.object(voice.sys, "executable", "/synthetic/notebook/kernel-python"), \
                patch.object(voice.time, "time", return_value=1000), \
                patch.object(voice.subprocess, "run",
                             return_value=SimpleNamespace(stdout=json.dumps(fixture.current))), \
                patch.object(voice.subprocess, "Popen", return_value=process) as native, \
                patch.object(voice, "_stop_owned_group"), self.assertRaises(voice.VoiceBlocked):
            voice.render(self.job_path, output, fixture.authority_path)
        native.assert_called_once()
        self.assertEqual(native.call_args.args[0][:3], [str(fixture.python), "-I", "-B"])
        self.assertNotIn("LD_LIBRARY_PATH", native.call_args.kwargs["env"])
        self.assertNotIn("LD_PRELOAD", native.call_args.kwargs["env"])
        events = [json.loads(line) for line in fixture.journal.read_text().splitlines()]
        self.assertEqual([event["event"] for event in events[-2:]],
                         ["render_intent", "render_failed_or_unknown"])
        self.assertTrue((output / "FAILURE.json").is_file())

    def test_missing_or_changed_setup_receipt_stops_before_probe_native_or_intent(self):
        fixture = self.bridge_fixture()
        original = fixture.result_path.read_bytes()
        journal_before = fixture.journal.read_bytes()
        output = self.root / "synthetic-rejected-output"
        for change in ["missing", "changed"]:
            if change == "missing":
                fixture.result_path.unlink()
            else:
                fixture.result_path.write_bytes(original + b" ")
            with self.subTest(change=change), patch.object(voice.sys, "platform", "linux"), \
                    patch.object(voice.platform, "machine", return_value="x86_64"), \
                    patch.object(voice.time, "time", return_value=1000), \
                    patch.object(voice.subprocess, "run") as probe, \
                    patch.object(voice.subprocess, "Popen") as native, \
                    self.assertRaises(voice.VoiceBlocked):
                voice.render(self.job_path, output, fixture.authority_path)
            fixture.result_path.write_bytes(original)
            probe.assert_not_called()
            native.assert_not_called()
            self.assertEqual(fixture.journal.read_bytes(), journal_before)
            self.assertFalse(output.exists())

    def test_setup_clock_cannot_be_rebound_by_rehashing_authority(self):
        fixture = self.bridge_fixture()
        setup = json.loads(fixture.setup_path.read_text())
        setup["absolute_deadline_epoch"] -= 1
        self.write(fixture.setup_path, setup)
        fixture.authority["runtime_setup_authority"] = self.absolute_descriptor(fixture.setup_path)
        self.write(fixture.authority_path, fixture.authority)
        before = fixture.journal.read_bytes()
        output = self.root / "synthetic-clock-drift-output"
        with patch.object(voice.sys, "platform", "linux"), \
                patch.object(voice.platform, "machine", return_value="x86_64"), \
                patch.object(voice.time, "time", return_value=1000), \
                patch.object(voice.subprocess, "run") as probe, \
                patch.object(voice.subprocess, "Popen") as native, \
                self.assertRaises(voice.VoiceBlocked):
            voice.render(self.job_path, output, fixture.authority_path)
        probe.assert_not_called()
        native.assert_not_called()
        self.assertEqual(fixture.journal.read_bytes(), before)
        self.assertFalse(output.exists())

    def test_selected_abi_package_or_startup_drift_stops_before_native_intent(self):
        fixture = self.bridge_fixture()
        before = fixture.journal.read_bytes()
        output = self.root / "synthetic-package-drift-output"
        for change in [
            lambda metadata: metadata.update(python="3.13"),
            lambda metadata: metadata["packages"].update(torch="2.7.0"),
            lambda metadata: metadata.update(provider_preloaded=False),
        ]:
            current = deepcopy(fixture.current)
            change(current)
            with self.subTest(change=change), patch.object(voice.sys, "platform", "linux"), \
                    patch.object(voice.platform, "machine", return_value="x86_64"), \
                    patch.object(voice.time, "time", return_value=1000), \
                    patch.object(voice.subprocess, "run",
                                 return_value=SimpleNamespace(stdout=json.dumps(current))) as probe, \
                    patch.object(voice.subprocess, "Popen") as native, \
                    self.assertRaises(voice.VoiceBlocked):
                voice.render(self.job_path, output, fixture.authority_path)
            probe.assert_called_once()
            native.assert_not_called()
            self.assertEqual(fixture.journal.read_bytes(), before)
            self.assertFalse(output.exists())

    def test_incomplete_setup_journal_does_not_create_replay_pool(self):
        fixture = self.bridge_fixture()
        fixture.journal.write_text(fixture.journal.read_text().splitlines()[0] + "\n")
        before = fixture.journal.read_bytes()
        output = self.root / "synthetic-incomplete-setup-output"
        with patch.object(voice.sys, "platform", "linux"), \
                patch.object(voice.platform, "machine", return_value="x86_64"), \
                patch.object(voice.time, "time", return_value=1000), \
                patch.object(voice.subprocess, "run") as probe, \
                patch.object(voice.subprocess, "Popen") as native, \
                self.assertRaisesRegex(voice.VoiceBlocked, "One completed original package attempt"):
            voice.render(self.job_path, output, fixture.authority_path)
        probe.assert_not_called()
        native.assert_not_called()
        self.assertEqual(fixture.journal.read_bytes(), before)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
