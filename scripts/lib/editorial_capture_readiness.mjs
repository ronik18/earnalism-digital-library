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
