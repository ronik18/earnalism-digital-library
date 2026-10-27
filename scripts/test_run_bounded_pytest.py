"""Real child-process checks: success, assertion failure and a hung test stay distinct."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from scripts.run_bounded_pytest import run_tests


class BoundedPytestTests(unittest.TestCase):
    def run_case(self, source, *, timeout=15, trace=10):
        with tempfile.TemporaryDirectory(prefix="bounded-pytest-") as directory:
            target = Path(directory) / "test_dummy.py"
            target.write_text(source)
            with tempfile.TemporaryFile(mode="w+") as output, contextlib.redirect_stderr(io.StringIO()):
                return run_tests(["-q", str(target)], timeout_seconds=timeout, trace_seconds=trace, output=output)

    def test_passing_child_is_the_only_success(self):
        self.assertEqual(self.run_case("def test_dummy(): assert True\n"), 0)

    def test_assertion_failure_remains_failure(self):
        self.assertEqual(self.run_case("def test_dummy(): assert False\n"), 1)

    def test_hung_test_cannot_be_reported_as_pass(self):
        self.assertEqual(self.run_case("import time\ndef test_dummy(): time.sleep(60)\n", timeout=2, trace=1), 124)

    def test_invalid_deadline_is_rejected_before_start(self):
        for timeout, trace in [(0, 1), (1, 0), (1, 2)]:
            with self.assertRaises(ValueError):
                run_tests(["not-executed"], timeout_seconds=timeout, trace_seconds=trace)


class FixtureDeadlineTests(unittest.TestCase):
    def test_limits_cannot_be_disabled_or_extended(self):
        from scripts.uat_mongo_fixture import CLIENT_DEADLINES_MS, bounded_client_options
        for key, limit in CLIENT_DEADLINES_MS.items():
            for invalid in (None, 0, -1, True, limit + 1):
                with self.subTest(option=key, value=invalid), self.assertRaises(ValueError):
                    bounded_client_options({key: invalid})

    def test_shorter_limits_preserve_other_client_controls(self):
        from scripts.uat_mongo_fixture import bounded_client_options
        options = {"socketTimeoutMS": 500, "retryWrites": False}
        result = bounded_client_options(options)
        self.assertEqual(result["socketTimeoutMS"], 500)
        self.assertIs(result["retryWrites"], False)
        self.assertEqual(result["serverSelectionTimeoutMS"], 3000)
        self.assertEqual(options, {"socketTimeoutMS": 500, "retryWrites": False})
