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
// Batch-1 reader-only releases are intentionally not homepage-promoted.
const expectedPipelineSlugs = [
  "kshudhita-pashan",
  "sherlock-holmes",
  "sultanas-dream",
  "calculus-made-easy",
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
const homeHeroFixture = JSON.parse(
  fs.readFileSync(path.resolve("frontend/src/data/homeCuratedSprint1.json"), "utf8"),
);
const homeHeroFixtureBooks = homeHeroFixture.hero.featured_books;
const expectedHeroCarouselBooks = homeHeroFixture.hero.carousel_books;
const expectedHeroCarouselSlugs = expectedHeroCarouselBooks.map((book) => book.slug);
const expectedHeroActiveSlug = expectedHeroCarouselSlugs[0];
const expectedHeroMeaningfulSlugs = [
  expectedHeroCarouselSlugs.at(-1),
  expectedHeroActiveSlug,
  expectedHeroCarouselSlugs[1],
].filter(Boolean);
const expectedVisibleShelfCount = homeHeroFixture.shelf_collage.groups
  .filter((group) => Array.isArray(group.books) && group.books.length > 0)
  .length;
const expectedApprovedAudioSlugs = homeHeroFixture.shelf_collage.selected_audiobooks
  .filter((book) => book.cover_valid && !book.is_placeholder && !book.is_typographic_only)
  .map((book) => book.slug);
const expectedHeroListeningSlug = expectedApprovedAudioSlugs.find((slug) => (
  slug !== expectedHeroActiveSlug && expectedHeroCarouselSlugs.includes(slug)
)) || expectedApprovedAudioSlugs.find((slug) => slug !== expectedHeroActiveSlug) || expectedApprovedAudioSlugs[0] || null;
const expectedHeroListenLinks = expectedHeroListeningSlug
  ? [`/reader/${expectedHeroListeningSlug}?listen=1`]
  : [];

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
  if (pathname === "/api/home/curated") return { status: 200, body: homeHeroFixture };
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
  await page.waitForSelector('[data-testid="premium-landing-hero"][data-catalog-state="ready"]', { timeout: 30000 });
  await page.waitForSelector('[data-testid="curated-shelf-collage"]', { timeout: 30000 });
  await page.waitForTimeout(900);
  const home = await page.evaluate(() => {
    const pipelineCards = [...document.querySelectorAll('[data-testid^="pipeline-card-"]')]
      .map((card) => card.getAttribute("data-testid")?.replace(/^pipeline-card-/, ""))
      .filter(Boolean);
    const requestUpdateLinks = [...document.querySelectorAll('[data-testid="bengali-gothic-pipeline-shelf"] a[href^="/contact?interest="]')]
      .map((link) => ({
        href: link.getAttribute("href"),
        label: link.textContent?.replace(/\s+/g, " ").trim() || "",
        ariaLabel: link.getAttribute("aria-label") || "",
      }));
    return {
      viewportWidth: window.innerWidth,
      hasHeroCard: Boolean(document.querySelector('[data-testid="hero-dracula-card"]')),
      hasPremiumHero: Boolean(document.querySelector('[data-testid="premium-landing-hero"]')),
      hasCuratedShelfCollage: Boolean(document.querySelector('[data-testid="curated-shelf-collage"]')),
      shelfGroupCount: document.querySelectorAll('[data-testid^="curated-shelf-tile-"]').length,
      selectedListeningCount: document.querySelectorAll('.selected-listening-card').length,
      selectedListeningLinks: [...document.querySelectorAll('.selected-listening-card__cta')]
        .map((link) => link.getAttribute("href") || ""),
      hasBengaliShelf: /Bengali Life & Legacy/i.test(document.querySelector('[data-testid="curated-shelf-collage"]')?.textContent || ""),
      hasGothicShelf: /Gothic & the Uncanny/i.test(document.querySelector('[data-testid="curated-shelf-collage"]')?.textContent || ""),
      hasInternalCollageCopy: /release gate|QA_PASSED|manifest|unapproved audio|browser gates/i.test(
        document.querySelector('[data-testid="curated-shelf-collage"]')?.textContent || "",
      ),
      hasReadingTimePath: Boolean(document.querySelector('[data-testid="reading-time-library-path"]')),
      readingPathPricingHref: document.querySelector('[data-testid="reading-path-pricing-cta"]')?.getAttribute("href"),
      hasKshudhitaPipeline: /Kshudhita Pashan|ক্ষুধিত পাষাণ/i.test(document.querySelector('[data-testid="bengali-gothic-pipeline-shelf"]')?.textContent || ""),
      hasPipelineShelf: Boolean(document.querySelector('[data-testid="bengali-gothic-pipeline-shelf"] .shelf-two-shelf')),
      headline: document.querySelector('[data-testid="hero-headline"]')?.textContent?.replace(/\s+/g, " ").trim(),
      heroLibraryHref: document.querySelector('[data-testid="hero-cta-library"]')?.getAttribute("href"),
      heroAudiobooksHref: document.querySelector('[data-testid="hero-cta-audiobooks"]')?.getAttribute("href"),
      heroCatalogState: document.querySelector('[data-testid="premium-landing-hero"]')?.getAttribute("data-catalog-state"),
      heroVisualSlugs: [...document.querySelectorAll('[data-testid="hero-catalog-visuals"] [data-active="true"][data-book-slug]')]
        .map((card) => card.getAttribute("data-book-slug"))
        .filter(Boolean),
      heroMeaningfulSlugs: [...document.querySelectorAll(
        '[data-testid="hero-catalog-visuals"] [data-position="previous"], [data-testid="hero-catalog-visuals"] [data-position="active"], [data-testid="hero-catalog-visuals"] [data-position="next"]',
      )]
        .map((card) => card.getAttribute("data-book-slug"))
        .filter(Boolean),
      heroVisualCoverAlts: [...document.querySelectorAll('[data-testid="hero-catalog-visuals"] [data-active="true"][data-book-slug] img')]
        .map((image) => image.getAttribute("alt") || ""),
      heroAllVisualSlugs: [...document.querySelectorAll('[data-testid="hero-catalog-visuals"] [data-position][data-book-slug]')]
        .map((card) => card.getAttribute("data-book-slug"))
        .filter(Boolean),
      heroListenLinks: [...document.querySelectorAll('[data-testid="premium-landing-hero"] a[href*="listen=1"]')]
        .map((link) => link.getAttribute("href") || ""),
      hasBengaliClassicsCard: /Bengali Classics/i.test(document.querySelector('[data-testid="curated-action-cards"]')?.textContent || ""),
      hasEnglishClassicsCard: /English Classics/i.test(document.querySelector('[data-testid="curated-action-cards"]')?.textContent || ""),
      hasApprovedAudiobooksCard: /Approved Audiobooks/i.test(document.querySelector('[data-testid="curated-action-cards"]')?.textContent || ""),
      bengaliCardHref: [...document.querySelectorAll('[data-testid="curated-action-cards"] a')]
        .map((link) => link.getAttribute("href") || "")
        .find((href) => href.includes("language=bn")),
      draculaCardHref: [...document.querySelectorAll('[data-testid="curated-action-cards"] a')]
        .map((link) => link.getAttribute("href") || "")
        .find((href) => href === "/reader/dracula"),
      approvedAudioCardLinks: [...document.querySelectorAll('[data-testid="curated-action-cards"] a')]
        .map((link) => link.getAttribute("href") || "")
        .filter((href) => /audio|listen|audiobook/i.test(href)),
      pipelineRequestUpdateLinkCount: requestUpdateLinks.length,
      pipelineCards,
      requestUpdateLinks,
      unsafePipelineLinks: [...document.querySelectorAll('[data-testid="bengali-gothic-pipeline-shelf"] a')]
        .map((link) => link.getAttribute("href") || "")
        .filter((href) => href.startsWith("/reader/") || href.startsWith("/pricing") || /listen|audio/i.test(href)),
      staleCarouselCount: document.querySelectorAll('[data-testid="controlled-carousel-section"]').length,
      staleAudioUnavailableCount: document.querySelectorAll('[data-testid="audiobook-unavailable"]').length,
      legacyLiveCoverCount: document.querySelectorAll('[data-testid^="live-cover-preview-"]').length,
      legacyCategoryCardCount: document.querySelectorAll('[data-testid^="category-card-"]').length,
      legacyBroadReaderLinks: [...document.querySelectorAll('a[href^="/reader/"]')]
        .filter((link) => !link.closest('[data-testid="premium-landing-hero"]'))
        .map((link) => link.getAttribute("href"))
        .filter((href) => href !== "/reader/dracula"),
      heroCurrentPayCount: document.querySelectorAll('[data-testid="hero-current-pay"]').length,
      railPrimaryPreviewCount: document.querySelectorAll('[data-testid="live-cover-primary-preview"]').length,
      railPrimaryPaymentCount: document.querySelectorAll('[data-testid="live-cover-primary-payment"]').length,
      railLibraryCount: document.querySelectorAll('[data-testid="live-cover-library"]').length,
    };
  });
  assert(!home.hasHeroCard, "retired Dracula-first hero card should not render");
  assert(home.hasPremiumHero, "premium editorial hero is missing");
  assert(home.hasCuratedShelfCollage, "curated shelf collage is missing");
  assert(home.shelfGroupCount === expectedVisibleShelfCount, `curated shelf group count mismatch: ${home.shelfGroupCount}`);
  assert(home.selectedListeningCount === expectedApprovedAudioSlugs.length, `selected listening count mismatch: ${home.selectedListeningCount}`);
  assert(home.hasBengaliShelf, "Bengali Life & Legacy shelf is missing");
  assert(home.hasGothicShelf, "Gothic & the Uncanny shelf is missing");
  assert(!home.hasInternalCollageCopy, "internal release language leaked into the public shelf collage");
  assert(
    JSON.stringify(home.selectedListeningLinks) === JSON.stringify(expectedApprovedAudioSlugs.map((slug) => `/reader/${slug}?listen=1`)),
    `selected listening links drifted from approved audio truth: ${JSON.stringify(home.selectedListeningLinks)}`,
  );
  assert(home.hasReadingTimePath, "reading-time library path section is missing");
  assert(home.readingPathPricingHref === "/pricing", `reading path pricing CTA mismatch: ${home.readingPathPricingHref}`);
  assert(
    home.headline === "A premium reading and listening sanctuary for timeless Bengali and English classics.",
    `hero headline does not match the approved premium catalog hero: ${home.headline}`,
  );
  assert(!/Begin with Dracula|Step into Dracula/i.test(home.headline || ""), `homepage regressed to Dracula-first headline: ${home.headline}`);
  assert(home.heroLibraryHref === "/library", `hero Start Reading CTA should open library, got ${home.heroLibraryHref}`);
  assert(
    home.heroAudiobooksHref === "/library?availability=approved-audiobook",
    `hero audiobook CTA should open only the approved-audiobook collection, got ${home.heroAudiobooksHref}`,
  );
  assert(home.heroCatalogState === "ready", `hero catalog state should be ready, got ${home.heroCatalogState}`);
  assert(
    new Set(expectedHeroCarouselSlugs).size === expectedHeroCarouselSlugs.length,
    `Sprint 1 hero source contains duplicate slugs: ${JSON.stringify(expectedHeroCarouselSlugs)}`,
  );
  assert(
    JSON.stringify(home.heroVisualSlugs) === JSON.stringify([expectedHeroActiveSlug]),
    `hero coverflow must have one dominant active Sprint 1 book: ${JSON.stringify(home.heroVisualSlugs)}`,
  );
  assert(
    home.heroMeaningfulSlugs.length === 3
      && expectedHeroMeaningfulSlugs.every((slug) => home.heroMeaningfulSlugs.includes(slug)),
    `hero coverflow must expose only previous, active, and next books: ${JSON.stringify(home.heroMeaningfulSlugs)}`,
  );
  assert(
    home.heroAllVisualSlugs.every((slug) => expectedHeroCarouselSlugs.includes(slug)),
    `hero rendered a book outside the Sprint 1 carousel: ${JSON.stringify(home.heroAllVisualSlugs)}`,
  );
  assert(
    home.heroVisualCoverAlts.every((alt, index) => {
      const slug = home.heroVisualSlugs[index];
      const book = [...expectedHeroCarouselBooks, ...homeHeroFixtureBooks, ...homeHeroFixture.shelves.approved_audiobooks]
        .find((candidate) => candidate.slug === slug);
      return alt === `${book?.title} by ${book?.author}`;
    }),
    `hero cover alt text drifted from canonical title and author: ${JSON.stringify(home.heroVisualCoverAlts)}`,
  );
  assert(
    JSON.stringify(home.heroListenLinks) === JSON.stringify(expectedHeroListenLinks),
    `hero listening visual exposed a hidden or fake title: ${JSON.stringify(home.heroListenLinks)}`,
  );
  assert(home.staleCarouselCount === 0, "retired controlled launch carousel should not render in the luxury homepage");
  assert(home.staleAudioUnavailableCount === 0, "stale audiobook unavailable note should not render");
  assert(home.legacyLiveCoverCount === 0, "retired live-cover preview cards should not render in the approved landing");
  assert(home.legacyCategoryCardCount === 0, "retired broad category cards should not render in the approved landing");
  assert(home.heroCurrentPayCount === 0, "hero Preview & Pay CTA should not render");
  assert(home.railPrimaryPreviewCount === 0, "rail-level Read Preview CTA should not render");
  assert(home.railPrimaryPaymentCount === 0, "rail-level Preview & Pay CTA should not render");
  assert(home.railLibraryCount === 0, "rail-level All books CTA should not render");
  const firstSlug = liveApprovedSlug;
  const homeScreenshot = await snapshot(page, "home");

  await gotoAppPath(page, "/library");
  await page.waitForSelector('[data-testid="library-book-grid"]', { timeout: 30000 });
  const library = await page.evaluate(() => ({
    hasSingleShelf: Boolean(document.querySelector('[data-testid="library-book-grid"]')),
    hasSearch: Boolean(document.querySelector('[data-testid="library-search"]')),
    hasLanguageFilters: Boolean(document.querySelector('[data-testid="language-filters"]')),
    hasReadingFilters: Boolean(document.querySelector('[data-testid="reading-filters"]')),
    hasListeningFilters: Boolean(document.querySelector('[data-testid="listening-filters"]')),
    hasSort: Boolean(document.querySelector('[data-testid="library-sort"]')),
    hasPremiumHero: Boolean(document.querySelector('[data-testid="library-page"] [data-testid="premium-landing-hero"]')),
    legacyShelfCount: document.querySelectorAll([
      '[data-testid="shelf-live-controlled-release"]',
      '[data-testid="shelf-pipeline"]',
      '[data-testid="shelf-audiobooks"]',
    ].join(", ")).length,
    previewLinks: [...document.querySelectorAll('[data-testid="library-dracula-preview"], [data-testid^="card-preview-"], a[href^="/reader/"]')]
      .slice(0, 20)
      .map((link) => link.getAttribute("href")),
    cards: [...document.querySelectorAll('[data-testid^="book-card-"]')].map((card) => ({
      status: card.getAttribute("data-launch-status"),
      hasNotify: Boolean(card.querySelector('[data-testid^="card-notify-"]')),
      readerLinks: [...card.querySelectorAll('a[href^="/reader/"]')].map((link) => link.getAttribute("href")),
      listenLinks: [...card.querySelectorAll('[data-testid^="card-listen-"]')].map((link) => link.getAttribute("href")),
    })),
  }));
  assert(library.hasSingleShelf, "library did not render the single editorial collection");
  assert(library.hasSearch, "library search control is missing");
  assert(library.hasLanguageFilters, "library language filters are missing");
  assert(library.hasReadingFilters, "library reading filters are missing");
  assert(library.hasListeningFilters, "library listening filters are missing");
  assert(library.hasSort, "library sort control is missing");
  assert(library.hasPremiumHero, "library did not render the shared premium hero");
  assert(library.legacyShelfCount === 0, "retired multi-shelf library architecture rendered unexpectedly");
  assert(library.cards.length > 0, "library collection rendered no book cards");
  assert(library.previewLinks.includes("/reader/dracula"), "library has no Dracula reader preview CTA");
  assert(
    library.cards.every((card) => ["LIVE_APPROVED", "COMING_SOON_PIPELINE"].includes(card.status)),
    `library rendered an unknown release state: ${JSON.stringify(library.cards)}`,
  );
  assert(
    library.cards.filter((card) => card.status === "COMING_SOON_PIPELINE")
      .every((card) => card.readerLinks.every((href) => href?.endsWith("?listen=1"))
        && card.listenLinks.every((href) => href?.endsWith("?listen=1"))
        && (card.listenLinks.length > 0 || card.hasNotify)),
    `pipeline cards exposed an unapproved reader route: ${JSON.stringify(library.cards)}`,
  );
  assert(
    library.cards.every((card) => card.readerLinks.every((href) => card.status === "LIVE_APPROVED" || href?.endsWith("?listen=1"))),
    `non-live cards exposed reader routes: ${JSON.stringify(library.cards)}`,
  );
  assert(
    library.cards.every((card) => card.listenLinks.length === 0
      || card.listenLinks.every((href) => href?.endsWith("?listen=1"))),
    `listening controls escaped the approved release contract: ${JSON.stringify(library.cards)}`,
  );

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
