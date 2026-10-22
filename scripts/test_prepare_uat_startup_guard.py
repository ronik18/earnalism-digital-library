"""Targeted fixture qualification; no app import, network or tests by default."""

import asyncio
import ast
import base64
import os
from pathlib import Path
import secrets
import shlex
import shutil
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.prepare_uat_startup_guard import prepare, validate_target


class TargetTests(unittest.TestCase):
    def test_rejects_non_uat_or_nonisolated_target_before_io(self):
        base = {"ENVIRONMENT": "uat", "UAT_MONGODB_PORT": "27099"}
        self.assertEqual(validate_target(base), 27099)
        for changes in ({"ENVIRONMENT": "production"}, {"DB_NAME": "earnalism"},
                        {"UAT_BACKEND_HOST": "example.invalid"},
                        {"UAT_MONGODB_PORT": "27017"}, {"UAT_MONGODB_PORT": "bad"}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, KeyError)):
                validate_target(dict(base, **changes))

    def test_fixture_precedes_backend_launch_without_guard_bypass(self):
        source = Path(__file__).with_name("start_local_uat.sh").read_text()
        self.assertLess(source.index("scripts/prepare_uat_startup_guard.py"),
                        source.index("-m uvicorn backend.server:app"))
        self.assertLess(source.index('source "$UAT_MONGO_FIXTURE_DIR/startup-guard.env"'),
                        source.index("-m uvicorn backend.server:app"))
        self.assertIn('--auth --keyFile "$MONGODB_KEYFILE"', source)
        self.assertIn('env -u UAT_MONGO_SETUP_FILE "$VENV_PYTHON" -m uvicorn', source)


@unittest.skipUnless(os.environ.get("UAT_GUARD_FIXTURE_INTEGRATION") == "1",
                     "explicit disposable local MongoDB fixture qualification only")
