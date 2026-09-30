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
  { slug: "a-ghost-story", title: "A Ghost Story", title_en: "A Ghost Story", author: "Mark Twain", language: "en", publication_status: "LIVE_APPROVED", reader_enabled: true, public_route: "/book/a-ghost-story", reader_url: "/reader/a-ghost-story", preview_enabled: false, preview_url: "", chapters: [{ id: "ghost-story-page-1", is_preview: true }], audiobook_enabled: false, audio_enabled: false, audiobook_assets: {} },
];

function collectDiagnostics(page) {
  const consoleErrors = [];
  const requestErrors = [];
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error" && !/Failed to load resource/i.test(message.text())) consoleErrors.push(message.text());
  });
  page.on("requestfailed", (request) => {
    if (new URL(request.url()).pathname.endsWith("/books")) return; // Controlled API failures exercise the error/retry state.
    requestErrors.push({ url: request.url(), error: request.failure()?.errorText || "unknown" });
  });
  return { consoleErrors, requestErrors };
}

function assertNoRuntimeDefects(diagnostics, label) {
  assert.deepEqual(diagnostics.consoleErrors, [], `${label}: console/runtime errors`);
  assert.deepEqual(diagnostics.requestErrors, [], `${label}: unexpected failed requests`);
}

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
  const diagnostics = collectDiagnostics(page);
  const officialBrandAsset = fs.readFileSync(path.resolve("frontend/public/assets/brand/earnalism-brand-lockup.png"));
  await page.route("**/assets/brand/earnalism-brand-lockup.png", (route) => route.fulfill({ status: 200, contentType: "image/png", body: officialBrandAsset }));
  await page.setViewportSize(viewport);
  const fixture = await installCatalogueFixture(page, [outcome]);
  await page.goto(`${baseUrl.replace(/\/$/, "")}/library?language=en&availability=reader-ready&sort=title`, { waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  return { page, fixture, diagnostics };
}

async function assertError(page, label) {
  const notice = page.getByTestId("library-catalogue-error");
  await notice.waitFor();
  assert.equal((await notice.textContent()).replace(/\s+/g, " ").trim(), "We couldn’t load the Library just now. Your search and filters are unchanged.Try again", `${label}: error message or recovery action changed`);
  assert.equal(await page.getByTestId("library-catalogue-retry").isEnabled(), true, `${label}: retry is not keyboard-operable`);
  assert.equal(await page.getByTestId("library-catalogue-fallback").count(), 0, `${label}: API error was mislabeled as curated fallback content`);
}

async function assertNoDocumentOverflow(page, label) {
  const geometry = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
  assert.equal(geometry.scrollWidth, geometry.clientWidth, `${label}: document has horizontal overflow`);
  return geometry;
}

async function captureFullPageAtTop(page, target) {
  await page.evaluate(() => { window.scrollTo(0, 0); return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))); });
  await page.screenshot({ path: target, fullPage: true, animations: "disabled" });
}

async function waitForCatalogueState(page, state) {
  const error = page.getByTestId("library-catalogue-error");
  const empty = page.getByTestId("library-catalogue-empty");
  if (state === "success") {
    const liveTile = page.getByTestId("reference-book-a-ghost-story");
    await liveTile.waitFor();
    await liveTile.getByText("Live", { exact: true }).waitFor();
    await liveTile.getByRole("link", { name: "Details", exact: true }).waitFor();
    await error.waitFor({ state: "detached" });
    await empty.waitFor({ state: "detached" });
    return;
  }
  if (state === "empty") {
    await empty.waitFor();
    await error.waitFor({ state: "detached" });
    return;
  }
  await error.waitFor();
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
  for (const [id, outcome, expectsError, expectsEmpty] of cases) {
    const { page, diagnostics } = await openScenario(context, outcome, { width: 1024, height: 768 });
    await waitForCatalogueState(page, id === "success" ? "success" : expectsError ? "error" : "empty");
    if (expectsError) await assertError(page, id);
    else assert.equal(await page.getByTestId("library-catalogue-error").count(), 0, `${id}: error notice should not render`);
    assert.equal(await page.getByTestId("library-catalogue-empty").count(), expectsEmpty ? 1 : 0, `${id}: empty state classification changed`);
    if (id === "empty") {
      assert.equal(await page.getByTestId("reference-book-a-ghost-story").count(), 0, "empty: valid empty response was replaced with fallback reader inventory");
      assert.equal(await page.getByText("The shelves are quiet for now.", { exact: true }).count(), 1, "empty: valid empty response lacks a distinct explanation");
    }
    if (id === "success") {
      const liveTile = page.getByTestId("reference-book-a-ghost-story");
      await liveTile.waitFor();
      await liveTile.getByText("Live", { exact: true }).waitFor();
      await liveTile.getByRole("link", { name: "Details", exact: true }).waitFor();
    }
    results.push({ id, geometry: await assertNoDocumentOverflow(page, id) });
    assertNoRuntimeDefects(diagnostics, id);
    if (["success", "rejected", "malformed", "empty"].includes(id)) {
      await captureFullPageAtTop(page, path.join(output, `library-${id === "rejected" ? "error" : id}-1024.png`));
    }
    await page.close();
  }
  return results;
}

