import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const baseUrl = (process.env.E2E_BASE_URL || "https://theearnalism.com").replace(/\/$/, "");
const apiUrl = (process.env.E2E_API_URL || "https://api.theearnalism.com").replace(/\/$/, "");
const outputDir = path.resolve(process.env.E2E_OUTPUT_DIR || "test-results/regression");
const isLocalFrontend = /^https?:\/\/(?:127\.0\.0\.1|localhost|\[::1\])/i.test(baseUrl);
const liveApprovedSlug = "dracula";
const expectedPipelineSlugs = [
  "frankenstein",
  "sherlock-holmes",
  "sultanas-dream",
];
const draculaFixtureBook = {
  id: "regression-dracula",
  slug: liveApprovedSlug,
  title: "Dracula",
  subtitle: "",
  author: "Bram Stoker",
  category_slug: "gothic-fiction",
  short_description: "An approved controlled launch classic.",
  description: "Dracula is the only live approved core reading release in this regression fixture.",
  cover_image_url: "",
  thumbnail_url: "",
  estimated_reading_time: "8h",
  publication_status: "LIVE_APPROVED",
  launch_status: "LIVE_APPROVED",
  reader_enabled: true,
  preview_enabled: true,
  audio_enabled: false,
  audiobook_enabled: false,
  reader_url: "/reader/dracula",
  preview_url: "/reader/dracula",
  audio_url: "",
  chapters: [
    {
      id: "chapter-1",
      title: "Chapter 1",
      order: 1,
      is_preview: true,
      content_version: "regression-chapter-1",
      word_count: 46,
      reading_minutes: 1,
      processing_status: "ready",
      content_url: "/api/reader/chapter/dracula/chapter-1?v=regression-chapter-1",
    },
  ],
};
const draculaManifestFixture = {
  book: draculaFixtureBook,
  chapters: draculaFixtureBook.chapters,
  audio: {
    enabled: false,
    asset_slug: "",
    provider: "",
    voice: "",
    assets: {},
    url: "",
    size: 0,
    duration_ms: 0,
    version: "regression-audio-disabled",
    updated_at: "",
  },
  access: {
    admin_preview: false,
    preview_chapter_ids: ["chapter-1"],
    wallet_seconds: 0,
  },
  version: "regression-manifest",
  generated_at: "2026-06-20T00:00:00Z",
};
const chapterFixture = {
  id: "chapter-1",
  title: "Chapter 1",
  order: 1,
  is_preview: true,
  content: "<p>Jonathan Harker opened his journal and began the journey toward Castle Dracula.</p>",
  locked: false,
};
const paymentPacksFixture = [
  { id: "first_chapter", label: "The First Chapter", minutes: 30, amount_paise: 4900 },
  { id: "quiet_hour", label: "The Quiet Hour", minutes: 60, amount_paise: 8900 },
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function sameOriginHeaders() {
  return {
    "access-control-allow-origin": baseUrl,
    "access-control-allow-credentials": "true",
    "vary": "Origin",
  };
}

function localFixtureFor(request) {
  const url = new URL(request.url());
  const pathname = url.pathname;
  if (request.method() !== "GET" && (pathname.endsWith("/analytics/event") || pathname.endsWith("/analytics/events"))) {
    return { status: 200, body: { ok: true } };
  }
  if (request.method() !== "GET" && pathname.endsWith("/reader/metrics")) {
    return { status: 200, body: { ok: true, recorded: false } };
  }
  if (request.method() !== "GET") return null;
  if (pathname === "/api/books") return { status: 200, body: [draculaFixtureBook] };
  if (pathname === "/api/books/dracula") return { status: 200, body: draculaFixtureBook };
  if (pathname === "/api/books/kshudhita-pashan") return { status: 404, body: { detail: "Book not found" } };
  if (pathname === "/api/reader/book/dracula/manifest") return { status: 200, body: draculaManifestFixture };
  if (pathname === "/api/reader/book/kshudhita-pashan/manifest") return { status: 404, body: { detail: "Book not found" } };
  if (pathname === "/api/reader/book/dracula/audiobook") return { status: 404, body: { detail: "Audiobook asset not found" } };
  if (pathname === "/api/reader/book/kshudhita-pashan/audiobook") return { status: 404, body: { detail: "Audiobook asset not found" } };
  if (pathname === "/api/reader/chapter/dracula/chapter-1") return { status: 200, body: chapterFixture };
  if (pathname === "/api/payments/packs") return { status: 200, body: paymentPacksFixture };
  if (pathname === "/api/payments/config") return { status: 200, body: { provider: "razorpay", test_mode: true } };
  return null;
}

async function installApiProxy(page) {
  if (!isLocalFrontend) return;
  await page.route(`${apiUrl}/api/**`, async (route) => {
    try {
      const request = route.request();
      const fixture = localFixtureFor(request);
      if (fixture) {
        await route.fulfill({
          status: fixture.status,
          body: JSON.stringify(fixture.body),
          headers: {
            "content-type": "application/json",
            ...sameOriginHeaders(),
          },
        });
        return;
      }
      const response = await fetch(request.url(), {
        method: request.method(),
        headers: {
          accept: request.headers().accept || "application/json",
          "content-type": request.headers()["content-type"] || "application/json",
        },
        body: request.method() === "GET" || request.method() === "HEAD"
          ? undefined
          : request.postData(),
      });
      const body = await response.text();
      await route.fulfill({
        status: response.status,
        body,
        headers: {
          "content-type": response.headers.get("content-type") || "application/json",
          ...sameOriginHeaders(),
        },
      });
    } catch (error) {
      await route.fulfill({
        status: 502,
        body: JSON.stringify({ error: error.message }),
        headers: {
          "content-type": "application/json",
          ...sameOriginHeaders(),
        },
      });
    }
  });
}

async function snapshot(page, name) {
  const file = path.join(outputDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function gotoAppPath(page, appPath) {
  if (!isLocalFrontend) {
    await page.goto(`${baseUrl}${appPath}`, { waitUntil: "domcontentloaded" });
    return;
  }
  await page.evaluate((nextPath) => {
    window.history.pushState({}, "", nextPath);
    window.dispatchEvent(new PopStateEvent("popstate", { state: {} }));
  }, appPath);
}

async function main() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 }, deviceScaleFactor: 1 });
  const consoleIssues = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleIssues.push(`${message.type()}: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) => consoleIssues.push(`pageerror: ${error.message}`));
  await installApiProxy(page);

  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="hero-dracula-card"]', { timeout: 30000 });
  await page.waitForTimeout(900);
  const home = await page.evaluate(() => {
    const pipelineCards = [...document.querySelectorAll('[data-testid^="pipeline-card-"]')]
      .map((card) => card.getAttribute("data-testid")?.replace(/^pipeline-card-/, ""))
      .filter(Boolean);
    const notifyLinks = [...document.querySelectorAll('[data-testid^="pipeline-notify-"]')]
      .map((link) => link.getAttribute("href"));
    return {
      viewportWidth: window.innerWidth,
      hasHeroCard: Boolean(document.querySelector('[data-testid="hero-dracula-card"]')),
      hasPremiumHero: Boolean(document.querySelector('[data-testid="premium-landing-hero"]')),
      hasReadingModel: Boolean(document.querySelector('[data-testid="dracula-reading-model"]')),
      hasReadingModelPassCta: Boolean(document.querySelector('[data-testid="reading-model-pass-cta"]')),
      hasKshudhitaPipeline: Boolean(document.querySelector('[data-testid="pipeline-kshudhita-pashan"]')),
      hasKshudhitaCoverStack: Boolean(document.querySelector('[data-testid="pipeline-kshudhita-cover-stack"]')),
      hasPipelineShelf: Boolean(document.querySelector('[data-testid="pipeline-books"]')),
      hasReadingCircle: Boolean(document.querySelector('[data-testid="reading-circle-section"]')),
      headline: document.querySelector('[data-testid="hero-headline"]')?.textContent?.replace(/\s+/g, " ").trim(),
      heroReadHref: document.querySelector('[data-testid="hero-cta-read"]')?.getAttribute("href"),
      heroStartHref: document.querySelector('[data-testid="hero-cta-start-dracula"]')?.getAttribute("href"),
      heroPassHref: document.querySelector('[data-testid="hero-cta-pricing"]')?.getAttribute("href"),
      readingModelPassHref: document.querySelector('[data-testid="reading-model-pass-cta"]')?.getAttribute("href"),
      kshudhitaNotifyHref: document.querySelector('[data-testid="pipeline-kshudhita-notify"]')?.getAttribute("href"),
      pipelineCards,
      notifyLinks,
      staleCarouselCount: document.querySelectorAll('[data-testid="controlled-carousel-section"]').length,
      staleAudioUnavailableCount: document.querySelectorAll('[data-testid="audiobook-unavailable"]').length,
      legacyLiveCoverCount: document.querySelectorAll('[data-testid^="live-cover-preview-"]').length,
      legacyCategoryCardCount: document.querySelectorAll('[data-testid^="category-card-"]').length,
      legacyBroadReaderLinks: [...document.querySelectorAll('a[href^="/reader/"]')]
        .map((link) => link.getAttribute("href"))
        .filter((href) => href !== "/reader/dracula"),
      heroCurrentPayCount: document.querySelectorAll('[data-testid="hero-current-pay"]').length,
      railPrimaryPreviewCount: document.querySelectorAll('[data-testid="live-cover-primary-preview"]').length,
      railPrimaryPaymentCount: document.querySelectorAll('[data-testid="live-cover-primary-payment"]').length,
      railLibraryCount: document.querySelectorAll('[data-testid="live-cover-library"]').length,
    };
  });
  assert(home.hasHeroCard, "Dracula hero card is missing");
  assert(home.hasPremiumHero, "premium Dracula hero is missing");
  assert(home.hasReadingModel, "reading-time revenue model section is missing");
  assert(home.hasReadingModelPassCta, "reading-time pass CTA is missing");
  assert(home.hasKshudhitaPipeline, "Kshudhita pipeline feature is missing");
  assert(home.hasKshudhitaCoverStack, "Kshudhita pipeline cover stack is missing");
  assert(home.hasPipelineShelf, "pipeline shelf is missing");
  assert(home.hasReadingCircle, "reading circle section is missing");
  assert(/Begin with Dracula/i.test(home.headline || ""), `hero headline is not Dracula-first: ${home.headline}`);
  assert(home.heroReadHref === "/reader/dracula", `hero free-read CTA should open Dracula reader, got ${home.heroReadHref}`);
  assert(home.heroStartHref === "/book/dracula", `hero Start Dracula CTA should open Dracula detail, got ${home.heroStartHref}`);
  assert(home.heroPassHref === "/pricing?source=homepage_hero&book=dracula", `hero reading pass CTA mismatch: ${home.heroPassHref}`);
  assert(home.readingModelPassHref === "/pricing?source=homepage_reading_model&book=dracula", `reading model pass CTA mismatch: ${home.readingModelPassHref}`);
  assert(home.kshudhitaNotifyHref === "/contact?interest=kshudhita-pashan", `Kshudhita must remain notify-only, got ${home.kshudhitaNotifyHref}`);
  assert(
    JSON.stringify(home.pipelineCards) === JSON.stringify(expectedPipelineSlugs),
    `pipeline cards mismatch: ${JSON.stringify(home.pipelineCards)}`,
  );
  assert(home.notifyLinks.length === 0, `mini pipeline cards must not expose reader/payment CTAs: ${JSON.stringify(home.notifyLinks)}`);
  assert(home.staleCarouselCount === 0, "retired controlled launch carousel should not render in the luxury homepage");
  assert(home.staleAudioUnavailableCount === 0, "stale audiobook unavailable note should not render");
  assert(home.legacyLiveCoverCount === 0, "retired live-cover preview cards should not render in Dracula-first launch");
  assert(home.legacyCategoryCardCount === 0, "retired broad category cards should not render in Dracula-first launch");
  assert(home.legacyBroadReaderLinks.length === 0, `non-Dracula reader links leaked: ${JSON.stringify(home.legacyBroadReaderLinks)}`);
  assert(home.heroCurrentPayCount === 0, "hero Preview & Pay CTA should not render");
  assert(home.railPrimaryPreviewCount === 0, "rail-level Read Preview CTA should not render");
  assert(home.railPrimaryPaymentCount === 0, "rail-level Preview & Pay CTA should not render");
  assert(home.railLibraryCount === 0, "rail-level All books CTA should not render");
  const firstSlug = liveApprovedSlug;
  const homeScreenshot = await snapshot(page, "home");

  await gotoAppPath(page, "/library");
  await page.waitForSelector('[data-testid="shelf-live-controlled-release"]', { timeout: 30000 });
  const library = await page.evaluate(() => ({
    hasLiveShelf: Boolean(document.querySelector('[data-testid="shelf-live-controlled-release"]')),
    hasPipelineShelf: Boolean(document.querySelector('[data-testid="shelf-pipeline"]')),
    hasAudioShelf: Boolean(document.querySelector('[data-testid="shelf-audiobooks"]')),
    previewLinks: [...document.querySelectorAll('[data-testid="library-dracula-preview"], [data-testid^="card-preview-"], a[href^="/reader/"]')]
      .slice(0, 20)
      .map((link) => link.getAttribute("href")),
    nonDraculaReaderLinks: [...document.querySelectorAll('a[href^="/reader/"]')]
      .map((link) => link.getAttribute("href"))
      .filter((href) => href !== "/reader/dracula"),
    pipelineStatuses: [...document.querySelectorAll('[data-testid^="book-card-"]')]
      .map((card) => card.getAttribute("data-launch-status")),
  }));
  assert(library.hasLiveShelf, "library did not render the live controlled shelf");
  assert(library.hasPipelineShelf, "library did not render the pipeline shelf");
  assert(library.hasAudioShelf, "library did not render the audiobook status shelf");
  assert(library.previewLinks.includes("/reader/dracula"), "library has no Dracula reader preview CTA");
  assert(library.nonDraculaReaderLinks.length === 0, `library leaked non-Dracula reader links: ${JSON.stringify(library.nonDraculaReaderLinks)}`);
  assert(library.pipelineStatuses.every((status) => status === "COMING_SOON_PIPELINE"), `pipeline cards are not notify-only: ${JSON.stringify(library.pipelineStatuses)}`);

  await gotoAppPath(page, `/book/${firstSlug}`);
  await page.waitForSelector('[data-testid="book-page"]', { timeout: 30000 });
  const bookDetail = await page.evaluate((slug) => ({
    topPreviewHref: document.querySelector('[data-testid="read-preview"]')?.getAttribute("href"),
    topStartHref: document.querySelector('[data-testid="start-reading"]')?.getAttribute("href"),
    topPassHref: document.querySelector('[data-testid="book-reading-pass"]')?.getAttribute("href"),
    requestAccessCount: document.querySelectorAll('[data-testid="request-access"]').length,
    topBuyReadingTimeCount: document.querySelectorAll('[data-testid="buy-reading-time"]').length,
    previewHref: document.querySelector('[data-testid="bottom-read-preview"]')?.getAttribute("href"),
    paymentHref: document.querySelector('[data-testid="bottom-buy-reading-time"]')?.getAttribute("href"),
    hasPaymentSection: Boolean(document.querySelector('[data-testid="preview-payment-section"]')),
    rawBodyIncludesRightsMetadata: document.body.innerText.includes("rights_metadata"),
    slug,
  }), firstSlug);
  if (bookDetail.topPreviewHref) {
    assert(bookDetail.topPreviewHref === `/reader/${firstSlug}`, `top preview CTA mismatch: ${bookDetail.topPreviewHref}`);
  }
  assert(
    bookDetail.topStartHref === `/reader/${firstSlug}`,
    `top Start Reading CTA should open Dracula reader, got ${bookDetail.topStartHref}`,
  );
  assert(
    bookDetail.topPassHref === `/pricing?source=book_detail&book=${firstSlug}`,
    `top reading pass CTA should open book-specific pricing, got ${bookDetail.topPassHref}`,
  );
  assert(bookDetail.requestAccessCount === 0, "Request Access CTA should not render on book detail");
  assert(bookDetail.topBuyReadingTimeCount === 0, "top Buy Reading Time CTA should not render on book detail");
  assert(bookDetail.previewHref === `/reader/${firstSlug}`, `book preview CTA mismatch: ${bookDetail.previewHref}`);
  assert(bookDetail.paymentHref?.includes(`book=${firstSlug}`), `payment CTA does not preserve book slug: ${bookDetail.paymentHref}`);
  assert(bookDetail.hasPaymentSection, "book detail payment section missing");
  assert(!bookDetail.rawBodyIncludesRightsMetadata, "internal rights metadata leaked into book page");

  await gotoAppPath(page, `/reader/${firstSlug}`);
  await page.waitForSelector([
    '[data-testid="reader-page"]',
    '[data-testid="reader-locked"]',
    '[data-testid="reader-not-found"]',
    '[data-testid="reader-error"]',
  ].join(", "), { timeout: 30000 });
  const reader = await page.evaluate(() => ({
    unlocked: Boolean(document.querySelector('[data-testid="reader-page"]')),
    locked: Boolean(document.querySelector('[data-testid="reader-locked"]')),
    notFound: Boolean(document.querySelector('[data-testid="reader-not-found"]')),
    error: Boolean(document.querySelector('[data-testid="reader-error"]')),
    text: document.body.innerText.replace(/\s+/g, " ").trim().slice(0, 240),
    hasSecureReader: Boolean(document.querySelector(".secure-reader")),
    hasReaderCanvas: Boolean(document.querySelector(".reader-canvas")),
  }));
  assert(reader.unlocked || reader.locked, `reader route did not render an access state: ${JSON.stringify(reader)}`);
  assert(reader.locked || reader.hasSecureReader || reader.hasReaderCanvas, "reader unlocked without secure reader/canvas");

  await browser.close();
  console.log(JSON.stringify({
    ok: true,
    baseUrl,
    firstSlug,
    pipelineCards: home.pipelineCards.length,
    homeScreenshot,
    consoleIssues: consoleIssues.slice(0, 10),
  }, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
