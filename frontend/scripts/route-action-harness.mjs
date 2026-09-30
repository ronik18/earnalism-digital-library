#!/usr/bin/env node

import assert from "node:assert/strict";
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const buildDir = path.join(frontendDir, "build");
const buildIndex = path.join(buildDir, "index.html");
const mimeTypes = { ".css": "text/css", ".html": "text/html", ".ico": "image/x-icon", ".js": "text/javascript", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".webp": "image/webp", ".woff2": "font/woff2" };
await stat(buildIndex).catch(() => { throw new Error("Build the frontend before running this harness: npm run build"); });
const localServer = createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url || "/", "http://localhost").pathname);
  const candidate = path.resolve(buildDir, `.${pathname}`);
  if (candidate.startsWith(buildDir + path.sep)) {
    try {
      const fileStat = await stat(candidate);
      if (fileStat.isFile()) {
        response.writeHead(200, { "Content-Type": mimeTypes[path.extname(candidate)] || "application/octet-stream" });
        response.end(await readFile(candidate));
        return;
      }
    } catch { /* SPA route falls through to index.html. */ }
  }
  response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
  response.end(await readFile(buildIndex));
});
await new Promise((resolve, reject) => {
  localServer.once("error", reject);
  localServer.listen(0, "127.0.0.1", resolve);
});
const address = localServer.address();
const baseUrl = `http://127.0.0.1:${address.port}`;
const parsedBase = new URL(baseUrl);

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(8000);
const calls = [];
let paymentMode = "test";
const mockResponse = (status, data) => ({
  status,
  contentType: "application/json",
  body: JSON.stringify(data),
});

await page.addInitScript(() => {
  localStorage.setItem("earnalism_user_token", "local-route-audit-token");
  window.Razorpay = function LocalOnlyCheckoutStub(options) {
    this.on = () => {};
    this.open = () => { void options.handler({ razorpay_order_id: "local-test-order", razorpay_payment_id: "local-test-payment", razorpay_signature: "local-test-signature" }); };
  };
});
await page.route("**/*", async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  if (url.origin !== parsedBase.origin) return route.abort("blockedbyclient");
  if (!url.pathname.startsWith("/api/")) return route.continue();

  const method = request.method().toUpperCase();
  const path = url.pathname;
  let status = 200;
  let data = {};

  if (method === "GET" && path === "/api/payments/offers") {
    data = {
      packs: [{ id: "local-audit-30", label: "30 minutes", note: "Local test offer", minutes: 30, price_inr: 49, amount_paise: 4900 }],
      config: { configured: paymentMode === "configured", mode: paymentMode === "configured" ? "live" : "test", key_id: "" },
    };
  } else if (method === "GET" && path === "/api/users/me") {
    data = { id: "local-audit-user", name: "Route Audit", email: "route-audit@example.invalid", reading_seconds_balance: 0 };
  } else if (method === "POST" && path === "/api/newsletter") {
    status = 201;
    data = { message: "Welcome to the Reading Circle. We will write when a story is worth opening together." };
  } else if (method === "POST" && path === "/api/contact") {
    status = 202;
    data = { message: "Local test inquiry accepted." };
  } else if (method === "POST" && path === "/api/payments/_simulate_topup") {
    status = 201;
    data = { intent_id: "local-test-intent" };
  } else if (method === "POST" && path === "/api/payments/_simulate_webhook") {
    data = { accepted: true, reading_seconds_balance: 1800 };
  } else if (method === "POST" && path === "/api/payments/topup") {
    status = 201;
    data = { key_id: "local-test-key", amount: 4900, currency: "INR", name: "Local test", description: "No charge", razorpay_order_id: "local-test-order", prefill: {}, intent_id: "local-test-intent" };
  } else if (method === "POST" && path === "/api/payments/verify") {
    data = { accepted: true, reading_seconds_balance: 1800 };
  } else if (method === "GET" && path === "/api/books") {
    data = [];
  } else if (method === "GET" && path === "/api/home/curated") {
    data = {};
  }

  calls.push({ method, path, status, testOnly: true });
  await route.fulfill(mockResponse(status, data));
});

