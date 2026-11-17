"""Saved-source regressions; no notebook execution, runtime or provider calls."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import check_colab_scope as checker


class SavedCellScopeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name).resolve() / "private.ipynb"
        self.expected_path = Path(self.directory.name).resolve() / "observed-controls.json"

    def notebook(self, source, extra=()):
        cell = {"cell_type": "code", "metadata": {"id": "admission"}, "source": source}
        self.path.write_text(json.dumps({"cells": [cell, *extra]}))
        return self.path

    def check(self, source, expected=None, extra=()):
        return checker.check_notebook(self.notebook(source, extra), "admission",
                                      {"OBSERVED_ACTUAL_L4": True} if expected is None else expected)

    def assertFailure(self, report, code):
        self.assertEqual(report["state"], "FAIL_SAVED_CELL_LITERAL_BINDINGS")
        self.assertIn(code, [issue["code"] for issue in report["issues"]])
        self.assertFalse(report["execution_authorized"])
        self.assertFalse(report["runtime_qualified"])

    def test_exact_saved_literals_pass_without_executing_code(self):
        source = ["OBSERVED_ACTUAL_L4 = True\n", "RATE = 2.5\n", "DETAIL = {'a': [1, None]}\n",
                  "raise AssertionError('this notebook must never execute')\n"]
        report = self.check(source, {"OBSERVED_ACTUAL_L4": True, "RATE": 2.5,
                                     "DETAIL": {"a": [1, None]}})
        self.assertEqual(report["state"], "PASS_SAVED_CELL_LITERAL_BINDINGS_ONLY")
        self.assertEqual(report["binding_counts"], {"OBSERVED_ACTUAL_L4": 1, "RATE": 1, "DETAIL": 1})
        self.assertEqual(len(report["notebook_sha256"]), 64)
        self.assertEqual(len(report["cell_source_sha256"]), 64)
        self.assertFalse(report["execution_authorized"])

    def test_false_first_true_later_real_failure_pattern_is_rejected(self):
        report = self.check("OBSERVED_ACTUAL_L4 = False\nassert OBSERVED_ACTUAL_L4 is True\n"
                            "OBSERVED_ACTUAL_L4 = True\nassert OBSERVED_ACTUAL_L4 is True\n")
        self.assertFailure(report, "EXACTLY_ONE_BINDING_REQUIRED")
        self.assertEqual(report["binding_counts"]["OBSERVED_ACTUAL_L4"], 2)

    def test_missing_control_is_rejected(self):
        report = self.check("unrelated = True\n")
        self.assertFailure(report, "EXACTLY_ONE_BINDING_REQUIRED")
        self.assertEqual(report["binding_counts"]["OBSERVED_ACTUAL_L4"], 0)

    def test_nonliteral_value_is_rejected(self):
        self.assertFailure(self.check("OBSERVED_ACTUAL_L4 = bool(1)\n"), "LITERAL_VALUE_REQUIRED")

    def test_nested_assignment_is_rejected_even_if_only_binding(self):
        self.assertFailure(self.check("if True:\n    OBSERVED_ACTUAL_L4 = True\n"),
                           "SIMPLE_TOP_LEVEL_ASSIGNMENT_REQUIRED")

    def test_dependent_reads_before_the_only_assignment_are_rejected(self):
        for source in ("assert OBSERVED_ACTUAL_L4 is True\nOBSERVED_ACTUAL_L4 = True\n",
                       "copy = OBSERVED_ACTUAL_L4; OBSERVED_ACTUAL_L4 = True\n",
                       "def later(): return OBSERVED_ACTUAL_L4\nOBSERVED_ACTUAL_L4 = True\n"):
            with self.subTest(source=source):
                report = self.check(source)
                self.assertFailure(report, "CONTROL_READ_PRECEDES_ASSIGNMENT")
                self.assertEqual(report["binding_counts"]["OBSERVED_ACTUAL_L4"], 1)

    def test_dependent_read_after_assignment_passes(self):
        self.assertEqual(self.check("OBSERVED_ACTUAL_L4 = True; assert OBSERVED_ACTUAL_L4 is True\n")["state"],
                         "PASS_SAVED_CELL_LITERAL_BINDINGS_ONLY")

    def test_complex_assignments_are_rejected(self):
        for source in ("OBSERVED_ACTUAL_L4 = other = True\n",
                       "OBSERVED_ACTUAL_L4, other = (True, False)\n",
                       "OBSERVED_ACTUAL_L4: bool = True\n",
                       "(OBSERVED_ACTUAL_L4 := True)\n"):
            with self.subTest(source=source):
                self.assertFailure(self.check(source), "SIMPLE_TOP_LEVEL_ASSIGNMENT_REQUIRED")

    def test_json_types_cannot_coerce_bool_int_or_float(self):
        for source, expected in (("VALUE = 1", True), ("VALUE = True", 1),
                                 ("VALUE = 1", 1.0), ("VALUE = 1.0", 1),
                                 ("VALUE = {'a': [True]}", {"a": [1]}),
                                 ("VALUE = (1, 2)", [1, 2])):
            with self.subTest(source=source):
                self.assertFailure(self.check(source, {"VALUE": expected}), "TYPED_LITERAL_VALUE_MISMATCH")

    def test_binding_in_any_ast_scope_prevents_a_false_unique_pass(self):
        suffixes = ("def OBSERVED_ACTUAL_L4(): pass", "class OBSERVED_ACTUAL_L4: pass",
                    "def f(OBSERVED_ACTUAL_L4): pass", "f = lambda OBSERVED_ACTUAL_L4: None",
                    "for OBSERVED_ACTUAL_L4 in []: pass",
                    "values = [1 for OBSERVED_ACTUAL_L4 in []]",
                    "with resource() as OBSERVED_ACTUAL_L4: pass",
                    "import module as OBSERVED_ACTUAL_L4", "from module import OBSERVED_ACTUAL_L4",
                    "try: pass\nexcept Exception as OBSERVED_ACTUAL_L4: pass",
                    "match value:\n    case OBSERVED_ACTUAL_L4: pass",
                    "match value:\n    case [*OBSERVED_ACTUAL_L4]: pass",
                    "match value:\n    case {**OBSERVED_ACTUAL_L4}: pass",
                    "OBSERVED_ACTUAL_L4 += 1", "del OBSERVED_ACTUAL_L4")
        for suffix in suffixes:
            with self.subTest(suffix=suffix):
                report = self.check("OBSERVED_ACTUAL_L4 = True\n" + suffix + "\n")
                self.assertFailure(report, "EXACTLY_ONE_BINDING_REQUIRED")
                self.assertEqual(report["binding_counts"]["OBSERVED_ACTUAL_L4"], 2)

    def test_unknown_wildcard_bindings_fail_closed(self):
        self.assertFailure(self.check("OBSERVED_ACTUAL_L4 = True\nfrom module import *\n"),
                           "WILDCARD_IMPORT_BINDINGS_UNKNOWN")

    def test_duplicate_cell_ids_are_rejected(self):
        for kind in ("code", "markdown"):
            with self.subTest(kind=kind):
                extra = ({"cell_type": kind, "metadata": {"id": "admission"}, "source": ""},)
                self.assertFailure(self.check("OBSERVED_ACTUAL_L4 = True", extra=extra),
                                   "EXACTLY_ONE_CODE_CELL_ID_REQUIRED")

    def test_other_cell_is_outside_the_reported_scope(self):
        extra = ({"cell_type": "code", "metadata": {"id": "other"},
                  "source": "OBSERVED_ACTUAL_L4 = False\nOBSERVED_ACTUAL_L4 = True"},)
        self.assertEqual(self.check("OBSERVED_ACTUAL_L4 = True", extra=extra)["state"],
                         "PASS_SAVED_CELL_LITERAL_BINDINGS_ONLY")

    def test_invalid_source_and_notebook_are_rejected(self):
        self.assertFailure(self.check("OBSERVED_ACTUAL_L4 ="), "INVALID_CELL_SYNTAX")
        self.path.write_text("not JSON")
        self.assertFailure(checker.check_notebook(self.path, "admission", {"VALUE": True}),
                           "INVALID_NOTEBOOK_JSON")
        self.assertFailure(checker.check_notebook(Path("relative.ipynb"), "admission", {"VALUE": True}),
                           "ABSOLUTE_NOTEBOOK_PATH_REQUIRED")

    def test_cli_does_not_expose_private_expected_or_saved_values(self):
        self.notebook("TOKEN = 'private-saved-literal'")
        self.expected_path.write_text('{"TOKEN":"private-expected-literal"}', encoding="utf-8")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = checker.main(["--notebook", str(self.path), "--cell-id", "admission",
                                   "--expected-json", str(self.expected_path)])
        self.assertEqual(status, 1)
        self.assertNotIn("private-saved-literal", stream.getvalue())
        self.assertNotIn("private-expected-literal", stream.getvalue())
        self.assertFailure(json.loads(stream.getvalue()), "TYPED_LITERAL_VALUE_MISMATCH")

    def test_cli_rejects_duplicate_json_keys_and_nonfinite_values(self):
        self.notebook("VALUE = True")
        for expected in ('{"VALUE":false,"VALUE":true}', '{"VALUE":NaN}', '{"VALUE":Infinity}'):
            self.expected_path.write_text(expected, encoding="utf-8")
            with self.subTest(expected=expected), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(checker.main(["--notebook", str(self.path), "--cell-id", "admission",
                                               "--expected-json", str(self.expected_path)]), 1)
                self.assertFailure(json.loads(output.getvalue()), "INVALID_EXPECTED_LITERAL_MAP")

    def test_cli_reads_absolute_utf8_file_and_has_no_inline_or_relative_fallback(self):
        self.notebook("VALUE = 'বাংলা'")
        self.expected_path.write_text('{"VALUE":"বাংলা"}', encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(checker.main(["--notebook", str(self.path), "--cell-id", "admission",
                                           "--expected-json", str(self.expected_path)]), 0)
            self.assertEqual(json.loads(output.getvalue())["state"], "PASS_SAVED_CELL_LITERAL_BINDINGS_ONLY")
        for supplied in ('{"VALUE":"বাংলা"}', "observed-controls.json"):
            with self.subTest(supplied=supplied), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(checker.main(["--notebook", str(self.path), "--cell-id", "admission",
                                               "--expected-json", supplied]), 1)
                self.assertFailure(json.loads(output.getvalue()), "INVALID_EXPECTED_LITERAL_MAP")


if __name__ == "__main__":
    unittest.main()
