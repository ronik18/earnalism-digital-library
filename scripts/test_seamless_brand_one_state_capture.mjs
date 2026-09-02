#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadStateManifest, selectStateRecords } from "./lib/seamless_brand_state_manifest.mjs";
import { stateOutputDirectory, validateOneStateCaptureSummary } from "./lib/seamless_brand_one_state_capture.mjs";

const root = process.cwd();
const captureScript = path.join(root, "scripts/capture_seamless_brand_owner_review.mjs");
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const inventoryPath = path.join(root, "docs/design-system/seamless-brand-route-inventory.json");
const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-one-state-test-"));
const manifest = loadStateManifest(manifestPath);
const home = selectStateRecords(manifest, ["home-desktop"])[0];
let cases = 0;

function test(name, callback) {
  callback();
  cases += 1;
  process.stdout.write(`PASS ${cases}: ${name}\n`);
}

function run(args, expectedStatus = 0) {
  const result = spawnSync(process.execPath, [captureScript, ...args], { cwd: root, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 });
  assert.equal(result.status, expectedStatus, `${args.join(" ")} status=${result.status} stderr=${result.stderr}`);
  return result;
}

function writeSynthetic(output, stable = true, includeViewport = true) {
  const stateDirectory = stateOutputDirectory(output, home.id);
  fs.mkdirSync(stateDirectory, { recursive: true });
  const png = Buffer.from("89504e470d0a1a0a", "hex");
  if (includeViewport) fs.writeFileSync(path.join(stateDirectory, "viewport.png"), png);
  fs.writeFileSync(path.join(stateDirectory, "metadata.json"), JSON.stringify({ stable, screenshot_paths: includeViewport ? { viewport: "viewport.png" } : {}, screenshot_sha256: includeViewport ? { viewport: crypto.createHash("sha256").update(png).digest("hex") } : {} }));
  return { requested_state_ids: [home.id], captured_state_ids: [home.id], missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], stable_state_count: stable ? 1 : 0, unstable_state_count: stable ? 0 : 1 };
}

test("capture mode rejects missing --output", () => run(["--capture", "--base-url", "http://127.0.0.1:19999", "--browser", "chromium", "--state-filter", home.id], 1));
test("capture mode rejects missing --base-url", () => run(["--capture", "--output", path.join(temp, "missing-base"), "--browser", "chromium", "--state-filter", home.id], 1));
test("unsupported browser fails", () => run(["--capture", "--output", path.join(temp, "unsupported-browser"), "--base-url", "http://127.0.0.1:19999", "--browser", "gecko", "--state-filter", home.id], 1));
test("unknown state ID fails", () => run(["--capture", "--output", path.join(temp, "unknown-state"), "--base-url", "http://127.0.0.1:19999", "--browser", "chromium", "--state-filter", "missing-state"], 1));
test("Home state resolves from manifest", () => assert.deepEqual({ id: home.id, route: home.route, viewport: home.viewport, zoom: home.zoom }, { id: "home-desktop", route: "/", viewport: { width: 1440, height: 1000 }, zoom: 100 }));
test("output paths are deterministic", () => assert.equal(stateOutputDirectory(path.join(temp, "deterministic"), home.id), path.join(path.resolve(temp, "deterministic"), "states", "home-desktop")));
test("one-state capture summary expects exactly one state", () => validateOneStateCaptureSummary(writeSynthetic(path.join(temp, "summary")), path.join(temp, "summary")));
test("missing viewport screenshot fails summary validation", () => assert.throws(() => validateOneStateCaptureSummary(writeSynthetic(path.join(temp, "missing-viewport"), true, false), path.join(temp, "missing-viewport")), /viewport screenshot/));
test("unstable state is recorded as unstable", () => assert.throws(() => validateOneStateCaptureSummary(writeSynthetic(path.join(temp, "unstable"), false), path.join(temp, "unstable")), /unstable/));
test("valid Home capture produces stable metadata and valid PNG", () => {
  if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the actual local production-build capture.");
  const output = path.join(temp, "actual-home");
  run(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", home.id, "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output]);
  const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8"));
  const metadata = validateOneStateCaptureSummary(summary, output);
  const png = fs.readFileSync(path.join(stateOutputDirectory(output, home.id), "viewport.png"));
  assert.equal(png.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.equal(metadata.stable, true);
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, temp }));
