#!/usr/bin/env node
import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the PR362 Header-to-Library journey.");

const books = [
  { slug: "devdas", title: "দেবদাস / Devdas", author: "Sarat Chandra Chattopadhyay", short_description: "Bengali edition", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, public_route: "/book/devdas", reader_url: "/reader/devdas", preview_enabled: true, preview_url: "/reader/devdas", chapters: [{ id: "devdas-page-1", is_preview: true }] },
  { slug: "pather-panchali", title: "পথের পাঁচালী / Pather Panchali", author: "Bibhutibhushan Bandyopadhyay", short_description: "Bengali edition", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, public_route: "/book/pather-panchali", reader_url: "/reader/pather-panchali", preview_enabled: true, preview_url: "/reader/pather-panchali", chapters: [{ id: "pather-page-1", is_preview: true }] },
  { slug: "frankenstein", title: "Batch-listed Bengali draft", author: "Fixture Editor", short_description: "Bengali edition", language: "bn", publication_status: "DRAFT", reader_enabled: false, preview_enabled: false, chapters: [] },
  { slug: "reader-disabled-edition", title: "Reader-disabled Bengali edition", author: "Fixture Editor", short_description: "Bengali edition", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: false, preview_enabled: false, chapters: [] },
  { slug: "book-edfcf810c5", title: "ক্ষুধিত পাষাণ", author: "Rabindranath Tagore", short_description: "Canonical Bengali publication", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, public_route: "/book/book-edfcf810c5", reader_url: "/reader/book-edfcf810c5", preview_enabled: true, preview_url: "/reader/book-edfcf810c5", chapters: [{ id: "chapter-001", is_preview: true }] },
  { slug: "book-d19e96859f", title: "Live Bengali edition without a preview", author: "Fixture Editor", short_description: "Bengali edition", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, public_route: "/book/book-d19e96859f", reader_url: "/reader/book-d19e96859f", preview_enabled: false, preview_url: "", chapters: [{ id: "chapter-001", is_preview: false }] },
  { slug: "book-f5d593e1f4", title: "Second live Bengali edition without a preview", author: "Fixture Editor", short_description: "Bengali edition", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, public_route: "/book/book-f5d593e1f4", reader_url: "/reader/book-f5d593e1f4", preview_enabled: false, preview_url: "", chapters: [{ id: "chapter-001", is_preview: false }] },
  { slug: "approved-audio-without-runtime", title: "Approved Bengali audio release", author: "Fixture Editor", short_description: "Bengali edition with approved audio metadata but no public media asset", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, public_route: "/book/approved-audio-without-runtime", reader_url: "/reader/approved-audio-without-runtime", preview_enabled: true, preview_url: "/reader/approved-audio-without-runtime", chapters: [{ id: "chapter-001", is_preview: true }], audio_enabled: true, audiobook_enabled: true, audiobook_release_gate: "APPROVED", audio_qa_status: "QA_PASSED", audio_url: "", audiobook_assets: {} },
  { slug: "hungry-stones", title: "The Hungry Stones", author: "Rabindranath Tagore", short_description: "English translation", language: "en", publication_status: "LIVE_APPROVED", reader_enabled: true, public_route: "/book/hungry-stones", reader_url: "/reader/hungry-stones", preview_enabled: true, preview_url: "/reader/hungry-stones", chapters: [{ id: "chapter-001", is_preview: true }] },
];
const expectedHeaderUrl = "?language=bn&availability=reader-ready";
const apiEligibleSlugs = ["devdas", "pather-panchali", "book-edfcf810c5", "book-d19e96859f", "book-f5d593e1f4"];
const fallbackEligibleSlugs = ["devdas", "pather-panchali"];
const ineligibleSlugs = ["frankenstein", "reader-disabled-edition", "kshudhita-pashan"];
const readerApprovedWithoutPreviewSlugs = ["book-d19e96859f", "book-f5d593e1f4"];
const approvedAudioWithoutRuntimeSlug = "approved-audio-without-runtime";
const canonicalBengaliKshudhitaSlug = "book-edfcf810c5";
const pipelineBengaliKshudhitaSlug = "kshudhita-pashan";
const searchEligibleSlugs = apiEligibleSlugs.filter((slug) => slug !== canonicalBengaliKshudhitaSlug);

