#!/usr/bin/env node
import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the PR362 Header-to-Library journey.");

const books = [
  { slug: "devdas", title: "দেবদাস / Devdas", author: "Sarat Chandra Chattopadhyay", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, chapters: [{ id: "devdas-page-1", is_preview: true }] },
  { slug: "pather-panchali", title: "পথের পাঁচালী / Pather Panchali", author: "Bibhutibhushan Bandyopadhyay", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, chapters: [{ id: "pather-page-1", is_preview: true }] },
  { slug: "fixture-in-preparation", title: "Fixture Bengali In Preparation", author: "Fixture Editor", language: "bn", publication_status: "PIPELINE_ONLY", reader_enabled: false, preview_enabled: false, chapters: [] },
];
const expectedHeaderUrl = "?language=bn&availability=reader-ready";
const expectedAudioUrl = "?language=bn&listening=available";

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

async function assertEligibleReaderResults(page) {
  await page.getByTestId("reference-book-devdas").waitFor();
  assert.equal(await page.getByTestId("reference-book-devdas").count(), 1, "Devdas is not an eligible reader result");
  assert.equal(await page.getByTestId("reference-book-pather-panchali").count(), 1, "Pather Panchali is not an eligible reader result");
  assert.equal(await page.getByTestId("reference-book-fixture-in-preparation").count(), 0, "fixture in-preparation title leaked into Reader only results");
  assert.equal(await page.getByTestId("reference-book-kshudhita-pashan").count(), 0, "checked-in in-preparation title leaked into Reader only results");
}

async function configureApi(page) {
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const body = pathname.endsWith("/books") ? books : { hero: { featured_books: [] } };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
}

async function run({ name, viewport, mobile }) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", serviceWorkers: "block" });
  const page = await context.newPage();
  const base = baseUrl.replace(/\/$/, "");
  await configureApi(page);
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
  await assertEligibleReaderResults(page);

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
  await assertEligibleReaderResults(page);
  await context.close();
  await browser.close();
  return { viewport, header_url: expectedHeaderUrl, audio_url: expectedAudioUrl, result: "PASS" };
}

const results = [];
for (const scenario of [
  { name: "desktop", viewport: { width: 1440, height: 900 }, mobile: false },
  { name: "mobile", viewport: { width: 390, height: 844 }, mobile: true },
]) {
  results.push(await run(scenario));
  console.log(`PASS ${scenario.name} ${scenario.viewport.width}x${scenario.viewport.height}`);
}
console.log(JSON.stringify({ result: "PASS", testCaseCount: results.length, results }));
