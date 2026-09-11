#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR377_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  libraryInteractionSurfaceHash,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR377_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const historicalSource = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeSource = (revision) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr377-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, historicalSource(revision, relativePath));
  }
  const record = path.join(temporary, PR377_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact PR377 baseline matches the reviewed Library surface", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR377_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeSource(baseline.reviewed_source.commit), PR377_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "0499acf4a59729151980cb220e0d7d22292d5add88e53abc6805d3aacb84c95b");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "4120516e672e41d0a873bcbdc38f08f218c2b1017c8bc5e030b9b0e727b1326f");
  assert.equal(comparison.authorization_scope, "Explicit PR #376 to PR #377 Library-interaction baseline transition");
  assert.deepEqual(baseline.reviewed_source, {
    commit: "f3e18e0a40bd025ef874220b873168dc793b87ee",
    tree: "767e5eb9af03238fd494119d370cbfad5c38ff0a",
    base: "babc3d320f5ed6c00b73c90ade2bc4a98f166f08",
  });
  assert.equal(comparison.result, "PASS");
});

test("a changed protected source fingerprint fails", () => {
  const temporary = materializeSource("f3e18e0a40bd025ef874220b873168dc793b87ee");
  fs.appendFileSync(path.join(temporary, "frontend/src/pages/Library.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, PR377_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("malformed provenance and unauthorized records fail", () => {
  const temporary = materializeSource("f3e18e0a40bd025ef874220b873168dc793b87ee");
  const record = path.join(temporary, PR377_LIBRARY_INTERACTION_BASELINE);
  const malformed = JSON.parse(read(record));
  malformed.reviewed_source.base = "0".repeat(40);
  write(record, malformed);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR377_LIBRARY_INTERACTION_BASELINE));
});

test("the PR376 baseline record remains unchanged", () => {
  const previousPath = "docs/design-system/pr376-library-interaction-baseline.json";
  assert.equal(read(path.join(root, previousPath)), historicalSource("f3e18e0a40bd025ef874220b873168dc793b87ee", previousPath));
});

test("the superseded PR377 source retains its historical surface in Git history", () => {
  assert.equal(
    libraryInteractionSurfaceHash(materializeSource("09b2c23b3400200f37899151c6c1a3bf9a404899")),
    "951c58fb49647147585d6d23caeed9699c98be69be79c48732da637862d9f705",
  );
});

test("capture output cannot become expected-value authority", () => {
  const generator = read(path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"));
  assert.match(generator, /libraryBaseline\.expected_surface_sha256/);
  assert.doesNotMatch(generator, /library_interaction_surface:\s*captureRouteHashes\.library_interaction_surface/);
  assert.match(generator, /libraryBaseline\.authorization_scope/);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
