"""Check saved-cell literal bindings only; never execute a notebook or grant scope.

--expected-json names an absolute private UTF-8 JSON file of control literals.
The report contains counts and hashes, never the supplied or saved literal values.
A PASS establishes only the selected saved source's bindings, not kernel state,
execution order, provider identity, compute authority or runtime qualification.
Reads are checked conservatively by source position, including nested scopes;
this is a saved-AST check, not a proof of Python's runtime execution order.
"""
import argparse
import ast
import hashlib
import json
import keyword
import math
from pathlib import Path


def _json_value(value):
    if type(value) in (str, int, bool, type(None)):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_json_value(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _json_value(item) for key, item in value.items())
    return False


def _same_typed_value(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _same_typed_value(a, e) for a, e in zip(actual, expected))
    if type(expected) is dict:
        return actual.keys() == expected.keys() and all(
            _same_typed_value(actual[key], expected[key]) for key in expected)
    return _json_value(actual) and actual == expected


class _Bindings(ast.NodeVisitor):
    """Count bindings even when they shadow a control in a nested scope."""

    def __init__(self, names):
        self.found = {name: [] for name in names}
        self.wildcard_import = False

    def add(self, name, node):
        if name in self.found:
            self.found[name].append(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.add(node.id, node)

    def visit_arg(self, node):
        self.add(node.arg, node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.add(node.name, node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef

    def visit_Import(self, node):
        for alias in node.names:
            self.add(alias.asname or alias.name.split(".", 1)[0], alias)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                self.wildcard_import = True
            else:
                self.add(alias.asname or alias.name, alias)

    def visit_ExceptHandler(self, node):
        self.add(node.name, node)
        self.generic_visit(node)

    def visit_MatchAs(self, node):
        self.add(node.name, node)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        self.add(node.rest, node)
        self.generic_visit(node)

    def visit_TypeVar(self, node):
        self.add(node.name, node)
        self.generic_visit(node)

    visit_ParamSpec = visit_TypeVar
    visit_TypeVarTuple = visit_TypeVar


def check_notebook(notebook, cell_id, expected):
    """Read and parse one saved code cell; return a value-free, scoped report."""
    report = {"state": "FAIL_SAVED_CELL_LITERAL_BINDINGS", "notebook_sha256": None,
              "cell_source_sha256": None, "matched_cells": 0, "matched_code_cells": 0,
              "expected_control_count": 0, "binding_counts": {}, "issues": [],
              "scope": "Selected saved cell AST literal bindings only",
              "execution_authorized": False, "runtime_qualified": False}

    def fail(code, name=None):
        report["issues"].append({"code": code, **({"control": name} if name else {})})
        return report

    if (type(expected) is not dict or not expected or not _json_value(expected)
            or any(not name.isidentifier() or keyword.iskeyword(name) for name in expected)):
        return fail("INVALID_EXPECTED_LITERAL_MAP")
    report["expected_control_count"] = len(expected)
    report["binding_counts"] = {name: 0 for name in expected}
    if type(cell_id) is not str or not cell_id:
        return fail("INVALID_CELL_ID")
    path = Path(notebook)
    if not path.is_absolute():
        return fail("ABSOLUTE_NOTEBOOK_PATH_REQUIRED")
    try:
        raw = path.read_bytes()
    except OSError:
        return fail("NOTEBOOK_READ_FAILED")
    report["notebook_sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError):
        return fail("INVALID_NOTEBOOK_JSON")
    if (not isinstance(document, dict) or not isinstance(document.get("cells"), list)
            or any(not isinstance(cell, dict) for cell in document["cells"])):
        return fail("INVALID_NOTEBOOK_CELLS")
    matches = [cell for cell in document["cells"]
               if isinstance(cell.get("metadata"), dict) and cell["metadata"].get("id") == cell_id]
    report["matched_cells"] = len(matches)
    report["matched_code_cells"] = sum(cell.get("cell_type") == "code" for cell in matches)
    if len(matches) != 1 or report["matched_code_cells"] != 1:
        return fail("EXACTLY_ONE_CODE_CELL_ID_REQUIRED")
    source = matches[0].get("source")
    if isinstance(source, list) and all(type(line) is str for line in source):
        source = "".join(source)
    if type(source) is not str:
        return fail("INVALID_CELL_SOURCE")
    report["cell_source_sha256"] = hashlib.sha256(source.encode()).hexdigest()
    try:
        tree = ast.parse(source, filename="<saved-cell>")
    except (SyntaxError, ValueError, RecursionError):
        return fail("INVALID_CELL_SYNTAX")
    bindings = _Bindings(expected)
    bindings.visit(tree)
    report["binding_counts"] = {name: len(nodes) for name, nodes in bindings.found.items()}
    if bindings.wildcard_import:
        fail("WILDCARD_IMPORT_BINDINGS_UNKNOWN")
    assignments = {node.targets[0].id: node for node in tree.body
                   if isinstance(node, ast.Assign) and len(node.targets) == 1
                   and isinstance(node.targets[0], ast.Name)}
    for name, expected_value in expected.items():
        found = bindings.found[name]
        if len(found) != 1:
            fail("EXACTLY_ONE_BINDING_REQUIRED", name)
            continue
        assignment = assignments.get(name)
        if assignment is None or assignment.targets[0] is not found[0]:
            fail("SIMPLE_TOP_LEVEL_ASSIGNMENT_REQUIRED", name)
            continue
        position = (assignment.lineno, assignment.col_offset)
        if any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
               and node.id == name and (node.lineno, node.col_offset) < position
               for node in ast.walk(tree)):
            fail("CONTROL_READ_PRECEDES_ASSIGNMENT", name)
        try:
            actual = ast.literal_eval(assignment.value)
        except (ValueError, TypeError, SyntaxError, RecursionError):
            fail("LITERAL_VALUE_REQUIRED", name)
            continue
        if not _same_typed_value(actual, expected_value):
            fail("TYPED_LITERAL_VALUE_MISMATCH", name)
    if not report["issues"]:
        report["state"] = "PASS_SAVED_CELL_LITERAL_BINDINGS_ONLY"
    return report


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", required=True)
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--expected-json", required=True, metavar="PRIVATE_JSON_FILE",
                        help="Absolute private UTF-8 JSON file; inline JSON is not accepted")
    args = parser.parse_args(argv)
    try:
        expected_path = Path(args.expected_json)
        if not expected_path.is_absolute():
            raise ValueError("Absolute private expected JSON file required")
        expected = json.loads(expected_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, ValueError, UnicodeError):
        expected = None
    report = check_notebook(args.notebook, args.cell_id, expected)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["state"] == "PASS_SAVED_CELL_LITERAL_BINDINGS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
