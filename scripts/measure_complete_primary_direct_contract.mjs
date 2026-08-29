#!/usr/bin/env node
/**
 * Pinned, routed direct-contract measurement for the remaining exact-primary
 * review states.  These assertions intentionally measure CSS pixels and
 * computed type/surface values; they are not component-presence substitutes.
 */
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const root = path.resolve(new URL("..", import.meta.url).pathname);
const requireFromRepository = createRequire(path.join(root, "package.json"));
const { chromium } = requireFromRepository("playwright");
const args = process.argv.slice(2);
const option = (name, fallback = "") => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] || fallback : fallback;
};
const baseUrl = option("--base-url", "http://127.0.0.1:3000").replace(/\/$/, "");
const output = option("--output");
const screenshots = option("--screenshots");
const requested = option("--state", "all").split(",").filter(Boolean);
const bookDetailFixture = JSON.parse(await fs.readFile(path.join(root, "backend/data/controlled_publications/dracula/public_book.json"), "utf8"));
const readerManifestFixture = JSON.parse(await fs.readFile(path.join(root, "backend/data/controlled_publications/dracula/reader_manifest.json"), "utf8"));

const range = (label, selector, property, min, max, category = "geometry", index = 0) => ({ label, selector, property, min, max, category, index });
const equal = (label, selector, property, expected, category = "geometry", index = 0) => ({ label, selector, property, expected, category, index });
const visible = (label, selector, category = "presence", count = 1) => ({ label, selector, property: "visibleCount", expected: count, category });
const font = (label, selector, family, minSize, maxSize, category = "typography") => ({ label, selector, property: "font", family, min: minSize, max: maxSize, category });

