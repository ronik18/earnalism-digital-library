#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { chromium } from "playwright";

const require = createRequire(import.meta.url);
const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(process.env.OWNER_REVIEW_CAPTURE_OUTPUT || "uat/evidence/editorial-support-owner-review/current");
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
  return { id, route, viewport: { width, height }, status: response?.status() || 0, errors, ...metrics, fixture_only: route.startsWith("/journal") };
}

async function captureRemoved(browser, id, width, height) {
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", reducedMotion: "reduce" });
  const page = await context.newPage();
  const result = removedHtml();
  await page.setContent(result.body, { waitUntil: "load" });
  const metrics = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, logo: Array.from(document.images).some((image) => /earnalism/i.test(image.alt || "")), focus: true }));
  await page.screenshot({ path: path.join(output, id + ".png"), fullPage: false, animations: "disabled" });
  await context.close();
  return { id, route: "/product/patterned-wrap-dress", viewport: { width, height }, status: result.status, errors: [], required: true, ...metrics, fixture_only: false, handler: "removed-content" };
}

fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const captures = [];
  for (const state of states) captures.push(await captureApp(browser, state));
  captures.push(await captureRemoved(browser, "removed-desktop", 1440, 1000));
  captures.push(await captureRemoved(browser, "removed-mobile", 390, 844));
  fs.writeFileSync(path.join(output, "capture.json"), JSON.stringify(captures, null, 2) + "\n");
  const failures = captures.filter((item) => item.errors.length || item.overflow || !item.required || !item.focus || !item.logo || item.status < 200 || item.status >= 500);
  console.log(JSON.stringify({ captured: captures.length, failed: failures.length, output }));
  if (failures.length) process.exitCode = 1;
} finally { await browser.close(); }
