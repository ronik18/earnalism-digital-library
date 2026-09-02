#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadStateManifest, selectStateRecords } from "./lib/seamless_brand_state_manifest.mjs";
import { stateOutputDirectory, validateCaptureSummary, validateUniqueOutputDirectories } from "./lib/seamless_brand_one_state_capture.mjs";

const root = process.cwd();
const captureScript = path.join(root, "scripts/capture_seamless_brand_owner_review.mjs");
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const inventoryPath = path.join(root, "docs/design-system/seamless-brand-route-inventory.json");
const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-representative-test-"));
const manifest = loadStateManifest(manifestPath);
const ids = ["home-mobile-zoom-200", "reader-mobile-390", "listener-mobile-390", "account-mobile"];
const selected = selectStateRecords(manifest, ids);
let cases = 0;

function test(name, callback) { callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`); }
function run(args, expectedStatus = 0) { const result = spawnSync(process.execPath, [captureScript, ...args], { cwd: root, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 }); assert.equal(result.status, expectedStatus, `${args.join(" ")} status=${result.status} stderr=${result.stderr}`); return result; }
function writeSynthetic(output, stable = true) {
  for (const state of selected) {
    const directory = stateOutputDirectory(output, state.id); fs.mkdirSync(directory, { recursive: true }); const png = Buffer.from("89504e470d0a1a0a", "hex"); fs.writeFileSync(path.join(directory, "viewport.png"), png);
    fs.writeFileSync(path.join(directory, "metadata.json"), JSON.stringify({ state_id: state.id, stable, screenshot_paths: { viewport: "viewport.png" }, screenshot_sha256: { viewport: crypto.createHash("sha256").update(png).digest("hex") } }));
  }
  return { requested_state_ids: ids, captured_state_ids: ids, missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], stable_state_count: stable ? 4 : 0, unstable_state_count: stable ? 0 : 4 };
}

test("four IDs resolve uniquely from the checked-in manifest", () => assert.deepEqual(selected.map((state) => state.id), ids));
test("reverse-order filter input executes in manifest order", () => assert.deepEqual(selectStateRecords(manifest, [...ids].reverse()).map((state) => state.id), ids));
test("each state receives a separate context", () => assert.equal(new Set(selected.map((_, index) => `context-${index + 1}`)).size, 4));
test("each state receives a unique output directory", () => assert.equal(new Set(validateUniqueOutputDirectories(temp, selected)).size, 4));
test("missing state output fails", () => { const output = path.join(temp, "missing"); const summary = writeSynthetic(output); fs.rmSync(path.join(stateOutputDirectory(output, ids[3]), "metadata.json")); assert.throws(() => validateCaptureSummary(summary, output, 4), /metadata is missing/); });
test("duplicate output path fails", () => assert.throws(() => validateUniqueOutputDirectories(temp, [{ id: "duplicate" }, { id: "duplicate" }]), /duplicate output path/));
test("unstable state fails the run", () => assert.throws(() => validateCaptureSummary(writeSynthetic(path.join(temp, "unstable"), false), path.join(temp, "unstable"), 4), /unstable/));
let actualRecords;
test("one state storage does not appear in another state", () => {
  if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the actual local production-build capture.");
  const output = path.join(temp, "actual");
  run(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", [...ids].reverse().join(","), "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output]);
  const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8")); actualRecords = validateCaptureSummary(summary, output, 4);
  assert.deepEqual(actualRecords.map((record) => record.context_id), ["context-1", "context-2", "context-3", "context-4"]);
  assert.ok(actualRecords.every((record) => record.initial_storage.cookies === 0 && record.initial_storage.origins === 0));
});
test("Home zoom metadata reports 200%", () => assert.equal(actualRecords.find((record) => record.state_id === "home-mobile-zoom-200").zoom, 200));
test("Reader fixture reports no protected-content exposure", () => assert.equal(actualRecords.find((record) => record.state_id === "reader-mobile-390").reader.protected_content_exposed, false));
test("Reader fixture reports no balance consumption", () => assert.equal(actualRecords.find((record) => record.state_id === "reader-mobile-390").reader.balance_consumption, 0));
test("Listener fixture reports no media URL/playback/preload", () => { const listener = actualRecords.find((record) => record.state_id === "listener-mobile-390").listener; assert.deepEqual({ raw_media_url: listener.raw_media_url, playable_source: listener.playable_source, autoplay: listener.autoplay, preload: listener.preload }, { raw_media_url: "absent", playable_source: "absent", autoplay: false, preload: "absent" }); });
test("Account fixture reports no sensitive values", () => assert.equal(actualRecords.find((record) => record.state_id === "account-mobile").account.sensitive_fixture_values_present, false));
test("valid four-state capture creates a correct summary", () => assert.equal(actualRecords.length, 4));

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, temp }));
