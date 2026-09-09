#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the Library recovery journey.");

const output = process.env.LIBRARY_RECOVERY_EVIDENCE_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), "earnalism-library-recovery-"));
fs.mkdirSync(output, { recursive: true });

const books = [
  { slug: "devdas", title: "দেবদাস / Devdas", author: "Sarat Chandra Chattopadhyay", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/devdas", chapters: [{ id: "devdas-page-1", is_preview: true }], audiobook_enabled: false },
  { slug: "pather-panchali", title: "পথের পাঁচালী / Pather Panchali", author: "Bibhutibhushan Bandyopadhyay", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/pather-panchali", chapters: [{ id: "pather-page-1", is_preview: true }], audiobook_enabled: false },
];

async function installCatalogueFixture(page, outcomes) {
  let requestCount = 0;
  let releasePendingFailure;
  const pendingFailure = new Promise((resolve) => { releasePendingFailure = resolve; });
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname.endsWith("/books")) {
      const outcome = outcomes[Math.min(requestCount, outcomes.length - 1)];
      requestCount += 1;
      if (outcome === "reject") return route.abort("failed");
      if (outcome === "malformed") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ books }) });
      if (outcome === "empty") return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
      if (outcome === "pending-failure") {
        await pendingFailure;
        return route.abort("failed");
      }
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(books) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ hero: { featured_books: [] }, literary_shelves: [] }) });
  });
  return { count: () => requestCount, releasePendingFailure };
}

