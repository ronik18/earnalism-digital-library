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
const output = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-interaction-test-"));
const manifest = loadStateManifest(manifestPath);
const ids = ["home-menu-open-390", "home-menu-open-320", "library-menu-open-390", "commerce-menu-open-390", "library-filters-open-390", "library-filters-open-320"];
const selected = selectStateRecords(manifest, ids);
let cases = 0;

function test(name, callback) { callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`); }
function run(args) {
  const result = spawnSync(process.execPath, [captureScript, ...args], { cwd: root, encoding: "utf8", maxBuffer: 20 * 1024 * 1024 });
  assert.equal(result.status, 0, `${args.join(" ")} status=${result.status} stderr=${result.stderr}`);
}
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function assertMenu(record) {
  const interaction = record.interaction_result;
  assert.equal(interaction.kind, "mobile-menu");
  assert.equal(interaction.visible_toggle_count, 1);
  assert.equal(interaction.owner_header_count, 1);
  assert.equal(interaction.active_dialog_count, 1);
  assert.ok(interaction.geometry.dialog_client_height > 0);
  assert.equal(interaction.escape_close, true);
  assert.equal(interaction.focus_restoration, true);
  assert.equal(interaction.body_scroll_restored, true);
  assert.equal(interaction.background_inert_restored, true);
  assert.equal(interaction.route_action_result, "PASS");
  assert.deepEqual(interaction.failures, []);
}
function assertFilters(record) {
  const interaction = record.interaction_result;
  assert.equal(interaction.kind, "library-filters");
  assert.equal(interaction.trigger_count, 1);
  assert.equal(interaction.panel_count, 1);
  assert.ok(interaction.geometry.panel_client_height > 0);
  assert.equal(interaction.apply_filters_reachable, true);
  assert.equal(interaction.focus_trap, true);
  assert.equal(interaction.close_result, true);
  assert.equal(interaction.focus_restoration, true);
  assert.equal(interaction.url_mutation_count, 0);
  assert.deepEqual(interaction.failures, []);
}
function writeSynthetic(target, stable = true) {
  const png = Buffer.from("89504e470d0a1a0a", "hex");
  for (const state of selected) {
    const directory = stateOutputDirectory(target, state.id); fs.mkdirSync(directory, { recursive: true });
    const paths = {}; const hashes = {};
    for (const name of requestedScreenshotNames(state.capture)) { fs.writeFileSync(path.join(directory, name), png); const key = name.replace(".png", "").replaceAll("-", "_"); paths[key] = name; hashes[key] = crypto.createHash("sha256").update(png).digest("hex"); }
    fs.writeFileSync(path.join(directory, "metadata.json"), JSON.stringify({ state_id: state.id, stable, screenshot_paths: paths, screenshot_sha256: hashes }));
  }
  return { requested_state_ids: ids, captured_state_ids: ids, missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], stable_state_count: stable ? 6 : 0, unstable_state_count: stable ? 0 : 6 };
}

test("exactly six selected interaction states resolve", () => assert.deepEqual(selected.map((state) => state.id), ids));
test("interaction states remain in the expanded manifest", () => assert.ok(manifest.states.length >= 43));
test("reverse filter executes in manifest order", () => assert.deepEqual(selectStateRecords(manifest, [...ids].reverse()).map((state) => state.id), ids));
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the local production-build interaction capture.");
run(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", [...ids].reverse().join(","), "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output]);
const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8"));
const records = validateCaptureSummary(summary, output, 6);
const menus = records.filter((record) => record.interaction_result?.kind === "mobile-menu");
const filters = records.filter((record) => record.interaction_result?.kind === "library-filters");

test("hidden menu fixture dialogs are ignored", () => { const record = clone(menus[0]); record.interaction_result.hidden_fixture_dialog_count = 2; assertMenu(record); });
test("zero visible menu dialog fails", () => { const record = clone(menus[0]); record.interaction_result.active_dialog_count = 0; assert.throws(() => assertMenu(record)); });
test("multiple visible owner dialogs fail", () => { const record = clone(menus[0]); record.interaction_result.active_dialog_count = 2; assert.throws(() => assertMenu(record)); });
test("zero-height menu fails", () => { const record = clone(menus[0]); record.interaction_result.geometry.dialog_client_height = 0; assert.throws(() => assertMenu(record)); });
test("menu Escape closes", () => menus.forEach((record) => assert.equal(record.interaction_result.escape_close, true)));
test("menu focus restores", () => menus.forEach((record) => assert.equal(record.interaction_result.focus_restoration, true)));
test("menu body scroll restores", () => menus.forEach((record) => assert.equal(record.interaction_result.body_scroll_restored, true)));
test("menu background inertness restores", () => menus.forEach((record) => assert.equal(record.interaction_result.background_inert_restored, true)));
test("menu route action closes and navigates", () => menus.forEach((record) => assert.equal(record.interaction_result.route_action_result, "PASS")));
test("Library filter trigger resolves uniquely", () => filters.forEach((record) => assert.equal(record.interaction_result.trigger_count, 1)));
test("zero-height filter surface fails", () => { const record = clone(filters[0]); record.interaction_result.geometry.panel_client_height = 0; assert.throws(() => assertFilters(record)); });
test("filter Apply action remains reachable", () => filters.forEach((record) => assert.equal(record.interaction_result.apply_filters_reachable, true)));
test("filter focus remains contained", () => filters.forEach((record) => assert.equal(record.interaction_result.focus_trap, true)));
test("filter closes", () => filters.forEach((record) => assert.equal(record.interaction_result.close_result, true)));
test("filter focus restores", () => filters.forEach((record) => assert.equal(record.interaction_result.focus_restoration, true)));
test("filter URL mutation count remains zero", () => filters.forEach((record) => assert.equal(record.interaction_result.url_mutation_count, 0)));
test("missing state output fails", () => { const synthetic = path.join(output, "missing"); const syntheticSummary = writeSynthetic(synthetic); fs.rmSync(path.join(stateOutputDirectory(synthetic, ids[5]), "metadata.json")); assert.throws(() => validateCaptureSummary(syntheticSummary, synthetic, 6), /metadata is missing/); });
test("unstable state fails", () => { const synthetic = path.join(output, "unstable"); assert.throws(() => validateCaptureSummary(writeSynthetic(synthetic, false), synthetic, 6), /unstable/); });
test("complete six-state summary passes", () => { assert.equal(summary.menu_state_count, 4); assert.equal(summary.filter_state_count, 2); assert.equal(summary.interaction_pass_count, 6); assert.deepEqual(summary.interaction_failure_states, []); records.forEach((record) => { assert.equal(record.rendered_ui_result, "PASS"); if (record.interaction_result.kind === "mobile-menu") assertMenu(record); else assertFilters(record); }); });

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, output }));
