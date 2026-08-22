const { test, expect } = require("playwright/test");

const VIEWPORT = { width: 1440, height: 1000 };
const ALLOWED_MASKS = [
  "[data-visual-mask='cover-art']",
  "[data-visual-mask='book-title']",
  "[data-visual-mask='book-author']",
  "[data-visual-mask='live-price']",
  "[data-visual-mask='timestamp']",
  "[data-visual-mask='availability']",
];

function visualMasks(page) {
  return ALLOWED_MASKS.map((selector) => page.locator(selector));
}

async function assertReferencePage(page, route, pageTestId, snapshot) {
  const pageErrors = [];
  const consoleErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto(route, { waitUntil: "networkidle" });
  await expect(page.getByTestId(pageTestId)).toBeVisible();
  await expect(page).toHaveScreenshot(snapshot, {
    animations: "disabled",
    caret: "hide",
    mask: visualMasks(page),
    maxDiffPixelRatio: 0.005,
  });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow, `${route} has horizontal overflow`).toBe(false);
  expect(pageErrors, `${route} emitted a page error`).toEqual([]);
  expect(consoleErrors, `${route} emitted a console error`).toEqual([]);
}

test.describe("approved desktop reference contract", () => {
  test.use({
    viewport: VIEWPORT,
    colorScheme: "light",
    reducedMotion: "reduce",
  });

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      const fixedNow = new Date("2026-08-22T00:00:00.000Z").valueOf();
      Date.now = () => fixedNow;
      window.requestAnimationFrame = (callback) => window.setTimeout(() => callback(fixedNow), 0);
    });
  });

  test("home matches the approved desktop composition", async ({ page }) => {
    await assertReferencePage(page, "/", "home-page", "home-desktop.png");
  });

  test("library matches the approved desktop composition", async ({ page }) => {
    await assertReferencePage(page, "/library", "library-page", "library-desktop.png");
  });

  test("commerce matches the approved desktop composition", async ({ page }) => {
    await assertReferencePage(page, "/pricing", "pricing-page", "commerce-desktop.png");
  });
});
