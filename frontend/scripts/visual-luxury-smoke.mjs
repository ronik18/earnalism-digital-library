#!/usr/bin/env node
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const baseUrl = process.env.VISUAL_SMOKE_BASE_URL || "http://127.0.0.1:4173";
const reportPath = path.join(repoRoot, "ux_visual_regression_report.json");
const protectionBypass = process.env.VERCEL_AUTOMATION_BYPASS_SECRET || process.env.VERCEL_PROTECTION_BYPASS || "";
const extraHeaders = parseExtraHeaders();
const sourceOnlyAllowed = process.env.VISUAL_SMOKE_SOURCE_ONLY_OK === "true";
const visualPhase = (process.env.EARNALISM_VISUAL_PHASE || "").trim().toUpperCase();
const routeMatrix = (process.env.VISUAL_SMOKE_ROUTE_MATRIX || "").trim().toLowerCase();
const requestedScreenshotDir = process.env.EARNALISM_VISUAL_OUTPUT_DIR || process.env.VISUAL_SMOKE_SCREENSHOT_DIR || "";

const homeRoutes = ["/"];
const libraryRoutes = ["/library"];
const brandHeaderLogoRoutes = ["/", "/library", "/book/dracula"];
const bookDetailSlugs = [
  "book-2b9853ec52",
  "a-ghost-story",
  "book-d19e96859f",
  "book-f5d593e1f4",
  "muchiram-gurer-jibanchorit",
  "pather-panchali",
  "bn-066",
  "dracula",
  "radharani",
  "nishkriti",
  "the-last-leaf",
  "the-masque-of-the-red-death",
];
const bookDetailRoutes = bookDetailSlugs.map((slug) => `/book/${slug}`);
const readerSlugs = [
  "book-2b9853ec52",
  "a-ghost-story",
  "dracula",
  "radharani",
  "nishkriti",
  "book-d19e96859f",
  "book-f5d593e1f4",
  "muchiram-gurer-jibanchorit",
  "pather-panchali",
  "the-last-leaf",
];
const readerRoutes = readerSlugs.map((slug) => `/reader/${slug}`);
const audiobookPlayerSlugs = [
  "book-2b9853ec52",
  "a-ghost-story",
  "book-d19e96859f",
  "book-f5d593e1f4",
  "pather-panchali",
  "the-last-leaf",
];
const audiobookPlayerRoutes = audiobookPlayerSlugs.flatMap((slug) => [`/book/${slug}`, `/reader/${slug}`]);
const settingsRoutes = [...readerRoutes];
const marketingLandingRoutes = ["/", "/about", "/pricing", "/contact", "/journal", "/micro-story"];
const allRoutes = [
  "/",
  "/library",
  "/book/book-2b9853ec52",
  "/reader/book-2b9853ec52",
  "/book/a-ghost-story",
  "/reader/a-ghost-story",
  "/book/dracula",
  "/reader/dracula",
  "/book/book-d19e96859f",
  "/reader/book-d19e96859f",
  "/book/book-f5d593e1f4",
  "/reader/book-f5d593e1f4",
  "/book/muchiram-gurer-jibanchorit",
  "/reader/muchiram-gurer-jibanchorit",
  "/book/pather-panchali",
  "/reader/pather-panchali",
  "/about",
  "/pricing",
  "/contact",
  "/journal",
  "/micro-story",
];
const routes = visualPhase === "HOME" || routeMatrix === "home"
  ? homeRoutes
  : visualPhase === "LIBRARY" || routeMatrix === "library"
    ? libraryRoutes
    : visualPhase === "BRAND_HEADER_LOGO" || routeMatrix === "brand-header-logo"
      ? brandHeaderLogoRoutes
    : visualPhase === "BOOK_DETAIL" || routeMatrix === "book-detail"
      ? bookDetailRoutes
      : visualPhase === "READER" || routeMatrix === "reader"
      ? readerRoutes
      : visualPhase === "AUDIOBOOK_PLAYER" || routeMatrix === "audiobook-player"
        ? audiobookPlayerRoutes
        : visualPhase === "SETTINGS" || routeMatrix === "settings"
          ? settingsRoutes
          : visualPhase === "MARKETING_LANDING" || routeMatrix === "marketing-landing"
            ? marketingLandingRoutes
            : allRoutes;
const visualSmokeMode = routes === homeRoutes
  ? "home_browser_and_source"
  : routes === libraryRoutes
    ? "library_browser_and_source"
    : routes === brandHeaderLogoRoutes
      ? "brand_header_logo_browser_and_source"
    : routes === bookDetailRoutes
      ? "book_detail_browser_and_source"
      : routes === readerRoutes
        ? "reader_browser_and_source"
        : routes === audiobookPlayerRoutes
          ? "audiobook_player_browser_and_source"
          : routes === settingsRoutes
            ? "settings_browser_and_source"
            : routes === marketingLandingRoutes
              ? "marketing_landing_browser_and_source"
              : "browser_and_source";
const isFullRouteSmoke = routes === allRoutes;
const shouldUseBookDetailMocks = routes === bookDetailRoutes || routes === audiobookPlayerRoutes || isFullRouteSmoke;
const shouldUseReaderMocks = routes === readerRoutes || routes === audiobookPlayerRoutes || routes === settingsRoutes || isFullRouteSmoke;
const shouldUseAudiobookPlayerMocks = routes === audiobookPlayerRoutes;
const shouldCheckSettingsPanel = routes === settingsRoutes;
const shouldCheckMarketingLanding = routes === marketingLandingRoutes;
const approvedAudiobookSmokeSlugs = new Set(["book-2b9853ec52", "a-ghost-story"]);

const allViewports = [
  { width: 1920, height: 1080 },
  { width: 1536, height: 864 },
  { width: 1440, height: 900 },
  { width: 1366, height: 768 },
  { width: 1280, height: 800 },
  { width: 1024, height: 768 },
  { width: 820, height: 1180 },
  { width: 430, height: 932 },
  { width: 390, height: 844 },
];
const viewports = shouldCheckMarketingLanding
  ? [
    { width: 1440, height: 900 },
    { width: 1536, height: 864 },
    { width: 430, height: 932 },
    { width: 390, height: 844 },
  ]
  : allViewports;

