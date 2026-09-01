#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadStateManifest } from "./lib/seamless_brand_state_manifest.mjs";
import { stateOutputDirectory, validateCaptureSummary } from "./lib/seamless_brand_one_state_capture.mjs";

const root = process.cwd();
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const manifest = loadStateManifest(manifestPath);
const expectedIds = manifest.states.map((state) => state.id);
const png = Buffer.from("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000049454e44ae426082", "hex");
const logoHash = "951d21e89cbcab58e0f9aed60778a8966d920e2fba464d1cade7bc37fb3ee919";

function git(...args) { return execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim(); }
function sha(value) { return crypto.createHash("sha256").update(value).digest("hex"); }
function assertEmpty(value, label) { assert.deepEqual(value || [], [], `${label} must be empty`); }
function assertPng(file) { const bytes = fs.readFileSync(file); assert.ok(bytes.length > 24, `${file} is empty`); assert.ok(bytes.subarray(0, 8).equals(png.subarray(0, 8)), `${file} has an invalid PNG signature`); }

export function validateFullChromiumMatrix(output, expectedProductionSurface) {
  const summaryPath = path.join(output, "capture-summary.json");
  assert.ok(fs.existsSync(summaryPath), "capture summary is missing");
  const summary = JSON.parse(fs.readFileSync(summaryPath, "utf8"));
  assert.equal(expectedIds.length, 65, "manifest must contain 65 states");
  assert.equal(summary.expected_state_count, 65, "expected state count must be 65");
  assert.equal(summary.captured_state_count, 65, "captured state count must be 65");
  assert.equal(summary.stable_state_count, 65, "stable state count must be 65");
  assert.equal(summary.unstable_state_count, 0, "unstable state count must be zero");
  assert.deepEqual(summary.requested_state_ids, expectedIds, "expected IDs must be derived from the manifest");
  assert.deepEqual(summary.captured_state_ids, expectedIds, "captured IDs must preserve manifest order");
  assertEmpty(summary.missing_state_ids, "missing state IDs"); assertEmpty(summary.unexpected_state_ids, "unexpected state IDs"); assertEmpty(summary.duplicate_state_ids, "duplicate state IDs");
  assert.equal(summary.source_head, git("rev-parse", "HEAD"), "capture source head must match local HEAD");
  assert.equal(summary.tree_sha, git("rev-parse", "HEAD^{tree}"), "capture tree SHA must match local tree");
  assert.equal(summary.production_surface_sha256, expectedProductionSurface, "production surface hash differs from pre-run value");
  assert.equal(summary.canonical_logo_sha256, logoHash, "canonical logo hash differs");
  for (const key of ["raw_duplicate_logo_states", "transform_logo_states", "logo_card_states", "clipped_logo_states", "clipped_control_states", "logo_control_overlap_states", "multiple_header_states", "horizontal_overflow_states", "interaction_failure_states", "reader_safety_defect_states", "listener_safety_defect_states", "status_contract_defect_states", "static_parity_defect_states", "runtime_failure_states", "rendered_ui_defect_states"]) assertEmpty(summary[key], key);
  assert.equal(summary.production_mutation_count, 0, "production mutation count must be zero");
  assert.equal(summary.menu_state_count, 4, "all four mobile menu states must execute");
  assert.equal(summary.filter_state_count, 2, "both filter states must execute");
  assert.ok(summary.zoom_150_state_count > 0 && summary.zoom_200_state_count > 0, "zoom states are absent");
  const records = validateCaptureSummary(summary, output, 65);
  for (const record of records) {
    assert.equal(record.source_head, summary.source_head, `${record.state_id}: source head mismatch`);
    assert.equal(record.tree_sha, summary.tree_sha, `${record.state_id}: tree SHA mismatch`);
    assert.equal(record.rendered_ui_result, "PASS", `${record.state_id}: rendered UI failure`);
    assert.equal(record.visible_header_count, 1, `${record.state_id}: multiple header state`);
    assert.equal(record.visible_canonical_lockup_count, 1, `${record.state_id}: duplicate logo state`);
    assert.equal(record.logo?.transform, "none", `${record.state_id}: transform logo use`);
    assert.equal(record.logo?.wrapper_background, "rgba(0, 0, 0, 0)", `${record.state_id}: logo wrapper background`);
    assert.equal(record.logo?.wrapper_border_width, "0px", `${record.state_id}: logo card border`);
    assert.equal(record.logo?.wrapper_border_radius, "0px", `${record.state_id}: logo card radius`);
    assert.equal(record.logo?.wrapper_box_shadow, "none", `${record.state_id}: logo card shadow`);
    assert.equal(record.logo?.wrapper_padding, "0px", `${record.state_id}: logo card padding`);
    assert.equal(record.logo?.clipped, false, `${record.state_id}: clipped logo`);
    assert.equal(record.overlap, false, `${record.state_id}: logo/control overlap`);
    assert.equal(record.horizontal_overflow, false, `${record.state_id}: horizontal overflow`);
    assert.equal(record.console_error_count, 0, `${record.state_id}: console error`);
    assert.equal(record.page_error_count, 0, `${record.state_id}: page error`);
    assert.equal(record.failed_required_request_count, 0, `${record.state_id}: failed request`);
    assert.equal(record.zoom_results?.clipped_control_count, 0, `${record.state_id}: clipped control`);
    assert.equal(record.zoom_results?.logo_control_overlap_area, 0, `${record.state_id}: zoom control overlap`);
    assert.equal(record.reader?.protected_content_exposed, false, `${record.state_id}: Reader protected content`);
    assert.equal(record.reader?.protected_prefetch, false, `${record.state_id}: Reader protected prefetch`);
    assert.equal(record.reader?.balance_consumption, 0, `${record.state_id}: Reader balance consumption`);
    assert.equal(record.listener?.raw_media_url, "absent", `${record.state_id}: Listener media URL`);
    assert.equal(record.listener?.playable_source, "absent", `${record.state_id}: Listener source`);
    assert.equal(record.listener?.autoplay, false, `${record.state_id}: Listener autoplay`);
    assert.equal(record.listener?.preload, "absent", `${record.state_id}: Listener preload`);
    assert.equal(record.listener?.balance_consumption, 0, `${record.state_id}: Listener balance consumption`);
    if (record.interaction === "open-mobile-menu" || record.interaction === "open-library-filters") assertEmpty(record.interaction_result?.failures, `${record.state_id}: interaction failures`);
    if (record.fixture === "error-404-contract" || record.fixture === "tombstone-410-contract") {
      assert.equal(record.status_contract?.result, "PASS", `${record.state_id}: status contract`);
      assert.ok(fs.existsSync(path.join(stateOutputDirectory(output, record.state_id), "status-contract-results.json")), `${record.state_id}: status contract output missing`);
    }
    for (const screenshot of Object.values(record.screenshot_paths)) assertPng(path.join(stateOutputDirectory(output, record.state_id), screenshot));
    assert.ok(!/\b(?:PENDING|NOT RUN|WORKFLOW RUNNING)\b/.test(JSON.stringify(record)), `${record.state_id}: mandatory pending value`);
  }
  assert.ok(fs.existsSync(path.join(output, "route-surface-hashes.json")), "route surface hashes are missing");
  return summary;
}

