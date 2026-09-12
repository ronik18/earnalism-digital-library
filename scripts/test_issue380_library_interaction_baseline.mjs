#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  ISSUE380_LIBRARY_INTERACTION_BASELINE,
  PR377_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, ISSUE380_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const historicalSource = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeSource = (revision) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "issue380-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, historicalSource(revision, relativePath));
  }
  const record = path.join(temporary, ISSUE380_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact issue #380 baseline matches the reviewed Library surface", () => {
  const baseline = loadLibraryInteractionBaseline(root, ISSUE380_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeSource(baseline.reviewed_source.commit), ISSUE380_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "54e3670f223a9f464ace67244802d4bcc3c25d6231c0ae7a4518aea4056dec66");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "0499acf4a59729151980cb220e0d7d22292d5add88e53abc6805d3aacb84c95b");
  assert.equal(comparison.authorization_scope, "Explicit PR #377 baseline to issue #380 inclusion-source transition.");
  assert.equal(comparison.result, "PASS");
});

test("a changed protected source fingerprint fails", () => {
  const temporary = materializeSource("dfde080137d6f722f09b44c3729e67f169521569");
  fs.appendFileSync(path.join(temporary, "frontend/src/pages/Library.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, ISSUE380_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("wrong hash, provenance, predecessor, and authorization fail", () => {
  const temporary = materializeSource("dfde080137d6f722f09b44c3729e67f169521569");
  const record = path.join(temporary, ISSUE380_LIBRARY_INTERACTION_BASELINE);
  for (const mutate of [
    (value) => { value.authorized_surface_sha256 = "0".repeat(64); },
    (value) => { value.reviewed_source.base = "0".repeat(40); },
    (value) => { value.previous_baseline.record_path = PR377_LIBRARY_INTERACTION_BASELINE.replace("pr377", "pr376"); },
    (value) => { value.owner_authorization.reference = "UNAUTHORIZED"; },
  ]) {
    const value = JSON.parse(read(record));
    mutate(value); write(record, value);
    assert.throws(() => loadLibraryInteractionBaseline(temporary, ISSUE380_LIBRARY_INTERACTION_BASELINE));
    fs.copyFileSync(baselinePath, record);
  }
});

test("stale PR #377 authority cannot satisfy the current source", () => {
  const temporary = materializeSource("dfde080137d6f722f09b44c3729e67f169521569");
  const stale = path.join(temporary, PR377_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(stale), { recursive: true });
  fs.copyFileSync(path.join(root, PR377_LIBRARY_INTERACTION_BASELINE), stale);
  assert.equal(compareLibraryInteractionBaseline(temporary, PR377_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("the historical PR #377 record remains unchanged", () => {
  assert.equal(read(path.join(root, PR377_LIBRARY_INTERACTION_BASELINE)), historicalSource("dfde080137d6f722f09b44c3729e67f169521569", PR377_LIBRARY_INTERACTION_BASELINE));
});

test("capture output cannot become expected-value authority", () => {
  const generator = read(path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"));
  assert.match(generator, /libraryBaseline\.expected_surface_sha256/);
  assert.doesNotMatch(generator, /library_interaction_surface:\s*captureRouteHashes\.library_interaction_surface/);
  assert.match(generator, /libraryBaseline\.authorization_scope/);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
