#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = String(process.env.RECOVERY_REVIEW_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(process.env.RECOVERY_REVIEW_OUTPUT || "uat/evidence/pr469-postmerge-recovery/current");
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("RECOVERY_REVIEW_BASE_URL must be an isolated loopback build.");
fs.mkdirSync(output, { recursive: true });

const captures = [];
const errors = [];
const knownLiveBook = {
  slug: "a-ghost-story", title: "A Ghost Story", title_en: "A Ghost Story", author: "Mark Twain",
  language: "en", publication_status: "LIVE_APPROVED", reader_enabled: true,
  public_route: "/book/a-ghost-story", reader_url: "/reader/a-ghost-story", preview_enabled: true,
  preview_url: "/reader/a-ghost-story", chapters: [{ id: "a-ghost-story-chapter-1", title: "A Ghost Story", is_preview: true }],
  audiobook_enabled: false,
};

async function makePage(browser, width, height, apiMode = {}) {
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", reducedMotion: "reduce", serviceWorkers: "block" });
  const page = await context.newPage();
  const pageErrors = [];
  const requestFailures = [];
  const apiCalls = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error" && !/Failed to load resource/i.test(message.text())) pageErrors.push(message.text()); });
  page.on("requestfailed", (request) => requestFailures.push({ url: request.url(), error: request.failure()?.errorText || "unknown" }));
  await context.route("**/api/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname.replace(/^\/api/, "");
    apiCalls.push({ method: request.method(), pathname });
    const mode = apiMode[pathname];
    if (typeof mode === "function") return mode(route, request);
    if (mode?.delay) await new Promise((resolve) => setTimeout(resolve, mode.delay));
    if (mode?.status && mode.status >= 400) return route.fulfill({ status: mode.status, contentType: "application/json", body: JSON.stringify({ detail: mode.detail || "Please try again later." }) });
    if (mode?.body !== undefined) return route.fulfill({ status: mode.status || 200, contentType: "application/json", body: JSON.stringify(mode.body) });
    if (pathname === "/settings") return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
    if (pathname === "/books") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([knownLiveBook]) });
    if (pathname === "/books/a-ghost-story") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(knownLiveBook) });
    if (pathname === "/payments/offers") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ packs: [{ id: "30", minutes: 30, price_inr: 49 }, { id: "60", minutes: 60, price_inr: 89 }, { id: "180", minutes: 180, price_inr: 239 }, { id: "600", minutes: 600, price_inr: 499 }], config: { configured: false, mode: "visual-fixture" } }) });
    if (pathname === "/payments/packs") return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
  return { context, page, pageErrors, requestFailures, apiCalls };
}

async function capture(browser, { id, route, width = 1440, height = 1000, apiMode = {}, action, assertState }) {
  const session = await makePage(browser, width, height, apiMode);
  const { page } = session;
  await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.evaluate(async () => { await document.fonts.ready; await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))); });
  if (action) await action(page);
  if (assertState) await assertState(page);
  const layout = await page.evaluate(() => ({ scroll_width: document.documentElement.scrollWidth, client_width: document.documentElement.clientWidth, viewport_width: window.innerWidth }));
  assert.equal(layout.scroll_width, layout.client_width, `${id}: horizontal overflow`);
  const filename = `${id}-${width}.png`;
  await page.screenshot({ path: path.join(output, filename), fullPage: true, animations: "disabled" });
  const result = { id, route, viewport: { width, height }, screenshot: filename, layout, page_errors: session.pageErrors, request_failures: session.requestFailures, api_calls: session.apiCalls };
  assert.deepEqual(session.pageErrors, [], `${id}: browser console/page errors`);
  assert.deepEqual(session.requestFailures, [], `${id}: failed requests`);
  captures.push(result);
  errors.push(...session.pageErrors);
  await session.context.close();
  return result;
}

