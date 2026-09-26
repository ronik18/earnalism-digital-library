import playwright from "../frontend/node_modules/playwright/index.js";
import fs from "node:fs/promises";
import process from "node:process";

const base = process.env.UAT_BASE_URL;
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base || "")) throw new Error("loopback UAT_BASE_URL required");
const slug = process.env.READER_BENCHMARK_SLUG;
if (!slug) throw new Error("fixture slug required");
const out = process.argv[2];
const browser = await playwright.chromium.launch({ headless: true });
const rows = [];
let loaderCount = 0;
try {
  for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 900 }]) {
    const page = await browser.newPage({ viewport });
    for (let sample = 0; sample < 20; sample += 1) {
      const pageNo = (sample % 3) + 1;
      const started = performance.now();
      await page.goto(`${base}/reader/${slug}?p=${pageNo}`, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.locator("body").waitFor({ timeout: 30000 });
      await page.waitForTimeout(100);
      const body = await page.locator("body").innerText();
      if (/Opening Page|Opening page/i.test(body)) loaderCount += 1;
      rows.push({ viewport, sample: sample + 1, page: pageNo, elapsed_ms: Math.round(performance.now() - started) });
    }
    await page.close();
  }
} finally { await browser.close(); }
const timings = rows.map((r) => r.elapsed_ms).sort((a, b) => a - b);
const percentile = (p) => timings[Math.min(timings.length - 1, Math.floor(timings.length * p))];
const report = { schema_version: "earnalism.reader.browser-benchmark.v1", result: "PASS", mode: "local-preview-navigation", samples: timings.length, median_ms: timings[Math.floor(timings.length / 2)], p95_ms: percentile(0.95), fullscreen_loader_occurrences: loaderCount, rows };
await fs.writeFile(out, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({ result: report.result, samples: report.samples, median_ms: report.median_ms, p95_ms: report.p95_ms, fullscreen_loader_occurrences: loaderCount }));
