"""Exercise the catalogue worker's real UID, Git and filesystem preflight.

Run on a disposable Linux runner before the implementation action. These
fixtures never use the application database, credentials or production files.
"""
from pathlib import Path
import os
import pwd
import shutil
import subprocess
import tempfile
import unittest
import sys

from scripts.catalogue_compliance_generated_evidence import CANONICAL, WORKER, preserve_generated_evidence


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/catalogue-compliance-go-live.yml"


def command(args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, timeout=30, **kwargs)


class WorkerPermissionPreflight(unittest.TestCase):
    def setUp(self):
        self.assertEqual(os.name, "posix", "This preflight requires the Linux runner")
        self.assertIsNotNone(shutil.which("sudo"))
        self.assertEqual(command(["sudo", "-n", "true"]).returncode, 0,
                         "The disposable controller must retain sudo")
        self.worker = pwd.getpwnam("nobody")
        self.assertNotEqual(self.worker.pw_uid, 0)
        marker = "      - name: Prepare and verify the unprivileged implementation account\n        run: |\n"
        source = WORKFLOW.read_text().split(marker, 1)[1].split("\n      - name:", 1)[0]
        self.script = source.split("bash -c '", 1)[1].rsplit("' --", 1)[0]
        self.temp = tempfile.TemporaryDirectory(prefix="catalogue-worker-permissions-")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.repo = self.parent / "fixture"
        self.repo.mkdir()
        command(["git", "init", "--quiet", str(self.repo)], check=True)
        (self.repo / "synthetic.txt").write_text("Synthetic worker permission fixture only.\n")
        command(["git", "-C", str(self.repo), "add", "synthetic.txt"], check=True)
        command(["git", "-C", str(self.repo), "-c", "user.name=Fixture",
                 "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "fixture"], check=True)
        self.head = command(["git", "-C", str(self.repo), "rev-parse", "HEAD"], check=True).stdout.strip()
        self.config = self.parent / "gitconfig"
        self.config.write_text("[safe]\n\tdirectory = " + str(self.repo) + "\n")
        self.parent.chmod(0o755)
        command(["sudo", "-n", "chgrp", "-R", str(self.worker.pw_gid), str(self.repo)], check=True)
        command(["sudo", "-n", "chmod", "-R", "g+rwX", str(self.repo)], check=True)
        command(["sudo", "-n", "find", str(self.repo), "-type", "d", "-exec", "chmod", "g+s", "{}", "+"], check=True)

    def run_worker(self, head=None, user="nobody"):
        return command(["sudo", "-n", "-H", "-u", user, "env",
                        "GIT_CONFIG_GLOBAL=" + str(self.config), "bash", "-c", self.script,
                        "--", str(self.repo), head or self.head])

    def test_unprivileged_worker_reads_exact_git_and_writes_clean_shared_checkout(self):
        result = self.run_worker()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(command(["git", "-C", str(self.repo), "status", "--porcelain"]).stdout, "")
        self.assertEqual(list(self.repo.glob(".catalogue-worker-write.*")), [])
        self.assertEqual(command(["sudo", "-n", "true"]).returncode, 0,
                         "Worker preflight must not remove controller privileges")

    def test_controller_recovers_new_worker_files_without_changing_bytes(self):
        code = "from pathlib import Path; import os; p=Path(__import__('sys').argv[1]); p.mkdir(mode=0o750); f=p/'candidate.json'; f.write_text('synthetic candidate bytes\\n'); f.chmod(0o640)"
        folder = self.repo / "new-worker-package"
        command(["sudo", "-n", "-u", "nobody", "python3", "-c", code, str(folder)], check=True)
        owner = command(["id", "-un"], check=True).stdout.strip()
        group = command(["id", "-gn"], check=True).stdout.strip()
        command(["sudo", "-n", "chown", "-R", owner + ":" + group, str(self.repo)], check=True)
        self.assertEqual((folder / "candidate.json").read_text(), "synthetic candidate bytes\n")

    def test_canonical_bootstrap_preserves_one_physical_checkout_and_workspace_alias(self):
        source = WORKFLOW.read_text().split("          # Keep the Codex working directory physical.", 1)[1]
        source = source.split("\n      - uses:", 1)[0]
        script = "# Keep the Codex working directory physical." + source
        canonical = self.parent / "canonical"
        script = script.replace("/tmp/earnalism-main-approved-integration", str(canonical))
        env = {**os.environ, "GITHUB_WORKSPACE": str(self.repo), "GITHUB_SHA": self.head}
        result = command(["bash", "-euo", "pipefail", "-c", script], env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(canonical.is_symlink())
        self.assertTrue(self.repo.is_symlink())
        self.assertEqual(self.repo.resolve(), canonical)
        self.assertEqual((canonical / "synthetic.txt").read_text(), "Synthetic worker permission fixture only.\n")

    def test_worker_generates_separate_reports_when_restored_reports_are_read_only(self):
        canonical = self.repo / CANONICAL
        canonical.mkdir(parents=True)
        historical = canonical / "catalogue_state.json"
        historical.write_text('{"historical":true}\n')
        command(["git", "-C", str(self.repo), "add", CANONICAL], check=True)
        command(["git", "-C", str(self.repo), "-c", "user.name=Fixture",
                 "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "historical reports"], check=True)
        command(["sudo", "-n", "chgrp", "-R", str(self.worker.pw_gid), str(self.repo)], check=True)
        command(["sudo", "-n", "chmod", "-R", "g+rwX", str(self.repo)], check=True)
        command(["sudo", "-n", "find", str(self.repo), "-type", "d", "-exec", "chmod", "g+s", "{}", "+"], check=True)
        historical.chmod(0o644)  # A controller restore creates a new non-group-writable file.
        code = """from pathlib import Path
import sys
historical, output = map(Path, sys.argv[1:])
try:
    historical.write_text('unexpected overwrite')
except PermissionError:
    pass
else:
    raise AssertionError('worker unexpectedly rewrote restored historical evidence')
output.mkdir()
(output/'catalogue_state.json').write_text('{"worker":true}\\n')
"""
        worker = self.repo / WORKER
        result = command(["sudo", "-n", "-u", "nobody", sys.executable, "-c", code,
                          str(historical), str(worker)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(historical.read_text(), '{"historical":true}\n')
        self.assertEqual((worker / "catalogue_state.json").stat().st_uid, self.worker.pw_uid)
        command(["sudo", "-n", "chown", "-R", f"{os.getuid()}:{os.getgid()}", str(self.repo)], check=True)
        archive = preserve_generated_evidence(self.repo)
        self.addCleanup(shutil.rmtree, archive)
        self.assertEqual((archive / worker.name / "catalogue_state.json").read_text(), '{"worker":true}\n')
        self.assertEqual(historical.read_text(), '{"historical":true}\n')
        self.assertFalse(worker.exists())
        self.assertEqual(command(["git", "-C", str(self.repo), "status", "--porcelain"]).stdout, "")

    def test_root_worker_is_rejected(self):
        self.assertNotEqual(self.run_worker(user="root").returncode, 0)

    def test_stale_head_is_rejected(self):
        self.assertNotEqual(self.run_worker(head="0" * 40).returncode, 0)

    def test_dirty_checkout_is_rejected(self):
        (self.repo / "synthetic.txt").write_text("changed synthetic fixture\n")
        self.assertNotEqual(self.run_worker().returncode, 0)


if __name__ == "__main__":
    unittest.main()
