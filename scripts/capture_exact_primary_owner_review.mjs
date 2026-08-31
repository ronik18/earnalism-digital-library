#!/usr/bin/env node
/*
 * Owner-review capture only.  This intentionally lives outside the React
 * application: it provides deterministic, public-safe review responses to a
 * local static build and cannot change production API or entitlement state.
 */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { chromium } from "playwright";

const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(process.env.EXACT_OWNER_REVIEW_CAPTURE_OUTPUT || "uat/evidence/exact-primary-design/current");
const strict = process.env.OWNER_REVIEW_CAPTURE_STRICT !== "false";
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("UAT_BASE_URL must be an explicit loopback URL.");

const books = [
  { slug: "dracula", title: "Dracula", author: "Bram Stoker", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/dracula", audiobook_enabled: false, category_slug: "english-classics", chapters: [{ id: "dracula-canonical-page-1", is_preview: true }] },
  { slug: "devdas", title: "দেবদাস / Devdas", author: "Sarat Chandra Chattopadhyay", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/devdas", audiobook_enabled: false, category_slug: "bengali-classics", chapters: [{ id: "devdas-canonical-page-1", is_preview: true }] },
  { slug: "pather-panchali", title: "পথের পাঁচালী / Pather Panchali", author: "Bibhutibhushan Bandyopadhyay", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/pather-panchali", audiobook_enabled: false, category_slug: "bengali-classics", chapters: [{ id: "pather-panchali-canonical-page-1", is_preview: true }] },
  { slug: "hungry-stones", title: "Kshudhita Pashan / The Hungry Stones", author: "Rabindranath Tagore", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/hungry-stones", audiobook_enabled: false, category_slug: "bengali-classics", chapters: [{ id: "hungry-stones-canonical-page-1", is_preview: true }] },
  { slug: "a-ghost-story", title: "A Ghost Story", author: "Mark Twain", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/a-ghost-story", audiobook_enabled: true, category_slug: "english-classics", chapters: [{ id: "a-ghost-story-canonical-page-1", is_preview: true }] },
];
const packs = [
  { id: "30m", label: "The Opening Hour", minutes: 30, amount_paise: 4900, price_inr: 49, note: "Continue after the free preview, one careful sitting at a time." },
  { id: "1h", label: "The Quiet Hour", minutes: 60, amount_paise: 8900, price_inr: 89, note: "An unhurried first return to any eligible title." },
  { id: "3h", label: "The Deep Reading Pass", minutes: 180, amount_paise: 23900, price_inr: 239, note: "A longer weekend return to the classics you choose." },
  { id: "10h", label: "The Reader’s Reserve", minutes: 600, amount_paise: 49900, price_inr: 499, note: "Ten quiet hours kept for every eligible classic." },
];
const user = { id: "owner-review-fixture", name: "Review Reader", email: "review-fixture@invalid.example", reading_pass_seconds: 12900, reading_pass_enabled: true, transactions: [], devices: [] };
const selectedStates = new Set(String(process.env.EXACT_OWNER_REVIEW_STATE_IDS || "").split(",").filter(Boolean));
const states = [
  ["home-desktop", "/", 1440, 1000, "home"], ["home-mobile", "/", 390, 844, "home"],
  ["library-desktop", "/library", 1440, 1000, "library"], ["library-mobile", "/library", 390, 844, "library"],
  ["library-filter-mobile", "/library", 390, 844, "filter"], ["commerce-desktop", "/pricing", 1440, 1000, "commerce"],
  ["commerce-mobile", "/pricing", 390, 844, "commerce"], ["reading-pass-mobile", "/pricing", 390, 844, "commerce"],
  ["mobile-navigation", "/", 390, 844, "navigation"], ["book-detail-desktop", "/book/dracula", 1440, 1000, "book"],
  ["book-detail-mobile", "/book/dracula", 390, 844, "book"], ["reader-desktop", "/reader/dracula?visual-fixture=1", 1440, 1000, "reader"],
  ["reader-mobile", "/reader/dracula?visual-fixture=1", 390, 844, "reader"], ["listener-desktop", "/listener/a-ghost-story?visual-fixture=1", 1440, 1000, "listener"],
  ["listener-mobile", "/listener/a-ghost-story?visual-fixture=1", 390, 844, "listener"], ["about-mobile", "/about", 390, 844, "about"],
  ["my-library-mobile", "/my-library", 390, 844, "my-library"], ["profile-mobile", "/account?visual-fixture=1", 390, 844, "profile"],
].map(([id, route, width, height, family]) => ({ id, route, viewport: { width, height }, family })).filter((state) => !selectedStates.size || selectedStates.has(state.id));
const fullPageStates = new Set(["home-desktop", "home-mobile", "library-desktop", "library-mobile", "commerce-desktop", "commerce-mobile", "book-detail-desktop", "book-detail-mobile"]);

const sha = (buffer) => crypto.createHash("sha256").update(buffer).digest("hex");
const jsonResponse = (route, value) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(value) });
const requiredFor = (family) => ({
  home: ["[data-testid=home-reference-surface]", "header"], library: ["[data-testid=library-reference-surface]", "header"],
  filter: ["[data-testid=library-reference-surface]", ".reference-filter-trigger"], commerce: ["[data-testid=pricing-reference-surface]", "header"],
  navigation: ["header"], book: [".book-detail-page", "header"], reader: ["#reader-v2-title"], listener: ["#listener-v2-title"],
  about: ["#about-v2-title"], "my-library": ["[data-testid=my-library-mobile]", ".my-library-v2__empty"], profile: ["[data-testid=account-profile-mobile]"],
}[family] || ["main"]);

async function installFixtureRoutes(page) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/books")) return jsonResponse(route, books);
    if (url.pathname.includes("/payments/") && (url.pathname.endsWith("/offers") || url.pathname.endsWith("/packs"))) return jsonResponse(route, { packs, config: { mode: "owner-review-fixture", recurring_enabled: false } });
    if (url.pathname.endsWith("/auth/me") || url.pathname.endsWith("/users/me")) return jsonResponse(route, user);
    if (url.pathname.includes("transactions")) return jsonResponse(route, []);
    if (url.pathname.includes("devices")) return jsonResponse(route, []);
    if (url.pathname.includes("reading-pass")) return jsonResponse(route, { enabled: true, balance_seconds: user.reading_pass_seconds });
    return jsonResponse(route, {});
  });
}

