#!/usr/bin/env node
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const baseUrl = String(process.env.SEAMLESS_BRAND_TEST_BASE_URL || "").replace(/\/$/, "");

if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) {
  throw new Error("SEAMLESS_BRAND_TEST_BASE_URL must be an isolated loopback build.");
}

const posts = [
  {
    slug: "how-reading-shapes-better-founders",
    title: "How Reading Shapes Better Founders",
    excerpt: "The founders who endure make room for attention, context, and stories that clarify a decision.",
    author: "The Earnalism",
    category: "Self-Growth",
    created_at: "2026-05-10T00:00:00.000Z",
    content: "Reading creates a pause before action.\n\nThat pause makes room for better questions and more careful work.",
  },
  {
    slug: "why-every-small-business-needs-a-story-before-a-strategy",
    title: "Why Every Small Business Needs a Story Before a Strategy",
    excerpt: "Strategy works best when a clear story gives it shape.",
    author: "The Earnalism",
    category: "Business",
    created_at: "2026-05-09T00:00:00.000Z",
    content: "A story gives strategy a human scale.\n\nIt helps a reader understand what matters.",
  },
];

const viewports = [
  ["desktop", 1440, 1000],
  ["tablet", 768, 1024],
  ["mobile", 390, 844],
];

async function focusByTab(page, testId) {
  for (let index = 0; index < 80; index += 1) {
    await page.keyboard.press("Tab");
    const active = await page.evaluate(() => document.activeElement?.getAttribute("data-testid"));
    if (active === testId) return;
  }
  throw new Error(`Keyboard Tab did not reach ${testId}.`);
}

async function runJourney(browser, [name, width, height]) {
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, reducedMotion: "reduce" });
  await context.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/api/blog") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(posts) });
    const slug = pathname.replace("/api/blog/", "");
    const post = posts.find((item) => item.slug === slug);
    if (post) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(post) });
    if (pathname === "/api/books") return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "fixture route not found" }) });
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });

  await page.goto(`${baseUrl}/journal`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="journal-feature-read"]');
  assert.equal(await page.locator('[data-testid="journal-library-link"]').getAttribute("href"), "/library", `${name}: Journal discovery link drifted`);
  assert.equal(await page.locator('[data-testid="journal-feature-read"]').getAttribute("href"), `/journal/${posts[0].slug}`, `${name}: featured story route drifted`);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${name}: Journal has horizontal overflow`);

  await focusByTab(page, "journal-feature-read");
  await page.keyboard.press("Enter");
  await page.waitForURL(`${baseUrl}/journal/${posts[0].slug}`);
  await page.waitForSelector('[data-testid="article-library-cta"]');
  assert.equal(await page.locator('[data-testid="article-library-cta"]').getAttribute("href"), "/library", `${name}: article Library CTA drifted`);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${name}: article has horizontal overflow`);

  await focusByTab(page, "article-library-cta");
  await page.keyboard.press("Enter");
  await page.waitForURL(`${baseUrl}/library`);
  await page.goBack();
  await page.waitForURL(`${baseUrl}/journal/${posts[0].slug}`);
  await page.goBack();
  await page.waitForURL(`${baseUrl}/journal`);
  await page.waitForSelector('[data-testid="journal-feature"]');
  assert.equal(await page.locator('[data-testid="journal-feature"]').count(), 1, `${name}: browser Back did not restore the Journal`);
  await page.locator('[data-testid="journal-filter-business"]').click();
  assert.equal(await page.locator('[data-testid="journal-filter-business"]').getAttribute("aria-pressed"), "true", `${name}: category selection is not announced`);
  assert.equal(await page.locator('[data-testid="journal-feature"]').getByRole("heading").textContent(), posts[1].title, `${name}: category filter did not retain its matching article`);
  assert.deepEqual(errors, [], `${name}: browser errors occurred during the Journal journey`);
  await context.close();
}

const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of viewports) await runJourney(browser, viewport);
} finally {
  await browser.close();
}

console.log(JSON.stringify({ result: "PASS", journeys: viewports.map(([name]) => name), fixture_only: true }));
