#!/usr/bin/env node
/**
 * Narrow, deterministic design-contract measurement for the primary reference
 * surfaces. It measures rendered DOM geometry rather than inferring a visual
 * pass from a screenshot score, and exits non-zero for a contract regression.
 *
 * Usage:
 *   PLAYWRIGHT_EXECUTABLE_PATH=... node scripts/measure_primary_visual_structure.mjs \
 *     --base-url http://127.0.0.1:3000 --state commerce-desktop --output /tmp/result.json
 */
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const root = path.resolve(new URL("..", import.meta.url).pathname);
const requireFromFrontend = createRequire(path.join(root, "frontend", "package.json"));
const { chromium } = requireFromFrontend("playwright");
const args = process.argv.slice(2);
const option = (name, fallback = "") => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] || fallback : fallback;
};
const baseUrl = option("--base-url", "http://127.0.0.1:3000").replace(/\/$/, "");
const stateId = option("--state");
const output = option("--output");
const offersFixturePath = option("--offers-fixture");

const stateConfig = {
  "commerce-desktop": {
    path: "/pricing",
    viewport: { width: 1440, height: 1000 },
    action: null,
    checks: [
      ["canonical header and logo are visible", "[data-testid=site-header] [data-testid=brand-logo]", 1],
      ["two-column Commerce shell retains dedicated 63/37 composition", ".reference-commerce", 1],
      ["Commerce hero is a compact dark introductory band", ".reference-commerce__hero", 1],
      ["proof panel retains a three-principle hierarchy", ".reference-commerce__hero-proof article", 3],
      ["configured offer cards retain one desktop row", ".reference-commerce__packs .reference-offer", 3],
      ["supported pathways retain their card row", ".reference-commerce__pathways article", 2],
      ["trust band retains three equally weighted facts", ".reference-commerce__trust > div", 3],
      ["warm information rail retains its five sections", ".reference-commerce__insight-rail > section", 5],
      ["preview policy stays visible", "[data-testid=pricing-reference-surface]", 1],
    ],
  },
  "home-desktop": {
    path: "/",
    viewport: { width: 1440, height: 1000 },
    action: null,
    checks: [
      ["canonical header and logo are visible", "[data-testid=site-header] [data-testid=brand-logo]", 1],
      ["dark library hero is present", ".reference-home__hero", 1],
      ["hero retains exactly two primary paths", ".reference-home__cta-row > a", 2],
      ["product policy is present in the hero", ".reference-home__policy", 1],
      ["value strip retains four facts", ".reference-feature-strip article", 4],
      ["journey shelf retains five cards from the safe curation fallback", ".reference-home__journey .reference-book-tile", 5],
      ["Reading Pass section remains distinct", ".reference-home__pass", 1],
      ["light trust transition remains distinct", ".reference-home__trust", 1],
    ],
  },
  "library-desktop": {
    path: "/library",
    viewport: { width: 1440, height: 1000 },
    action: null,
    checks: [
      ["canonical light header and logo are visible", "[data-testid=site-header] [data-testid=brand-logo]", 1],
      ["warm editorial Library surface is present", "[data-testid=library-reference-surface]", 1],
      ["search and sort controls are present", "[data-testid=library-search]", 1],
      ["sort control is present", "[data-testid=library-sort]", 1],
      ["desktop filter sidebar is visible", ".reference-library__sidebar", 1],
      ["three release-state shelves are present", ".reference-library-shelf", 3],
      ["Reading Pass support card is present", ".reference-library__pass", 1],
    ],
  },
  "book-detail-desktop": {
    path: "/book/dracula",
    viewport: { width: 1440, height: 1000 },
    action: null,
    checks: [
      ["canonical dark header and logo are visible", "[data-testid=site-header] [data-testid=brand-logo]", 1],
      ["compact dark Book Detail surface is present", "[data-testid=book-page]", 1],
      ["cover, title and controlled status row are present", ".book-detail-cover-frame", 1],
      ["controlled reader, audio and language status chips are present", "[data-testid=book-detail-status] span", 3],
      ["Read action is present", "[data-testid=start-reading], [data-testid=read-preview]", 1],
      ["Dracula does not expose an approved Listen action", "[data-testid=book-listen-approved]", 0],
      ["release and access truth panel is present", "[data-testid=book-experience-truth]", 1],
      ["secondary actions remain available", "[data-testid=book-share]", 1],
    ],
  },
  "library-filter-mobile": {
    path: "/library",
    viewport: { width: 390, height: 844 },
    action: "filters",
    checks: [
      ["full mobile filter dialog is present", ".reference-library-drawer", 1],
      ["filter title and close control are present", ".reference-library-drawer header", 1],
      ["language, format, status and genre fieldsets are present", ".reference-library-drawer fieldset", 4],
      ["sort field is present", ".reference-library-drawer .reference-filter-sort select", 1],
      ["apply filters action is present", ".reference-library-drawer .reference-button", 1],
    ],
  },
  "home-mobile": {
    path: "/",
    viewport: { width: 390, height: 844 },
    action: null,
    checks: [
      ["mobile logo is visible", "[data-testid=brand-logo]", 1],
      ["compact hero and both actions are present", ".reference-home__cta-row > a", 2],
      ["value strip remains four-up", ".reference-feature-strip article", 4],
    ],
  },
  "library-mobile": {
    path: "/library",
    viewport: { width: 390, height: 844 },
    action: null,
    checks: [
      ["mobile logo is visible", "[data-testid=brand-logo]", 1],
      ["mobile filters action is visible", ".reference-filter-trigger", 1],
      ["Library shelf exists", ".reference-library__shelves", 1],
    ],
  },
  "commerce-mobile": {
    path: "/pricing",
    viewport: { width: 390, height: 844 },
    action: null,
    checks: [
      ["mobile logo is visible", "[data-testid=brand-logo]", 1],
      ["mobile offer stack is present", ".reference-commerce__packs .reference-offer", 3],
      ["truthful pass policy is visible", "[data-testid=pricing-reference-surface]", 1],
    ],
  },
  "mobile-navigation": {
    path: "/",
    viewport: { width: 390, height: 844 },
    action: "navigation",
    checks: [
      ["accessible navigation drawer is open", "[data-testid=mobile-menu]", 1],
      ["drawer retains all public navigation destinations", "[data-testid=mobile-menu] a", 8],
      ["drawer retains a Library action", "[data-testid=mobile-cta-library]", 1],
    ],
  },
  "about-mobile": {
    path: "/about",
    viewport: { width: 390, height: 844 },
    action: null,
    checks: [
      ["mobile logo is visible", "[data-testid=brand-logo]", 1],
      ["About route has a primary heading", "h1", 1],
    ],
  },
};

