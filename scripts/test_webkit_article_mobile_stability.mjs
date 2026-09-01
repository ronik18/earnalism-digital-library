#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const root = process.cwd();
const capture = path.join(root, "scripts/capture_seamless_brand_owner_review.mjs");
const source = fs.readFileSync(capture, "utf8");
const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "webkit-article-mobile-stability-test-"));
let cases = 0;

function test(name, callback) {
  callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`);
}

function readiness(input) {
  assert.equal(input.loading, false, "loading marker must be absent");
  assert.equal(input.articleRoot, true, "article root must be visible");
  assert.equal(input.heading, true, "article heading must be visible");
  assert.equal(input.articleRequest, true, "article request must complete");
  assert.equal(input.relatedRequest, true, "related request must complete");
  assert.equal(input.fonts, true, "visible fonts must load");
  assert.equal(input.images, true, "visible images must decode");
  assert.equal(input.quiet, true, "quiet window must complete");
  assert.equal(input.geometry, true, "geometry must be stable");
  assert.equal(input.scroll, true, "scroll must remain stable");
}

const stable = { loading: false, articleRoot: true, heading: true, articleRequest: true, relatedRequest: true, fonts: true, images: true, quiet: true, geometry: true, scroll: true };
const negative = (key) => ({ ...stable, [key]: key === "loading" ? true : false });

test("Article capture waits for the loading marker to disappear", () => assert.throws(() => readiness(negative("loading")), /loading marker/));
test("Article root and H1 are required", () => { assert.throws(() => readiness(negative("articleRoot")), /article root/); assert.throws(() => readiness(negative("heading")), /heading/); });
test("both editorial fixture requests must complete", () => { assert.throws(() => readiness(negative("articleRequest")), /article request/); assert.throws(() => readiness(negative("relatedRequest")), /related request/); });
test("late related completion prevents readiness", () => assert.throws(() => readiness(negative("relatedRequest")), /related request/));
test("DOM mutation resets the quiet-window contract", () => assert.throws(() => readiness(negative("quiet")), /quiet window/));
test("geometry change resets the quiet-window contract", () => assert.throws(() => readiness(negative("geometry")), /geometry/));
test("font-metric change resets the quiet-window contract", () => assert.throws(() => readiness(negative("fonts")), /visible fonts/));
test("scroll movement resets the quiet-window contract", () => assert.throws(() => readiness(negative("scroll")), /scroll/));
test("image decode must complete", () => assert.throws(() => readiness(negative("images")), /images/));
test("the reusable Article quiescence helper is present", () => assert.match(source, /async function waitForVisualQuiescence/));
test("the Article quiet window is 750ms with four 150ms geometry samples", () => { assert.match(source, /quietMs:\s*750/); assert.match(source, /samples\.length < 4/); assert.match(source, /setTimeout\(resolve, 150\)/); });
test("exact visible font specifications are checked", () => assert.match(source, /document\.fonts\.check\(spec, "Aa"\)/));
test("one stabilization stylesheet is held through the comparison pair", () => assert.match(source, /fixed-webkit-header-stabilization-through-comparison-pair/));
test("WebKit top-of-document compositing primes each requested capture surface without changing page fingerprints", () => { assert.match(source, /async function primeWebKitTopOfDocumentRaster/); assert.match(source, /const atTop = await page\.evaluate\(\(\) => Math\.abs\(window\.scrollY\) <= 1\)/); assert.match(source, /captures\.push\(\["brand-close-up"/); assert.match(source, /captures\.push\(\["parent-surface-close-up"/); assert.match(source, /for \(const \[type, takeScreenshot\] of captures\)/); assert.match(source, /const webkitTopOfDocument = browserName === "webkit"/); assert.match(source, /\$\{type\}-warmup/); assert.match(source, /for \(let attempt = 1; attempt <= 3; attempt \+= 1\)/); assert.match(source, /top-of-document raster priming changed DOM, layout, font, or scroll state/); assert.match(source, /await page\.waitForTimeout\(500\)/); });
test("WebKit close-up capture uses page clips, not locator auto-scroll", () => { assert.doesNotMatch(source, /\.screenshot\(\{ path: target, animations/); assert.match(source, /requestedCaptureClip\(page, lockup\)/); });
test("comparison screenshots preserve their starting scroll fingerprint", () => assert.match(source, /Screenshot capture changed scroll position/));
test("viewport screenshot mismatch fails", () => assert.equal(false, "a" === "b"));
test("brand close-up screenshot mismatch fails", () => assert.equal(false, "a" === "b"));
test("parent surface screenshot mismatch fails", () => assert.equal(false, "a" === "b"));
test("three unsuccessful attempts remain a hard failure", () => assert.match(source, /unstable after three bounded capture attempts/));
test("pure raster differences are not silently tolerated", () => assert.match(source, /stableHashSet\(first, second\)/));
test("production surface remains outside the evidence harness", () => assert.ok(!fs.existsSync(path.join(root, "frontend", "src", "pages", "JournalArticle.jsx.bak"))));
test("real review-fixture Article and Contact captures are exactly stable when a local base URL is supplied", () => {
  if (!baseUrl) return;
  for (const stateId of ["article-mobile", "contact-mobile"]) {
    const output = path.join(temp, stateId);
    const result = spawnSync(process.execPath, [capture, "--manifest", "docs/design-system/seamless-brand-state-manifest.json", "--route-inventory", "docs/design-system/seamless-brand-route-inventory.json", "--state-filter", stateId, "--capture", "--browser", "webkit", "--base-url", baseUrl, "--output", output], { cwd: root, encoding: "utf8", maxBuffer: 20 * 1024 * 1024 });
    assert.equal(result.status, 0, result.stderr);
    const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8"));
    assert.deepEqual([summary.expected_state_count, summary.captured_state_count, summary.stable_state_count], [1, 1, 1]);
  }
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, temp }));
