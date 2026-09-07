#!/usr/bin/env node
import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the PR362 Header-to-Library journey.");

const books = [
  { slug: "devdas", title: "দেবদাস / Devdas", author: "Sarat Chandra Chattopadhyay", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/devdas", chapters: [{ id: "devdas-page-1", is_preview: true }] },
  { slug: "pather-panchali", title: "পথের পাঁচালী / Pather Panchali", author: "Bibhutibhushan Bandyopadhyay", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/pather-panchali", chapters: [{ id: "pather-page-1", is_preview: true }] },
  { slug: "frankenstein", title: "Batch-listed Bengali draft", author: "Fixture Editor", language: "bn", publication_status: "DRAFT", reader_enabled: false, preview_enabled: false, chapters: [] },
  { slug: "reader-disabled-edition", title: "Reader-disabled Bengali edition", author: "Fixture Editor", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: false, preview_enabled: false, chapters: [] },
  { slug: "book-d19e96859f", title: "Live-labelled Bengali edition without a preview", author: "Fixture Editor", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: false, preview_url: "", chapters: [{ id: "chapter-001", is_preview: false }] },
  { slug: "book-f5d593e1f4", title: "Second live-labelled Bengali edition without a preview", author: "Fixture Editor", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: false, preview_url: "", chapters: [{ id: "chapter-001", is_preview: false }] },
];
const expectedHeaderUrl = "?language=bn&availability=reader-ready";
const expectedAudioUrl = "?language=bn&listening=available";
const apiEligibleSlugs = ["devdas", "pather-panchali"];
const fallbackEligibleSlugs = ["devdas", "pather-panchali"];
const ineligibleSlugs = ["frankenstein", "reader-disabled-edition", "book-d19e96859f", "book-f5d593e1f4"];
const productionShapedPreparationSlugs = ["book-d19e96859f", "book-f5d593e1f4"];

function query(page) {
  return new URL(page.url()).search;
}

async function selectedControls(page, mobile) {
  const surface = mobile
    ? page.locator('.reference-library-drawer[role="dialog"]:visible')
    : page.locator("aside.reference-library__sidebar:visible");
  const groups = surface.locator("fieldset");
  const language = groups.nth(0).getByRole("button", { name: "Bengali", exact: true });
  const status = groups.nth(2).getByRole("button", { name: "Reader only", exact: true });
  await assertSelected(language, "Bengali");
  await assertSelected(status, "Reader only");
}

async function assertSelected(locator, label) {
  await locator.waitFor();
  assert.equal(await locator.getAttribute("aria-pressed"), "true", `${label} is not selected`);
}

async function assertEligibleReaderResults(page, expectedSlugs) {
  await page.getByTestId("reference-book-devdas").waitFor();
  const displayedSlugs = await page.locator('[data-testid^="reference-book-"]').evaluateAll((nodes) => (
    nodes.map((node) => node.getAttribute("data-testid").replace("reference-book-", "")).sort()
  ));
  assert.deepEqual(displayedSlugs, [...expectedSlugs].sort(), "every displayed Reader-only result must satisfy the canonical release predicate");
  for (const slug of ineligibleSlugs) {
    assert.equal(await page.getByTestId(`reference-book-${slug}`).count(), 0, `${slug} leaked into Reader only results`);
  }
}

async function assertProductionShapedPreparationCards(context, base) {
  const page = await context.newPage();
  await configureApi(page, "api");
  await page.goto(`${base}/library?language=bn`, { waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  for (const slug of productionShapedPreparationSlugs) {
    const card = page.getByTestId(`reference-book-${slug}`);
    await card.waitFor();
    await expectText(card.locator(".reference-book-tile__status"), "Coming soon", `${slug} must retain its truthful visible status`);
    const cta = card.getByRole("link", { name: "Notify me", exact: true });
    await cta.waitFor();
    assert.equal(await cta.getAttribute("href"), `/contact?interest=${slug}`, `${slug} must retain its notification destination`);
  }
  await page.close();
}

async function expectText(locator, expected, message) {
  assert.equal((await locator.textContent()).trim(), expected, message);
}

async function configureApi(page, source) {
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname.endsWith("/books") && source === "fallback") {
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "isolated catalogue failure" }) });
      return;
    }
    const body = pathname.endsWith("/books") ? books : { hero: { featured_books: [] } };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
}

