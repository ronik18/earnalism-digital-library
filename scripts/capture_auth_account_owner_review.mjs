#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(process.env.OWNER_REVIEW_CAPTURE_OUTPUT || "uat/evidence/auth-account-owner-review/current");

if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) {
  throw new Error("UAT_BASE_URL must be an explicit loopback URL.");
}

const fixtureUser = {
  id: "owner-review-reader",
  name: "Sample Reader",
  email: "reader@example.invalid",
  reading_seconds_balance: 18_600,
};

const fixtureTransactions = [
  { id: "review-activity-1", type: "consume", reason: "Reading Dracula", seconds: 150, created_at: "2026-08-23T10:00:00.000Z", session_id: "review-session-1" },
  { id: "review-activity-2", type: "credit", reason: "Reading Pass", seconds: 18_000, created_at: "2026-08-22T10:00:00.000Z" },
];

const fixtureDevices = {
  devices: [
    { session_id: "review-device-current", device_id: "review-device-current", device_label: "Review browser", current: true, status: "active", last_seen_at: "2026-08-23T10:00:00.000Z" },
    { session_id: "review-device-secondary", device_id: "review-device-secondary", device_label: "Review tablet", current: false, status: "active", last_seen_at: "2026-08-22T10:00:00.000Z" },
  ],
};

const states = [
  { id: "login-desktop", route: "/login", viewport: { width: 1440, height: 1000 }, required: ["[data-testid=user-login-page]", "[data-testid=user-login-form]", "[data-testid=earnalism-brand-lockup]"] },
  { id: "login-mobile", route: "/login", viewport: { width: 390, height: 844 }, required: ["[data-testid=user-login-page]", "[data-testid=user-login-form]", "[data-testid=earnalism-brand-lockup]"] },
  { id: "signup-desktop", route: "/signup", viewport: { width: 1440, height: 1000 }, required: ["[data-testid=user-signup-page]", "[data-testid=user-signup-form]", "[data-testid=earnalism-brand-lockup]"] },
  { id: "signup-mobile", route: "/signup", viewport: { width: 390, height: 844 }, required: ["[data-testid=user-signup-page]", "[data-testid=user-signup-form]", "[data-testid=earnalism-brand-lockup]"] },
  { id: "account-desktop", route: "/account", viewport: { width: 1440, height: 1000 }, requiresFixture: true, required: ["[data-testid=account-page]", "[data-testid=account-balance-card]", "[data-testid=reading-pass-devices]"] },
  { id: "account-mobile", route: "/account", viewport: { width: 390, height: 844 }, requiresFixture: true, required: ["[data-testid=account-page]", "[data-testid=account-balance-card]", "[data-testid=reading-pass-devices]"] },
];

function fixtureResponse(url) {
  const pathname = new URL(url).pathname;
  if (pathname.endsWith("/users/me")) return fixtureUser;
  if (pathname.endsWith("/users/me/transactions")) return fixtureTransactions;
  if (pathname.endsWith("/books")) return [];
  if (pathname.endsWith("/home/hero")) return { schema_version: "home-hero-v1", hero: {}, revision: "owner-review-fixture" };
  if (pathname.endsWith("/reading-pass/config")) return { enabled: true, public_text_pages: 3, public_audio_seconds: 0 };
  if (pathname.endsWith("/reading-pass/devices")) return fixtureDevices;
  return null;
}

fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const captures = [];
  for (const state of states) {
    const context = await browser.newContext({
      viewport: state.viewport,
      deviceScaleFactor: 1,
      colorScheme: "light",
      locale: "en-US",
      timezoneId: "UTC",
      reducedMotion: "reduce",
    });
    await context.route("http://127.0.0.1:18007/api/**", async (route) => {
      const body = fixtureResponse(route.request().url());
      if (body) {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
        return;
      }
      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "fixture route not found" }) });
    });
    const page = await context.newPage();
    const errors = [];
    const failedRequests = [];
    page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(`console:${message.text()}`);
    });
    page.on("response", (response) => {
      if (response.status() >= 400) failedRequests.push(`${response.status()}:${response.url()}`);
    });
    await page.addInitScript(({ authenticated }) => {
      const fixedNow = new Date("2026-08-23T10:00:00.000Z").valueOf();
      Date.now = () => fixedNow;
      window.requestAnimationFrame = (callback) => window.setTimeout(() => callback(fixedNow), 0);
      if (authenticated) localStorage.setItem("earnalism_user_token", "owner-review-fixture-only");
    }, { authenticated: Boolean(state.requiresFixture) });
    const response = await page.goto(`${baseUrl}/`, { waitUntil: "networkidle", timeout: 90_000 });
    await page.evaluate((route) => {
      window.history.pushState({}, "", route);
      window.dispatchEvent(new PopStateEvent("popstate"));
    }, state.route);
    await page.waitForFunction((required) => required.every((selector) => document.querySelector(selector)), state.required, { timeout: 30_000 });
    await page.waitForLoadState("networkidle");
    await page.keyboard.press("Tab");
    const metrics = await page.evaluate((required) => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      required: required.map((selector) => Boolean(document.querySelector(selector))),
      focusTarget: document.activeElement?.matches("a[href], button, input, select, textarea")
        ? document.activeElement.tagName.toLowerCase()
        : "",
      interactiveControlCount: document.querySelectorAll("a[href], button, input, select, textarea").length,
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
      failedRequests,
      scrollWidth: metrics.scrollWidth,
      clientWidth: metrics.clientWidth,
      required: metrics.required,
      keyboard_focus_target: metrics.focusTarget,
      interactive_control_count: metrics.interactiveControlCount,
      accessible_fixture: Boolean(state.requiresFixture),
      fixture_only: Boolean(state.requiresFixture),
      deviceScaleFactor: 1,
      locale: "en-US",
      timezone: "UTC",
    });
    await context.close();
  }
  fs.writeFileSync(path.join(output, "capture.json"), JSON.stringify(captures, null, 2) + "\n");
  const failed = captures.filter((capture) => (
    capture.status !== 200
    || capture.errors.length > 0
    || capture.failedRequests.length > 0
    || capture.scrollWidth !== capture.clientWidth
    || capture.required.includes(false)
    || !capture.keyboard_focus_target
  ));
  console.log(JSON.stringify({ captured: captures.length, failed: failed.length, output }));
  if (failed.length) process.exitCode = 1;
} finally {
  await browser.close();
}
