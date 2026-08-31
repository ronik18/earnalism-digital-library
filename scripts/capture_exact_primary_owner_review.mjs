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
import { fileURLToPath } from "node:url";
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
  ["mobile-navigation", "/", 390, 844, "navigation"], ["mobile-navigation-320", "/", 320, 568, "navigation"], ["mobile-navigation-430", "/", 430, 932, "navigation"],
  ["mobile-navigation-768", "/", 768, 1024, "navigation"], ["mobile-navigation-1024", "/", 1024, 768, "navigation"], ["mobile-navigation-1279", "/", 1279, 800, "navigation"],
  ["book-detail-desktop", "/book/dracula", 1440, 1000, "book"],
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

const mobileMenuDiagnostics = () => {
  const visible = (node) => { const style = getComputedStyle(node); return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity || "1") > 0; };
  const toggle = window.__earnalismOwnerReviewToggle;
  const dialog = window.__earnalismOwnerReviewDialog;
  const header = toggle?.closest('header[data-testid="site-header"]');
  const box = (node) => {
    const rect = node?.getBoundingClientRect();
    return rect ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height, top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left } : null;
  };
  const styleSummary = (node) => {
    if (!node) return null;
    const style = getComputedStyle(node);
    return {
      tag: node.tagName.toLowerCase(), class: node.className || "", box: box(node), position: style.position, top: style.top, right: style.right, bottom: style.bottom, left: style.left,
      insetBlock: style.insetBlock, insetInline: style.insetInline, width: style.width, height: style.height, minHeight: style.minHeight, maxHeight: style.maxHeight,
      display: style.display, visibility: style.visibility, overflow: style.overflow, overflowY: style.overflowY, zIndex: style.zIndex,
      transform: style.transform, translate: style.translate, scale: style.scale, rotate: style.rotate, filter: style.filter, backdropFilter: style.backdropFilter,
      perspective: style.perspective, contain: style.contain, containerType: style.containerType, contentVisibility: style.contentVisibility,
      willChange: style.willChange, clipPath: style.clipPath, isolation: style.isolation,
      offsetParent: node.offsetParent ? { tag: node.offsetParent.tagName.toLowerCase(), class: node.offsetParent.className || "" } : null,
      clientHeight: node.clientHeight, scrollHeight: node.scrollHeight,
    };
  };
  const ancestors = [];
  for (let node = dialog?.parentElement; node; node = node.parentElement) ancestors.push(styleSummary(node));
  const visibleDialogCount = header ? [...header.children].filter((node) => node.matches?.('[data-testid="mobile-menu"][role="dialog"]') && visible(node)).length : 0;
  return {
    schema_version: "earnalism-mobile-menu-containing-block-v1",
    viewport: { innerHeight: window.innerHeight, innerWidth: window.innerWidth, documentClientHeight: document.documentElement.clientHeight, visualViewportHeight: window.visualViewport?.height || null },
    siteHeaderHeight: header ? getComputedStyle(header).getPropertyValue("--site-header-height").trim() : null,
    header: styleSummary(header), dialog: styleSummary(dialog), ancestors, visibleToggleCount: toggle ? 1 : 0, activeVisibleOwnerDialogCount: visibleDialogCount,
    toggleExpanded: toggle?.getAttribute("aria-expanded") || null, ariaControls: toggle?.getAttribute("aria-controls") || null,
    ariaModal: dialog?.getAttribute("aria-modal") || null, closeVisible: Boolean(dialog?.querySelector('button[aria-label="Close menu"]') && visible(dialog.querySelector('button[aria-label="Close menu"]'))),
    requiredRowsVisible: ["mobile-nav-home", "mobile-nav-library", "mobile-nav-reading-passes"].every((id) => { const row = dialog?.querySelector(`[data-testid="${id}"]`); return Boolean(row && visible(row)); }),
    bodyScrollLocked: document.body.style.overflow === "hidden",
    backgroundInert: [document.getElementById("main-content"), document.querySelector("footer")].filter(Boolean).every((node) => node.hasAttribute("inert") && node.getAttribute("aria-hidden") === "true"),
  };
};

/** Capture exactly one real mobile menu, never a page-wide fixture dialog. */
export async function openActualMobileMenu(page) {
  const selected = await page.evaluate(() => {
    const visible = (node) => { const style = getComputedStyle(node); return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity || "1") > 0; };
    const toggles = [...document.querySelectorAll('header[data-testid="site-header"] [data-testid="mobile-menu-toggle"]')]
      .filter((node) => visible(node) && node.getBoundingClientRect().width > 0 && node.getBoundingClientRect().height > 0);
    if (toggles.length !== 1) return { visibleToggleCount: toggles.length };
    const toggle = toggles[0];
    window.__earnalismOwnerReviewToggle = toggle;
    return { visibleToggleCount: 1, ariaExpandedBefore: toggle.getAttribute("aria-expanded"), ariaControls: toggle.getAttribute("aria-controls"), ownerHeaderFound: Boolean(toggle.closest('header[data-testid="site-header"]')) };
  });
  if (selected.visibleToggleCount !== 1) throw new Error(`Expected exactly one visible mobile-menu toggle; found ${selected.visibleToggleCount}.`);
  if (!selected.ownerHeaderFound || selected.ariaExpandedBefore !== "false" || !selected.ariaControls) throw new Error(`Invalid mobile-menu toggle contract: ${JSON.stringify(selected)}.`);
  const toggleHandle = await page.evaluateHandle(() => window.__earnalismOwnerReviewToggle);
  await toggleHandle.asElement().click();
  await page.waitForFunction(() => window.__earnalismOwnerReviewToggle?.getAttribute("aria-expanded") === "true");
  try {
    await page.waitForFunction(({ controls }) => {
      const visible = (node) => { const style = getComputedStyle(node); return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity || "1") > 0; };
      const toggle = window.__earnalismOwnerReviewToggle;
      const header = toggle?.closest('header[data-testid="site-header"]');
      if (!header) return false;
      const dialogs = [...header.children].filter((node) => node.matches?.('[data-testid="mobile-menu"][role="dialog"]') && node.id === controls && visible(node));
      if (dialogs.length !== 1) return false;
      window.__earnalismOwnerReviewDialog = dialogs[0];
      return true;
    }, { controls: selected.ariaControls }, { timeout: 10_000 });
  } catch (error) {
    const diagnostics = await page.evaluate(mobileMenuDiagnostics);
    throw new Error(`Owner-scoped active mobile-menu dialog selection failed: ${JSON.stringify(diagnostics)}. ${error.message}`);
  }
  return page.evaluate(mobileMenuDiagnostics);
}

