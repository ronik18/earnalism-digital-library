import playwright from "../frontend/node_modules/playwright/index.js";
import fs from "node:fs/promises";
import process from "node:process";
import crypto from "node:crypto";

const base = process.env.UAT_BASE_URL;
const api = process.env.UAT_API_BASE_URL;
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base || "") || !/^http:\/\/127\.0\.0\.1:\d+\/api$/.test(api || "")) throw new Error("loopback UAT URLs required");
const slug = process.env.READER_BENCHMARK_SLUG;
if (!slug) throw new Error("fixture slug required");
const { ADMIN_EMAIL: adminEmail, ADMIN_PASSWORD: adminPassword } = process.env;
if (!adminEmail || !adminPassword) throw new Error("isolated admin credentials required");
const out = process.argv[2];
const browser = await playwright.chromium.launch({ headless: true });
const apiRequest = await playwright.request.newContext();
const rows = [];
let loaderCount = 0;
const waitForCanonical = async (page, expected, timeout = 30000) => {
  await page.getByTestId("reader-page-content").waitFor({ timeout }).catch(async () => {
    throw new Error(`reader content missing: ${(await page.locator("body").innerText()).slice(0, 400)}`);
  });
  await page.getByRole("combobox", { name: "Go to page" }).waitFor({ timeout });
  await page.waitForFunction((value) => document.querySelector('select[aria-label="Go to page"]')?.value === String(value), expected, { timeout }).catch(async () => {
    throw new Error(`page ${expected} not reached; current=${await page.locator('select[aria-label="Go to page"]').inputValue().catch(() => "missing")}; body=${(await page.locator("body").innerText()).slice(-500)}`);
  });
};
try {
  for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 900 }]) {
    const page = await browser.newPage({ viewport });
    const identity = `reader-benchmark-${crypto.randomUUID().slice(0, 12)}@example.com`;
    const password = `local-${crypto.randomUUID()}`;
    const post = async (url, body, token) => {
      const response = await apiRequest.post(`${api}${url}`, { data: body, headers: token ? { Authorization: `Bearer ${token}` } : {} });
      return { status: response.status(), body: await response.json() };
    };
    const user = await post("/users/signup", { name: "Reader benchmark", email: identity, password });
    if (user.status !== 200) throw new Error(`isolated signup failed: ${user.status}`);
    const admin = await post("/auth/login", { email: adminEmail, password: adminPassword });
    if (admin.status !== 200) throw new Error(`isolated admin login failed: ${admin.status}`);
    const adjust = await post(`/admin/users/${user.body.user.id}/wallet/adjust`, { minutes: 30, reason: "isolated reader control benchmark" }, admin.body.token);
    if (adjust.status !== 200) throw new Error(`isolated wallet setup failed: ${adjust.status}`);
    const auth = { token: user.body.token };
    await page.addInitScript((token) => localStorage.setItem("earnalism_user_token", token), auth.token);
    await page.goto(`${base}/reader/${slug}?p=1`, { waitUntil: "domcontentloaded", timeout: 30000 });
    await waitForCanonical(page, 1);
    const navigation = page.locator('nav[aria-label="Page navigation"]');
    const next = navigation.getByRole("button").nth(1);
    const prev = navigation.getByRole("button").nth(0);
    const measure = async (name, action, from, to) => { const started = performance.now(); await action(); await waitForCanonical(page, to); rows.push({ viewport, scenario: name, from, to, elapsed_ms: Math.round(performance.now() - started) }); };
    await page.waitForTimeout(150);
    await measure("uncached-next", () => next.click({ force: true }), 1, 2);
    await measure("prefetched-next", () => next.click({ force: true }), 2, 3);
    await measure("cached-previous", () => prev.click({ force: true }), 3, 2);
    await measure("rapid-navigation", () => next.dblclick({ delay: 20, force: true }), 2, 3);
    await page.route("**/reading-pass/books/*/pages/3", async (route) => { await new Promise((resolve) => setTimeout(resolve, 450)); await route.continue(); });
    const retainedBefore = await page.getByTestId("reader-page-content").innerText();
    await prev.click({ force: true });
    await waitForCanonical(page, 2);
    const delayedStarted = performance.now();
    await next.click({ force: true });
    const duringDelay = await page.getByTestId("reader-page-content").innerText();
    if (!duringDelay || !retainedBefore) throw new Error("delayed navigation lost current page shell");
    await waitForCanonical(page, 3);
    rows.push({ viewport, scenario: "delayed-response-retains-current-page", from: 2, to: 3, elapsed_ms: Math.round(performance.now() - delayedStarted), retained_current_page: true });
    if (/Opening Page/i.test(await page.locator("body").innerText())) loaderCount += 1;
    await page.close();
  }
} finally { await apiRequest.dispose(); await browser.close(); }
const timings = rows.map((r) => r.elapsed_ms).sort((a, b) => a - b);
const percentile = (p) => timings[Math.min(timings.length - 1, Math.floor(timings.length * p))];
const scenarios = [...new Set(rows.map((r) => r.scenario))];
if (scenarios.length !== 5 || rows.length !== 10) throw new Error(`incomplete control benchmark: ${rows.length} rows / ${scenarios.join(",")}`);
const report = { schema_version: "earnalism.reader.browser-benchmark.v2", result: "PASS", mode: "local-authenticated-reader-controls", samples: rows.length, scenarios, median_ms: timings[Math.floor(timings.length / 2)], p95_ms: percentile(0.95), fullscreen_loader_occurrences: loaderCount, rows };
await fs.writeFile(out, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({ result: report.result, mode: report.mode, samples: report.samples, scenarios, median_ms: report.median_ms, p95_ms: report.p95_ms, fullscreen_loader_occurrences: loaderCount }));
