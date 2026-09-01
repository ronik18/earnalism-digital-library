#!/usr/bin/env node
import assert from "node:assert/strict";
import { chromium, firefox, webkit } from "playwright";

const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for real-browser Library filter focus verification.");

const books = [
  { slug: "dracula", title: "Dracula", author: "Bram Stoker", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, chapters: [{ id: "p1", is_preview: true }] },
  { slug: "a-ghost-story", title: "A Ghost Story", author: "Mark Twain", publication_status: "LIVE_APPROVED", reader_enabled: true, audiobook_enabled: false, preview_enabled: true, chapters: [{ id: "p1", is_preview: true }] },
  { slug: "devdas", title: "দেবদাস / Devdas", author: "Sarat Chandra Chattopadhyay", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, audiobook_enabled: false, preview_enabled: true, chapters: [{ id: "devdas-canonical-page-1", is_preview: true }] },
];
const browserTypes = { chromium, firefox, webkit };
const settle = (page) => page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));

async function candidates(page) {
  return page.evaluate(() => {
    const drawer = document.querySelector('.reference-library-drawer[role="dialog"][aria-modal="true"]');
    const selector = "a[href], button:not([disabled]), input:not([disabled]):not([type='hidden']), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";
    const excluded = (node) => { for (let current = node; current; current = current.parentElement) { if (current.hasAttribute("inert") || current.getAttribute("aria-hidden") === "true") return true; } return false; };
    const rendered = (node) => { const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display !== "none" && style.visibility !== "hidden" && style.visibility !== "collapse" && node.getClientRects().length > 0 && rect.width > 0 && rect.height > 0; };
    const name = (node) => node.getAttribute("aria-label") || node.labels?.[0]?.innerText?.trim().replace(/\s+/g, " ") || node.innerText?.trim().replace(/\s+/g, " ") || node.textContent?.trim().replace(/\s+/g, " ") || "";
    return [...drawer.querySelectorAll(selector)].filter((node) => !excluded(node) && rendered(node)).map((node) => ({ tag: node.tagName, name: name(node) }));
  });
}

async function focusAt(page, index) {
  await page.evaluate((targetIndex) => {
    const drawer = document.querySelector('.reference-library-drawer[role="dialog"][aria-modal="true"]');
    const selector = "a[href], button:not([disabled]), input:not([disabled]):not([type='hidden']), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";
    const excluded = (node) => { for (let current = node; current; current = current.parentElement) { if (current.hasAttribute("inert") || current.getAttribute("aria-hidden") === "true") return true; } return false; };
    const rendered = (node) => { const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display !== "none" && style.visibility !== "hidden" && style.visibility !== "collapse" && node.getClientRects().length > 0 && rect.width > 0 && rect.height > 0; };
    [...drawer.querySelectorAll(selector)].filter((node) => !excluded(node) && rendered(node))[targetIndex]?.focus();
  }, index);
  await settle(page);
}

async function active(page) {
  return page.evaluate(() => {
    const drawer = document.querySelector('.reference-library-drawer[role="dialog"][aria-modal="true"]');
    const node = document.activeElement;
    return { inside: Boolean(drawer?.contains(node)), body: node === document.body, name: node?.getAttribute("aria-label") || node?.labels?.[0]?.innerText?.trim().replace(/\s+/g, " ") || node?.innerText?.trim().replace(/\s+/g, " ") || node?.textContent?.trim().replace(/\s+/g, " ") || "" };
  });
}

