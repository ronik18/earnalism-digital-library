#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadStateManifest } from "./lib/seamless_brand_state_manifest.mjs";

const root = process.cwd();
const selectionPath = path.join(root, "docs/design-system/seamless-brand-cross-browser-shell-matrix.json");
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const selection = JSON.parse(fs.readFileSync(selectionPath, "utf8"));
const manifest = loadStateManifest(manifestPath);
const ids = selection.families.map((family) => family.selected_state_id);
const png = Buffer.from("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0000003010100c9fe92ef0000000049454e44ae426082", "hex");
const sha = (value) => crypto.createHash("sha256").update(value).digest("hex");
const read = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const write = (file, value) => fs.writeFileSync(file, JSON.stringify(value));

function validate(output) {
  const summary = read(path.join(output, "cross-browser-summary.json"));
  assert.equal(summary.shell_family_count, 20, "shell-family count differs");
  assert.deepEqual(summary.selected_state_ids, ids, "selected IDs differ from selection contract");
  assert.equal(summary.production_mutation_count, 0, "production mutation recorded");
  for (const browser of ["firefox", "webkit"]) {
    const result = summary[browser];
    assert.ok(result.version, `${browser} version is missing`);
    assert.equal(result.expected_state_count, 20, `${browser} expected count differs`);
    assert.equal(result.captured_state_count, 20, `${browser} capture count differs`);
    assert.equal(result.stable_state_count, 20, `${browser} stability count differs`);
    assert.equal(result.font_result, "PASS", `${browser} font result fails`);
    assert.equal(result.interaction_result, "PASS", `${browser} interaction result fails`);
    assert.equal(result.reader_result, "PASS", `${browser} Reader result fails`);
    assert.equal(result.listener_result, "PASS", `${browser} Listener result fails`);
    assert.equal(result.status_result, "PASS", `${browser} error-status result fails`);
    assert.equal(result.rendered_ui_result, "PASS", `${browser} rendered UI result fails`);
    const metadata = ids.map((id) => read(path.join(output, browser, "states", id, "metadata.json")));
    for (const record of metadata) {
      assert.equal(record.browser, browser, `${browser}:${record.state_id} browser differs`);
      assert.equal(record.stable, true, `${browser}:${record.state_id} unstable`);
      assert.equal(record.rendered_ui_result, "PASS", `${browser}:${record.state_id} rendered UI failure`);
      assert.equal(record.unclassified_http_error_responses?.length || 0, 0, `${browser}:${record.state_id} has unclassified HTTP error`);
      if (record.fixture === "reader-visual-safe") assert.ok(!record.reader.protected_content_exposed && !record.reader.protected_prefetch && record.reader.balance_consumption === 0 && record.zoom_results.clipped_control_count === 0, `${browser}:${record.state_id} Reader safety or reflow fails`);
      if (record.fixture.includes("listener")) assert.ok(record.listener.raw_media_url === "absent" && record.listener.playable_source === "absent" && !record.listener.autoplay && record.listener.preload === "absent" && record.listener.balance_consumption === 0, `${browser}:${record.state_id} Listener safety fails`);
      if (record.fixture === "error-404-contract" || record.fixture === "tombstone-410-contract") assert.equal(record.status_contract?.result, "PASS", `${browser}:${record.state_id} status contract fails`);
      if (record.interaction_result) assert.deepEqual(record.interaction_result.failures, [], `${browser}:${record.state_id} interaction fails`);
    }
  }
  for (const key of ["duplicate_logo_states", "logo_card_states", "transform_states", "clipped_logo_states", "clipped_control_states", "overlap_states", "multiple_header_states", "overflow_states", "console_page_request_failure_states", "unclassified_http_error_states", "rendered_ui_defect_states"]) assert.deepEqual(summary[key], [], `${key} is not empty`);
  return summary;
}

