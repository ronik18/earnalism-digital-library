#!/usr/bin/env node
/* Functional responsive evidence for the owner-review package. This uses the
 * same local, public-safe responses as the Chromium capture without recording
 * screenshots or touching any production service. */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { openActualMobileMenu, assertMobileMenuGeometry, closeActualMobileMenu } from "./capture_exact_primary_owner_review.mjs";

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require("playwright"); }
catch { playwright = require("../frontend/node_modules/playwright"); }
const { firefox, webkit } = playwright;

const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const browserName = process.env.EXACT_OWNER_REVIEW_BROWSER;
const output = path.resolve(process.env.EXACT_OWNER_REVIEW_BROWSER_OUTPUT || "uat/evidence/exact-primary-design/current/browser-results.json");
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("UAT_BASE_URL must be an explicit loopback URL.");
if (!{ firefox, webkit }[browserName]) throw new Error("EXACT_OWNER_REVIEW_BROWSER must be firefox or webkit.");

const books = [
  { slug: "dracula", title: "Dracula", author: "Bram Stoker", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/dracula", audiobook_enabled: false, category_slug: "english-classics", chapters: [{ id: "dracula-canonical-page-1", is_preview: true }] },
  { slug: "a-ghost-story", title: "A Ghost Story", author: "Mark Twain", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/a-ghost-story", audiobook_enabled: true, category_slug: "english-classics", chapters: [{ id: "a-ghost-story-canonical-page-1", is_preview: true }] },
];
const packs = [{ id: "30m", label: "The Opening Hour", minutes: 30, amount_paise: 4900, price_inr: 49 }];
const user = { id: "owner-review-fixture", name: "Review Reader", email: "review-fixture@invalid.example", reading_pass_seconds: 12900, reading_pass_enabled: true, transactions: [], devices: [] };
const states = [
  ["home-desktop", "/", 1440, 1000, "home"], ["home-mobile", "/", 390, 844, "home"],
  ["library-desktop", "/library", 1440, 1000, "library"], ["library-mobile", "/library", 390, 844, "library"],
  ["library-filter-mobile", "/library", 390, 844, "filter"], ["commerce-desktop", "/pricing", 1440, 1000, "commerce"],
  ["commerce-mobile", "/pricing", 390, 844, "commerce"], ["reading-pass-mobile", "/pricing", 390, 844, "commerce"],
  ["mobile-navigation", "/", 390, 844, "navigation"], ["mobile-navigation-320", "/", 320, 568, "navigation"], ["mobile-navigation-430", "/", 430, 932, "navigation"],
  ["mobile-navigation-768", "/", 768, 1024, "navigation"], ["mobile-navigation-1024", "/", 1024, 768, "navigation"], ["mobile-navigation-1279", "/", 1279, 800, "navigation"],
  ["book-detail-desktop", "/book/dracula", 1440, 1000, "book"],
  ["book-detail-mobile", "/book/dracula", 390, 844, "book"], ["reader-desktop", "/reader/dracula?visual-fixture=1", 1440, 1000, "reader"],
  ["reader-mobile", "/reader/dracula?visual-fixture=1", 390, 844, "reader"], ["listener-desktop", "/listener/a-ghost-story?visual-fixture=1", 1440, 1000, "listener"],
  ["listener-mobile", "/listener/a-ghost-story?visual-fixture=1", 390, 844, "listener"], ["about-mobile", "/about", 390, 844, "about"],
  ["my-library-mobile", "/my-library", 390, 844, "my-library"], ["profile-mobile", "/account?visual-fixture=1", 390, 844, "profile"],
].map(([id, route, width, height, family]) => ({ id, route, viewport: { width, height }, family }));
const requiredFor = (family) => ({ home: ["header"], library: ["[data-testid=library-reference-surface]"], filter: [".reference-library-drawer[role=dialog]"], commerce: ["[data-testid=pricing-reference-surface]"], navigation: ["header"], book: [".book-detail-page"], reader: ["#reader-v2-title"], listener: ["#listener-v2-title"], about: ["#about-v2-title"], "my-library": ["[data-testid=my-library-mobile]"], profile: ["[data-testid=account-profile-mobile]"], }[family] || ["main"]);
const sha = (value) => crypto.createHash("sha256").update(value).digest("hex");
const json = (route, body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

async function installLocalResponses(page) {
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname.endsWith("/books")) return json(route, books);
    if (pathname.includes("/books/")) return json(route, books.find((book) => pathname.endsWith(`/${book.slug}`)) || {});
    if (pathname.includes("payments/") && (pathname.endsWith("/offers") || pathname.endsWith("/packs"))) return json(route, { packs, config: { mode: "owner-review-fixture", recurring_enabled: false } });
    if (pathname.endsWith("/auth/me") || pathname.endsWith("/users/me")) return json(route, user);
    if (pathname.includes("transactions") || pathname.includes("devices")) return json(route, []);
    if (pathname.includes("reading-pass")) return json(route, { enabled: true, balance_seconds: user.reading_pass_seconds });
    return json(route, {});
  });
  await page.route("https://theearnalism.com/assets/brand/earnalism-brand-lockup.png", async (route) => {
    await route.fulfill({ status: 200, contentType: "image/png", body: fs.readFileSync(path.resolve("frontend/public/assets/brand/earnalism-brand-lockup.png")) });
  });
}

