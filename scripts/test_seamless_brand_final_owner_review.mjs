#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const root = process.cwd();
const validator = path.join(root, "scripts/validate_seamless_brand_final_owner_review.py");
const argument = (name) => { const index = process.argv.indexOf(name); return index >= 0 ? process.argv[index + 1] : undefined; };
const packageValue = argument("--package"); const realPackage = packageValue ? path.resolve(packageValue) : null;
const reportValue = argument("--report-json"); const reportPath = reportValue ? path.resolve(reportValue) : null;
const python = argument("--python") || process.env.PYTHON_BIN || "python3";
const git = (...args) => execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
const sha = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const write = (file, value) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, typeof value === "string" || Buffer.isBuffer(value) ? value : `${JSON.stringify(value, null, 2)}\n`); };
const tinyPng = Buffer.from("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0000003010100c9fe92ef0000000049454e44ae426082", "hex");
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
const logo = "951d21e89cbcab58e0f9aed60778a8966d920e2fba464d1cade7bc37fb3ee919";

function createSynthetic() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "pr344-final-owner-review-synthetic-"));
  const screenshot = "screenshots/chromium/states/synthetic/viewport.png";
  write(path.join(dir, screenshot), tinyPng); write(path.join(dir, "contact-sheet.png"), tinyPng); write(path.join(dir, "owner-review.pdf"), "%PDF-1.4\nsynthetic\n%%EOF\n");
  write(path.join(dir, "owner-review.html"), `<html><body><img src="${screenshot}"></body></html>`);
  const summary = { expected_state_count: 1, captured_state_count: 1, stable_state_count: 1 };
  const common = { result: "PASS" };
  const files = {
    "executive-summary.json": { production_surface_sha256: production, canonical_logo_sha256: logo, rendered_ui_defects: 0, production_mutations: 0 },
    "visual-decision-checklist.json": { owner_review_status: "OWNER_REVIEW_REQUIRED" }, "route-inventory.json": {}, "state-manifest.json": {}, "cross-browser-selection-contract.json": {},
    "final-evidence-inputs.json": { production_surface_sha256: production, canonical_logo_sha256: logo, article_stability: { article_mobile: { webkit: { expected: 10, captured: 10, stable: 10 }, chromium: { expected: 5, captured: 5, stable: 5 }, firefox: { expected: 5, captured: 5, stable: 5 } } } }, "article-stability-results.json": { article_mobile: { webkit: { expected: 10, captured: 10, stable: 10 }, chromium: { expected: 5, captured: 5, stable: 5 }, firefox: { expected: 5, captured: 5, stable: 5 } } }, "chromium-summary.json": summary, "firefox-summary.json": summary, "webkit-summary.json": summary,
    "browser-results.json": common, "interaction-results.json": common, "zoom-results.json": common, "optical-readability-results.json": common, "logo-integrity-results.json": common, "brand-placement-results.json": common,
    "static-snapshot-brand-results.json": common, "route-surface-hashes.json": common, "approval-carry-forward.json": common, "accessibility-results.json": common, "safety-results.json": common,
    "package-statistics.json": { zero_byte_required_file_count: 0, sensitive_data_finding_count: 0, pdf_count: 1, contact_sheet_bytes: tinyPng.length },
    "provenance.json": { package_generation_head: git("rev-parse", "HEAD"), production_implementation_head: "dc2fababbe531f51b90fc9dcb6c584ece86838c2", browsers: { chromium: "synthetic", firefox: "synthetic", webkit: "synthetic" }, capture_tool_sha256: "x", generator_sha256: "x", validator_sha256: "x" },
  };
  for (const [name, value] of Object.entries(files)) write(path.join(dir, name), value);
  const entries = [];
  for (const file of fs.readdirSync(dir, { recursive: true }).map(item => path.join(dir, item)).filter(item => fs.statSync(item).isFile())) {
    const relative = path.relative(dir, file).split(path.sep).join("/"); if (["manifest.json", "manifest.sha256", "artifact.zip"].includes(relative)) continue;
    entries.push({ path: relative, bytes: fs.statSync(file).size, sha256: sha(file), required: true });
  }
  write(path.join(dir, "manifest.json"), { files: entries }); write(path.join(dir, "manifest.sha256"), `${sha(path.join(dir, "manifest.json"))}\n`);
  execFileSync("zip", ["-q", "-X", "artifact.zip", ...entries.map(entry => entry.path), "manifest.json", "manifest.sha256"], { cwd: dir });
  return dir;
}

function validate(dir, allowSynthetic = true) {
  const result = spawnSync(python, [validator, "--package", dir, ...(allowSynthetic ? ["--allow-synthetic"] : [])], { cwd: root, encoding: "utf8" });
  if (result.error) throw new Error(`Python validator could not start with ${python}: ${result.error.message}`);
  return result;
}
const interpreter = spawnSync(python, ["--version"], { encoding: "utf8" });
if (interpreter.error || interpreter.status !== 0) throw new Error(`Python interpreter is unavailable (${python}): ${interpreter.error?.message || interpreter.stderr || interpreter.stdout}`);
const executedCaseNames = []; const requiredCaseNames = [];
function pass(name, fn, required = true) { if (required) requiredCaseNames.push(name); assert(!executedCaseNames.includes(name), `duplicate test name: ${name}`); fn(); executedCaseNames.push(name); console.log(`PASS ${executedCaseNames.length}: ${name}`); }
function fails(name, mutate) { const dir = createSynthetic(); mutate(dir); const result = validate(dir); assert.notEqual(result.status, 0, `${name} should fail`); executedCaseNames.push(name); requiredCaseNames.push(name); console.log(`PASS ${executedCaseNames.length}: ${name}`); }