const states = {
  "reader-desktop": {
    path: "/reader/dracula?visual-fixture=1", viewport: { width: 1440, height: 1000 }, fixture: "DETERMINISTIC_READER_VISUAL_FIXTURE",
    assertions: [
      range("top bar height", ".experience-header", "height", 54, 56), range("top bar logo x", ".experience-header .earnalism-brand-lockup", "x", 21, 24), range("top bar logo width", ".experience-header .earnalism-brand-lockup", "width", 117, 120),
      range("reader layout x", ".reader-v2__layout", "x", 15, 17), range("reader layout y", ".reader-v2__layout", "y", 72, 74), range("reader layout width", ".reader-v2__layout", "width", 1407, 1409), equal("reader layout has three columns", ".reader-v2__layout", "gridColumns", 3),
      range("left rail width", ".reader-v2__rail", "width", 237, 239), range("left rail padding", ".reader-v2__rail", "paddingLeft", 11, 13, "spacing"), visible("contents rows", ".reader-v2__contents li", "presence", 4),
      range("central canvas x", ".reader-v2__canvas", "x", 269, 271), range("central canvas width", ".reader-v2__canvas", "width", 921, 923), range("central canvas padding", ".reader-v2__canvas", "paddingTop", 53, 55, "spacing"), range("central canvas radius", ".reader-v2__canvas", "borderRadius", 7, 9, "color-border-radius"),
      range("chapter heading x", ".reader-v2__chapter h1", "x", 324, 326), font("chapter display face", ".reader-v2__chapter h1", "Cormorant Garamond", 44, 46), range("chapter heading line height", ".reader-v2__chapter h1", "lineHeight", 46, 49, "typography"),
      range("toolbar width", ".reader-v2__toolbar", "width", 206, 208), range("castle illustration width", ".reader-v2__illustration", "width", 619, 621), range("castle illustration height", ".reader-v2__illustration", "height", 423, 425),
      range("body text width", ".reader-v2__body", "width", 517, 521), font("reader body face", ".reader-v2__body", "Cormorant Garamond", 15, 17), range("right context width", ".reader-v2__context", "width", 215, 217), range("continuation height", ".reader-v2__continuation", "height", 65, 67),
    ],
  },
  "reader-mobile": {
    path: "/reader/dracula?visual-fixture=1", viewport: { width: 390, height: 844 }, fixture: "DETERMINISTIC_READER_VISUAL_FIXTURE",
    assertions: [
      range("mobile reader top bar height", ".reader-v2__mobile-topbar", "height", 47, 49), range("mobile reader top bar width", ".reader-v2__mobile-topbar", "width", 389, 391), visible("back touch action", ".reader-v2__mobile-topbar button", "presence", 3),
      range("mobile canvas y", ".reader-v2__canvas", "y", 47, 49), range("mobile canvas padding", ".reader-v2__canvas", "paddingTop", 21, 23, "spacing"), range("mobile chapter x", ".reader-v2__chapter", "x", 15, 17), font("mobile chapter display face", ".reader-v2__chapter h1", "Cormorant Garamond", 30, 32), range("mobile chapter line height", ".reader-v2__chapter h1", "lineHeight", 31, 34, "typography"),
      range("mobile toolbar width", ".reader-v2__toolbar", "width", 357, 359), range("mobile toolbar height", ".reader-v2__toolbar", "height", 43, 45), range("mobile castle width", ".reader-v2__illustration", "width", 339, 341), range("mobile castle height", ".reader-v2__illustration", "height", 231, 234),
      range("mobile body width", ".reader-v2__body", "width", 357, 359), font("mobile reader body face", ".reader-v2__body", "Cormorant Garamond", 15, 17), range("mobile continuation width", ".reader-v2__continuation", "width", 389, 391), range("mobile continuation height", ".reader-v2__continuation", "height", 96, 99), visible("mobile continuation action", ".reader-v2__continuation button", "presence"),
      range("mobile action targets", ".reader-v2__mobile-actions button", "height", 43, 46, "spacing"),
    ],
  },
  "listener-desktop": {
    path: "/listener/a-ghost-story?visual-fixture=1", viewport: { width: 1440, height: 1000 }, fixture: "DETERMINISTIC_APPROVED_AUDIO_PREPLAYBACK_FIXTURE",
    assertions: [
      range("listener top bar height", ".experience-header", "height", 54, 56), range("listener logo x", ".experience-header .earnalism-brand-lockup", "x", 21, 24), range("listener layout x", ".listener-v2__layout", "x", 159, 161), range("listener layout y", ".listener-v2__layout", "y", 74, 76), range("listener layout width", ".listener-v2__layout", "width", 1119, 1121), equal("listener has main and side panels", ".listener-v2__layout", "gridColumns", 2),
      range("listener main width", ".listener-v2__main", "width", 851, 853), range("listener artwork width", ".listener-v2__art", "width", 171, 173), range("listener artwork height", ".listener-v2__art", "height", 257, 259), range("listener artwork radius", ".listener-v2__art", "borderRadius", 7, 9, "color-border-radius"),
      range("listener title x", ".listener-v2__copy h1", "x", 359, 361), font("listener title display face", ".listener-v2__copy h1", "Cormorant Garamond", 45, 47), range("listener title line height", ".listener-v2__copy h1", "lineHeight", 42, 45, "typography"),
      range("timeline width", ".listener-v2__timeline", "width", 851, 853), range("timeline height", ".listener-v2__timeline", "height", 40, 42), range("primary control width", ".listener-v2__play", "width", 59, 61), range("primary control height", ".listener-v2__play", "height", 59, 61), equal("primary control is circular", ".listener-v2__play", "borderRadius", 50, "color-border-radius"),
      range("seek controls gap", ".listener-v2__controls", "gap", 23, 25, "spacing"), range("utilities top", ".listener-v2__utilities", "y", 483, 485), visible("speed and sleep actions", ".listener-v2__utilities label, .listener-v2__utilities button", "presence", 3),
      range("up-next side panel width", ".listener-v2__side", "width", 243, 245), range("side panel gap", ".listener-v2__side", "gap", 13, 15, "spacing"), visible("up-next, listening-mode, and Reading Pass panels", ".listener-v2__side .experience-panel", "presence", 3),
    ],
  },
  "listener-mobile": {
    path: "/listener/a-ghost-story?visual-fixture=1", viewport: { width: 390, height: 844 }, fixture: "DETERMINISTIC_APPROVED_AUDIO_PREPLAYBACK_FIXTURE",
    assertions: [
      equal("generic desktop header is hidden", ".listener-v2 .experience-header", "display", "none"), range("mobile listener top width", ".listener-v2__mobile-top", "width", 357, 359), range("mobile listener top height", ".listener-v2__mobile-top", "height", 43, 45), visible("mobile listener actions", ".listener-v2__mobile-top button", "presence", 2),
      range("mobile listener main padding", ".listener-v2__main", "paddingTop", 61, 63, "spacing"), range("mobile listener artwork x", ".listener-v2__art", "x", 119, 121), range("mobile listener artwork width", ".listener-v2__art", "width", 149, 151), range("mobile listener artwork height", ".listener-v2__art", "height", 224, 226),
      font("mobile listener title face", ".listener-v2__copy h1", "Cormorant Garamond", 30, 32), range("mobile listener title y", ".listener-v2__copy h1", "y", 341, 344), range("mobile timeline x", ".listener-v2__timeline", "x", 27, 29), range("mobile timeline width", ".listener-v2__timeline", "width", 333, 335),
      range("mobile play control width", ".listener-v2__play", "width", 59, 61), range("mobile play control height", ".listener-v2__play", "height", 59, 61), range("mobile seek controls width", ".listener-v2__controls", "width", 195, 197),
      range("mobile utility target height", ".listener-v2__utilities", "height", 43, 45, "spacing"), visible("mobile speed and actions", ".listener-v2__utilities label, .listener-v2__utilities button", "presence", 3), range("listener bottom navigation height", ".listener-v2 .experience-bottom-nav", "height", 67, 69), equal("listener bottom nav has four columns", ".listener-v2 .experience-bottom-nav", "gridColumns", 4),
    ],
  },
  "book-detail-mobile": {
    path: "/book/dracula", viewport: { width: 390, height: 844 }, fixture: "CONTROLLED_PUBLIC_BOOK_DETAIL",
    assertions: [
      range("book detail mobile header height", "[data-testid=site-header]", "height", 55, 57), range("book detail mobile logo width", "[data-testid=brand-logo] img", "width", 155, 157),
      range("book detail return band height", ".book-detail-reference__return", "height", 61, 64), range("book detail return padding", ".book-detail-reference__return", "paddingLeft", 19, 21, "spacing"),
      equal("book detail mobile is a single column", ".book-detail-reference__hero", "gridColumns", 1), range("book detail mobile hero padding", ".book-detail-reference__hero", "paddingLeft", 19, 21, "spacing"), range("book detail mobile cover x", ".book-detail-cover-frame", "x", 107, 110), range("book detail mobile cover width", ".book-detail-cover-frame", "width", 171, 174), range("book detail mobile cover height", ".book-detail-cover-frame", "height", 229, 232), range("book detail mobile cover radius", ".book-detail-cover-frame", "borderRadius", 8, 10, "color-border-radius"),
      range("book detail mobile title x", ".book-detail-reference__hero h1", "x", 19, 21), font("book detail mobile title face", ".book-detail-reference__hero h1", "Cormorant Garamond", 42, 44), range("book detail mobile title line height", ".book-detail-reference__hero h1", "lineHeight", 39, 42, "typography"),
      range("book detail mobile status width", "[data-testid=book-detail-status]", "width", 349, 351), range("book detail mobile status height", "[data-testid=book-detail-status]", "height", 43, 45), visible("book detail truthful read action", "[data-testid=read-preview]"),
      range("book detail mobile tabs width", ".book-detail-reference__tabs", "width", 349, 351), range("book detail mobile tab height", ".book-detail-reference__tabs", "height", 40, 42), range("book detail truth panel width", "[data-testid=book-experience-truth]", "width", 349, 351), range("book detail truth panel radius", "[data-testid=book-experience-truth]", "borderRadius", 23, 25, "color-border-radius"),
    ],
  },
  "my-library-mobile": {
    path: "/my-library", viewport: { width: 390, height: 844 }, fixture: "TRUTHFUL_EMPTY_STATE_PRODUCTION_ROUTE",
    assertions: [
      range("my library header height", ".experience-header", "height", 54, 56), range("my library logo width", ".experience-header .earnalism-brand-lockup", "width", 106, 109), range("my library content width", ".my-library-v2__content", "width", 357, 359), range("my library content top padding", ".my-library-v2__content", "paddingTop", 35, 37, "spacing"),
      font("my library heading face", ".my-library-v2 h1", "Cormorant Garamond", 37, 39), range("my library heading line height", ".my-library-v2 h1", "lineHeight", 37, 39, "typography"), range("my library tabs width", ".my-library-v2__tabs", "width", 357, 359), equal("my library tabs columns", ".my-library-v2__tabs", "gridColumns", 2),
      range("my library tab target height", ".my-library-v2__tabs button", "height", 43, 45, "spacing"), visible("my library format tabs", ".my-library-v2__tabs button", "presence", 2), range("empty state top", ".my-library-v2__empty", "y", 315, 318), range("empty state width", ".my-library-v2__empty", "width", 357, 359), range("empty state padding", ".my-library-v2__empty", "paddingTop", 31, 33, "spacing"), range("empty state radius", ".my-library-v2__empty", "borderRadius", 8, 10, "color-border-radius"),
      font("empty-state title face", ".my-library-v2__empty h2", "Cormorant Garamond", 24, 26), range("empty-state copy measure", ".my-library-v2__empty p", "width", 263, 266), range("empty-state CTA height", ".my-library-v2__empty a", "height", 43, 45, "spacing"), range("my library bottom nav height", ".my-library-v2 .experience-bottom-nav", "height", 67, 69), equal("my library bottom nav columns", ".my-library-v2 .experience-bottom-nav", "gridColumns", 4), visible("truthful empty state action", ".my-library-v2__empty a"),
    ],
  },
  "profile-mobile": {
    path: "/account?visual-fixture=1", viewport: { width: 390, height: 844 }, fixture: "SANITIZED_DETERMINISTIC_PROFILE_FIXTURE",
    assertions: [
      range("profile site header height", "[data-testid=site-header]", "height", 54, 58), range("profile site logo width", "[data-testid=brand-logo] img", "width", 156, 172), range("profile shell width", ".account-profile-mobile", "width", 389, 391), range("profile identity height", ".account-profile-mobile__identity", "height", 222, 225), range("profile identity top padding", ".account-profile-mobile__identity", "paddingTop", 31, 33, "spacing"),
      range("profile avatar x", ".account-profile-mobile__avatar", "x", 160, 162), range("profile avatar width", ".account-profile-mobile__avatar", "width", 67, 69), range("profile avatar height", ".account-profile-mobile__avatar", "height", 67, 69), equal("profile avatar is circular", ".account-profile-mobile__avatar", "borderRadius", 50, "color-border-radius"),
      font("profile identity display face", ".account-profile-mobile__identity h1", "Cormorant Garamond", 31, 33), range("profile identity line height", ".account-profile-mobile__identity h1", "lineHeight", 31, 33, "typography"), range("profile action rail padding", ".account-profile-mobile__actions", "paddingLeft", 15, 17, "spacing"),
      range("profile row width", ".account-profile-mobile__row", "width", 357, 359), range("profile row minimum target", ".account-profile-mobile__row", "height", 65, 68, "spacing"), range("profile row radius", ".account-profile-mobile__row", "borderRadius", 8, 10, "color-border-radius"), visible("profile provides truthful action rows", ".account-profile-mobile__row", "presence", 5),
      font("profile row display face", ".account-profile-mobile__row b", "Cormorant Garamond", 15, 17), range("profile bottom nav height", ".account-profile-mobile .experience-bottom-nav", "height", 67, 69), equal("profile bottom nav columns", ".account-profile-mobile .experience-bottom-nav", "gridColumns", 4), visible("profile sign-out action", "[data-testid=account-profile-mobile-logout]"),
    ],
  },
};

