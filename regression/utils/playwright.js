const fs = require("fs");
const path = require("path");

async function getChromium() {
  try {
    return { chromium: require("playwright").chromium, skipped: false };
  } catch (error) {
    return { skipped: true, reason: `playwright package is not available: ${error.message}` };
  }
}

async function withPage(fn, options = {}) {
  const loaded = await getChromium();
  if (loaded.skipped) return loaded;
  let browser;
  try {
    browser = await loaded.chromium.launch({ headless: true });
  } catch (error) {
    return { skipped: true, reason: `playwright browser is unavailable: ${error.message}` };
  }
  const context = await browser.newContext({
    viewport: options.viewport || { width: 1280, height: 900 },
    deviceScaleFactor: 1,
  });
  await context.addInitScript(() => {
    Date.now = () => 1700000000000;
    const style = document.createElement("style");
    style.textContent = "*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}";
    document.documentElement.appendChild(style);
  });
  const page = await context.newPage();
  try {
    return await fn(page, context);
  } finally {
    await browser.close();
  }
}

async function screenshot(page, name) {
  const outDir = path.resolve("regression", "artifacts", "screenshots");
  fs.mkdirSync(outDir, { recursive: true });
  const file = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true, animations: "disabled" });
  return file;
}

module.exports = { getChromium, withPage, screenshot };