const browser = await chromium.launch({ headless: true });
try {
  for (const width of [1440, 390]) {
    for (const state of ["validation", "success", "error"]) {
      const responseMode = state === "error" ? { status: 422, detail: "Please try again later." } : { status: 200, body: { message: "Thank you for joining." } };
      await capture(browser, {
        id: `newsletter-${state}`, route: "/", width, height: width === 390 ? 844 : 1000,
        apiMode: { "/newsletter": responseMode },
        action: async (page) => {
          const form = page.getByTestId("newsletter-card");
          await form.waitFor();
          if (state === "validation") {
            await page.getByTestId("newsletter-submit").click();
            assert.equal(await page.getByTestId("newsletter-name").evaluate((node) => node.validity.valueMissing), true);
          } else {
            await page.getByTestId("newsletter-name").fill("Sample Reader");
            await page.getByTestId("newsletter-email").fill("reader@example.invalid");
            await page.getByTestId("newsletter-submit").click();
            await page.locator("#newsletter-status").waitFor();
            await page.waitForFunction((expected) => document.querySelector("#newsletter-status")?.textContent.includes(expected), state === "error" ? "Please try again later." : "Welcome to the Reading Circle");
          }
        },
      });
    }
  }

  for (const width of [1440, 390]) {
    await capture(browser, { id: "contact-error", route: "/contact", width, height: width === 390 ? 844 : 1000, apiMode: { "/contact": { status: 422, detail: "Please review your message and try again." } }, action: async (page) => {
      await page.getByTestId("contact-name").fill("Review Reader");
      await page.getByTestId("contact-email-input").fill("reader@example.invalid");
      await page.getByTestId("contact-message").fill("A synthetic owner review submission.");
      await page.getByTestId("contact-submit").click();
      await page.getByRole("alert").waitFor();
    } });
    await capture(browser, { id: "contact-success", route: "/contact", width, height: width === 390 ? 844 : 1000, apiMode: { "/contact": { status: 200, body: { ok: true } } }, action: async (page) => {
      await page.getByTestId("contact-name").fill("Review Reader");
      await page.getByTestId("contact-email-input").fill("reader@example.invalid");
      await page.getByTestId("contact-message").fill("A synthetic owner review submission.");
      await page.getByTestId("contact-submit").click();
      await page.waitForFunction(() => document.querySelector("#contact-form-status")?.textContent.includes("Thank you. Your message has been received."));
    } });
  }

  for (const width of [1440, 390]) {
    await capture(browser, { id: "reading-pass-api-unavailable", route: "/pricing", width, height: width === 390 ? 844 : 1000, apiMode: { "/payments/offers": { status: 503 }, "/payments/packs": { status: 503 }, "/payments/config": { status: 503 } }, assertState: async (page) => page.getByTestId("pricing-offers-error").waitFor() });
  }

  for (const width of [1440, 390]) {
    for (const form of ["login", "signup"]) {
      const route = form === "login" ? "/login?next=%2Fpricing" : "/signup";
      const testId = form === "login" ? "user-login-form" : "user-signup-form";
      const submitId = form === "login" ? "user-login-submit" : "user-signup-submit";
      const emailId = form === "login" ? "user-login-email" : "user-signup-email";
      const state = await makePage(browser, width, width === 390 ? 844 : 1000, {
        [form === "login" ? "/users/login" : "/users/signup"]: async (routeRequest) => {
          await new Promise((resolve) => setTimeout(resolve, 1200));
          return routeRequest.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Review-only request stopped before account creation." }) });
        },
      });
      await state.page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded" });
      await state.page.getByTestId(testId).waitFor();
      if (form === "login") await state.page.getByTestId("login-continuation-note").waitFor();
      else await state.page.getByTestId("signup-wallet-note").waitFor();
      const validationFile = `${form}-validation-${width}.png`;
      await state.page.screenshot({ path: path.join(output, validationFile), fullPage: true, animations: "disabled" });
      await state.page.getByTestId(emailId).fill("reader@example.invalid");
      if (form === "login") await state.page.getByTestId("user-login-password").fill("review-only-password");
      else {
        await state.page.getByTestId("user-signup-name").fill("Review Reader");
        await state.page.getByTestId("user-signup-password").fill("review-only-password");
      }
      await state.page.getByTestId(submitId).click();
      await state.page.getByText(form === "login" ? "Signing in…" : "Creating account…", { exact: true }).waitFor();
      const loadingFile = `${form}-submitting-${width}.png`;
      await state.page.screenshot({ path: path.join(output, loadingFile), fullPage: true, animations: "disabled" });
      const layout = await state.page.evaluate(() => ({ scroll_width: document.documentElement.scrollWidth, client_width: document.documentElement.clientWidth, viewport_width: window.innerWidth }));
      assert.equal(layout.scroll_width, layout.client_width, `${form} submitting ${width}: horizontal overflow`);
      const result = { id: `${form}-validation-and-submitting`, route, viewport: { width, height: width === 390 ? 844 : 1000 }, screenshot: [validationFile, loadingFile], layout, page_errors: state.pageErrors, request_failures: state.requestFailures, api_calls: state.apiCalls, submission_fixture: "delayed unauthenticated local response; no account created" };
      assert.deepEqual(state.pageErrors, [], `${form}: browser errors`);
      assert.deepEqual(state.requestFailures, [], `${form}: failed requests`);
      captures.push(result);
      await state.context.close();
    }
  }

  const result = { result: "PASS", classification: "ISOLATED_LOCAL_FIXTURE_EVIDENCE_ONLY", generated_at: new Date().toISOString(), output, captures };
  fs.writeFileSync(path.join(output, "summary.json"), `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
