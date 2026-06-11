const { frontendUrl, isGoLive } = require("../utils/envGuard");
const { apiGet } = require("../utils/http");
const { withPage } = require("../utils/playwright");

describe("End-to-End UAT", () => {
  const browserTest = (isGoLive() || process.env.REGRESSION_ENABLE_BROWSER_CHECKS === "true") ? test : test.skip;

  browserTest("guest browse flow reaches homepage, library, book detail, reader and 404", async () => {
    const books = (await apiGet("/books")).data;
    expect(books.length).toBeGreaterThan(0);
    const book = books[0];
    const result = await withPage(async (page) => {
      await page.goto(`${frontendUrl()}/`, { waitUntil: "networkidle" });
      await page.waitForFunction(() => document.body && document.body.innerText.trim().length > 20, null, { timeout: 20000 });
      expect(await page.locator("body").innerText()).toMatch(/Earnalism/i);

      await page.goto(`${frontendUrl()}/library`, { waitUntil: "networkidle" });
      await page.waitForFunction(() => document.body && document.body.innerText.trim().length > 20, null, { timeout: 20000 });
      expect(await page.locator("body").innerText()).toMatch(/Library|Reading/i);

      await page.goto(`${frontendUrl()}/book/${book.slug}`, { waitUntil: "networkidle" });
      await page.waitForFunction(() => document.body && document.body.innerText.trim().length > 20, null, { timeout: 20000 });
      expect(await page.locator("body").innerText()).toContain(book.title);

      await page.goto(`${frontendUrl()}/reader/${book.slug}`, { waitUntil: "networkidle" });
      await page.waitForFunction(() => document.body && document.body.innerText.trim().length > 20, null, { timeout: 20000 });
      expect(await page.locator("body").innerText()).toMatch(/Reading|access|chapter|preview/i);

      await page.setViewportSize({ width: 375, height: 900 });
      await page.goto(`${frontendUrl()}/library`, { waitUntil: "networkidle" });
      expect(await page.locator("body").innerText()).toMatch(/Library|Reading/i);

      await page.goto(`${frontendUrl()}/book/regression-invalid-slug`, { waitUntil: "networkidle" });
      expect(await page.locator("body").innerText()).toMatch(/not found|no longer available|404/i);
    });
    if (result && result.skipped) throw new Error(result.reason);
  });
});
