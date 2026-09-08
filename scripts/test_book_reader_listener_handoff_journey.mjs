#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for the Book Detail handoff journey.");
const output = process.env.BOOK_READER_LISTENER_EVIDENCE_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), "book-reader-listener-handoff-"));
fs.mkdirSync(output, { recursive: true });
const browserLaunchOptions = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
  ? { headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
  : { headless: true };

const readerBook = {
  slug: "mapped-edition",
  title: "Mapped Edition",
  author: "Fixture Author",
  publication_status: "LIVE_APPROVED",
  description: "An isolated reader-ready title.",
  chapters: [{ id: "chapter-one", title: "Chapter One" }, { id: "chapter-two", title: "Chapter Two" }],
};
const preparationBook = {
  slug: "preparation-edition",
  title: "Preparation Edition",
  author: "Fixture Editor",
  publication_status: "DRAFT",
  description: "An isolated preparation title.",
  chapters: [{ id: "draft-chapter", title: "Draft Chapter" }],
};
const protectedChapterBook = {
  slug: "protected-chapter-edition",
  title: "Protected Chapter Edition",
  author: "Fixture Author",
  publication_status: "LIVE_APPROVED",
  description: "An isolated edition with a server-mapped protected chapter.",
  chapters: [{ id: "chapter-one", title: "Chapter One" }, { id: "chapter-two", title: "Chapter Two" }],
};
const audioBook = {
  slug: "audio-edition",
  title: "Approved Listening Edition",
  author: "Fixture Narrator",
  publication_status: "LIVE_APPROVED",
  description: "An isolated approved-audio title.",
  audiobook_enabled: true,
  audio_enabled: true,
  audiobook_release_gate: "APPROVED",
  audio_qa_status: "QA_PASSED",
  audiobook_assets: { mp3: "/api/reader/book/audio-edition/audiobook" },
  chapters: [{ id: "audio-chapter", title: "Approved Chapter" }],
};

function manifestFor(book, { readingPassEnabled = true } = {}) {
  const approvedAudio = book.slug === audioBook.slug;
  const mappedProtectedChapter = book.slug === protectedChapterBook.slug;
  return {
    book,
    access: { reading_pass: { enabled: readingPassEnabled, total_pages: 8 } },
    canonical_pages: {
      page_count: 8,
      pages: approvedAudio || mappedProtectedChapter
        ? [
          { page_number: 1, chapter_id: "chapter-one", chapter_title: "Chapter One" },
          { page_number: 4, chapter_id: "chapter-two", chapter_title: "Chapter Two" },
        ]
        : [
          { page_number: 1, chapter_id: "chapter-one", chapter_title: "Chapter One" },
          // Chapter two deliberately has no server-provided canonical page.
          // The detail view must not derive one from its ID or its order.
        ],
    },
    audio: approvedAudio ? {
      enabled: true,
      provider: "fixture-provider",
      version: "fixture-v1",
      release_gate: "APPROVED",
      qa_status: "QA_PASSED",
      asset_slug: book.slug,
      assets: { mp3: `/api/reader/book/${book.slug}/audiobook` },
    } : { enabled: false, assets: {} },
  };
}

function pagePayload(book, pageIndex) {
  return {
    book_slug: book.slug,
    page_index: pageIndex,
    total_pages: 8,
    is_preview: pageIndex <= 3,
    chapter_id: pageIndex < 4 ? "chapter-one" : "chapter-two",
    chapter_title: pageIndex < 4 ? "Chapter One" : "Chapter Two",
    content: `<p>Fixture canonical page ${pageIndex}.</p>`,
  };
}

async function configureApi(page, { authenticated = false, denyLease = false, readingPassEnabled = true, sessionStartDelayMs = 0 } = {}) {
  const requests = { sessionStarts: 0, protectedPageRequests: 0 };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;
    const book = [readerBook, preparationBook, protectedChapterBook, audioBook].find((candidate) => (
      pathname.endsWith(`/books/${candidate.slug}`)
      || pathname.includes(`/reader/book/${candidate.slug}/`)
      || pathname.includes(`/reading-pass/books/${candidate.slug}/`)
    ));
    if (pathname.endsWith("/users/me")) {
      await route.fulfill({ status: authenticated ? 200 : 401, contentType: "application/json", body: JSON.stringify(authenticated ? { id: "fixture-user", name: "Fixture Reader" } : { detail: "Not signed in" }) });
      return;
    }
    if (pathname.endsWith("/books")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([readerBook, preparationBook, protectedChapterBook, audioBook]) });
      return;
    }
    if (book && pathname.endsWith(`/books/${book.slug}`)) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(book) });
      return;
    }
    if (book && pathname.includes(`/reader/book/${book.slug}/manifest`)) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(manifestFor(book, { readingPassEnabled })) });
      return;
    }
    if (book && /\/reading-pass\/books\/[^/]+\/pages\/\d+$/.test(pathname)) {
      const pageIndex = Number(pathname.split("/").at(-1));
      if (pageIndex > 3) requests.protectedPageRequests += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(pagePayload(book, pageIndex)) });
      return;
    }
    if (pathname.endsWith("/reading-pass/sessions/start")) {
      requests.sessionStarts += 1;
      if (sessionStartDelayMs) await new Promise((resolve) => setTimeout(resolve, sessionStartDelayMs));
      const response = !authenticated
        ? { status: 401, body: { detail: { message: "Sign in to continue." } } }
        : denyLease
          ? { status: 403, body: { detail: { message: "A current Reading Pass is required to continue." } } }
          : { status: 200, body: { session_id: "fixture-lease", lease_token: "fixture-token", lease_version: 1 } };
      await route.fulfill({ status: response.status, contentType: "application/json", body: JSON.stringify(response.body) });
      return;
    }
    if (pathname.endsWith("/reader/book/audio-edition/audiobook")) {
      await route.fulfill({ status: 403, contentType: "application/json", body: JSON.stringify({ detail: "Fixture protected stream" }) });
      return;
    }
    await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Unhandled isolated fixture request" }) });
  });
  return requests;
}

