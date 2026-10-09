#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = String(process.env.HEADER_REVIEW_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(process.env.HEADER_REVIEW_OUTPUT || "/tmp/pr471-canonical-header-evidence");
// For pull_request workflows, GITHUB_SHA is the synthetic merge ref. Bind the
// screenshots to the checked-out PR head supplied explicitly by the workflow.
const headSha = process.env.PR_HEAD_SHA || execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
const officialBrandAsset = fs.readFileSync(path.resolve("frontend/public/assets/brand/earnalism-brand-lockup.png"));
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("HEADER_REVIEW_BASE_URL must be an isolated loopback build.");
fs.mkdirSync(output, { recursive: true });

const CANONICAL_LOGO_PATH = "/assets/brand/earnalism-brand-lockup.png";
const APPROVED_RESPONSIVE_LOGO_PATH = /^\/assets\/performance\/earnalism-brand-lockup-(?:320|640)\.(?:avif|webp)$/;
const BRAND_ALT = "The Earnalism — Read. Reflect. Remember.";
const isApprovedLogoSource = (value) => {
  const pathname = new URL(value, baseUrl).pathname;
  return pathname === CANONICAL_LOGO_PATH || APPROVED_RESPONSIVE_LOGO_PATH.test(pathname);
};

const navLabels = ["Home", "Library", "Bengali Classics", "English Classics", "Audiobooks", "Reading Pass", "Blog", "About"];
const activeLabelByState = {
  home: "Home", library: "Library", "bengali-classics": "Bengali Classics", "english-classics": "English Classics",
  audiobooks: "Audiobooks", "reading-pass": "Reading Pass", journal: "Blog", "journal-article": "Blog", about: "About",
};
const routes = [
  { id: "home", path: "/" },
  { id: "library", path: "/library" },
  { id: "bengali-classics", path: "/library?language=bn&availability=reader-ready" },
  { id: "english-classics", path: "/library?language=en" },
  { id: "audiobooks", path: "/library?availability=approved-audiobook" },
  { id: "book-detail", path: "/book/a-ghost-story" },
  { id: "reading-pass", path: "/pricing" },
  { id: "journal", path: "/journal" },
  { id: "journal-article", path: "/journal/how-reading-shapes-better-founders" },
  { id: "about", path: "/about" },
  { id: "contact", path: "/contact" },
  { id: "account", path: "/account?visual-fixture=1" },
  { id: "login", path: "/login" },
  { id: "signup", path: "/signup" },
  { id: "privacy", path: "/privacy" },
  { id: "terms", path: "/terms" },
  { id: "copyright", path: "/copyright" },
  // Render the design fixture through an approved live route; Dracula stays fail-closed.
  { id: "reader", path: "/reader/a-ghost-story?visual-fixture=1" },
  { id: "listener", path: "/listener/a-ghost-story?visual-fixture=1" },
];
const viewports = [
  { width: 1440, height: 900 }, { width: 1280, height: 720 }, { width: 1024, height: 768 },
  { width: 768, height: 1024 }, { width: 390, height: 844 }, { width: 844, height: 390 },
];
const fullPageScreenshotWidths = new Set([1440, 1024, 390]);
const book = {
  slug: "a-ghost-story", title: "A Ghost Story", title_en: "A Ghost Story", author: "Mark Twain", language: "en",
  publication_status: "LIVE_APPROVED", reader_enabled: true, public_route: "/book/a-ghost-story", reader_url: "/reader/a-ghost-story",
  preview_enabled: true, preview_url: "/reader/a-ghost-story", chapters: [{ id: "a-ghost-story-chapter-1", title: "A Ghost Story", is_preview: true }],
  cover_image_url: "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1788115329/earnalism/covers/front/cover_candidate_controlled-a-ghost-story-d79e673971bf6de537d4886877d9e9daedd08efeeff467af0b2f9fbe43e52742.png", description: "A live reader edition for deterministic local review.",
};

const editorialSource = JSON.parse(fs.readFileSync("frontend/static-seo/editorial-public.json", "utf8"));
const editorialArticle = editorialSource.articles.find((article) => article.slug === "how-reading-shapes-better-founders");
assert.ok(editorialArticle, "Canonical public editorial fixture is present");
const editorialPost = { ...editorialArticle, created_at: editorialArticle.published_at, content: editorialArticle.excerpt };

