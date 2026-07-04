const fs = require("node:fs");
const path = require("node:path");
const { expect, test } = require("playwright/test");

const FRONTEND_URL = process.env.EARNALISM_FRONTEND_URL || "https://theearnalism.com";
const API_URL = (process.env.EARNALISM_API_URL || "https://api.theearnalism.com/api").replace(/\/$/, "");
const API_ORIGIN = new URL(API_URL).origin;
const EVIDENCE_DIR = path.resolve("output/real-user-ux/evidence");
const ENVIRONMENT_PATH = path.join(EVIDENCE_DIR, "environment.json");
const NETWORK_SUMMARY_PATH = path.join(EVIDENCE_DIR, "network-console-summary.json");

const FORBIDDEN_BROAD_COPY = [
  "A quieter bookstore for readers who linger",
  "Preview every book before you pay",
  "Discover thoughtful books across",
];

const OLD_PACK_NAMES = [
  "Afternoon Pause",
  "An Evening In",
  "Long Weekend",
];

const PIPELINE_FORBIDDEN_CTAS = [
  "Start Reading",
  "Read Preview",
  "Listen Now",
];

const pageAuditSummaries = [];

function ensureEvidenceDir() {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
}

function slugify(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

async function capture(page, name) {
  ensureEvidenceDir();
  await page.screenshot({
    path: path.join(EVIDENCE_DIR, `${slugify(name)}.png`),
    fullPage: true,
  });
}

function writeJson(filePath, value) {
  ensureEvidenceDir();
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

function isCriticalApiUrl(url) {
  return [
    `${API_URL}/books`,
    `${API_URL}/books/dracula`,
    `${API_URL}/reader/book/dracula/manifest`,
  ].some((critical) => url === critical || url.startsWith(`${critical}?`));
}

function isPaymentProviderOrChargeUrl(url) {
  const lowered = url.toLowerCase();
  return lowered.includes("checkout.razorpay.com")
    || lowered.includes("api.razorpay.com")
    || lowered.includes("/api/payments/topup")
    || lowered.includes("/api/payments/verify")
    || lowered.includes("/api/payments/_simulate");
}

function isAudiobookEndpoint(url) {
  return /\/api\/reader\/book\/[^/]+\/audiobook(?:\/|$|\?)/.test(url);
}

function installPageAudit(page, journey) {
  const summary = {
    journey,
    console_errors: [],
    page_errors: [],
    failed_requests: [],
    server_errors: [],
    critical_api_failures: [],
    payment_provider_or_charge_calls: [],
    audiobook_endpoint_200s: [],
  };
  pageAuditSummaries.push(summary);

  page.on("console", (message) => {
    if (message.type() !== "error") return;
    summary.console_errors.push({
      text: message.text(),
      location: message.location(),
    });
  });

  page.on("pageerror", (error) => {
    summary.page_errors.push({
      message: error.message,
      stack: error.stack || "",
    });
  });

  page.on("requestfailed", (request) => {
    summary.failed_requests.push({
      url: request.url(),
      method: request.method(),
      failure: request.failure()?.errorText || "",
    });
  });

  page.on("response", (response) => {
    const url = response.url();
    const status = response.status();
    if (status >= 500) {
      summary.server_errors.push({ url, status });
    }
    if (isCriticalApiUrl(url) && status >= 400) {
      summary.critical_api_failures.push({ url, status });
    }
    if (isPaymentProviderOrChargeUrl(url)) {
      summary.payment_provider_or_charge_calls.push({ url, status });
    }
    if (isAudiobookEndpoint(url) && status === 200) {
      summary.audiobook_endpoint_200s.push({ url, status });
    }
  });

  return summary;
}

function assertPageAuditClean(summary) {
  writeJson(NETWORK_SUMMARY_PATH, {
    generated_at: new Date().toISOString(),
    frontend_url: FRONTEND_URL,
    api_url: API_URL,
    journeys: pageAuditSummaries,
  });
  expect(summary.page_errors, `${summary.journey} page errors`).toEqual([]);
  expect(summary.server_errors, `${summary.journey} 5xx responses`).toEqual([]);
  expect(summary.critical_api_failures, `${summary.journey} critical API failures`).toEqual([]);
  expect(summary.payment_provider_or_charge_calls, `${summary.journey} payment provider/charge calls`).toEqual([]);
  expect(summary.audiobook_endpoint_200s, `${summary.journey} audiobook endpoint returned 200`).toEqual([]);
}

async function openJourneyPage(page, route, name) {
  const audit = installPageAudit(page, name);
  const response = await page.goto(route, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 25_000 }).catch(() => {});
  await expect(page.locator("body")).toBeVisible();
  await capture(page, name);
  assertPageAuditClean(audit);
  return response;
}

async function bodyText(page) {
  return page.locator("body").innerText();
}

function segmentAround(text, needle, radius = 650) {
  const index = text.toLowerCase().indexOf(needle.toLowerCase());
  if (index < 0) return "";
  return text.slice(Math.max(0, index - radius), index + needle.length + radius);
}

function expectNoBroadCatalogClaims(text) {
  const normalized = text.toLowerCase();
  for (const phrase of FORBIDDEN_BROAD_COPY) {
    expect(normalized, `Unexpected broad catalog claim: ${phrase}`).not.toContain(phrase.toLowerCase());
  }
}

function expectNoOldPackNames(text) {
  const normalized = text.toLowerCase();
  for (const phrase of OLD_PACK_NAMES) {
    expect(normalized, `Old pricing pack name still visible: ${phrase}`).not.toContain(phrase.toLowerCase());
  }
}

function expectTextContains(text, phrase) {
  expect(text.toLowerCase()).toContain(phrase.toLowerCase());
}

function expectPipelineOnlyBlock(text, label) {
  const block = segmentAround(text, label);
  expect(block, `${label} should be present as a pipeline title`).toBeTruthy();
  expect(block).toMatch(/Notify Me|Coming Soon|Reading Circle/i);
  const normalized = block.toLowerCase();
  for (const cta of PIPELINE_FORBIDDEN_CTAS) {
    expect(normalized, `${label} must not expose ${cta}`).not.toContain(cta.toLowerCase());
  }
}

async function expectPipelineLocatorOnly(locator, label) {
  await expect(locator, `${label} pipeline block should be visible`).toBeVisible();
  const text = await locator.innerText();
  expect(text, `${label} should expose a pipeline CTA`).toMatch(/Notify Me|Coming Soon|Reading Circle/i);
  const normalized = text.toLowerCase();
  for (const cta of PIPELINE_FORBIDDEN_CTAS) {
    expect(normalized, `${label} must not expose ${cta}`).not.toContain(cta.toLowerCase());
  }
}

async function assertDraculaBackendTruth(request) {
  const statusResponse = await request.get(`${API_URL}/controlled-launch/status`);
  expect(statusResponse.status()).toBe(200);
  const status = await statusResponse.json();
  const controlledLiveSlugs = Array.isArray(status.live_approved_slugs) ? status.live_approved_slugs : ["dracula"];
  expect(controlledLiveSlugs[0]).toBe("dracula");

  const booksResponse = await request.get(`${API_URL}/books`);
  expect(booksResponse.status()).toBe(200);
  const books = await booksResponse.json();
  expect(Array.isArray(books)).toBe(true);
  const bookSlugs = books.map((book) => book.slug);
  expect(bookSlugs[0]).toBe("dracula");
  expect(bookSlugs).toEqual(expect.arrayContaining(controlledLiveSlugs));

  const bookResponse = await request.get(`${API_URL}/books/dracula`);
  expect(bookResponse.status()).toBe(200);
  const book = await bookResponse.json();
  expect(book.slug).toBe("dracula");
  expect(book.title).toBe("Dracula");
  expect(book.author).toBe("Bram Stoker");
  expect(book.publication_status).toBe("LIVE_APPROVED");
  expect(book.reader_enabled).toBe(true);
  expect(book.preview_enabled).toBe(true);
  expect(book.reader_url).toBe("/reader/dracula");
  expect(book.preview_url).toBe("/reader/dracula");
  expect(book.audio_enabled).toBe(false);
  expect(book.audiobook_enabled).toBe(false);
  expect(book.audiobook || null).toBeNull();
  expect(Object.keys(book.audiobook_assets || {})).toHaveLength(0);
  expect(book).not.toHaveProperty("source_hash");
  expect(book).not.toHaveProperty("content_hash");
  expect(book).not.toHaveProperty("provenance_hash");
  expect(Array.isArray(book.chapters)).toBe(true);
  expect(book.chapters).toHaveLength(27);

  const manifestResponse = await request.get(`${API_URL}/reader/book/dracula/manifest`);
  expect(manifestResponse.status()).toBe(200);
  const manifest = await manifestResponse.json();
  expect(manifest.book?.slug || manifest.slug || manifest.bookSlug).toBeTruthy();
  expect(manifest.chapters).toHaveLength(27);
  expect(manifest.chapters[0]?.is_preview || manifest.chapters[0]?.is_free_preview).toBeTruthy();
  expect(manifest.audio?.enabled || manifest.book?.audiobook_enabled || false).toBeFalsy();

  const audiobookResponse = await request.get(`${API_URL}/reader/book/dracula/audiobook`);
  expect(audiobookResponse.status()).toBe(404);
}

test.describe("Earnalism real-user UX video audit", () => {
  test.beforeEach(async ({ context }) => {
    await context.clearCookies();
  });

  test("live environment stamp captures audited production context", async ({ request, browserName }, testInfo) => {
    const healthResponse = await request.get(`${API_ORIGIN}/healthz`);
    let healthBody = null;
    try {
      healthBody = await healthResponse.json();
    } catch {
      healthBody = { raw: await healthResponse.text() };
    }

    writeJson(ENVIRONMENT_PATH, {
      timestamp: new Date().toISOString(),
      frontend_url: FRONTEND_URL,
      api_url: API_URL,
      healthz_url: `${API_ORIGIN}/healthz`,
      healthz_status: healthResponse.status(),
      healthz: healthBody,
      browser_name: browserName,
      project_name: testInfo.project.name,
      viewports: {
        desktop: { width: 1440, height: 1000 },
        mobile: { width: 390, height: 844 },
        reader: { width: 1280, height: 900 },
      },
    });

    expect(healthResponse.status()).toBe(200);
    expect(healthBody?.status || healthBody?.ok).toBeTruthy();
  });

  test("backend catalog truth gate matches the controlled Dracula launch", async ({ request }) => {
    await assertDraculaBackendTruth(request);
  });

  test("homepage desktop is Dracula-first and truthful", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await openJourneyPage(page, "/", "homepage-desktop");

    const text = await bodyText(page);
    expectTextContains(text, "Step into the classics");
    expectTextContains(text, "Stay with the story");
    expectTextContains(text, "The Earnalism launch begins with one approved classic");
    expectTextContains(text, "Read Chapter 1 Free");
    expectTextContains(text, "Start Dracula");
    expectTextContains(text, "Get 7-Day Reading Pass");
    expectTextContains(text, "Rights-safe & ethical");
    expectTextContains(text, "Coming Through the Rights-Safe Pipeline");
    expectNoBroadCatalogClaims(text);
    await expectPipelineLocatorOnly(page.getByTestId("pipeline-card-kshudhita-pashan"), "Kshudhita Pashan");
  });

  test("homepage mobile keeps Dracula above the fold and pipeline titles gated", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openJourneyPage(page, "/", "homepage-mobile");

    const text = await bodyText(page);
    expectTextContains(text, "Step into the classics");
    expectTextContains(text, "Read Chapter 1 Free");
    expectTextContains(text, "Start Dracula");
    expectTextContains(text, "Get 7-Day Reading Pass");
    expectNoBroadCatalogClaims(text);
    await expectPipelineLocatorOnly(page.getByTestId("pipeline-card-kshudhita-pashan"), "Kshudhita Pashan");
  });

  test("Shelf-II slideshow keeps future rooms gated", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 900 });
    await openJourneyPage(page, "/", "shelf-two-pipeline-section");

    await expect(page.getByTestId("bengali-gothic-pipeline-shelf")).toContainText("2 curated pages");
    await expectPipelineLocatorOnly(page.getByTestId("pipeline-card-kshudhita-pashan"), "Kshudhita Pashan");
    await expectPipelineLocatorOnly(page.getByTestId("pipeline-card-sherlock-holmes"), "Sherlock Holmes");
    await expectPipelineLocatorOnly(page.getByTestId("pipeline-card-sultanas-dream"), "Sultana's Dream");
  });

  test("library desktop shows controlled releases and gated pipeline", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await openJourneyPage(page, "/library", "library-desktop");

    const text = await bodyText(page);
    expectTextContains(text, "Live Controlled Releases");
    expectTextContains(text, "Dracula");
    expectTextContains(text, "Coming Through the Rights-Safe Pipeline");
    expectTextContains(text, "Reader-only public-domain shelf");
    expectNoBroadCatalogClaims(text);
    await expectPipelineLocatorOnly(page.getByTestId("library-bengali-gothic-pipeline"), "Kshudhita Pashan");
  });

  test("library mobile keeps unapproved titles notify-only", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openJourneyPage(page, "/library", "library-mobile");

    const text = await bodyText(page);
    expectTextContains(text, "Live Controlled Releases");
    expectTextContains(text, "Notify Me");
    await expectPipelineLocatorOnly(page.getByTestId("library-bengali-gothic-pipeline"), "Kshudhita Pashan");
  });

  test("Dracula book page exposes rights, source, preview, and reading pass CTAs", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 950 });
    await openJourneyPage(page, "/book/dracula", "dracula-book-page");

    const text = await bodyText(page);
    expectTextContains(text, "Dracula");
    expectTextContains(text, "by Bram Stoker");
    expectTextContains(text, "27 chapters");
    expectTextContains(text, "Project Gutenberg eBook #345");
    expectTextContains(text, "Approved classic reading release");
    expectTextContains(text, "Audiobook experience in private review");
    expectTextContains(text, "Read Chapter 1 Free");
    expectTextContains(text, "Get Reading Pass");
  });

  test("Dracula reader page loads manifest-backed preview without audiobook controls", async ({ page, request }) => {
    await assertDraculaBackendTruth(request);
    await page.setViewportSize({ width: 1280, height: 900 });
    await openJourneyPage(page, "/reader/dracula", "dracula-reader-page");

    const text = await bodyText(page);
    expectTextContains(text, "Dracula");
    expect(text).toMatch(/Ch\. 1 of 27|Chapter 1|Page 1/i);
    await expect(page.getByTestId("generated-audiobook")).toHaveCount(0);
    expect(text.toLowerCase()).not.toContain("listen now");
    expect(text.toLowerCase()).not.toContain("generated audiobook");
  });

  test("pricing page uses Dracula-first reading-time packs and trust copy", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 950 });
    await openJourneyPage(page, "/pricing?source=ux_video_audit&book=dracula", "pricing-page");

    const text = await bodyText(page);
    expectTextContains(text, "Choose your reading time");
    expectTextContains(text, "Start with Chapter 1 free");
    expectTextContains(text, "The First Chapter");
    expectTextContains(text, "₹49");
    expectTextContains(text, "The Quiet Hour");
    expectTextContains(text, "₹89");
    expectTextContains(text, "Best first choice");
    expectTextContains(text, "The Deep Reading Pass");
    expectTextContains(text, "₹239");
    expectTextContains(text, "The Reader’s Reserve");
    expectTextContains(text, "₹499");
    expectTextContains(text, "Best value");
    expectTextContains(text, "Why reading time?");
    expectTextContains(text, "Secure payment by Razorpay");
    expectTextContains(text, "sales@reoenterprise.org");
    expectNoOldPackNames(text);
  });

  test("journal and contact pages are reachable without demo/catalog leakage", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await openJourneyPage(page, "/journal", "journal-page");
    let text = await bodyText(page);
    expect(text).toContain("The Journal");
    expectNoBroadCatalogClaims(text);

    await openJourneyPage(page, "/contact", "contact-page");
    text = await bodyText(page);
    expect(text).toContain("Write to us");
    expect(text).toContain("sales@reoenterprise.in");
    expectNoBroadCatalogClaims(text);
  });

  test("removed demo route does not serve the generic Earnalism shell", async ({ page }) => {
    const response = await openJourneyPage(page, "/product/patterned-wrap-dress", "removed-demo-route-canary");
    expect([404, 410]).toContain(response?.status());

    const text = await bodyText(page);
    expect(text).not.toContain("Step into the classics");
    expect(text).not.toContain("The Earnalism launch begins with one approved classic");
    expect(text).not.toContain("A quieter bookstore");

    const robots = response?.headers()["x-robots-tag"] || "";
    expect(robots).toContain("noindex");
    expect(robots).toContain("nofollow");
    expect(robots).toContain("noarchive");
  });
});