const sourceChecks = [
  {
    name: "book-cover-fallback-no-typography",
    file: "frontend/src/components/BookCoverImage.jsx",
    failIf: ["book-cover-image__fallback-title", "book-cover-image__fallback-author"],
  },
  {
    name: "shelf-two-shared-cover-resolver",
    file: "frontend/src/components/ShelfTwoSlideshow.jsx",
    require: ["<BookCoverImage"],
  },
  {
    name: "home-hero-type-calm",
    file: "frontend/src/pages/Home.jsx",
    failIf: ["lg:text-[4.45rem]", "sm:text-[3.75rem]"],
  },
  {
    name: "library-hero-type-calm",
    file: "frontend/src/pages/Library.jsx",
    failIf: ["lg:text-[4.8rem]", "sm:text-6xl"],
  },
  {
    name: "reader-no-browser-speech-fallback",
    file: "frontend/src/pages/Reader.jsx",
    failIf: ["speechSynthesis", "SpeechSynthesisUtterance", "browser speech", "system speech"],
  },
  {
    name: "reader-no-static-audio-derivation",
    file: "frontend/src/pages/Reader.jsx",
    failIf: ["/audio/"],
  },
  {
    name: "reader-settings-premium-baseline",
    file: "frontend/src/pages/Reader.jsx",
    require: ["Bengali font mode", "Reduced motion", "label: 'Night'", "Reset comfort defaults", "data-testid=\"reader-settings-panel\""],
  },
  {
    name: "reader-settings-persistence-helper",
    file: "frontend/src/lib/readerSettings.js",
    require: ["READER_SETTINGS_STORAGE_KEY", "sanitizeReaderSettings", "loadReaderSettings", "saveReaderSettings"],
  },
  {
    name: "audio-player-no-static-audio-or-fake-sync",
    file: "frontend/src/components/AudioPlayer.jsx",
    failIf: ["/audio/", "word-level", "word level", "word sync", "speechSynthesis", "SpeechSynthesisUtterance"],
  },
  {
    name: "audio-player-duplicate-quarantined",
    file: "frontend/src/components/AudioPlayer 2.jsx",
    mustNotExist: true,
  },
  {
    name: "service-worker-no-static-audio-cache",
    file: "frontend/public/service-worker.js",
    failIf: ["/audio/"],
  },
  {
    name: "audio-release-safety-blocks-static-audio-paths",
    file: "frontend/src/lib/audioReleaseSafety.js",
    require: ["isStaticAudiobookAssetPath", "Same-origin static audiobook assets are not public release evidence."],
  },
  {
    name: "brand-header-logo-deterministic-proofreader-lockup",
    file: "frontend/src/components/BrandHeaderLogo.jsx",
    require: [
      "earnalism-logo-transparent-96.webp",
      "LEarnalism",
      "Where Learning Becomes Earning",
      "brand-header-logo__inserted-l",
      "brand-header-logo__caret",
      "exact-flag",
      "tricolor",
      "none",
    ],
    failIf: ["data:image", "ai-garbled", "Comic Sans"],
  },
  {
    name: "header-uses-brand-header-logo",
    file: "frontend/src/components/Header.jsx",
    require: ["BrandHeaderLogo", "badgeVariant=\"tricolor\""],
    failIf: ["IndiaCraftBadge"],
  },
  {
    name: "marketing-default-seo-balanced",
    file: "frontend/src/hooks/useSEO.js",
    require: ["Bengali and English digital library"],
    failIf: ["beginning with Dracula"],
  },
  {
    name: "marketing-about-not-dracula-first",
    file: "frontend/src/pages/About.jsx",
    require: ["Bengali and English Digital Library", "Bengali and English classics", "Audiobooks appear only when approval evidence proves"],
    failIf: ["Dracula-First", "beginning with Dracula", "Dracula is live first"],
  },
  {
    name: "marketing-controlled-launch-audio-evidence-gated",
    file: "frontend/src/lib/controlledLaunch.js",
    require: ["Audio availability remains evidence-gated", "audiobook_enabled: false"],
    failIf: ["audiobook experience in private review"],
  },
  {
    name: "marketing-support-domain-consistent",
    file: "frontend/src/pages/Pricing.jsx",
    require: ["sales@reoenterprise.org"],
    failIf: ["sales@reoenterprise.in", "theearnalism.org"],
  },
  {
    name: "marketing-pipeline-interest-cta-truthful",
    file: "frontend/src/components/ShelfTwoSlideshow.jsx",
    require: ["Request Update", "/contact?interest="],
    failIf: ["Notify Me", "preventDefault()"],
  },
];

