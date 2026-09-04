#!/usr/bin/env node
/* Validate base-to-PR service-worker upgrade in one persistent Chromium profile. */
import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { chromium, firefox, webkit } from "playwright";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const baseSha = process.env.P0_BASE_SHA;
const headSha = process.env.P0_HEAD_SHA || execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim();
if (!/^[0-9a-f]{40}$/.test(baseSha || "") || !/^[0-9a-f]{40}$/.test(headSha)) throw new Error("P0_BASE_SHA and P0_HEAD_SHA must be full commit SHAs.");
const port = Number(process.env.P0_FRONTEND_PORT || 13080);
const origin = `http://127.0.0.1:${port}`;
const work = fs.mkdtempSync(path.join(os.tmpdir(), "earnalism-p0-sw-"));
const profile = path.join(work, "persistent-chromium");
const titles = [
  { slug: "dracula", title: "Dracula", author: "Bram Stoker", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, chapters: [{ id: "dracula-page-1", is_preview: true }] },
  { slug: "a-ghost-story", title: "A Ghost Story", author: "Mark Twain", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, chapters: [{ id: "ghost-page-1", is_preview: true }] },
];

function materialize(revision, name) {
  const target = path.join(work, name);
  fs.mkdirSync(target, { recursive: true });
  execFileSync("git", ["archive", revision], { cwd: root, stdio: ["ignore", fs.openSync(path.join(work, `${name}.tar`), "w"), "inherit"] });
  execFileSync("tar", ["-xf", path.join(work, `${name}.tar`), "-C", target]);
  fs.symlinkSync(path.join(root, "node_modules"), path.join(target, "node_modules"), "dir");
  fs.symlinkSync(path.join(root, "frontend", "node_modules"), path.join(target, "frontend", "node_modules"), "dir");
  execFileSync("npm", ["--prefix", "frontend", "run", "build"], { cwd: target, stdio: "inherit", env: { ...process.env, CI: "true", REACT_APP_ENABLE_SERVICE_WORKER: "true", REACT_APP_BACKEND_URL: `${origin}/api` } });
  return target;
}

function serve(target) {
  const child = spawn("node", ["scripts/serve_frontend_build.js", "--directory", "frontend/build", "--port", String(port)], { cwd: target, stdio: "inherit" });
  return child;
}
async function until(check, message) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) { if (await check()) return; await new Promise((resolve) => setTimeout(resolve, 200)); }
  throw new Error(message);
}
async function routeApi(page, requests) {
  await page.route("**/api/**", async (route) => {
    const request = new URL(route.request().url());
    const slug = request.pathname.match(/^\/api\/(?:books|reader\/book)\/([^/]+)/)?.[1];
    const title = titles.find((entry) => entry.slug === decodeURIComponent(slug || ""));
    if (request.pathname.endsWith("/manifest")) {
      requests.push(`manifest:${slug}`);
      return route.fulfill({ status: title ? 200 : 404, contentType: "application/json", body: JSON.stringify(title ? { book: title, chapters: title.chapters, audio: { enabled: false, assets: {} } } : { detail: "Book not found" }) });
    }
    if (/^\/api\/books\/[^/]+$/.test(request.pathname)) {
      requests.push(`book:${slug}`);
      return route.fulfill({ status: title ? 200 : 404, contentType: "application/json", body: JSON.stringify(title || { detail: "Book not found" }) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(request.pathname.endsWith("/books") ? titles : []) });
  });
}
async function assertTitleMatrix(browserType, persistent = false, expectedCachePrefix = "") {
  const requests = [];
  const context = persistent ? await browserType.launchPersistentContext(profile, { headless: true }) : await browserType.launch({ headless: true }).then((browser) => browser.newContext());
  const page = await context.newPage();
  await routeApi(page, requests);
  for (const title of titles) {
    await page.goto(`${origin}/book/${title.slug}`, { waitUntil: "networkidle" });
    await until(async () => await page.locator(".book-detail-page").count() === 1, `Book Detail did not load for ${title.slug}`);
    assert.match(await page.locator(".book-detail-page").innerText(), new RegExp(title.title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    const manifest = await page.evaluate(async (slug) => (await fetch(`/api/reader/book/${slug}/manifest`, { cache: "no-store" })).json(), title.slug);
    assert.equal(manifest.book.slug, title.slug, `manifest identity leaked for ${title.slug}`);
  }
  await page.goto(`${origin}/book/not-available`, { waitUntil: "networkidle" });
  assert.equal(await page.locator(".book-detail-page").count(), 0, "unavailable title must not render a detail page");
  assert(requests.includes("manifest:dracula") && requests.includes("manifest:a-ghost-story"), "both title manifests must reach the origin");
  let caches = [];
  if (persistent) {
    await until(async () => await page.evaluate(() => Boolean(navigator.serviceWorker?.controller)), "service worker did not take control");
    await page.evaluate(async () => { const registration = await navigator.serviceWorker.ready; await registration.update(); });
    if (expectedCachePrefix) await until(async () => (await page.evaluate(() => window.caches.keys())).some((name) => name.startsWith(expectedCachePrefix)), `service worker did not activate ${expectedCachePrefix}`);
    caches = await page.evaluate(() => window.caches.keys());
  }
  await context.close();
  return caches;
}

let server;
try {
  const base = materialize(baseSha, "base");
  server = serve(base);
  await new Promise((resolve) => setTimeout(resolve, 1000));
  const baseCaches = await assertTitleMatrix(chromium, true, "earnalism-v3-reading-pass");
  assert(baseCaches.some((name) => name.startsWith("earnalism-v3-reading-pass")), "base worker cache was not created in the persistent profile");
  const baseCache = fs.readFileSync(path.join(base, "frontend/public/service-worker.js"), "utf8");
  assert.match(baseCache, /earnalism-v3-reading-pass/);
  server.kill("SIGTERM");
  const head = materialize(headSha, "head");
  server = serve(head);
  await new Promise((resolve) => setTimeout(resolve, 1000));
  const headCaches = await assertTitleMatrix(chromium, true, "earnalism-v4-reader-identity");
  assert(headCaches.some((name) => name.startsWith("earnalism-v4-reader-identity")), "PR worker cache was not created in the persistent profile");
  assert(!headCaches.some((name) => name.startsWith("earnalism-v3-reading-pass")), "base worker cache survived the PR worker upgrade");
  const currentCache = fs.readFileSync(path.join(head, "frontend/public/service-worker.js"), "utf8");
  assert.match(currentCache, /earnalism-v4-reader-identity/);
  assert.match(currentCache, /isReaderTextApiRequest/);
  await Promise.all([assertTitleMatrix(firefox), assertTitleMatrix(webkit)]);
  console.log(JSON.stringify({ status: "PASS", base_sha: baseSha, head_sha: headSha, browsers: ["chromium", "firefox", "webkit"], profile: "persistent-chromium", title_fingerprints: titles.map((title) => title.slug) }));
} finally {
  if (server && !server.killed) server.kill("SIGTERM");
  fs.rmSync(work, { recursive: true, force: true });
}