async function openScenario(context, outcome, viewport) {
  const page = await context.newPage();
  await page.setViewportSize(viewport);
  const fixture = await installCatalogueFixture(page, [outcome]);
  await page.goto(`${baseUrl.replace(/\/$/, "")}/library?language=bn&availability=reader-ready&sort=title`, { waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  return { page, fixture };
}

async function assertFallback(page, label) {
  const notice = page.getByTestId("library-catalogue-fallback");
  await notice.waitFor();
  assert.equal((await notice.textContent()).replace(/\s+/g, " ").trim(), "We couldn’t load the full collection. You’re viewing a limited selection.Try again", `${label}: fallback message or recovery action changed`);
  assert.equal(await page.getByTestId("library-catalogue-retry").isEnabled(), true, `${label}: retry is not keyboard-operable`);
}

async function assertNoDocumentOverflow(page, label) {
  const geometry = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
  assert.equal(geometry.scrollWidth, geometry.clientWidth, `${label}: document has horizontal overflow`);
  return geometry;
}

async function waitForCatalogueState(page, state) {
  const fallback = page.getByTestId("library-catalogue-fallback");
  const empty = page.getByTestId("library-catalogue-empty");
  if (state === "success") {
    await page.getByTestId("reference-book-devdas").waitFor();
    await fallback.waitFor({ state: "detached" });
    await empty.waitFor({ state: "detached" });
    return;
  }
  if (state === "empty") {
    await empty.waitFor();
    await fallback.waitFor({ state: "detached" });
    return;
  }
  await fallback.waitFor();
  await page.getByTestId("library-catalogue-retry").waitFor({ state: "visible" });
}

async function focusRetryByTab(page, retry, label) {
  await page.evaluate(() => document.activeElement?.blur());
  for (let attempt = 0; attempt < 60; attempt += 1) {
    await page.keyboard.press("Tab");
    if (await retry.evaluate((node) => document.activeElement === node)) return attempt + 1;
  }
  throw new Error(`${label}: Tab traversal did not reach the retry action.`);
}

async function testInitialStates(context) {
  const cases = [
    ["success", "success", false, false],
    ["rejected", "reject", true, false],
    ["malformed", "malformed", true, false],
    ["empty", "empty", false, true],
  ];
  const results = [];
  for (const [id, outcome, expectsFallback, expectsEmpty] of cases) {
    const { page } = await openScenario(context, outcome, { width: 768, height: 1024 });
    await waitForCatalogueState(page, id === "success" ? "success" : expectsFallback ? "fallback" : "empty");
    if (expectsFallback) await assertFallback(page, id);
    else assert.equal(await page.getByTestId("library-catalogue-fallback").count(), 0, `${id}: fallback notice should not render`);
    assert.equal(await page.getByTestId("library-catalogue-empty").count(), expectsEmpty ? 1 : 0, `${id}: empty state classification changed`);
    if (id === "empty") {
      assert.equal(await page.getByTestId("reference-book-devdas").count(), 0, "empty: valid empty response was replaced with fallback reader inventory");
      assert.equal(await page.getByText("No reader-ready editions are currently available.", { exact: false }).count(), 1, "empty: valid empty response lacks a distinct explanation");
    }
    if (id === "success") await page.getByTestId("reference-book-devdas").waitFor();
    results.push({ id, geometry: await assertNoDocumentOverflow(page, id) });
    if (id === "rejected" || id === "malformed" || id === "empty") {
      await page.screenshot({ path: path.join(output, `library-${id}-768.png`), fullPage: true });
    }
    await page.close();
  }
  return results;
}

async function testKeyboardRetryAndRecovery(context, viewport) {
  const page = await context.newPage();
  await page.setViewportSize(viewport);
  const fixture = await installCatalogueFixture(page, ["reject", "pending-failure", "success"]);
  const initialUrl = "/library?language=bn&availability=reader-ready&sort=title";
  await page.goto(`${baseUrl.replace(/\/$/, "")}${initialUrl}`, { waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  await waitForCatalogueState(page, "fallback");
  await assertFallback(page, `${viewport.width}px initial`);

  const retry = page.getByTestId("library-catalogue-retry");
  const tabSteps = await focusRetryByTab(page, retry, `${viewport.width}px initial`);
  await page.keyboard.press("Enter");
  await page.getByTestId("library-catalogue-retry").waitFor();
  assert.equal(await retry.isDisabled(), true, `${viewport.width}px retry: pending retry is not disabled`);
  assert.equal(fixture.count(), 2, `${viewport.width}px retry: duplicate catalogue request started`);
  await retry.click({ force: true });
  assert.equal(fixture.count(), 2, `${viewport.width}px retry: repeated click started another catalogue request`);
  await page.screenshot({ path: path.join(output, `library-pending-retry-${viewport.width}.png`), fullPage: true });
  await page.locator("button.reference-filter-trigger:visible").click();
  const drawer = page.locator('.reference-library-drawer[role="dialog"]:visible');
  await drawer.getByRole("button", { name: "Bengali", exact: true }).click();
  await page.getByRole("button", { name: "Apply filters", exact: true }).click();
  assert.equal(new URL(page.url()).search, "?language=bn&availability=reader-ready&sort=title", `${viewport.width}px retry: filter state was not retained while retrying`);
  fixture.releasePendingFailure();
  await page.waitForFunction(() => document.querySelector('[data-testid="library-catalogue-retry"]')?.disabled === false);
  await waitForCatalogueState(page, "fallback");
  await assertFallback(page, `${viewport.width}px retry failure`);
  assert.equal(await retry.isEnabled(), true, `${viewport.width}px retry failure: recovery action stayed disabled`);

  const recoveryTabSteps = await focusRetryByTab(page, retry, `${viewport.width}px retry failure`);
  await page.keyboard.press("Enter");
  await waitForCatalogueState(page, "success");
  assert.equal(new URL(page.url()).search, "?language=bn&availability=reader-ready&sort=title", `${viewport.width}px recovery: URL state changed after success`);
  const geometry = await assertNoDocumentOverflow(page, `${viewport.width}px recovery`);
  await page.screenshot({ path: path.join(output, `library-recovery-${viewport.width}.png`), fullPage: true });
  await page.close();
  return { viewport, request_count: fixture.count(), keyboard_activation: { focus: "Tab traversal", key: "Enter", initial_tab_steps: tabSteps, recovery_tab_steps: recoveryTabSteps }, geometry, result: "PASS" };
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 768, height: 1024 }, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", serviceWorkers: "block" });
const initialStates = await testInitialStates(context);
const recovery = [];
for (const viewport of [{ width: 768, height: 1024 }, { width: 390, height: 844 }, { width: 320, height: 568 }]) {
  recovery.push(await testKeyboardRetryAndRecovery(context, viewport));
}
await context.close();
await browser.close();

const result = { result: "PASS", classification: "ISOLATED_UI_AND_INTERACTION_EVIDENCE_ONLY", output, initial_states: initialStates, recovery };
fs.writeFileSync(path.join(output, "summary.json"), `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify(result));
