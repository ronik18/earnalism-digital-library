#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { frontendUrl } = require("../utils/envGuard");
const { withPage } = require("../utils/playwright");

const viewports = [
  { width: 375, height: 900 },
  { width: 768, height: 1000 },
  { width: 1280, height: 900 },
  { width: 1920, height: 1080 },
];

async function main() {
  if (process.env.CI === "true") {
    throw new Error("Visual baselines may not be updated in CI.");
  }
  const outDir = path.resolve("regression", "fixtures", "visual-baselines");
  fs.mkdirSync(outDir, { recursive: true });
  for (const viewport of viewports) {
    const result = await withPage(async (page) => {
      await page.goto(`${frontendUrl()}/`, { waitUntil: "domcontentloaded" });
      await page.waitForSelector("body", { timeout: 15000 });
      await page.screenshot({
        path: path.join(outDir, `home-${viewport.width}.png`),
        fullPage: true,
        animations: "disabled",
      });
    }, { viewport });
    if (result && result.skipped) throw new Error(result.reason);
  }
  console.log(`Updated visual baselines in ${outDir}`);
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