async function run(browserName, viewport) {
  const browser = await browserTypes[browserName].launch({ headless: true });
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", serviceWorkers: "block" });
  const page = await context.newPage();
  const consoleErrors = []; const pageErrors = []; const failedRequests = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push(request.url()));
  await page.route("**/api/**", (route) => {
    const requestUrl = new URL(route.request().url());
    const body = requestUrl.pathname.endsWith("/books") ? books : requestUrl.pathname.includes("auth") ? { id: "fixture", email: "fixture@invalid.example" } : [];
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.goto(`${baseUrl.replace(/\/$/, "")}/library`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.locator("button.reference-filter-trigger:visible").click();
  const drawer = page.locator('.reference-library-drawer[role="dialog"][aria-modal="true"]:visible');
  await drawer.waitFor(); await settle(page);
  const controls = await candidates(page);
  assert.ok(controls.length > 0, `${browserName} ${viewport.width}: no rendered drawer controls`);
  assert.ok(controls.some((control) => control.name === "Reset"), "Reset is absent");
  assert.ok(controls.some((control) => control.name === "Close filters"), "Close filters is absent");
  assert.ok(controls.some((control) => control.name === "Apply filters"), "Apply filters is absent");
  assert.ok(controls.filter((control) => control.tag === "SELECT").length >= 2, "Sort and Genre selects are absent");
  assert.ok(controls.filter((control) => control.tag === "BUTTON").length >= 10, "enabled filter choices are absent");
  assert.equal((await active(page)).inside, true, "initial focus leaves drawer");
  await focusAt(page, 0); await page.keyboard.press("Shift+Tab"); await settle(page); assert.equal((await active(page)).name, controls.at(-1).name, "first + Shift+Tab does not wrap to last");
  await focusAt(page, controls.length - 1); await page.keyboard.press("Tab"); await settle(page); assert.equal((await active(page)).name, controls[0].name, "last + Tab does not wrap to first");
  for (const key of ["Tab", "Shift+Tab"]) {
    await focusAt(page, key === "Tab" ? 0 : controls.length - 1);
    const seen = new Set();
    for (let index = 0; index < controls.length + 2; index += 1) { await page.keyboard.press(key); await settle(page); const state = await active(page); assert.ok(state.inside && !state.body, `${key} left the drawer`); seen.add(state.name); }
    assert.equal(seen.size, controls.length, `${key} did not reach every rendered control`);
  }
  const restoredState = () => page.evaluate(() => ({ focus: document.activeElement?.classList.contains("reference-filter-trigger"), overflow: document.body.style.overflow, headerInert: document.querySelector('[data-testid="site-header"]')?.hasAttribute("inert") ?? false, footerInert: document.querySelector("footer")?.hasAttribute("inert") ?? false, overflowed: document.documentElement.scrollWidth > document.documentElement.clientWidth }));
  await page.keyboard.press("Escape"); await drawer.waitFor({ state: "detached" }); await settle(page);
  const restored = await restoredState();
  assert.ok(restored.focus, "focus does not restore to Filters trigger"); assert.equal(restored.overflow, "", "body scroll does not restore"); assert.ok(!restored.headerInert && !restored.footerInert, "background inertness does not restore"); assert.ok(!restored.overflowed, "horizontal overflow detected");
  await page.locator("button.reference-filter-trigger:visible").click(); await drawer.waitFor();
  await drawer.getByRole("button", { name: "Close filters" }).click(); await drawer.waitFor({ state: "detached" }); await settle(page);
  assert.ok((await restoredState()).focus, "Close filters does not restore focus");
  await page.locator("button.reference-filter-trigger:visible").click(); await drawer.waitFor();
  await drawer.click({ position: { x: 1, y: 1 } }); await drawer.waitFor({ state: "detached" }); await settle(page);
  assert.ok((await restoredState()).focus, "drawer backdrop does not restore focus");
  assert.deepEqual([consoleErrors.length, pageErrors.length, failedRequests.length], [0, 0, 0], "runtime errors detected");
  await context.close(); await browser.close();
}

let cases = 0;
for (const browser of Object.keys(browserTypes)) {
  for (const viewport of [{ width: 390, height: 844 }, { width: 320, height: 568 }]) {
    await run(browser, viewport); cases += 1; console.log(`PASS ${cases}: ${browser} ${viewport.width}x${viewport.height}`);
  }
}
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