pass("valid synthetic package passes", () => assert.equal(validate(createSynthetic()).status, 0));
fails("missing HTML fails", dir => fs.rmSync(path.join(dir, "owner-review.html")));
fails("missing PDF fails", dir => fs.rmSync(path.join(dir, "owner-review.pdf")));
fails("missing contact sheet fails", dir => fs.rmSync(path.join(dir, "contact-sheet.png")));
fails("missing Chromium state fails", dir => { const p = path.join(dir, "chromium-summary.json"); const v = JSON.parse(fs.readFileSync(p)); v.captured_state_count = 0; write(p, v); });
fails("missing Firefox family fails", dir => { const p = path.join(dir, "firefox-summary.json"); const v = JSON.parse(fs.readFileSync(p)); v.captured_state_count = 0; write(p, v); });
fails("missing WebKit family fails", dir => { const p = path.join(dir, "webkit-summary.json"); const v = JSON.parse(fs.readFileSync(p)); v.captured_state_count = 0; write(p, v); });
for (const [name, file] of [["missing interaction evidence fails", "interaction-results.json"], ["missing zoom evidence fails", "zoom-results.json"], ["missing static evidence fails", "static-snapshot-brand-results.json"], ["missing route hashes fails", "route-surface-hashes.json"], ["missing optical data fails", "optical-readability-results.json"]]) fails(name, dir => fs.rmSync(path.join(dir, file)));
fails("bad screenshot hash fails", dir => fs.appendFileSync(path.join(dir, "screenshots/chromium/states/synthetic/viewport.png"), "x"));
fails("absolute private path fails", dir => fs.appendFileSync(path.join(dir, "owner-review.html"), "/tmp/private-path"));
fails("sensitive Account value fails", dir => fs.appendFileSync(path.join(dir, "owner-review.html"), "review@example.invalid"));
fails("raw media URL fails", dir => fs.appendFileSync(path.join(dir, "owner-review.html"), "https://example.invalid/audio.mp3"));
fails("protected Reader text fails", dir => fs.appendFileSync(path.join(dir, "owner-review.html"), "PROTECTED_READER_TEXT"));
fails("PENDING value fails", dir => { const p = path.join(dir, "executive-summary.json"); const v = JSON.parse(fs.readFileSync(p)); v.result = "PENDING"; write(p, v); });
fails("rendered defect count fails", dir => { const p = path.join(dir, "executive-summary.json"); const v = JSON.parse(fs.readFileSync(p)); v.rendered_ui_defects = 1; write(p, v); });
fails("production mutation count fails", dir => { const p = path.join(dir, "executive-summary.json"); const v = JSON.parse(fs.readFileSync(p)); v.production_mutations = 1; write(p, v); });
fails("bad manifest fails", dir => fs.writeFileSync(path.join(dir, "manifest.json"), "{}"));
fails("bad manifest SHA fails", dir => fs.writeFileSync(path.join(dir, "manifest.sha256"), "0".repeat(64)));
fails("missing ZIP fails", dir => fs.rmSync(path.join(dir, "artifact.zip")));
fails("ZIP traversal fails", dir => execFileSync(python, ["-c", "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1],'w'); z.writestr('../escape.txt','x'); z.close()", path.join(dir, "artifact.zip")]));
fails("bad extracted hash fails", dir => { const p = path.join(dir, "artifact.zip"); execFileSync(python, ["-c", "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1],'a'); z.writestr('screenshots/chromium/states/synthetic/viewport.png','bad'); z.close()", p]); });
fails("missing package statistics fails", dir => fs.rmSync(path.join(dir, "package-statistics.json")));
fails("zero-byte required file fails", dir => { const p = path.join(dir, "package-statistics.json"); const v = JSON.parse(fs.readFileSync(p)); v.zero_byte_required_file_count = 1; write(p, v); });
fails("wrong package head fails", dir => { const p = path.join(dir, "provenance.json"); const v = JSON.parse(fs.readFileSync(p)); v.package_generation_head = "0".repeat(40); write(p, v); });
fails("wrong production-surface SHA fails", dir => { const p = path.join(dir, "executive-summary.json"); const v = JSON.parse(fs.readFileSync(p)); v.production_surface_sha256 = "0".repeat(64); write(p, v); });
fails("incomplete Article stability evidence fails", dir => { const p = path.join(dir, "final-evidence-inputs.json"); const v = JSON.parse(fs.readFileSync(p)); v.article_stability.article_mobile.webkit.stable = 9; write(p, v); });
let realPackageValidationResult = "NOT_APPLICABLE";
if (realPackage) { pass("complete real local package passes", () => assert.equal(validate(realPackage, false).status, 0)); realPackageValidationResult = "PASS"; }
const report = { schema_version: 1, result: "PASS", test_case_count: executedCaseNames.length, executed_case_names: executedCaseNames, required_case_names: requiredCaseNames, missing_required_case_names: requiredCaseNames.filter(name => !executedCaseNames.includes(name)), duplicate_case_names: executedCaseNames.filter((name, index) => executedCaseNames.indexOf(name) !== index), real_package_path: realPackage, real_package_validation_executed: Boolean(realPackage), real_package_validation_result: realPackageValidationResult, validator_path: validator, python_executable: python, python_version: `${interpreter.stdout}${interpreter.stderr}`.trim(), generated_timestamp: new Date().toISOString() };
if (report.missing_required_case_names.length || report.duplicate_case_names.length || report.test_case_count !== report.executed_case_names.length) throw new Error("package test report contract failed");
if (reportPath) write(reportPath, report);
console.log(JSON.stringify({ result: "PASS", testCaseCount: report.test_case_count, realPackage, reportPath }));
