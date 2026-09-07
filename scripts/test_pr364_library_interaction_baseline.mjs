#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR364_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR364_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const materializeCurrentSurface = () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr364-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(path.join(root, relativePath), destination);
  }
  const record = path.join(temporary, PR364_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact PR364 baseline matches the repaired Library surface", () => {
  const baseline = loadLibraryInteractionBaseline(root);
  const comparison = compareLibraryInteractionBaseline(root);
  assert.equal(comparison.expected_surface_sha256, "d0c094fbf9db03139d68a6706dcc3af5a59aa53cc22b3b1a9ba352101a0e3770");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "a698315a69c6979ca6eedb2d2bab59461b19745ba883827deac02f79c187cd52");
  assert.equal(comparison.authorization_scope, "Explicit PR #362 to PR #364 Library-interaction baseline transition");
  assert.equal(baseline.reviewed_source.commit, "3b4f7047dcaebf60c3fb1a1490ac989abebc7fe6");
  assert.equal(baseline.reviewed_source.tree, "92c5df30e2dad2240cfa2f1dc07f406f9a4a7836");
  assert.equal(comparison.result, "PASS");
});

test("a changed three-file source fingerprint fails", () => {
  const temporary = materializeCurrentSurface();
  fs.appendFileSync(path.join(temporary, "frontend/src/components/ReferencePublicPages.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary).result, "FAIL");
});

test("malformed or unauthorized transition records fail", () => {
  const temporary = materializeCurrentSurface();
  const record = path.join(temporary, PR364_LIBRARY_INTERACTION_BASELINE);
  const malformed = JSON.parse(read(record));
  malformed.previous_baseline.record_path = "docs/design-system/library-filter-focus-hash-change.json";
  write(record, malformed);
  assert.throws(() => loadLibraryInteractionBaseline(temporary));
});

test("capture output cannot become expected-value authority", () => {
  const generator = read(path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"));
  assert.match(generator, /libraryBaseline\.expected_surface_sha256/);
  assert.doesNotMatch(generator, /library_interaction_surface:\s*captureRouteHashes\.library_interaction_surface/);
  assert.match(generator, /libraryBaseline\.authorization_scope/);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
