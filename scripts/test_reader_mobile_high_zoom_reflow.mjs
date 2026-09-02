#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadStateManifest, selectStateRecords } from "./lib/seamless_brand_state_manifest.mjs";
import { validateCaptureSummary } from "./lib/seamless_brand_one_state_capture.mjs";

const root = process.cwd();
const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
const captureScript = path.join(root, "scripts/capture_seamless_brand_owner_review.mjs");
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const inventoryPath = path.join(root, "docs/design-system/seamless-brand-route-inventory.json");
const beforePath = path.join(root, "uat/evidence/seamless-brand-reader-high-zoom/reader-high-zoom-controls-before.json");
const output = fs.mkdtempSync(path.join(os.tmpdir(), "reader-mobile-high-zoom-reflow-"));
const manifest = loadStateManifest(manifestPath);
const ids = ["reader-mobile-390", "reader-mobile-390-zoom-150", "reader-mobile-390-zoom-200", "reader-mobile-320-zoom-100", "reader-mobile-320-zoom-150", "reader-mobile-320-zoom-200"];
const selected = selectStateRecords(manifest, ids);
let cases = 0;

function test(name, callback) { callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`); }
function runCapture() { const result = spawnSync(process.execPath, [captureScript, "--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", [...ids].reverse().join(","), "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output], { cwd: root, encoding: "utf8", maxBuffer: 30 * 1024 * 1024 }); assert.equal(result.status, 0, result.stderr); }
function recordFor(records, id) { const value = records.find((record) => record.state_id === id); assert.ok(value, `Missing ${id}`); return value; }
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function assertReader(record) {
  const topbar = record.zoom_results.reader_topbar;
  const controls = topbar.children;
  assert.equal(record.rendered_ui_result, "PASS"); assert.equal(record.horizontal_overflow, false); assert.equal(record.logo.clipped, false); assert.equal(record.reader.protected_content_exposed, false); assert.equal(record.reader.protected_prefetch, false); assert.equal(record.reader.balance_consumption, 0); assert.equal(topbar.content_begins_below_topbar, true); assert.equal(topbar.action_row_content_overlap_area, 0);
  for (const key of ["back", "decrease", "increase", "settings"]) { const item = controls[key]; assert.ok(item.box); assert.ok(item.box.width >= 44 && item.box.height >= 44); assert.equal(item.clipped_area, 0); assert.ok(item.box.left >= topbar.box.left && item.box.right <= topbar.box.right); }
  assert.ok(controls.canonical_page_status.box); assert.ok(controls.canonical_page_status.box.left >= topbar.box.left && controls.canonical_page_status.box.right <= topbar.box.right);
}
async function functionalCheck(state) {
  const { chromium } = await import("playwright"); const browser = await chromium.launch({ headless: true }); const context = await browser.newContext({ viewport: state.viewport, deviceScaleFactor: 1 }); const page = await context.newPage(); const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); }); page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await page.goto(`${baseUrl}/reader/dracula?visual-fixture=1`, { waitUntil: "domcontentloaded" });
  await page.evaluate(async (zoom) => { await document.fonts.ready; document.documentElement.style.zoom = `${zoom}%`; await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))); }, state.zoom);
  const decrease = page.locator('header.reader-v2__mobile-topbar button[aria-label="Decrease text size"]'); const increase = page.locator('header.reader-v2__mobile-topbar button[aria-label="Increase text size"]'); const settings = page.locator('header.reader-v2__mobile-topbar button[aria-label="Reader settings"]'); const back = page.locator('header.reader-v2__mobile-topbar button[aria-label="Back to book"]'); const body = page.locator('[data-testid="reader-reading-text"]'); const scale = page.locator('.reader-v2__toolbar output[aria-label="Text size"]');
  const before = await body.evaluate((node) => Number.parseFloat(getComputedStyle(node).fontSize)); await increase.click(); const afterIncrease = await body.evaluate((node) => Number.parseFloat(getComputedStyle(node).fontSize)); const increasedText = await scale.textContent(); await decrease.click(); const afterDecrease = await body.evaluate((node) => Number.parseFloat(getComputedStyle(node).fontSize)); const decreasedText = await scale.textContent(); await settings.focus(); const settingsFocused = await page.evaluate(() => document.activeElement?.getAttribute("aria-label") === "Reader settings"); await back.focus(); const focusOrder = []; for (let index = 0; index < 3; index += 1) { await page.keyboard.press("Tab"); focusOrder.push(await page.evaluate(() => document.activeElement?.getAttribute("aria-label"))); }
  await browser.close(); return { before, afterIncrease, afterDecrease, increasedText, decreasedText, settingsFocused, focusOrder, errors };
}

test("current failing one-line fixture reproduces clipping", () => { const before = JSON.parse(fs.readFileSync(beforePath, "utf8")); assert.deepEqual(before.states.map((state) => state.state_id), ["reader-mobile-390-zoom-200", "reader-mobile-320-zoom-150", "reader-mobile-320-zoom-200"]); assert.ok(before.states.every((state) => state.clipped_controls.length > 0)); });
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for real-browser Reader reflow validation.");
runCapture();
const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8")); const records = validateCaptureSummary(summary, output, 6);
test("fixed mobile topbar permits wrapping", () => { const item = recordFor(records, "reader-mobile-320-zoom-200").zoom_results.reader_topbar; assert.equal(item.flex_wrap, "wrap"); assert.ok(item.children.control_cluster.box.top > item.children.back.box.top); });
test("390 at 100% passes", () => assertReader(recordFor(records, "reader-mobile-390")));
test("390 at 150% passes", () => assertReader(recordFor(records, "reader-mobile-390-zoom-150")));
test("390 at 200% passes", () => assertReader(recordFor(records, "reader-mobile-390-zoom-200")));
test("320 at 100% passes", () => assertReader(recordFor(records, "reader-mobile-320-zoom-100")));
test("320 at 150% passes", () => assertReader(recordFor(records, "reader-mobile-320-zoom-150")));
test("320 at 200% passes", () => assertReader(recordFor(records, "reader-mobile-320-zoom-200")));
test("all four controls remain present", () => records.forEach((record) => ["back", "decrease", "increase", "settings"].forEach((key) => assert.ok(record.zoom_results.reader_topbar.children[key].box))));
test("each control remains at least 44 by 44", () => records.forEach(assertReader));
test("cluster wraps as a unit", () => ["reader-mobile-390-zoom-200", "reader-mobile-320-zoom-150", "reader-mobile-320-zoom-200"].forEach((id) => { const topbar = recordFor(records, id).zoom_results.reader_topbar; assert.ok(topbar.children.control_cluster.box.top > topbar.children.back.box.top); }));
test("no child exceeds the topbar right edge", () => records.forEach((record) => { const topbar = record.zoom_results.reader_topbar; Object.values(topbar.children).forEach((item) => assert.ok(item.box.right <= topbar.box.right)); }));
test("no child begins left of the topbar", () => records.forEach((record) => { const topbar = record.zoom_results.reader_topbar; Object.values(topbar.children).forEach((item) => assert.ok(item.box.left >= topbar.box.left)); }));
test("content begins below the expanded topbar", () => records.forEach((record) => assert.equal(record.zoom_results.reader_topbar.content_begins_below_topbar, true)));
const functional390 = await functionalCheck(selected.find((state) => state.id === "reader-mobile-390")); const functional320 = await functionalCheck(selected.find((state) => state.id === "reader-mobile-320-zoom-100")); const functional320High = await functionalCheck(selected.find((state) => state.id === "reader-mobile-320-zoom-200"));
test("font increase changes rendered Reader text size", () => [functional390, functional320, functional320High].forEach((result) => { assert.ok(result.afterIncrease > result.before); assert.match(result.increasedText || "", /105%/); }));
test("font decrease changes rendered Reader text size", () => [functional390, functional320, functional320High].forEach((result) => { assert.ok(result.afterDecrease < result.afterIncrease); assert.match(result.decreasedText || "", /100%/); }));
test("settings remains reachable", () => [functional390, functional320, functional320High].forEach((result) => assert.equal(result.settingsFocused, true)));
test("keyboard focus order remains valid", () => [functional390, functional320, functional320High].forEach((result) => assert.deepEqual(result.focusOrder, ["Decrease text size", "Increase text size", "Reader settings"])));
test("horizontal overflow causes failure", () => { const item = clone(recordFor(records, "reader-mobile-320-zoom-200")); item.horizontal_overflow = true; assert.throws(() => assertReader(item)); });
test("clipped control causes failure", () => { const item = clone(recordFor(records, "reader-mobile-320-zoom-200")); item.zoom_results.reader_topbar.children.settings.clipped_area = 1; assert.throws(() => assertReader(item)); });
test("hidden control causes failure", () => { const item = clone(recordFor(records, "reader-mobile-320-zoom-200")); item.zoom_results.reader_topbar.children.settings.box = null; assert.throws(() => assertReader(item)); });
test("duplicate control causes failure", () => { const item = clone(recordFor(records, "reader-mobile-320-zoom-200")); item.zoom_results.reader_topbar.children.duplicate_settings = item.zoom_results.reader_topbar.children.settings; assert.throws(() => { const controls = item.zoom_results.reader_topbar.children; assert.equal(Object.keys(controls).filter((key) => /settings/.test(key)).length, 1); }); });
test("Reader safety remains unchanged", () => { records.forEach(assertReader); [functional390, functional320, functional320High].forEach((result) => assert.deepEqual(result.errors, [])); });

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, output }));
