#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const baseUrl = process.env.VISUAL_SMOKE_BASE_URL || "";
const reportPath = path.join(repoRoot, "ux_visual_regression_report.json");
const frontendPackageJson = path.join(repoRoot, "frontend", "package.json");
const runnerPath = path.join(repoRoot, "frontend", "scripts", ".visual-luxury-smoke-runner.mjs");
const screenshotDir = process.env.VISUAL_SMOKE_SCREENSHOT_DIR || path.join("/tmp", "earnalism-visual-smoke-screenshots");
const runnerTimeoutMs = Number(process.env.VISUAL_SMOKE_RUNNER_TIMEOUT_MS || 180000);
const fullRoutes = ["/", "/library", "/book/dracula", "/reader/dracula", "/book/a-ghost-story", "/reader/a-ghost-story", "/book/book-ac5a71075e", "/reader/book-ac5a71075e"];
const defaultRoutes = ["/", "/library", "/book/dracula", "/reader/dracula", "/book/a-ghost-story", "/reader/a-ghost-story"];
const fullViewports = [
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
const defaultViewports = [
  { width: 1536, height: 864 },
  { width: 1366, height: 768 },
  { width: 820, height: 1180 },
  { width: 390, height: 844 },
];
const routes = process.env.VISUAL_SMOKE_ROUTES
  ? process.env.VISUAL_SMOKE_ROUTES.split(",").map((route) => route.trim()).filter(Boolean)
  : process.env.VISUAL_SMOKE_FULL_MATRIX === "true"
    ? fullRoutes
    : defaultRoutes;
const viewports = process.env.VISUAL_SMOKE_FULL_MATRIX === "true" ? fullViewports : defaultViewports;
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

function buildRunnerSource() {
  return `
import { createRequire } from "node:module";
import fs from "node:fs";

const require = createRequire(${JSON.stringify(frontendPackageJson)});
const baseUrl = ${JSON.stringify(baseUrl)};
const screenshotDir = ${JSON.stringify(screenshotDir)};
const routes = ${JSON.stringify(routes)};
const viewports = ${JSON.stringify(viewports)};
const attempted = [];
const completed = [];
const failedSubchecks = [];
let playwrightImportStatus = "not_run";
let browserLaunchStatus = "not_run";
let chromium;
let browser;

try {
  ({ chromium } = require("playwright"));
  playwrightImportStatus = "passed";
} catch (error) {
  playwrightImportStatus = "failed";
  failedSubchecks.push({ scope: "playwright_import", issue: error.message });
  console.log(JSON.stringify({
    skipped: false,
    playwright_import_status: playwrightImportStatus,
    browser_launch_status: browserLaunchStatus,
    routes_attempted: attempted,
    routes_completed: completed,
    failed_subchecks: failedSubchecks,
    final_status: "BLOCKED",
    blockers: failedSubchecks,
  }, null, 2));
  process.exit(1);
}

try {
  try {
    browser = await chromium.launch({ channel: "chrome", headless: true });
  } catch {
    browser = await chromium.launch({ headless: true });
  }
  browserLaunchStatus = "passed";
} catch (error) {
  browserLaunchStatus = "failed";
  failedSubchecks.push({ scope: "browser_launch", issue: error.message });
  console.log(JSON.stringify({
    skipped: false,
    playwright_import_status: playwrightImportStatus,
    browser_launch_status: browserLaunchStatus,
    routes_attempted: attempted,
    routes_completed: completed,
    failed_subchecks: failedSubchecks,
    final_status: "BLOCKED",
    blockers: failedSubchecks,
  }, null, 2));
  process.exit(1);
}

fs.mkdirSync(screenshotDir, { recursive: true });
const results = [];
try {
  for (const route of routes) {
    for (const viewport of viewports) {
      attempted.push({ route, viewport });
      const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
      page.setDefaultTimeout(5000);
      page.setDefaultNavigationTimeout(15000);
      const consoleErrors = [];
      page.on("console", (msg) => {
        if (msg.type() === "error") consoleErrors.push(msg.text());
      });
      const url = new URL(route, baseUrl).toString();
      let status = 0;
      try {
        const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
        await page.waitForLoadState("networkidle", { timeout: 2500 }).catch(() => undefined);
        await page.waitForTimeout(150);
        status = response?.status() || 0;
      } catch (error) {
        consoleErrors.push(error.message);
      }
      const metrics = await page.evaluate(() => {
        const body = document.body;
        const hero = document.querySelector("[data-testid='premium-landing-hero'], [data-testid='library-hero']");
        const heading = document.querySelector("[data-testid='hero-headline'], [data-testid='library-hero'] h1, h1");
        const cover = document.querySelector("[data-testid='hero-dracula-cover-frame'], .book-cover-image, .reference-hero-book");
        const cta = document.querySelector("[data-testid='hero-cta-read'], [data-testid='library-hero-read'], .btn-primary");
        const headingStyle = heading ? getComputedStyle(heading) : null;
        const heroStyle = hero ? getComputedStyle(hero) : null;
        const rect = cover ? cover.getBoundingClientRect() : null;
        return {
          appContentVisible: Boolean(document.querySelector("[data-testid='home-page'], [data-testid='library-page'], [data-testid='book-page'], [data-testid='reader-page']")),
          vercelLoginShellDetected: /vercel deployment protection|log in to continue/i.test(body.innerText || ""),
          horizontalOverflow: body.scrollWidth > window.innerWidth + 1,
          heroHeadingVisible: heading ? Boolean(heading.offsetWidth && heading.offsetHeight) : null,
          heroCtaVisible: cta ? Boolean(cta.offsetWidth && cta.offsetHeight) : true,
          coverClipped: rect ? rect.right > window.innerWidth + 1 || rect.left < -1 : false,
          textColor: headingStyle?.color || "",
          heroBackground: heroStyle?.backgroundColor || "",
        };
      });
      const screenshotPath = screenshotDir + "/" + route.replace(/[^a-z0-9]+/gi, "_").replace(/^_$/, "home") + "_" + viewport.width + "x" + viewport.height + ".png";
      await page.screenshot({ path: screenshotPath, fullPage: false });
      await page.close();
      const result = { route, viewport, status, screenshotPath, consoleErrors, ...metrics };
      results.push(result);
      completed.push({ route, viewport });
    }
  }
} finally {
  await browser.close();
}

for (const result of results) {
  const issues = [];
  if (!result.appContentVisible) issues.push("app content not visible");
  if (result.vercelLoginShellDetected) issues.push("Vercel login shell");
  if (result.horizontalOverflow) issues.push("horizontal overflow");
  if ((result.route === "/" || result.route === "/library") && !result.heroHeadingVisible) issues.push("hero heading invisible");
  if (!result.heroCtaVisible) issues.push("CTA invisible");
  if (result.coverClipped) issues.push("cover clipped");
  if (result.consoleErrors.length) issues.push("console errors");
  for (const issue of issues) {
    failedSubchecks.push({ route: result.route, viewport: result.viewport, issue });
  }
}

const finalStatus = failedSubchecks.length ? "FAIL" : "PASS";
console.log(JSON.stringify({
  skipped: false,
  screenshotDir,
  results,
  playwright_import_status: playwrightImportStatus,
  browser_launch_status: browserLaunchStatus,
  routes_attempted: attempted,
  routes_completed: completed,
  failed_subchecks: failedSubchecks,
  final_status: finalStatus,
  blockers: failedSubchecks,
}, null, 2));
process.exit(failedSubchecks.length ? 1 : 0);
`;
}

function runBrowserChecks() {
  if (!baseUrl) {
    return {
      skipped: true,
      reason: "VISUAL_SMOKE_BASE_URL not set",
      playwright_import_status: "not_run",
      browser_launch_status: "not_run",
      routes_attempted: [],
      routes_completed: [],
      failed_subchecks: [{ scope: "configuration", issue: "VISUAL_SMOKE_BASE_URL not set" }],
      final_status: "BLOCKED",
      blockers: [{ scope: "configuration", issue: "VISUAL_SMOKE_BASE_URL not set" }],
    };
  }
  fs.writeFileSync(runnerPath, buildRunnerSource(), "utf8");
  const result = spawnSync(process.execPath, [runnerPath], {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    timeout: runnerTimeoutMs,
    killSignal: "SIGTERM",
    maxBuffer: 50 * 1024 * 1024,
  });
  try {
    fs.unlinkSync(runnerPath);
  } catch {
    // Best-effort cleanup only.
  }
  let parsed = null;
  try {
    parsed = JSON.parse(result.stdout);
  } catch {
    parsed = {
      skipped: false,
      failedToParse: true,
      stdout: result.stdout.slice(-2000),
      stderr: result.stderr.slice(-2000),
      status: result.status,
      playwright_import_status: "unknown",
      browser_launch_status: "unknown",
      routes_attempted: [],
      routes_completed: [],
      failed_subchecks: [{ scope: "browser_runner", issue: "Browser runner output was not parseable JSON" }],
      final_status: "BLOCKED",
      blockers: [{ scope: "browser_runner", issue: "Browser runner output was not parseable JSON" }],
    };
  }
  if (result.status !== 0 && (!parsed.blockers || parsed.blockers.length === 0)) {
    const issue = result.error?.code === "ETIMEDOUT"
      ? `Browser runner timed out after ${runnerTimeoutMs}ms`
      : `Browser runner exited ${result.status}`;
    parsed.blockers = [{ scope: "browser_runner", issue }];
    parsed.failed_subchecks = parsed.blockers;
    parsed.final_status = "BLOCKED";
  }
  return parsed;
}

const source = runSourceChecks();
const browser = runBrowserChecks();
const sourceBlockers = source.flatMap((check) => check.blockers.map((blocker) => ({ check: check.name, blocker })));
const browserBlockers = browser?.blockers || [];
const allBlockers = [...sourceBlockers, ...browserBlockers];
const report = {
  generated_at: new Date().toISOString(),
  mode: baseUrl ? "browser_and_source" : "blocked_no_browser_target",
  routes,
  viewports: viewports.map((viewport) => `${viewport.width}x${viewport.height}`),
  source_checks: source,
  browser_checks: browser,
  playwright_import_status: browser?.playwright_import_status || "unknown",
  browser_launch_status: browser?.browser_launch_status || "unknown",
  routes_attempted: browser?.routes_attempted || [],
  routes_completed: browser?.routes_completed || [],
  failed_subchecks: browser?.failed_subchecks || [],
  critical_blockers: allBlockers,
  visual_smoke_status: allBlockers.length === 0 ? "PASS" : "FAIL",
};
fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({
  visual_smoke_status: report.visual_smoke_status,
  mode: report.mode,
  playwright_import_status: report.playwright_import_status,
  browser_launch_status: report.browser_launch_status,
  routes_attempted: report.routes_attempted.length,
  routes_completed: report.routes_completed.length,
  failed_subchecks: report.failed_subchecks.length,
  critical_blockers: report.critical_blockers.length,
  report_path: reportPath,
}, null, 2));
if (report.critical_blockers.length) process.exit(1);
