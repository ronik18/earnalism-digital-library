/** Bounded rendered readiness; unrelated open connections are not app readiness. */
export async function openEditorialRoute(page, baseUrl, route, required) {
  const response = await page.goto(baseUrl + "/", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector('#root header[data-testid="site-header"]', { state: "visible", timeout: 30000 });
  await page.evaluate((nextRoute) => { window.history.pushState({}, "", nextRoute); window.dispatchEvent(new PopStateEvent("popstate")); }, route);
  await page.waitForSelector(required, { state: "visible", timeout: 30000 });
  await page.waitForFunction(() => document.fonts.status === "loaded"
    && Array.from(document.images).some((image) => /earnalism/i.test(image.alt || "") && image.complete && image.naturalWidth > 0), null, { timeout: 30000 });
  return response;
}

/** Flush a visible, laid-out compositor frame before the one screenshot attempt. */
export async function prepareEditorialScreenshot(page) {
  await page.bringToFront();
  await page.waitForFunction(() => document.visibilityState === "visible"
    && document.readyState === "complete"
    && document.documentElement.clientWidth > 0
    && document.body?.getBoundingClientRect().height > 0, null, { timeout: 10000 });
  await page.evaluate(() => new Promise((resolve, reject) => {
    const deadline = setTimeout(() => reject(new Error("Visible screenshot frame deadline")), 3000);
    requestAnimationFrame(() => requestAnimationFrame(() => { clearTimeout(deadline); resolve(); }));
  }));
}