async function testLoadingAndNoResults(context) {
  const loading = await context.newPage();
  const loadingDiagnostics = collectDiagnostics(loading);
  const officialBrandAsset = fs.readFileSync(path.resolve("frontend/public/assets/brand/earnalism-brand-lockup.png"));
  await loading.route("**/assets/brand/earnalism-brand-lockup.png", (route) => route.fulfill({ status: 200, contentType: "image/png", body: officialBrandAsset }));
  await loading.setViewportSize({ width: 1440, height: 900 });
  const pending = await installCatalogueFixture(loading, ["pending-failure"]);
  await loading.goto(`${baseUrl.replace(/\/$/, "")}/library?language=en&availability=reader-ready&sort=title`, { waitUntil: "domcontentloaded" });
  await loading.getByText("Finding your next read…", { exact: true }).waitFor();
  await captureFullPageAtTop(loading, path.join(output, "library-loading-1440.png"));
  pending.releasePendingFailure();
  await waitForCatalogueState(loading, "error");
  await assertError(loading, "1440px loading completion");
  const loadingGeometry = await assertNoDocumentOverflow(loading, "1440px error");
  assertNoRuntimeDefects(loadingDiagnostics, "loading to error");
  await captureFullPageAtTop(loading, path.join(output, "library-error-1440.png"));
  await loading.close();

  const noResults = await context.newPage();
  const noResultsDiagnostics = collectDiagnostics(noResults);
  await noResults.route("**/assets/brand/earnalism-brand-lockup.png", (route) => route.fulfill({ status: 200, contentType: "image/png", body: officialBrandAsset }));
  await noResults.setViewportSize({ width: 1024, height: 768 });
  await installCatalogueFixture(noResults, ["success"]);
  await noResults.goto(`${baseUrl.replace(/\/$/, "")}/library?language=en&q=earnalism-no-result-9f3b&sort=title`, { waitUntil: "domcontentloaded" });
  await noResults.getByTestId("library-no-results").waitFor();
  const noResultsGeometry = await assertNoDocumentOverflow(noResults, "1024px no results");
  assertNoRuntimeDefects(noResultsDiagnostics, "no results");
  await captureFullPageAtTop(noResults, path.join(output, "library-no-results-1024.png"));
  await noResults.close();
  return { loading_geometry: loadingGeometry, no_results_geometry: noResultsGeometry };
}