class FixtureIntegrationTests(unittest.TestCase):
    def test_real_restricted_fixture_passes_unmodified_guard(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        from pymongo import MongoClient
        from pymongo.errors import OperationFailure
        from backend.startup_data_guard import verify_startup_data

        mongod = shutil.which("mongod")
        self.assertIsNotNone(mongod, "local mongod required")
        # Reserve an unused port in the launcher's isolated range; never stop or
        # reconfigure an existing listener. A bind race fails this fixture.
        port = None
        for candidate in range(27099, 27017, -1):
            with socket.socket() as probe:
                try:
                    probe.bind(("127.0.0.1", candidate))
                    port = candidate
                    break
                except OSError:
                    pass
        self.assertIsNotNone(port, "unused isolated MongoDB port required")
        with tempfile.TemporaryDirectory(prefix="earnalism-guard-fixture-") as directory:
            root = Path(directory)
            (root / "db").mkdir()
            key = root / "keyfile"
            key.write_bytes(base64.b64encode(secrets.token_bytes(512)))
            key.chmod(0o600)
            process = subprocess.Popen([
                mongod, "--auth", "--keyFile", str(key), "--replSet", "earnalism-uat-rs0",
                "--bind_ip", "127.0.0.1", "--port", str(port), "--dbpath", str(root / "db"),
                "--logpath", str(root / "mongodb.log"), "--nounixsocket"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                env = {**os.environ, "ENVIRONMENT": "uat", "DB_NAME": "earnalism_uat",
                       "UAT_FRONTEND_HOST": "127.0.0.1", "UAT_BACKEND_HOST": "127.0.0.1",
                       "UAT_MONGODB_PORT": str(port)}
                init = subprocess.run([os.sys.executable, str(Path(__file__).with_name("init_uat_mongodb.py"))],
                                      env=env, capture_output=True, timeout=55)
                self.assertEqual(init.returncode, 0, "disposable replica bootstrap failed")
                output = root / "fixture.env"
                policy = prepare(env, output)
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                values = {}
                for line in output.read_text().splitlines():
                    assignment = shlex.split(line)[1]
                    name, value = assignment.split("=", 1)
                    values[name] = value
                self.assertNotIn("uat_setup_", output.read_text())
                self.assertEqual(values["DB_NAME"], "earnalism_uat")
                self.assertEqual(len(policy["markers"]), 2)

                async def guard():
                    client = AsyncIOMotorClient(values["MONGODB_URL"], serverSelectionTimeoutMS=3000)
                    try:
                        await verify_startup_data(client, client["earnalism_uat"],
                                                  values["EARNALISM_STARTUP_DATA_GUARD_JSON"])
                    finally:
                        client.close()
                asyncio.run(guard())
                with MongoClient(values["MONGODB_URL"], serverSelectionTimeoutMS=3000) as app:
                    auth = app.admin.command({"connectionStatus": 1, "showPrivileges": False})
                    self.assertEqual(auth["authInfo"]["authenticatedUserRoles"],
                                     [{"role": "readWrite", "db": "earnalism_uat"}])
                    for operation in (lambda: app["unrelated_fixture"].books.find_one({}),
                                      lambda: app.admin.command("usersInfo")):
                        with self.assertRaises(OperationFailure) as denied:
                            operation()
                        self.assertEqual(denied.exception.code, 13)
                with MongoClient(f"mongodb://127.0.0.1:{port}/?directConnection=true",
                                 serverSelectionTimeoutMS=3000) as anonymous:
                    with self.assertRaises(OperationFailure) as denied:
                        anonymous.earnalism_uat.books.find_one({})
                    self.assertEqual(denied.exception.code, 13)

                # Exercise the changed namespace provisioning and both success
                # and exception cleanup; the application role is never changed.
                from scripts.uat_mongo_fixture import isolated_database, setup_configuration
                fixture_environment = {**env, **values, "READER_SEGMENT_MONGO_INTEGRATION": "1",
                                       "JWT_SECRET": "uat-fixture-local-only-jwt",
                                       "READING_PASS_TOKEN_SECRET": "uat-fixture-local-only-token-0123456789",
                                       "READING_PASS_V2_ENABLED": "true", "COST_CONTROL_MODE": "true",
                                       "ENABLE_BACKGROUND_WORKERS": "false", "ENABLE_STARTUP_DB_MAINTENANCE": "false",
                                       "TRUSTED_DEVICE_MAX_ACTIVE_SESSIONS": "5"}
                config = setup_configuration(fixture_environment)
                async def namespaces():
                    with patch.dict(os.environ, fixture_environment):
                        async with isolated_database("rpseg_it_") as (first, one):
                            async with isolated_database("rpadmit_it_") as (second, two):
                                await one.probe.insert_one({"fixture": 1})
                                await two.probe.insert_one({"fixture": 2})
                                role = await first.admin.command({"connectionStatus": 1, "showPrivileges": False})
                                self.assertEqual(role["authInfo"]["authenticatedUserRoles"],
                                                 [{"role": "readWrite", "db": one.name}])
                                with self.assertRaises(OperationFailure):
                                    await first[two.name].probe.find_one({})
                        with self.assertRaisesRegex(RuntimeError, "fixture-body-stop"):
                            async with isolated_database("rpadmit_it_") as (_, database):
                                await database.probe.insert_one({"fixture": 3})
                                raise RuntimeError("fixture-body-stop")
                asyncio.run(namespaces())

                # Run only tests whose fixture code changed, not their unrelated
                # unit tests or the unchanged 13 startup-guard checks.
                repo = Path(__file__).resolve().parents[1]
                selection = []
                for name in ("test_reader_segment_promotion_mongo_integration.py",
                             "test_reading_pass_text_admission_mongo_integration.py"):
                    path = repo / "backend/tests" / name
                    for node in ast.parse(path.read_text()).body:
                        if (isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
                                and "_isolated_database" in ast.get_source_segment(path.read_text(), node)):
                            selection.append(f"backend/tests/{name}::{node.name}")
                selection.extend([
                    "backend/tests/test_reading_pass_acceptance_budget.py::test_actual_mongo_budget_wallet_ledger_atomicity",
                    "backend/tests/test_reader_acceptance_operator.py::test_actual_mongo_concurrent_enable_cas_has_no_reset_or_wallet_mutation",
                    "backend/tests/test_yugalanguriya_publication_inspection.py::test_real_motor_preserves_max_time_ms_after_prequery_delay",
                    "backend/tests/test_reader_benchmark_mongo_integration.py::test_real_http_login_refresh_lease_and_twenty_page_responses"])
                run = subprocess.run([os.sys.executable, "-m", "pytest", "-q", *selection],
                                     cwd=repo, env=fixture_environment, capture_output=True, text=True, timeout=180)
                if run.returncode:
                    # Avoid printing even disposable credential-bearing URIs.
                    import re
                    diagnostic = re.sub(r"mongodb[^\s\"']*", "[local MongoDB diagnostic redacted]",
                                        run.stdout + run.stderr)
                    self.fail(diagnostic[-10000:])
                print("changed-namespace-fixture-tests: " + run.stdout.splitlines()[0], flush=True)
                with MongoClient(f"mongodb://127.0.0.1:{port}/?directConnection=true",
                                 username=config["principal"], password=config["password"],
                                 authSource="admin", serverSelectionTimeoutMS=3000) as setup:
                    users = setup.admin.command("usersInfo")["users"]
                    self.assertFalse(any(user["user"].startswith("uat_case_") for user in users))
                    self.assertFalse(any(name.startswith(tuple(__import__("scripts.uat_mongo_fixture", fromlist=["PREFIXES"]).PREFIXES))
                                         for name in setup.list_database_names()))
                output.unlink()
                Path(values["UAT_MONGO_SETUP_FILE"]).unlink()
            finally:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
