#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { chromium, firefox, webkit } from "playwright";

const args = new Map(process.argv.slice(2).map((value, index, values) => value.startsWith("--") ? [value.slice(2), values[index + 1]] : []));
const baseUrl = String(args.get("base-url") || process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(args.get("output") || "uat/evidence/p0-header-readability/manual");
const engine = String(args.get("engine") || "chromium");
const requestedRoutes = new Set(String(args.get("routes") || "").split(",").filter(Boolean));

if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) {
  throw new Error("--base-url must be an explicit loopback URL.");
}
if (!({ chromium, firefox, webkit })[engine]) throw new Error(`Unsupported engine: ${engine}`);

const routes = [
  ["home", "/"], ["library", "/library"], ["commerce", "/pricing"],
  ["book-detail", "/book/dracula"], ["about", "/about"], ["login", "/login"], ["account-fixture", "/account"],
];
const viewports = [
  [1920, 1080], [1440, 1000], [1280, 800], [1024, 768], [390, 844], [320, 568],
];
const selectedRoutes = requestedRoutes.size ? routes.filter(([id]) => requestedRoutes.has(id)) : routes;

function contrast(hexA, hexB) {
  const rgb = (value) => (value.match(/\d+(?:\.\d+)?/g) || []).slice(0, 3).map(Number);
  const luminance = (value) => rgb(value).map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
  }).reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0);
  const [a, b] = [luminance(hexA), luminance(hexB)].sort((left, right) => right - left);
  return Number(((a + 0.05) / (b + 0.05)).toFixed(2));
}

fs.mkdirSync(output, { recursive: true });
const browser = await ({ chromium, firefox, webkit })[engine].launch({ headless: true });
const records = [];
try {
  for (const [routeId, route] of selectedRoutes) {
    for (const [width, height] of viewports) {
      const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1, colorScheme: "light", reducedMotion: "reduce" });
      const errors = [];
      page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
      page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
      if (routeId === "account-fixture") {
        await page.addInitScript(() => {
          localStorage.setItem("token", "sanitized-owner-review-fixture");
          localStorage.setItem("user", JSON.stringify({ id: "fixture", name: "Owner Review", email: "fixture@example.invalid" }));
        });
      }
      const response = await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 45_000 });
      await page.waitForTimeout(900);
      const metrics = await page.evaluate(({ routeId }) => {
        const rect = (node) => node ? Object.fromEntries(["x", "y", "width", "height", "top", "right", "bottom", "left"].map((key) => [key, Number(node.getBoundingClientRect()[key].toFixed(2))])) : null;
        const style = (node) => node ? getComputedStyle(node) : null;
        const visible = (selector) => [...document.querySelectorAll(selector)].find((node) => node.getClientRects().length > 0);
        const header = document.querySelector("[data-testid=site-header]");
        const brand = visible("[data-testid=earnalism-brand-lockup]");
        const image = brand?.querySelector("img");
        const nav = visible(".premium-header-nav");
        const navItem = nav?.querySelector("a");
        const account = visible("[data-testid=nav-account], [data-testid=nav-sign-in], [data-testid=mobile-menu-toggle]");
        const search = visible("[data-testid=nav-search], [data-testid=mobile-header-search]");
        const headerStyle = style(header);
        const navStyle = style(navItem);
        const brandRect = rect(brand);
        const imageRect = rect(image);
        const headerRect = rect(header);
        const clipping = Boolean(brandRect && imageRect && (imageRect.left < brandRect.left - 0.5 || imageRect.right > brandRect.right + 0.5 || imageRect.top < brandRect.top - 0.5 || imageRect.bottom > brandRect.bottom + 0.5));
        return {
          routeId, headers: document.querySelectorAll("[data-testid=site-header]").length,
          header: headerRect, brand: brandRect, image: { ...imageRect, naturalWidth: image?.naturalWidth || 0, naturalHeight: image?.naturalHeight || 0, complete: Boolean(image?.complete) },
          nav: navItem ? { fontSize: navStyle.fontSize, lineHeight: navStyle.lineHeight, fontWeight: navStyle.fontWeight, color: navStyle.color } : null,
          headerBackground: headerStyle?.backgroundColor || "",
          account: rect(account), search: rect(search), clipping,
          overlap: Boolean(brandRect && nav && brandRect.right > nav.getBoundingClientRect().left),
          overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth,
        };
      }, { routeId });
      const navContrast = metrics.nav ? contrast(metrics.nav.color, metrics.headerBackground) : null;
      const filename = `${routeId}-${width}x${height}-${engine}.png`;
      await page.screenshot({ path: path.join(output, filename), fullPage: false, animations: "disabled" });
      records.push({ route: route, width, height, engine, status: response?.status() || 0, errors, navContrast, screenshot: filename, ...metrics });
      await page.close();
    }
  }
} finally {
  await browser.close();
}

const report = { schema_version: "earnalism.p0_header_readability.capture.v1", base_url: baseUrl, engine, records };
fs.writeFileSync(path.join(output, `metrics-${engine}.json`), JSON.stringify(report, null, 2) + "\n");
const failed = records.filter((record) => record.status !== 200 || record.errors.length || record.overflow || record.headers !== 1 || !record.image.complete);
console.log(JSON.stringify({ output, engine, captured: records.length, failed: failed.length }, null, 2));
if (failed.length) process.exitCode = 1;
