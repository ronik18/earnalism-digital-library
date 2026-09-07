#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR362_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR362_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const materializeCurrentSurface = () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr362-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(path.join(root, relativePath), destination);
  }
  const record = path.join(temporary, PR362_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact PR362 baseline matches the reviewed Library surface", () => {
  const baseline = loadLibraryInteractionBaseline(root);
  const comparison = compareLibraryInteractionBaseline(root);
  assert.equal(comparison.expected_surface_sha256, "a698315a69c6979ca6eedb2d2bab59461b19745ba883827deac02f79c187cd52");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "a2925700553b5eef5adcc1f9cc52dbc1590d92fe70a022199864c3c3726c8003");
  assert.equal(baseline.reviewed_source.commit, "96257f2c010512477e97dfc7a66771b7443c8a44");
  assert.equal(baseline.reviewed_source.tree, "739062485bb53d07747ac84a48fb9826c4f4e862");
  assert.equal(comparison.result, "PASS");
});

test("a changed three-file source fingerprint fails", () => {
  const temporary = materializeCurrentSurface();
  fs.appendFileSync(path.join(temporary, "frontend/src/pages/Library.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary).result, "FAIL");
});

test("malformed or unauthorized transition records fail", () => {
  const temporary = materializeCurrentSurface();
  const record = path.join(temporary, PR362_LIBRARY_INTERACTION_BASELINE);
  const malformed = JSON.parse(read(record));
  malformed.previous_baseline.record_path = "docs/design-system/library-filter-focus-hash-change.json";
  write(record, malformed);
  assert.throws(() => loadLibraryInteractionBaseline(temporary));
});

test("capture output cannot become expected-value authority", () => {
  const generator = read(path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"));
  assert.match(generator, /libraryBaseline\.expected_surface_sha256/);
  assert.doesNotMatch(generator, /library_interaction_surface:\s*captureRouteHashes\.library_interaction_surface/);
  assert.match(generator, /libraryBaseline\.owner_authorization\.scope/);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
