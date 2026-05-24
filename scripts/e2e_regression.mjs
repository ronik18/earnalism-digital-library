import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const baseUrl = (process.env.E2E_BASE_URL || "https://theearnalism.com").replace(/\/$/, "");
const apiUrl = (process.env.E2E_API_URL || "https://api.theearnalism.com").replace(/\/$/, "");
const outputDir = path.resolve(process.env.E2E_OUTPUT_DIR || "test-results/regression");
const isLocalFrontend = /^https?:\/\/(?:127\.0\.0\.1|localhost|\[::1\])/i.test(baseUrl);

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

async function installApiProxy(page) {
  if (!isLocalFrontend) return;
  await page.route(`${apiUrl}/api/**`, async (route) => {
    try {
      const request = route.request();
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
  await page.waitForSelector('[data-testid^="live-cover-preview-"]', { timeout: 30000 });
  await page.waitForTimeout(900);
  const home = await page.evaluate(() => {
    const band = document.querySelector(".live-cover-showcase--band");
    const cards = [...document.querySelectorAll('[data-testid^="live-cover-preview-"]')].map((link) => ({
      href: link.getAttribute("href"),
      slug: link.getAttribute("href")?.replace(/^\/reader\//, ""),
      title: link.querySelector(".live-cover-card__title")?.textContent?.trim(),
    }));
    const bandRect = band?.getBoundingClientRect().toJSON();
    const visiblePreviewPills = [...document.querySelectorAll(".live-cover-card__preview")].filter((pill) => {
      const style = getComputedStyle(pill);
      return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) > 0.5;
    }).length;
    return {
      viewportWidth: window.innerWidth,
      bandRect,
      cards,
      visiblePreviewPills,
    };
  });
  assert(home.bandRect, "home slideshow band is missing");
  assert(Math.round(home.bandRect.x) === 0, `home slideshow is not flush-left: ${home.bandRect.x}`);
  assert(Math.abs(home.bandRect.width - home.viewportWidth) <= 2, `home slideshow is not full width: ${home.bandRect.width}/${home.viewportWidth}`);
  assert(home.cards.length > 0, "home slideshow has no live book cards");
  assert(home.cards.every((card) => card.href?.startsWith("/reader/")), `one or more slideshow cards do not open readers: ${JSON.stringify(home.cards)}`);
  assert(home.visiblePreviewPills >= home.cards.length, "preview affordance is not visible on every primary card");
  const firstSlug = home.cards[0].slug;
  assert(firstSlug, "could not infer first live book slug from slideshow");
  const homeScreenshot = await snapshot(page, "home");

  await gotoAppPath(page, "/library");
  await page.waitForSelector('[data-testid^="book-card-"], [data-testid="single-book-spotlight"]', { timeout: 30000 });
  const library = await page.evaluate(() => ({
    hasGrid: Boolean(document.querySelector('[data-testid="books-grid"], [data-testid="single-book-spotlight"]')),
    previewLinks: [...document.querySelectorAll('[data-testid^="card-preview-"], a[href^="/reader/"]')]
      .slice(0, 20)
      .map((link) => link.getAttribute("href")),
  }));
  assert(library.hasGrid, "library did not render books");
  assert(library.previewLinks.some((href) => href?.startsWith("/reader/")), "library has no reader preview CTA");

  await gotoAppPath(page, `/book/${firstSlug}`);
  await page.waitForSelector('[data-testid="book-page"]', { timeout: 30000 });
  const bookDetail = await page.evaluate((slug) => ({
    previewHref: document.querySelector('[data-testid="bottom-read-preview"]')?.getAttribute("href"),
    paymentHref: document.querySelector('[data-testid="bottom-buy-reading-time"]')?.getAttribute("href"),
    hasPaymentSection: Boolean(document.querySelector('[data-testid="preview-payment-section"]')),
    rawBodyIncludesRightsMetadata: document.body.innerText.includes("rights_metadata"),
    slug,
  }), firstSlug);
  assert(bookDetail.previewHref === `/reader/${firstSlug}`, `book preview CTA mismatch: ${bookDetail.previewHref}`);
  assert(bookDetail.paymentHref?.includes(`book=${firstSlug}`), `payment CTA does not preserve book slug: ${bookDetail.paymentHref}`);
  assert(bookDetail.hasPaymentSection, "book detail payment section missing");
  assert(!bookDetail.rawBodyIncludesRightsMetadata, "internal rights metadata leaked into book page");

  await gotoAppPath(page, `/reader/${firstSlug}`);
  await page.waitForFunction(() => (
    Boolean(document.querySelector('[data-testid="reader-page"]'))
    || document.body.innerText.includes("Reading access")
  ), null, { timeout: 30000 });
  const reader = await page.evaluate(() => ({
    unlocked: Boolean(document.querySelector('[data-testid="reader-page"]')),
    locked: document.body.innerText.includes("Reading access"),
    hasSecureReader: Boolean(document.querySelector(".secure-reader")),
    hasReaderCanvas: Boolean(document.querySelector(".reader-canvas")),
  }));
  assert(reader.unlocked || reader.locked, "reader route did not render an access state");
  assert(reader.locked || reader.hasSecureReader || reader.hasReaderCanvas, "reader unlocked without secure reader/canvas");

  await browser.close();
  console.log(JSON.stringify({
    ok: true,
    baseUrl,
    firstSlug,
    homeCards: home.cards.length,
    homeScreenshot,
    consoleIssues: consoleIssues.slice(0, 10),
  }, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
