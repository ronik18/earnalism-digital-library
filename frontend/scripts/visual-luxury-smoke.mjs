#!/usr/bin/env node
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const baseUrl = process.env.VISUAL_SMOKE_BASE_URL || "";
const reportPath = path.join(repoRoot, "ux_visual_regression_report.json");
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

function runBrowserChecks() {
  if (!baseUrl) return { skipped: true, reason: "VISUAL_SMOKE_BASE_URL not set" };
  const runnerPath = path.join(os.tmpdir(), "earnalism-visual-smoke-runner.mjs");
  const screenshotDir = process.env.VISUAL_SMOKE_SCREENSHOT_DIR || path.join(os.tmpdir(), "earnalism-visual-smoke-screenshots");
  fs.mkdirSync(screenshotDir, { recursive: true });
  fs.writeFileSync(runnerPath, `
import { chromium } from "playwright";
import fs from "node:fs";
const baseUrl = ${JSON.stringify(baseUrl)};
const screenshotDir = ${JSON.stringify(screenshotDir)};
const routes = ["/", "/library", "/book/dracula", "/reader/dracula", "/book/a-ghost-story", "/reader/a-ghost-story", "/book/book-ac5a71075e", "/reader/book-ac5a71075e"];
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
let browser;
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
} catch {
  browser = await chromium.launch({ headless: true });
}
const results = [];
for (const route of routes) {
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
    const consoleErrors = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    const url = new URL(route, baseUrl).toString();
    let status = 0;
    try {
      const response = await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
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
        heroHeadingVisible: heading ? Boolean(heading.offsetWidth && heading.offsetHeight) : true,
        heroCtaVisible: cta ? Boolean(cta.offsetWidth && cta.offsetHeight) : true,
        coverClipped: rect ? rect.right > window.innerWidth + 1 || rect.left < -1 : false,
        textColor: headingStyle?.color || "",
        heroBackground: heroStyle?.backgroundColor || "",
      };
    });
    const screenshotPath = screenshotDir + "/" + route.replace(/[^a-z0-9]+/gi, "_").replace(/^_$/, "home") + "_" + viewport.width + "x" + viewport.height + ".png";
    await page.screenshot({ path: screenshotPath, fullPage: false });
    await page.close();
    results.push({ route, viewport, status, screenshotPath, consoleErrors, ...metrics });
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
  if (result.consoleErrors.length) issues.push("console errors");
  return issues.map((issue) => ({ route: result.route, viewport: result.viewport, issue }));
});
console.log(JSON.stringify({ skipped: false, screenshotDir, results, blockers }, null, 2));
process.exit(blockers.length ? 1 : 0);
`);
  const result = spawnSync("npx", ["--yes", "-p", "playwright", "node", runnerPath], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
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
    };
  }
  return parsed;
}

const source = runSourceChecks();
const browser = runBrowserChecks();
const sourceBlockers = source.flatMap((check) => check.blockers.map((blocker) => ({ check: check.name, blocker })));
const browserBlockers = browser?.blockers || [];
const report = {
  generated_at: new Date().toISOString(),
  mode: baseUrl ? "browser_and_source" : "source_only",
  routes: ["/", "/library", "/book/dracula", "/reader/dracula", "/book/a-ghost-story", "/reader/a-ghost-story"],
  viewports: ["1920x1080", "1536x864", "1440x900", "1366x768", "1280x800", "1024x768", "820x1180", "430x932", "390x844"],
  source_checks: source,
  browser_checks: browser,
  critical_blockers: [...sourceBlockers, ...browserBlockers],
  visual_smoke_status: sourceBlockers.length === 0 && browserBlockers.length === 0 ? "PASS" : "FAIL",
};
fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({
  visual_smoke_status: report.visual_smoke_status,
  mode: report.mode,
  critical_blockers: report.critical_blockers.length,
  report_path: reportPath,
}, null, 2));
if (report.critical_blockers.length) process.exit(1);