async function tabTo(page, predicate, label) {
  for (let index = 0; index < 80; index += 1) {
    await page.keyboard.press("Tab");
    const active = await page.evaluate(() => ({ testId: document.activeElement?.getAttribute("data-testid") || "", href: document.activeElement?.getAttribute("href") || "" }));
    if (predicate(active)) return active;
  }
  throw new Error(`${label}: target was not reachable by Tab`);
}

async function runAnonymousHandoffs({ id, viewport }) {
  const browser = await chromium.launch(browserLaunchOptions);
  const context = await browser.newContext({ viewport, serviceWorkers: "block", locale: "en-US", timezoneId: "UTC" });
  const page = await context.newPage();
  page.setDefaultTimeout(8_000);
  await configureApi(page);
  const base = baseUrl.replace(/\/$/, "");

  await page.goto(`${base}/book/${audioBook.slug}`, { waitUntil: "domcontentloaded" });
  const listenerCta = page.getByTestId("book-listen-approved");
  await listenerCta.waitFor();
  assert.equal(await listenerCta.getAttribute("href"), `/listener/${audioBook.slug}`, `${id}: approved audio CTA must target Listener`);
  assert.equal((await listenerCta.textContent()).trim(), "Open Listening Room", `${id}: approved audio CTA wording drifted`);
  await tabTo(page, (active) => active.testId === "book-listen-approved", `${id}: listener CTA`);
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");
  await Promise.all([page.waitForURL((url) => url.pathname === `/listener/${audioBook.slug}`), page.keyboard.press("Enter")]);
  await page.getByRole("button", { name: "Authorize Listening" }).waitFor();
  assert.equal(await page.locator("audio").count(), 0, `${id}: anonymous listener exposed an audio element`);
  await page.screenshot({ path: path.join(output, `${id}-listener-anonymous.png`), fullPage: true });
  await page.goBack({ waitUntil: "domcontentloaded" });
  await listenerCta.waitFor();
  assert.equal(new URL(page.url()).pathname, `/book/${audioBook.slug}`, `${id}: browser Back did not restore Book Detail`);
  await page.goForward({ waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Authorize Listening" }).waitFor();
  await Promise.all([page.waitForURL((url) => url.pathname === "/login"), page.getByRole("button", { name: "Authorize Listening" }).click()]);
  assert.equal(new URL(page.url()).searchParams.get("next"), `/listener/${audioBook.slug}`, `${id}: listener sign-in return destination changed`);

  await page.goto(`${base}/book/${preparationBook.slug}`, { waitUntil: "domcontentloaded" });
  const preparationAction = page.getByTestId("start-reading");
  await preparationAction.waitFor();
  assert.equal((await preparationAction.textContent()).trim(), "Back to Library", `${id}: preparation wording drifted`);
  assert.equal(await preparationAction.getAttribute("href"), "/library", `${id}: preparation recovery must target Library`);
  await page.screenshot({ path: path.join(output, `${id}-preparation.png`), fullPage: true });

  await page.goto(`${base}/book/${readerBook.slug}`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "Chapters", exact: true }).click();
  const mappedChapter = page.getByRole("link", { name: "Chapter One", exact: true });
  await mappedChapter.waitFor();
  assert.equal(await mappedChapter.getAttribute("href"), `/reader/${readerBook.slug}?p=1`, `${id}: chapter start must use manifest page p=1`);
  assert.equal(await page.getByRole("link", { name: "Chapter Two", exact: true }).count(), 0, `${id}: unmapped chapter must not claim a jump link`);
  const ordinaryEntry = page.getByTestId("chapter-reader-entry");
  assert.equal(await ordinaryEntry.getAttribute("href"), `/reader/${readerBook.slug}`, `${id}: unmapped chapter recovery must be ordinary reader entry`);
  await page.screenshot({ path: path.join(output, `${id}-chapters.png`), fullPage: true });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "Chapters", exact: true }).click();
  assert.equal(await page.getByTestId("chapter-reader-entry").getAttribute("href"), `/reader/${readerBook.slug}`, `${id}: reload changed missing-mapping recovery`);

  await page.goto(`${base}/book/${readerBook.slug}`, { waitUntil: "domcontentloaded" });
  assert.equal(await page.getByTestId("book-listen-approved").count(), 0, `${id}: unapproved audio received a listening CTA`);

  const geometry = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
  assert.equal(geometry.scrollWidth, geometry.clientWidth, `${id}: document has horizontal overflow`);
  await context.close();
  await browser.close();
  return { id, viewport, authenticated: false, geometry, result: "PASS" };
}