function createSynthetic(output) {
  const records = [];
  for (const browser of ["firefox", "webkit"]) {
    for (const id of ids) {
      const state = manifest.states.find((item) => item.id === id); const directory = path.join(output, browser, "states", id); fs.mkdirSync(directory, { recursive: true }); fs.writeFileSync(path.join(directory, "viewport.png"), png);
      const metadata = { state_id: id, fixture: state.fixture, browser, stable: true, rendered_ui_result: "PASS", visible_header_count: 1, visible_canonical_lockup_count: 1, logo: { transform: "none", wrapper_border_width: "0px", wrapper_border_radius: "0px", wrapper_box_shadow: "none", clipped: false }, overlap: false, horizontal_overflow: false, console_error_count: 0, page_error_count: 0, failed_required_request_count: 0, unclassified_http_error_responses: [], zoom_results: { clipped_control_count: 0, logo_control_overlap_area: 0 }, font_results: { cormorant_garamond: true, outfit: true, noto_serif_bengali: true, noto_sans_bengali: true }, reader: { protected_content_exposed: false, protected_prefetch: false, balance_consumption: 0 }, listener: { raw_media_url: "absent", playable_source: "absent", autoplay: false, preload: "absent", balance_consumption: 0 }, production_mutation_count: 0, screenshot_paths: { viewport: "viewport.png" }, screenshot_sha256: { viewport: sha(png) }, interaction_result: state.interaction === "open-mobile-menu" || state.interaction === "open-library-filters" ? { failures: [] } : undefined, status_contract: state.fixture.includes("contract") ? { result: "PASS" } : undefined };
      write(path.join(directory, "metadata.json"), metadata); records.push(metadata);
    }
    const result = { browser, version: `${browser}-synthetic`, expected_state_count: 20, captured_state_count: 20, stable_state_count: 20, screenshot_count: 20, font_result: "PASS", interaction_result: "PASS", reader_result: "PASS", listener_result: "PASS", status_result: "PASS", rendered_ui_result: "PASS", production_mutation_count: 0, selected_state_ids: ids };
    fs.mkdirSync(path.join(output, browser), { recursive: true }); write(path.join(output, browser, "capture-summary.json"), { ...result, requested_state_ids: ids, captured_state_ids: ids });
  }
  const browserResult = (browser) => ({ browser, version: `${browser}-synthetic`, expected_state_count: 20, captured_state_count: 20, stable_state_count: 20, screenshot_count: 20, font_result: "PASS", interaction_result: "PASS", reader_result: "PASS", listener_result: "PASS", status_result: "PASS", rendered_ui_result: "PASS", production_mutation_count: 0, selected_state_ids: ids });
  write(path.join(output, "cross-browser-summary.json"), { shell_family_count: 20, selected_state_ids: ids, firefox: browserResult("firefox"), webkit: browserResult("webkit"), duplicate_logo_states: [], logo_card_states: [], transform_states: [], clipped_logo_states: [], clipped_control_states: [], overlap_states: [], multiple_header_states: [], overflow_states: [], console_page_request_failure_states: [], unclassified_http_error_states: [], rendered_ui_defect_states: [], production_mutation_count: 0 });
}

const synthetic = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-cross-browser-"));
createSynthetic(synthetic); let cases = 0;
const test = (name, callback) => { callback(); cases += 1; console.log(`PASS ${cases}: ${name}`); };
const reset = () => createSynthetic(synthetic);
const mutate = (callback) => { callback(); assert.throws(() => validate(synthetic)); reset(); };

test("selection contract resolves exactly twenty families", () => assert.equal(selection.families.length, 20));
test("every selected ID exists in the sixty-five-state manifest", () => assert.ok(ids.every((id) => manifest.states.some((state) => state.id === id))));
test("no duplicate selected ID", () => assert.equal(new Set(ids).size, 20));
test("missing shell family fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.shell_family_count = 19; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("missing Firefox state fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.firefox.captured_state_count = 19; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("missing WebKit state fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.webkit.captured_state_count = 19; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("unstable Firefox state fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.firefox.stable_state_count = 19; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("unstable WebKit state fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.webkit.stable_state_count = 19; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("missing browser version fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.firefox.version = ""; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("font failure fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.webkit.font_result = "FAIL"; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("unclassified WebKit 4xx or 5xx fails", () => mutate(() => { const p = path.join(synthetic, "webkit", "states", ids[0], "metadata.json"); const m = read(p); m.unclassified_http_error_responses = [{ status: 404 }]; write(p, m); }));
test("mobile-menu interaction failure fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.firefox.interaction_result = "FAIL"; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("Library-filter interaction failure fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.webkit.interaction_result = "FAIL"; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("Reader clipping or reflow failure fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.firefox.reader_result = "FAIL"; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("Reader safety failure fails", () => mutate(() => { const p = path.join(synthetic, "firefox", "states", "reader-mobile-390", "metadata.json"); const m = read(p); m.reader.protected_prefetch = true; write(p, m); }));
test("Listener media exposure fails", () => mutate(() => { const p = path.join(synthetic, "webkit", "states", "listener-mobile-390", "metadata.json"); const m = read(p); m.listener.raw_media_url = "present"; write(p, m); }));
test("404 or 410 contract failure fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.webkit.status_result = "FAIL"; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("zoom overflow failure fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.overflow_states = ["firefox:home-mobile-zoom-200"]; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("production mutation fails", () => mutate(() => { const s = read(path.join(synthetic, "cross-browser-summary.json")); s.production_mutation_count = 1; write(path.join(synthetic, "cross-browser-summary.json"), s); }));
test("valid synthetic two-browser summary passes", () => validate(synthetic));

const index = process.argv.indexOf("--output");
if (index >= 0) { const output = process.argv[index + 1]; if (!output) throw new Error("--output requires a directory"); validate(path.resolve(output)); }
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, output: index >= 0 ? path.resolve(process.argv[index + 1]) : null }));