function createSynthetic(output, productionSurface) {
  const head = git("rev-parse", "HEAD"); const tree = git("rev-parse", "HEAD^{tree}");
  for (const state of manifest.states) {
    const directory = stateOutputDirectory(output, state.id); fs.mkdirSync(directory, { recursive: true }); fs.writeFileSync(path.join(directory, "viewport.png"), png);
    const metadata = { source_head: head, tree_sha: tree, state_id: state.id, route: state.route, stable: true, fixture: state.fixture, interaction: state.interaction, rendered_ui_result: "PASS", visible_header_count: 1, visible_canonical_lockup_count: 1, logo: { transform: "none", wrapper_background: "rgba(0, 0, 0, 0)", wrapper_border_width: "0px", wrapper_border_radius: "0px", wrapper_box_shadow: "none", wrapper_padding: "0px", clipped: false }, overlap: false, horizontal_overflow: false, console_error_count: 0, page_error_count: 0, failed_required_request_count: 0, reader: { protected_content_exposed: false, protected_prefetch: false, balance_consumption: 0 }, listener: { raw_media_url: "absent", playable_source: "absent", autoplay: false, preload: "absent", balance_consumption: 0 }, zoom_results: { clipped_control_count: 0, logo_control_overlap_area: 0 }, interaction_result: state.interaction === "none" || state.interaction === "sanitize-account-fixture" || state.interaction === "scroll-to-footer" ? undefined : { failures: [] }, screenshot_paths: { viewport: "viewport.png" }, screenshot_sha256: { viewport: sha(png) } };
    if (state.fixture === "error-404-contract" || state.fixture === "tombstone-410-contract") { metadata.status_contract = { result: "PASS" }; fs.writeFileSync(path.join(directory, "status-contract-results.json"), JSON.stringify(metadata.status_contract)); }
    fs.writeFileSync(path.join(directory, "metadata.json"), JSON.stringify(metadata));
  }
  const classifications = { PUBLIC_INDEXABLE: 1 };
  const summary = { source_head: head, tree_sha: tree, manifest_path: manifestPath, manifest_sha256: sha(fs.readFileSync(manifestPath)), route_inventory_path: "synthetic", route_inventory_sha256: "synthetic", production_surface_sha256: productionSurface, canonical_logo_sha256: logoHash, requested_state_ids: expectedIds, captured_state_ids: expectedIds, manifest_order_execution_list: expectedIds, missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], expected_state_count: 65, captured_state_count: 65, stable_state_count: 65, unstable_state_count: 0, generated_screenshot_count: 65, menu_state_count: 4, filter_state_count: 2, zoom_100_state_count: 1, zoom_150_state_count: 1, zoom_200_state_count: 1, route_family_counts: classifications, raw_duplicate_logo_states: [], transform_logo_states: [], logo_card_states: [], clipped_logo_states: [], clipped_control_states: [], logo_control_overlap_states: [], multiple_header_states: [], horizontal_overflow_states: [], interaction_failure_states: [], reader_safety_defect_states: [], listener_safety_defect_states: [], status_contract_defect_states: [], static_parity_defect_states: [], runtime_failure_states: [], rendered_ui_defect_states: [], production_mutation_count: 0 };
  fs.writeFileSync(path.join(output, "capture-summary.json"), JSON.stringify(summary)); fs.writeFileSync(path.join(output, "route-surface-hashes.json"), "{}"); return summary;
}