const activeStates = requested.includes("all") ? Object.keys(states) : requested;
for (const id of activeStates) if (!states[id]) throw new Error(`Unknown --state ${id}`);
if (screenshots) await fs.mkdir(screenshots, { recursive: true });
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const results = [];
for (const id of activeStates) {
  const state = states[id];
  const context = await browser.newContext({ viewport: state.viewport, deviceScaleFactor: 1, locale: "en-IN", timezoneId: "Asia/Kolkata", reducedMotion: "reduce", serviceWorkers: "block" });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  if (id === "book-detail-mobile") {
    await page.route("**/api/books/dracula", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(bookDetailFixture) }));
    await page.route("**/api/reader/book/dracula/manifest?*", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(readerManifestFixture) }));
  }
  await page.goto(`${baseUrl}${state.path}`, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.addStyleTag({ content: "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}" });
  const fontReport = await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([
      document.fonts.load('500 48px "Cormorant Garamond"', "Jonathan Harker"),
      document.fonts.load('400 16px "Outfit"', "Earnalism"),
      document.fonts.load('500 32px "Noto Serif Bengali"', "বাংলা"),
      document.fonts.load('400 16px "Noto Sans Bengali"', "বাংলা"),
    ]);
    return {
      cormorant: document.fonts.check('500 48px "Cormorant Garamond"', "Jonathan Harker"),
      outfit: document.fonts.check('400 16px "Outfit"', "Earnalism"),
      notoSerifBengali: document.fonts.check('500 32px "Noto Serif Bengali"', "বাংলা"),
      notoSansBengali: document.fonts.check('400 16px "Noto Sans Bengali"', "বাংলা"),
    };
  });
  await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});
  await page.waitForTimeout(500);
  const one = await page.screenshot({ fullPage: true });
  await page.waitForTimeout(500);
  const two = await page.screenshot({ fullPage: true });
  const stability = { first_sha256: crypto.createHash("sha256").update(one).digest("hex"), second_sha256: crypto.createHash("sha256").update(two).digest("hex") };
  stability.pass = stability.first_sha256 === stability.second_sha256;
  if (screenshots) await fs.writeFile(path.join(screenshots, `${id}.png`), one);
  const measured = await page.evaluate((assertions) => {
    const isVisible = (element) => { const rect = element.getBoundingClientRect(); const style = getComputedStyle(element); return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden"; };
    const numeric = (value) => { const result = Number.parseFloat(value); return Number.isFinite(result) ? result : value; };
    const getValue = (element, property) => {
      const rect = element.getBoundingClientRect(); const style = getComputedStyle(element);
      if (property === "visibleCount") return null;
      if (property === "gridColumns") return style.gridTemplateColumns.split(" ").filter((value) => value && value !== "none").length;
      if (["x", "y", "width", "height", "top", "right", "bottom", "left"].includes(property)) return rect[property];
      return numeric(style[property]);
    };
    const results = assertions.map((item) => {
      const elements = item.property === "display" ? [...document.querySelectorAll(item.selector)] : [...document.querySelectorAll(item.selector)].filter(isVisible);
      if (item.property === "visibleCount") return { ...item, actual: elements.length, pass: elements.length === item.expected };
      const element = elements[item.index || 0];
      if (!element) return { ...item, actual: "missing", pass: false };
      if (item.property === "font") {
        const style = getComputedStyle(element);
        const size = numeric(style.fontSize);
        return { ...item, actual: { family: style.fontFamily, size }, pass: style.fontFamily.includes(item.family) && size >= item.min && size <= item.max };
      }
      const actual = getValue(element, item.property);
      return { ...item, actual, pass: Object.hasOwn(item, "expected") ? actual === item.expected : actual >= item.min && actual <= item.max };
    });
    const guarded = [...document.querySelectorAll(".experience-header,.reader-v2__canvas,.reader-v2__continuation,.listener-v2__main,.listener-v2__timeline,.listener-v2__controls,.my-library-v2__content,.account-profile-mobile")].filter(isVisible);
    const clipped = guarded.filter((element) => { const rect = element.getBoundingClientRect(); return rect.left < -0.5 || rect.right > innerWidth + 0.5; }).map((element) => element.className);
    results.push({ label: "horizontal overflow is zero", category: "geometry", actual: document.documentElement.scrollWidth - document.documentElement.clientWidth, expected: 0, pass: document.documentElement.scrollWidth === document.documentElement.clientWidth });
    results.push({ label: "guarded primary regions are not horizontally clipped", category: "geometry", actual: clipped, expected: [], pass: clipped.length === 0 });
    return results;
  }, state.assertions);
  measured.push({ label: "all four locked font checks pass", category: "typography", actual: fontReport, expected: true, pass: Object.values(fontReport).every(Boolean) });
  measured.push({ label: "capture is stable", category: "capture", actual: stability, expected: true, pass: stability.pass });
  measured.push({ label: "no console errors", category: "runtime", actual: consoleErrors, expected: [], pass: consoleErrors.length === 0 });
  measured.push({ label: "no page errors", category: "runtime", actual: pageErrors, expected: [], pass: pageErrors.length === 0 });
  const directPassed = measured.slice(0, state.assertions.length).filter((item) => item.pass).length;
  const passed = measured.filter((item) => item.pass).length;
  const quantitative = measured.filter((item) => ["geometry", "typography", "spacing", "color-border-radius"].includes(item.category)).length;
  results.push({ id, path: state.path, fixture: state.fixture, viewport: state.viewport, fontReport, stability, assertions: measured, direct_passed: directPassed, direct_total: state.assertions.length, passed, total: measured.length, quantitative_assertions: quantitative, quantitative_percent: Number((100 * quantitative / measured.length).toFixed(6)), score: Number((100 * passed / measured.length).toFixed(6)), consoleErrors, pageErrors });
  await context.close();
}
await browser.close();
const summary = { generated_at: new Date().toISOString(), base_url: baseUrl, environment: { playwright: requireFromRepository("playwright/package.json").version, deviceScaleFactor: 1, locale: "en-IN", timezone: "Asia/Kolkata", pixelmatch_threshold: 0.2 }, states: results, passed: results.reduce((sum, result) => sum + result.passed, 0), total: results.reduce((sum, result) => sum + result.total, 0) };
summary.score = Number((100 * summary.passed / summary.total).toFixed(6));
if (output) await fs.writeFile(output, `${JSON.stringify(summary, null, 2)}\n`);
process.stdout.write(`${JSON.stringify(summary)}\n`);
if (summary.passed !== summary.total) process.exitCode = 1;