async function openProtectedChapterFromBookDetail(page, id) {
  await page.getByRole("tab", { name: "Chapters", exact: true }).click();
  const chapter = page.getByRole("link", { name: "Chapter Two", exact: true });
  await chapter.waitFor();
  assert.equal(await chapter.getAttribute("href"), `/reader/${protectedChapterBook.slug}?p=4`, `${id}: Book Detail must use the server-mapped canonical protected page`);
  await tabTo(page, (active) => active.href === `/reader/${protectedChapterBook.slug}?p=4`, `${id}: protected chapter link`);
  await Promise.all([
    page.waitForURL((url) => url.pathname === `/reader/${protectedChapterBook.slug}` && url.searchParams.get("p") === "4"),
    page.keyboard.press("Enter"),
  ]);
}

async function runProtectedChapterEntry({ id, viewport }) {
  const base = baseUrl.replace(/\/$/, "");
  const browser = await chromium.launch(browserLaunchOptions);
  const context = await browser.newContext({ viewport, serviceWorkers: "block", locale: "en-US", timezoneId: "UTC" });
  await context.addInitScript(() => localStorage.setItem("earnalism_user_token", "fixture-token"));
  const page = await context.newPage();
  page.setDefaultTimeout(8_000);
  const requests = await configureApi(page, { authenticated: true, sessionStartDelayMs: 75 });

  await page.goto(`${base}/book/${protectedChapterBook.slug}`, { waitUntil: "domcontentloaded" });
  await openProtectedChapterFromBookDetail(page, id);
  await page.getByRole("heading", { name: "Continue to this chapter" }).waitFor();
  assert.equal(requests.sessionStarts, 0, `${id}: navigating to a protected chapter must not create a lease`);
  assert.equal(requests.protectedPageRequests, 0, `${id}: navigating to a protected chapter must not request protected content`);
  await page.screenshot({ path: path.join(output, `${id}-protected-chapter-awaiting-authorization.png`), fullPage: true });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByTestId("reader-authorize-chapter").waitFor();
  assert.equal(requests.sessionStarts, 0, `${id}: reload must retain an explicit authorization step`);
  assert.equal(requests.protectedPageRequests, 0, `${id}: reload must not request protected content`);
  await tabTo(page, (active) => active.testId === "reader-authorize-chapter", `${id}: chapter authorization action`);
  await page.getByTestId("reader-authorize-chapter").evaluate((node) => { node.click(); node.click(); });
  await page.getByTestId("reader-reading-text").waitFor();
  assert.match(await page.getByTestId("reader-reading-text").textContent(), /Fixture canonical page 4/, `${id}: authorization must open the requested canonical page`);
  assert.equal(requests.sessionStarts, 1, `${id}: duplicate authorization submissions created more than one lease`);
  assert.equal(requests.protectedPageRequests, 1, `${id}: authorization must request exactly the selected protected page`);
  await page.screenshot({ path: path.join(output, `${id}-protected-chapter-authorized.png`), fullPage: true });
  await context.close();

  const anonymousContext = await browser.newContext({ viewport, serviceWorkers: "block", locale: "en-US", timezoneId: "UTC" });
  const anonymousPage = await anonymousContext.newPage();
  anonymousPage.setDefaultTimeout(8_000);
  const anonymousRequests = await configureApi(anonymousPage);
  await anonymousPage.goto(`${base}/book/${protectedChapterBook.slug}`, { waitUntil: "domcontentloaded" });
  await openProtectedChapterFromBookDetail(anonymousPage, `${id}: anonymous`);
  await anonymousPage.getByTestId("reader-recovery-sign-in").waitFor();
  assert.equal(await anonymousPage.getByTestId("reader-recovery-sign-in").getAttribute("href"), `/login?next=%2Freader%2F${protectedChapterBook.slug}%3Fp%3D4`, `${id}: anonymous return must preserve book and canonical page`);
  assert.equal(anonymousRequests.sessionStarts, 0, `${id}: anonymous navigation must not start a lease`);
  assert.equal(anonymousRequests.protectedPageRequests, 0, `${id}: anonymous navigation must not request protected content`);
  await anonymousPage.screenshot({ path: path.join(output, `${id}-protected-chapter-anonymous.png`), fullPage: true });
  await anonymousContext.close();

  const deniedContext = await browser.newContext({ viewport, serviceWorkers: "block", locale: "en-US", timezoneId: "UTC" });
  await deniedContext.addInitScript(() => localStorage.setItem("earnalism_user_token", "fixture-token"));
  const deniedPage = await deniedContext.newPage();
  deniedPage.setDefaultTimeout(8_000);
  const deniedRequests = await configureApi(deniedPage, { authenticated: true, denyLease: true });
  await deniedPage.goto(`${base}/book/${protectedChapterBook.slug}`, { waitUntil: "domcontentloaded" });
  await openProtectedChapterFromBookDetail(deniedPage, `${id}: denied`);
  await deniedPage.getByTestId("reader-authorize-chapter").click();
  await deniedPage.getByRole("heading", { name: "Reader unavailable" }).waitFor();
  assert.equal(await deniedPage.getByTestId("reader-reading-text").count(), 0, `${id}: denied authorization exposed protected content`);
  assert.equal(await deniedPage.getByTestId("reader-authorize-chapter").count(), 0, `${id}: denied authorization offered an automatic retry`);
  assert.equal(deniedRequests.protectedPageRequests, 0, `${id}: denied authorization requested protected content`);
  await deniedContext.close();

  const disabledContext = await browser.newContext({ viewport, serviceWorkers: "block", locale: "en-US", timezoneId: "UTC" });
  await disabledContext.addInitScript(() => localStorage.setItem("earnalism_user_token", "fixture-token"));
  const disabledPage = await disabledContext.newPage();
  disabledPage.setDefaultTimeout(8_000);
  const disabledRequests = await configureApi(disabledPage, { authenticated: true, readingPassEnabled: false });
  await disabledPage.goto(`${base}/book/${protectedChapterBook.slug}`, { waitUntil: "domcontentloaded" });
  await openProtectedChapterFromBookDetail(disabledPage, `${id}: disabled`);
  await disabledPage.getByRole("heading", { name: "Reader unavailable" }).waitFor();
  assert.equal(await disabledPage.getByTestId("reader-authorize-chapter").count(), 0, `${id}: disabled edition offered authorization`);
  assert.equal(await disabledPage.getByTestId("reader-reading-text").count(), 0, `${id}: disabled edition exposed protected content`);
  assert.equal(disabledRequests.sessionStarts, 0, `${id}: disabled edition started a lease`);
  assert.equal(disabledRequests.protectedPageRequests, 0, `${id}: disabled edition requested protected content`);
  await disabledContext.close();
  await browser.close();
  return { id, viewport, protectedChapter: true, result: "PASS" };
}