function query(page) {
  return new URL(page.url()).search;
}

function referenceSurface(page) {
  return page.getByTestId("library-reference-surface");
}

async function selectedControls(page, mobile) {
  const language = filterGroup(page, mobile, "language").getByRole("button", { name: "Bengali", exact: true });
  const status = filterGroup(page, mobile, "listening").getByRole("button", { name: "Reader only", exact: true });
  await assertSelected(language, "Bengali");
  await assertSelected(status, "Reader only");
}

function filterSurface(page, mobile) {
  return mobile
    ? page.locator('.reference-library-drawer[role="dialog"]:visible')
    : page.locator("aside.reference-library__sidebar:visible");
}

function filterGroup(page, mobile, groupId) {
  return filterSurface(page, mobile).locator(`[data-filter-group="${groupId}"]`);
}

function params(page) {
  return new URL(page.url()).searchParams;
}

async function assertFilterTarget(locator, label) {
  const box = await locator.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return { width: rect.width, height: rect.height, scrollWidth: element.scrollWidth, clientWidth: element.clientWidth, display: style.display, visibility: style.visibility };
  });
  assert.ok(box.width >= 44 && box.height >= 44, `${label} must have a 44×44 CSS-pixel target; received ${box.width}×${box.height}`);
  assert.ok(box.scrollWidth <= box.clientWidth, `${label} must wrap rather than clip`);
  assert.notEqual(box.display, "none", `${label} must be displayed`);
  assert.notEqual(box.visibility, "hidden", `${label} must be visible`);
}

async function assertNoHorizontalOverflow(page, label) {
  const metrics = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
  assert.ok(metrics.scrollWidth <= metrics.clientWidth, `${label}: document overflows horizontally (${metrics.scrollWidth}px > ${metrics.clientWidth}px)`);
}

async function assertDrawerOptionPolicy(page, mobile) {
  if (!mobile) return;
  assert.equal(await filterGroup(page, true, "language").getByRole("button", { name: "All books", exact: true }).count(), 0, "Language must retain its compact hideAll behavior");
  assert.equal(await filterGroup(page, true, "reading").getByRole("button", { name: "All forms", exact: true }).count(), 0, "Format must retain its compact hideAll behavior");
  assert.equal(await filterGroup(page, true, "listening").getByRole("button", { name: "All releases", exact: true }).count(), 1, "Listening must expose All releases by stable group id");
}

async function closeFilters(page, mobile) {
  if (mobile) await page.getByRole("button", { name: "Apply filters", exact: true }).click();
}

async function assertSelected(locator, label) {
  await locator.waitFor();
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (await locator.getAttribute("aria-pressed") === "true") return;
    await locator.page().waitForTimeout(25);
  }
  assert.equal(await locator.getAttribute("aria-pressed"), "true", `${label} is not selected`);
}

async function assertEligibleReaderResults(page, expectedSlugs) {
  const surface = referenceSurface(page);
  const expected = [...expectedSlugs].sort();
  await page.waitForFunction((expectedIds) => {
    const container = document.querySelector('[data-testid="library-reference-surface"]');
    const ids = [...(container?.querySelectorAll('[data-testid^="reference-book-"]') || [])]
      .map((node) => node.getAttribute("data-testid").replace("reference-book-", ""))
      .sort();
    return ids.join("\u0000") === expectedIds.join("\u0000");
  }, expected, { timeout: Number(process.env.LIBRARY_JOURNEY_SETTLE_TIMEOUT_MS || 30000) });
  const displayedSlugs = await surface.locator('[data-testid^="reference-book-"]').evaluateAll((nodes) => (
    nodes.map((node) => node.getAttribute("data-testid").replace("reference-book-", "")).sort()
  ));
  assert.deepEqual(displayedSlugs, expected, "every displayed Reader-only result must satisfy the canonical release predicate");
  for (const slug of ineligibleSlugs) {
    assert.equal(await surface.getByTestId(`reference-book-${slug}`).count(), 0, `${slug} leaked into Reader only results`);
  }
}

