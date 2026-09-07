#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the isolated My Library journey.");

const output = process.env.MY_LIBRARY_EVIDENCE_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), "my-library-isolated-journey-"));
fs.mkdirSync(output, { recursive: true });

async function runScenario({ id, viewport, zoom = 100 }) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", serviceWorkers: "block" });
  const page = await context.newPage();
  const requests = [];
  const failures = [];
  page.on("request", (request) => requests.push({ url: request.url(), method: request.method() }));
  page.on("requestfailed", (request) => failures.push({ url: request.url(), error: request.failure()?.errorText || "unknown" }));
  await page.route("**/api/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));

  await page.goto(`${baseUrl.replace(/\/$/, "")}/my-library`, { waitUntil: "domcontentloaded" });
  await page.evaluate(async (requestedZoom) => {
    await document.fonts.ready;
    document.documentElement.style.zoom = `${requestedZoom}%`;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, zoom);

  const shelf = page.getByTestId("my-library-mobile");
  const browse = page.getByTestId("my-library-browse-ready");
  await shelf.waitFor();
  await browse.waitFor();
  assert.equal(await shelf.getByRole("heading", { name: "No saved titles to show." }).count(), 1, `${id}: truthful empty state is absent`);
  assert.equal(await browse.getAttribute("href"), "/library?availability=reader-ready", `${id}: reader-ready destination changed`);
  await browse.focus();
  assert.equal(await page.evaluate(() => document.activeElement?.getAttribute("data-testid")), "my-library-browse-ready", `${id}: primary action is not keyboard reachable`);

  const geometry = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    heading: document.querySelector("#my-library-title")?.textContent?.trim(),
    emptyState: document.querySelector("#my-library-empty-title")?.textContent?.trim(),
  }));
  assert.equal(geometry.scrollWidth, geometry.clientWidth, `${id}: document has horizontal overflow`);
  assert.equal(geometry.heading, "My Library", `${id}: heading changed unexpectedly`);
  assert.equal(geometry.emptyState, "No saved titles to show.", `${id}: empty state changed unexpectedly`);

  await page.screenshot({ path: path.join(output, `${id}.png`), fullPage: true });
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.search === "?availability=reader-ready"),
    page.keyboard.press("Enter"),
  ]);
  await page.getByTestId("library-reference-surface").waitFor();
  await page.goBack({ waitUntil: "domcontentloaded" });
  await shelf.waitFor();
  assert.equal(new URL(page.url()).pathname, "/my-library", `${id}: browser Back did not restore My Library`);
  await page.reload({ waitUntil: "domcontentloaded" });
  await shelf.waitFor();
  assert.equal(await shelf.getByRole("heading", { name: "No saved titles to show." }).count(), 1, `${id}: reload lost the truthful empty state`);

  await context.close();
  await browser.close();
  return { id, viewport, zoom, geometry, request_count: requests.length, api_requests: requests.filter(({ url }) => new URL(url).pathname.includes("/api/")).length, failed_requests: failures, result: "PASS" };
}

const results = [];
for (const scenario of [
  { id: "desktop-1440", viewport: { width: 1440, height: 900 } },
  { id: "tablet-768", viewport: { width: 768, height: 1024 } },
  { id: "mobile-390", viewport: { width: 390, height: 844 } },
  { id: "mobile-320-zoom-200", viewport: { width: 320, height: 568 }, zoom: 200 },
]) results.push(await runScenario(scenario));

const result = { result: "PASS", classification: "ISOLATED_UI_EVIDENCE_ONLY", output, results };
fs.writeFileSync(path.join(output, "summary.json"), `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify(result));
