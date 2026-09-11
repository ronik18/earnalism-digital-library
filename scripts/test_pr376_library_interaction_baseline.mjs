#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR376_LIBRARY_INTERACTION_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR376_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const historicalSource = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeSource = (revision) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr376-library-surface-"));
  const baseline = JSON.parse(read(baselinePath));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, historicalSource(revision, relativePath));
  }
  const record = path.join(temporary, PR376_LIBRARY_INTERACTION_BASELINE);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(baselinePath, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the exact PR376 baseline matches the reviewed Library surface", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR376_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeSource(baseline.reviewed_source.commit), PR376_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "4120516e672e41d0a873bcbdc38f08f218c2b1017c8bc5e030b9b0e727b1326f");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "750e6eb58ebc1e6c55df6f6ba305dae460a2f39bbb4dda5661c08f59a6fd2a34");
  assert.equal(comparison.authorization_scope, "Explicit PR #372 to PR #376 Library-interaction baseline transition");
  assert.deepEqual(baseline.reviewed_source, {
    commit: "f286262009a845c8aaf3da8ba8da349c6718b4de",
    tree: "eb68ff05ae5b89fa660549410eb6993daee82e0d",
    base: "bd1e37680b833599b36345a21e6842df4144d499",
  });
  assert.equal(comparison.result, "PASS");
});

test("a changed protected source fingerprint fails", () => {
  const temporary = materializeSource("f286262009a845c8aaf3da8ba8da349c6718b4de");
  fs.appendFileSync(path.join(temporary, "frontend/src/pages/Library.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, PR376_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("malformed provenance or unauthorized transitions fail", () => {
  const temporary = materializeSource("f286262009a845c8aaf3da8ba8da349c6718b4de");
  const record = path.join(temporary, PR376_LIBRARY_INTERACTION_BASELINE);
  const malformed = JSON.parse(read(record));
  malformed.reviewed_source.base = "0".repeat(40);
  write(record, malformed);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR376_LIBRARY_INTERACTION_BASELINE));
});

test("the PR372 baseline record remains unchanged", () => {
  const previousPath = "docs/design-system/pr372-library-interaction-baseline.json";
  assert.equal(read(path.join(root, previousPath)), historicalSource("f286262009a845c8aaf3da8ba8da349c6718b4de", previousPath));
});

test("capture output cannot become expected-value authority", () => {
  const generator = read(path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"));
  assert.match(generator, /libraryBaseline\.expected_surface_sha256/);
  assert.doesNotMatch(generator, /library_interaction_surface:\s*captureRouteHashes\.library_interaction_surface/);
  assert.match(generator, /libraryBaseline\.authorization_scope/);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
