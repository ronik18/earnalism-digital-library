#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadStateManifest, selectStateRecords } from "./lib/seamless_brand_state_manifest.mjs";
import { requestedScreenshotNames, stateOutputDirectory, validateCaptureSummary } from "./lib/seamless_brand_one_state_capture.mjs";

const root = process.cwd();
const captureScript = path.join(root, "scripts/capture_seamless_brand_owner_review.mjs");
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const inventoryPath = path.join(root, "docs/design-system/seamless-brand-route-inventory.json");
const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
const output = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-core-zoom-test-"));
const manifest = loadStateManifest(manifestPath);
const addedIds = ["home-mobile-zoom-100", "home-mobile-zoom-150", "home-mobile-320-zoom-100", "home-mobile-320-zoom-150", "home-mobile-320-zoom-200", "account-mobile-zoom-150", "account-mobile-zoom-200", "my-library-mobile-zoom-150", "my-library-mobile-zoom-200"];
const baselineIds = ["home-mobile-zoom-200", "account-mobile", "my-library-mobile"];
const ids = ["home-mobile-zoom-200", "account-mobile", "my-library-mobile", ...addedIds];
const selected = selectStateRecords(manifest, ids);
let cases = 0;

function test(name, callback) { callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`); }
function run(args) { const result = spawnSync(process.execPath, [captureScript, ...args], { cwd: root, encoding: "utf8", maxBuffer: 30 * 1024 * 1024 }); assert.equal(result.status, 0, `${args.join(" ")} status=${result.status} stderr=${result.stderr}`); }
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function assertZoomRecord(record, state) {
  assert.equal(record.route, state.route); assert.deepEqual(record.viewport, state.viewport); assert.equal(record.zoom_results.requested_zoom_percent, state.zoom); assert.equal(record.zoom_results.effective_zoom_percent, state.zoom); assert.equal(record.zoom_results.zoom_method, "document.documentElement.style.zoom"); assert.equal(record.zoom_results.logo_control_overlap_area, 0); assert.equal(record.zoom_results.clipped_control_count, 0); assert.equal(record.horizontal_overflow, false); assert.equal(record.logo.clipped, false); assert.equal(record.rendered_ui_result, "PASS");
  assert.deepEqual(record.zoom_results.screenshot_dimensions["viewport.png"], state.viewport);
}
function assertPrivate(record) { assert.equal(record.private_fixture.fixture_visible, true); assert.equal(record.private_fixture.sensitive_fixture_values_present, false); assert.equal(record.private_fixture.production_authentication_used, false); assert.equal(record.private_fixture.production_account_api_called, false); assert.equal(record.private_fixture.mutation_count, 0); }
function validateForFailure(record) { assertZoomRecord(record, selected.find((state) => state.id === record.state_id)); if (record.private_fixture) assertPrivate(record); }
function writeSynthetic(target, stable = true) {
  const png = Buffer.from("89504e470d0a1a0a", "hex");
  for (const state of selected) { const directory = stateOutputDirectory(target, state.id); fs.mkdirSync(directory, { recursive: true }); const paths = {}; const hashes = {}; for (const name of requestedScreenshotNames(state.capture)) { fs.writeFileSync(path.join(directory, name), png); const key = name.replace(".png", "").replaceAll("-", "_"); paths[key] = name; hashes[key] = crypto.createHash("sha256").update(png).digest("hex"); } fs.writeFileSync(path.join(directory, "metadata.json"), JSON.stringify({ state_id: state.id, stable, screenshot_paths: paths, screenshot_sha256: hashes })); }
  return { requested_state_ids: ids, captured_state_ids: ids, missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], stable_state_count: stable ? 12 : 0, unstable_state_count: stable ? 0 : 12 };
}

test("nine new zoom states resolve", () => assert.deepEqual(manifest.states.filter((state) => state.introduced_in === "core-zoom-2c2a").map((state) => state.id), addedIds));
test("three existing baseline states are reused", () => baselineIds.forEach((id) => assert.ok(manifest.states.some((state) => state.id === id && state.introduced_in !== "core-zoom-2c2a"))));
test("no semantic duplicate zoom state exists", () => assert.equal(new Set(selected.map((state) => [state.route, state.viewport.width, state.viewport.height, state.zoom, state.fixture, state.interaction].join("|"))).size, 12));
test("selected state count is twelve", () => assert.equal(selected.length, 12));
test("each route and viewport family has 100/150/200 coverage", () => {
  const families = [["/", 390, 844], ["/", 320, 568], ["/account", 390, 844], ["/my-library", 390, 844]];
  for (const [route, width, height] of families) assert.deepEqual(selected.filter((state) => state.route === route && state.viewport.width === width && state.viewport.height === height).map((state) => state.zoom).sort((a, b) => a - b), [100, 150, 200]);
});
test("reverse-order state filter executes in manifest order", () => assert.deepEqual(selectStateRecords(manifest, [...ids].reverse()).map((state) => state.id), ids));
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the local fixture-enabled production-build zoom capture.");
run(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", [...ids].reverse().join(","), "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output]);
const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8"));
const records = validateCaptureSummary(summary, output, 12);
const record = (id) => records.find((item) => item.state_id === id);

test("requested zoom is recorded", () => records.forEach((item) => assert.equal(item.zoom_results.requested_zoom_percent, item.zoom)));
test("effective zoom is recorded", () => records.forEach((item) => assert.equal(item.zoom_results.effective_zoom_percent, item.zoom)));
test("post-capture PNG resizing cannot satisfy zoom evidence", () => records.forEach((item) => { assert.equal(item.zoom_results.zoom_method, "document.documentElement.style.zoom"); assert.deepEqual(item.zoom_results.screenshot_dimensions["viewport.png"], item.viewport); }));
test("Home 320x568 200% metadata contract", () => { const item = record("home-mobile-320-zoom-200"); assertZoomRecord(item, selected.find((state) => state.id === item.state_id)); assert.equal(item.zoom_results.masthead_row_count, 1); assert.ok(item.zoom_results.controls.menu); assert.ok(item.zoom_results.controls.search); assert.equal(item.zoom_results.content_begins_below_masthead, true); });
test("Account 200% sanitized contract", () => { const item = record("account-mobile-zoom-200"); assertZoomRecord(item, selected.find((state) => state.id === item.state_id)); assertPrivate(item); });
test("My Library 200% empty-state contract", () => { const item = record("my-library-mobile-zoom-200"); assertZoomRecord(item, selected.find((state) => state.id === item.state_id)); assertPrivate(item); assert.equal(item.private_fixture.my_library_empty_state_visible, true); });
test("logo/control overlap causes failure", () => { const item = clone(record("home-mobile-zoom-100")); item.zoom_results.logo_control_overlap_area = 1; assert.throws(() => validateForFailure(item)); });
test("clipped logo causes failure", () => { const item = clone(record("home-mobile-zoom-100")); item.logo.clipped = true; assert.throws(() => validateForFailure(item)); });
test("clipped primary control causes failure", () => { const item = clone(record("home-mobile-zoom-100")); item.zoom_results.clipped_control_count = 1; assert.throws(() => validateForFailure(item)); });
test("horizontal overflow causes failure", () => { const item = clone(record("home-mobile-zoom-100")); item.horizontal_overflow = true; assert.throws(() => validateForFailure(item)); });
test("sensitive Account data causes failure", () => { const item = clone(record("account-mobile-zoom-200")); item.private_fixture.sensitive_fixture_values_present = true; assert.throws(() => validateForFailure(item)); });
test("production authentication causes failure", () => { const item = clone(record("account-mobile-zoom-200")); item.private_fixture.production_authentication_used = true; assert.throws(() => validateForFailure(item)); });
test("production API use causes failure", () => { const item = clone(record("account-mobile-zoom-200")); item.private_fixture.production_account_api_called = true; assert.throws(() => validateForFailure(item)); });
test("production mutation causes failure", () => { const item = clone(record("account-mobile-zoom-200")); item.private_fixture.mutation_count = 1; assert.throws(() => validateForFailure(item)); });
test("missing state output causes failure", () => { const synthetic = path.join(output, "missing"); const syntheticSummary = writeSynthetic(synthetic); fs.rmSync(path.join(stateOutputDirectory(synthetic, ids[11]), "metadata.json")); assert.throws(() => validateCaptureSummary(syntheticSummary, synthetic, 12), /metadata is missing/); });
test("unstable state causes failure", () => { const synthetic = path.join(output, "unstable"); assert.throws(() => validateCaptureSummary(writeSynthetic(synthetic, false), synthetic, 12), /unstable/); });
test("valid twelve-state summary passes", () => { assert.equal(summary.expected_state_count, 12); assert.equal(summary.captured_state_count, 12); assert.equal(summary.stable_state_count, 12); assert.equal(summary.zoom_100_state_count, 4); assert.equal(summary.zoom_150_state_count, 4); assert.equal(summary.zoom_200_state_count, 4); assert.deepEqual(summary.rendered_ui_defect_states, []); assert.equal(summary.production_mutation_count, 0); records.forEach((item) => assertZoomRecord(item, selected.find((state) => state.id === item.state_id))); });

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, output }));
