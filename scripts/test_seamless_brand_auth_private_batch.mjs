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
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-auth-private-test-"));
const manifest = loadStateManifest(manifestPath);
const newIds = ["login-desktop", "login-mobile", "signup-desktop", "signup-mobile", "account-desktop", "my-library-desktop", "my-library-mobile"];
const selected = selectStateRecords(manifest, [...newIds, "account-mobile"]);
let cases = 0;

function test(name, callback) { callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`); }
function run(args) { const result = spawnSync(process.execPath, [captureScript, ...args], { cwd: root, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 }); assert.equal(result.status, 0, `${args.join(" ")} status=${result.status} stderr=${result.stderr}`); }
function key(name) { return name.replace(".png", "").replaceAll("-", "_"); }
function writeSynthetic(output, stable = true) { for (const state of selected) { const directory = stateOutputDirectory(output, state.id); fs.mkdirSync(directory, { recursive: true }); const paths = {}; const hashes = {}; for (const name of requestedScreenshotNames(state.capture)) { const png = Buffer.from("89504e470d0a1a0a", "hex"); fs.writeFileSync(path.join(directory, name), png); paths[key(name)] = name; hashes[key(name)] = crypto.createHash("sha256").update(png).digest("hex"); } fs.writeFileSync(path.join(directory, "metadata.json"), JSON.stringify({ state_id: state.id, stable, screenshot_paths: paths, screenshot_sha256: hashes })); } return { requested_state_ids: selected.map((state) => state.id), captured_state_ids: selected.map((state) => state.id), missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], stable_state_count: stable ? 8 : 0, unstable_state_count: stable ? 0 : 8 }; }
function assertBrand(record, state) { assert.equal(record.route, state.route); assert.deepEqual(record.viewport, state.viewport); assert.equal(record.visible_header_count, 1); assert.equal(record.visible_canonical_lockup_count, 1); assert.equal(record.logo.natural_width, 2400); assert.equal(record.logo.natural_height, 720); assert.ok(Math.abs(record.logo.aspect_ratio - (10 / 3)) < 0.01); assert.equal(record.logo.transform, "none"); assert.equal(record.logo.wrapper_background, "rgba(0, 0, 0, 0)"); assert.equal(record.logo.wrapper_border_width, "0px"); assert.equal(record.logo.wrapper_border_radius, "0px"); assert.equal(record.logo.wrapper_box_shadow, "none"); assert.equal(record.logo.wrapper_padding, "0px"); assert.equal(record.logo.parent_background, "rgb(255, 249, 238)"); assert.equal(record.logo.clipped, false); assert.equal(record.overlap, false); assert.equal(record.horizontal_overflow, false); assert.equal(record.console_error_count, 0); assert.equal(record.page_error_count, 0); assert.equal(record.failed_required_request_count, 0); for (const name of requestedScreenshotNames(state.capture)) assert.ok(Object.values(record.screenshot_paths).includes(name), `${state.id} missing ${name}`); }
function assertPrivate(record, emptyLibrary = false) { assert.equal(record.private_fixture.fixture_visible, true); assert.equal(record.private_fixture.sensitive_fixture_values_present, false); assert.equal(record.private_fixture.production_authentication_used, false); assert.equal(record.private_fixture.production_account_api_called, false); assert.equal(record.private_fixture.mutation_count, 0); assert.match(record.private_fixture.fixture_sha256, /^[a-f0-9]{64}$/); if (emptyLibrary) assert.equal(record.private_fixture.my_library_empty_state_visible, true); }

test("seven new state IDs resolve", () => assert.deepEqual(manifest.states.filter((state) => state.introduced_in === "auth-private-2b2").map((state) => state.id), newIds));
test("existing Account-mobile state is reused", () => assert.equal(manifest.states.filter((state) => state.route === "/account" && state.viewport.width === 390 && state.viewport.height === 844 && state.zoom === 100 && state.fixture === "sanitized-account" && state.interaction === "sanitize-account-fixture").map((state) => state.id).join(","), "account-mobile"));
test("no duplicate Account-mobile state exists", () => assert.equal(manifest.states.filter((state) => state.id === "account-mobile").length, 1));
test("selected state count is eight", () => assert.equal(selected.length, 8));
test("reverse filter executes in manifest order", () => assert.deepEqual(selectStateRecords(manifest, [...newIds, "account-mobile"].reverse()).map((state) => state.id), selected.map((state) => state.id)));
let actual;
test("Login desktop metadata contract", () => { if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the actual local production-build capture."); const output = path.join(temp, "actual"); run(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", [...newIds, "account-mobile"].reverse().join(","), "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output]); const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8")); actual = validateCaptureSummary(summary, output, 8); assertBrand(actual.find((record) => record.state_id === "login-desktop"), manifest.states.find((state) => state.id === "login-desktop")); });
test("Login mobile metadata contract", () => assertBrand(actual.find((record) => record.state_id === "login-mobile"), manifest.states.find((state) => state.id === "login-mobile")));
test("Signup desktop metadata contract", () => assertBrand(actual.find((record) => record.state_id === "signup-desktop"), manifest.states.find((state) => state.id === "signup-desktop")));
test("Signup mobile metadata contract", () => assertBrand(actual.find((record) => record.state_id === "signup-mobile"), manifest.states.find((state) => state.id === "signup-mobile")));
test("Account desktop sanitized contract", () => { const record = actual.find((item) => item.state_id === "account-desktop"); assertBrand(record, manifest.states.find((state) => state.id === "account-desktop")); assertPrivate(record); });
test("Account mobile sanitized contract", () => { const record = actual.find((item) => item.state_id === "account-mobile"); assertBrand(record, manifest.states.find((state) => state.id === "account-mobile")); assertPrivate(record); });
test("My Library desktop empty-state contract", () => { const record = actual.find((item) => item.state_id === "my-library-desktop"); assertBrand(record, manifest.states.find((state) => state.id === "my-library-desktop")); assertPrivate(record, true); assert.equal(record.final_url, `${baseUrl}/my-library`); });
test("My Library mobile empty-state contract", () => { const record = actual.find((item) => item.state_id === "my-library-mobile"); assertBrand(record, manifest.states.find((state) => state.id === "my-library-mobile")); assertPrivate(record, true); assert.equal(record.final_url, `${baseUrl}/my-library`); });
test("production authentication remains unused", () => assert.ok(actual.filter((record) => record.private_fixture).every((record) => record.private_fixture.production_authentication_used === false)));
test("sensitive values remain absent", () => assert.ok(actual.filter((record) => record.private_fixture).every((record) => record.private_fixture.sensitive_fixture_values_present === false)));
test("no mutation occurs", () => assert.ok(actual.every((record) => !record.private_fixture || record.private_fixture.mutation_count === 0)));
test("missing state output fails", () => { const output = path.join(temp, "missing"); const summary = writeSynthetic(output); fs.rmSync(path.join(stateOutputDirectory(output, selected[7].id), "metadata.json")); assert.throws(() => validateCaptureSummary(summary, output, 8), /metadata is missing/); });
test("unstable state fails", () => assert.throws(() => validateCaptureSummary(writeSynthetic(path.join(temp, "unstable"), false), path.join(temp, "unstable"), 8), /unstable/));
test("valid eight-state summary passes", () => assert.equal(actual.length, 8));

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, temp }));
