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

const routes = [
  "/",
  "/library",
  "/book/dracula",
  "/reader/dracula",
  "/book/a-ghost-story",
  "/reader/a-ghost-story",
  "/book/book-ac5a71075e",
  "/reader/book-ac5a71075e",
];

const viewports = [
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
  const screenshotDir = process.env.VISUAL_SMOKE_SCREENSHOT_DIR || path.join(os.tmpdir(), "earnalism-visual-smoke-screenshots");
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
      const response = await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
      status = response?.status() || 0;
    } catch (error) {
      consoleErrors.push(error.message);
    }
    await page.waitForSelector(
      "[data-testid='home-page'], [data-testid='library-page'], [data-testid='book-page'], [data-testid='reader-page'], [data-testid='book-not-found'], [data-testid='reader-not-found']",
      { timeout: 12000 },
    ).catch(() => {});
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
      return {
        appContentVisible: Boolean(document.querySelector("[data-testid='home-page'], [data-testid='library-page'], [data-testid='book-page'], [data-testid='reader-page'], [data-testid='book-not-found'], [data-testid='reader-not-found']")),
        vercelLoginShellDetected: /vercel deployment protection|log in to continue|continue with github|saml sso|vercel\\.com\\/sso-api/i.test(bodyText),
        horizontalOverflow: body.scrollWidth > window.innerWidth + 1,
        heroHeadingVisible: heading ? Boolean(heading.offsetWidth && heading.offsetHeight) : true,
        heroCtaVisible: cta ? Boolean(cta.offsetWidth && cta.offsetHeight) : true,
        coverClipped: rect ? rect.right > window.innerWidth + 1 || rect.left < -1 : false,
        textOnlyCoverFallbackVisible: textOnlyFallback,
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
  if (!result.appContentVisible) issues.push("app content not visible");
  if (result.vercelLoginShellDetected) issues.push("Vercel login shell");
  if (result.horizontalOverflow) issues.push("horizontal overflow");
  if (!result.heroHeadingVisible) issues.push("hero heading invisible");
  if (!result.heroCtaVisible) issues.push("CTA invisible");
  if (result.coverClipped) issues.push("cover clipped");
  if (result.textOnlyCoverFallbackVisible) issues.push("text-only cover fallback visible");
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
  mode: "browser_and_source",
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