async function assertReaderApprovedWithoutPreviewCards(page) {
  const surface = referenceSurface(page);
  for (const slug of readerApprovedWithoutPreviewSlugs) {
    const card = surface.getByTestId(`reference-book-${slug}`);
    await card.waitFor();
    await expectText(card.locator(".reference-book-tile__status"), "Live", `${slug} must retain its reader-approved visible status`);
    const cta = card.getByRole("link", { name: "Details", exact: true });
    await cta.waitFor();
    assert.equal(await cta.getAttribute("href"), `/book/${slug}`, `${slug} must retain its safe Book Detail destination`);
    assert.equal(await card.getByRole("link", { name: "Read", exact: true }).count(), 0, `${slug} must not invent a preview CTA`);
  }
}

async function assertApprovedAudioWithoutRuntimeCard(page, name) {
  const cards = referenceSurface(page).getByTestId(`reference-book-${approvedAudioWithoutRuntimeSlug}`);
  await cards.first().waitFor();
  const count = await cards.count();
  assert.equal(count, 2, `${name}: approved mixed-format edition must remain present in both Live now and Audiobooks shelves`);
  for (let index = 0; index < count; index += 1) {
    const card = cards.nth(index);
    await expectText(card.locator(".reference-book-tile__status"), "Live", `${name}: approved mixed-format edition became coming soon`);
    const detail = card.getByRole("link", { name: "Read", exact: true });
    await detail.waitFor();
    assert.equal(await detail.getAttribute("href"), `/reader/${approvedAudioWithoutRuntimeSlug}`, `${name}: approved mixed-format preview lost its reader destination`);
    assert.equal(await card.getByRole("link", { name: "Notify me", exact: true }).count(), 0, `${name}: approved mixed-format edition redirected to Notify me`);
    assert.equal(await card.getByText("Listening unavailable", { exact: true }).count(), 1, `${name}: unavailable Reader runtime was not explained truthfully`);
  }
}

async function assertNotifyDestination(page, slug, label) {
  const card = referenceSurface(page).getByTestId(`reference-book-${slug}`);
  await card.waitFor();
  const cta = card.getByRole("link", { name: "Notify me", exact: true });
  await cta.waitFor();
  assert.equal(await cta.getAttribute("href"), `/contact?interest=${slug}`, `${label}: ${slug} notification destination changed`);
}

async function assertApiCanonicalKshudhita(page, name) {
  const surface = referenceSurface(page);
  await surface.getByTestId(`reference-book-${canonicalBengaliKshudhitaSlug}`).waitFor();
  assert.equal(await surface.getByTestId(`reference-book-${pipelineBengaliKshudhitaSlug}`).count(), 0, `${name}: pipeline placeholder duplicated the canonical Bengali edition`);
  const detail = surface.getByTestId(`reference-book-${canonicalBengaliKshudhitaSlug}`).getByRole("link", { name: "Read", exact: true });
  await detail.waitFor();
  assert.equal(await detail.getAttribute("href"), `/reader/${canonicalBengaliKshudhitaSlug}`, `${name}: canonical Bengali edition lost its approved reader route`);
}

async function assertFallbackKshudhita(page, mobile, expectedSlugs, name) {
  await openFilters(page, mobile);
  const allReleases = filterGroup(page, mobile, "listening").getByRole("button", { name: "All releases", exact: true });
  await assertFilterTarget(allReleases, `${name}: All releases`);
  await allReleases.click();
  await closeFilters(page, mobile);

  const surface = referenceSurface(page);
  await surface.getByTestId(`reference-book-${pipelineBengaliKshudhitaSlug}`).waitFor();
  assert.equal(await surface.getByTestId(`reference-book-${canonicalBengaliKshudhitaSlug}`).count(), 0, `${name}: fallback invented the absent canonical publication`);
  await assertNotifyDestination(page, pipelineBengaliKshudhitaSlug, name);

  await openFilters(page, mobile);
  const english = filterGroup(page, mobile, "language").getByRole("button", { name: "English", exact: true });
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.searchParams.get("language") === "en"),
    english.click(),
  ]);
  await closeFilters(page, mobile);
  await surface.getByTestId("reference-book-hungry-stones").waitFor();
  assert.equal(await surface.getByTestId(`reference-book-${pipelineBengaliKshudhitaSlug}`).count(), 0, `${name}: Bengali pipeline edition leaked into English results`);

  await openFilters(page, mobile);
  const bengali = filterGroup(page, mobile, "language").getByRole("button", { name: "Bengali", exact: true });
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.searchParams.get("language") === "bn"),
    bengali.click(),
  ]);
  await assertSelected(bengali, `${name}: Bengali`);
  const readerOnly = filterGroup(page, mobile, "listening").getByRole("button", { name: "Reader only", exact: true });
  await readerOnly.press("Enter");
  await closeFilters(page, mobile);
  await assertEligibleReaderResults(page, expectedSlugs);
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

