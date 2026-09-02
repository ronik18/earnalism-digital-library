#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const args = Object.fromEntries(process.argv.slice(2).reduce((entries, item, index, values) => item.startsWith("--") ? [...entries, [item.slice(2), values[index + 1]]] : entries, []));
const required = ["production-build", "review-build", "output"];
for (const name of required) assert.ok(args[name], `--${name} is required`);
const root = process.cwd();
const serverPath = path.join(root, "scripts", "serve_frontend_build.js");
const productionBuild = path.resolve(args["production-build"]);
const reviewBuild = path.resolve(args["review-build"]);
const output = path.resolve(args.output);
for (const directory of [productionBuild, reviewBuild]) assert.ok(fs.statSync(directory).isDirectory(), `build directory missing: ${directory}`);

function start(directory, port) {
  const child = spawn(process.execPath, [serverPath, "--directory", directory, "--port", String(port)], { cwd: root, stdio: ["ignore", "ignore", "pipe"] });
  let stderr = "";
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  return { child, stderr: () => stderr, url: `http://127.0.0.1:${port}` };
}
async function waitFor(url, server) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try { const response = await fetch(url); if (response.ok) return; } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`fixture build server did not become reachable: ${url}\n${server.stderr()}`);
}
async function inspect(browser, baseUrl, route) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: "en-US", timezoneId: "UTC", serviceWorkers: "block" });
  const page = await context.newPage();
  const apiRequests = [];
  page.on("request", (request) => { if (new URL(request.url()).pathname.includes("/api/")) apiRequests.push({ url: request.url(), method: request.method() }); });
  await page.route("**/api/**", (request) => request.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => !document.body.innerText.includes("Loading The Earnalism reading room."), undefined, { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(150);
  const result = await page.evaluate(() => {
    const marker = document.querySelector('[data-testid="account-visual-fixture"]');
    const visible = Boolean(marker && getComputedStyle(marker).display !== "none" && marker.getBoundingClientRect().width > 0 && marker.getBoundingClientRect().height > 0);
    return { marker_count: document.querySelectorAll('[data-testid="account-visual-fixture"]').length, marker_visible: visible, sanitized_email_present: Boolean(marker?.textContent?.includes("review@example.invalid")), title: document.title };
  });
  const finalUrl = page.url();
  await context.close();
  return { route, final_url: finalUrl, ...result, production_account_api_called: apiRequests.some(({ url }) => /\/api\/users\/me(?:[/?#]|$)|\/api\/users\/me\/transactions/.test(new URL(url).pathname)), production_authentication_used: apiRequests.some(({ url }) => /\/api\/(?:auth|users)\/(?:me|login|signup)/.test(new URL(url).pathname)), mutation_count: apiRequests.filter(({ method }) => !["GET", "HEAD", "OPTIONS"].includes(method)).length };
}

const production = start(productionBuild, Number(args["production-port"] || 14121));
const review = start(reviewBuild, Number(args["review-port"] || 14122));
let browser;
try {
  await Promise.all([waitFor(`${production.url}/`, production), waitFor(`${review.url}/`, review)]);
  browser = await chromium.launch({ headless: true });
  const productionAccount = await inspect(browser, production.url, "/account?visual-fixture=1");
  const reviewAccount = await inspect(browser, review.url, "/account?visual-fixture=1");
  const reviewNoQuery = await inspect(browser, review.url, "/account");
  const publicRoutes = [];
  for (const route of ["/", "/library", "/pricing"]) publicRoutes.push(await inspect(browser, review.url, route));
  assert.equal(productionAccount.marker_count, 0, "production-contract build exposed Account visual fixture");
  assert.equal(productionAccount.sanitized_email_present, false, "production-contract build exposed sanitized identity");
  assert.equal(new URL(productionAccount.final_url).pathname, "/login", "production-contract build did not retain the anonymous fail-closed Account route");
  assert.equal(reviewAccount.marker_count, 1, "review fixture build did not expose the Account fixture marker");
  assert.equal(reviewAccount.marker_visible, true, "review fixture marker is not visible");
  assert.equal(reviewAccount.sanitized_email_present, true, "review fixture identity is missing");
  assert.equal(reviewAccount.production_authentication_used, false, "review fixture used production authentication");
  assert.equal(reviewAccount.production_account_api_called, false, "review fixture called the production Account API");
  assert.equal(reviewAccount.mutation_count, 0, "review fixture made a mutation request");
  assert.equal(reviewNoQuery.marker_count, 0, "review fixture activates without visual-fixture query");
  for (const record of publicRoutes) assert.equal(record.marker_count, 0, `public route exposed private fixture: ${record.route}`);
  const result = { result: "PASS", label: "DETERMINISTIC_VISUAL_FIXTURE_BUILD_NOT_DEPLOYED", production_contract: productionAccount, review_fixture: reviewAccount, review_no_query: reviewNoQuery, public_routes: publicRoutes };
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify(result));
} finally {
  await browser?.close();
  production.child.kill(); review.child.kill();
}