const expectedProduction = process.env.SEAMLESS_BRAND_EXPECTED_PRODUCTION_SURFACE || "synthetic-production-surface";
const synthetic = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-full-chromium-")); createSynthetic(synthetic, expectedProduction);
let cases = 0; const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };
const load = () => JSON.parse(fs.readFileSync(path.join(synthetic, "capture-summary.json"), "utf8")); const save = (summary) => fs.writeFileSync(path.join(synthetic, "capture-summary.json"), JSON.stringify(summary));
test("final manifest contains sixty-five states", () => assert.equal(expectedIds.length, 65));
test("expected IDs derive from manifest order", () => assert.deepEqual(load().requested_state_ids, expectedIds));
test("all sixty-five states are required", () => validateFullChromiumMatrix(synthetic, expectedProduction));
test("missing state fails", () => { const s = load(); s.missing_state_ids = [expectedIds[0]]; save(s); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("duplicate state fails", () => { const s = load(); s.duplicate_state_ids = [expectedIds[0]]; save(s); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("unstable state fails", () => { const s = load(); s.stable_state_count = 64; s.unstable_state_count = 1; save(s); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("interaction failure fails", () => { const p = path.join(stateOutputDirectory(synthetic, "home-menu-open-390"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.interaction_result.failures = ["focus-trap"]; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("zoom failure fails", () => { const p = path.join(stateOutputDirectory(synthetic, "reader-mobile-390-zoom-200"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.zoom_results.clipped_control_count = 1; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("Reader safety failure fails", () => { const p = path.join(stateOutputDirectory(synthetic, "reader-mobile-390"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.reader.protected_prefetch = true; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("Listener safety failure fails", () => { const p = path.join(stateOutputDirectory(synthetic, "listener-mobile-390"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.listener.raw_media_url = "present"; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("status contract failure fails", () => { const p = path.join(stateOutputDirectory(synthetic, "error-404-desktop"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.status_contract.result = "FAIL"; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("logo card use fails", () => { const p = path.join(stateOutputDirectory(synthetic, "home-desktop"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.logo.wrapper_border_radius = "20px"; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("clipping fails", () => { const p = path.join(stateOutputDirectory(synthetic, "home-desktop"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.logo.clipped = true; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("control overlap fails", () => { const p = path.join(stateOutputDirectory(synthetic, "home-desktop"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.overlap = true; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("overflow fails", () => { const p = path.join(stateOutputDirectory(synthetic, "home-desktop"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.horizontal_overflow = true; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("runtime error fails", () => { const p = path.join(stateOutputDirectory(synthetic, "home-desktop"), "metadata.json"); const r = JSON.parse(fs.readFileSync(p)); r.console_error_count = 1; fs.writeFileSync(p, JSON.stringify(r)); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("production mutation fails", () => { const s = load(); s.production_mutation_count = 1; save(s); assert.throws(() => validateFullChromiumMatrix(synthetic, expectedProduction)); createSynthetic(synthetic, expectedProduction); });
test("valid synthetic sixty-five-state summary passes", () => validateFullChromiumMatrix(synthetic, expectedProduction));

const outputIndex = process.argv.indexOf("--output");
if (outputIndex >= 0) { const output = process.argv[outputIndex + 1]; if (!output) throw new Error("--output requires a directory"); validateFullChromiumMatrix(path.resolve(output), expectedProduction); }
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, output: outputIndex >= 0 ? path.resolve(process.argv[outputIndex + 1]) : null }));