async function testKeyboardRetryAndRecovery(context, viewport) {
  const page = await context.newPage();
  const diagnostics = collectDiagnostics(page);
  const officialBrandAsset = fs.readFileSync(path.resolve("frontend/public/assets/brand/earnalism-brand-lockup.png"));
  await page.route("**/assets/brand/earnalism-brand-lockup.png", (route) => route.fulfill({ status: 200, contentType: "image/png", body: officialBrandAsset }));
  await page.setViewportSize(viewport);
  const fixture = await installCatalogueFixture(page, ["reject", "pending-failure", "success"]);
  const initialUrl = "/library?language=en&availability=reader-ready&sort=title";
  await page.goto(`${baseUrl.replace(/\/$/, "")}${initialUrl}`, { waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  await waitForCatalogueState(page, "error");
  await assertError(page, `${viewport.width}px initial`);
  await captureFullPageAtTop(page, path.join(output, `library-api-error-${viewport.width}.png`));
  // The active Retry action is part of the failure state and is captured before
  // keyboard activation so owner review can judge its visibility and wording.
  await captureFullPageAtTop(page, path.join(output, `library-retry-visible-${viewport.width}.png`));

  const retry = page.getByTestId("library-catalogue-retry");
  const tabSteps = await focusRetryByTab(page, retry, `${viewport.width}px initial`);
  await page.keyboard.press("Enter");
  await page.getByTestId("library-catalogue-retry").waitFor();
  assert.equal(await retry.isDisabled(), true, `${viewport.width}px retry: pending retry is not disabled`);
  assert.equal(fixture.count(), 2, `${viewport.width}px retry: duplicate catalogue request started`);
  await retry.click({ force: true });
  assert.equal(fixture.count(), 2, `${viewport.width}px retry: repeated click started another catalogue request`);
  await captureFullPageAtTop(page, path.join(output, `library-pending-retry-${viewport.width}.png`));
  await page.getByTestId("library-reference-surface").getByTestId("library-search").fill("A Ghost Story");
  const searchDuringRetry = new URL(page.url()).searchParams;
  assert.equal(searchDuringRetry.get("language"), "en", `${viewport.width}px retry: language filter was not retained`);
  assert.equal(searchDuringRetry.get("availability"), "reader-ready", `${viewport.width}px retry: availability filter was not retained`);
  assert.equal(searchDuringRetry.get("sort"), "title", `${viewport.width}px retry: sort was not retained`);
  assert.equal(searchDuringRetry.get("q"), "A Ghost Story", `${viewport.width}px retry: search query was not retained`);
  fixture.releasePendingFailure();
  await page.waitForFunction(() => document.querySelector('[data-testid="library-catalogue-retry"]')?.disabled === false);
  await waitForCatalogueState(page, "error");
  await assertError(page, `${viewport.width}px retry failure`);
  assert.equal(await retry.isEnabled(), true, `${viewport.width}px retry failure: recovery action stayed disabled`);

  const recoveryTabSteps = await focusRetryByTab(page, retry, `${viewport.width}px retry failure`);
  await page.keyboard.press("Enter");
  await waitForCatalogueState(page, "success");
  const recoveredSearch = new URL(page.url()).searchParams;
  assert.equal(recoveredSearch.get("language"), "en", `${viewport.width}px recovery: language filter changed`);
  assert.equal(recoveredSearch.get("availability"), "reader-ready", `${viewport.width}px recovery: availability filter changed`);
  assert.equal(recoveredSearch.get("sort"), "title", `${viewport.width}px recovery: sort changed`);
  assert.equal(recoveredSearch.get("q"), "A Ghost Story", `${viewport.width}px recovery: search query changed`);
  const geometry = await assertNoDocumentOverflow(page, `${viewport.width}px recovery`);
  assertNoRuntimeDefects(diagnostics, `${viewport.width}px retry and recovery`);
  await captureFullPageAtTop(page, path.join(output, `library-recovery-${viewport.width}.png`));
  await page.close();
  return { viewport, request_count: fixture.count(), recovered_title: "A Ghost Story", recovered_state: "canonical live fixture displays Live + Details; runtime preview and segment readiness are not inferred from publication metadata", recovery_source: "successful second catalogue API response fixture; no bundled fallback", keyboard_activation: { focus: "Tab traversal", key: "Enter", initial_tab_steps: tabSteps, recovery_tab_steps: recoveryTabSteps }, geometry, result: "PASS" };
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 768, height: 1024 }, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", serviceWorkers: "block" });
const initialStates = await testInitialStates(context);
const supplementalStates = await testLoadingAndNoResults(context);
const recovery = [];
for (const viewport of [{ width: 1440, height: 900 }, { width: 1024, height: 768 }, { width: 390, height: 844 }]) {
  recovery.push(await testKeyboardRetryAndRecovery(context, viewport));
}
await context.close();
await browser.close();

const result = { result: "PASS", classification: "ISOLATED_UI_AND_INTERACTION_EVIDENCE_ONLY", output, initial_states: initialStates, supplemental_states: supplementalStates, recovery };
fs.writeFileSync(path.join(output, "summary.json"), `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify(result));
