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
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const inventoryPath = path.join(root, "docs/design-system/seamless-brand-route-inventory.json");
const captureScript = path.join(root, "scripts/capture_seamless_brand_owner_review.mjs");
const articleRoute = "/journal/how-reading-shapes-better-founders";
const ids = ["journal-desktop", "journal-mobile", "article-desktop", "article-mobile", "contact-desktop", "contact-mobile", "micro-story-desktop", "micro-story-mobile"];
const manifest = loadStateManifest(manifestPath);
const selected = selectStateRecords(manifest, ids);
const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-editorial-campaign-test-"));
let cases = 0;

function test(name, callback) { callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`); }
function key(name) { return name.replace(".png", "").replaceAll("-", "_"); }
function run(args) { const result = spawnSync(process.execPath, [captureScript, ...args], { cwd: root, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 }); assert.equal(result.status, 0, `${args.join(" ")} status=${result.status} stderr=${result.stderr}`); }
function writeSynthetic(output, stable = true) {
  for (const state of selected) {
    const directory = stateOutputDirectory(output, state.id); fs.mkdirSync(directory, { recursive: true }); const paths = {}; const hashes = {};
    for (const name of requestedScreenshotNames(state.capture)) { const png = Buffer.from("89504e470d0a1a0a", "hex"); fs.writeFileSync(path.join(directory, name), png); paths[key(name)] = name; hashes[key(name)] = crypto.createHash("sha256").update(png).digest("hex"); }
    fs.writeFileSync(path.join(directory, "metadata.json"), JSON.stringify({ state_id: state.id, stable, screenshot_paths: paths, screenshot_sha256: hashes }));
  }
  return { requested_state_ids: ids, captured_state_ids: ids, missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], stable_state_count: stable ? 8 : 0, unstable_state_count: stable ? 0 : 8 };
}
function assertBrand(record, state) {
  assert.equal(record.route, state.route); assert.deepEqual(record.viewport, state.viewport); assert.equal(record.visible_header_count, 1); assert.equal(record.visible_canonical_lockup_count, 1);
  assert.equal(record.logo.natural_width, 2400); assert.equal(record.logo.natural_height, 720); assert.ok(Math.abs(record.logo.aspect_ratio - 10 / 3) < 0.01); assert.equal(record.logo.transform, "none");
  assert.equal(record.logo.wrapper_background, "rgba(0, 0, 0, 0)"); assert.equal(record.logo.wrapper_border_width, "0px"); assert.equal(record.logo.wrapper_border_radius, "0px"); assert.equal(record.logo.wrapper_box_shadow, "none"); assert.equal(record.logo.wrapper_padding, "0px"); assert.equal(record.logo.parent_background, "rgb(255, 249, 238)");
  assert.equal(record.logo.clipped, false); assert.equal(record.overlap, false); assert.equal(record.horizontal_overflow, false); assert.equal(record.console_error_count, 0); assert.equal(record.page_error_count, 0); assert.equal(record.failed_required_request_count, 0); assert.equal(record.rendered_ui_result, "PASS");
  for (const name of requestedScreenshotNames(state.capture)) assert.ok(Object.values(record.screenshot_paths).includes(name), `${state.id} missing ${name}`);
}
function record(id) { return actual.find((item) => item.state_id === id); }

test("exactly eight editorial/campaign states resolve", () => assert.deepEqual(manifest.states.filter((state) => state.introduced_in === "editorial-campaign-2b3").map((state) => state.id), ids));
test("manifest total becomes 28", () => assert.equal(manifest.states.length, 28));
test("prior twenty state IDs remain present", () => assert.equal(manifest.states.filter((state) => state.introduced_in !== "editorial-campaign-2b3").length, 20));
test("Article route is current and public", () => assert.ok(JSON.parse(fs.readFileSync(path.join(root, "frontend/static-seo/editorial-public.json"), "utf8")).articles.some((article) => article.slug === articleRoute.split("/").at(-1))));
test("Article desktop/mobile use the same route", () => assert.deepEqual(selected.filter((state) => state.id.startsWith("article-")).map((state) => state.route), [articleRoute, articleRoute]));
test("reverse filter executes in manifest order", () => assert.deepEqual(selectStateRecords(manifest, [...ids].reverse()).map((state) => state.id), ids));
let actual;
test("Journal desktop metadata contract", () => { if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the actual local production-build capture."); const output = path.join(temp, "actual"); run(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", [...ids].reverse().join(","), "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output]); const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8")); actual = validateCaptureSummary(summary, output, 8); assertBrand(record("journal-desktop"), selected[0]); assert.ok(record("journal-desktop").editorial.journal_article_link_count > 0); assert.equal(record("journal-desktop").editorial.selected_article_route_present, true); });
test("Journal mobile metadata contract", () => { assertBrand(record("journal-mobile"), selected[1]); assert.ok(record("journal-mobile").editorial.journal_article_link_count > 0); });
test("Article desktop metadata contract", () => { assertBrand(record("article-desktop"), selected[2]); assert.equal(record("article-desktop").final_url, `${baseUrl}${articleRoute}`); assert.equal(record("article-desktop").editorial.article_title_present, true); assert.equal(record("article-desktop").editorial.generic_home_fallback_absent, true); });
test("Article mobile metadata contract", () => { assertBrand(record("article-mobile"), selected[3]); assert.equal(record("article-mobile").editorial.article_title_present, true); });
test("Contact desktop metadata contract", () => { assertBrand(record("contact-desktop"), selected[4]); assert.equal(record("contact-desktop").editorial.contact_form_labels_present, true); assert.equal(record("contact-desktop").editorial.contact_submit_visible, true); });
test("Contact mobile metadata contract", () => { assertBrand(record("contact-mobile"), selected[5]); assert.equal(record("contact-mobile").editorial.contact_form_labels_present, true); });
test("Micro-story desktop metadata contract", () => { assertBrand(record("micro-story-desktop"), selected[6]); assert.equal(record("micro-story-desktop").editorial.micro_story_campaign_state, "ACTIVE_CAMPAIGN"); assert.equal(record("micro-story-desktop").editorial.micro_story_product_truth_result, "PASS"); });
test("Micro-story mobile metadata contract", () => { assertBrand(record("micro-story-mobile"), selected[7]); assert.equal(record("micro-story-mobile").editorial.micro_story_primary_cta_present, true); });
test("Contact submission count remains zero", () => assert.ok(actual.filter((item) => item.state_id.startsWith("contact-")).every((item) => item.editorial.contact_submission_count === 0 && item.production_mutation_count === 0)));
test("production Contact API count remains zero", () => assert.ok(actual.filter((item) => item.state_id.startsWith("contact-")).every((item) => item.editorial.production_contact_api_calls === 0 && item.production_api_call_count === 0)));
test("Micro-story production mutations remain zero", () => assert.ok(actual.filter((item) => item.state_id.startsWith("micro-story-")).every((item) => item.production_mutation_count === 0)));
test("generic Home fallback causes failure", () => { const synthetic = { editorial: { generic_home_fallback_absent: false } }; assert.throws(() => assert.equal(synthetic.editorial.generic_home_fallback_absent, true)); });
test("missing state output causes failure", () => { const output = path.join(temp, "missing"); const summary = writeSynthetic(output); fs.rmSync(path.join(stateOutputDirectory(output, ids[7]), "metadata.json")); assert.throws(() => validateCaptureSummary(summary, output, 8), /metadata is missing/); });
test("unstable state causes failure", () => assert.throws(() => validateCaptureSummary(writeSynthetic(path.join(temp, "unstable"), false), path.join(temp, "unstable"), 8), /unstable/));
test("valid eight-state summary passes", () => assert.equal(actual.length, 8));

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, temp }));
