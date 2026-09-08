#!/usr/bin/env node
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import path from "node:path";
import { chromium } from "playwright";

const require = createRequire(import.meta.url);
const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("UAT_BASE_URL must be a loopback URL.");

const viewports = [
  ["narrow", 320, 568],
  ["mobile", 390, 844],
  ["tablet", 768, 1024],
  ["desktop", 1440, 900],
];

function invoke(handler, request) {
  const response = { headers: {}, body: "", statusCode: 200 };
  handler(request, {
    setHeader(key, value) { response.headers[key] = value; },
    end(value) { response.body = value; },
    set statusCode(value) { response.statusCode = value; },
    get statusCode() { return response.statusCode; },
  });
  return response;
}

async function routeClientPage(page, route, selector) {
  await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
  await page.evaluate((nextRoute) => {
    window.history.pushState({}, "", nextRoute);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, route);
  await page.waitForSelector(selector, { timeout: 30000 });
}

async function assertControls(page, selector, label) {
  const controls = await page.locator(selector).evaluateAll((elements) => elements.map((element) => {
    const box = element.getBoundingClientRect();
    return { text: element.textContent?.trim(), width: box.width, height: box.height };
  }));
  assert.ok(controls.length > 0, `${label}: controls must render`);
  for (const control of controls) {
    assert.ok(control.width >= 44 && control.height >= 44, `${label}: ${control.text} must be at least 44 by 44 CSS pixels`);
  }
}

async function focusByTab(page, testId, label) {
  for (let index = 0; index < 48; index += 1) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => document.activeElement?.getAttribute("data-testid"));
    if (focused === testId) return;
  }
  assert.fail(`${label}: Tab navigation did not reach ${testId}`);
}

const browser = await chromium.launch({ headless: true });
try {
  for (const [label, width, height] of viewports) {
    const context = await browser.newContext({ viewport: { width, height }, reducedMotion: "reduce" });
    const page = await context.newPage();
    await routeClientPage(page, "/micro-story", ".micro-story-page");
    assert.equal(await page.locator('[data-testid="micro-story-library-cta"]').getAttribute("href"), "/library?source=reading_invitation", `${label}: campaign source must remain intact`);
    assert.equal(await page.locator('[data-testid="micro-story-path-1"]').getAttribute("href"), "/library", `${label}: discovery path must remain Library`);
    assert.equal(await page.locator('[data-testid="micro-story-path-3"]').getAttribute("href"), "/pricing", `${label}: pass path must remain Pricing`);
    await assertControls(page, ".micro-story-page a[data-testid]", `${label}: Micro Story`);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${label}: Micro Story must not overflow`);
    await focusByTab(page, "micro-story-library-cta", `${label}: Micro Story`);
    await page.keyboard.press("Enter");
    await page.waitForURL("**/library?source=reading_invitation", { timeout: 30000 });

    await routeClientPage(page, "/__quiet-heritage-missing__", '[data-testid="not-found-page"]');
    assert.equal(await page.locator('[data-testid="not-found-library-link"]').getAttribute("href"), "/library", `${label}: 404 Library recovery target must remain canonical`);
    assert.equal(await page.locator('[data-testid="not-found-home-link"]').getAttribute("href"), "/", `${label}: 404 Home recovery target must remain canonical`);
    await assertControls(page, '.error-route-page a[data-testid]', `${label}: 404 recovery`);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${label}: 404 recovery must not overflow`);
    await focusByTab(page, "not-found-library-link", `${label}: 404 recovery`);
    await page.keyboard.press("Enter");
    await page.waitForURL("**/library", { timeout: 30000 });
    await context.close();
  }

  const notFound = require(path.resolve("frontend/api/not-found.js"));
  const removedContent = require(path.resolve("frontend/api/removed-content.js"));
  const unknown = invoke(notFound, { query: {}, headers: {}, url: "/__quiet-heritage-missing__" });
  const retired = invoke(removedContent, { query: { path: "/product/patterned-wrap-dress" }, headers: {}, url: "/product/patterned-wrap-dress" });
  for (const [label, response, status, eyebrow] of [["404", unknown, 404, "404 · Page unavailable"], ["410", retired, 410, "410 · Retired route"]]) {
    assert.equal(response.statusCode, status, `${label}: direct handler status must remain authoritative`);
    assert.equal(response.headers["X-Robots-Tag"], "noindex, nofollow, noarchive", `${label}: direct handler must remain noindex`);
    assert.match(response.body, new RegExp(eyebrow), `${label}: direct status copy must remain distinct`);
    assert.match(response.body, /href="\/library"/, `${label}: direct status must recover to Library`);
    assert.match(response.body, /href="\/"/, `${label}: direct status must recover to Home`);
    assert.match(response.body, /min-height: 44px/, `${label}: direct status controls must retain target size`);
  }
  console.log(JSON.stringify({ result: "PASS", viewports: viewports.map(([label]) => label), directHandlers: [404, 410] }));
} finally {
  await browser.close();
}