async function inspectResponsiveState(page, viewport, expectedSlugs) {
  await page.setViewportSize(viewport);
  const compact = viewport.width <= 1023;
  if (compact) {
    await page.locator("button.reference-filter-trigger:visible").click();
    await selectedControls(page, true);
  } else {
    await selectedControls(page, false);
  }
  await assertEligibleReaderResults(page, expectedSlugs);
  if (compact) await page.getByRole("button", { name: "Close filters", exact: true }).click();
}

async function run({ name, viewport, mobile, source, resize = [] }) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", serviceWorkers: "block" });
  const page = await context.newPage();
  const base = baseUrl.replace(/\/$/, "");
  await configureApi(page, source);
  await page.goto(`${base}/`, { waitUntil: "domcontentloaded" });

  const headerLink = mobile
    ? page.getByTestId("mobile-nav-bengali-classics")
    : page.getByTestId("nav-bengali-classics");
  if (mobile) await page.getByTestId("mobile-menu-toggle").click();
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.search === expectedHeaderUrl),
    headerLink.click(),
  ]);
  await page.getByTestId("library-reference-surface").waitFor();

  if (mobile) {
    await page.locator("button.reference-filter-trigger:visible").click();
    await selectedControls(page, true);
  } else {
    await selectedControls(page, false);
  }
  assert.equal(query(page), expectedHeaderUrl, `${name}: Header navigation did not preserve the established query contract`);
  const expectedSlugs = source === "fallback" ? fallbackEligibleSlugs : apiEligibleSlugs;
  await assertEligibleReaderResults(page, expectedSlugs);
  if (source === "api") await assertProductionShapedPreparationCards(context, base);

  const statusGroup = mobile
    ? page.locator('.reference-library-drawer[role="dialog"]:visible fieldset').nth(2)
    : page.locator("aside.reference-library__sidebar:visible fieldset").nth(2);
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.search === expectedAudioUrl),
    statusGroup.getByRole("button", { name: "Audiobooks", exact: true }).click(),
  ]);
  if (mobile) await page.getByRole("button", { name: "Apply filters", exact: true }).click();
  assert.equal(query(page), expectedAudioUrl, `${name}: filter change did not replace deprecated availability state`);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  assert.equal(query(page), expectedAudioUrl, `${name}: reload did not preserve selected filter URL state`);

  await page.goBack({ waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  assert.equal(query(page), expectedHeaderUrl, `${name}: browser Back did not restore Header-selected URL state`);
  if (mobile) {
    await page.locator("button.reference-filter-trigger:visible").click();
    await selectedControls(page, true);
  } else {
    await selectedControls(page, false);
  }
  await assertEligibleReaderResults(page, expectedSlugs);
  for (const responsiveViewport of resize) await inspectResponsiveState(page, responsiveViewport, expectedSlugs);
  await context.close();
  await browser.close();
  return { viewport, source, resized_to: resize, header_url: expectedHeaderUrl, audio_url: expectedAudioUrl, result: "PASS" };
}

const results = [];
for (const scenario of [
  { name: "desktop-api", viewport: { width: 1440, height: 900 }, mobile: false, source: "api", resize: [{ width: 768, height: 1024 }, { width: 390, height: 844 }] },
  { name: "mobile-api", viewport: { width: 390, height: 844 }, mobile: true, source: "api" },
  { name: "desktop-fallback", viewport: { width: 1440, height: 900 }, mobile: false, source: "fallback", resize: [{ width: 768, height: 1024 }, { width: 390, height: 844 }] },
  { name: "mobile-fallback", viewport: { width: 390, height: 844 }, mobile: true, source: "fallback" },
]) {
  results.push(await run(scenario));
  console.log(`PASS ${scenario.name} ${scenario.viewport.width}x${scenario.viewport.height}`);
}
console.log(JSON.stringify({ result: "PASS", testCaseCount: results.length, results }));
