#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  DEFAULT_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, DEFAULT_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, typeof value === "string" ? value : `${JSON.stringify(value, null, 2)}\n`);
const baseline = JSON.parse(read(baselinePath));
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact authorized baseline matches the current Library surface", () => {
  const comparison = compareLibraryInteractionBaseline(root);
  assert.equal(comparison.expected_surface_sha256, "a2925700553b5eef5adcc1f9cc52dbc1590d92fe70a022199864c3c3726c8003");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(baseline.reviewed_source.commit, "14b50734e2f752102d9b9646effaba709b71d1a2");
  assert.equal(baseline.reviewed_source.tree, "bf1255698c3c702a2488615ed83ab94b831827ae");
  assert.equal(comparison.result, "PASS");
  assert.equal(comparison.changed_from_previous, true);
});

test("a missing or malformed baseline record fails", () => {
  assert.throws(() => loadLibraryInteractionBaseline(root, "docs/design-system/missing-pr360-library-baseline.json"));
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr360-library-baseline-"));
  const malformed = path.join(temporary, "baseline.json");
  write(malformed, "not-json");
  assert.throws(() => loadLibraryInteractionBaseline(root, malformed));
});

test("a baseline for the wrong surface fails", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr360-library-baseline-"));
  const wrongSurface = path.join(temporary, "baseline.json");
  write(wrongSurface, { ...baseline, surface: "shared_public_header" });
  assert.throws(() => loadLibraryInteractionBaseline(root, wrongSurface));
});

test("a changed Library source fingerprint fails", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr360-library-surface-"));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(path.join(root, relativePath), destination);
  }
  fs.appendFileSync(path.join(temporary, "frontend/src/components/ReferencePublicPages.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, baselinePath).result, "FAIL");
});

test("capture output cannot supply the expected Library fingerprint", () => {
  const generator = read(path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"));
  assert.match(generator, /libraryBaseline\.expected_surface_sha256/);
  assert.doesNotMatch(generator, /library_interaction_surface:\s*captureRouteHashes\.library_interaction_surface/);
  assert.match(generator, /Explicitly authorized PR344 to PR360 Library-interaction baseline transition/);
});

test("the PR344 historical record remains unchanged", () => {
  const historicalPath = "docs/design-system/library-filter-focus-hash-change.json";
  const reviewed = execFileSync("git", ["show", `14b50734e2f752102d9b9646effaba709b71d1a2:${historicalPath}`], { cwd: root, encoding: "utf8" });
  assert.equal(read(path.join(root, historicalPath)), reviewed);
});

test("generated provenance identifies the authorized PR344 to PR360 transition", () => {
  const comparison = compareLibraryInteractionBaseline(root);
  assert.equal(comparison.previous_surface_sha256, "696a0c8d760d349439280e63e19b8656d6fd1beff19696d6f1a369dc15cb144a");
  assert.equal(comparison.authorization, "OWNER_AUTHORIZATION_PR360_VERSIONED_LIBRARY_INTERACTION_BASELINE");
  assert.equal(comparison.approval_source, DEFAULT_LIBRARY_INTERACTION_BASELINE);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
