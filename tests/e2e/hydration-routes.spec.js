const { expect, test } = require("playwright/test");

function localUatBaseUrl() {
  const value = String(process.env.UAT_BASE_URL || "").trim().replace(/\/$/, "");
  if (!value) throw new Error("UAT_BASE_URL is required; production fallback is disabled.");
  const parsed = new URL(value);
  if (parsed.protocol !== "http:" || parsed.hostname !== "127.0.0.1") {
    throw new Error("UAT_BASE_URL must use http://127.0.0.1 only.");
  }
  return value;
}

const BASE_URL = localUatBaseUrl();
const ROUTES = ["/", "/library", "/book/dracula", "/reader/dracula", "/pricing", "/journal", "/contact"];

for (const route of ROUTES) {
  test(`client route ${route} has no page error or hydration warning`, async ({ page }) => {
    const pageErrors = [];
    const hydrationErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("console", (message) => {
      const text = message.text();
      if (message.type() === "error" && /hydration|hydrateRoot|React error #418/i.test(text)) {
        hydrationErrors.push(text);
      }
    });

    const response = await page.goto(`${BASE_URL}${route}`, { waitUntil: "networkidle" });
    expect(response?.status(), `${route} HTTP status`).toBe(200);
    await expect(page.locator("#root")).toBeVisible();
    expect(pageErrors, `${route} page errors`).toEqual([]);
    expect(hydrationErrors, `${route} hydration errors`).toEqual([]);
  });
}
