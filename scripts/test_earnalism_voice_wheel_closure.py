"""Real, tiny offline pip probes; no model, network, or GPU qualification."""
import csv
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from scripts.earnalism_voice_runtime import setup


class EnglishWheelClosureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="earnalism-wheel-closure-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.wheels = self.root / "wheels"
        self.wheels.mkdir()
        self.environment = {
            "PATH": os.defpath, "LANG": "C.UTF-8", "PIP_CONFIG_FILE": os.devnull,
            "PIP_NO_INDEX": "1", "PYTHONNOUSERSITE": "1", "CUDA_VISIBLE_DEVICES": "",
            "PYTHONDONTWRITEBYTECODE": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1",
        }

    def wheel(self, name, version, requirements=()):
        normalized = name.replace("-", "_")
        info = normalized + "-" + version + ".dist-info"
        files = {
            normalized + ".py": b"raise AssertionError('Fixture must never be imported')\n",
            info + "/METADATA": (
                "Metadata-Version: 2.1\nName: " + name + "\nVersion: " + version + "\n"
                + "".join("Requires-Dist: " + row + "\n" for row in requirements) + "\n"
            ).encode(),
            info + "/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        }
        record = io.StringIO()
        writer = csv.writer(record)
        for filename in list(files) + [info + "/RECORD"]:
            writer.writerow([filename, "", ""])
        files[info + "/RECORD"] = record.getvalue().encode()
        path = self.wheels / (normalized + "-" + version + "-py3-none-any.whl")
        with zipfile.ZipFile(path, "x") as archive:
            for filename, data in files.items():
                archive.writestr(filename, data)
        return name + "==" + version + " --hash=sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

    def commands(self, *, omit_dependency=False, core_version="2.1"):
        # A local file VCS locator cannot reach a network service. Pip must not
        # resolve it: the actual retained Parler wheel uses a Git URL instead.
        rows = [self.wheel("earnalism-fixture-root", "0.2.2", [
            "earnalism-fixture-audiotools @ git+file:///must-not-access-earnalism-fixture",
            "earnalism-fixture-core>=2.0",
        ]), self.wheel("earnalism-fixture-core", core_version)]
        if not omit_dependency:
            rows.append(self.wheel("earnalism-fixture-audiotools", "0.7.4"))
        requirements = self.root / "requirements.lock.txt"
        requirements.write_text("\n".join(rows) + "\n")
        return setup._english_install_commands(
            Path(sys.executable), self.root / "owned-venv", self.wheels, requirements)

    def run_command(self, command):
        return subprocess.run(command, env=self.environment, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=45)

    def prepare(self, commands):
        result = self.run_command(commands[0])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_original_resolver_reproduces_unhashable_vcs_failure(self):
        commands = self.commands()
        self.prepare(commands)
        original = [arg for arg in commands[1] if arg != "--no-deps"]
        result = self.run_command(original)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash", (result.stdout + result.stderr).lower())
        self.assertIn("version control", (result.stdout + result.stderr).lower())

    def test_exact_hashed_closure_installs_and_dependency_check_passes(self):
        commands = self.commands()
        for command in commands:
            result = self.run_command(command)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_dependency_still_fails_pip_check(self):
        commands = self.commands(omit_dependency=True)
        self.prepare(commands)
        installed = self.run_command(commands[1])
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        checked = self.run_command(commands[2])
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("not installed", checked.stdout + checked.stderr)

    def test_incompatible_dependency_still_fails_pip_check(self):
        commands = self.commands(core_version="1.0")
        self.prepare(commands)
        installed = self.run_command(commands[1])
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        checked = self.run_command(commands[2])
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("earnalism-fixture-core>=2.0", checked.stdout + checked.stderr)
        self.assertIn("1.0", checked.stdout + checked.stderr)

    def test_changed_wheel_still_fails_hash_verification(self):
        commands = self.commands()
        root_wheel = next(self.wheels.glob("earnalism_fixture_root-*.whl"))
        with root_wheel.open("ab") as handle:
            handle.write(b"changed bytes")
        self.prepare(commands)
        result = self.run_command(commands[1])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash", (result.stdout + result.stderr).lower())


if __name__ == "__main__":
    unittest.main()