async function runEntitledReader({ id, viewport }) {
  const browser = await chromium.launch(browserLaunchOptions);
  const context = await browser.newContext({ viewport, serviceWorkers: "block", locale: "en-US", timezoneId: "UTC" });
  await context.addInitScript(() => localStorage.setItem("earnalism_user_token", "fixture-token"));
  const page = await context.newPage();
  page.setDefaultTimeout(8_000);
  await configureApi(page, { authenticated: true });
  const base = baseUrl.replace(/\/$/, "");
  await page.goto(`${base}/reader/${readerBook.slug}?p=3`, { waitUntil: "domcontentloaded" });
  await page.getByTestId("reader-reading-text").waitFor();
  await Promise.all([page.waitForURL((url) => url.searchParams.get("p") === "4"), page.getByRole("button", { name: /Use Reading Time to Continue/ }).click()]);
  await page.getByTestId("reader-reading-text").waitFor();
  assert.match(await page.getByTestId("reader-reading-text").textContent(), /Fixture canonical page 4/, `${id}: entitled reader did not receive the server fixture page`);
  await page.screenshot({ path: path.join(output, `${id}-reader-entitled.png`), fullPage: true });
  await context.close();
  await browser.close();
  return { id, viewport, authenticated: true, result: "PASS" };
}