const browser = await chromium.launch({ headless: true });
const captures = [];
try {
  for (const routeInfo of routes) {
    for (const viewport of viewports) {
      const context = await browser.newContext({ viewport, deviceScaleFactor: 1, reducedMotion: "reduce", serviceWorkers: "block" });
      const page = await context.newPage();
      const pageErrors = [];
      const consoleErrors = [];
      const requestFailures = [];
      const badResponses = [];
      page.on("pageerror", (error) => pageErrors.push(error.message));
      page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
      page.on("requestfailed", (request) => requestFailures.push({ url: request.url(), error: request.failure()?.errorText || "unknown" }));
      page.on("response", (response) => { if (response.status() >= 400) badResponses.push({ url: response.url(), status: response.status() }); });
      await context.route("**/*", async (requestRoute) => {
        const requestUrl = requestRoute.request().url();
        const url = new URL(requestUrl);
        if (url.pathname === "/assets/brand/earnalism-brand-lockup.png") return requestRoute.fulfill({ status: 200, contentType: "image/png", body: officialBrandAsset });
        if (url.pathname.includes("/api/")) {
          const pathname = url.pathname.slice(url.pathname.indexOf("/api/") + 4);
          let body = {};
          if (pathname === "/settings") body = {};
          if (pathname === "/blog") body = [editorialPost];
          if (pathname === `/blog/${editorialPost.slug}`) body = editorialPost;
          if (pathname === `/blog/${editorialPost.slug}/discussion`) body = { likes: 0, comments: [] };
          if (pathname === "/books") body = [book];
          if (pathname === "/books/a-ghost-story") body = book;
          if (pathname === "/payments/offers") body = { packs: [{ id: "30", minutes: 30, price_inr: 49 }, { id: "60", minutes: 60, price_inr: 89 }, { id: "180", minutes: 180, price_inr: 239 }, { id: "600", minutes: 600, price_inr: 499 }], config: { configured: false, mode: "review" } };
          return requestRoute.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
        }
        if (/^https?:\/\//.test(requestUrl) && !["127.0.0.1", "localhost"].includes(url.hostname) && url.hostname !== "res.cloudinary.com") return requestRoute.abort();
        return requestRoute.continue();
      });
      await page.goto(`${baseUrl}${routeInfo.path}`, { waitUntil: "domcontentloaded" });
      const header = page.locator('header[data-testid="site-header"]').first();
      await header.waitFor({ state: "visible", timeout: 15000 });
      await page.evaluate(() => document.fonts?.ready);
      await page.waitForTimeout(300);

      const headerInfo = await header.evaluate((node) => {
        const rect = node.getBoundingClientRect();
        const logo = node.querySelector('[data-brand-asset="earnalism-brand-lockup.png"] img');
        const visible = (selector) => {
          const element = node.querySelector(selector);
          if (!element) return false;
          const style = getComputedStyle(element);
          return style.display !== "none" && style.visibility !== "hidden" && element.getClientRects().length > 0;
        };
        const firstControl = node.querySelector(window.innerWidth >= 1280 ? '.premium-header-nav--desktop > a' : '[data-testid="mobile-header-search"]');
        return {
          logo_right: logo.getBoundingClientRect().right,
          control_left: firstControl.getBoundingClientRect().left,
          nav_font_weight: getComputedStyle(node.querySelector('.premium-header-nav--desktop > a')).fontWeight,
          nav_font_family: getComputedStyle(node.querySelector('.premium-header-nav--desktop > a')).fontFamily,
          background: getComputedStyle(node).backgroundColor,
          height: Math.round(rect.height),
          width: Math.round(rect.width),
          logo_asset: node.querySelector('[data-brand-asset="earnalism-brand-lockup.png"]')?.getAttribute("data-brand-asset") || "",
          logo_width: logo ? Math.round(logo.getBoundingClientRect().width) : 0,
          logo_natural_width: logo?.naturalWidth || 0,
          logo_declared_src: logo?.getAttribute("src") || "",
          logo_src: logo?.currentSrc || logo?.src || "",
          logo_alt: logo?.getAttribute("alt") || "",
          header_scroll_width: node.scrollWidth,
          header_client_width: node.clientWidth,
          public_nav_labels: [...node.querySelectorAll('.premium-header-nav--desktop > a[data-nav-key]')].map((link) => link.textContent.trim()),
          active_public_nav_labels: [...node.querySelectorAll('.premium-header-nav--desktop > a[data-nav-key][aria-current="page"]')].map((link) => link.textContent.trim()),
          has_search_field: visible(".premium-header-search input"),
          has_mobile_search: visible('[data-testid="mobile-header-search"]'),
          has_immersive_search: visible('[aria-label="Search library"]'),
        };
      });
      assert.ok(headerInfo.logo_right <= headerInfo.control_left, `${routeInfo.id}: logo/control collision`);
      if (routeInfo.id === "reading-pass") {
        assert.equal(await page.locator('.rp-fact-rings > div:nth-child(2) > span').innerText(), "NO");
        assert.equal(await page.locator('.rp-fact-rings > div:nth-child(2) > strong').innerText(), "auto-renewals");
      }
      assert.equal(headerInfo.nav_font_weight, "600", `${routeInfo.id}: shared navigation weight`);
      assert.ok(headerInfo.nav_font_family.includes("Outfit"), `${routeInfo.id}: shared navigation font`);
      assert.equal(headerInfo.background, "rgb(255, 249, 238)", `${routeInfo.id}: shared parchment background`);
      assert.equal(headerInfo.logo_asset, "earnalism-brand-lockup.png", `${routeInfo.id} ${viewport.width}: canonical brand asset`);
      assert.equal(new URL(headerInfo.logo_declared_src, baseUrl).pathname, CANONICAL_LOGO_PATH, `${routeInfo.id} ${viewport.width}: canonical master remains the image fallback`);
      assert.ok(isApprovedLogoSource(headerInfo.logo_src), `${routeInfo.id} ${viewport.width}: only the canonical master or an approved responsive derivative may render`);
      assert.equal(headerInfo.logo_alt, BRAND_ALT, `${routeInfo.id} ${viewport.width}: brand asset keeps its accessible name`);
      assert.ok(headerInfo.logo_natural_width > 0, `${routeInfo.id} ${viewport.width}: logo loaded`);
      assert.ok(headerInfo.header_scroll_width <= headerInfo.header_client_width, `${routeInfo.id} ${viewport.width}: header overflow`);
      const expectedHeaderHeight = viewport.width >= 1280 ? 104 : viewport.width >= 768 ? 96 : 80;
      assert.ok(Math.abs(headerInfo.height - expectedHeaderHeight) <= 1, `${routeInfo.id} ${viewport.width}: header height ${headerInfo.height}px`);
      const expectedWidth = viewport.width >= 1280 ? [320, 320] : viewport.width >= 768 ? [288, 288] : [Math.min(256, viewport.width - 136), Math.min(256, viewport.width - 136)];
      assert.ok(headerInfo.logo_width >= expectedWidth[0] && headerInfo.logo_width <= expectedWidth[1], `${routeInfo.id} ${viewport.width}: logo width ${headerInfo.logo_width}`);
      const expectedNavLabels = navLabels;
      if (viewport.width >= 1280) assert.deepEqual(headerInfo.public_nav_labels, expectedNavLabels, `${routeInfo.id}: desktop nav labels/order`);
      if (viewport.width >= 1280) assert.deepEqual(headerInfo.active_public_nav_labels, activeLabelByState[routeInfo.id] ? [activeLabelByState[routeInfo.id]] : [], `${routeInfo.id}: single route-aware active item`);
      if (viewport.width >= 1440) assert.equal(headerInfo.has_search_field, true, `${routeInfo.id}: shared desktop search`);
      if (viewport.width < 1440) assert.equal(headerInfo.has_mobile_search, true, `${routeInfo.id}: shared mobile search`);

      let menuLabels = [...headerInfo.public_nav_labels];
      if (viewport.width < 1280) {
        const menuToggle = header.locator('[data-testid="mobile-menu-toggle"], .experience-header__menu-toggle').first();
        await menuToggle.click();
        const menu = page.locator("#mobile-menu, #experience-header-menu").first();
        await menu.waitFor({ state: "visible" });
        menuLabels = await menu.locator("a").allTextContents();
        const canonicalMenuLabels = await menu.locator("a[data-nav-key]").allTextContents();
        assert.deepEqual(canonicalMenuLabels.map((label) => label.trim()), expectedNavLabels, `${routeInfo.id} ${viewport.width}: exact canonical menu options`);
        assert.deepEqual(menuLabels.slice(0, expectedNavLabels.length).map((label) => label.trim()), expectedNavLabels, `${routeInfo.id} ${viewport.width}: menu labels/order`);
        assert.match(menuLabels[expectedNavLabels.length]?.trim() || "", /^(Sign In|Account)$/, `${routeInfo.id} ${viewport.width}: account action follows route navigation`);
        const activeMenuLabels = (await menu.locator('a[data-nav-key][aria-current="page"]').allTextContents()).map((label) => label.trim());
        assert.deepEqual(activeMenuLabels, activeLabelByState[routeInfo.id] ? [activeLabelByState[routeInfo.id]] : [], `${routeInfo.id} ${viewport.width}: menu active state`);
        if (routeInfo.id === "home" && viewport.width === 390) await page.screenshot({ path: path.join(output, "home-mobile-menu.png"), fullPage: true, animations: "disabled" });
        if (routeInfo.id === "reader" && viewport.width === 390) await page.screenshot({ path: path.join(output, "reader-mobile-menu.png"), fullPage: true, animations: "disabled" });
        if (routeInfo.id === "listener" && viewport.width === 390) await page.screenshot({ path: path.join(output, "listener-mobile-menu.png"), fullPage: true, animations: "disabled" });
        await menuToggle.click();
      } else {
        assert.deepEqual(menuLabels, expectedNavLabels, `${routeInfo.id} ${viewport.width}: desktop nav labels/order`);
      }

      const pageWidth = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
      assert.ok(pageWidth.scroll <= pageWidth.client, `${routeInfo.id} ${viewport.width}: page overflow ${pageWidth.scroll}px > ${pageWidth.client}px`);
      assert.deepEqual(pageErrors, [], `${routeInfo.id} ${viewport.width}: uncaught page errors`);
      assert.deepEqual(consoleErrors, [], `${routeInfo.id} ${viewport.width}: browser console errors`);
      assert.deepEqual(badResponses, [], `${routeInfo.id} ${viewport.width}: failed HTTP responses`);
      assert.deepEqual(requestFailures, [], `${routeInfo.id} ${viewport.width}: failed requests`);
      const headerScreenshot = fullPageScreenshotWidths.has(viewport.width) ? `header-${routeInfo.id}-${viewport.width}.png` : null;
      const fullPageScreenshot = fullPageScreenshotWidths.has(viewport.width) ? `${routeInfo.id}-${viewport.width}.png` : null;
      if (headerScreenshot) await header.screenshot({ path: path.join(output, headerScreenshot), animations: "disabled" });
      if (fullPageScreenshot) await page.screenshot({ path: path.join(output, fullPageScreenshot), fullPage: true, animations: "disabled" });
      captures.push({ route: routeInfo.path, state: routeInfo.id, viewport, screenshot: fullPageScreenshot, header_screenshot: headerScreenshot, header: headerInfo, page_width: pageWidth, page_errors: pageErrors, console_errors: consoleErrors, bad_responses: badResponses, request_failures: requestFailures, menu_labels: menuLabels.map((label) => label.trim()) });
      fs.writeFileSync(path.join(output, "progress.json"), JSON.stringify(captures, null, 2));
      await context.close();
    }
  }

const fullPageCaptures = captures.filter((capture) => capture.screenshot);
const html = `<!doctype html><meta charset="utf-8"><title>PR471 canonical header evidence</title><style>body{font:16px system-ui;background:#f7f1e7;color:#251814;margin:24px}h1{font:32px Georgia}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}figure{margin:0;padding:10px;background:#fff;border:1px solid #ddd}img{display:block;width:100%;height:180px;object-fit:cover;object-position:top}figcaption{padding:8px 2px;font-size:13px}</style><h1>PR #471 canonical navigation — exact-head screenshots</h1><p>Local isolated fixtures; no production writes. Every screenshot is mapped to route and viewport in summary.json.</p><main>${fullPageCaptures.map((capture) => `<figure><a href="${capture.screenshot}"><img src="${capture.screenshot}" alt="${capture.state} at ${capture.viewport.width}px"></a><figcaption>${capture.state} · ${capture.viewport.width}px · ${capture.header.height}px masthead · logo ${capture.header.logo_width}px</figcaption></figure>`).join("")}</main>`;
fs.writeFileSync(path.join(output, "index.html"), html);
const headerCaptures = captures.filter((capture) => capture.header_screenshot);
const headerSheet = `<!doctype html><meta charset="utf-8"><title>PR #471 header comparison contact sheet</title><style>body{font:14px system-ui;background:#f7f1e7;color:#251814;margin:20px}h1{font:28px Georgia}h2{font:20px Georgia;margin:28px 0 8px}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}figure{margin:0;padding:8px;background:#fff;border:1px solid #ddd}img{display:block;width:100%;height:auto}figcaption{padding:6px 2px;font-size:12px}</style><h1>PR #471 canonical header comparison</h1><p>Exact-head local fixtures. Header crops are grouped by viewport and mapped in summary.json.</p>${[1440,1024,390].map((width) => `<h2>${width}px</h2><section>${headerCaptures.filter((capture) => capture.viewport.width === width).map((capture) => `<figure><img src="${capture.header_screenshot}" alt="${capture.state} header at ${width}px"><figcaption>${capture.state} · ${capture.header.height}px masthead · lockup ${capture.header.logo_width}px</figcaption></figure>`).join("")}</section>`).join("")}`;
fs.writeFileSync(path.join(output, "header-contact-sheet.html"), headerSheet);
const summary = { result: "PASS", classification: "ISOLATED_LOCAL_FIXTURE_VISUAL_EVIDENCE", head_sha: headSha, route_count: routes.length, viewport_count: viewports.length, full_page_screenshot_count: captures.filter((capture) => capture.screenshot).length, header_screenshot_count: headerCaptures.length, canonical_navigation: navLabels, captures };
  fs.writeFileSync(path.join(output, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`);
  console.log(JSON.stringify({ result: summary.result, output, screenshot_count: summary.screenshot_count, routes: routes.length, viewports: viewports.map(({ width }) => width) }));
} finally {
  await browser.close();
}
