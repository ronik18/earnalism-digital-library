#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { compareLibraryInteractionBaseline, loadLibraryInteractionBaseline, DEFAULT_LIBRARY_INTERACTION_BASELINE } from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const validator = path.join(root, "scripts/validate_seamless_brand_final_evidence_inputs.py");
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "issue380-final-inputs-"));
const currentRecord = DEFAULT_LIBRARY_INTERACTION_BASELINE;
const currentHash = "5ccaaef2ff0fb795e701933703bb79e50f79043738e2276e93566edac8a9b975";
const sha = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const head = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
const stateCount = JSON.parse(fs.readFileSync(path.join(root, "docs/design-system/seamless-brand-state-manifest.json"), "utf8")).states.length;
const shellCount = JSON.parse(fs.readFileSync(path.join(root, "docs/design-system/seamless-brand-cross-browser-shell-matrix.json"), "utf8")).families.length;
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
    state_manifest: { path: "synthetic", sha256: "synthetic", count: stateCount },
    cross_browser_contract: { path: "synthetic", sha256: "synthetic", count: shellCount },
    chromium: { summary_path: chromium.path, summary_sha256: chromium.sha256, expected: stateCount, captured: stateCount, stable: stateCount },
    firefox: { summary_path: firefox.path, summary_sha256: firefox.sha256, expected: shellCount, captured: shellCount, stable: shellCount, result: "PASS" },
    webkit: { summary_path: webkit.path, summary_sha256: webkit.sha256, expected: shellCount, captured: shellCount, stable: shellCount, result: "PASS" },
    article_stability: { article_mobile: { webkit: { expected: 10, captured: 10, stable: 10 }, chromium: { expected: 5, captured: 5, stable: 5 }, firefox: { expected: 5, captured: 5, stable: 5 } } },
    static_snapshot: { path: staticResult.path, sha256: staticResult.sha256, expected: 1, inspected: 1, passing: 1, result: "PASS" },
    route_hashes: { path: hashes.path, sha256: hashes.sha256, result: "PASS" },
    approval_carry_forward: { path: carry.path, sha256: carry.sha256, result: "PASS" },
    library_interaction_baseline: {
      surface: "library_interaction_surface",
      approval_source: currentRecord,
      approval_source_sha256: sha(path.join(root, currentRecord)),
      expected_surface_sha256: currentHash,
      observed_surface_sha256: currentHash,
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
test("active Hourglass/Sherlock baseline is the canonical reproduced current surface", () => {
  const baseline = compareLibraryInteractionBaseline(root);
  assert.equal(currentRecord, "docs/design-system/hourglass-sherlock-library-interaction-baseline-20261101.json");
  assert.equal(baseline.result, "PASS");
  assert.equal(baseline.expected_surface_sha256, currentHash);
  assert.equal(baseline.observed_surface_sha256, currentHash);
});
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
test("the now-stale issue380 Library baseline cannot satisfy the current run", () => invalid((input) => {
  input.library_interaction_baseline.approval_source = "docs/design-system/issue380-library-interaction-baseline.json";
  input.library_interaction_baseline.approval_source_sha256 = sha(path.join(root, input.library_interaction_baseline.approval_source));
  input.library_interaction_baseline.expected_surface_sha256 = "54e3670f223a9f464ace67244802d4bcc3c25d6231c0ae7a4518aea4056dec66";
  input.library_interaction_baseline.observed_surface_sha256 = "54e3670f223a9f464ace67244802d4bcc3c25d6231c0ae7a4518aea4056dec66";
}));
test("the historical Task B baseline cannot satisfy the current run", () => invalid((input) => {
  input.library_interaction_baseline.approval_source = "docs/design-system/task-b-production-link-action-integrity-library-interaction-baseline.json";
  input.library_interaction_baseline.approval_source_sha256 = sha(path.join(root, input.library_interaction_baseline.approval_source));
  input.library_interaction_baseline.expected_surface_sha256 = "d213e1e3ac86428cb6ebcc840cee04ebf9864e4e3b0c8b11fda6e6cad8c9bd86";
  input.library_interaction_baseline.observed_surface_sha256 = "d213e1e3ac86428cb6ebcc840cee04ebf9864e4e3b0c8b11fda6e6cad8c9bd86";
}));
test("an unauthorized Library baseline record fails", () => invalid((input) => { input.library_interaction_baseline.approval_source = "docs/design-system/pr360-library-interaction-baseline.json"; }));



// Exercise the actual generator, not just the downstream validator. All capture
// metadata here is synthetic; unrelated route hashes deliberately remain FAIL.
const generatorFixture = fs.mkdtempSync(path.join(os.tmpdir(), "library-generator-inputs-"));
const copy = (relative) => {
  const target = path.join(generatorFixture, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(path.join(root, relative), target);
};
const activeBaseline = loadLibraryInteractionBaseline(root);
for (const relative of [...activeBaseline.input_paths, "frontend/package.json", "frontend/package-lock.json", "frontend/vercel.json", "frontend/public/assets/brand/earnalism-brand-lockup.png"]) copy(relative);
fs.symlinkSync(path.join(root, "docs"), path.join(generatorFixture, "docs"));
const generatorChromium = path.join(generatorFixture, "chromium");
const generatorCross = path.join(generatorFixture, "cross");
const generatorOutput = path.join(generatorFixture, "output");
fs.mkdirSync(generatorChromium, { recursive: true });
fs.mkdirSync(generatorCross, { recursive: true });
const routeFamilies = ["home_library_commerce_body", "shared_public_header", "shared_footer", "auth_account", "editorial_campaign", "book_detail", "error_surfaces", "reader", "listener"];
write(path.join(generatorChromium, "capture-summary.json"), {
  route_surface_hashes: Object.fromEntries(routeFamilies.map((name) => [name, "a".repeat(64)])),
  expected_state_count: stateCount, captured_state_count: stateCount, stable_state_count: stateCount,
  rendered_ui_defect_states: [], production_mutation_count: 0,
});
const states = JSON.parse(fs.readFileSync(path.join(root, "docs/design-system/seamless-brand-state-manifest.json"), "utf8")).states;
for (const state of states) {
  const directory = path.join(generatorChromium, "states", state.id);
  fs.mkdirSync(directory, { recursive: true });
  write(path.join(directory, "metadata.json"), { fixture: "synthetic-generator-test-only", zoom: 100 });
}
const cross = Object.fromEntries(["firefox", "webkit"].map((browser) => [browser, {
  expected_state_count: shellCount, captured_state_count: shellCount, stable_state_count: shellCount, rendered_ui_result: "PASS",
}]));
write(path.join(generatorCross, "cross-browser-summary.json"), cross);
for (const browser of Object.keys(cross)) {
  fs.mkdirSync(path.join(generatorCross, browser));
  write(path.join(generatorCross, browser, "capture-summary.json"), cross[browser]);
}
const build = path.join(generatorFixture, "frontend/build");
fs.mkdirSync(build);
write(path.join(build, "static-seo-snapshot-manifest.json"), { routes: [{ route: "/" }] });
write(path.join(build, "index.html"), '<title>Synthetic generator test</title><link rel="canonical" href="https://theearnalism.com/"><meta name="robots" content="index,follow"><img src="https://theearnalism.com/assets/brand/earnalism-brand-lockup.png">');
const generate = () => {
  execFileSync(process.execPath, [path.join(root, "scripts/generate_seamless_brand_final_evidence_inputs.mjs"), "--output", generatorOutput, "--chromium", generatorChromium, "--cross-browser", generatorCross], {
    cwd: generatorFixture, stdio: "pipe",
    env: { ...process.env, GIT_DIR: execFileSync("git", ["rev-parse", "--absolute-git-dir"], { cwd: root, encoding: "utf8" }).trim(), GIT_WORK_TREE: generatorFixture },
  });
  return JSON.parse(fs.readFileSync(path.join(generatorOutput, "route-surface-hashes.json"), "utf8"));
};
test("actual generator hashes the reviewed six-file Library input set consistently", () => {
  const generated = generate();
  expectLibrary(generated, "PASS");
  assert.equal(generated.route_family_hashes.library_interaction_surface.current_hash, currentHash);
  assert.equal(generated.route_family_hashes.library_interaction_surface.approval_source, currentRecord);
  assert.equal(generated.route_family_hashes.reader.result, "FAIL", "synthetic captures must not imply real route acceptance");
});
function expectLibrary(generated, expected) {
  assert.equal(generated.route_family_hashes.library_interaction_surface.result, expected);
}
test("actual generator rejects an unreviewed mapping change despite synthetic capture values", () => {
  fs.appendFileSync(path.join(generatorFixture, "frontend/src/lib/controlledLaunch.js"), "\n// unreviewed test mutation\n");
  expectLibrary(generate(), "FAIL");
});
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
