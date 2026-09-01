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
const output = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-experience-footer-zoom-test-"));
const manifest = loadStateManifest(manifestPath);
const addedIds = ["reader-mobile-390-zoom-150", "reader-mobile-390-zoom-200", "reader-mobile-320-zoom-100", "reader-mobile-320-zoom-150", "reader-mobile-320-zoom-200", "listener-mobile-390-zoom-150", "listener-mobile-390-zoom-200", "listener-mobile-320-zoom-100", "listener-mobile-320-zoom-150", "listener-mobile-320-zoom-200", "library-footer-mobile-zoom-100", "library-footer-mobile-zoom-150", "library-footer-mobile-zoom-200"];
const baselineIds = ["reader-mobile-390", "listener-mobile-390"];
const requestedIds = [...baselineIds, ...addedIds];
const selected = selectStateRecords(manifest, requestedIds);
let cases = 0;

function test(name, callback) { callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`); }
function run(args) { const result = spawnSync(process.execPath, [captureScript, ...args], { cwd: root, encoding: "utf8", maxBuffer: 30 * 1024 * 1024 }); assert.equal(result.status, 0, `${args.join(" ")} status=${result.status} stderr=${result.stderr}`); }
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function recordFor(records, id) { const record = records.find((item) => item.state_id === id); assert.ok(record, `Missing ${id}`); return record; }
function assertCommon(record, state) { assert.equal(record.route, state.route); assert.deepEqual(record.viewport, state.viewport); assert.equal(record.zoom_results.requested_zoom_percent, state.zoom); assert.equal(record.zoom_results.effective_zoom_percent, state.zoom); assert.equal(record.zoom_results.zoom_method, "document.documentElement.style.zoom"); assert.deepEqual(record.zoom_results.screenshot_dimensions["viewport.png"], state.viewport); assert.equal(record.logo.clipped, false); assert.equal(record.horizontal_overflow, false); assert.equal(record.zoom_results.logo_control_overlap_area, 0); assert.equal(record.zoom_results.clipped_control_count, 0); assert.equal(record.rendered_ui_result, "PASS"); assert.ok(fs.existsSync(path.join(output, "states", record.state_id, "safety-results.json"))); }
function assertReader(record) { assert.equal(record.fixture, "reader-visual-safe"); assert.equal(record.reader.protected_content_exposed, false); assert.equal(record.reader.protected_prefetch, false); assert.equal(record.reader.balance_consumption, 0); assert.equal(record.action_row_below_brand, true); }
function assertListener(record) { assert.equal(record.fixture, "listener-non-playable"); assert.equal(record.listener.raw_media_url, "absent"); assert.equal(record.listener.playable_source, "absent"); assert.equal(record.listener.autoplay, false); assert.equal(record.listener.preload, "absent"); assert.equal(record.listener.balance_consumption, 0); assert.equal(record.listener.cover_visible, true); assert.equal(record.action_row_below_brand, true); }
function assertFooter(record) { const footer = record.interaction_result; assert.equal(footer.kind, "scroll-to-footer"); assert.deepEqual(footer.failures, []); assert.equal(footer.footer_in_view, true); assert.equal(footer.navigation_reachable, true); assert.equal(footer.legal_links_reachable, true); assert.equal(footer.geometry.logo_navigation_overlap_area, 0); assert.equal(footer.geometry.clipped_control_count, 0); assert.equal(footer.geometry.horizontal_overflow, false); assert.equal(footer.geometry.wrapper.background, "rgba(0, 0, 0, 0)"); assert.equal(footer.geometry.wrapper.border_width, "0px"); assert.equal(footer.geometry.wrapper.border_radius, "0px"); assert.equal(footer.geometry.wrapper.box_shadow, "none"); assert.equal(footer.geometry.wrapper.padding, "0px"); assert.equal(footer.geometry.wrapper.transform, "none"); }
function assertRecord(record) { const state = selected.find((item) => item.id === record.state_id); assertCommon(record, state); if (state.fixture === "reader-visual-safe") assertReader(record); if (state.fixture === "listener-non-playable") assertListener(record); if (state.interaction === "scroll-to-footer") assertFooter(record); }
function writeSynthetic(target, stable = true) { const png = Buffer.from("89504e470d0a1a0a", "hex"); for (const state of selected) { const directory = stateOutputDirectory(target, state.id); fs.mkdirSync(directory, { recursive: true }); const screenshot_paths = {}; const screenshot_sha256 = {}; for (const name of requestedScreenshotNames(state.capture)) { fs.writeFileSync(path.join(directory, name), png); const key = name.replace(".png", "").replaceAll("-", "_"); screenshot_paths[key] = name; screenshot_sha256[key] = crypto.createHash("sha256").update(png).digest("hex"); } fs.writeFileSync(path.join(directory, "metadata.json"), JSON.stringify({ state_id: state.id, stable, screenshot_paths, screenshot_sha256 })); } return { requested_state_ids: selected.map((state) => state.id), captured_state_ids: selected.map((state) => state.id), missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], stable_state_count: stable ? 15 : 0, unstable_state_count: stable ? 0 : 15 }; }

test("thirteen new states resolve", () => assert.deepEqual(manifest.states.filter((state) => state.introduced_in === "experience-footer-zoom-2c2b").map((state) => state.id), addedIds));
test("existing Reader 390 100% state is reused", () => assert.equal(manifest.states.filter((state) => state.route === "/reader/dracula" && state.viewport.width === 390 && state.viewport.height === 844 && state.zoom === 100 && state.fixture === "reader-visual-safe").map((state) => state.id).join(","), "reader-mobile-390"));
test("existing Listener 390 100% state is reused", () => assert.equal(manifest.states.filter((state) => state.route === "/listener/a-ghost-story" && state.viewport.width === 390 && state.viewport.height === 844 && state.zoom === 100 && state.fixture === "listener-non-playable").map((state) => state.id).join(","), "listener-mobile-390"));
test("no semantic duplicate zoom state exists", () => assert.equal(new Set(selected.map((state) => [state.route, state.viewport.width, state.viewport.height, state.zoom, state.fixture, state.interaction].join("|"))).size, 15));
test("selected state count is fifteen", () => assert.equal(selected.length, 15));
test("each family has 100/150/200 coverage", () => { for (const [route, width, height, fixture, interaction] of [["/reader/dracula", 390, 844, "reader-visual-safe", "none"], ["/reader/dracula", 320, 568, "reader-visual-safe", "none"], ["/listener/a-ghost-story", 390, 844, "listener-non-playable", "none"], ["/listener/a-ghost-story", 320, 568, "listener-non-playable", "none"], ["/library", 390, 844, "public-safe", "scroll-to-footer"]]) assert.deepEqual(selected.filter((state) => state.route === route && state.viewport.width === width && state.viewport.height === height && state.fixture === fixture && state.interaction === interaction).map((state) => state.zoom).sort((a, b) => a - b), [100, 150, 200]); });
test("reverse filter executes in manifest order", () => assert.deepEqual(selectStateRecords(manifest, [...requestedIds].reverse()).map((state) => state.id), selected.map((state) => state.id)));
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the local fixture-enabled production-build zoom capture.");
run(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", [...requestedIds].reverse().join(","), "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output]);
const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8"));
const records = validateCaptureSummary(summary, output, 15);

test("requested and effective zoom are recorded", () => records.forEach((record) => { assert.equal(record.zoom_results.requested_zoom_percent, record.zoom); assert.equal(record.zoom_results.effective_zoom_percent, record.zoom); }));
test("post-capture image resizing cannot satisfy zoom evidence", () => records.forEach((record) => { assert.equal(record.zoom_results.zoom_method, "document.documentElement.style.zoom"); assert.deepEqual(record.zoom_results.screenshot_dimensions["viewport.png"], record.viewport); }));
test("Reader 320 at 200% metadata contract", () => assertRecord(recordFor(records, "reader-mobile-320-zoom-200")));
test("Reader protected exposure fails validation", () => { const record = clone(recordFor(records, "reader-mobile-320-zoom-200")); record.reader.protected_content_exposed = true; assert.throws(() => assertReader(record)); });
test("Reader prefetch fails validation", () => { const record = clone(recordFor(records, "reader-mobile-320-zoom-200")); record.reader.protected_prefetch = true; assert.throws(() => assertReader(record)); });
test("Reader balance consumption fails validation", () => { const record = clone(recordFor(records, "reader-mobile-320-zoom-200")); record.reader.balance_consumption = 1; assert.throws(() => assertReader(record)); });
test("Listener media URL fails validation", () => { const record = clone(recordFor(records, "listener-mobile-320-zoom-200")); record.listener.raw_media_url = "present"; assert.throws(() => assertListener(record)); });
test("Listener playable source fails validation", () => { const record = clone(recordFor(records, "listener-mobile-320-zoom-200")); record.listener.playable_source = "present"; assert.throws(() => assertListener(record)); });
test("Listener preload or autoplay fails validation", () => { const record = clone(recordFor(records, "listener-mobile-320-zoom-200")); record.listener.autoplay = true; assert.throws(() => assertListener(record)); });
test("Listener balance consumption fails validation", () => { const record = clone(recordFor(records, "listener-mobile-320-zoom-200")); record.listener.balance_consumption = 1; assert.throws(() => assertListener(record)); });
test("Footer 200% geometry contract", () => assertRecord(recordFor(records, "library-footer-mobile-zoom-200")));
test("Footer logo clipping fails validation", () => { const record = clone(recordFor(records, "library-footer-mobile-zoom-200")); record.logo.clipped = true; assert.throws(() => assertCommon(record, selected.find((state) => state.id === record.state_id))); });
test("Footer navigation overlap fails validation", () => { const record = clone(recordFor(records, "library-footer-mobile-zoom-200")); record.interaction_result.geometry.logo_navigation_overlap_area = 1; assert.throws(() => assertFooter(record)); });
test("horizontal overflow fails validation", () => { const record = clone(recordFor(records, "library-footer-mobile-zoom-200")); record.horizontal_overflow = true; assert.throws(() => assertCommon(record, selected.find((state) => state.id === record.state_id))); });
test("missing state output fails", () => { const synthetic = path.join(output, "missing"); const syntheticSummary = writeSynthetic(synthetic); fs.rmSync(path.join(stateOutputDirectory(synthetic, selected[14].id), "metadata.json")); assert.throws(() => validateCaptureSummary(syntheticSummary, synthetic, 15), /metadata is missing/); });
test("unstable state fails", () => { const synthetic = path.join(output, "unstable"); assert.throws(() => validateCaptureSummary(writeSynthetic(synthetic, false), synthetic, 15), /unstable/); });
test("complete fifteen-state summary passes", () => { assert.equal(summary.expected_state_count, 15); assert.equal(summary.captured_state_count, 15); assert.equal(summary.stable_state_count, 15); assert.equal(summary.zoom_100_state_count, 5); assert.equal(summary.zoom_150_state_count, 5); assert.equal(summary.zoom_200_state_count, 5); assert.equal(summary.reader_state_count, 6); assert.equal(summary.listener_state_count, 6); assert.equal(summary.footer_state_count, 3); assert.deepEqual(summary.rendered_ui_defect_states, []); assert.deepEqual(summary.reader_safety_defect_states, []); assert.deepEqual(summary.listener_safety_defect_states, []); assert.equal(summary.production_mutation_count, 0); records.forEach(assertRecord); });

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, output }));
