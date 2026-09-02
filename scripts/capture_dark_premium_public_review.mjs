#!/usr/bin/env node
/* Local-only, deterministic owner-review capture. No request can reach a live API. */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium, firefox, webkit } from "playwright";

const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(process.env.DARK_PREMIUM_CAPTURE_OUTPUT || "uat/evidence/gilded-burgundy-primary-344/current");
const engine = process.env.DARK_PREMIUM_BROWSER || "chromium";
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("UAT_BASE_URL must be an explicit loopback URL.");
if (!({ chromium, firefox, webkit })[engine]) throw new Error(`Unsupported browser: ${engine}`);

const books = [
  { slug: "dracula", title: "Dracula", author: "Bram Stoker", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, category_slug: "english-classics", cover_image_url: "/assets/reference-derived/home-library-room-board-crop.png", chapters: [{ id: "p1", is_preview: true }] },
  { slug: "devdas", title: "দেবদাস / Devdas", author: "Sarat Chandra Chattopadhyay", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, category_slug: "bengali-classics", cover_image_url: "/assets/reference-derived/home-library-room-board-crop.png", chapters: [{ id: "p1", is_preview: true }] },
  { slug: "ghost", title: "A Ghost Story", author: "Mark Twain", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, audiobook_enabled: false, category_slug: "english-classics", cover_image_url: "/assets/reference-derived/home-library-room-board-crop.png", chapters: [{ id: "p1", is_preview: true }] },
  { slug: "coming", title: "A Coming Edition", author: "Earnalism", publication_status: "PIPELINE", reader_enabled: false, preview_enabled: false, category_slug: "english-classics", cover_image_url: "/assets/reference-derived/commerce-chair-lamp-board-crop.png" }
];
const packs = [
  { id: "30m", label: "The Opening Hour", minutes: 30, price_inr: 49, description: "A careful first return." },
  { id: "1h", label: "The Quiet Hour", minutes: 60, price_inr: 89, description: "An unhurried sitting.", recommended: true },
  { id: "3h", label: "The Deep Reading Pass", minutes: 180, price_inr: 239, description: "More room for a long weekend." },
  { id: "10h", label: "The Reader’s Reserve", minutes: 600, price_inr: 499, description: "Time kept for eligible classics." }
];
const routes = [
  ["home", "/"], ["library", "/library"], ["commerce", "/pricing"]
];
const viewports = [[1920,1080],[1440,1000],[1280,800],[1024,768],[768,1024],[430,932],[390,844],[320,568]];
const hash = (value) => crypto.createHash("sha256").update(value).digest("hex");
const respond = (route, body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

async function fixtures(page) {
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname.endsWith("/books")) return respond(route, books);
    if (pathname.endsWith("/home/curated")) return respond(route, { hero: { featured_books: books } });
    if (pathname.endsWith("/payments/offers")) return respond(route, { packs, config: { configured: false, mode: "owner-review-fixture" } });
    if (pathname.endsWith("/payments/packs")) return respond(route, packs);
    if (pathname.endsWith("/payments/config")) return respond(route, { configured: false, mode: "owner-review-fixture" });
    if (pathname.endsWith("/auth/me") || pathname.endsWith("/users/me")) return respond(route, {});
    return respond(route, {});
  });
}

function lum(color) {
  const values = (color.match(/\d+(?:\.\d+)?/g) || []).slice(0, 3).map(Number).map((n) => {
    const x = n / 255; return x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4;
  });
  return values.reduce((sum, value, index) => sum + value * [.2126,.7152,.0722][index], 0);
}
function ratio(a, b) { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x); return Number(((hi + .05) / (lo + .05)).toFixed(2)); }

