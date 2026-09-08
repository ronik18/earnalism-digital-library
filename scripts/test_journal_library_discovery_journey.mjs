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
  {
    slug: "the-quiet-work-of-a-bengali-classic",
    title: "The Quiet Work of a Bengali Classic",
    excerpt: "A lasting book rewards patient attention across generations.",
    author: "The Earnalism",
    category: "Bengali Classics",
    created_at: "2026-05-08T00:00:00.000Z",
    content: "A classic gives its reader another way to keep company with a question.",
  },
  {
    slug: "notes-on-literature-and-culture",
    title: "Notes on Literature and Culture",
    excerpt: "Literary attention makes room for a wider shared culture.",
    author: "The Earnalism",
    category: "Literature & Culture",
    created_at: "2026-05-07T00:00:00.000Z",
    content: "A library is a place to return to a conversation already in progress.",
  },
];

const viewports = [
  ["desktop", 1440, 1000],
  ["tablet", 768, 1024],
  ["mobile-390", 390, 844],
  ["mobile-320", 320, 568],
];

async function focusByTab(page, testId) {
  for (let index = 0; index < 80; index += 1) {
    await page.keyboard.press("Tab");
    const active = await page.evaluate(() => document.activeElement?.getAttribute("data-testid"));
    if (active === testId) return;
  }
  throw new Error(`Keyboard Tab did not reach ${testId}.`);
}

async function inspectCategoryControls(page, name, viewportWidth) {
  const controls = await page.locator('[data-testid="journal-filters"] button').evaluateAll((buttons) => buttons.map((button) => {
    const rect = button.getBoundingClientRect();
    const style = getComputedStyle(button);
    return {
      label: button.textContent?.trim(),
      width: rect.width,
      height: rect.height,
      left: rect.left,
      right: rect.right,
      top: rect.top,
      visible: style.display !== "none" && style.visibility !== "hidden",
    };
  }));

  assert.ok(controls.length >= 5, `${name}: fixture did not render every category control`);
  for (const control of controls) {
    assert.equal(control.visible, true, `${name}: ${control.label} is not visible`);
    assert.ok(control.width >= 44, `${name}: ${control.label} width is below 44px (${control.width}px)`);
    assert.ok(control.height >= 44, `${name}: ${control.label} height is below 44px (${control.height}px)`);
    assert.ok(control.left >= 0 && control.right <= viewportWidth, `${name}: ${control.label} overflows the viewport`);
  }
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${name}: category controls cause horizontal overflow`);

  const rows = new Set(controls.map((control) => Math.round(control.top)));
  if (viewportWidth <= 390) assert.ok(rows.size > 1, `${name}: category controls did not wrap at the narrow viewport`);
  return {
    category_button_count: controls.length,
    minimum_width: Math.min(...controls.map((control) => control.width)),
    minimum_height: Math.min(...controls.map((control) => control.height)),
    wrapped_rows: rows.size,
  };
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
  const categoryControls = await inspectCategoryControls(page, name, width);

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
  await focusByTab(page, "journal-filter-business");
  assert.equal(await page.evaluate(() => document.activeElement?.getAttribute("data-testid")), "journal-filter-business", `${name}: keyboard focus did not reach Business`);
  await page.keyboard.press("Enter");
  assert.equal(await page.locator('[data-testid="journal-filter-business"]').getAttribute("aria-pressed"), "true", `${name}: category selection is not announced`);
  assert.equal(await page.locator('[data-testid="journal-feature"]').getByRole("heading").textContent(), posts[1].title, `${name}: category filter did not retain its matching article`);
  assert.deepEqual(errors, [], `${name}: browser errors occurred during the Journal journey`);
  await context.close();
  return { name, ...categoryControls };
}

const browser = await chromium.launch({ headless: true });
try {
  const results = [];
  for (const viewport of viewports) results.push(await runJourney(browser, viewport));
  console.log(JSON.stringify({ result: "PASS", journeys: results, fixture_only: true }));
} finally {
  await browser.close();
}
