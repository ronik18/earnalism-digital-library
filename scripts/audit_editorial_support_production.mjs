import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const site = "https://theearnalism.com";
const routes = [
  { id: "journal", path: "/journal" },
  { id: "article", path: "/journal/how-reading-shapes-better-founders" },
  { id: "contact", path: "/contact" },
  { id: "micro-story", path: "/micro-story" },
  { id: "not-found", path: "/not-a-real-route" },
  { id: "removed", path: "/product/patterned-wrap-dress" },
];
const viewports = [{ name: "mobile", width: 390, height: 844 }, { name: "desktop", width: 1440, height: 1000 }];
const forbidden = ["Chapter 1 free", "First chapter free", "Chapter 1 is on us", "First 3 minutes free", "First 180 seconds free", "Free audiobook preview", "Free listening sample", "Listen free"];
const output = process.argv.includes("--out") ? process.argv[process.argv.indexOf("--out") + 1] : path.resolve("uat/evidence/editorial-support-modernization/production-baseline/before");

const meta = (html, pattern) => (html.match(pattern) || [])[1] || "";
const text = (value) => String(value || "").replace(/\s+/g, " ").trim();

async function main() {
  await mkdir(path.join(output, "screenshots"), { recursive: true });
  const result = [];
  const browser = await chromium.launch({ headless: true });
  try {
    for (const route of routes) {
      const response = await fetch(site + route.path, { redirect: "follow" });
      const html = await response.text();
      const raw = {
        status: response.status,
        final_url: response.url,
        title: text(meta(html, /<title[^>]*>([\s\S]*?)<\/title>/i)),
        description: text(meta(html, /<meta[^>]+name=["']description["'][^>]+content=["']([^"']*)/i)),
        canonical_url: text(meta(html, /<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']*)/i)),
        robots: text(meta(html, /<meta[^>]+name=["']robots["'][^>]+content=["']([^"']*)/i)) || response.headers.get("x-robots-tag") || "",
        h1: text(meta(html, /<h1[^>]*>([\s\S]*?)<\/h1>/i).replace(/<[^>]+>/g, "")),
        generic_home_fallback: /A library made for lingering/i.test(html),
        forbidden_copy: forbidden.filter((phrase) => html.toLowerCase().includes(phrase.toLowerCase())),
      };
      for (const viewport of viewports) {
        const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
        const consoleErrors = [];
        const pageErrors = [];
        page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
        page.on("pageerror", (error) => pageErrors.push(error.message));
        const navigation = await page.goto(site + route.path, { waitUntil: "networkidle", timeout: 30000 });
        const metrics = await page.evaluate(() => ({
          h1: document.querySelector("h1")?.textContent?.replace(/\s+/g, " ").trim() || "",
          overflow: document.documentElement.scrollWidth > window.innerWidth,
          logo_visible: Array.from(document.images).some((image) => /earnalism/i.test(image.alt || "") && image.naturalWidth > 0 && image.getBoundingClientRect().width > 0),
          footer_present: Boolean(document.querySelector("footer")),
        }));
        const screenshot = route.id + "-" + viewport.name + ".png";
        await page.screenshot({ path: path.join(output, "screenshots", screenshot), fullPage: true });
        result.push({ route: route.path, viewport: viewport.name, status: navigation?.status() || raw.status, final_url: page.url(), raw_html: raw, ...metrics, console_errors: consoleErrors, page_errors: pageErrors, screenshot: "screenshots/" + screenshot });
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  const rawResults = result.map((entry) => ({ route: entry.route, raw_html: entry.raw_html }));
  await writeFile(path.join(output, "route-results.json"), JSON.stringify(result, null, 2) + "\n");
  await writeFile(path.join(output, "raw-html-results.json"), JSON.stringify(rawResults, null, 2) + "\n");
  await writeFile(path.join(output, "static-seo-gap-report.json"), JSON.stringify(result.map((entry) => ({ route: entry.route, viewport: entry.viewport, status: entry.status, generic_home_fallback: entry.raw_html.generic_home_fallback, missing_title: !entry.raw_html.title, missing_description: !entry.raw_html.description, missing_canonical: !entry.raw_html.canonical_url, missing_robots: !entry.raw_html.robots, forbidden_copy: entry.raw_html.forbidden_copy })), null, 2) + "\n");
  await writeFile(path.join(output, "before-review.html"), "<!doctype html><title>Earnalism editorial/support production baseline</title><pre>" + text(JSON.stringify(result, null, 2)).replace(/&/g, "&amp;").replace(/</g, "&lt;") + "</pre>");
  console.log("EDITORIAL_SUPPORT_PRODUCTION_BASELINE=" + output);
}

main().catch((error) => { console.error(error.stack || error.message); process.exitCode = 1; });
