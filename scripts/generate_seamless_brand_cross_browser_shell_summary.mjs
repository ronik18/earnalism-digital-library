#!/usr/bin/env node
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { loadStateManifest } from "./lib/seamless_brand_state_manifest.mjs";

const root = process.cwd();
const defaultSelection = "docs/design-system/seamless-brand-cross-browser-shell-matrix.json";
const defaultManifest = "docs/design-system/seamless-brand-state-manifest.json";
const defaultInventory = "docs/design-system/seamless-brand-route-inventory.json";
const logoPath = "frontend/public/assets/brand/earnalism-brand-lockup.png";
const requiredFonts = ["cormorant_garamond", "outfit", "noto_serif_bengali", "noto_sans_bengali"];

function argument(name) { const at = process.argv.indexOf(name); return at < 0 ? undefined : process.argv[at + 1]; }
function sha(file) { return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex"); }
function git(...args) { return execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim(); }
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function writeJson(file, value) { fs.writeFileSync(file, JSON.stringify(value, null, 2) + "\n"); }
function productionSurfaceHash() {
  const files = [];
  const walk = (directory) => { for (const entry of fs.readdirSync(directory, { withFileTypes: true })) { const file = path.join(directory, entry.name); if (entry.isDirectory()) walk(file); else if (!/(^|\/)(__tests__\/|.*\.(test|spec)\.[^/]+$)/.test(file)) files.push(file); } };
  walk("frontend/src"); walk("frontend/public"); files.push("frontend/package.json", "frontend/package-lock.json", "frontend/vercel.json");
  return crypto.createHash("sha256").update(files.sort().map((file) => `${sha(file)}  ${file}\n`).join("")).digest("hex");
}
function requireValue(condition, message) { if (!condition) throw new Error(message); }
function validPng(file) { const bytes = fs.readFileSync(file); return bytes.length > 8 && bytes.subarray(0, 8).equals(Buffer.from("89504e470d0a1a0a", "hex")); }

const output = path.resolve(argument("--output") || "");
const selectionPath = path.resolve(argument("--selection") || defaultSelection);
const manifestPath = path.resolve(argument("--manifest") || defaultManifest);
const inventoryPath = path.resolve(argument("--route-inventory") || defaultInventory);
requireValue(output, "--output is required");
const selection = readJson(selectionPath); const manifest = loadStateManifest(manifestPath); const inventory = readJson(inventoryPath);
const ids = selection.families.map((family) => family.selected_state_id);
requireValue(selection.families.length === 20, "selection must contain exactly twenty shell families");
requireValue(new Set(ids).size === 20, "selection contains duplicate state IDs");
requireValue(sha(manifestPath) === selection.source_state_manifest_sha256, "selection state-manifest SHA differs");
requireValue(sha(inventoryPath) === selection.source_route_inventory_sha256, "selection route-inventory SHA differs");
const states = new Map(manifest.states.map((state) => [state.id, state]));
for (const family of selection.families) {
  const state = states.get(family.selected_state_id);
  requireValue(Boolean(state), `selection references unknown state ${family.selected_state_id}`);
  requireValue(state.route === family.route && state.viewport.width === family.viewport?.width && state.viewport.height === family.viewport?.height && state.zoom === family.zoom && state.fixture === family.fixture && state.interaction === family.interaction, `selection record does not match manifest state ${family.selected_state_id}`);
}

const browserResults = {};
for (const browser of ["firefox", "webkit"]) {
  const browserDirectory = path.join(output, browser); const summaryPath = path.join(browserDirectory, "capture-summary.json");
  const capture = readJson(summaryPath); const metadata = ids.map((id) => readJson(path.join(browserDirectory, "states", id, "metadata.json")));
  requireValue(capture.expected_state_count === 20 && capture.captured_state_count === 20 && capture.stable_state_count === 20, `${browser}: expected 20 stable captures`);
  requireValue(metadata.every((record) => record.browser === browser && record.stable), `${browser}: metadata browser or stability mismatch`);
  const fontFailures = metadata.filter((record) => !requiredFonts.every((font) => record.font_results?.[font] === true)).map((record) => record.state_id);
  const interactionFailures = metadata.filter((record) => record.interaction_result?.failures?.length).map((record) => record.state_id);
  const readerFailures = metadata.filter((record) => record.fixture === "reader-visual-safe" && (record.reader.protected_content_exposed || record.reader.protected_prefetch || record.reader.balance_consumption !== 0 || record.zoom_results?.clipped_control_count > 0)).map((record) => record.state_id);
  const listenerFailures = metadata.filter((record) => record.fixture.includes("listener") && (record.listener.raw_media_url !== "absent" || record.listener.playable_source !== "absent" || record.listener.autoplay || record.listener.preload !== "absent" || record.listener.balance_consumption !== 0)).map((record) => record.state_id);
  const statusFailures = metadata.filter((record) => (record.fixture === "error-404-contract" || record.fixture === "tombstone-410-contract") && record.status_contract?.result !== "PASS").map((record) => record.state_id);
  const defects = metadata.filter((record) => record.rendered_ui_result !== "PASS" || record.visible_header_count !== 1 || record.visible_canonical_lockup_count !== 1 || record.logo?.transform !== "none" || record.logo?.clipped || record.overlap || record.horizontal_overflow || record.console_error_count || record.page_error_count || record.failed_required_request_count || record.unclassified_http_error_responses?.length).map((record) => record.state_id);
  const screenshotsDirectory = path.join(browserDirectory, "screenshots"); fs.mkdirSync(screenshotsDirectory, { recursive: true });
  let screenshotCount = 0;
  for (const record of metadata) for (const [label, relative] of Object.entries(record.screenshot_paths || {})) { const source = path.join(browserDirectory, "states", record.state_id, relative); requireValue(fs.existsSync(source) && validPng(source), `${browser}:${record.state_id}:${label} invalid PNG`); requireValue(sha(source) === record.screenshot_sha256[label], `${browser}:${record.state_id}:${label} SHA mismatch`); fs.copyFileSync(source, path.join(screenshotsDirectory, `${record.state_id}-${relative}`)); screenshotCount += 1; }
  const result = { browser, version: capture.browser_version, expected_state_count: capture.expected_state_count, captured_state_count: capture.captured_state_count, stable_state_count: capture.stable_state_count, screenshot_count: screenshotCount, font_result: fontFailures.length === 0 ? "PASS" : "FAIL", font_failure_states: fontFailures, interaction_result: interactionFailures.length === 0 ? "PASS" : "FAIL", interaction_failure_states: interactionFailures, reader_result: readerFailures.length === 0 ? "PASS" : "FAIL", reader_failure_states: readerFailures, listener_result: listenerFailures.length === 0 ? "PASS" : "FAIL", listener_failure_states: listenerFailures, status_result: statusFailures.length === 0 ? "PASS" : "FAIL", status_failure_states: statusFailures, rendered_ui_result: defects.length === 0 ? "PASS" : "FAIL", rendered_ui_defect_states: defects, production_mutation_count: metadata.reduce((sum, record) => sum + (record.production_mutation_count || 0), 0), selected_state_ids: ids };
  writeJson(path.join(browserDirectory, "selection-contract.json"), { selection_path: selectionPath, families: selection.families });
  writeJson(path.join(browserDirectory, "browser-results.json"), result);
  writeJson(path.join(browserDirectory, "font-results.json"), { browser, required_fonts: requiredFonts, records: metadata.map((record) => ({ state_id: record.state_id, font_results: record.font_results })) });
  writeJson(path.join(browserDirectory, "interaction-results.json"), metadata.filter((record) => record.interaction_result).map((record) => ({ state_id: record.state_id, result: record.interaction_result })));
  writeJson(path.join(browserDirectory, "safety-results.json"), metadata.filter((record) => record.fixture.includes("reader") || record.fixture.includes("listener")).map((record) => ({ state_id: record.state_id, reader: record.reader, listener: record.listener })));
  browserResults[browser] = result;
}
const combined = Object.values(browserResults);
const allMetadata = ["firefox", "webkit"].flatMap((browser) => ids.map((id) => readJson(path.join(output, browser, "states", id, "metadata.json"))));
const statesWith = (predicate) => allMetadata.filter(predicate).map((record) => `${record.browser}:${record.state_id}`);
const summary = { source_head: git("rev-parse", "HEAD"), tree_sha: git("rev-parse", "HEAD^{tree}"), state_manifest_path: manifestPath, state_manifest_sha256: sha(manifestPath), route_inventory_path: inventoryPath, route_inventory_sha256: sha(inventoryPath), selection_contract_path: selectionPath, selection_contract_sha256: sha(selectionPath), production_surface_sha256: productionSurfaceHash(), canonical_logo_sha256: sha(logoPath), shell_family_count: 20, selected_state_ids: ids, firefox: browserResults.firefox, webkit: browserResults.webkit, interaction_result_counts: Object.fromEntries(combined.map((result) => [result.browser, result.interaction_result])), reader_result_counts: Object.fromEntries(combined.map((result) => [result.browser, result.reader_result])), listener_result_counts: Object.fromEntries(combined.map((result) => [result.browser, result.listener_result])), error_state_result_counts: Object.fromEntries(combined.map((result) => [result.browser, result.status_result])), zoom_result_counts: Object.fromEntries(combined.map((result) => [result.browser, allMetadata.filter((record) => record.browser === result.browser && record.zoom > 100).length])), font_result_counts: Object.fromEntries(combined.map((result) => [result.browser, result.font_result])), duplicate_logo_states: statesWith((record) => record.visible_canonical_lockup_count !== 1), logo_card_states: statesWith((record) => record.logo?.wrapper_border_width !== "0px" || record.logo?.wrapper_border_radius !== "0px" || record.logo?.wrapper_box_shadow !== "none"), transform_states: statesWith((record) => record.logo?.transform !== "none"), clipped_logo_states: statesWith((record) => record.logo?.clipped), clipped_control_states: statesWith((record) => record.zoom_results?.clipped_control_count > 0), overlap_states: statesWith((record) => record.overlap || record.zoom_results?.logo_control_overlap_area > 0), multiple_header_states: statesWith((record) => record.visible_header_count !== 1), overflow_states: statesWith((record) => record.horizontal_overflow), console_page_request_failure_states: statesWith((record) => record.console_error_count || record.page_error_count || record.failed_required_request_count), unclassified_http_error_states: statesWith((record) => record.unclassified_http_error_responses?.length), rendered_ui_defect_states: statesWith((record) => record.rendered_ui_result !== "PASS"), production_mutation_count: allMetadata.reduce((sum, record) => sum + (record.production_mutation_count || 0), 0), generated_timestamp: new Date().toISOString() };
writeJson(path.join(output, "cross-browser-summary.json"), summary);
console.log(JSON.stringify({ result: "PASS", output, firefox: browserResults.firefox, webkit: browserResults.webkit }));
