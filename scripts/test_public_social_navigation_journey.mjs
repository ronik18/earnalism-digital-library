#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const baseUrl = String(process.env.PUBLIC_SOCIAL_TEST_BASE_URL || "").replace(/\/$/, "");
const evidencePath = process.env.PUBLIC_SOCIAL_TEST_EVIDENCE_PATH || "";

if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) {
  throw new Error("PUBLIC_SOCIAL_TEST_BASE_URL must be an isolated loopback production build.");
}

const expected = {
  linkedin: "https://social.example.invalid/earnalism-linkedin",
  email: "mailto:reader@example.invalid",
  facebook: "https://social.example.invalid/earnalism-facebook",
  instagram: "https://social.example.invalid/earnalism-instagram",
  x: "https://social.example.invalid/earnalism-x",
  youtube: "https://social.example.invalid/earnalism-youtube",
};
const viewports = [["desktop", 1440, 1000], ["tablet", 768, 1024], ["mobile-390", 390, 844], ["mobile-320", 320, 568]];

async function focusByTab(page, testId) {
  for (let index = 0; index < 160; index += 1) {
    await page.keyboard.press("Tab");
    if (await page.evaluate(() => document.activeElement?.getAttribute("data-testid")) === testId) return;
  }
  throw new Error(`Keyboard Tab did not reach ${testId}.`);
}

async function assertVisibleControlBounds(page, selector, label) {
  const bounds = await page.locator(selector).evaluateAll((elements) => elements.map((element) => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return { width: rect.width, height: rect.height, visible: style.display !== "none" && style.visibility !== "hidden" };
  }));
  assert.ok(bounds.length, `${label}: no controls`);
  bounds.forEach((bound) => {
    assert.equal(bound.visible, true, `${label}: control is hidden`);
    assert.ok(bound.width >= 44, `${label}: width below 44 CSS px (${bound.width})`);
    assert.ok(bound.height >= 44, `${label}: height below 44 CSS px (${bound.height})`);
  });
}

async function verifyLinkSet(page, prefix, label) {
  for (const [id, href] of Object.entries(expected)) {
    const locator = page.getByTestId(`${prefix}-${id}`);
    await locator.scrollIntoViewIfNeeded();
    assert.equal(await locator.getAttribute("href"), href, `${label}: ${id} destination drifted`);
    if (id === "email") {
      assert.equal(await locator.getAttribute("target"), null, `${label}: mailto must remain in the current context`);
    } else {
      assert.equal(await locator.getAttribute("target"), "_blank", `${label}: external ${id} must open separately`);
      assert.equal(await locator.getAttribute("rel"), "noopener noreferrer", `${label}: external ${id} missing safe rel`);
    }
  }
}

async function runJourney(browser, [name, width, height]) {
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, reducedMotion: "reduce" });
  await context.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/api/settings/public") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ social: expected, brand: {} }) });
    return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="home-socials"]');
  await page.waitForTimeout(4800);
  assert.equal(await page.locator('[data-testid="home-socials"]').evaluate((element) => {
    const style = getComputedStyle(element);
    return style.display !== "none" && style.visibility !== "hidden" && !element.closest('[aria-hidden="true"]');
  }), true, `${name}: Home social navigation is not publicly visible`);
  await verifyLinkSet(page, "home-social", `${name}: Home`);
  await assertVisibleControlBounds(page, '[data-testid^="home-social-"]', `${name}: Home social`);
  await page.locator('[data-testid="site-footer"]').scrollIntoViewIfNeeded();
  await page.waitForSelector('[data-testid="footer-socials"]');
  await verifyLinkSet(page, "footer-social", `${name}: Footer`);
  await assertVisibleControlBounds(page, '[data-testid^="footer-social-"]', `${name}: Footer social`);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${name}: public page has horizontal overflow`);
  if (width < 1280) {
    const toggle = page.getByTestId("mobile-menu-toggle");
    await toggle.click();
    await page.waitForSelector('[data-testid="mobile-menu"]');
    assert.equal(await page.locator("#main-content").getAttribute("inert"), "", `${name}: main must become inert while menu is open`);
    assert.equal(await page.locator('[data-testid="site-footer"]').getAttribute("inert"), "", `${name}: footer must become inert while menu is open`);
    await verifyLinkSet(page, "mobile-social", `${name}: mobile menu`);
    await assertVisibleControlBounds(page, '[data-testid^="mobile-social-"]', `${name}: mobile social`);
    await focusByTab(page, "mobile-social-email");
    assert.equal(await page.evaluate(() => document.activeElement?.getAttribute("data-testid")), "mobile-social-email", `${name}: mobile email target is not keyboard reachable`);
    await page.keyboard.press("Escape");
    assert.equal(await page.locator('[data-testid="mobile-menu"]').count(), 0, `${name}: Escape did not close the modal menu`);
    assert.equal(await page.locator("#main-content").getAttribute("inert"), null, `${name}: main remained inert after close`);
    await page.waitForFunction(() => document.activeElement?.getAttribute("data-testid") === "mobile-menu-toggle");
    assert.equal(await page.evaluate(() => document.activeElement?.getAttribute("data-testid")), "mobile-menu-toggle", `${name}: focus did not return to menu control`);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${name}: menu close caused horizontal overflow`);
  }
  await page.goto(`${baseUrl}/contact`, { waitUntil: "networkidle" });
  await page.waitForFunction((href) => document.querySelector('[data-testid="contact-social-linkedin"]')?.getAttribute("href") === href, expected.linkedin);
  assert.match(await page.getByTestId("contact-email-link").getAttribute("href"), /^mailto:/, `${name}: Contact email must remain mailto`);
  await verifyLinkSet(page, "contact-social", `${name}: Contact`);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${name}: Contact has horizontal overflow`);
  assert.deepEqual(errors, [], `${name}: page errors: ${errors.join(" | ")}`);
  await context.close();
  return { viewport: { width, height }, mobileMenuTested: width < 1280 };
}

const browser = await chromium.launch({ headless: true });
try {
  const journeys = [];
  for (const viewport of viewports) journeys.push(await runJourney(browser, viewport));
  const summary = { result: "PASS", fixture: "isolated-configured-socials", journeys };
  if (evidencePath) fs.writeFileSync(evidencePath, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(summary));
} catch (error) {
  if (evidencePath) fs.writeFileSync(evidencePath, `${JSON.stringify({ result: "FAIL", error: error.message }, null, 2)}\n`, "utf8");
  throw error;
} finally {
  await browser.close();
}