async function verify(state, context) {
  const page = await context.newPage();
  await page.setViewportSize(state.viewport);
  const usesSanitizedIdentity = ["reader", "listener", "profile"].includes(state.family);
  await page.addInitScript(({ needsIdentity }) => {
    if (needsIdentity) localStorage.setItem("earnalism_user_token", "owner-review-fixture-token");
    else localStorage.removeItem("earnalism_user_token");
  }, { needsIdentity: usesSanitizedIdentity });
  await installLocalResponses(page);
  const errors = [];
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  const response = await page.goto(`${baseUrl}${state.route}`, { waitUntil: "domcontentloaded", timeout: 90_000 });
  await page.evaluate(async () => {
    await Promise.race([Promise.all([
      document.fonts.ready,
      document.fonts.load('500 48px "Cormorant Garamond"'),
      document.fonts.load('400 16px "Outfit"'),
      document.fonts.load('500 32px "Noto Serif Bengali"', 'বাংলা'),
      document.fonts.load('400 16px "Noto Sans Bengali"', 'বাংলা'),
    ]), new Promise((resolve) => setTimeout(resolve, 10_000))]);
  });
  for (const selector of requiredFor(state.family).filter((selector) => !selector.includes("mobile-menu") && !selector.includes("reference-library-drawer"))) {
    await page.locator(selector).first().waitFor({ state: "attached", timeout: 10_000 });
  }
  if (state.family === "filter") { await page.locator(".reference-filter-trigger").click(); await page.locator(".reference-library-drawer[role=dialog]").waitFor({ state: "visible", timeout: 10_000 }); }
  let navigation = null;
  let navigationClose = null;
  if (state.family === "navigation") { navigation = await openActualMobileMenu(page); assertMobileMenuGeometry(navigation); navigationClose = await closeActualMobileMenu(page); }
  const result = await page.evaluate((required) => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    required: required.map((selector) => Boolean(document.querySelector(selector))),
    fonts: {
      cormorant: document.fonts.check('500 48px "Cormorant Garamond"'),
      outfit: document.fonts.check('400 16px "Outfit"'),
      notoSerifBengali: document.fonts.check('500 32px "Noto Serif Bengali"', 'বাংলা'),
      notoSansBengali: document.fonts.check('400 16px "Noto Sans Bengali"', 'বাংলা'),
    },
  }), requiredFor(state.family));
  await page.close();
  return { ...state, status: response?.status() || 0, errors, navigation, navigationClose, ...result, pass: response?.status() === 200 && !errors.length && result.scrollWidth === result.clientWidth && result.required.every(Boolean) && Object.values(result.fonts).every(Boolean), fixture: usesSanitizedIdentity ? "sanitized-fixture" : "anonymous-public-shell" };
}

const browser = await { firefox, webkit }[browserName].launch({ headless: true });
const context = await browser.newContext({ deviceScaleFactor: 1, colorScheme: "dark", reducedMotion: "reduce" });
try {
  const results = [];
  for (const state of states) results.push(await verify(state, context));
  const report = { schema_version: "pr341-cross-browser-v1", browser: browserName, browser_version: browser.version(), playwright_version: "1.60.0", fixture_sha256: sha(JSON.stringify({ books, packs, user })), states: results, failed: results.filter((result) => !result.pass).map((result) => result.id) };
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ browser: browserName, version: browser.version(), states: results.length, failed: report.failed }));
  if (report.failed.length) process.exitCode = 1;
} finally { await browser.close(); }
