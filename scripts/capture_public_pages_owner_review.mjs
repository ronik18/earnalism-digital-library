#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(process.env.OWNER_REVIEW_CAPTURE_OUTPUT || "uat/evidence/actual-redesign/after");
const strict = process.env.OWNER_REVIEW_CAPTURE_STRICT !== "false";

if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) {
  throw new Error("UAT_BASE_URL must be an explicit loopback URL.");
}

const states = [
  { id: "home-desktop", route: "/", viewport: { width: 1440, height: 1000 }, required: ["[data-testid=home-page]", "header"] },
  { id: "home-mobile", route: "/", viewport: { width: 390, height: 844 }, required: ["[data-testid=home-page]", "header"] },
  { id: "library-desktop", route: "/library", viewport: { width: 1440, height: 1000 }, required: ["[data-testid=library-page]", "[data-testid=library-search]"] },
  { id: "library-mobile", route: "/library", viewport: { width: 390, height: 844 }, required: ["[data-testid=library-page]", "[data-testid=library-search]"] },
  { id: "commerce-desktop", route: "/pricing", viewport: { width: 1440, height: 1000 }, required: ["[data-testid=pricing-page]", "[data-testid=pricing-wallet-explainer]"] },
  { id: "commerce-mobile", route: "/pricing", viewport: { width: 390, height: 844 }, required: ["[data-testid=pricing-page]", "[data-testid=pricing-wallet-explainer]"] },
];

fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const captures = [];
  for (const state of states) {
    const page = await browser.newPage({
      viewport: state.viewport,
      deviceScaleFactor: 1,
      colorScheme: state.id.includes("library") ? "light" : "dark",
      reducedMotion: "reduce",
    });
    const errors = [];
    page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(`console:${message.text()}`);
    });
    await page.addInitScript(() => {
      const fixedNow = new Date("2026-08-23T00:00:00.000Z").valueOf();
      Date.now = () => fixedNow;
      window.requestAnimationFrame = (callback) => window.setTimeout(() => callback(fixedNow), 0);
    });
    const response = await page.goto(`${baseUrl}${state.route}`, { waitUntil: "networkidle", timeout: 90_000 });
    const metrics = await page.evaluate((required) => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      required: required.map((selector) => Boolean(document.querySelector(selector))),
    }), state.required);
    const screenshot = path.join(output, `${state.id}.png`);
    await page.screenshot({ path: screenshot, fullPage: false, animations: "disabled" });
    captures.push({
      id: state.id,
      route: state.route,
      width: state.viewport.width,
      height: state.viewport.height,
      status: response?.status() || 0,
      errors,
      scrollWidth: metrics.scrollWidth,
      clientWidth: metrics.clientWidth,
      required: metrics.required,
      deviceScaleFactor: 1,
      fonts: "loaded",
    });
    await page.close();
  }
  fs.writeFileSync(path.join(output, "capture.json"), JSON.stringify(captures, null, 2) + "\n");
  const failed = captures.filter((capture) => capture.status !== 200 || capture.errors.length || capture.scrollWidth !== capture.clientWidth || capture.required.includes(false));
  console.log(JSON.stringify({ captured: captures.length, failed: failed.length, strict, output }));
  if (strict && failed.length) process.exitCode = 1;
} finally {
  await browser.close();
}
