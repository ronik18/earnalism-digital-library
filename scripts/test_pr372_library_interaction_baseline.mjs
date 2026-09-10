#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR372_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR372_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const historicalSource = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeSource = (revision) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr372-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, historicalSource(revision, relativePath));
  }
  const record = path.join(temporary, PR372_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact PR372 baseline matches the reviewed Library surface", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR372_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeSource(baseline.reviewed_source.commit), PR372_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "750e6eb58ebc1e6c55df6f6ba305dae460a2f39bbb4dda5661c08f59a6fd2a34");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "0fc10999d742f8c36ee8e0febdfb6715d3526843e90b96c5918fe9408eaf0d07");
  assert.equal(comparison.authorization_scope, "Explicit PR #371 to PR #372 Library-interaction baseline transition");
  assert.equal(baseline.reviewed_source.commit, "66ecdf65215521c2148307616c2c36c393008277");
  assert.equal(baseline.reviewed_source.tree, "35e7418b288e1bb1199e33626de3eb9c6ee361e5");
  assert.equal(comparison.result, "PASS");
});

test("a changed protected source fingerprint fails", () => {
  const temporary = materializeSource("66ecdf65215521c2148307616c2c36c393008277");
  fs.appendFileSync(path.join(temporary, "frontend/src/components/ReferencePublicPages.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, PR372_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("malformed or unauthorized transition records fail", () => {
  const temporary = materializeSource("66ecdf65215521c2148307616c2c36c393008277");
  const record = path.join(temporary, PR372_LIBRARY_INTERACTION_BASELINE);
  const malformed = JSON.parse(read(record));
  malformed.previous_baseline.record_path = "docs/design-system/pr364-library-interaction-baseline.json";
  write(record, malformed);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR372_LIBRARY_INTERACTION_BASELINE));
});

test("the PR371 baseline record remains unchanged", () => {
  const previousPath = "docs/design-system/pr371-library-interaction-baseline.json";
  assert.equal(read(path.join(root, previousPath)), historicalSource("66ecdf65215521c2148307616c2c36c393008277", previousPath));
});

test("capture output cannot become expected-value authority", () => {
  const generator = read(path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"));
  assert.match(generator, /libraryBaseline\.expected_surface_sha256/);
  assert.doesNotMatch(generator, /library_interaction_surface:\s*captureRouteHashes\.library_interaction_surface/);
  assert.match(generator, /libraryBaseline\.authorization_scope/);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
