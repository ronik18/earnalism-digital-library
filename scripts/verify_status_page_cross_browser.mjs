#!/usr/bin/env node
import crypto from "node:crypto";
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const browserName = process.argv[2];
const output = path.resolve(process.argv[3] || "uat/evidence/status-page-cross-browser");
if (!new Set(["chromium", "firefox", "webkit"]).has(browserName)) throw new Error("Usage: node scripts/verify_status_page_cross_browser.mjs <chromium|firefox|webkit> <output>");

const states = [
  { id: "error-404-desktop", route: "/__seamless-brand-review-not-found-344__", fixture: "error-404", viewport: { width: 1440, height: 1000 }, expectedStatus: 404 },
  { id: "error-404-mobile", route: "/__seamless-brand-review-not-found-344__", fixture: "error-404", viewport: { width: 390, height: 844 }, expectedStatus: 404 },
  { id: "tombstone-410-desktop", route: "/product/patterned-wrap-dress", fixture: "tombstone-410", viewport: { width: 1440, height: 1000 }, expectedStatus: 410 },
  { id: "tombstone-410-mobile", route: "/product/patterned-wrap-dress", fixture: "tombstone-410", viewport: { width: 390, height: 844 }, expectedStatus: 410 },
];

function statusResponse(state) {
  const handler = require(path.resolve(state.fixture === "tombstone-410" ? "frontend/api/removed-content.js" : "frontend/api/not-found.js"));
  const result = { status: 200, headers: {}, body: "" };
  handler({ query: { path: state.route }, headers: {}, url: state.route }, {
    set statusCode(value) { result.status = value; },
    get statusCode() { return result.status; },
    setHeader(key, value) { result.headers[key] = value; },
    end(value) { result.body = value; },
  });
  return result;
}

const { [browserName]: browserType } = await import("playwright");
const browser = await browserType.launch({ headless: true });
const browserVersion = browser.version();
const results = [];
try {
  for (const state of states) {
    const fixture = statusResponse(state);
    const context = await browser.newContext({ viewport: state.viewport, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", serviceWorkers: "block" });
    const page = await context.newPage();
    const errors = []; const pageErrors = []; const failed = [];
    page.on("console", (entry) => { if (entry.type() === "error") errors.push(entry.text()); });
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("requestfailed", (request) => failed.push({ url: request.url(), error: request.failure()?.errorText || "unknown" }));
    await page.route("**/*", (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname === state.route) return route.fulfill({ status: fixture.status, headers: fixture.headers, body: fixture.body });
      if (pathname === "/assets/brand/earnalism-brand-lockup.png") return route.fulfill({ path: "frontend/public/assets/brand/earnalism-brand-lockup.png", contentType: "image/png" });
      return route.abort();
    });
    const response = await page.goto(`http://127.0.0.1:4174${state.route}`, { waitUntil: "load" });
    const statusNavigationConsoleErrors = [...errors];
    // Browsers log the deliberate 404/410 document response as a resource error.
    // The status contract is asserted independently, so it is not a page-runtime defect.
    errors.length = 0;
    await page.evaluate(async () => { await document.fonts.ready; await document.querySelector("img")?.decode(); });
    const data = await page.evaluate(() => {
      const header = document.querySelector('header[data-testid="status-brand-masthead"]');
      const logo = header?.querySelector('img[src="/assets/brand/earnalism-brand-lockup.png"]');
      const computed = logo && getComputedStyle(logo); const headerStyle = header && getComputedStyle(header);
      const rect = logo?.getBoundingClientRect(); const headerRect = header?.getBoundingClientRect();
      const visible = (node) => { const style = getComputedStyle(node); const bounds = node.getBoundingClientRect(); return style.display !== "none" && style.visibility !== "hidden" && bounds.width > 0 && bounds.height > 0; };
      let cardCount = 0; let node = logo?.parentElement;
      while (node && node !== document.body) { const style = getComputedStyle(node); const bounds = node.getBoundingClientRect(); if (bounds.width < innerWidth * .95 && (style.borderTopWidth !== "0px" || style.borderRadius !== "0px" || style.boxShadow !== "none")) cardCount += 1; node = node.parentElement; }
      return {
        header_count: [...document.querySelectorAll('header[data-testid="status-brand-masthead"]')].filter(visible).length,
        logo_count: [...document.querySelectorAll('img[src="/assets/brand/earnalism-brand-lockup.png"]')].filter(visible).length,
        card_count: cardCount,
        logo_transform: computed?.transform || null,
        logo_clipped: !rect || rect.left < 0 || rect.top < 0 || rect.right > innerWidth || rect.bottom > innerHeight,
        header_width_ratio: !headerRect ? 0 : headerRect.width / innerWidth,
        header_radius: headerStyle?.borderRadius || null,
        header_shadow: headerStyle?.boxShadow || null,
        overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        actions_valid: [...document.querySelectorAll(".status-page__action")].map((action) => action.getAttribute("href")).sort().join(",") === "/,/library",
      };
    });
    const screenshotPath = path.join(output, browserName, `${state.id}.png`);
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath, animations: "disabled", caret: "hide", scale: "css" });
    const pass = response?.status() === state.expectedStatus && fixture.headers["X-Robots-Tag"] === "noindex, nofollow, noarchive" && data.header_count === 1 && data.logo_count === 1 && data.card_count === 0 && data.logo_transform === "none" && !data.logo_clipped && data.header_width_ratio >= .95 && data.header_radius === "0px" && data.header_shadow === "none" && !data.overflow && data.actions_valid && errors.length === 0 && pageErrors.length === 0 && failed.length === 0;
    results.push({ ...state, response_status: response?.status(), headers: fixture.headers, ...data, status_navigation_console_errors: statusNavigationConsoleErrors, console_error_count: errors.length, page_error_count: pageErrors.length, failed_request_count: failed.length, screenshot_sha256: crypto.createHash("sha256").update(fs.readFileSync(screenshotPath)).digest("hex"), result: pass ? "PASS" : "FAIL" });
    await context.close();
  }
} finally { await browser.close(); }
const report = { browser: browserName, browser_version: browserVersion, states: results, result: results.every((state) => state.result === "PASS") ? "PASS" : "FAIL" };
fs.mkdirSync(path.join(output, browserName), { recursive: true });
fs.writeFileSync(path.join(output, browserName, "status-results.json"), JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report));
if (report.result !== "PASS") process.exitCode = 1;
