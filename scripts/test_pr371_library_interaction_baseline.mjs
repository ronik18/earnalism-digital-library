#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR371_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR371_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const historicalSource = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeSource = (revision) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr371-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, historicalSource(revision, relativePath));
  }
  const record = path.join(temporary, PR371_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact PR371 baseline matches the reviewed Library surface", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR371_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeSource(baseline.reviewed_source.commit), PR371_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "0fc10999d742f8c36ee8e0febdfb6715d3526843e90b96c5918fe9408eaf0d07");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "d0c094fbf9db03139d68a6706dcc3af5a59aa53cc22b3b1a9ba352101a0e3770");
  assert.equal(comparison.authorization_scope, "Explicit PR #364 to PR #371 Library-interaction baseline transition");
  assert.equal(baseline.reviewed_source.commit, "3f89874046258bdd9e0cb531af7f15f1039d8ce1");
  assert.equal(baseline.reviewed_source.tree, "f230f7f5b97605923df2550e55c36d3b4e84d6c0");
  assert.equal(comparison.result, "PASS");
});

test("a changed three-file source fingerprint fails", () => {
  const temporary = materializeSource("3f89874046258bdd9e0cb531af7f15f1039d8ce1");
  fs.appendFileSync(path.join(temporary, "frontend/src/components/ReferencePublicPages.css"), "\n/* fixture-only source change */\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, PR371_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("malformed or unauthorized transition records fail", () => {
  const temporary = materializeSource("3f89874046258bdd9e0cb531af7f15f1039d8ce1");
  const record = path.join(temporary, PR371_LIBRARY_INTERACTION_BASELINE);
  const malformed = JSON.parse(read(record));
  malformed.previous_baseline.record_path = "docs/design-system/library-filter-focus-hash-change.json";
  write(record, malformed);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR371_LIBRARY_INTERACTION_BASELINE));
});

test("current source cannot be passed off as the historical PR371 baseline", () => {
  assert.equal(compareLibraryInteractionBaseline(root, PR371_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("the PR364 baseline record remains unchanged", () => {
  const previousPath = "docs/design-system/pr364-library-interaction-baseline.json";
  assert.equal(read(path.join(root, previousPath)), historicalSource("3f89874046258bdd9e0cb531af7f15f1039d8ce1", previousPath));
});

test("capture output cannot become expected-value authority", () => {
  const generator = read(path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"));
  assert.match(generator, /libraryBaseline\.expected_surface_sha256/);
  assert.doesNotMatch(generator, /library_interaction_surface:\s*captureRouteHashes\.library_interaction_surface/);
  assert.match(generator, /libraryBaseline\.authorization_scope/);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
