#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  ISSUE380_LIBRARY_INTERACTION_BASELINE,
  ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const historicalSource = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeSource = (revision) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "issue380-ui-completion-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, historicalSource(revision, relativePath));
  }
  const record = path.join(temporary, ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact issue380 UI-completion baseline matches its reviewed Library surface", () => {
  const baseline = loadLibraryInteractionBaseline(root, ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeSource(baseline.reviewed_source.commit), ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "eb5b100dd080afb4213e86f9b91b711bbe442b8a82071161dc9f44cd89ea9738");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "54e3670f223a9f464ace67244802d4bcc3c25d6231c0ae7a4518aea4056dec66");
  assert.equal(comparison.result, "PASS");
});

test("a changed current Library input fails", () => {
  const temporary = materializeSource("2fc56906697e016b570b3fd13d9673717408a60a");
  fs.appendFileSync(path.join(temporary, "frontend/src/pages/Library.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("wrong provenance, predecessor, input set, and authorization fail", () => {
  const temporary = materializeSource("2fc56906697e016b570b3fd13d9673717408a60a");
  const record = path.join(temporary, ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE);
  for (const mutate of [
    (value) => { value.reviewed_source.base = "0".repeat(40); },
    (value) => { value.previous_baseline.record_path = ISSUE380_LIBRARY_INTERACTION_BASELINE.replace("issue380", "pr377"); },
    (value) => { value.input_paths.pop(); },
    (value) => { value.owner_authorization.reference = "UNAUTHORIZED"; },
  ]) {
    const value = JSON.parse(read(record));
    mutate(value); write(record, value);
    assert.throws(() => loadLibraryInteractionBaseline(temporary, ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE));
    fs.copyFileSync(baselinePath, record);
  }
});

test("the historical issue380 baseline remains unchanged", () => {
  assert.equal(read(path.join(root, ISSUE380_LIBRARY_INTERACTION_BASELINE)), historicalSource("2fc56906697e016b570b3fd13d9673717408a60a", ISSUE380_LIBRARY_INTERACTION_BASELINE));
});

test("capture output cannot become expected-value authority", () => {
  const generator = read(path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"));
  assert.match(generator, /libraryBaseline\.expected_surface_sha256/);
  assert.doesNotMatch(generator, /library_interaction_surface:\s*captureRouteHashes\.library_interaction_surface/);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
