#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { chromium } from "playwright";

const require = createRequire(import.meta.url);
const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(process.env.OWNER_REVIEW_CAPTURE_OUTPUT || "uat/evidence/editorial-support-owner-review/current");
const strict = process.env.OWNER_REVIEW_STRICT === "true";
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("UAT_BASE_URL must be a loopback URL.");

const posts = [
  { slug: "how-reading-shapes-better-founders", title: "How Reading Shapes Better Founders", excerpt: "The founders who endure make room for attention, context, and the stories that clarify a decision.", author: "The Earnalism", category: "Self-Growth", created_at: "2026-05-10T00:00:00.000Z", cover_image_url: "", content: "Reading creates a pause before action.\n\nThat pause makes room for better questions and more careful work." },
  { slug: "why-every-small-business-needs-a-story-before-a-strategy", title: "Why Every Small Business Needs a Story Before a Strategy", excerpt: "Strategy works best when a clear story gives it shape.", author: "The Earnalism", category: "Business", created_at: "2026-05-10T00:00:00.000Z", cover_image_url: "", content: "A story gives strategy a human scale.\n\nIt helps a reader understand what matters." },
];
const states = [
  ["journal-desktop", "/journal", 1440, 1000, "[data-testid=journal-page]"],
  ["journal-mobile", "/journal", 390, 844, "[data-testid=journal-page]"],
  ["article-desktop", "/journal/how-reading-shapes-better-founders", 1440, 1000, "[data-testid=journal-article]"],
  ["article-mobile", "/journal/how-reading-shapes-better-founders", 390, 844, "[data-testid=journal-article]"],
  ["article-not-found-desktop", "/journal/quiet-heritage-missing", 1440, 1000, "[data-testid=journal-article-not-found]"],
  ["article-not-found-mobile", "/journal/quiet-heritage-missing", 390, 844, "[data-testid=journal-article-not-found]"],
  ["about-desktop", "/about", 1440, 1000, ".about-v3, .about-v2"],
  ["about-mobile", "/about", 390, 844, ".about-v3, .about-v2"],
  ["contact-desktop", "/contact", 1440, 1000, "[data-testid=contact-page]"],
  ["contact-mobile", "/contact", 390, 844, "[data-testid=contact-page]"],
  ["micro-story-desktop", "/micro-story", 1440, 1000, ".micro-story-page"],
  ["micro-story-mobile", "/micro-story", 390, 844, ".micro-story-page"],
  ["not-found-desktop", "/not-a-real-route", 1440, 1000, "[data-testid=not-found-page]"],
  ["not-found-mobile", "/not-a-real-route", 390, 844, "[data-testid=not-found-page]"],
];

function removedHtml() {
  const handler = require(path.resolve("frontend/api/removed-content.js"));
  let body = "";
  const response = { statusCode: 0, setHeader() {}, end(value) { body = value; } };
  handler({ query: { path: "/product/patterned-wrap-dress" }, headers: {}, url: "/product/patterned-wrap-dress" }, response);
  return { body, status: response.statusCode };
}

function notFoundHtml() {
  const handler = require(path.resolve("frontend/api/not-found.js"));
  let body = "";
  const response = { statusCode: 0, setHeader() {}, end(value) { body = value; } };
  handler({ query: {}, headers: {}, url: "/quiet-heritage-missing" }, response);
  return { body, status: response.statusCode };
}