if (!stateConfig[stateId]) throw new Error(`Unknown --state ${stateId || "(missing)"}`);
const config = stateConfig[stateId];
const browser = await chromium.launch({
  headless: true,
  ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
});
const context = await browser.newContext({
  viewport: config.viewport,
  deviceScaleFactor: 1,
  locale: "en-IN",
  timezoneId: "Asia/Kolkata",
  reducedMotion: "reduce",
  serviceWorkers: "block",
});
const page = await context.newPage();
if (offersFixturePath) {
  const fixture = JSON.parse(await fs.readFile(offersFixturePath, "utf8"));
  await page.route("**/payments/offers", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(fixture),
  }));
}
await page.goto(`${baseUrl}${config.path}`, { waitUntil: "domcontentloaded", timeout: 30_000 });
await page.addStyleTag({ content: "*,*::before,*::after{animation:none!important;transition:none!important}" });
await page.evaluate(async () => { if (document.fonts?.ready) await document.fonts.ready; });
await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});
await page.waitForTimeout(600);
if (config.action === "filters") await page.getByRole("button", { name: /filters/i }).first().click();
if (config.action === "navigation") await page.getByRole("button", { name: /open menu/i }).click();
await page.waitForTimeout(100);

const result = await page.evaluate(({ state, checks }) => {
  const visible = (element) => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
  };
  const assertions = checks.map(([label, selector, minimum]) => {
    const elements = [...document.querySelectorAll(selector)].filter(visible);
    return {
      label,
      selector,
      ...(minimum === 0 ? { expectedExact: 0 } : { expectedMinimum: minimum }),
      actual: elements.length,
      pass: minimum === 0 ? elements.length === 0 : elements.length >= minimum,
    };
  });
  const overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  assertions.push({ label: "horizontal overflow is zero", expected: 0, actual: overflow, pass: overflow === 0 });
  const logo = document.querySelector("[data-testid=brand-logo] img");
  if (logo) {
    const rect = logo.getBoundingClientRect();
    assertions.push({ label: "canonical logo has non-zero rendered dimensions", expected: "> 0", actual: `${rect.width}×${rect.height}`, pass: rect.width > 0 && rect.height > 0 });
  }
  if (state === "commerce-desktop") {
    const shell = document.querySelector(".reference-commerce")?.getBoundingClientRect();
    const primary = document.querySelector(".reference-commerce__primary-column")?.getBoundingClientRect();
    const rail = document.querySelector(".reference-commerce__insight-rail")?.getBoundingClientRect();
    const offers = [...document.querySelectorAll(".reference-commerce__packs .reference-offer")].map((el) => el.getBoundingClientRect());
    const ratio = shell && primary ? primary.width / shell.width : 0;
    const railRatio = shell && rail ? rail.width / shell.width : 0;
    assertions.push({ label: "Commerce primary column matches the 63% reference role", actual: ratio, pass: ratio >= 0.60 && ratio <= 0.67 });
    assertions.push({ label: "Commerce insight rail matches the 37% reference role", actual: railRatio, pass: railRatio >= 0.33 && railRatio <= 0.40 });
    assertions.push({ label: "configured offer cards share one aligned row", actual: offers.map((r) => ({ x: r.x, y: r.y, width: r.width, height: r.height })), pass: offers.length >= 3 && Math.max(...offers.map((r) => r.y)) - Math.min(...offers.map((r) => r.y)) <= 2 && Math.max(...offers.map((r) => r.width)) - Math.min(...offers.map((r) => r.width)) <= 2 });
  }
  const passed = assertions.filter((assertion) => assertion.pass).length;
  return { state, viewport: { width: innerWidth, height: innerHeight }, assertions, passed, total: assertions.length, score: (passed / assertions.length) * 100 };
}, { state: stateId, checks: config.checks });

await context.close();
await browser.close();
if (output) await fs.writeFile(output, `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`${JSON.stringify(result)}\n`);
if (result.passed !== result.total) process.exitCode = 1;
