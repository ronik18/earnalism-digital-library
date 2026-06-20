const fs = require("node:fs");
const path = require("node:path");
const { expect, test } = require("playwright/test");

const FRONTEND_URL = process.env.EARNALISM_FRONTEND_URL || "https://theearnalism.com";
const API_URL = (process.env.EARNALISM_API_URL || "https://api.theearnalism.com/api").replace(/\/$/, "");
const EVIDENCE_DIR = path.resolve("output/real-user-ux/evidence");

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

async function openJourneyPage(page, route, name) {
  const response = await page.goto(route, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 25_000 }).catch(() => {});
  await expect(page.locator("body")).toBeVisible();
  await capture(page, name);
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
  const booksResponse = await request.get(`${API_URL}/books`);
  expect(booksResponse.status()).toBe(200);
  const books = await booksResponse.json();
  expect(Array.isArray(books)).toBe(true);
  expect(books.map((book) => book.slug)).toEqual(["dracula"]);

  const bookResponse = await request.get(`${API_URL}/books/dracula`);
  expect(bookResponse.status()).toBe(200);
  const book = await bookResponse.json();
  expect(book.slug).toBe("dracula");
  expect(book.title).toBe("Dracula");
  expect(book.author).toBe("Bram Stoker");
  expect(book.audio_enabled || book.audiobook_enabled || false).toBeFalsy();
  expect(Array.isArray(book.chapters)).toBe(true);
  expect(book.chapters).toHaveLength(27);

  const manifestResponse = await request.get(`${API_URL}/reader/book/dracula/manifest`);
  expect(manifestResponse.status()).toBe(200);
  const manifest = await manifestResponse.json();
  expect(manifest.book?.slug || manifest.slug || manifest.bookSlug).toBeTruthy();
  expect(manifest.chapters).toHaveLength(27);
  expect(manifest.chapters[0]?.is_preview || manifest.chapters[0]?.is_free_preview).toBeTruthy();
  expect(manifest.audio?.enabled || manifest.book?.audiobook_enabled || false).toBeFalsy();
}

test.describe("Earnalism real-user UX video audit", () => {
  test.beforeEach(async ({ context }) => {
    await context.clearCookies();
  });

  test("backend catalog truth gate matches the controlled Dracula launch", async ({ request }) => {
    await assertDraculaBackendTruth(request);
  });

  test("homepage desktop is Dracula-first and truthful", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await openJourneyPage(page, "/", "homepage-desktop");

    const text = await bodyText(page);
    expectTextContains(text, "Begin with Dracula");
    expectTextContains(text, "The Earnalism controlled launch starts with one approved classic");
    expectTextContains(text, "Read Chapter 1 Free");
    expectTextContains(text, "Start Dracula");
    expectTextContains(text, "Get 7-Day Reading Pass");
    expectTextContains(text, "Live controlled release");
    expectTextContains(text, "Audio not available yet");
    expectNoBroadCatalogClaims(text);
    await expectPipelineLocatorOnly(page.getByTestId("pipeline-kshudhita-pashan"), "Kshudhita Pashan");
  });

  test("homepage mobile keeps Dracula above the fold and pipeline titles gated", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openJourneyPage(page, "/", "homepage-mobile");

    const text = await bodyText(page);
    expectTextContains(text, "Begin with Dracula");
    expectTextContains(text, "Read Chapter 1 Free");
    expectTextContains(text, "Start Dracula");
    expectTextContains(text, "Get 7-Day Reading Pass");
    expectNoBroadCatalogClaims(text);
    await expectPipelineLocatorOnly(page.getByTestId("pipeline-kshudhita-pashan"), "Kshudhita Pashan");
  });

  test("carousel and featured shelves show Dracula live while future rooms stay gated", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 900 });
    await openJourneyPage(page, "/", "carousel-featured-dracula-section");

    await expect(page.getByTestId("controlled-carousel-section")).toContainText("One live room");
    await expect(page.getByTestId("controlled-carousel-section")).toContainText("Dracula by Bram Stoker");
    await expect(page.getByTestId("controlled-carousel-section")).toContainText("Read Chapter 1 Free");
    await expect(page.getByTestId("dracula-shelves")).toContainText("Dracula is the only open reading room");
    await expect(page.getByTestId("audiobook-unavailable")).toContainText("Audio is being prepared through QA");
    await expectPipelineLocatorOnly(page.getByTestId("pipeline-card-frankenstein"), "Frankenstein");
    await expectPipelineLocatorOnly(page.getByTestId("pipeline-card-sherlock-holmes"), "Sherlock Holmes");
  });

  test("library desktop shows Dracula as the only live controlled release", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await openJourneyPage(page, "/library", "library-desktop");

    const text = await bodyText(page);
    expectTextContains(text, "Live Controlled Release");
    expectTextContains(text, "Dracula is the only live approved core reading release today");
    expectTextContains(text, "Coming Through the Rights-Safe Pipeline");
    expectTextContains(text, "These books are not live products yet. They have Notify Me CTAs only.");
    expectTextContains(text, "Dracula only");
    expectNoBroadCatalogClaims(text);
    await expectPipelineLocatorOnly(page.getByTestId("library-bengali-gothic-pipeline"), "Kshudhita Pashan");
    await expectPipelineLocatorOnly(page.getByTestId("book-card-frankenstein"), "Frankenstein");
    expect(text.toLowerCase()).not.toContain("listen now");
  });

  test("library mobile keeps unapproved titles notify-only", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openJourneyPage(page, "/library", "library-mobile");

    const text = await bodyText(page);
    expectTextContains(text, "Live Controlled Release");
    expectTextContains(text, "Dracula only");
    expectTextContains(text, "Notify Me");
    await expectPipelineLocatorOnly(page.getByTestId("library-bengali-gothic-pipeline"), "Kshudhita Pashan");
    await expectPipelineLocatorOnly(page.getByTestId("book-card-sultanas-dream"), "Sultana's Dream");
  });

  test("Dracula book page exposes rights, source, preview, and reading pass CTAs", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 950 });
    await openJourneyPage(page, "/book/dracula", "dracula-book-page");

    const text = await bodyText(page);
    expectTextContains(text, "Dracula");
    expectTextContains(text, "by Bram Stoker");
    expectTextContains(text, "27 chapters");
    expectTextContains(text, "Project Gutenberg eBook #345");
    expectTextContains(text, "Approved Tier A core reading candidate");
    expectTextContains(text, "Audio: Not available yet");
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
    expect(text).toContain("sales@reoenterprise.org");
    expectNoBroadCatalogClaims(text);
  });

  test("removed demo route does not serve the generic Earnalism shell", async ({ page }) => {
    const response = await openJourneyPage(page, "/product/patterned-wrap-dress", "removed-demo-route-canary");
    expect([404, 410]).toContain(response?.status());

    const text = await bodyText(page);
    expect(text).not.toContain("Begin with Dracula");
    expect(text).not.toContain("The Earnalism controlled launch starts with one approved classic");
    expect(text).not.toContain("A quieter bookstore");

    const robots = response?.headers()["x-robots-tag"] || "";
    expect(robots).toContain("noindex");
    expect(robots).toContain("nofollow");
    expect(robots).toContain("noarchive");
  });
});