async function openFilters(page, mobile) {
  if (mobile) await page.locator("button.reference-filter-trigger:visible").click();
}

async function assertAllReleasesRoundTrip(page, mobile, expectedSlugs, name, source) {
  await openFilters(page, mobile);
  await assertDrawerOptionPolicy(page, mobile);
  const listeningGroup = filterGroup(page, mobile, "listening");
  const allReleases = listeningGroup.getByRole("button", { name: "All releases", exact: true });
  await assertFilterTarget(allReleases, `${name}: All releases`);
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.searchParams.get("language") === "bn" && !url.searchParams.has("listening") && !url.searchParams.has("availability")),
    allReleases.click(),
  ]);
  assert.equal(params(page).get("language"), "bn", `${name}: All releases must retain Bengali`);
  assert.equal(params(page).get("listening"), null, `${name}: All releases must remove listening`);
  assert.equal(params(page).get("availability"), null, `${name}: All releases must remove legacy availability`);
  await assertSelected(filterGroup(page, mobile, "listening").getByRole("button", { name: "All releases", exact: true }), "All releases");

  const sort = mobile
    ? filterSurface(page, true).getByRole("combobox", { name: "Sort by", exact: true })
    : page.getByTestId("library-reference-surface").getByTestId("library-sort");
  await sort.selectOption("title");
  await closeFilters(page, mobile);
  await assertReaderApprovedWithoutPreviewCards(page);
  if (source === "api") await assertApprovedAudioWithoutRuntimeCard(page, name);
  await assertApiCanonicalKshudhita(page, name);
  await openFilters(page, mobile);
  const english = filterGroup(page, mobile, "language").getByRole("button", { name: "English", exact: true });
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.searchParams.get("language") === "en"),
    english.click(),
  ]);
  await closeFilters(page, mobile);
  await referenceSurface(page).getByTestId("reference-book-hungry-stones").waitFor();
  assert.equal(await referenceSurface(page).getByTestId(`reference-book-${canonicalBengaliKshudhitaSlug}`).count(), 0, `${name}: Bengali edition leaked into English results`);
  await openFilters(page, mobile);
  const bengali = filterGroup(page, mobile, "language").getByRole("button", { name: "Bengali", exact: true });
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.searchParams.get("language") === "bn"),
    bengali.click(),
  ]);
  await assertSelected(filterGroup(page, mobile, "language").getByRole("button", { name: "Bengali", exact: true }), `${name}: Bengali`);
  assert.equal(params(page).get("language"), "bn", `${name}: Bengali selection did not update the URL`);
  await closeFilters(page, mobile);
  await assertNoHorizontalOverflow(page, `${name}: All releases`);
  const search = page.getByTestId("library-reference-surface").getByTestId("library-search");
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.searchParams.get("q") === "edition"),
    search.fill("edition"),
  ]);
  assert.equal(params(page).get("language"), "bn", `${name}: search must retain Bengali`);
  assert.equal(params(page).get("sort"), "title", `${name}: search must retain sort`);
  assert.equal(params(page).get("q"), "edition", `${name}: search query must persist`);
  assert.equal(params(page).get("listening"), null, `${name}: search must not restore listening`);
  await assertReaderApprovedWithoutPreviewCards(page);

  await openFilters(page, mobile);
  const readerOnly = filterGroup(page, mobile, "listening").getByRole("button", { name: "Reader only", exact: true });
  await assertFilterTarget(readerOnly, `${name}: Reader only`);
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/library" && url.searchParams.get("listening") === "hidden"),
    readerOnly.press("Enter"),
  ]);
  await closeFilters(page, mobile);
  assert.equal(params(page).get("language"), "bn", `${name}: Reader only must retain Bengali`);
  assert.equal(params(page).get("sort"), "title", `${name}: Reader only must retain sort`);
  assert.equal(params(page).get("q"), "edition", `${name}: Reader only must retain search`);
  assert.equal(params(page).get("listening"), "hidden", `${name}: Reader only must use canonical listening=hidden`);
  assert.equal(params(page).get("availability"), null, `${name}: Reader only must not restore legacy availability`);
  await assertEligibleReaderResults(page, source === "api" ? searchEligibleSlugs : expectedSlugs);
  await assertNoHorizontalOverflow(page, name);

  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  assert.equal(params(page).get("listening"), "hidden", `${name}: reload must retain Reader-only`);
  assert.equal(params(page).get("sort"), "title", `${name}: reload must retain sort`);
  assert.equal(params(page).get("q"), "edition", `${name}: reload must retain search`);
  await assertEligibleReaderResults(page, source === "api" ? searchEligibleSlugs : expectedSlugs);

  await page.goBack({ waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  assert.equal(params(page).get("language"), "bn", `${name}: Back must retain Bengali`);
  assert.equal(params(page).get("sort"), "title", `${name}: Back must retain sort`);
  assert.equal(params(page).get("q"), "edition", `${name}: Back must retain search`);
  assert.equal(params(page).get("listening"), null, `${name}: Back must restore All releases`);
  assert.equal(params(page).get("availability"), null, `${name}: Back must keep legacy availability removed`);
  await assertReaderApprovedWithoutPreviewCards(page);
}

async function assertAudiobooksRoundTrip(page, mobile, name, source) {
  const returnUrl = query(page);
  await openFilters(page, mobile);
  const audiobooks = filterGroup(page, mobile, "listening").getByRole("button", { name: "Audiobooks", exact: true });
  await assertFilterTarget(audiobooks, `${name}: Audiobooks`);
  await audiobooks.click();
  await closeFilters(page, mobile);
  assert.equal(params(page).get("listening"), "available", `${name}: Audiobooks must use canonical listening=available`);
  assert.equal(params(page).get("availability"), null, `${name}: Audiobooks must remove legacy availability`);
  if (source === "api") await assertApprovedAudioWithoutRuntimeCard(page, name);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  assert.equal(params(page).get("listening"), "available", `${name}: Audiobooks reload must retain the selected filter`);
  await page.goBack({ waitUntil: "domcontentloaded" });
  await page.getByTestId("library-reference-surface").waitFor();
  assert.equal(query(page), returnUrl, `${name}: Back must restore the preceding filter state`);
}

async function run({ name, viewport, mobile, source }) {
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
  if (mobile) await page.getByRole("button", { name: "Close filters", exact: true }).click();
  if (source === "api") await assertAllReleasesRoundTrip(page, mobile, expectedSlugs, name, source);
  else {
    await assertFallbackKshudhita(page, mobile, expectedSlugs, name);
    await assertNoHorizontalOverflow(page, name);
  }
  await assertAudiobooksRoundTrip(page, mobile, name, source);
  await context.close();
  await browser.close();
  return { viewport, source, header_url: expectedHeaderUrl, result: "PASS" };
}

const results = [];
const scenarios = [
  { name: "320-api", viewport: { width: 320, height: 568 }, mobile: true, source: "api" },
  { name: "390-api", viewport: { width: 390, height: 844 }, mobile: true, source: "api" },
  { name: "768-api", viewport: { width: 768, height: 1024 }, mobile: true, source: "api" },
  { name: "1440-api", viewport: { width: 1440, height: 900 }, mobile: false, source: "api" },
  { name: "320-fallback", viewport: { width: 320, height: 568 }, mobile: true, source: "fallback" },
  { name: "1440-fallback", viewport: { width: 1440, height: 900 }, mobile: false, source: "fallback" },
];
const requestedScenarios = String(process.env.LIBRARY_JOURNEY_SCENARIOS || "")
  .split(",")
  .map((name) => name.trim())
  .filter(Boolean);
const selectedScenarios = requestedScenarios.length
  ? scenarios.filter((scenario) => requestedScenarios.includes(scenario.name))
  : scenarios;
if (!selectedScenarios.length) throw new Error("No requested Library journey scenarios matched the supported fixture names.");
for (const scenario of selectedScenarios) {
  results.push(await run(scenario));
  console.log(`PASS ${scenario.name} ${scenario.viewport.width}x${scenario.viewport.height}`);
}
console.log(JSON.stringify({ result: "PASS", testCaseCount: results.length, results }));
