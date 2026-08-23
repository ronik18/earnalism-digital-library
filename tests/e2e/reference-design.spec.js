const { test, expect } = require("playwright/test");

const VIEWPORT = { width: 1440, height: 1000 };
const RESPONSIVE_VIEWPORTS = [
  { name: "320x568", width: 320, height: 568 },
  { name: "360x800", width: 360, height: 800 },
  { name: "390x844", width: 390, height: 844 },
  { name: "430x932", width: 430, height: 932 },
  { name: "768x1024", width: 768, height: 1024 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1440x1000", width: 1440, height: 1000 },
  { name: "1920x1080", width: 1920, height: 1080 },
];
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

async function assertResponsivePage(page, route, pageTestId, viewport) {
  const pageErrors = [];
  const consoleErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.setViewportSize(viewport);
  await page.goto(route, { waitUntil: "networkidle" });
  await expect(page.getByTestId(pageTestId)).toBeVisible();
  const geometry = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(geometry.scrollWidth, `${route} overflows at ${viewport.width}px`).toBeLessThanOrEqual(geometry.clientWidth + 1);
  expect(pageErrors, `${route} emitted a page error at ${viewport.width}px`).toEqual([]);
  expect(consoleErrors, `${route} emitted a console error at ${viewport.width}px`).toEqual([]);
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

for (const viewport of RESPONSIVE_VIEWPORTS) {
  test.describe(`approved responsive contract ${viewport.name}`, () => {
    test.use({ colorScheme: "light", reducedMotion: "reduce" });

    test("Home retains the approved structure without overflow", async ({ page }) => {
      await assertResponsivePage(page, "/", "home-page", viewport);
      await expect(page.getByTestId("home-quick-paths")).toBeVisible();
    });

    test("Library retains its search and responsive filter affordance", async ({ page }) => {
      await assertResponsivePage(page, "/library", "library-page", viewport);
      await expect(page.getByTestId("library-search")).toBeVisible();
      if (viewport.width < 1024) await expect(page.getByRole("button", { name: "Filters" })).toBeVisible();
    });

    test("Commerce retains its wallet and offer structure", async ({ page }) => {
      await assertResponsivePage(page, "/pricing", "pricing-page", viewport);
      await expect(page.getByTestId("pricing-wallet-explainer")).toBeVisible();
    });
  });
}
