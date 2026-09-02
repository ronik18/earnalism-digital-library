#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadStateManifest, selectStateRecords } from "./lib/seamless_brand_state_manifest.mjs";
import { requestedScreenshotNames, stateOutputDirectory, validateCaptureSummary, validateUniqueOutputDirectories } from "./lib/seamless_brand_one_state_capture.mjs";

const root = process.cwd();
const captureScript = path.join(root, "scripts/capture_seamless_brand_owner_review.mjs");
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const inventoryPath = path.join(root, "docs/design-system/seamless-brand-route-inventory.json");
const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-public-shell-test-"));
const manifest = loadStateManifest(manifestPath);
const ids = ["library-desktop", "library-mobile", "commerce-desktop", "commerce-mobile", "book-detail-desktop", "book-detail-mobile", "about-desktop", "about-mobile"];
const selected = selectStateRecords(manifest, ids);
let cases = 0;

function test(name, callback) { callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`); }
function run(args) { const result = spawnSync(process.execPath, [captureScript, ...args], { cwd: root, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 }); assert.equal(result.status, 0, `${args.join(" ")} status=${result.status} stderr=${result.stderr}`); }
function metadataKey(name) { return name.replace(".png", "").replaceAll("-", "_"); }
function writeSynthetic(output, stable = true) {
  for (const state of selected) {
    const directory = stateOutputDirectory(output, state.id); fs.mkdirSync(directory, { recursive: true });
    const paths = {}; const hashes = {};
    for (const name of requestedScreenshotNames(state.capture)) { const png = Buffer.from("89504e470d0a1a0a", "hex"); fs.writeFileSync(path.join(directory, name), png); paths[metadataKey(name)] = name; hashes[metadataKey(name)] = crypto.createHash("sha256").update(png).digest("hex"); }
    fs.writeFileSync(path.join(directory, "metadata.json"), JSON.stringify({ state_id: state.id, stable, screenshot_paths: paths, screenshot_sha256: hashes }));
  }
  return { requested_state_ids: ids, captured_state_ids: ids, missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], stable_state_count: stable ? 8 : 0, unstable_state_count: stable ? 0 : 8 };
}
function assertBrandContract(record, state) {
  assert.equal(record.route, state.route); assert.deepEqual(record.viewport, state.viewport); assert.equal(record.zoom, 100);
  assert.equal(record.visible_header_count, 1); assert.equal(record.visible_canonical_lockup_count, 1); assert.equal(record.logo.natural_width, 2400); assert.equal(record.logo.natural_height, 720);
  assert.ok(Math.abs(record.logo.aspect_ratio - (10 / 3)) < 0.01); assert.equal(record.logo.transform, "none"); assert.equal(record.logo.wrapper_background, "rgba(0, 0, 0, 0)"); assert.equal(record.logo.wrapper_border_width, "0px"); assert.equal(record.logo.wrapper_border_radius, "0px"); assert.equal(record.logo.wrapper_box_shadow, "none"); assert.equal(record.logo.wrapper_padding, "0px");
  assert.equal(record.logo.parent_background, "rgb(255, 249, 238)"); assert.equal(record.logo.clipped, false); assert.equal(record.overlap, false); assert.equal(record.horizontal_overflow, false); assert.equal(record.console_error_count, 0); assert.equal(record.page_error_count, 0); assert.equal(record.failed_required_request_count, 0); assert.equal(record.rendered_ui_result, "PASS");
  for (const name of requestedScreenshotNames(state.capture)) assert.ok(Object.values(record.screenshot_paths).includes(name), `${state.id} missing ${name}`);
}

test("exactly eight public-shell IDs resolve", () => assert.deepEqual(selected.map((state) => state.id), ids));
test("prior representative states remain present", () => assert.deepEqual(["home-desktop", "home-mobile-zoom-200", "reader-mobile-390", "listener-mobile-390", "account-mobile"].filter((id) => manifest.states.some((state) => state.id === id)).length, 5));
test("reverse input executes in manifest order", () => assert.deepEqual(selectStateRecords(manifest, [...ids].reverse()).map((state) => state.id), ids));
test("public-shell states have unique output directories", () => assert.equal(new Set(validateUniqueOutputDirectories(temp, selected)).size, 8));
test("missing state output fails", () => { const output = path.join(temp, "missing"); const summary = writeSynthetic(output); fs.rmSync(path.join(stateOutputDirectory(output, ids[7]), "metadata.json")); assert.throws(() => validateCaptureSummary(summary, output, 8), /metadata is missing/); });
test("unstable state fails", () => assert.throws(() => validateCaptureSummary(writeSynthetic(path.join(temp, "unstable"), false), path.join(temp, "unstable"), 8), /unstable/));
let actualRecords;
test("Library desktop metadata contract", () => { if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the actual local production-build capture."); const output = path.join(temp, "actual"); run(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", [...ids].reverse().join(","), "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output]); const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8")); actualRecords = validateCaptureSummary(summary, output, 8); assertBrandContract(actualRecords.find((record) => record.state_id === "library-desktop"), selected[0]); });
test("Library mobile metadata contract", () => assertBrandContract(actualRecords.find((record) => record.state_id === "library-mobile"), selected[1]));
test("Commerce desktop metadata contract", () => assertBrandContract(actualRecords.find((record) => record.state_id === "commerce-desktop"), selected[2]));
test("Commerce mobile metadata contract", () => assertBrandContract(actualRecords.find((record) => record.state_id === "commerce-mobile"), selected[3]));
test("Book Detail desktop metadata contract", () => assertBrandContract(actualRecords.find((record) => record.state_id === "book-detail-desktop"), selected[4]));
test("Book Detail mobile metadata contract", () => assertBrandContract(actualRecords.find((record) => record.state_id === "book-detail-mobile"), selected[5]));
test("About desktop metadata contract", () => assertBrandContract(actualRecords.find((record) => record.state_id === "about-desktop"), selected[6]));
test("About mobile metadata contract", () => assertBrandContract(actualRecords.find((record) => record.state_id === "about-mobile"), selected[7]));
test("complete eight-state summary passes", () => assert.equal(actualRecords.length, 8));

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, temp }));
