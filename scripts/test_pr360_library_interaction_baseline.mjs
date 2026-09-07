#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR360_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR360_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const historicalSource = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeSource = (revision) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr360-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, historicalSource(revision, relativePath));
  }
  const record = path.join(temporary, PR360_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact PR360 historical baseline matches its reviewed Library surface", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR360_LIBRARY_INTERACTION_BASELINE);
  const historicalRoot = materializeSource(baseline.reviewed_source.commit);
  const comparison = compareLibraryInteractionBaseline(historicalRoot, PR360_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "a2925700553b5eef5adcc1f9cc52dbc1590d92fe70a022199864c3c3726c8003");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.reviewed_source.commit, "14b50734e2f752102d9b9646effaba709b71d1a2");
});

test("current source cannot be passed off as the historical PR360 baseline", () => {
  assert.equal(compareLibraryInteractionBaseline(root, PR360_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("unrecognized or malformed baseline paths fail closed", () => {
  assert.throws(() => loadLibraryInteractionBaseline(root, "docs/design-system/missing-pr360-library-baseline.json"));
  const temporary = materializeSource("14b50734e2f752102d9b9646effaba709b71d1a2");
  const record = path.join(temporary, PR360_LIBRARY_INTERACTION_BASELINE);
  const malformed = JSON.parse(read(record));
  malformed.owner_authorization.capture_is_not_expected_value_authority = false;
  fs.writeFileSync(record, `${JSON.stringify(malformed, null, 2)}\n`);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR360_LIBRARY_INTERACTION_BASELINE));
});

test("the PR344 and PR360 records remain byte-for-byte historical", () => {
  const pr344Path = "docs/design-system/library-filter-focus-hash-change.json";
  assert.equal(read(path.join(root, pr344Path)), historicalSource("14b50734e2f752102d9b9646effaba709b71d1a2", pr344Path));
  assert.equal(read(baselinePath), historicalSource("96257f2c010512477e97dfc7a66771b7443c8a44", PR360_LIBRARY_INTERACTION_BASELINE));
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