const results = [];
try {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.getByTestId("newsletter-name").fill("Route Audit Fixture");
  await page.getByTestId("newsletter-email").fill("route-audit@example.invalid");
  await page.getByTestId("newsletter-submit").click();
  await page.locator("#newsletter-status").getByText(/Welcome to the Reading Circle/).waitFor();
  assert(calls.some((call) => call.method === "POST" && call.path === "/api/newsletter" && call.status === 201));
  results.push({ action: "newsletter submit", result: "POST /api/newsletter → 201 (local mock)" });

  await page.getByTestId("home-reference-primary-cta").click();
  await page.waitForURL("**/library");
  assert.equal(new URL(page.url()).pathname, "/library");
  results.push({ action: "Explore the Library", result: "navigates to /library" });

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  const catalogueCard = page.getByRole("link", { name: /Browse the Library/ }).last();
  assert.equal(await catalogueCard.getAttribute("href"), "/library#library-collection");
  await catalogueCard.click();
  await page.waitForURL("**/library#library-collection");
  results.push({ action: "Browse the Library collection card", result: "navigates to /library#library-collection" });

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  const listeningCard = page.getByRole("link", { name: /Stories to hear in quiet moments/ });
  assert.equal(await listeningCard.getAttribute("href"), "/library?availability=approved-audiobook");
  await listeningCard.click();
  await page.waitForURL("**/library?availability=approved-audiobook");
  assert.equal(new URL(page.url()).searchParams.get("availability"), "approved-audiobook");
  results.push({ action: "Listening Room discovery card", result: "navigates to the approved-audiobook filter; audio remains gated" });

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  const passesLink = page.getByRole("link", { name: /View Reading Pass Plans/ });
  assert.equal(await passesLink.getAttribute("href"), "/pricing");
  await passesLink.click();
  await page.waitForURL("**/pricing");
  results.push({ action: "View Reading Pass Plans", result: "navigates to /pricing" });

  await page.goto(`${baseUrl}/library`, { waitUntil: "domcontentloaded" });
  const titleInquiry = page.getByRole("link", { name: "Ask about title" }).first();
  await titleInquiry.waitFor({ state: "visible" });
  const inquiryHref = await titleInquiry.getAttribute("href");
  assert.match(inquiryHref || "", /^\/contact\?interest=[a-z0-9-]+$/);
  await titleInquiry.click();
  await page.waitForURL("**/contact?interest=*");
  await page.waitForFunction(() => document.querySelector('[data-testid="contact-subject"]')?.value.startsWith("Title inquiry: "));
  assert.match(await page.getByTestId("contact-subject").inputValue(), /^Title inquiry: /);
  await page.getByTestId("contact-name").fill("Route Audit Fixture");
  await page.getByTestId("contact-email-input").fill("route-audit@example.invalid");
  await page.getByTestId("contact-message").fill("Local test-only inquiry. Do not send.");
  await page.getByTestId("contact-submit").click();
  await page.getByRole("status").getByText("Thank you. Your message has been received.").waitFor();
  assert(calls.some((call) => call.method === "POST" && call.path === "/api/contact" && call.status === 202));
  results.push({ action: "title inquiry CTA + contact form", result: `${inquiryHref} → POST /api/contact → 202 (local mock)` });

  await page.goto(`${baseUrl}/pricing`, { waitUntil: "domcontentloaded" });
  await page.getByTestId("pricing-pack-local-audit-30").waitFor({ state: "visible" });
  await page.getByTestId("pricing-pack-local-audit-30").click();
  await page.waitForURL("**/account");
  assert(calls.some((call) => call.method === "GET" && call.path === "/api/payments/offers" && call.status === 200));
  assert(calls.some((call) => call.method === "POST" && call.path === "/api/payments/_simulate_topup" && call.status === 201));
  assert(calls.some((call) => call.method === "POST" && call.path === "/api/payments/_simulate_webhook" && call.status === 200));
  results.push({ action: "Reading Pass CTA", result: "local test-mode stub: POST /api/payments/_simulate_topup → 201; POST /api/payments/_simulate_webhook → 200; no external network or real payment" });

  paymentMode = "configured";
  await page.goto(`${baseUrl}/pricing`, { waitUntil: "domcontentloaded" });
  await page.getByTestId("pricing-pack-local-audit-30").waitFor({ state: "visible" });
  await page.getByTestId("pricing-pack-local-audit-30").click();
  await page.waitForURL("**/account");
  assert(calls.some((call) => call.method === "POST" && call.path === "/api/payments/topup" && call.status === 201));
  assert(calls.some((call) => call.method === "POST" && call.path === "/api/payments/verify" && call.status === 200));
  results.push({ action: "configured Reading Pass CTA", result: "local Razorpay stub: POST /api/payments/topup → 201; POST /api/payments/verify → 200; vendor script and external network blocked; no real payment" });

  const allowedPaths = new Set([
    "/api/payments/offers", "/api/users/me", "/api/newsletter", "/api/books",
    "/api/home/curated", "/api/contact", "/api/payments/_simulate_topup", "/api/payments/_simulate_webhook",
    "/api/payments/topup", "/api/payments/verify",
  ]);
  for (const call of calls) assert(allowedPaths.has(call.path), `Unexpected API path ${call.path}`);
  process.stdout.write(`${JSON.stringify({ baseUrl, safety: "Localhost-only Playwright run. All API calls are intercepted and fulfilled with test fixtures; external origins are blocked; no production data or payment is sent.", actions: results, apiCalls: calls }, null, 2)}\n`);
} finally {
  await browser.close();
  await new Promise((resolve) => localServer.close(resolve));
}
