#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR399_LIBRARY_INTERACTION_BASELINE,
  PR414_LIBRARY_INTERACTION_BASELINE,
  PR416_LIBRARY_INTERACTION_BASELINE,
  HOME_SECTIONS_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR414_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const sourceAt = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeReviewedSurface = (recordPath = PR414_LIBRARY_INTERACTION_BASELINE) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr414-library-surface-"));
  const sourceRecord = path.join(root, recordPath);
  const baseline = JSON.parse(read(sourceRecord));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, sourceAt(baseline.reviewed_source.commit, relativePath));
  }
  const record = path.join(temporary, recordPath);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(sourceRecord, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the explicit PR414 baseline matches the reviewed fail-closed Library source", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR414_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(), PR414_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "7bd2fc4b5dc9dcac43a1a9a4086c92075d9ea5443262e77b99385841f66853f4");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "eb5b100dd080afb4213e86f9b91b711bbe442b8a82071161dc9f44cd89ea9738");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.capture_is_not_expected_value_authority, true);
});

test("a changed held-release Library input is rejected", () => {
  const temporary = materializeReviewedSurface();
  fs.appendFileSync(path.join(temporary, "frontend/src/pages/Library.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, PR414_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("wrong predecessor, source provenance, and authorization are rejected", () => {
  const temporary = materializeReviewedSurface();
  const record = path.join(temporary, PR414_LIBRARY_INTERACTION_BASELINE);
  for (const mutate of [
    (value) => { value.previous_baseline.record_path = PR399_LIBRARY_INTERACTION_BASELINE.replace("pr399", "pr397"); },
    (value) => { value.reviewed_source.tree = "0".repeat(40); },
    (value) => { value.owner_authorization.reference = "UNAUTHORIZED"; },
  ]) {
    const value = JSON.parse(read(record));
    mutate(value); write(record, value);
    assert.throws(() => loadLibraryInteractionBaseline(temporary, PR414_LIBRARY_INTERACTION_BASELINE));
    fs.copyFileSync(baselinePath, record);
  }
});

test("the historical PR399 baseline remains byte-for-byte unchanged", () => {
  assert.equal(read(path.join(root, PR399_LIBRARY_INTERACTION_BASELINE)), sourceAt("b6bb598457c3a425c1b8dc77c78db431a95b36e0", PR399_LIBRARY_INTERACTION_BASELINE));
});

test("the owner-authorized PR416 Home shelf transition remains valid at its reviewed source", () => {
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(PR416_LIBRARY_INTERACTION_BASELINE), PR416_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "7bd2fc4b5dc9dcac43a1a9a4086c92075d9ea5443262e77b99385841f66853f4");
  assert.equal(comparison.expected_surface_sha256, "29dc1e90c0fbf4bffcd9edbdd1878c94c2647d039528878c70bb15669f90366f");
  assert.equal(comparison.result, "PASS");
});

test("the requested Home sections transition matches the current shared Library source", () => {
  const comparison = compareLibraryInteractionBaseline(root, HOME_SECTIONS_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "29dc1e90c0fbf4bffcd9edbdd1878c94c2647d039528878c70bb15669f90366f");
  assert.equal(comparison.expected_surface_sha256, "af86e390c9fdcc21c985e9106701117d0bc5fd79cbb2d327fd71bffe22e62d9e");
  assert.equal(comparison.result, "PASS");
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
