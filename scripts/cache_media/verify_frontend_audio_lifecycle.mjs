#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium, firefox, webkit } = require("../../frontend/node_modules/playwright");
const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");

if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) {
  throw new Error("UAT_BASE_URL must be an explicit loopback URL.");
}

const response = (slug) => ({
  book: { slug, title: slug, author: "Lifecycle test" },
  audio: { enabled: false, assets: {} },
  access: { reading_pass: { total_pages: 3 } },
  canonical_pages: { page_count: 3, pages: [] },
});

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function expectCancellation(page, pendingPath, initialUrl, navigateTo) {
  let requestObserved = false;
  const observedPaths = [];
  let observedResolve;
  const observed = new Promise((resolve) => { observedResolve = resolve; });
  let cancellationResolve;
  const cancellation = new Promise((resolve) => { cancellationResolve = resolve; });
  page.on("requestfailed", (request) => {
    if (new URL(request.url()).pathname === pendingPath) cancellationResolve(request.failure()?.errorText || "aborted");
  });
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    observedPaths.push(pathname);
    if (pathname === pendingPath) {
      requestObserved = true;
      observedResolve();
      await sleep(4_000);
      try { await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(response("first")) }); } catch { /* aborted request */ }
      return;
    }
    if (/\/reader\/book\/[^/]+\/manifest$/.test(pathname)) {
      const slug = pathname.split("/")[4];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(response(slug)) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });
  await page.goto(initialUrl, { waitUntil: "domcontentloaded" });
  await Promise.race([observed, sleep(3_000)]);
  await navigateTo();
  assert.equal(requestObserved, true, `expected pending request ${pendingPath}; observed ${observedPaths.join(", ")}`);
  const result = await Promise.race([cancellation, sleep(3_000).then(() => null)]);
  assert.ok(result, `expected route-owned request cancellation for ${pendingPath}`);
}

async function verifyFixture(page, route, viewport, requiredSelector, zoom = 1) {
  const errors = [];
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  await page.setViewportSize(viewport);
  await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded" });
  await page.locator(requiredSelector).waitFor({ state: "visible", timeout: 10_000 });
  await page.waitForTimeout(750);
  const result = await page.evaluate((scale) => {
    document.documentElement.style.zoom = String(scale);
    const listener = document.querySelector("#listener-v2-title");
    const reader = document.querySelector("#reader-v2-title");
    return {
      audio_count: document.querySelectorAll("audio").length,
      autoplay_count: document.querySelectorAll("audio[autoplay]").length,
      raw_provider_url_count: [...document.querySelectorAll("audio[src], audio source[src]")].filter((node) => /provider|storage|b2/i.test(node.getAttribute("src") || "")).length,
      horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      listener_visible: Boolean(listener?.getClientRects().length),
      reader_visible: Boolean(reader?.getClientRects().length),
    };
  }, zoom);
  const actionableErrors = errors.filter((entry) => !entry.includes("downloadable font: download failed"));
  assert.equal(actionableErrors.length, 0, `unexpected fixture errors for ${route}: ${actionableErrors.join(" | ")}`);
  assert.equal(result.audio_count, 0, `fixture must not create audio: ${route}`);
  assert.equal(result.autoplay_count, 0, `fixture must not autoplay: ${route}`);
  assert.equal(result.raw_provider_url_count, 0, `fixture must not expose provider URL: ${route}`);
  assert.equal(result.horizontal_overflow, false, `fixture must not overflow: ${route}`);
  return { route, viewport, zoom, local_fixture_font_warnings: errors.length - actionableErrors.length, ...result };
}

async function verifyEngine(browserName, browserType) {
  const browser = await browserType.launch({ headless: true });
  const results = [];
  try {
    const listener = await browser.newPage();
    await expectCancellation(listener, "/api/reader/book/first/manifest", `${baseUrl}/listener/first`, () => listener.evaluate(() => {
      history.pushState({}, "", "/listener/second");
      dispatchEvent(new PopStateEvent("popstate"));
    }));
    results.push("listener_manifest");
    await listener.close();

    const reader = await browser.newPage();
    await expectCancellation(reader, "/api/reader/book/first/manifest", `${baseUrl}/reader/first?p=1`, () => reader.evaluate(() => {
      history.pushState({}, "", "/reader/second?p=1");
      dispatchEvent(new PopStateEvent("popstate"));
    }));
    results.push("reader_manifest");
    await reader.close();

    const fixture = await browser.newPage();
    results.push(await verifyFixture(fixture, "/listener/a-ghost-story?visual-fixture=1", { width: 1440, height: 1000 }, "#listener-v2-title"));
    results.push(await verifyFixture(fixture, "/listener/a-ghost-story?visual-fixture=1", { width: 390, height: 844 }, "#listener-v2-title"));
    results.push(await verifyFixture(fixture, "/listener/a-ghost-story?visual-fixture=1", { width: 320, height: 568 }, "#listener-v2-title", 2));
    results.push(await verifyFixture(fixture, "/reader/dracula?visual-fixture=1", { width: 1440, height: 1000 }, "#reader-v2-title"));
    results.push(await verifyFixture(fixture, "/reader/dracula?visual-fixture=1", { width: 390, height: 844 }, "#reader-v2-title"));
    results.push(await verifyFixture(fixture, "/reader/dracula?visual-fixture=1", { width: 320, height: 568 }, "#reader-v2-title", 2));
    await fixture.close();
  } finally {
    await browser.close();
  }
  return { browser: browserName, results };
}

const reports = [];
for (const [name, browserType] of Object.entries({ chromium, firefox, webkit })) {
  reports.push(await verifyEngine(name, browserType));
}
const report = { schema_version: "cache-media-a7-frontend-lifecycle.v1", base_url: baseUrl, reports };
if (process.env.A7_REPORT_PATH) fs.writeFileSync(process.env.A7_REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify(report, null, 2));
