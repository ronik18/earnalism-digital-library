#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR397_LIBRARY_INTERACTION_BASELINE,
  PR399_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR399_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const sourceAt = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeReviewedSurface = () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr399-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, sourceAt(baseline.reviewed_source.commit, relativePath));
  }
  const record = path.join(temporary, PR399_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the explicit PR399 baseline matches the reviewed testimonial-removal source", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR399_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(), PR399_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "eb5b100dd080afb4213e86f9b91b711bbe442b8a82071161dc9f44cd89ea9738");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "99f0892ea0c1de2de7c11c90d7b0a36f09ed40ecdc0be2af7249d1de089c3f99");
  assert.equal(comparison.result, "PASS");
});

test("a changed protected Home or Library input is rejected", () => {
  const temporary = materializeReviewedSurface();
  fs.appendFileSync(path.join(temporary, "frontend/src/components/EditorialHomeLibrarySurfaces.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, PR399_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("wrong predecessor, source provenance, and authorization are rejected", () => {
  const temporary = materializeReviewedSurface();
  const record = path.join(temporary, PR399_LIBRARY_INTERACTION_BASELINE);
  for (const mutate of [
    (value) => { value.previous_baseline.record_path = PR397_LIBRARY_INTERACTION_BASELINE.replace("pr397", "pr377"); },
    (value) => { value.reviewed_source.tree = "0".repeat(40); },
    (value) => { value.owner_authorization.reference = "UNAUTHORIZED"; },
  ]) {
    const value = JSON.parse(read(record));
    mutate(value); write(record, value);
    assert.throws(() => loadLibraryInteractionBaseline(temporary, PR399_LIBRARY_INTERACTION_BASELINE));
    fs.copyFileSync(baselinePath, record);
  }
});

test("the historical PR397 baseline remains byte-for-byte unchanged", () => {
  assert.equal(read(path.join(root, PR397_LIBRARY_INTERACTION_BASELINE)), sourceAt("db5c8f70a5546766c90b196eb85cdb18be59ceca", PR397_LIBRARY_INTERACTION_BASELINE));
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
