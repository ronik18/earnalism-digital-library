#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const root = process.cwd();
const validator = path.join(root, "scripts/validate_seamless_brand_final_evidence_inputs.py");
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "issue380-final-inputs-"));
const issue380Record = "docs/design-system/issue380-library-interaction-baseline.json";
const issue380Hash = "54e3670f223a9f464ace67244802d4bcc3c25d6231c0ae7a4518aea4056dec66";
const sha = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const head = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
const production = (() => {
  const files = [];
  const walk = (directory) => fs.readdirSync(directory, { withFileTypes: true }).forEach((entry) => {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(file);
    else if (!file.includes("__tests__") && !/\.(test|spec)\./.test(file)) files.push(file);
  });
  walk(path.join(root, "frontend/src"));
  walk(path.join(root, "frontend/public"));
  files.push(...["frontend/package.json", "frontend/package-lock.json", "frontend/vercel.json"].map((file) => path.join(root, file)));
  return crypto.createHash("sha256").update(files.sort().map((file) => `${sha(file)}  ${path.relative(root, file)}\n`).join("")).digest("hex");
})();
const write = (file, value) => fs.writeFileSync(file, typeof value === "string" ? value : JSON.stringify(value));
const run = () => execFileSync("python3", [validator, "--inputs", path.join(temp, "final-evidence-inputs.json")], { cwd: root, stdio: "pipe" });
const reference = (name, value = {}) => {
  const file = path.join(temp, `${name}.json`);
  write(file, { ok: true, ...value });
  return { path: file, sha256: sha(file) };
};
const make = () => {
  const chromium = reference("chromium");
  const firefox = reference("firefox");
  const webkit = reference("webkit");
  const staticResult = reference("static");
  const hashes = reference("hashes", { result: "PASS", route_family_hashes: { shared_header: { result: "PASS" } } });
  const carry = reference("carry");
  const libraryBaseline = reference("library-baseline", { surface: "library_interaction_surface" });
  const input = {
    current_pr_head: head,
    production_surface_sha256: production,
    canonical_logo_sha256: sha(path.join(root, "frontend/public/assets/brand/earnalism-brand-lockup.png")),
    chromium: { summary_path: chromium.path, summary_sha256: chromium.sha256, expected: 65, captured: 65, stable: 65 },
    firefox: { summary_path: firefox.path, summary_sha256: firefox.sha256, expected: 20, captured: 20, stable: 20, result: "PASS" },
    webkit: { summary_path: webkit.path, summary_sha256: webkit.sha256, expected: 20, captured: 20, stable: 20, result: "PASS" },
    article_stability: { article_mobile: { webkit: { expected: 10, captured: 10, stable: 10 }, chromium: { expected: 5, captured: 5, stable: 5 }, firefox: { expected: 5, captured: 5, stable: 5 } } },
    static_snapshot: { path: staticResult.path, sha256: staticResult.sha256, expected: 1, inspected: 1, passing: 1, result: "PASS" },
    route_hashes: { path: hashes.path, sha256: hashes.sha256, result: "PASS" },
    approval_carry_forward: { path: carry.path, sha256: carry.sha256, result: "PASS" },
    library_interaction_baseline: {
      surface: "library_interaction_surface",
      approval_source: issue380Record,
      approval_source_sha256: sha(path.join(root, issue380Record)),
      expected_surface_sha256: issue380Hash,
      observed_surface_sha256: issue380Hash,
      changed_from_previous: true,
      expected_change: true,
      result: "PASS",
      fixture_path: libraryBaseline.path,
    },
    reader_safety_result: "PASS",
    listener_safety_result: "PASS",
    interaction_result: "PASS",
    zoom_result: "PASS",
    error_status_result: "PASS",
    rendered_ui_defect_count: 0,
    production_mutation_count: 0,
  };
  write(path.join(temp, "final-evidence-inputs.json"), input);
  return input;
};

let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };
const invalid = (mutate) => {
  const input = make();
  mutate(input);
  write(path.join(temp, "final-evidence-inputs.json"), input);
  assert.throws(run);
};

test("valid exact-head input set passes", () => { make(); run(); });
test("wrong head fails", () => invalid((input) => { input.current_pr_head = "wrong"; }));
test("wrong production hash fails", () => invalid((input) => { input.production_surface_sha256 = "wrong"; }));
test("wrong logo hash fails", () => invalid((input) => { input.canonical_logo_sha256 = "wrong"; }));
test("missing Chromium state fails", () => invalid((input) => { input.chromium.captured = 64; }));
test("unstable Chromium state fails", () => invalid((input) => { input.chromium.stable = 64; }));
test("incomplete Article stability fails", () => invalid((input) => { input.article_stability.article_mobile.webkit.stable = 9; }));
test("Library focus failure fails", () => invalid((input) => { input.interaction_result = "FAIL"; }));
test("Reader safety failure fails", () => invalid((input) => { input.reader_safety_result = "FAIL"; }));
test("Listener safety failure fails", () => invalid((input) => { input.listener_safety_result = "FAIL"; }));
test("static snapshot failure fails", () => invalid((input) => { input.static_snapshot.result = "FAIL"; }));
test("unexpected route-family hash change fails", () => invalid((input) => { input.route_hashes.result = "FAIL"; }));
test("Firefox failure fails", () => invalid((input) => { input.firefox.result = "FAIL"; }));
test("WebKit failure fails", () => invalid((input) => { input.webkit.result = "FAIL"; }));
test("missing referenced file fails", () => invalid((input) => { input.webkit.summary_path = path.join(temp, "missing.json"); }));
test("SHA mismatch fails", () => invalid((input) => { input.firefox.summary_sha256 = "wrong"; }));
test("production mutation fails", () => invalid((input) => { input.production_mutation_count = 1; }));
test("PENDING value fails", () => invalid((input) => { input.interaction_result = "PENDING"; }));
test("a failing route-family hash entry fails", () => {
  const input = make();
  write(input.route_hashes.path, { result: "PASS", route_family_hashes: { shared_header: { result: "FAIL" } } });
  input.route_hashes.sha256 = sha(input.route_hashes.path);
  write(path.join(temp, "final-evidence-inputs.json"), input);
  assert.throws(run);
});
test("a mismatching Library baseline fails", () => invalid((input) => { input.library_interaction_baseline.observed_surface_sha256 = "wrong"; }));
test("the now-stale PR377 Library baseline cannot satisfy the current run", () => invalid((input) => {
  input.library_interaction_baseline.approval_source = "docs/design-system/pr377-library-interaction-baseline.json";
  input.library_interaction_baseline.approval_source_sha256 = sha(path.join(root, input.library_interaction_baseline.approval_source));
  input.library_interaction_baseline.expected_surface_sha256 = "0499acf4a59729151980cb220e0d7d22292d5add88e53abc6805d3aacb84c95b";
  input.library_interaction_baseline.observed_surface_sha256 = "0499acf4a59729151980cb220e0d7d22292d5add88e53abc6805d3aacb84c95b";
}));
test("an unauthorized Library baseline record fails", () => invalid((input) => { input.library_interaction_baseline.approval_source = "docs/design-system/pr360-library-interaction-baseline.json"; }));

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