export function assertMobileMenuGeometry(diagnostics) {
  const dialog = diagnostics.dialog?.box;
  const header = diagnostics.header?.box;
  const availableHeight = (diagnostics.viewport.visualViewportHeight || diagnostics.viewport.innerHeight) - header.bottom;
  const failures = [];
  if (diagnostics.visibleToggleCount !== 1 || diagnostics.activeVisibleOwnerDialogCount !== 1) failures.push("owner scope count");
  if (!dialog || !header || dialog.height <= 0) failures.push("non-zero dialog height");
  if (dialog && Math.abs(dialog.top - header.bottom) > 2) failures.push("dialog top");
  if (dialog && Math.abs(dialog.left) > 2) failures.push("dialog left");
  if (dialog && Math.abs(dialog.width - diagnostics.viewport.innerWidth) > 2) failures.push("dialog width");
  if (dialog && Math.abs(dialog.height - availableHeight) > 3) failures.push("dialog height");
  if (dialog && dialog.height < availableHeight * 0.95) failures.push("dialog coverage");
  if (diagnostics.ariaModal !== "true" || !diagnostics.closeVisible || !diagnostics.requiredRowsVisible || !diagnostics.bodyScrollLocked || !diagnostics.backgroundInert) failures.push("modal interaction contract");
  if (failures.length) throw new Error(`Mobile-menu geometry contract failed: ${failures.join(", ")}. ${JSON.stringify({ dialog, header, availableHeight, viewport: diagnostics.viewport })}`);
  return { availableHeight, pass: true };
}

export async function closeActualMobileMenu(page) {
  await page.keyboard.press("Escape");
  await page.waitForFunction(() => {
    const visible = (node) => { const style = getComputedStyle(node); return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity || "1") > 0; };
    const toggle = window.__earnalismOwnerReviewToggle;
    const dialog = window.__earnalismOwnerReviewDialog;
    const active = dialog && document.contains(dialog) && visible(dialog) ? 1 : 0;
    return toggle?.getAttribute("aria-expanded") === "false" && active === 0 && document.activeElement === toggle && document.body.style.overflow !== "hidden" && [document.getElementById("main-content"), document.querySelector("footer")].filter(Boolean).every((node) => !node.hasAttribute("inert") && node.getAttribute("aria-hidden") !== "true");
  }, undefined, { timeout: 10_000 });
  return page.evaluate(() => { const visible = (node) => { const style = getComputedStyle(node); return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity || "1") > 0; }; return { escapeClose: window.__earnalismOwnerReviewToggle?.getAttribute("aria-expanded") === "false", focusRestored: document.activeElement === window.__earnalismOwnerReviewToggle, activeVisibleDialogCount: window.__earnalismOwnerReviewDialog && document.contains(window.__earnalismOwnerReviewDialog) && visible(window.__earnalismOwnerReviewDialog) ? 1 : 0, bodyScrollRestored: document.body.style.overflow !== "hidden", backgroundRestored: [document.getElementById("main-content"), document.querySelector("footer")].filter(Boolean).every((node) => !node.hasAttribute("inert") && node.getAttribute("aria-hidden") !== "true") }; });
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
  let navigation = null;
  let navigationClose = null;
  if (state.family === "navigation") {
    try {
      navigation = await openActualMobileMenu(page);
      assertMobileMenuGeometry(navigation);
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
  if (navigation) navigationClose = await closeActualMobileMenu(page);
  await page.close();
  const fixture = state.family === "profile"
    ? "sanitized-owner-review-user"
    : ["reader", "listener"].includes(state.family)
      ? "server-contract-review-fixture"
      : "anonymous-public-shell";
  return { ...state, status: response?.status() || 0, errors, fontLoad, font_load_scope: "shared-pinned-browser-session", ...metrics, navigation, navigationClose, stable: sha(first) === sha(second), screenshot_sha256: sha(second), full_page_screenshot: fullPageScreenshot ? path.basename(fullPageScreenshot) : null, fixture, product_truth: "Read the first 3 pages free. Listening requires an active Reading Pass." };
}

export async function runCapture() {
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
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await runCapture();