async function captureApp(browser, state) {
  const [id, route, width, height, required] = state;
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", reducedMotion: "reduce" });
  await context.route("**/api/**", async (request) => {
    const pathname = new URL(request.request().url()).pathname;
    const payload = pathname.endsWith("/blog") ? posts : pathname.endsWith("/blog/how-reading-shapes-better-founders") ? posts[0] : pathname.endsWith("/settings") ? {} : null;
    await request.fulfill({ status: payload ? 200 : 404, contentType: "application/json", body: JSON.stringify(payload || { detail: "fixture route not found" }) });
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    const messageText = message.text();
    if (message.type() === "error" && !/Failed to load resource: the server responded with a status of 404/i.test(messageText)) errors.push(messageText);
  });
  const response = await page.goto(baseUrl + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.evaluate((nextRoute) => { window.history.pushState({}, "", nextRoute); window.dispatchEvent(new PopStateEvent("popstate")); }, route);
  await page.waitForSelector(required, { timeout: 30000 });
  await page.keyboard.press("Tab");
  const metrics = await page.evaluate((selector) => ({ required: Boolean(document.querySelector(selector)), overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, focus: Boolean(document.activeElement?.matches("a[href],button,input,textarea,select")), logo: Array.from(document.images).some((image) => /earnalism/i.test(image.alt || "") && image.naturalWidth > 0) }), required);
  await page.screenshot({ path: path.join(output, id + ".png"), fullPage: false, animations: "disabled" });
  await context.close();
  return { id, route, viewport: { width, height }, status: response?.status() || 0, errors, ...metrics, fixture_only: true, evidence_scope: "LOCAL_ISOLATED_CAPTURE" };
}

async function captureDirectStatus(browser, id, width, height, source, route, handler) {
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", reducedMotion: "reduce" });
  const page = await context.newPage();
  const fontPaths = ["/assets/fonts/eb-garamond-400.ttf", "/assets/fonts/outfit-400.ttf", "/assets/fonts/outfit-600.ttf"];
  const fontResponses = new Map();
  const fontResourceErrors = [];
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("requestfailed", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (fontPaths.includes(pathname)) fontResourceErrors.push({ pathname, error: request.failure()?.errorText || "unknown request failure" });
  });
  page.on("response", (response) => {
    const pathname = new URL(response.url()).pathname;
    if (fontPaths.includes(pathname)) fontResponses.set(pathname, response.status());
  });
  const result = handler();
  const fixtureRoute = `${baseUrl}/__isolated-direct-status-${id}`;
  await page.route(fixtureRoute, async (route) => {
    await route.fulfill({ status: result.status, contentType: "text/html; charset=utf-8", body: result.body });
  });
  const documentResponse = await page.goto(fixtureRoute, { waitUntil: "load" });
  if (documentResponse?.status() !== result.status) errors.push(`direct status response changed from ${result.status} to ${documentResponse?.status() ?? "missing"}`);
  const metrics = await page.evaluate(async () => {
    await Promise.all([
      document.fonts.load('400 16px "EB Garamond"'),
      document.fonts.load("400 16px Outfit"),
      document.fonts.load("600 16px Outfit"),
    ]);
    await document.fonts.ready;
    return {
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      logo: Array.from(document.images).some((image) => /earnalism/i.test(image.alt || "") && image.naturalWidth > 0),
      font_faces: Array.from(document.fonts).map((face) => ({ family: face.family.replaceAll('"', ""), weight: String(face.weight), status: face.status })),
    };
  });
  await page.keyboard.press("Tab");
  metrics.focus = await page.evaluate(() => document.activeElement?.matches('a[href]') || false);
  const fontResources = fontPaths.map((pathname) => ({ pathname, status: fontResponses.get(pathname) ?? null }));
  const requiredFaces = [["EB Garamond", "400"], ["Outfit", "400"], ["Outfit", "600"]];
  const fontsLoaded = fontResources.every((resource) => resource.status === 200)
    && fontResourceErrors.length === 0
    && requiredFaces.every(([family, weight]) => metrics.font_faces.some((face) => face.family === family && face.weight === weight && face.status === "loaded"));
  if (!fontsLoaded) errors.push("direct status document font resources or FontFace entries did not load");
  await page.screenshot({ path: path.join(output, id + ".png"), fullPage: false, animations: "disabled" });
  await context.close();
  return { id, route, viewport: { width, height }, status: result.status, document_response_status: documentResponse?.status() ?? null, errors, required: true, ...metrics, font_resources: fontResources, font_resource_errors: fontResourceErrors, fonts_loaded: fontsLoaded, fixture_only: true, evidence_scope: "LOCAL_ISOLATED_HANDLER_CAPTURE", handler: source };
}

fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const captures = [];
  for (const state of states) captures.push(await captureApp(browser, state));
  captures.push(await captureDirectStatus(browser, "not-found-direct-desktop", 1440, 1000, "not-found", "/quiet-heritage-missing", notFoundHtml));
  captures.push(await captureDirectStatus(browser, "not-found-direct-mobile", 390, 844, "not-found", "/quiet-heritage-missing", notFoundHtml));
  captures.push(await captureDirectStatus(browser, "removed-desktop", 1440, 1000, "removed-content", "/product/patterned-wrap-dress", removedHtml));
  captures.push(await captureDirectStatus(browser, "removed-mobile", 390, 844, "removed-content", "/product/patterned-wrap-dress", removedHtml));
  fs.writeFileSync(path.join(output, "capture.json"), JSON.stringify(captures, null, 2) + "\n");
  const failures = captures.filter((item) => item.errors.length || item.overflow || (strict && (!item.required || !item.focus || !item.logo || ("fonts_loaded" in item && !item.fonts_loaded))) || item.status < 200 || item.status >= 500);
  console.log(JSON.stringify({ captured: captures.length, failed: failures.length, output }));
  if (failures.length) process.exitCode = 1;
} finally { await browser.close(); }
