#!/usr/bin/env node
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const baseUrl = String(process.env.SEAMLESS_BRAND_TEST_BASE_URL || "").replace(/\/$/, "");

if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) {
  throw new Error("SEAMLESS_BRAND_TEST_BASE_URL must be an isolated loopback build.");
}

const viewports = [
  ["desktop", 1440, 1000],
  ["tablet", 768, 1024],
  ["mobile-390", 390, 844],
  ["mobile-320", 320, 568],
];

async function focusByTab(page, testId) {
  for (let index = 0; index < 120; index += 1) {
    await page.keyboard.press("Tab");
    if (await page.evaluate(() => document.activeElement?.getAttribute("data-testid")) === testId) return;
  }
  throw new Error(`Keyboard Tab did not reach ${testId}.`);
}

async function assertMinimumControlSize(page, selector, label) {
  const bounds = await page.locator(selector).evaluateAll((elements) => elements.map((element) => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return { width: rect.width, height: rect.height, visible: style.display !== "none" && style.visibility !== "hidden" };
  }));
  assert.ok(bounds.length, `${label}: expected at least one control`);
  bounds.forEach((bound) => {
    assert.equal(bound.visible, true, `${label}: control is not visible`);
    assert.ok(bound.width >= 44, `${label}: width is below 44px (${bound.width}px)`);
    assert.ok(bound.height >= 44, `${label}: height is below 44px (${bound.height}px)`);
  });
}

async function runJourney(browser, [name, width, height]) {
  let contactRequests = 0;
  let contactMode = "failure";
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, reducedMotion: "reduce" });
  await context.route("**/api/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === "/api/settings") return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
    if (pathname === "/api/contact") {
      contactRequests += 1;
      return route.fulfill(contactMode === "failure"
        ? { status: 422, contentType: "application/json", body: JSON.stringify({ detail: "Please review your message and try again." }) }
        : { status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
    return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "fixture route not found" }) });
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error" && !/Failed to load resource/i.test(message.text())) errors.push(message.text());
  });

  await page.goto(`${baseUrl}/about`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="about-page"]');
  assert.equal(await page.locator('[data-testid="site-header"]').count(), 1, `${name}: About must retain the public Header`);
  assert.equal(await page.locator('[data-testid="site-footer"]').count(), 1, `${name}: About must retain the public Footer`);
  assert.equal(await page.locator('[data-testid="about-library-link"]').getAttribute("href"), "/library", `${name}: About Library destination drifted`);
  assert.equal(await page.locator('[data-testid="about-contact-link"]').getAttribute("href"), "/contact", `${name}: About contact destination drifted`);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${name}: About has horizontal overflow`);
  await assertMinimumControlSize(page, '[data-testid="about-library-link"], [data-testid="about-contact-link"]', `${name}: About CTA`);

  await focusByTab(page, "about-contact-link");
  await page.keyboard.press("Enter");
  await page.waitForURL(`${baseUrl}/contact`);
  await page.waitForSelector('[data-testid="contact-page"]');
  assert.equal(contactRequests, 0, `${name}: Contact made a request before submit`);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${name}: Contact has horizontal overflow`);
  await assertMinimumControlSize(page, '[data-testid^="contact-social-"], [data-testid="contact-submit"]', `${name}: Contact controls`);

  await page.goBack();
  await page.waitForURL(`${baseUrl}/about`);
  await page.waitForSelector('[data-testid="about-contact-link"]');

  await page.goto(`${baseUrl}/contact?interest=book-d19e96859f`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="contact-intent"]');
  assert.match(await page.locator('[data-testid="contact-subject"]').inputValue(), /Title inquiry: book-d19e96859f/, `${name}: title-interest context was not preserved`);
  await page.locator('[data-testid="contact-name"]').fill("Fixture Reader");
  await page.locator('[data-testid="contact-email-input"]').fill("fixture@example.invalid");
  await page.locator('[data-testid="contact-message"]').fill("Please tell me when this edition is ready.");
  await page.locator('[data-testid="contact-submit"]').click();
  await page.waitForSelector('[role="alert"]');
  assert.match(await page.locator('[role="alert"]').textContent(), /Please review your message/, `${name}: Contact failure is not visible`);

  contactMode = "success";
  await page.waitForFunction(() => !document.querySelector('[data-testid="contact-submit"]')?.disabled);
  await page.locator('[data-testid="contact-submit"]').click();
  await page.waitForFunction(() => document.querySelector('[role="status"]')?.textContent?.includes("Thank you. Your message has been received."));
  assert.match(await page.locator('[role="status"]').textContent(), /Thank you\. Your message has been received\./, `${name}: Contact success is not visible`);
  assert.equal(contactRequests, 2, `${name}: expected one failure and one success request`);
  assert.deepEqual(errors, [], `${name}: browser errors occurred during the support journey`);
  await context.close();
  return { name, contact_requests: contactRequests, fixture_only: true };
}

const browser = await chromium.launch({ headless: true });
try {
  const journeys = [];
  for (const viewport of viewports) journeys.push(await runJourney(browser, viewport));
  console.log(JSON.stringify({ result: "PASS", journeys, fixture_only: true }));
} finally {
  await browser.close();
}