async function capture(state, context, sessionFontLoad) {
  const page = await context.newPage();
  await page.setViewportSize(state.viewport);
  await page.emulateMedia({ colorScheme: state.family === "library" || state.family === "filter" ? "light" : "dark", reducedMotion: "reduce" });
  const errors = [];
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  const usesSanitizedIdentity = ["reader", "listener", "profile"].includes(state.family);
  await page.addInitScript(({ usesSanitizedIdentity: needsIdentity }) => {
    if (needsIdentity) localStorage.setItem("earnalism_user_token", "owner-review-fixture-token");
    else localStorage.removeItem("earnalism_user_token");
    const fixedNow = new Date("2026-08-29T00:00:00.000Z").valueOf(); Date.now = () => fixedNow;
  }, { usesSanitizedIdentity });
  await installFixtureRoutes(page);
  const response = await page.goto(`${baseUrl}${state.route}`, { waitUntil: "domcontentloaded", timeout: 90_000 });
  await page.evaluate(async () => {
    const settle = Promise.all([document.fonts.ready, ...[...document.images].map((image) => image.decode().catch(() => undefined))]);
    await Promise.race([settle, new Promise((resolve) => setTimeout(resolve, 10_000))]);
  });
  const fontLoad = sessionFontLoad.value || await page.evaluate(async () => {
    await Promise.all([
      document.fonts.load('500 48px "Cormorant Garamond"'),
      document.fonts.load('400 16px "Outfit"'),
      document.fonts.load('500 32px "Noto Serif Bengali"', 'বাংলা'),
      document.fonts.load('400 16px "Noto Sans Bengali"', 'বাংলা'),
    ]);
    return {
      cormorant: document.fonts.check('500 48px "Cormorant Garamond"'),
      outfit: document.fonts.check('400 16px "Outfit"'),
      notoSerifBengali: document.fonts.check('500 32px "Noto Serif Bengali"', 'বাংলা'),
      notoSansBengali: document.fonts.check('400 16px "Noto Sans Bengali"', 'বাংলা'),
    };
  });
  sessionFontLoad.value = fontLoad;
  if (state.family === "filter") {
    await page.locator(".reference-filter-trigger").click();
    await page.locator(".reference-library-drawer[role=dialog]").waitFor({ state: "visible", timeout: 10_000 });
  }
  if (state.family === "navigation") {
    try {
      await page.locator("[data-testid=mobile-menu-toggle]:visible").click();
      await page.locator("[data-testid=mobile-menu][role=dialog]:visible").waitFor({ state: "visible", timeout: 10_000 });
    } catch (error) {
      if (strict) throw error;
      errors.push(`navigation-overlay:${error.message}`);
    }
  }
  // React can insert a fixture cover after the initial document-image pass.
  // Decode that post-render image set before comparing review screenshots so
  // an immutable remote cover cannot create a false visual-stability failure.
  await page.evaluate(async () => {
    const settle = Promise.all([...document.images].map((image) => image.decode().catch(() => undefined)));
    await Promise.race([settle, new Promise((resolve) => setTimeout(resolve, 10_000))]);
  });
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await page.waitForTimeout(500);
  const first = await page.screenshot({ fullPage: false, animations: "disabled" });
  await page.waitForTimeout(500);
  const second = await page.screenshot({ fullPage: false, animations: "disabled" });
  const screenshot = path.join(output, `${state.id}.png`); fs.writeFileSync(screenshot, second);
  let fullPageScreenshot = null;
  if (fullPageStates.has(state.id)) {
    fullPageScreenshot = path.join(output, `${state.id}-full.png`);
    await page.screenshot({ path: fullPageScreenshot, fullPage: true, animations: "disabled" });
  }
  const selectors = requiredFor(state.family);
  const metrics = await page.evaluate((required) => ({
    scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth,
    required: required.map((selector) => Boolean(document.querySelector(selector))),
    h1: document.querySelector("h1")?.textContent?.trim() || "",
    geometry: required.map((selector) => { const node = document.querySelector(selector); if (!node) return { selector, present: false }; const r = node.getBoundingClientRect(); const s = getComputedStyle(node); return { selector, present: true, x: r.x, y: r.y, width: r.width, height: r.height, fontSize: s.fontSize, lineHeight: s.lineHeight }; }),
  }), selectors);
  await page.close();
  const fixture = state.family === "profile"
    ? "sanitized-owner-review-user"
    : ["reader", "listener"].includes(state.family)
      ? "server-contract-review-fixture"
      : "anonymous-public-shell";
  return { ...state, status: response?.status() || 0, errors, fontLoad, font_load_scope: "shared-pinned-browser-session", ...metrics, stable: sha(first) === sha(second), screenshot_sha256: sha(second), full_page_screenshot: fullPageScreenshot ? path.basename(fullPageScreenshot) : null, fixture, product_truth: "Read the first 3 pages free. Listening requires an active Reading Pass." };
}

fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const checkoutSha = process.env.ACTUAL_CHECKOUT_SHA || execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
const checkoutTreeSha = process.env.CHECKOUT_TREE_SHA || execFileSync("git", ["rev-parse", "HEAD^{tree}"], { encoding: "utf8" }).trim();
const captureScriptSha = sha(fs.readFileSync(new URL(import.meta.url)));
const context = await browser.newContext({ deviceScaleFactor: 1, colorScheme: "dark", reducedMotion: "reduce" });
const sessionFontLoad = { value: null };
try {
  const captures = [];
  for (const state of states) {
    const result = await capture(state, context, sessionFontLoad);
    captures.push(result);
    console.log(JSON.stringify({ state: state.id, status: result.status, stable: result.stable, errors: result.errors.length }));
  }
  const capturePath = path.join(output, "capture.json");
  const previous = process.env.EXACT_OWNER_REVIEW_APPEND_CAPTURE === "1" && fs.existsSync(capturePath) ? JSON.parse(fs.readFileSync(capturePath, "utf8")).states || [] : [];
  const all = [...previous.filter((item) => !captures.some((capture) => capture.id === item.id)), ...captures];
  fs.writeFileSync(capturePath, JSON.stringify({ schema_version: "earnalism-exact-primary-owner-review-v2", provenance: { pr_head_sha: process.env.PR_HEAD_SHA || null, actual_checkout_sha: checkoutSha, checkout_tree_sha: checkoutTreeSha, workflow_event_sha: process.env.WORKFLOW_EVENT_SHA || null, capture_script_sha256: captureScriptSha, browser_version: browser.version(), fixture_sha256: sha(Buffer.from(JSON.stringify({ books, packs, user }))), build_configuration: { visual_fixtures: process.env.REACT_APP_ENABLE_VISUAL_FIXTURES || null } }, states: all }, null, 2) + "\n");
  const failed = all.filter((item) => item.status !== 200 || item.errors.length || !item.stable || item.scrollWidth !== item.clientWidth || item.required.includes(false) || !Object.values(item.fontLoad || {}).every(Boolean));
  const failureReasons = failed.map((item) => ({
    id: item.id,
    status: item.status,
    overflow: item.scrollWidth !== item.clientWidth ? { scrollWidth: item.scrollWidth, clientWidth: item.clientWidth } : null,
    missing_required: item.geometry.filter((entry) => !entry.present).map((entry) => entry.selector),
    errors: item.errors,
    stable: item.stable,
    fontLoad: item.fontLoad,
  }));
  console.log(JSON.stringify({ captured: all.length, failed: failed.map((item) => item.id), failureReasons, strict, output }));
  if (strict && failed.length) process.exitCode = 1;
} finally { await browser.close(); }