function parseExtraHeaders() {
  if (!process.env.VISUAL_SMOKE_EXTRA_HEADERS_JSON) return {};
  try {
    const parsed = JSON.parse(process.env.VISUAL_SMOKE_EXTRA_HEADERS_JSON);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function runSourceChecks() {
  return sourceChecks.map((check) => {
    const absolute = path.join(repoRoot, check.file);
    if (check.mustNotExist) {
      const exists = fs.existsSync(absolute);
      return {
        name: check.name,
        file: check.file,
        passed: !exists,
        blockers: exists ? ["Forbidden legacy file still exists"] : [],
      };
    }
    const source = fs.existsSync(absolute) ? fs.readFileSync(absolute, "utf8") : "";
    const blockers = [];
    for (const token of check.failIf || []) {
      if (source.includes(token)) blockers.push(`Forbidden token remains: ${token}`);
    }
    for (const token of check.require || []) {
      if (!source.includes(token)) blockers.push(`Required token missing: ${token}`);
    }
    return {
      name: check.name,
      file: check.file,
      passed: blockers.length === 0,
      blockers,
    };
  });
}

function routeToken(route) {
  const token = route.replace(/[^a-z0-9]+/gi, "_").replace(/^_+|_+$/g, "");
  return token || "home";
}

function readJsonFile(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

const bookDetailFallbacks = {
  "a-ghost-story": { title: "A Ghost Story", author: "Mark Twain", category_slug: "english-classics" },
  "bn-066": { title: "আনন্দমঠ", author: "বঙ্কিমচন্দ্র চট্টোপাধ্যায়", category_slug: "bengali-classics" },
  nishkriti: { title: "নিষ্কৃতি", author: "শরৎচন্দ্র চট্টোপাধ্যায়", category_slug: "bengali-classics" },
  "the-last-leaf": { title: "The Last Leaf", author: "O. Henry", category_slug: "english-classics" },
  "the-masque-of-the-red-death": { title: "The Masque of the Red Death", author: "Edgar Allan Poe", category_slug: "english-classics" },
};

function compactChapterList(book = {}) {
  if (Array.isArray(book.chapters) && book.chapters.length) {
    return book.chapters.slice(0, 4).map((chapter, index) => ({
      id: chapter.id || `chapter-${String(index + 1).padStart(3, "0")}`,
      title: chapter.title || `Chapter ${index + 1}`,
    }));
  }
  return [{ id: "chapter-001", title: "Reading Edition" }];
}

function approvedAudioAssetsForSlug(slug) {
  return {
    mp3: `/api/reader/book/${slug}/audiobook`,
    timestamps: `/api/reader/book/${slug}/audiobook/timestamps`,
    manifest: `/api/reader/book/${slug}/audiobook/manifest`,
  };
}

function safeBookDetailFixture(slug, { approvedAudio = false } = {}) {
  const publicBookPath = path.join(repoRoot, "data", "controlled_publications", slug, "public_book.json");
  const contentBookPath = path.join(repoRoot, "content", "books", slug, "book.json");
  const publicBook = readJsonFile(publicBookPath, null);
  const contentBook = readJsonFile(contentBookPath, null);
  const fallback = bookDetailFallbacks[slug] || {};
  const book = publicBook || contentBook || fallback;
  const audioAssets = approvedAudio ? approvedAudioAssetsForSlug(slug) : {};
  return {
    ...book,
    slug,
    title: book.title || fallback.title || slug,
    author: book.author || fallback.author || "The Earnalism",
    category_slug: book.category_slug || fallback.category_slug || "classics",
    publication_status: book.publication_status || "LIVE_APPROVED",
    description: book.description || book.short_description || `A reader-ready Earnalism detail page for ${book.title || fallback.title || slug}.`,
    chapters: compactChapterList(book),
    audiobook_enabled: approvedAudio,
    generate_audiobook: approvedAudio,
    audio_disabled: !approvedAudio,
    audiobook_release_gate: approvedAudio ? "APPROVED" : "",
    audio_qa_status: approvedAudio ? "PASS" : "",
    audiobook_assets: audioAssets,
    _readerManifest: approvedAudio ? {
      audio: {
        enabled: true,
        provider: "sarvam",
        version: "visual-smoke-approved-audio",
        release_gate: "APPROVED",
        qa_status: "PASS",
        sync_mode: "paragraph_stanza",
        assets: audioAssets,
      },
    } : undefined,
  };
}

const bookDetailFixtureSlugs = routes === audiobookPlayerRoutes ? audiobookPlayerSlugs : bookDetailSlugs;
const bookDetailFixtures = Object.fromEntries(bookDetailFixtureSlugs.map((slug) => [
  slug,
  safeBookDetailFixture(slug, {
    approvedAudio: shouldUseAudiobookPlayerMocks && approvedAudiobookSmokeSlugs.has(slug),
  }),
]));

const readerFallbacks = {
  "book-2b9853ec52": { title: "দুই বিঘা জমি", author: "রবীন্দ্রনাথ ঠাকুর", language: "ben" },
  "a-ghost-story": { title: "A Ghost Story", author: "Mark Twain", language: "eng" },
  dracula: { title: "Dracula", author: "Bram Stoker", language: "eng" },
  radharani: { title: "রাধারাণী", author: "বঙ্কিমচন্দ্র চট্টোপাধ্যায়", language: "ben" },
  nishkriti: { title: "নিষ্কৃতি", author: "শরৎচন্দ্র চট্টোপাধ্যায়", language: "ben" },
  "book-d19e96859f": { title: "Bengali reader-only canary", author: "Earnalism Bengali Classics", language: "ben" },
  "book-f5d593e1f4": { title: "Bengali reader-only canary", author: "Earnalism Bengali Classics", language: "ben" },
  "muchiram-gurer-jibanchorit": { title: "মুচিরাম গুড়ের জীবনচরিত", author: "বঙ্কিমচন্দ্র চট্টোপাধ্যায়", language: "ben" },
  "pather-panchali": { title: "পথের পাঁচালী", author: "বিভূতিভূষণ বন্দ্যোপাধ্যায়", language: "ben" },
  "the-last-leaf": { title: "The Last Leaf", author: "O. Henry", language: "eng" },
};

function safeReaderFixture(slug, { approvedAudio = false } = {}) {
  const detail = safeBookDetailFixture(slug, { approvedAudio });
  const fallback = readerFallbacks[slug] || {};
  const title = detail.title || fallback.title || slug;
  const author = detail.author || fallback.author || "Earnalism";
  const language = detail.language || detail.language_code || fallback.language || (/[^\u0000-\u007F]/.test(title) ? "ben" : "eng");
  const chapterId = "chapter-001";
  const bengali = language === "ben" || /[\u0980-\u09FF]/.test(`${title} ${author}`);
  const audioAssets = approvedAudio ? approvedAudioAssetsForSlug(slug) : {};
  const body = bengali
    ? `<p>${title} পাঠের জন্য প্রস্তুত। এই পাঠঘরটি শান্ত, সংযত, এবং পাঠক-কেন্দ্রিক। অডিও কেবল অনুমোদিত উৎপাদন প্রমাণ থাকলে দেখা যাবে।</p><p>বাংলা সাহিত্যের পাঠ যেন উদার লাইন-স্পেস, মর্যাদাপূর্ণ অক্ষর, এবং মনোযোগী নীরবতার মধ্যে থাকে।</p>`
    : `<p>${title} is prepared as a calm Earnalism reading edition. The reader is complete without implying that an audiobook is available.</p><p>Audio controls stay hidden unless release evidence proves an approved listening room.</p>`;
  return {
    slug,
    manifest: {
      version: "reader-smoke-v1",
      generated_at: new Date(0).toISOString(),
      access: { admin_preview: false, wallet_seconds: 0 },
      audio: {
        enabled: approvedAudio,
        release_gate: approvedAudio ? "APPROVED" : "",
        qa_status: approvedAudio ? "PASS" : "",
        provider: approvedAudio ? "sarvam" : "",
        version: approvedAudio ? "visual-smoke-approved-audio" : "",
        sync_mode: approvedAudio ? "paragraph_stanza" : "",
        assets: audioAssets,
      },
      book: {
        ...detail,
        slug,
        title,
        author,
        language,
        publication_status: detail.publication_status || "LIVE_APPROVED",
        audiobook_enabled: approvedAudio,
        generate_audiobook: approvedAudio,
        audio_disabled: !approvedAudio,
        audiobook_release_gate: approvedAudio ? "APPROVED" : "",
        audio_qa_status: approvedAudio ? "PASS" : "",
        audiobook_assets: audioAssets,
        chapters: [{ id: chapterId, title: "Reading Edition", order: 0, is_preview: true, content_version: "reader-smoke-v1" }],
      },
      chapters: [{ id: chapterId, title: "Reading Edition", order: 0, is_preview: true, content_version: "reader-smoke-v1" }],
    },
    chapter: {
      id: chapterId,
      title: "Reading Edition",
      order: 0,
      is_preview: true,
      content: body,
    },
  };
}

const readerFixtureSlugs = routes === audiobookPlayerRoutes ? audiobookPlayerSlugs : readerSlugs;
const readerFixtures = Object.fromEntries(readerFixtureSlugs.map((slug) => [
  slug,
  safeReaderFixture(slug, {
    approvedAudio: shouldUseAudiobookPlayerMocks && approvedAudiobookSmokeSlugs.has(slug),
  }),
]));

function runBrowserChecks() {
  if (!baseUrl && sourceOnlyAllowed) return { skipped: true, reason: "VISUAL_SMOKE_BASE_URL not set and source-only mode explicitly allowed" };
  if (!baseUrl) {
    return {
      skipped: false,
      playwright_import_status: "not_run",
      browser_launch_status: "not_run",
      browser_checks_required: true,
      routes_attempted: routes.length * viewports.length,
      routes_completed: 0,
      failed_subchecks: [{ issue: "VISUAL_SMOKE_BASE_URL not set" }],
      blockers: [{ route: "*", viewport: "*", issue: "VISUAL_SMOKE_BASE_URL not set" }],
    };
  }

  const runnerPath = path.join(repoRoot, "frontend", ".earnalism-visual-smoke-runner.mjs");
  const browserResultPath = path.join(os.tmpdir(), "earnalism-visual-smoke-browser-result.json");
  const screenshotDir = requestedScreenshotDir || path.join(os.tmpdir(), "earnalism-visual-smoke-screenshots");
  const headers = {
    ...extraHeaders,
    ...(protectionBypass ? { "x-vercel-protection-bypass": protectionBypass } : {}),
  };
  fs.mkdirSync(screenshotDir, { recursive: true });
  fs.writeFileSync(runnerPath, `
import fs from "node:fs";
let chromium;
let playwrightImportStatus = "not_run";
let browserLaunchStatus = "not_run";
try {
  ({ chromium } = await import("playwright"));
  playwrightImportStatus = "passed";
} catch (error) {
  console.log(JSON.stringify({
    skipped: false,
    playwright_import_status: "failed",
    browser_launch_status: "not_run",
    browser_checks_required: true,
    routes_attempted: ${routes.length * viewports.length},
    routes_completed: 0,
    failed_subchecks: [{ issue: "playwright import failed", message: error.message }],
    blockers: [{ route: "*", viewport: "*", issue: "playwright import failed" }],
  }, null, 2));
  process.exit(1);
}

const baseUrl = ${JSON.stringify(baseUrl)};
const screenshotDir = ${JSON.stringify(screenshotDir)};
const resultFile = ${JSON.stringify(browserResultPath)};
const routes = ${JSON.stringify(routes)};
const viewports = ${JSON.stringify(viewports)};
const headers = ${JSON.stringify(headers)};
const pageWaitUntil = ${JSON.stringify(shouldCheckMarketingLanding ? "domcontentloaded" : "networkidle")};
const bookDetailFixtures = ${JSON.stringify(shouldUseBookDetailMocks ? bookDetailFixtures : {})};
const readerFixtures = ${JSON.stringify(shouldUseReaderMocks ? readerFixtures : {})};
const shouldMockBookDetailApi = ${JSON.stringify(shouldUseBookDetailMocks)};
const shouldMockReaderApi = ${JSON.stringify(shouldUseReaderMocks)};
const shouldMockAudiobookPlayerApi = ${JSON.stringify(shouldUseAudiobookPlayerMocks)};
const shouldMockMarketingLandingApi = ${JSON.stringify(shouldCheckMarketingLanding)};
const shouldUseSpaDocumentFallback = ${JSON.stringify(shouldUseReaderMocks || shouldCheckMarketingLanding)};
const approvedAudiobookSmokeSlugs = new Set(${JSON.stringify(Array.from(approvedAudiobookSmokeSlugs))});
let browser;
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  browserLaunchStatus = "passed";
} catch (chromeError) {
  try {
    browser = await chromium.launch({ headless: true });
    browserLaunchStatus = "passed";
  } catch (error) {
    console.log(JSON.stringify({
      skipped: false,
      playwright_import_status: playwrightImportStatus,
      browser_launch_status: "failed",
      browser_checks_required: true,
      routes_attempted: routes.length * viewports.length,
      routes_completed: 0,
      failed_subchecks: [{ issue: "browser launch failed", message: error.message }],
      blockers: [{ route: "*", viewport: "*", issue: "browser launch failed" }],
    }, null, 2));
    process.exit(1);
  }
}

const results = [];
for (const route of routes) {
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport, deviceScaleFactor: 1, extraHTTPHeaders: headers });
    if (shouldUseSpaDocumentFallback) {
      const indexHtmlPath = ${JSON.stringify(path.join(repoRoot, "frontend", "build", "index.html"))};
      const indexHtml = fs.existsSync(indexHtmlPath) ? fs.readFileSync(indexHtmlPath, "utf8") : "";
      await page.route("**/*", async (apiRoute) => {
        const request = apiRoute.request();
        const requestUrl = new URL(request.url());
        if (request.resourceType() === "document" && routes.includes(requestUrl.pathname) && indexHtml) {
          await apiRoute.fulfill({ status: 200, contentType: "text/html", body: indexHtml });
          return;
        }
        await apiRoute.fallback();
      });
    }
    if (shouldMockMarketingLandingApi) {
      await page.route("**/api/payments/packs", async (apiRoute) => {
        await apiRoute.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: "30m", label: "The First Chapter", minutes: 30, price_inr: 49, note: "A quiet first reading step with no subscription." },
            { id: "1h", label: "One Hour", minutes: 60, price_inr: 89, note: "A focused reading visit for one classic chapter or essay." },
          ]),
        });
      });
      await page.route("**/api/payments/config", async (apiRoute) => {
        await apiRoute.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ configured: false, mode: "test", key_id: "" }) });
      });
      await page.route("**/api/blog", async (apiRoute) => {
        await apiRoute.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      });
    }
    if (shouldMockReaderApi) {
      await page.route("**/api/payments/packs", async (apiRoute) => {
        await apiRoute.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      });
      await page.route("**/api/reader/metrics", async (apiRoute) => {
        await apiRoute.fulfill({ status: 204, body: "" });
      });
      await page.route("**/api/reader/book/*/manifest", async (apiRoute) => {
        const requestUrl = new URL(apiRoute.request().url());
        const parts = requestUrl.pathname.split("/").filter(Boolean);
        if (parts[4] === "audiobook" && parts[5] === "manifest") {
          const slug = decodeURIComponent(parts[3] || "");
          if (!approvedAudiobookSmokeSlugs.has(slug)) {
            await apiRoute.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not approved" }) });
            return;
          }
          await apiRoute.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              slug,
              provider: "sarvam",
              version: "visual-smoke-approved-audio",
              sync_mode: "paragraph_stanza",
            }),
          });
          return;
        }
        const slug = decodeURIComponent(parts[parts.length - 2] || "");
        const fixture = readerFixtures[slug];
        if (!fixture) {
          await apiRoute.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found" }) });
          return;
        }
        await apiRoute.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixture.manifest) });
      });
      await page.route("**/api/reader/chapter/*/*", async (apiRoute) => {
        const requestUrl = new URL(apiRoute.request().url());
        const parts = requestUrl.pathname.split("/").filter(Boolean);
        const slug = decodeURIComponent(parts[parts.length - 2] || "");
        const fixture = readerFixtures[slug];
        if (!fixture) {
          await apiRoute.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found" }) });
          return;
        }
        await apiRoute.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ chapter: fixture.chapter, is_preview: true }) });
      });
      await page.route("**/api/reader/book/*/audiobook/timestamps", async (apiRoute) => {
        const requestUrl = new URL(apiRoute.request().url());
        const parts = requestUrl.pathname.split("/").filter(Boolean);
        const slug = decodeURIComponent(parts[3] || "");
        if (!approvedAudiobookSmokeSlugs.has(slug)) {
          await apiRoute.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not approved" }) });
          return;
        }
        await apiRoute.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            words: [
              { word: "দুই", start_ms: 0, end_ms: 520, word_index: 0 },
              { word: "বিঘা", start_ms: 520, end_ms: 1040, word_index: 1 },
              { word: "জমি", start_ms: 1040, end_ms: 1560, word_index: 2 },
            ],
          }),
        });
      });
      await page.route("**/api/reader/book/*/audiobook/manifest", async (apiRoute) => {
        const requestUrl = new URL(apiRoute.request().url());
        const parts = requestUrl.pathname.split("/").filter(Boolean);
        const slug = decodeURIComponent(parts[3] || "");
        if (!approvedAudiobookSmokeSlugs.has(slug)) {
          await apiRoute.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not approved" }) });
          return;
        }
        await apiRoute.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            slug,
            provider: "sarvam",
            version: "visual-smoke-approved-audio",
            sync_mode: "paragraph_stanza",
          }),
        });
      });
      await page.route("**/api/reader/book/*/audiobook", async (apiRoute) => {
        const requestUrl = new URL(apiRoute.request().url());
        const parts = requestUrl.pathname.split("/").filter(Boolean);
        const slug = decodeURIComponent(parts[3] || "");
        if (!approvedAudiobookSmokeSlugs.has(slug)) {
          await apiRoute.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not approved" }) });
          return;
        }
        await apiRoute.fulfill({
          status: 206,
          headers: {
            "accept-ranges": "bytes",
            "content-range": "bytes 0-0/1",
          },
          contentType: "audio/mpeg",
          body: Buffer.from([0]),
        });
      });
    }
    if (shouldMockBookDetailApi) {
      await page.route("**/api/books/*", async (apiRoute) => {
        const requestUrl = new URL(apiRoute.request().url());
        const slug = decodeURIComponent(requestUrl.pathname.split("/").filter(Boolean).pop() || "");
        const fixture = bookDetailFixtures[slug];
        if (!fixture) {
          await apiRoute.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found" }) });
          return;
        }
        await apiRoute.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixture) });
      });
    }
    const consoleErrors = [];
    const resourceErrors = [];
    page.on("console", (msg) => {
      if (msg.type() !== "error") return;
      const text = msg.text();
      if (/^Failed to load resource:/i.test(text)) resourceErrors.push(text);
      else consoleErrors.push(text);
    });
    const url = new URL(route, baseUrl).toString();
    let status = 0;
    try {
      const response = await page.goto(url, { waitUntil: pageWaitUntil, timeout: 30000 });
      status = response?.status() || 0;
    } catch (error) {
      consoleErrors.push(error.message);
    }
    await page.waitForSelector(
      "[data-testid='home-page'], [data-testid='library-page'], [data-testid='book-page'], [data-testid='reader-page'], [data-testid='about-page'], [data-testid='pricing-page'], [data-testid='contact-page'], [data-testid='journal-page'], .micro-story-page, [data-testid='book-not-found'], [data-testid='reader-not-found']",
      { timeout: 12000 },
    ).catch(() => {});
    if (${JSON.stringify(shouldCheckSettingsPanel)}) {
      await page.click("button[aria-label='Open reading settings']").catch(() => {});
      await page.waitForSelector("[data-testid='reader-settings-panel']", { timeout: 6000 }).catch(() => {});
      await page.waitForFunction(() => {
        const panel = document.querySelector("[data-testid='reader-settings-panel']");
        return Boolean(panel && panel.contains(document.activeElement));
      }, null, { timeout: 2500 }).catch(() => {});
      if (route === routes[0] && viewport.width === viewports[0].width && viewport.height === viewports[0].height) {
        await page.keyboard.press("Escape").catch(() => {});
        await page.waitForSelector("[data-testid='reader-settings-panel']", { state: "hidden", timeout: 1200 }).catch(() => {});
        await page.click("button[aria-label='Open reading settings']").catch(() => {});
        await page.waitForSelector("[data-testid='reader-settings-panel']", { timeout: 6000 }).catch(() => {});
        await page.waitForFunction(() => {
          const panel = document.querySelector("[data-testid='reader-settings-panel']");
          return Boolean(panel && panel.contains(document.activeElement));
        }, null, { timeout: 2500 }).catch(() => {});
      }
    }
    const metrics = await page.evaluate(() => {
      const body = document.body;
      const bodyText = body?.innerText || "";
      const hero = document.querySelector("[data-testid='premium-landing-hero'], [data-testid='library-hero']");
      const heading = document.querySelector("[data-testid='hero-headline'], [data-testid='library-hero'] h1, h1");
      const cover = document.querySelector("[data-testid='hero-dracula-cover-frame'], .book-cover-image, .reference-hero-book, .reader-cover-page img");
      const cta = document.querySelector("[data-testid='hero-cta-read'], [data-testid='library-hero-read'], .btn-primary, a[href*='/reader/']");
      const headingStyle = heading ? getComputedStyle(heading) : null;
      const heroStyle = hero ? getComputedStyle(hero) : null;
      const rect = cover ? cover.getBoundingClientRect() : null;
      const textOnlyFallback = Boolean(document.querySelector(".book-cover-image__fallback-title, .book-cover-image__fallback-author"));
      const structuredData = Array.from(document.querySelectorAll("script[type='application/ld+json']")).map((node) => node.textContent || "").join("\\n");
      const listenCta = document.querySelector("[data-testid='book-listen-approved'], a[href*='listen=1']");
      const primaryCta = document.querySelector("[data-testid='start-reading']");
      const audioStatus = document.querySelector("[data-testid='book-detail-audio-status']");
      const readerStatus = document.querySelector("[data-testid='book-detail-reader-status']");
      const waveform = document.querySelector("[data-testid*='waveform'], .waveform, [class*='waveform']");
      const progress = document.querySelector("[data-testid*='progress'], progress, [role='progressbar']");
      const readerSettingsButton = document.querySelector("button[aria-label='Open reading settings']");
      const readerSettingsPanel = document.querySelector("[data-testid='reader-settings-panel']");
      const readerSettingsReset = document.querySelector(".reader-settings-reset");
      const readerSettingsThemeButtons = Array.from(document.querySelectorAll("[aria-label^='Use'][aria-label$='theme']"));
      const readerSettingsPressed = Array.from(document.querySelectorAll("[data-testid='reader-settings-panel'] [aria-pressed='true']")).length;
      const readerContentsButton = document.querySelector("button[aria-label='Open contents']");
      const readerAudioButton = document.querySelector(".reader-audio-button");
      const readerAudioUnavailable = document.querySelector(".reader-audio-unavailable");
      const generatedAudio = document.querySelector("[data-testid='generated-audiobook']");
      const readerContent = document.querySelector(".reader-content, .reader-index-page, .reader-cover-page");
      const audioSources = Array.from(document.querySelectorAll("audio, source")).map((node) => node.getAttribute("src") || "").filter(Boolean);
      const approvedAudiobookPlayer = document.querySelector("[data-testid='approved-audiobook-player']");
      const approvedAudiobookAudio = document.querySelector("[data-testid='approved-audiobook-audio']");
      const approvedAudiobookSync = document.querySelector("[data-testid='approved-audiobook-sync']");
      const brandHeaderLogo = document.querySelector("[data-testid='brand-header-logo']");
      const brandHeaderProofread = document.querySelector("[data-testid='brand-header-logo-proofread']");
      const brandHeaderTagline = document.querySelector("[data-testid='brand-header-logo-tagline']");
      const brandHeaderTricolorBadge = document.querySelector("[data-testid='brand-header-logo-badge-tricolor']");
      const brandHeaderExactBadge = document.querySelector("[data-testid='brand-header-logo-badge-exact']");
      const brandRect = brandHeaderLogo ? brandHeaderLogo.getBoundingClientRect() : null;
      const marketingPage = document.querySelector("[data-testid='home-page'], [data-testid='about-page'], [data-testid='pricing-page'], [data-testid='contact-page'], [data-testid='journal-page'], .micro-story-page");
      const marketingPrimaryCta = document.querySelector("[data-testid='hero-cta-library'], [data-testid='pricing-to-library'], [data-testid='contact-submit'], .micro-story-hero__cta, a[href='/library'], a[href*='/pricing']");
      return {
        appContentVisible: Boolean(document.querySelector("[data-testid='home-page'], [data-testid='library-page'], [data-testid='book-page'], [data-testid='reader-page'], [data-testid='about-page'], [data-testid='pricing-page'], [data-testid='contact-page'], [data-testid='journal-page'], .micro-story-page, [data-testid='book-not-found'], [data-testid='reader-not-found']")),
        vercelLoginShellDetected: /vercel deployment protection|log in to continue|continue with github|saml sso|vercel\\.com\\/sso-api/i.test(bodyText),
        horizontalOverflow: body.scrollWidth > window.innerWidth + 1,
        heroHeadingVisible: heading ? Boolean(heading.offsetWidth && heading.offsetHeight) : true,
        heroCtaVisible: cta ? Boolean(cta.offsetWidth && cta.offsetHeight) : true,
        coverClipped: rect ? rect.right > window.innerWidth + 1 || rect.left < -1 : false,
        textOnlyCoverFallbackVisible: textOnlyFallback,
        bookTitle: heading?.textContent?.trim() || "",
        primaryCtaText: primaryCta?.textContent?.trim() || "",
        readerStatusText: readerStatus?.textContent?.trim() || "",
        audioStatusText: audioStatus?.textContent?.trim() || "",
        listenCtaVisible: Boolean(listenCta && listenCta.offsetWidth && listenCta.offsetHeight),
        narratorMetadataVisible: /\\bnarrator\\b/i.test(bodyText),
        durationMetadataVisible: Boolean(document.querySelector("[data-testid*='duration'], time[datetime]")),
        waveformVisible: Boolean(waveform),
        progressUiVisible: Boolean(progress),
        audioObjectStructuredData: /"@type"\\s*:\\s*"AudioObject"|AudioObject/i.test(structuredData),
        wordLevelSyncCopyVisible: /word-level|word level/i.test(bodyText),
        speechFallbackCopyVisible: /speechSynthesis|system speech|browser speech/i.test(bodyText),
        readerPageVisible: Boolean(document.querySelector("[data-testid='reader-page']")),
        readerContentVisible: Boolean(readerContent && readerContent.textContent?.trim()),
        readerSettingsReachable: Boolean(readerSettingsButton),
        readerSettingsPanelVisible: Boolean(readerSettingsPanel && readerSettingsPanel.offsetWidth && readerSettingsPanel.offsetHeight),
        readerSettingsPanelHasFocus: Boolean(readerSettingsPanel?.contains(document.activeElement)),
        readerSettingsResetVisible: Boolean(readerSettingsReset && readerSettingsReset.offsetWidth && readerSettingsReset.offsetHeight),
        readerSettingsThemeButtonCount: readerSettingsThemeButtons.length,
        readerSettingsPressedCount: readerSettingsPressed,
        readerSettingsHasAudioLeakCopy: /Listen CTA|AudioObject|browser speech|system speech|word-level|word sync/i.test(readerSettingsPanel?.textContent || ""),
        readerContentsReachable: Boolean(readerContentsButton),
        readerAudioButtonVisible: Boolean(readerAudioButton && readerAudioButton.offsetWidth && readerAudioButton.offsetHeight),
        generatedAudioElementVisible: Boolean(generatedAudio),
        approvedAudiobookPlayerVisible: Boolean(approvedAudiobookPlayer && approvedAudiobookPlayer.offsetWidth && approvedAudiobookPlayer.offsetHeight),
        approvedAudiobookAudioSrcVisible: Boolean(approvedAudiobookAudio?.getAttribute("src")),
        approvedAudiobookSyncCopy: approvedAudiobookSync?.textContent?.trim() || "",
        brandHeaderLogoVisible: Boolean(brandHeaderLogo && brandHeaderLogo.offsetWidth && brandHeaderLogo.offsetHeight),
        brandHeaderLabel: brandHeaderLogo?.getAttribute("aria-label") || "",
        brandHeaderProofreadVisible: Boolean(brandHeaderProofread && brandHeaderProofread.offsetWidth && brandHeaderProofread.offsetHeight),
        brandHeaderTaglineVisible: Boolean(brandHeaderTagline && brandHeaderTagline.offsetWidth && brandHeaderTagline.offsetHeight),
        brandHeaderTricolorBadgeVisible: Boolean(brandHeaderTricolorBadge && brandHeaderTricolorBadge.offsetWidth && brandHeaderTricolorBadge.offsetHeight),
        brandHeaderExactBadgeVisible: Boolean(brandHeaderExactBadge && brandHeaderExactBadge.offsetWidth && brandHeaderExactBadge.offsetHeight),
        brandHeaderRectSafe: brandRect ? brandRect.left >= -1 && brandRect.right <= window.innerWidth + 1 : false,
        marketingPageVisible: Boolean(marketingPage && marketingPage.offsetWidth && marketingPage.offsetHeight),
        marketingPrimaryCtaVisible: Boolean(
          (marketingPrimaryCta && marketingPrimaryCta.offsetWidth && marketingPrimaryCta.offsetHeight)
          || (cta && cta.offsetWidth && cta.offsetHeight)
        ),
        marketingBengaliVisible: /Bengali|বাংলা|বঙ্গ|শরৎচন্দ্র|রবীন্দ্রনাথ/i.test(bodyText),
        marketingEnglishVisible: /English|Dracula|classics|reading room|literature/i.test(bodyText),
        marketingDraculaFirstRiskVisible: /Dracula-First|beginning with Dracula|Dracula is live first/i.test(bodyText),
        marketingPrivateReviewAudioVisible: /audiobook experience in private review|private review audio/i.test(bodyText),
        marketingNotifyMeVisible: /\\bNotify Me\\b/i.test(bodyText),
        marketingSupportDomainMismatchVisible: /sales@reoenterprise\\.in|support@theearnalism\\.org|theearnalism\\.org/i.test(bodyText),
        marketingRequestUpdateVisible: /Request Update/i.test(bodyText),
        marketingStaticAudioPathVisible: /\\/audio\\//i.test(bodyText) || /\\/audio\\//i.test(structuredData),
        marketingUnapprovedListenVisible: Boolean(listenCta && listenCta.offsetWidth && listenCta.offsetHeight),
        staticAudioSrcVisible: audioSources.some((src) => src.includes("/audio/")),
        readerAudioHiddenCopyVisible: Boolean(readerAudioUnavailable)
          && /Reading edition available|Audio will appear only after narration, sync, and browser gates pass/i.test(readerAudioUnavailable.textContent || ""),
        textColor: headingStyle?.color || "",
        heroBackground: heroStyle?.backgroundColor || "",
      };
    });
    const routeToken = route.replace(/[^a-z0-9]+/gi, "_").replace(/^_+|_+$/g, "") || "home";
    const screenshotPath = screenshotDir + "/" + routeToken + "_" + viewport.width + "x" + viewport.height + ".png";
    await page.screenshot({ path: screenshotPath, fullPage: false });
    await page.close();
    results.push({ route, viewport, status, screenshotPath, consoleErrors, resourceErrors, ...metrics });
  }
}
await browser.close();
const blockers = results.flatMap((result) => {
  const issues = [];
  const approvedAudioRoute = shouldMockAudiobookPlayerApi
    && [...approvedAudiobookSmokeSlugs].some((slug) => result.route.includes(slug));
  const isReaderRoute = result.route.startsWith("/reader/");
  const marketingNeedsBilingualProof = ["/", "/about"].includes(result.route);
  const marketingNeedsPrimaryCta = ["/", "/pricing", "/micro-story"].includes(result.route);
  if (!result.appContentVisible) issues.push("app content not visible");
  if (result.vercelLoginShellDetected) issues.push("Vercel login shell");
  if (result.horizontalOverflow) issues.push("horizontal overflow");
  if (!result.heroHeadingVisible) issues.push("hero heading invisible");
  if (!result.heroCtaVisible) issues.push("CTA invisible");
  if (result.coverClipped) issues.push("cover clipped");
  if (result.textOnlyCoverFallbackVisible) issues.push("text-only cover fallback visible");
  if (${JSON.stringify(routes === brandHeaderLogoRoutes)} && !result.brandHeaderLogoVisible) issues.push("brand header logo not visible");
  if (${JSON.stringify(routes === brandHeaderLogoRoutes)} && result.brandHeaderLabel !== "LEarnalism — Where Learning Becomes Earning") issues.push("brand header accessible label missing");
  if (${JSON.stringify(routes === brandHeaderLogoRoutes)} && !result.brandHeaderProofreadVisible) issues.push("brand header proofreader correction not visible");
  if (${JSON.stringify(routes === brandHeaderLogoRoutes)} && result.viewport.width >= 768 && !result.brandHeaderTaglineVisible) issues.push("brand header tagline not visible on desktop");
  if (${JSON.stringify(routes === brandHeaderLogoRoutes)} && !result.brandHeaderTricolorBadgeVisible) issues.push("brand header tricolor badge not visible");
  if (${JSON.stringify(routes === brandHeaderLogoRoutes)} && result.brandHeaderExactBadgeVisible) issues.push("exact flag badge visible in default header");
  if (${JSON.stringify(routes === brandHeaderLogoRoutes)} && !result.brandHeaderRectSafe) issues.push("brand header lockup overflows viewport");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && !result.marketingPageVisible) issues.push("marketing page not visible");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && marketingNeedsPrimaryCta && !result.marketingPrimaryCtaVisible) issues.push("marketing primary CTA not visible");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && marketingNeedsBilingualProof && !result.marketingBengaliVisible) issues.push("Bengali representation missing");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && marketingNeedsBilingualProof && !result.marketingEnglishVisible) issues.push("English representation missing");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && result.marketingDraculaFirstRiskVisible) issues.push("Dracula-first marketing copy visible");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && result.marketingPrivateReviewAudioVisible) issues.push("private review audiobook copy visible");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && result.marketingNotifyMeVisible) issues.push("fake Notify Me affordance visible");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && result.marketingSupportDomainMismatchVisible) issues.push("support email/domain mismatch visible");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && result.marketingStaticAudioPathVisible) issues.push("static audio path visible on marketing route");
  if (${JSON.stringify(shouldCheckMarketingLanding)} && result.marketingUnapprovedListenVisible) issues.push("unapproved Listen CTA visible on marketing route");
  if (shouldMockBookDetailApi && result.listenCtaVisible && !approvedAudioRoute) issues.push("book detail local fixture exposed Listen CTA");
  if (shouldMockAudiobookPlayerApi && approvedAudioRoute && result.route.startsWith("/book/") && !result.listenCtaVisible) issues.push("approved audiobook detail did not expose approved Listen CTA");
  if (result.audioObjectStructuredData) issues.push("AudioObject structured data visible");
  if (result.wordLevelSyncCopyVisible) issues.push("word-level sync copy visible");
  if (result.speechFallbackCopyVisible) issues.push("speech fallback copy visible");
  if (shouldMockReaderApi && isReaderRoute && !result.readerPageVisible) issues.push("reader page not visible");
  if (shouldMockReaderApi && isReaderRoute && !result.readerContentVisible) issues.push("reader text not visible");
  if (shouldMockReaderApi && isReaderRoute && !result.readerSettingsReachable) issues.push("reader settings not reachable");
  if (${JSON.stringify(shouldCheckSettingsPanel)} && isReaderRoute && !result.readerSettingsPanelVisible) issues.push("reader settings panel not visible");
  if (${JSON.stringify(shouldCheckSettingsPanel)} && isReaderRoute && !result.readerSettingsPanelHasFocus) issues.push("reader settings panel did not retain keyboard focus");
  if (${JSON.stringify(shouldCheckSettingsPanel)} && isReaderRoute && !result.readerSettingsResetVisible) issues.push("reader settings reset not visible");
  if (${JSON.stringify(shouldCheckSettingsPanel)} && isReaderRoute && result.readerSettingsThemeButtonCount < 3) issues.push("reader settings theme controls missing");
  if (${JSON.stringify(shouldCheckSettingsPanel)} && isReaderRoute && result.readerSettingsPressedCount < 6) issues.push("reader settings selected states missing");
  if (${JSON.stringify(shouldCheckSettingsPanel)} && isReaderRoute && result.readerSettingsHasAudioLeakCopy) issues.push("reader settings audio leakage copy visible");
  if (shouldMockReaderApi && isReaderRoute && !result.readerContentsReachable) issues.push("reader contents not reachable");
  if (shouldMockReaderApi && isReaderRoute && result.readerAudioButtonVisible && !approvedAudioRoute) issues.push("reader local fixture exposed audio controls");
  if (shouldMockReaderApi && isReaderRoute && result.generatedAudioElementVisible && !approvedAudioRoute) issues.push("reader local fixture exposed audio element");
  if (shouldMockAudiobookPlayerApi && approvedAudioRoute && isReaderRoute && !result.readerAudioButtonVisible) issues.push("approved audiobook reader controls missing");
  if (shouldMockReaderApi && result.staticAudioSrcVisible) issues.push("reader static audio src visible");
  if (shouldMockReaderApi && isReaderRoute && !approvedAudioRoute && !result.readerAudioHiddenCopyVisible) issues.push("reader audio-hidden copy missing");
  if (result.consoleErrors.length) issues.push("console errors");
  return issues.map((issue) => ({ route: result.route, viewport: result.viewport, issue }));
});
const resultPayload = {
  skipped: false,
  playwright_import_status: playwrightImportStatus,
  browser_launch_status: browserLaunchStatus,
  browser_checks_required: true,
  browser_checks_completed: results.length,
  routes_attempted: routes.length * viewports.length,
  routes_completed: results.length,
  screenshotDir,
  results,
  failed_subchecks: blockers,
  blockers,
};
fs.writeFileSync(resultFile, JSON.stringify(resultPayload, null, 2));
console.log(JSON.stringify({
  skipped: false,
  playwright_import_status: playwrightImportStatus,
  browser_launch_status: browserLaunchStatus,
  browser_checks_required: true,
  browser_checks_completed: results.length,
  routes_attempted: routes.length * viewports.length,
  routes_completed: results.length,
  failed_subcheck_count: blockers.length,
  resultFile,
}, null, 2));
process.exit(blockers.length ? 1 : 0);
`);

  const result = spawnSync("node", [runnerPath], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  try {
    fs.unlinkSync(runnerPath);
  } catch {
    // Best effort cleanup only; a stale runner must not turn a real browser pass into failure.
  }
  let parsed = null;
  try {
    parsed = JSON.parse(result.stdout);
    if (parsed?.resultFile && fs.existsSync(parsed.resultFile)) {
      parsed = readJsonFile(parsed.resultFile, parsed);
    }
  } catch {
    parsed = {
      skipped: false,
      playwright_import_status: "unknown",
      browser_launch_status: "unknown",
      browser_checks_required: true,
      routes_attempted: routes.length * viewports.length,
      routes_completed: 0,
      failed_subchecks: [{ issue: "visual smoke runner output parse failed" }],
      blockers: [{ route: "*", viewport: "*", issue: "visual smoke runner output parse failed" }],
      stdout: result.stdout.slice(-2000),
      stderr: result.stderr.slice(-2000),
      status: result.status,
    };
  }
  if (result.status !== 0 && !parsed.blockers?.length) {
    parsed.blockers = [{ route: "*", viewport: "*", issue: "visual smoke runner exited non-zero" }];
    parsed.failed_subchecks = parsed.blockers;
  }
  return parsed;
}

const source = runSourceChecks();
const browser = runBrowserChecks();
const sourceBlockers = source.flatMap((check) => check.blockers.map((blocker) => ({ check: check.name, blocker })));
const browserBlockers = browser?.blockers || [];
const report = {
  generated_at: new Date().toISOString(),
  mode: visualSmokeMode,
  visual_phase: visualPhase || null,
  route_matrix: routeMatrix || null,
  base_url: baseUrl,
  routes,
  viewports: viewports.map((viewport) => `${viewport.width}x${viewport.height}`),
  source_checks: source,
  browser_checks: browser,
  playwright_import_status: browser?.playwright_import_status || "not_run",
  browser_launch_status: browser?.browser_launch_status || "not_run",
  browser_checks_required: true,
  browser_checks_completed: browser?.browser_checks_completed || 0,
  routes_attempted: browser?.routes_attempted || routes.length * viewports.length,
  routes_completed: browser?.routes_completed || 0,
  failed_subchecks: browser?.failed_subchecks || [],
  protection_bypass_configured: Boolean(protectionBypass),
  extra_header_names: Object.keys(extraHeaders).concat(protectionBypass ? ["x-vercel-protection-bypass"] : []),
  critical_blockers: [...sourceBlockers, ...browserBlockers],
  visual_smoke_status: sourceBlockers.length === 0 && browserBlockers.length === 0 ? "PASS" : "FAIL",
};
fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({
  visual_smoke_status: report.visual_smoke_status,
  mode: report.mode,
  playwright_import_status: report.playwright_import_status,
  browser_launch_status: report.browser_launch_status,
  routes_attempted: report.routes_attempted,
  routes_completed: report.routes_completed,
  failed_subchecks: report.failed_subchecks.length,
  critical_blockers: report.critical_blockers.length,
  report_path: reportPath,
}, null, 2));
if (report.critical_blockers.length) process.exit(1);
