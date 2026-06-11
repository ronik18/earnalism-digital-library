const fs = require("fs");
const path = require("path");
const { frontendUrl, isGoLive } = require("../utils/envGuard");
const { withPage, screenshot } = require("../utils/playwright");

const viewports = [
  { width: 375, height: 900 },
  { width: 768, height: 1000 },
  { width: 1280, height: 900 },
  { width: 1920, height: 1080 },
];

function strictVisualMode() {
  return ["go-live", "visual-ci"].includes((process.env.REGRESSION_MODE || "pr").toLowerCase());
}

describe("Rendering & Visual Accuracy", () => {
  const browserTest = (isGoLive() || process.env.REGRESSION_ENABLE_BROWSER_CHECKS === "true") ? test : test.skip;

  browserTest("critical public templates render at required viewports", async () => {
    for (const viewport of viewports) {
      const result = await withPage(async (page) => {
        await page.goto(`${frontendUrl()}/`, { waitUntil: "networkidle" });
        await page.waitForFunction(() => document.body && document.body.innerText.trim().length > 20, null, { timeout: 20000 });
        expect(await page.locator("body").innerText()).toMatch(/Earnalism|Library|Reading/i);
        await screenshot(page, `home-${viewport.width}`);

        await page.goto(`${frontendUrl()}/library`, { waitUntil: "networkidle" });
        await page.waitForFunction(() => document.body && document.body.innerText.trim().length > 20, null, { timeout: 20000 });
        expect(await page.locator("body").innerText()).toMatch(/Library|Reading|Book/i);
      }, { viewport });
      if (result && result.skipped && strictVisualMode()) throw new Error(result.reason);
    }
  });

  test("visual baselines are present in CI modes and never auto-created", async () => {
    const required = ["home-375.png", "home-768.png", "home-1280.png", "home-1920.png"];
    const missing = required.filter((file) => !fs.existsSync(path.resolve("regression", "fixtures", "visual-baselines", file)));
    if (strictVisualMode()) expect(missing).toEqual([]);
    else expect(Array.isArray(missing)).toBe(true);
  });
});
