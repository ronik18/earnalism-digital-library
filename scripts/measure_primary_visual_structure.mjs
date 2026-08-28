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
      ["standalone mobile canonical logo is visible", ".experience-header .earnalism-brand-lockup", 1],
      ["About route has a primary heading", "h1", 1],
    ],
  },
};

// These are region-level, numeric design-contract checks.  They intentionally
// supplement the older presence checks above: each one evaluates a concrete
// box, type, grid, border, or colour role that is visible in the canonical
// reference region.  Bounds are expressed in CSS pixels for the pinned
// 1×/en-IN/Asia-Kolkata capture environment and reject a structural move,
// rather than merely confirming that an element happens to exist.
const metric = (label, selector, property, minimum, maximum, index = 0) => ({ label, selector, property, minimum, maximum, index });
const gridColumns = (label, selector, expected, index = 0) => ({ label, selector, property: "gridColumns", expected, index });
const exact = (label, selector, property, expected, index = 0) => ({ label, selector, property, expected, index });
const geometryByState = {
  "home-desktop": [
    metric("header x", "[data-testid=site-header]", "x", 0, 0), metric("header y", "[data-testid=site-header]", "y", 0, 0), metric("header width", "[data-testid=site-header]", "width", 1438, 1440), metric("header height", "[data-testid=site-header]", "height", 80, 88),
    metric("logo x", "[data-testid=brand-logo] img", "x", 47, 53), metric("logo y", "[data-testid=brand-logo] img", "y", 8, 12), metric("logo width", "[data-testid=brand-logo] img", "width", 205, 216), metric("logo height", "[data-testid=brand-logo] img", "height", 59, 68),
    metric("hero x", ".reference-home__hero", "x", 0, 0), metric("hero y", ".reference-home__hero", "y", 80, 88), metric("hero width", ".reference-home__hero", "width", 1438, 1440), metric("hero height", ".reference-home__hero", "height", 590, 610),
    metric("hero-copy x", ".reference-home__hero-copy", "x", 76, 88), metric("hero-copy y", ".reference-home__hero-copy", "y", 165, 178), metric("hero-copy width", ".reference-home__hero-copy", "width", 590, 620), metric("hero-copy height", ".reference-home__hero-copy", "height", 415, 435),
    metric("heading font size", ".reference-home__hero h1", "fontSize", 72, 78), metric("heading line height", ".reference-home__hero h1", "lineHeight", 60, 66),
    metric("CTA row x", ".reference-home__cta-row", "x", 76, 88), metric("CTA row y", ".reference-home__cta-row", "y", 478, 492), metric("CTA row height", ".reference-home__cta-row", "height", 42, 46),
    metric("policy x", ".reference-home__policy", "x", 76, 88), metric("policy y", ".reference-home__policy", "y", 542, 555), metric("policy height", ".reference-home__policy", "height", 44, 51),
    metric("value strip x", ".reference-feature-strip", "x", 46, 54), metric("value strip y", ".reference-feature-strip", "y", 650, 662), metric("value strip width", ".reference-feature-strip", "width", 1334, 1344), metric("value strip height", ".reference-feature-strip", "height", 82, 92), gridColumns("value strip columns", ".reference-feature-strip", 4),
    metric("journey width", ".reference-home__journey", "width", 1334, 1344), metric("journey top", ".reference-home__journey", "y", 736, 750), gridColumns("journey shelf columns", ".reference-book-shelf", 5), metric("journey card width", ".reference-home__journey .reference-book-tile", "width", 250, 264), metric("journey card height", ".reference-home__journey .reference-book-tile", "height", 460, 478),
    metric("pass width", ".reference-home__pass", "width", 1334, 1344), metric("pass top", ".reference-home__pass", "y", 1418, 1434), metric("trust transition top", ".reference-home__trust", "y", 2130, 2155), exact("trust surface", ".reference-home__trust", "backgroundColor", "rgb(248, 241, 228)"),
  ],
  "library-desktop": [
    metric("header x", "[data-testid=site-header]", "x", 0, 0), metric("header y", "[data-testid=site-header]", "y", 0, 0), metric("header width", "[data-testid=site-header]", "width", 1438, 1440), metric("header height", "[data-testid=site-header]", "height", 80, 88),
    metric("logo x", "[data-testid=brand-logo] img", "x", 47, 53), metric("logo y", "[data-testid=brand-logo] img", "y", 8, 12), metric("logo width", "[data-testid=brand-logo] img", "width", 205, 216), metric("logo height", "[data-testid=brand-logo] img", "height", 59, 68),
    metric("library outer left", ".reference-library", "paddingLeft", 46, 54), metric("library outer right", ".reference-library", "paddingRight", 46, 54), exact("library surface", ".reference-library", "backgroundColor", "rgb(251, 247, 239)"),
    metric("titlebar y", ".reference-library__titlebar", "y", 134, 144), metric("titlebar width", ".reference-library__titlebar", "width", 1334, 1344), metric("title font size", ".reference-library__titlebar h1", "fontSize", 58, 63),
    metric("controls y", ".reference-library__controls", "y", 180, 190), metric("search width", ".reference-search", "width", 320, 340), metric("search height", ".reference-search", "height", 40, 45),
    metric("content x", ".reference-library__content", "x", 46, 54), metric("content y", ".reference-library__content", "y", 258, 274), metric("content width", ".reference-library__content", "width", 1334, 1344), gridColumns("content columns", ".reference-library__content", 2),
    metric("sidebar x", ".reference-library__sidebar", "x", 46, 54), metric("sidebar width", ".reference-library__sidebar", "width", 196, 204), metric("sidebar top", ".reference-library__sidebar", "y", 285, 299), metric("sidebar radius", ".reference-library__sidebar", "borderRadius", 6, 8),
    metric("shelves x", ".reference-library__shelves", "x", 270, 281), metric("shelves width", ".reference-library__shelves", "width", 1108, 1121), metric("shelf gap", ".reference-library__shelves", "gap", 34, 38),
    metric("first shelf top", ".reference-library-shelf", "y", 285, 299), metric("first shelf height", ".reference-library-shelf", "height", 480, 500), metric("shelf heading font", ".reference-library-shelf h2", "fontSize", 28, 33),
    gridColumns("book grid columns", ".reference-library-grid", 5), metric("book grid gap", ".reference-library-grid", "gap", 10, 14), metric("book card width", ".reference-library-grid .reference-book-tile", "width", 207, 219), metric("book card height", ".reference-library-grid .reference-book-tile", "height", 387, 403), metric("book card radius", ".reference-library-grid .reference-book-tile", "borderRadius", 6, 8),
    metric("pass card x", ".reference-library__pass", "x", 64, 70), metric("pass card width", ".reference-library__pass", "width", 162, 170), metric("pass card top", ".reference-library__pass", "y", 950, 968), exact("pass card surface", ".reference-library__pass", "backgroundColor", "rgb(227, 185, 103)"),
  ],
  "commerce-desktop": [
    metric("header height", "[data-testid=site-header]", "height", 80, 88), metric("logo width", "[data-testid=brand-logo] img", "width", 205, 216), metric("logo height", "[data-testid=brand-logo] img", "height", 59, 68),
    metric("commerce x", ".reference-commerce", "x", 0, 0), metric("commerce top", ".reference-commerce", "y", 80, 88), metric("commerce width", ".reference-commerce", "width", 1438, 1440), gridColumns("commerce shell columns", ".reference-commerce", 2),
    metric("primary column width", ".reference-commerce__primary-column", "width", 905, 924), metric("insight rail width", ".reference-commerce__insight-rail", "width", 516, 534), metric("hero width", ".reference-commerce__hero", "width", 905, 924), metric("hero height", ".reference-commerce__hero", "height", 265, 283), exact("hero surface", ".reference-commerce__hero", "backgroundColor", "rgb(7, 17, 15)"),
    metric("hero copy x", ".reference-commerce__hero > div", "x", 56, 65), metric("hero copy y", ".reference-commerce__hero > div", "y", 112, 126), metric("hero copy width", ".reference-commerce__hero > div", "width", 370, 392), metric("hero heading size", ".reference-commerce__hero h1", "fontSize", 47, 50),
    metric("proof x", ".reference-commerce__hero-proof", "x", 570, 585), metric("proof y", ".reference-commerce__hero-proof", "y", 96, 105), metric("proof width", ".reference-commerce__hero-proof", "width", 314, 326), metric("proof height", ".reference-commerce__hero-proof", "height", 128, 138), gridColumns("proof principles", ".reference-commerce__hero-proof > div", 3),
    metric("main width", ".reference-commerce__main", "width", 835, 852), metric("main x", ".reference-commerce__main", "x", 32, 40), metric("main top", ".reference-commerce__main", "y", 351, 365),
    gridColumns("offer columns", ".reference-commerce__packs", 4), metric("offer gap", ".reference-commerce__packs", "gap", 8, 12), metric("offer card width", ".reference-offer", "width", 202, 204), metric("offer card min height", ".reference-offer", "height", 255, 300), metric("offer card radius", ".reference-offer", "borderRadius", 5, 8), metric("offer title size", ".reference-offer__minutes", "fontSize", 13, 16), metric("offer price size", ".reference-offer > strong", "fontSize", 24, 29),
    gridColumns("pathway columns", ".reference-commerce__pathways", 3), metric("pathway top", ".reference-commerce__pathways", "y", 678, 692), metric("pathway card radius", ".reference-commerce__pathways article", "borderRadius", 6, 8),
    gridColumns("trust columns", ".reference-commerce__trust", 3), metric("trust top", ".reference-commerce__trust", "y", 842, 854), metric("trust radius", ".reference-commerce__trust", "borderRadius", 6, 8), exact("trust surface", ".reference-commerce__trust", "backgroundColor", "rgb(10, 28, 24)"),
    metric("rail x", ".reference-commerce__insight-rail", "x", 905, 924), metric("rail top", ".reference-commerce__insight-rail", "y", 80, 88), metric("rail padding left", ".reference-commerce__insight-rail", "paddingLeft", 16, 24), metric("rail padding top", ".reference-commerce__insight-rail", "paddingTop", 18, 25), metric("rail heading size", ".reference-commerce__insight-rail h2", "fontSize", 22, 31),
  ],
  "book-detail-desktop": [
    metric("header height", "[data-testid=site-header]", "height", 80, 88), metric("logo width", "[data-testid=brand-logo] img", "width", 205, 216), metric("logo height", "[data-testid=brand-logo] img", "height", 59, 68),
    metric("return top", ".book-detail-reference__return", "y", 80, 88), metric("return height", ".book-detail-reference__return", "height", 80, 88),
    metric("hero x", ".book-detail-reference__hero", "x", 76, 84), metric("hero top", ".book-detail-reference__hero", "y", 160, 176), metric("hero width", ".book-detail-reference__hero", "width", 1274, 1286), metric("hero padding top", ".book-detail-reference__hero", "paddingTop", 76, 84), gridColumns("hero columns", ".book-detail-reference__hero", 12), metric("hero gap", ".book-detail-reference__hero", "gap", 60, 68),
    metric("cover x", ".book-detail-cover-frame", "x", 124, 132), metric("cover y", ".book-detail-cover-frame", "y", 242, 254), metric("cover width", ".book-detail-cover-frame", "width", 450, 462), metric("cover height", ".book-detail-cover-frame", "height", 602, 614), metric("cover radius", ".book-detail-cover-frame", "borderRadius", 12, 16),
    metric("title x", ".book-detail-reference__hero h1", "x", 644, 652), metric("title y", ".book-detail-reference__hero h1", "y", 280, 300), metric("title width", ".book-detail-reference__hero h1", "width", 320, 330), metric("title font", ".book-detail-reference__hero h1", "fontSize", 50, 54), metric("title line height", ".book-detail-reference__hero h1", "lineHeight", 54, 58),
    metric("status x", "[data-testid=book-detail-status]", "x", 644, 652), metric("status top", "[data-testid=book-detail-status]", "y", 438, 450), metric("status height", "[data-testid=book-detail-status]", "height", 28, 36),
    metric("truth x", "[data-testid=book-experience-truth]", "x", 644, 652), metric("truth top", "[data-testid=book-experience-truth]", "y", 972, 990), metric("truth width", "[data-testid=book-experience-truth]", "width", 655, 672), metric("truth radius", "[data-testid=book-experience-truth]", "borderRadius", 20, 28), metric("truth padding", "[data-testid=book-experience-truth]", "paddingTop", 18, 25),
    exact("book surface", "[data-testid=book-page]", "color", "rgb(255, 248, 233)"), exact("cover surface", ".book-detail-cover-frame", "backgroundColor", "rgb(16, 32, 27)"), metric("no horizontal overflow", "[data-testid=book-page]", "width", 1438, 1440),
  ],
  "library-filter-mobile": [
    metric("drawer x", ".reference-library-drawer", "x", 0, 0), metric("drawer y", ".reference-library-drawer", "y", 0, 0), metric("drawer width", ".reference-library-drawer", "width", 390, 390), metric("drawer height", ".reference-library-drawer", "height", 844, 844), exact("drawer display", ".reference-library-drawer", "display", "grid"),
    metric("panel x", ".reference-library-drawer > div", "x", 10, 11), metric("panel y", ".reference-library-drawer > div", "y", 10, 11), metric("panel width", ".reference-library-drawer > div", "width", 369, 370), metric("panel height", ".reference-library-drawer > div", "height", 399, 401), metric("panel radius", ".reference-library-drawer > div", "borderRadius", 14, 15),
    metric("header height", ".reference-library-drawer header", "height", 49, 51), metric("title size", ".reference-library-drawer header strong", "fontSize", 17, 18), metric("reset x", ".reference-filter-reset", "x", 267, 268), metric("close target height", ".reference-library-drawer header button", "height", 43, 45),
    exact("fieldset count", ".reference-library-drawer fieldset", "count", 4), metric("fieldset gap", ".reference-library-drawer fieldset", "gap", 1, 2), metric("sort width", ".reference-filter-sort select", "width", 340, 341), metric("sort height", ".reference-filter-sort select", "height", 30, 31), metric("apply width", ".reference-library-drawer .reference-button", "width", 340, 341), metric("apply height", ".reference-library-drawer .reference-button", "height", 37, 38),
  ],
  "home-mobile": [metric("header width", "[data-testid=site-header]", "width", 390, 390), metric("header height", "[data-testid=site-header]", "height", 56, 72), metric("logo width", "[data-testid=brand-logo] img", "width", 156, 160), metric("logo height", "[data-testid=brand-logo] img", "height", 36, 48), metric("hero top", ".reference-home__hero", "y", 56, 72), metric("hero width", ".reference-home__hero", "width", 390, 390), metric("hero height", ".reference-home__hero", "height", 480, 540), metric("hero padding left", ".reference-home__hero", "paddingLeft", 15, 22), metric("heading size", ".reference-home h1", "fontSize", 45, 56), gridColumns("CTA columns", ".reference-home__cta-row", 2), metric("CTA height", ".reference-home__cta-row", "height", 40, 56), metric("value strip width", ".reference-feature-strip", "width", 390, 390), gridColumns("value strip columns", ".reference-feature-strip", 4), metric("value strip height", ".reference-feature-strip", "height", 76, 98), metric("journey width", ".reference-home__journey", "width", 350, 370), metric("journey card width", ".reference-home__journey .reference-book-tile", "width", 132, 137), metric("pass width", ".reference-home__pass", "width", 350, 370), metric("trust width", ".reference-home__trust", "width", 390, 390), exact("trust surface", ".reference-home__trust", "backgroundColor", "rgb(248, 241, 228)"), metric("body overflow width", "body", "width", 390, 390)],
  "library-mobile": [metric("header width", "[data-testid=site-header]", "width", 390, 390), metric("header height", "[data-testid=site-header]", "height", 56, 72), metric("logo width", "[data-testid=brand-logo] img", "width", 156, 160), metric("library padding left", ".reference-library", "paddingLeft", 14, 20), metric("title top", ".reference-library__titlebar", "y", 76, 80), metric("title size", ".reference-library__titlebar h1", "fontSize", 38, 46), metric("controls width", ".reference-library__controls", "width", 350, 370), metric("search width", ".reference-search", "width", 350, 370), metric("filter height", ".reference-filter-trigger", "height", 36, 46), metric("content width", ".reference-library__content", "width", 350, 370), exact("content columns", ".reference-library__content", "gridColumns", 1), metric("shelves width", ".reference-library__shelves", "width", 350, 370), metric("shelf gap", ".reference-library__shelves", "gap", 30, 40), metric("shelf heading size", ".reference-library-shelf h2", "fontSize", 24, 28), metric("book grid width", ".reference-library-grid", "width", 350, 370), metric("book card width", ".reference-library-grid .reference-book-tile", "width", 132, 137), metric("book card height", ".reference-library-grid .reference-book-tile", "height", 270, 330), metric("card radius", ".reference-library-grid .reference-book-tile", "borderRadius", 6, 9), exact("library surface", ".reference-library", "backgroundColor", "rgb(251, 247, 239)"), metric("body overflow width", "body", "width", 390, 390)],
  "commerce-mobile": [metric("header width", "[data-testid=site-header]", "width", 390, 390), metric("header height", "[data-testid=site-header]", "height", 56, 72), metric("logo width", "[data-testid=brand-logo] img", "width", 150, 164), exact("commerce stack display", ".reference-commerce", "display", "block"), metric("commerce width", ".reference-commerce", "width", 390, 390), metric("hero top", ".reference-commerce__hero", "y", 56, 72), metric("hero width", ".reference-commerce__hero", "width", 390, 390), metric("hero height", ".reference-commerce__hero", "height", 642, 660), metric("hero padding left", ".reference-commerce__hero", "paddingLeft", 16, 20), metric("hero heading size", ".reference-commerce__hero h1", "fontSize", 52, 57), metric("main width", ".reference-commerce__main", "width", 350, 370), exact("offer columns", ".reference-commerce__packs", "gridColumns", 1), metric("offer width", ".reference-offer", "width", 350, 370), metric("offer height", ".reference-offer", "height", 275, 295), metric("offer radius", ".reference-offer", "borderRadius", 7, 9), metric("pathway width", ".reference-commerce__pathways", "width", 350, 370), exact("pathway columns", ".reference-commerce__pathways", "gridColumns", 1), exact("trust columns", ".reference-commerce__trust", "gridColumns", 1), metric("hero proof width", ".reference-commerce__hero-proof", "width", 340, 360), metric("hero proof height", ".reference-commerce__hero-proof", "height", 214, 218), metric("body overflow width", "body", "width", 390, 390)],
  "mobile-navigation": [metric("drawer width", "[data-testid=mobile-menu]", "width", 390, 390), metric("drawer height", "[data-testid=mobile-menu]", "height", 440, 460), metric("drawer x", "[data-testid=mobile-menu]", "x", 0, 0), metric("drawer y", "[data-testid=mobile-menu]", "y", 54, 60), exact("drawer display", "[data-testid=mobile-menu]", "display", "block"), metric("drawer content padding", "[data-testid=mobile-menu] > div", "paddingLeft", 18, 22), metric("drawer title size", "[data-testid=mobile-menu]", "fontSize", 14, 18), exact("navigation link count", "[data-testid=mobile-menu] a", "count", 15), metric("first link x", "[data-testid=mobile-menu] a", "x", 18, 22), metric("first link height", "[data-testid=mobile-menu] a", "height", 23, 30), metric("Library action width", "[data-testid=mobile-cta-library]", "width", 350, 360), metric("Library action height", "[data-testid=mobile-cta-library]", "height", 42, 52), metric("close control height", "[data-testid=mobile-menu-toggle]", "height", 42, 46), metric("drawer top content", "[data-testid=mobile-menu] > div", "y", 55, 61), metric("drawer width guard", "body", "width", 390, 390), metric("drawer right edge", "[data-testid=mobile-menu]", "right", 390, 390), metric("drawer bottom", "[data-testid=mobile-menu]", "bottom", 500, 515), metric("primary CTA y", "[data-testid=mobile-cta-library]", "y", 338, 352), metric("navigation border", "[data-testid=mobile-menu]", "borderTopWidth", 0, 2), metric("social target width", "[data-testid=mobile-socials] a", "width", 38, 44)],
  "about-mobile": [metric("about width", ".experience-v2", "width", 390, 390), metric("header width", ".experience-header", "width", 390, 390), metric("header height", ".experience-header", "height", 54, 76), metric("logo width", ".experience-header .earnalism-brand-lockup", "width", 158, 172), metric("logo height", ".experience-header .earnalism-brand-lockup", "height", 32, 58), metric("content width", ".about-v2__content", "width", 350, 370), metric("content top", ".about-v2__content", "y", 66, 70), metric("heading size", ".about-v2 h1", "fontSize", 36, 40), metric("heading line height", ".about-v2 h1", "lineHeight", 36, 40), metric("intro width", ".about-v2__intro", "width", 300, 360), metric("card list width", ".about-v2__cards", "width", 350, 370), metric("card radius", ".about-v2__cards article", "borderRadius", 8, 10), metric("card gap", ".about-v2__cards", "gap", 9, 13), metric("bottom nav width", ".experience-bottom-nav", "width", 390, 390), metric("bottom nav height", ".experience-bottom-nav", "height", 64, 72), exact("bottom nav columns", ".experience-bottom-nav", "gridColumns", 4), metric("surface font", ".experience-v2", "fontSize", 14, 18), metric("body overflow width", "body", "width", 390, 390), metric("header left", ".experience-header", "x", 0, 0), metric("header top", ".experience-header", "y", 0, 0)],
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

const result = await page.evaluate(({ state, checks, geometry }) => {
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
  const metricValue = (element, property) => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    if (property === "count") return document.querySelectorAll(element.dataset.measureSelector || "").length;
    if (property === "gridColumns") return style.gridTemplateColumns.split(" ").filter((value) => value && value !== "none").length;
    if (["x", "y", "width", "height", "top", "right", "bottom", "left"].includes(property)) return rect[property];
    const raw = style[property];
    const numeric = Number.parseFloat(raw);
    return Number.isFinite(numeric) && /^-?\d/.test(raw) ? numeric : raw;
  };
  for (const item of geometry) {
    const elements = [...document.querySelectorAll(item.selector)].filter(visible);
    if (item.property === "count") {
      assertions.push({ label: item.label, selector: item.selector, expectedExact: item.expected, actual: elements.length, pass: elements.length === item.expected });
      continue;
    }
    const element = elements[item.index || 0];
    if (!element) {
      assertions.push({ label: item.label, selector: item.selector, expected: item.expected ?? `${item.minimum}..${item.maximum}`, actual: "missing", pass: false });
      continue;
    }
    const value = metricValue(element, item.property);
    const pass = Object.hasOwn(item, "expected") ? value === item.expected : value >= item.minimum && value <= item.maximum;
    assertions.push({ label: item.label, selector: item.selector, property: item.property, expected: Object.hasOwn(item, "expected") ? item.expected : `${item.minimum}..${item.maximum}`, actual: value, pass });
  }
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
}, { state: stateId, checks: config.checks, geometry: geometryByState[stateId] || [] });

await context.close();
await browser.close();
if (output) await fs.writeFile(output, `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`${JSON.stringify(result)}\n`);
if (result.passed !== result.total) process.exitCode = 1;