async function runEntitledListener({ id, viewport }) {
  const browser = await chromium.launch(browserLaunchOptions);
  const context = await browser.newContext({ viewport, serviceWorkers: "block", locale: "en-US", timezoneId: "UTC" });
  await context.addInitScript(() => localStorage.setItem("earnalism_user_token", "fixture-token"));
  const page = await context.newPage();
  page.setDefaultTimeout(8_000);
  await configureApi(page, { authenticated: true });
  const base = baseUrl.replace(/\/$/, "");
  await page.goto(`${base}/listener/${audioBook.slug}`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Authorize Listening" }).waitFor();
  await page.getByRole("button", { name: "Authorize Listening" }).click();
  await page.locator("audio").waitFor({ state: "attached" });
  const stream = await page.locator("audio").getAttribute("src");
  assert.match(stream, new RegExp(`/api/reader/book/${audioBook.slug}/audiobook$`), `${id}: entitled listener did not use the protected stream route`);
  await page.screenshot({ path: path.join(output, `${id}-listener-entitled.png`), fullPage: true });
  await context.close();
  await browser.close();
  return { id, viewport, authenticated: true, result: "PASS" };
}

async function runDeniedAccess({ id, viewport }) {
  const browser = await chromium.launch(browserLaunchOptions);
  const context = await browser.newContext({ viewport, serviceWorkers: "block", locale: "en-US", timezoneId: "UTC" });
  await context.addInitScript(() => localStorage.setItem("earnalism_user_token", "fixture-token"));
  const page = await context.newPage();
  page.setDefaultTimeout(8_000);
  await configureApi(page, { authenticated: true, denyLease: true });
  const base = baseUrl.replace(/\/$/, "");

  await page.goto(`${base}/reader/${readerBook.slug}?p=3`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /Use Reading Time to Continue/ }).click();
  await page.getByRole("heading", { name: "Reader unavailable" }).waitFor();
  assert.equal(await page.getByTestId("reader-recovery-passes").getAttribute("href"), "/pricing", `${id}: denied reader recovery must use existing passes route`);

  await page.goto(`${base}/listener/${audioBook.slug}`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Authorize Listening" }).click();
  await page.getByRole("heading", { name: "Listening access needs attention" }).waitFor();
  assert.equal(await page.getByTestId("listener-recovery-passes").getAttribute("href"), "/pricing", `${id}: denied listener recovery must use existing passes route`);
  await page.screenshot({ path: path.join(output, `${id}-access-denied.png`), fullPage: true });
  await context.close();
  await browser.close();
  return { id, viewport, authenticated: true, denied: true, result: "PASS" };
}

const results = [];
const scenarios = [
  { id: "desktop-1440", viewport: { width: 1440, height: 900 } },
  { id: "tablet-768", viewport: { width: 768, height: 1024 } },
  { id: "mobile-390", viewport: { width: 390, height: 844 } },
];
const selectedScenarioIds = new Set((process.env.BOOK_READER_LISTENER_SCENARIOS || "").split(",").filter(Boolean));
for (const scenario of scenarios.filter(({ id }) => selectedScenarioIds.size === 0 || selectedScenarioIds.has(id))) {
  results.push(await runAnonymousHandoffs(scenario));
  results.push(await runProtectedChapterEntry(scenario));
  results.push(await runEntitledReader(scenario));
  results.push(await runEntitledListener(scenario));
  results.push(await runDeniedAccess(scenario));
}

const summary = { result: "PASS", classification: "ISOLATED_FIXTURE_EVIDENCE_ONLY", css_zoom: { applied: false, classification: "NOT_APPLIED" }, output, results };
fs.writeFileSync(path.join(output, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`);
console.log(JSON.stringify(summary));
