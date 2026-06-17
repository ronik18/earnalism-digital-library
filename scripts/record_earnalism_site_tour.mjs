import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(SCRIPT_DIR, "..");
const args = new Set(process.argv.slice(2));
const baseUrl = (process.env.SITE_TOUR_BASE_URL || "https://theearnalism.com").replace(/\/+$/, "");
const apiUrl = normalizeApiUrl(process.env.SITE_TOUR_API_URL || "https://api.theearnalism.com/api");
const outputDir = path.resolve(process.env.SITE_TOUR_OUTPUT_DIR || "output/marketing/site-tour");
const tempVideoDir = path.join(outputDir, ".playwright-video");
const width = Number(process.env.SITE_TOUR_WIDTH || 1920);
const height = Number(process.env.SITE_TOUR_HEIGHT || 1080);
const zoom = Number(process.env.SITE_TOUR_ZOOM || 0.8);
const headed = process.env.SITE_TOUR_HEADED === "1";
const scorePath = path.resolve(process.env.SITE_TOUR_SCORE_PATH || path.join(ROOT_DIR, "assets/marketing/earnalism-site-tour-score.mp3"));
const englishPreferredSlugs = [
  process.env.SITE_TOUR_ENGLISH_SLUG,
  "the-principles-of-scientific-management",
  "pride-and-prejudice",
  "the-picture-of-dorian-gray",
  "dracula",
].filter(Boolean);
const bengaliPreferredSlugs = [
  process.env.SITE_TOUR_BENGALI_SLUG,
  "bolai",
  "chuti",
  "khudito-pashan",
  "kabuliwala",
].filter(Boolean);

const BENGALI_RE = /[\u0980-\u09FF]/;

if (args.has("--help") || args.has("-h")) {
  printHelp();
  process.exit(0);
}

function printHelp() {
  console.log(`
Record a premium Earnalism site-tour video.

Usage:
  npm run marketing:site-tour
  SITE_TOUR_HEADED=1 npm run marketing:site-tour
  SITE_TOUR_SCORE_PATH=/absolute/path/music.mp3 npm run marketing:site-tour

Environment:
  SITE_TOUR_BASE_URL       Default: https://theearnalism.com
  SITE_TOUR_API_URL        Default: https://api.theearnalism.com/api
  SITE_TOUR_OUTPUT_DIR     Default: output/marketing/site-tour
  SITE_TOUR_ENGLISH_SLUG   Optional explicit English reader slug
  SITE_TOUR_BENGALI_SLUG   Optional explicit Bengali reader slug
  SITE_TOUR_SCORE_PATH     Optional local music file for ffmpeg mix
  SITE_TOUR_HEADED=1       Show browser while recording
`);
}

