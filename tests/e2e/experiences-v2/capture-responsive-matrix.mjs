import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../../../frontend/node_modules/playwright");

const baseUrl = process.argv[2];
const outputDir = process.argv[3];
const viewports = [[320,568],[360,800],[390,844],[430,932],[768,1024],[1024,768],[1280,800],[1440,1000],[1920,1080]];
const panels = ["reader", "listener", "about"];
fs.mkdirSync(outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [];
for (const [width, height] of viewports) for (const panel of panels) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`${baseUrl}/?panel=${panel}`, { waitUntil: "networkidle" });
  const metrics = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth > window.innerWidth, touchTargetFailures: [...document.querySelectorAll("button")].filter((button) => { const rect = button.getBoundingClientRect(); const style = getComputedStyle(button); const visible = rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none"; return visible && window.innerWidth <= 767 && (rect.width < 44 || rect.height < 44); }).length }));
  await page.screenshot({ path: path.join(outputDir, `${panel}-${width}x${height}.png`), fullPage: false, animations: "disabled" });
  results.push({ panel, width, height, ...metrics, errors });
  await page.close();
}
await browser.close();
fs.writeFileSync(path.join(outputDir, "responsive-results.json"), JSON.stringify(results, null, 2));
if (results.some((result) => result.overflow || result.touchTargetFailures || result.errors.length)) process.exitCode = 1;
console.log(JSON.stringify({ total: results.length, passed: results.filter((result) => !result.overflow && !result.touchTargetFailures && !result.errors.length).length }));