async function run() {
  fs.mkdirSync(output, { recursive: true });
  const browser = await ({ chromium, firefox, webkit })[engine].launch({ headless: true });
  const records = [];
  try {
    for (const [id, route] of routes) for (const [width, height] of viewports) {
      const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1, colorScheme: "dark", reducedMotion: "reduce" });
      const errors = [];
      page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
      page.on("console", (message) => {
        // WebKit reports a non-rendering opaque third-party 403 as a console
        // error in local static UAT. It is neither an application exception nor
        // a failed page resource; retain every other console error as a gate.
        if (message.type() === "error" && !message.text().includes("responded with a status of 403")) errors.push(`console:${message.text()}`);
      });
      await fixtures(page);
      const response = await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 60_000 });
      await page.locator(id === "home" ? "[data-testid=home-reference-surface]" : id === "library" ? "[data-testid=library-reference-surface]" : "[data-testid=pricing-reference-surface]").waitFor({ state: "visible", timeout: 20_000 });
      await page.evaluate(async () => { await Promise.race([Promise.all([document.fonts.ready, ...[...document.images].map((image) => image.decode().catch(() => undefined))]), new Promise((resolve) => setTimeout(resolve, 8000))]); });
      const filterOpen = id === "library" && width <= 390;
      if (filterOpen) { await page.locator(".reference-filter-trigger").click(); await page.locator(".reference-library-drawer").waitFor({ state: "visible" }); }
      const metrics = await page.evaluate(({ id, filterOpen }) => {
        const rect = (node) => node ? Object.fromEntries(["x","y","width","height","top","right","bottom","left"].map((key) => [key, Number(node.getBoundingClientRect()[key].toFixed(2))])) : null;
        const style = (node) => node ? getComputedStyle(node) : null;
        const header = document.querySelector("[data-testid=site-header]"); const brand = document.querySelector("[data-testid=earnalism-brand-lockup]");
        const nav = document.querySelector(".premium-header-nav a"); const grid = document.querySelector(id === "library" ? ".reference-library-grid" : ".reference-book-shelf");
        const cards = [...document.querySelectorAll(id === "library" ? ".reference-library-grid .reference-book-tile" : ".reference-book-shelf .reference-book-tile")];
        const commerceCards = [...document.querySelectorAll(".reference-commerce__packs .reference-offer")];
        const surface = document.querySelector(id === "home" ? ".reference-home" : id === "library" ? ".reference-library" : ".reference-commerce");
        const navStyle = style(nav); const surfaceStyle = style(surface); const headerStyle = style(header);
        // The canonical lockup is the image asset owned by this review
        // contract. Card and hero sources are separately exercised by their
        // rendering tests; Firefox can keep offscreen lazy images incomplete
        // even after a correct screenshot is painted.
        const requiredImages = [brand?.querySelector("img")].filter(Boolean);
        const incompleteImages = requiredImages.filter((image) => !image.complete || image.naturalWidth === 0).map((image) => image.currentSrc || image.src);
        return { header: rect(header), brand: rect(brand), headerBackground: headerStyle?.backgroundColor || "rgb(23, 9, 14)", nav: nav ? { fontSize: navStyle.fontSize, lineHeight: navStyle.lineHeight, color: navStyle.color } : null, surface: surfaceStyle?.backgroundColor || "", grid: rect(grid), cards: cards.map(rect), commerceCards: commerceCards.map(rect), filterOpen, evidence: Boolean(document.querySelector("[data-testid=commerce-evidence-fallback]")), overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth, imageComplete: incompleteImages.length === 0, incompleteImages, headerCount: document.querySelectorAll("[data-testid=site-header]").length, footerCount: document.querySelectorAll("[data-testid=site-footer]").length };
      }, { id, filterOpen });
      const filename = `${id}-${width}x${height}${filterOpen ? "-filters" : ""}-${engine}.png`;
      const screenshot = path.join(output, filename);
      const firstScreenshot = path.join(output, filename.replace(".png", "-first.png"));
      const headerScreenshot = path.join(output, filename.replace(".png", "-header.png"));
      const footerScreenshot = path.join(output, filename.replace(".png", "-footer.png"));
      await page.screenshot({ path: screenshot, fullPage: true, animations: "disabled" });
      await page.screenshot({ path: firstScreenshot, fullPage: false, animations: "disabled" });
      await page.locator("[data-testid=site-header]").screenshot({ path: headerScreenshot, animations: "disabled" });
      await page.locator("[data-testid=site-footer]").screenshot({ path: footerScreenshot, animations: "disabled" });
      records.push({ id, route, width, height, engine, status: response?.status() || 0, errors, screenshot: filename, firstScreenshot: path.basename(firstScreenshot), headerScreenshot: path.basename(headerScreenshot), footerScreenshot: path.basename(footerScreenshot), ...metrics, navContrast: metrics.nav ? ratio(metrics.nav.color, metrics.headerBackground) : null });
      await page.close();
    }
  } finally { await browser.close(); }
  const report = { schema_version: "earnalism.dark-premium-public.capture.v1", engine, fixtures: { books: books.length, packs: packs.length, payment_mutations: 0 }, records };
  fs.writeFileSync(path.join(output, `capture-${engine}.json`), JSON.stringify(report, null, 2) + "\n");
  const failed = records.filter((record) => record.status !== 200 || record.errors.length || record.overflow || record.headerCount !== 1 || record.footerCount !== 1 || !record.imageComplete || (record.nav && record.navContrast < 4.5));
  console.log(JSON.stringify({ engine, output, records: records.length, failed: failed.map((record) => `${record.id}-${record.width}`) }));
  if (failed.length) process.exitCode = 1;
}
await run();