function normalizeApiUrl(value) {
  const clean = String(value || "").replace(/\/+$/, "");
  return clean.endsWith("/api") ? clean : `${clean}/api`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function apiGet(pathname) {
  const response = await fetch(`${apiUrl}${pathname}`, {
    headers: { accept: "application/json" },
  });
  if (!response.ok) throw new Error(`GET ${pathname} failed with ${response.status}`);
  return response.json();
}

function isBengaliBook(book = {}) {
  return BENGALI_RE.test(`${book.title || ""} ${book.author || ""} ${book.category_slug || ""}`)
    || String(book.category_slug || "").toLowerCase().includes("bengali");
}

function isEnglishBook(book = {}) {
  return !isBengaliBook(book);
}

async function discoverBooks() {
  let books = [];
  try {
    const payload = await apiGet("/books");
    books = Array.isArray(payload) ? payload : payload.books || [];
  } catch (error) {
    console.warn(`[site-tour] Could not fetch /books: ${error.message}`);
  }

  const bySlug = new Map(books.map((book) => [book.slug, book]));
  const english = chooseBook(books, bySlug, englishPreferredSlugs, isEnglishBook);
  const bengali = chooseBook(books, bySlug, bengaliPreferredSlugs, isBengaliBook);

  return {
    books,
    englishSlug: english?.slug || englishPreferredSlugs[0],
    bengaliSlug: bengali?.slug || bengaliPreferredSlugs[0],
  };
}

function chooseBook(books, bySlug, preferredSlugs, predicate) {
  for (const slug of preferredSlugs) {
    const found = bySlug.get(slug);
    if (found) return found;
  }
  return books.find(predicate) || books[0] || null;
}

async function setZoom(page) {
  await page.evaluate((nextZoom) => {
    document.documentElement.style.zoom = String(nextZoom);
    document.documentElement.dataset.siteTourZoom = String(nextZoom);
  }, zoom).catch(() => {});
}

async function installTourLayer(page) {
  await setZoom(page);
  await page.addStyleTag({
    content: `
      #earnalism-video-tour-layer {
        position: fixed;
        inset: 0;
        z-index: 2147483000;
        pointer-events: none;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      .earnalism-video-tour-vignette {
        position: absolute;
        inset: auto 0 0 0;
        height: 42%;
        background: linear-gradient(0deg, rgba(20, 8, 12, 0.72), rgba(20, 8, 12, 0));
      }
      .earnalism-video-tour-card {
        position: absolute;
        left: 54px;
        bottom: 44px;
        width: min(680px, calc(100vw - 108px));
        padding: 24px 28px 26px;
        border: 1px solid rgba(216, 185, 122, 0.5);
        border-radius: 8px;
        background: rgba(26, 10, 15, 0.82);
        color: #fdfcf8;
        box-shadow: 0 28px 90px rgba(0, 0, 0, 0.32);
        backdrop-filter: blur(18px);
        opacity: 0;
        transform: translateY(10px);
        transition: opacity 320ms ease, transform 320ms ease;
      }
      .earnalism-video-tour-card.is-visible {
        opacity: 1;
        transform: translateY(0);
      }
      .earnalism-video-tour-eyebrow {
        color: #d8b97a;
        font-size: 12px;
        line-height: 1.2;
        letter-spacing: 0.22em;
        text-transform: uppercase;
      }
      .earnalism-video-tour-title {
        margin: 8px 0 0;
        color: #fdfcf8;
        font-family: Georgia, "Times New Roman", serif;
        font-size: 34px;
        font-weight: 400;
        line-height: 1.08;
        letter-spacing: 0;
      }
      .earnalism-video-tour-body {
        margin: 12px 0 0;
        max-width: 58ch;
        color: rgba(253, 252, 248, 0.84);
        font-size: 16px;
        line-height: 1.65;
      }
      .earnalism-video-tour-cursor {
        position: absolute;
        left: 0;
        top: 0;
        width: 30px;
        height: 30px;
        border: 2px solid rgba(216, 185, 122, 0.95);
        border-radius: 999px;
        background: rgba(92, 26, 43, 0.2);
        box-shadow: 0 0 0 8px rgba(216, 185, 122, 0.14), 0 10px 30px rgba(0, 0, 0, 0.24);
        transform: translate3d(72px, 72px, 0);
        transition: transform 520ms cubic-bezier(0.22, 1, 0.36, 1), opacity 220ms ease;
        opacity: 0.95;
      }
      .earnalism-video-tour-cursor::after {
        content: "";
        position: absolute;
        left: 11px;
        top: 11px;
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: #fdfcf8;
      }
      .earnalism-video-tour-cursor.is-clicking {
        transform: var(--tour-cursor-transform) scale(0.78);
      }
    `,
  }).catch(() => {});

  await page.evaluate(() => {
    if (window.__earnalismVideoTour) return;
    const layer = document.createElement("div");
    layer.id = "earnalism-video-tour-layer";
    layer.innerHTML = `
      <div class="earnalism-video-tour-vignette" aria-hidden="true"></div>
      <section class="earnalism-video-tour-card" aria-live="polite">
        <div class="earnalism-video-tour-eyebrow"></div>
        <h2 class="earnalism-video-tour-title"></h2>
        <p class="earnalism-video-tour-body"></p>
      </section>
      <div class="earnalism-video-tour-cursor" aria-hidden="true"></div>
    `;
    document.documentElement.appendChild(layer);

    const card = layer.querySelector(".earnalism-video-tour-card");
    const eyebrow = layer.querySelector(".earnalism-video-tour-eyebrow");
    const title = layer.querySelector(".earnalism-video-tour-title");
    const body = layer.querySelector(".earnalism-video-tour-body");
    const cursor = layer.querySelector(".earnalism-video-tour-cursor");

    window.__earnalismVideoTour = {
      caption(next) {
        eyebrow.textContent = next.eyebrow || "Earnalism";
        title.textContent = next.title || "";
        body.textContent = next.body || "";
        card.classList.add("is-visible");
      },
      clearCaption() {
        card.classList.remove("is-visible");
      },
      moveCursor(x, y) {
        const transform = `translate3d(${Math.round(x)}px, ${Math.round(y)}px, 0)`;
        cursor.style.setProperty("--tour-cursor-transform", transform);
        cursor.style.transform = transform;
      },
      clickCursor() {
        cursor.classList.add("is-clicking");
        window.setTimeout(() => cursor.classList.remove("is-clicking"), 220);
      },
    };
  });
}

async function preparePage(page) {
  await installTourLayer(page);
  await dismissSiteTour(page);
}

async function dismissSiteTour(page) {
  const tour = page.locator('[data-testid="first-visit-site-tour"]');
  if (await tour.count().catch(() => 0)) {
    const skip = page.getByRole("button", { name: /skip/i }).first();
    if (await skip.isVisible().catch(() => false)) {
      await skip.click().catch(() => {});
    }
  }
}

async function gotoScene(page, pathname, waitFor = "body") {
  await page.goto(`${baseUrl}${pathname}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector(waitFor, { timeout: 45000 }).catch(() => {});
  await preparePage(page);
  await page.waitForTimeout(700);
}

async function caption(page, eyebrow, title, body, duration = 2200) {
  await installTourLayer(page);
  await page.evaluate((payload) => window.__earnalismVideoTour?.caption(payload), { eyebrow, title, body });
  await page.waitForTimeout(duration);
}

async function moveCursorToLocator(page, locator, fallback = { x: 980, y: 540 }) {
  const box = await locator.boundingBox().catch(() => null);
  const x = box ? box.x + box.width / 2 : fallback.x;
  const y = box ? box.y + Math.min(box.height / 2, 80) : fallback.y;
  await page.evaluate(({ x: nextX, y: nextY }) => {
    window.__earnalismVideoTour?.moveCursor(nextX, nextY);
  }, { x, y });
  await page.mouse.move(x, y, { steps: 16 }).catch(() => {});
  await page.waitForTimeout(450);
}

async function clickWithCursor(page, locator, options = {}) {
  await moveCursorToLocator(page, locator, options.fallback);
  await page.evaluate(() => window.__earnalismVideoTour?.clickCursor());
  await locator.click({ timeout: options.timeout || 10000 }).catch(() => {});
  await page.waitForTimeout(options.after || 900);
}

async function smoothScroll(page, y, duration = 1000) {
  await page.evaluate(async ({ nextY, ms }) => {
    const startY = window.scrollY;
    const delta = nextY - startY;
    const start = performance.now();
    await new Promise((resolve) => {
      function frame(now) {
        const t = Math.min(1, (now - start) / ms);
        const eased = 1 - Math.pow(1 - t, 3);
        window.scrollTo(0, startY + delta * eased);
        if (t < 1) requestAnimationFrame(frame);
        else resolve();
      }
      requestAnimationFrame(frame);
    });
  }, { nextY: y, ms: duration });
}

async function tourHome(page) {
  await gotoScene(page, "/", '[data-testid="home-page"]');
  await caption(
    page,
    "Earnalism - Where Learning Becomes Earning",
    "Preview first. Pay only for reading time.",
    "A calm digital library and audiobook experience by Reo Enterprise, built for focused reading and confident discovery.",
    3800,
  );
  const heroCta = page.locator('[data-testid="hero-cta-read"]').first();
  if (await heroCta.isVisible().catch(() => false)) await moveCursorToLocator(page, heroCta, { x: 420, y: 600 });
  await smoothScroll(page, Math.floor(height * 0.74), 1200);
  await caption(
    page,
    "Live shelves",
    "Books load visually, then the reader takes over.",
    "The tour highlights public customer paths only: browsing, previews, page turns, synced audio, and safe pricing exploration.",
    3200,
  );
  await smoothScroll(page, Math.floor(height * 1.65), 1300);
  await caption(
    page,
    "Curated library",
    "Bengali classics, English literature, business, history, AI, and more.",
    "The campaign promise is measurable growth, not guaranteed outcomes: every CTA points to real reader behavior.",
    3200,
  );
}

async function tourLibrary(page) {
  await gotoScene(page, "/library?utm_source=site_tour&utm_medium=video&utm_campaign=100_day_growth", '[data-testid="library-page"]');
  await caption(
    page,
    "Browse",
    "Choose a shelf, search a title, start with a preview.",
    "This is the primary growth path for new readers from social posts, ads, newsletters, and community shares.",
    3000,
  );
  const search = page.locator('[data-testid="library-search"]').first();
  if (await search.isVisible().catch(() => false)) {
    await clickWithCursor(page, search, { after: 300 });
    await page.keyboard.type("classic", { delay: 45 }).catch(() => {});
    await page.waitForTimeout(1200);
    await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A").catch(() => {});
    await page.keyboard.press("Backspace").catch(() => {});
  }
  const firstCard = page.locator('[data-testid^="book-card-"]').first();
  if (await firstCard.isVisible().catch(() => false)) {
    await moveCursorToLocator(page, firstCard, { x: 640, y: 520 });
  }
  await page.waitForTimeout(900);
}

async function tourReader(page, slug, label) {
  if (!slug) return false;
  await gotoScene(page, `/reader/${encodeURIComponent(slug)}`, "body");
  await page.waitForFunction(() => (
    Boolean(document.querySelector('[data-testid="reader-page"]'))
    || document.body.innerText.includes("Reading access")
    || Boolean(document.querySelector('[data-testid="reader-not-found"]'))
  ), null, { timeout: 45000 }).catch(() => {});
  await preparePage(page);

  const freePreview = page.getByRole("button", { name: /read free preview/i }).first();
  if (await freePreview.isVisible().catch(() => false)) {
    await clickWithCursor(page, freePreview, { after: 1200 });
    await preparePage(page);
  }

  const unlocked = await page.locator('[data-testid="reader-page"]').first().isVisible().catch(() => false);
  if (!unlocked) {
    await caption(
      page,
      `${label} reader`,
      "Preview access is protected.",
      "Locked paid chapters are intentionally not bypassed in the marketing recording.",
      2500,
    );
    return false;
  }

  await caption(
    page,
    `${label} reader`,
    "A quiet reading surface with page-level navigation.",
    "The tour shows real public reader rendering without credentials, private data, or admin screens.",
    3000,
  );

  const nextButton = page.getByRole("button", { name: /next page|next/i }).last();
  if (await nextButton.isEnabled().catch(() => false)) {
    await clickWithCursor(page, nextButton, { after: 1300, fallback: { x: 1440, y: 980 } });
    await caption(page, "Reader controls", "Next page keeps momentum.", "Page transitions stay focused on the words, not the chrome.", 1800);
  }

  const prevButton = page.getByRole("button", { name: /prev page|prev/i }).first();
  if (await prevButton.isEnabled().catch(() => false)) {
    await clickWithCursor(page, prevButton, { after: 1200, fallback: { x: 470, y: 980 } });
    await caption(page, "Reader controls", "Previous page returns instantly.", "This gives the recording a visible proof point for navigation and reader comfort.", 1800);
  }

  const played = await tryAudioPlayback(page, label);
  if (!played) {
    await caption(
      page,
      `${label} audio`,
      "Audio is skipped when unavailable.",
      "The recorder checks for the public synced-audio control and continues safely if a title has no playable asset.",
      2100,
    );
  }
  return true;
}

async function tryAudioPlayback(page, label) {
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const audioButton = page.locator(".reader-audio-button").first();
    if (await audioButton.isVisible().catch(() => false)) {
      const disabled = await audioButton.isDisabled().catch(() => true);
      if (!disabled) {
        await caption(
          page,
          `${label} audiobook`,
          "Tap Play for synced narration.",
          "The hidden audio element uses metadata/range-friendly loading; the page highlights text as audio advances when timestamps are available.",
          2300,
        );
        await clickWithCursor(page, audioButton, { after: 4200, fallback: { x: 970, y: 978 } });
        const pauseButton = page.locator(".reader-audio-button").first();
        if (await pauseButton.isVisible().catch(() => false)) {
          await clickWithCursor(page, pauseButton, { after: 700, fallback: { x: 970, y: 978 } });
        }
        return true;
      }
    }
    const nextButton = page.getByRole("button", { name: /next page|next/i }).last();
    if (await nextButton.isEnabled().catch(() => false)) {
      await clickWithCursor(page, nextButton, { after: 900, fallback: { x: 1440, y: 980 } });
    } else {
      break;
    }
  }
  return false;
}

async function tourPricing(page) {
  await gotoScene(page, "/pricing?source=site_tour_demo&utm_source=site_tour&utm_medium=video&utm_campaign=100_day_growth", '[data-testid="pricing-page"]');
  await caption(
    page,
    "Safe pricing walkthrough",
    "Pay only for reading time.",
    "This video never processes a real payment. It demonstrates the conversion path and where a signed-in reader would choose a reading-time pack.",
    3600,
  );
  const pack = page.locator('.card-elegant[data-testid^="pack-"]').first();
  if (await pack.isVisible().catch(() => false)) {
    await moveCursorToLocator(page, pack, { x: 550, y: 520 });
  }
  const buy = page.locator('button[data-testid$="-buy"]').first();
  if (await buy.isVisible().catch(() => false)) {
    await moveCursorToLocator(page, buy, { x: 550, y: 735 });
  }
  await caption(
    page,
    "Growth CTA",
    "Preview first. Then buy time when the value is clear.",
    "Campaign analytics should track source, preview starts, reader opens, audio plays, pricing starts, and purchases.",
    3000,
  );
}

async function tourFinalCta(page) {
  await gotoScene(page, "/library?utm_source=site_tour&utm_medium=video&utm_campaign=100_day_growth&utm_content=final_cta", '[data-testid="library-page"]');
  await caption(
    page,
    "Start reading",
    "Read beautifully. Listen deeply.",
    "Earnalism invites readers to preview a book first, then pay only for the reading time they need.",
    4300,
  );
}

function commandExists(command) {
  const result = spawnSync(command, ["-version"], { stdio: "ignore" });
  return result.status === 0;
}

function mixScoreIfAvailable(rawVideoPath) {
  if (!fs.existsSync(scorePath)) {
    return { mixedPath: null, message: `No background score found at ${scorePath}` };
  }
  if (!commandExists("ffmpeg")) {
    return { mixedPath: null, message: "ffmpeg not found; raw video recorded without score" };
  }

  const mixedPath = path.join(outputDir, "earnalism-site-tour-with-score.webm");
  const result = spawnSync("ffmpeg", [
    "-y",
    "-i", rawVideoPath,
    "-stream_loop", "-1",
    "-i", scorePath,
    "-shortest",
    "-filter_complex", "[1:a]volume=0.16[a]",
    "-map", "0:v:0",
    "-map", "[a]",
    "-c:v", "copy",
    "-c:a", "libopus",
    mixedPath,
  ], { stdio: "inherit" });

  if (result.status !== 0) {
    return { mixedPath: null, message: "ffmpeg mix failed; raw video remains available" };
  }
  return { mixedPath, message: "Background score mixed successfully" };
}

async function main() {
  fs.mkdirSync(tempVideoDir, { recursive: true });
  const discovered = await discoverBooks();

  if (args.has("--dry-run")) {
    console.log(JSON.stringify({
      baseUrl,
      apiUrl,
      outputDir,
      zoom,
      englishSlug: discovered.englishSlug,
      bengaliSlug: discovered.bengaliSlug,
      bookCount: discovered.books.length,
      scorePath,
    }, null, 2));
    return;
  }

  const browser = await chromium.launch({ headless: !headed });
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    colorScheme: "light",
    recordVideo: { dir: tempVideoDir, size: { width, height } },
  });

  await context.addInitScript((tourZoom) => {
    try {
      window.localStorage.setItem("earnalism:first-visit-site-tour:v1", "complete");
    } catch (_) {}
    const applyZoom = () => {
      document.documentElement.style.zoom = String(tourZoom);
      document.documentElement.dataset.siteTourZoom = String(tourZoom);
    };
    applyZoom();
    document.addEventListener("DOMContentLoaded", applyZoom);
  }, zoom);

  const page = await context.newPage();
  page.setDefaultTimeout(20000);

  try {
    await tourHome(page);
    await tourLibrary(page);
    await tourReader(page, discovered.englishSlug, "English book");
    await tourReader(page, discovered.bengaliSlug, "Bengali book");
    await tourPricing(page);
    await tourFinalCta(page);
  } finally {
    await page.evaluate(() => window.__earnalismVideoTour?.clearCaption()).catch(() => {});
    const video = page.video();
    await context.close();
    await browser.close();

    const recordedPath = await video.path();
    const rawPath = path.join(outputDir, "earnalism-site-tour-raw.webm");
    fs.copyFileSync(recordedPath, rawPath);
    const scoreResult = mixScoreIfAvailable(rawPath);
    console.log(JSON.stringify({
      ok: true,
      rawVideo: rawPath,
      scoredVideo: scoreResult.mixedPath,
      scoreMessage: scoreResult.message,
      englishSlug: discovered.englishSlug,
      bengaliSlug: discovered.bengaliSlug,
      zoom,
    }, null, 2));
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
