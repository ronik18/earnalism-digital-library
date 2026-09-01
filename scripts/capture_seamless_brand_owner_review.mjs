#!/usr/bin/env node
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import {
  listStateRecords,
  loadStateManifest,
  selectStateRecords,
  validateStateManifest,
} from "./lib/seamless_brand_state_manifest.mjs";
import {
  requestedScreenshotNames,
  stateOutputDirectory,
  validateUniqueOutputDirectories,
} from "./lib/seamless_brand_one_state_capture.mjs";

const DEFAULT_MANIFEST = "docs/design-system/seamless-brand-state-manifest.json";
const DEFAULT_ROUTE_INVENTORY = "docs/design-system/seamless-brand-route-inventory.json";
const SUPPORTED_BROWSERS = new Set(["chromium", "firefox", "webkit"]);
const REQUIRED_FONT_SPECS = {
  cormorant_garamond: "16px 'Cormorant Garamond'",
  outfit: "16px Outfit",
  noto_serif_bengali: "16px 'Noto Serif Bengali'",
  noto_sans_bengali: "16px 'Noto Sans Bengali'",
};
const SANITIZED_PRIVATE_FIXTURE_SHA256 = crypto.createHash("sha256").update(JSON.stringify({ version: "sanitized-private-v1", identity: "Review Reader", email: "review@example.invalid", saved_library: [] })).digest("hex");
const EDITORIAL_FIXTURE_PATH = "frontend/static-seo/editorial-public.json";
const require = createRequire(import.meta.url);

function statusFixtureResponse(state) {
  const modulePath = state.fixture === "tombstone-410-contract" ? "./frontend/api/removed-content.js" : "./frontend/api/not-found.js";
  const handler = require(path.resolve(modulePath));
  const result = { status: 200, headers: {}, body: "" };
  handler({ query: { path: state.route }, headers: {}, url: state.route }, { set statusCode(value) { result.status = value; }, get statusCode() { return result.status; }, setHeader(key, value) { result.headers[key] = value; }, end(value) { result.body = value; } });
  return result;
}

function editorialFixture() {
  const source = JSON.parse(fs.readFileSync(EDITORIAL_FIXTURE_PATH, "utf8"));
  const article = source.articles.find((item) => item.slug === "how-reading-shapes-better-founders");
  if (!article) throw new Error("Editorial fixture: required public article is absent.");
  const post = { ...article, created_at: article.published_at, content: article.excerpt };
  return { source, post, sha256: digest(EDITORIAL_FIXTURE_PATH) };
}

function staticSnapshotParity(route) {
  const snapshotPath = path.join("frontend", "build", route.replace(/^\//, ""), "index.html");
  if (!fs.existsSync(snapshotPath)) return { snapshot_path: snapshotPath, snapshot_exists: false, static_title: "", static_canonical_url: "", static_robots: "", static_logo_url: "" };
  const html = fs.readFileSync(snapshotPath, "utf8");
  const attribute = (tag, name) => tag.match(new RegExp(`${name}=["']([^"']+)["']`, "i"))?.[1] || "";
  const tags = [...html.matchAll(/<(?:link|meta)[^>]*>/gi)].map((match) => match[0]);
  const canonical = tags.find((tag) => /rel=["']canonical["']/i.test(tag));
  const robots = tags.find((tag) => /name=["']robots["']/i.test(tag));
  return {
    snapshot_path: snapshotPath,
    snapshot_exists: true,
    static_title: html.match(/<title>([^<]*)<\/title>/i)?.[1] || "",
    static_canonical_url: canonical ? attribute(canonical, "href") : "",
    static_robots: robots ? attribute(robots, "content") : "",
    static_logo_url: html.includes("https://theearnalism.com/assets/brand/earnalism-brand-lockup.png") ? "https://theearnalism.com/assets/brand/earnalism-brand-lockup.png" : "",
  };
}

function parseCliArgs(argv) {
  const options = { manifest: DEFAULT_MANIFEST, routeInventory: DEFAULT_ROUTE_INVENTORY, listStates: false, dryRun: false, capture: false, stateFilter: undefined, output: undefined, baseUrl: undefined, browser: undefined };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--manifest" || arg === "--route-inventory" || arg === "--state-filter" || arg === "--output" || arg === "--base-url" || arg === "--browser") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error(`${arg} requires a value.`);
      if (arg === "--manifest") options.manifest = value;
      if (arg === "--route-inventory") options.routeInventory = value;
      if (arg === "--state-filter") options.stateFilter = value.split(",").map((item) => item.trim());
      if (arg === "--output") options.output = value;
      if (arg === "--base-url") options.baseUrl = value;
      if (arg === "--browser") options.browser = value;
      index += 1;
    } else if (arg === "--list-states") {
      options.listStates = true;
    } else if (arg === "--dry-run") {
      options.dryRun = true;
    } else if (arg === "--capture") {
      options.capture = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if ([options.listStates, options.dryRun, options.capture].filter(Boolean).length > 1) throw new Error("Use only one of --list-states, --dry-run, or --capture.");
  if (options.stateFilter && !options.listStates && !options.dryRun && !options.capture) throw new Error("--state-filter requires --list-states, --dry-run, or --capture.");
  if ((options.output || options.baseUrl || options.browser) && !options.capture) throw new Error("--output, --base-url, and --browser require --capture.");
  return options;
}

function digest(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

async function launchRequestedBrowser(name) {
  if (!SUPPORTED_BROWSERS.has(name)) {
    throw new Error(`Unsupported browser ${JSON.stringify(name)}; expected chromium, firefox, or webkit.`);
  }
  const playwright = await import("playwright");
  return playwright[name].launch({ headless: true });
}

function gitReference(...args) {
  return execFileSync("git", args, { cwd: process.cwd(), encoding: "utf8" }).trim();
}

function hashFileSet(paths) {
  const files = [];
  const collect = (entry) => {
    if (!fs.existsSync(entry)) return;
    const stat = fs.statSync(entry);
    if (stat.isDirectory()) {
      for (const child of fs.readdirSync(entry)) collect(path.join(entry, child));
    } else if (!/(^|\/)(__tests__\/|.*\.(test|spec)\.[^/]+$)/.test(entry)) {
      files.push(entry);
    }
  };
  paths.forEach(collect);
  return crypto.createHash("sha256").update(files.sort().map((file) => `${digest(file)}  ${file}\n`).join("")).digest("hex");
}

function routeSurfaceHashes() {
  return {
    home_library_commerce_body: hashFileSet(["frontend/src/components/ReferencePublicPages.jsx", "frontend/src/components/ReferencePublicPages.css", "frontend/src/pages/Library.jsx", "frontend/src/pages/BookDetail.jsx", "frontend/src/pages/BookDetailReference.css"]),
    shared_public_header: hashFileSet(["frontend/src/components/Header.jsx", "frontend/src/components/Header.css", "frontend/src/components/EarnalismBrandLockup.jsx", "frontend/src/components/EarnalismBrandLockup.css"]),
    shared_footer: hashFileSet(["frontend/src/components/Footer.jsx", "frontend/src/components/FooterSocialLinks.jsx"]),
    auth_account: hashFileSet(["frontend/src/components/AuthPageShell.jsx", "frontend/src/pages/Account.jsx", "frontend/src/pages/MyLibrary.jsx", "frontend/src/pages/MyLibrary.css", "frontend/src/context/AuthContext.jsx"]),
    editorial_campaign: hashFileSet(["frontend/src/pages/Journal.jsx", "frontend/src/pages/JournalArticle.jsx", "frontend/src/pages/Contact.jsx", "frontend/src/pages/MicroStoryLanding.jsx", "frontend/src/styles/editorial-support.css"]),
    book_detail: hashFileSet(["frontend/src/pages/BookDetail.jsx", "frontend/src/pages/BookDetailReference.css"]),
    error_surfaces: hashFileSet(["frontend/src/pages/NotFound.jsx", "frontend/api/not-found.js", "frontend/api/removed-content.js", "frontend/api/_lib"]),
    reader: hashFileSet(["frontend/src/experiences-v2/reader", "frontend/src/experiences-v2/shared"]),
    listener: hashFileSet(["frontend/src/experiences-v2/listener", "frontend/src/experiences-v2/shared"]),
    canonical_logo_asset: digest("frontend/public/assets/brand/earnalism-brand-lockup.png"),
  };
}

function runManifestCli(options) {
  const manifestPath = path.resolve(options.manifest);
  const routeInventoryPath = path.resolve(options.routeInventory);
  const manifest = loadStateManifest(manifestPath);
  const routeInventory = JSON.parse(fs.readFileSync(routeInventoryPath, "utf8"));
  validateStateManifest(manifest, routeInventory);
  if (routeInventory.routes.length !== 19) throw new Error(`Route inventory: invalid route count; received ${routeInventory.routes.length}; expected 19.`);
  if (manifest.states.length < 5) throw new Error(`State manifest: invalid state count; received ${manifest.states.length}; expected at least 5.`);
  const requestedIds = options.stateFilter === undefined ? undefined : options.stateFilter;
  const selected = requestedIds === undefined ? listStateRecords(manifest) : selectStateRecords(manifest, requestedIds);
  if (options.listStates) {
    for (const state of selected) {
      console.log(JSON.stringify({ id: state.id, route: state.route, viewport: state.viewport, zoom: state.zoom, fixture: state.fixture, interaction: state.interaction, capture: state.capture }));
    }
    return;
  }
  const captureTypeCounts = {};
  for (const state of selected) {
    for (const [captureType, enabled] of Object.entries(state.capture)) {
      if (enabled) captureTypeCounts[captureType] = (captureTypeCounts[captureType] || 0) + 1;
    }
  }
  console.log(JSON.stringify({
    schema_version: manifest.schema_version,
    total_states: manifest.states.length,
    selected_states: selected.map((state) => state.id),
    unique_routes: [...new Set(selected.map((state) => state.route))],
    fixtures: [...new Set(selected.map((state) => state.fixture))],
    interactions: [...new Set(selected.map((state) => state.interaction))],
    capture_type_counts: captureTypeCounts,
    manifest_sha256: digest(manifestPath),
    route_inventory_sha256: digest(routeInventoryPath),
  }));
}

function loadManifestSelection(options) {
  const manifestPath = path.resolve(options.manifest);
  const routeInventoryPath = path.resolve(options.routeInventory);
  const manifest = loadStateManifest(manifestPath);
  const routeInventory = JSON.parse(fs.readFileSync(routeInventoryPath, "utf8"));
  validateStateManifest(manifest, routeInventory);
  if (routeInventory.routes.length !== 19) throw new Error(`Route inventory: invalid route count; received ${routeInventory.routes.length}; expected 19.`);
  if (manifest.states.length < 5) throw new Error(`State manifest: invalid state count; received ${manifest.states.length}; expected at least 5.`);
  const selected = options.stateFilter === undefined ? listStateRecords(manifest) : selectStateRecords(manifest, options.stateFilter);
  return { manifestPath, routeInventoryPath, manifest, routeInventory, selected };
}

function productionSurfaceHash() {
  const files = [];
  const walk = (directory) => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const file = path.join(directory, entry.name);
      if (entry.isDirectory()) walk(file);
      else if (!/(^|\/)(__tests__\/|.*\.(test|spec)\.[^/]+$)/.test(file)) files.push(file);
    }
  };
  walk("frontend/src");
  walk("frontend/public");
  files.push("frontend/package.json", "frontend/package-lock.json", "frontend/vercel.json");
  const listing = files.sort().map((file) => `${digest(file)}  ${file}\n`).join("");
  return crypto.createHash("sha256").update(listing).digest("hex");
}

function stableHashSet(first, second) {
  return Object.keys(first).length === Object.keys(second).length
    && Object.keys(first).every((key) => first[key].sha256 === second[key].sha256);
}

function canonicalPathname(url) {
  const pathname = new URL(url).pathname;
  return pathname === "/" ? "/" : pathname.replace(/\/+$/, "");
}

async function captureRequestedScreenshots(page, stateDirectory, capture, label, header, lockup) {
  const files = {};
  const attemptDirectory = path.join(stateDirectory, "attempts", label);
  fs.mkdirSync(attemptDirectory, { recursive: true });
  const scrollPosition = await page.evaluate(() => ({ x: window.scrollX, y: window.scrollY }));
  const write = async (name, action) => {
    const target = path.join(attemptDirectory, name);
    await action(target);
    files[name] = { path: target, sha256: digest(target) };
  };
  try {
    if (capture.viewport) await write("viewport.png", async (target) => {
      const clip = await page.evaluate(() => ({ x: window.scrollX, y: window.scrollY, width: window.innerWidth, height: window.innerHeight }));
      await page.screenshot({ path: target, clip, animations: "disabled", caret: "hide", scale: "css" });
    });
    if (capture.full_page) await write("full-page.png", (target) => page.screenshot({ path: target, fullPage: true, animations: "disabled", caret: "hide", scale: "css" }));
    if (capture.brand_close_up) await write("brand-close-up.png", (target) => lockup.screenshot({ path: target, animations: "disabled", caret: "hide", scale: "css" }));
    if (capture.parent_surface_close_up) await write("parent-surface-close-up.png", (target) => header.screenshot({ path: target, animations: "disabled", caret: "hide", scale: "css" }));
  } finally {
    await page.evaluate(({ x, y }) => window.scrollTo(x, y), scrollPosition);
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  }
  return files;
}

async function runOneStateCapture(options) {
  if (!options.output) throw new Error("--capture requires --output.");
  if (!options.baseUrl) throw new Error("--capture requires --base-url.");
  if (!options.browser) throw new Error("--capture requires --browser chromium, firefox, or webkit.");
  if (!SUPPORTED_BROWSERS.has(options.browser)) throw new Error(`Unsupported browser ${JSON.stringify(options.browser)}; expected chromium, firefox, or webkit.`);
  const baseUrl = String(options.baseUrl).replace(/\/$/, "");
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("--base-url must be a loopback http://127.0.0.1:<port> URL.");
  const selection = loadManifestSelection(options);
  if (selection.selected.length !== 1) throw new Error(`--capture requires exactly one selected state; received ${selection.selected.length}.`);
  const state = selection.selected[0];
  const outputDirectory = path.resolve(options.output);
  const stateDirectory = stateOutputDirectory(outputDirectory, state.id);
  const requiredScreenshots = requestedScreenshotNames(state.capture);
  if (!requiredScreenshots.includes("viewport.png")) throw new Error(`State ${state.id} capture declaration must include viewport.`);
  fs.mkdirSync(stateDirectory, { recursive: true });
  if (process.env.SEAMLESS_BRAND_BROWSER_IMPORT_SENTINEL === "1") throw new Error("Browser import sentinel reached during --capture.");
  const browser = await launchRequestedBrowser(options.browser);
  const context = await browser.newContext({ viewport: state.viewport, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", colorScheme: "dark", serviceWorkers: "block" });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push({ url: request.url(), failure: request.failure()?.errorText || "unknown" }));
  await page.route("**/api/**", (route) => {
    const requestUrl = new URL(route.request().url());
    const books = [{ slug: "dracula", title: "Dracula", author: "Bram Stoker", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, chapters: [{ id: "p1", is_preview: true }] }, { slug: "a-ghost-story", title: "A Ghost Story", author: "Mark Twain", publication_status: "LIVE_APPROVED", reader_enabled: true, audiobook_enabled: false, preview_enabled: true, chapters: [{ id: "p1", is_preview: true }] }];
    const body = requestUrl.pathname.endsWith("/books") ? books : requestUrl.pathname.includes("auth") ? { id: "fixture", email: "fixture@invalid.example" } : [];
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.goto(`${baseUrl}${state.route}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.evaluate(async ({ zoom, fontSpecs }) => {
    await document.fonts.ready;
    await Promise.all(Object.values(fontSpecs).map((font) => document.fonts.load(font, "অA").catch(() => [])));
    await Promise.all([...document.images].filter((image) => {
      const style = getComputedStyle(image); const rect = image.getBoundingClientRect();
      return style.display !== "none" && rect.width > 0 && rect.height > 0;
    }).map((image) => image.decode().catch(() => undefined)));
    const style = document.createElement("style");
    style.textContent = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}";
    document.head.append(style);
    document.documentElement.style.zoom = `${zoom}%`;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, { zoom: state.zoom, fontSpecs: REQUIRED_FONT_SPECS });
  await page.emulateMedia({ reducedMotion: "reduce" });
  const header = page.locator('[data-testid="site-header"]:visible');
  if (await header.count() !== 1) throw new Error(`State ${state.id}: expected exactly one visible public header; received ${await header.count()}.`);
  const lockup = header.locator('[data-testid="earnalism-brand-lockup"]:visible');
  if (await lockup.count() !== 1) throw new Error(`State ${state.id}: expected exactly one visible canonical lockup; received ${await lockup.count()}.`);
  let stable = false;
  const stabilityAttempts = [];
  let finalFiles = {};
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const first = await captureRequestedScreenshots(page, stateDirectory, state.capture, `attempt-${attempt}-first`, header, lockup);
    await page.waitForTimeout(500);
    const second = await captureRequestedScreenshots(page, stateDirectory, state.capture, `attempt-${attempt}-second`, header, lockup);
    const matches = stableHashSet(first, second);
    stabilityAttempts.push({ attempt, stable: matches, first: Object.fromEntries(Object.entries(first).map(([name, file]) => [name, file.sha256])), second: Object.fromEntries(Object.entries(second).map(([name, file]) => [name, file.sha256])) });
    if (matches) {
      stable = true;
      for (const [name, file] of Object.entries(second)) {
        const target = path.join(stateDirectory, name);
        fs.copyFileSync(file.path, target);
        finalFiles[name] = { path: name, sha256: digest(target) };
      }
      break;
    }
  }
  const data = await page.evaluate((statusFixture) => {
    const visible = (node) => { if (!node) return false; const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0; };
    const headers = [...document.querySelectorAll('[data-testid="site-header"]')].filter(visible);
    const header = headers[0];
    const lockups = header ? [...header.querySelectorAll('[data-testid="earnalism-brand-lockup"]')].filter(visible) : [];
    const lockup = lockups[0]; const image = lockup?.querySelector("img"); const rect = lockup?.getBoundingClientRect(); const wrapper = lockup && getComputedStyle(lockup); const parent = header && getComputedStyle(header);
    const intersects = (a, b) => Math.max(a.left, b.left) < Math.min(a.right, b.right) && Math.max(a.top, b.top) < Math.min(a.bottom, b.bottom);
    const overlap = Boolean(lockup && [...header.querySelectorAll("a,button")].filter((node) => node !== lockup && !lockup.contains(node) && !node.contains(lockup) && visible(node)).some((node) => intersects(rect, node.getBoundingClientRect())));
    return { document_height: document.documentElement.scrollHeight, scroll_width: document.documentElement.scrollWidth, client_width: document.documentElement.clientWidth, visible_header_count: headers.length, visible_canonical_lockup_count: lockups.length, logo: lockup ? { natural_width: image.naturalWidth, natural_height: image.naturalHeight, rendered_width: rect.width, rendered_height: rect.height, aspect_ratio: rect.width / rect.height, transform: getComputedStyle(image).transform, wrapper_background: wrapper.backgroundColor, wrapper_border_width: wrapper.borderWidth, wrapper_border_radius: wrapper.borderRadius, wrapper_box_shadow: wrapper.boxShadow, wrapper_padding: wrapper.padding, parent_background: parent.backgroundColor, clipped: rect.left < 0 || rect.top < 0 || rect.right > innerWidth || rect.bottom > innerHeight } : null, overlap, horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth };
  });
  const metadata = { state_id: state.id, route: state.route, final_url: page.url(), viewport: state.viewport, zoom: state.zoom, fixture: state.fixture, interaction: state.interaction, browser: options.browser, browser_version: browser.version(), screenshot_paths: Object.fromEntries(Object.entries(finalFiles).map(([name, file]) => [name.replace(".png", "").replaceAll("-", "_"), file.path])), screenshot_sha256: Object.fromEntries(Object.entries(finalFiles).map(([name, file]) => [name.replace(".png", "").replaceAll("-", "_"), file.sha256])), stability_attempts: stabilityAttempts, stable, ...data, console_error_count: consoleErrors.length, page_error_count: pageErrors.length, failed_required_request_count: failedRequests.length };
  fs.writeFileSync(path.join(stateDirectory, "metadata.json"), JSON.stringify(metadata, null, 2) + "\n");
  fs.writeFileSync(path.join(stateDirectory, "console-errors.json"), JSON.stringify(consoleErrors, null, 2) + "\n");
  fs.writeFileSync(path.join(stateDirectory, "page-errors.json"), JSON.stringify(pageErrors, null, 2) + "\n");
  fs.writeFileSync(path.join(stateDirectory, "failed-requests.json"), JSON.stringify(failedRequests, null, 2) + "\n");
  await context.close();
  await browser.close();
  const summary = { manifest_path: selection.manifestPath, manifest_sha256: digest(selection.manifestPath), route_inventory_path: selection.routeInventoryPath, route_inventory_sha256: digest(selection.routeInventoryPath), production_surface_sha256: productionSurfaceHash(), canonical_logo_sha256: digest("frontend/public/assets/brand/earnalism-brand-lockup.png"), requested_state_ids: [state.id], captured_state_ids: [state.id], missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], expected_state_count: 1, captured_state_count: 1, requested_capture_count: requiredScreenshots.length, generated_screenshot_count: Object.keys(finalFiles).length, stable_state_count: stable ? 1 : 0, unstable_state_count: stable ? 0 : 1, browser_version: metadata.browser_version, output_directory: outputDirectory, generated_timestamp: new Date().toISOString() };
  fs.writeFileSync(path.join(outputDirectory, "capture-summary.json"), JSON.stringify(summary, null, 2) + "\n");
  if (!stable) throw new Error(`State ${state.id} is unstable after three bounded capture attempts.`);
  console.log(JSON.stringify({ captured: state.id, output: outputDirectory, stable, summary: path.join(outputDirectory, "capture-summary.json") }));
}

function fixtureUrl(baseUrl, state) {
  const target = new URL(state.route, `${baseUrl}/`);
  if (state.fixture === "reader-visual-safe" || state.fixture === "listener-non-playable" || state.route === "/account") target.searchParams.set("visual-fixture", "1");
  return target.toString();
}

function routeFixture(route) {
  const requestUrl = new URL(route.request().url());
  const books = [{ slug: "dracula", title: "Dracula", author: "Bram Stoker", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, chapters: [{ id: "p1", is_preview: true }] }, { slug: "a-ghost-story", title: "A Ghost Story", author: "Mark Twain", publication_status: "LIVE_APPROVED", reader_enabled: true, audiobook_enabled: false, preview_enabled: true, chapters: [{ id: "p1", is_preview: true }] }, { slug: "devdas", title: "দেবদাস / Devdas", author: "Sarat Chandra Chattopadhyay", language: "bn", publication_status: "LIVE_APPROVED", reader_enabled: true, audiobook_enabled: false, preview_enabled: true, short_description: "A public-safe Bengali reader edition.", chapters: [{ id: "devdas-canonical-page-1", is_preview: true }] }];
  const editorial = editorialFixture();
  const approvedManifest = { book: { slug: "the-art-of-money-getting", title: "The Art of Money Getting", author: "P. T. Barnum", cover_image_url: "" }, audio: { enabled: true, asset_slug: "the-art-of-money-getting", provider: "review-fixture", version: "v1", release_gate: "APPROVED", qa_status: "QA_PASSED", assets: { manifest: "/api/reader/book/the-art-of-money-getting/audiobook/manifest" }, package_version: `sha256-${"a".repeat(64)}` }, access: { reading_pass: { total_pages: 3 } } };
  const body = requestUrl.pathname.endsWith("/books") ? books : requestUrl.pathname.endsWith("/the-art-of-money-getting/manifest") ? approvedManifest : requestUrl.pathname === "/api/blog" ? [editorial.post] : requestUrl.pathname === `/api/blog/${editorial.post.slug}` ? editorial.post : requestUrl.pathname.includes("auth") ? { id: "fixture", email: "fixture@invalid.example" } : [];
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

async function waitFor(page, predicate, arg, message) {
  await page.waitForFunction(predicate, arg, { timeout: 5000 });
  if (!await page.evaluate(predicate, arg)) throw new Error(message);
}

async function ownerScopedMobileMenu(page, state) {
  const header = page.locator('[data-testid="site-header"]:visible');
  const toggle = header.locator('[data-testid="mobile-menu-toggle"]:visible');
  const result = {
    kind: "mobile-menu",
    visible_toggle_count: await toggle.count(),
    owner_header_count: await header.count(),
    hidden_fixture_dialog_count: 0,
    aria_expanded_before: null,
    aria_expanded_after: null,
    active_dialog_count: 0,
    focus_trap: false,
    escape_close: false,
    focus_restoration: false,
    body_scroll_lock: false,
    background_inert: false,
    body_scroll_restored: false,
    background_inert_restored: false,
    route_action_result: "FAIL",
    route_action_destination: null,
    route_action_navigated: false,
    route_action_returned: false,
    route_action_urls: [],
    failures: [],
  };
  if (result.owner_header_count !== 1 || result.visible_toggle_count !== 1) {
    result.failures.push("owner-scoped-mobile-toggle");
    return { result, surface: undefined, finalize: async () => result };
  }
  result.aria_expanded_before = await toggle.getAttribute("aria-expanded");
  const controls = await toggle.getAttribute("aria-controls");
  if (result.aria_expanded_before !== "false" || !controls) result.failures.push("menu-initial-aria-contract");
  await toggle.click();
  await waitFor(page, (id) => { const visible = (node) => { const style = node && getComputedStyle(node); const rect = node?.getBoundingClientRect(); return Boolean(style && rect && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0); }; return [...document.querySelectorAll('[data-testid="mobile-menu-toggle"]')].some((node) => visible(node) && node.getAttribute("aria-expanded") === "true") && [...document.querySelectorAll('[data-testid="mobile-menu"]')].some((node) => node.id === id && visible(node)); }, controls, `State ${state.id}: menu did not open.`);
  const dialog = header.locator(`[data-testid="mobile-menu"]#${controls}[role="dialog"][aria-modal="true"]:visible`);
  result.aria_expanded_after = await toggle.getAttribute("aria-expanded");
  result.active_dialog_count = await dialog.count();
  result.hidden_fixture_dialog_count = await page.locator('[data-testid="mobile-menu"][role="dialog"]').count() - result.active_dialog_count;
  if (result.active_dialog_count !== 1) result.failures.push("owner-scoped-active-dialog");
  if (result.aria_expanded_after !== "true") result.failures.push("menu-open-aria-contract");
  if (result.active_dialog_count !== 1) return { result, surface: dialog, finalize: async () => result };
  result.geometry = await page.evaluate((id) => {
    const box = (node) => { const rect = node?.getBoundingClientRect(); return rect ? { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height } : null; };
    const visible = (node) => { const style = node && getComputedStyle(node); const rect = node?.getBoundingClientRect(); return Boolean(style && rect && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0); };
    const header = [...document.querySelectorAll('[data-testid="site-header"]')].find(visible);
    const toggle = [...(header?.querySelectorAll('[data-testid="mobile-menu-toggle"]') || [])].find(visible);
    const dialog = [...document.querySelectorAll('[data-testid="mobile-menu"]')].find((node) => node.id === id && visible(node));
    const view = window.visualViewport;
    const style = dialog && getComputedStyle(dialog);
    return { viewport: { width: innerWidth, height: innerHeight }, visual_viewport: { width: view?.width ?? innerWidth, height: view?.height ?? innerHeight }, header: box(header), toggle: box(toggle), dialog: box(dialog), dialog_client_height: dialog?.clientHeight ?? 0, dialog_scroll_height: dialog?.scrollHeight ?? 0, computed_position: style?.position ?? "", top: style?.top ?? "", bottom: style?.bottom ?? "", width: style?.width ?? "", height: style?.height ?? "", max_height: style?.maxHeight ?? "", overflow: style?.overflowY ?? "", z_index: style?.zIndex ?? "", body_overflow: document.body.style.overflow, main_inert: document.getElementById("main-content")?.hasAttribute("inert") ?? false, footer_inert: document.querySelector("footer")?.hasAttribute("inert") ?? false, horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth };
  }, controls);
  const geometry = result.geometry;
  const available = geometry.visual_viewport.height - geometry.header.height;
  if (!(geometry.dialog_client_height > 0 && Math.abs(geometry.dialog.top - geometry.header.bottom) <= 2 && Math.abs(geometry.dialog.width - geometry.visual_viewport.width) <= 2 && Math.abs(geometry.dialog.bottom - geometry.visual_viewport.height) <= 3 && geometry.dialog.height >= available * .95 && !geometry.horizontal_overflow)) result.failures.push("menu-geometry");
  result.body_scroll_lock = geometry.body_overflow === "hidden";
  result.background_inert = geometry.main_inert && geometry.footer_inert;
  if (!result.body_scroll_lock) result.failures.push("menu-body-scroll-lock");
  if (!result.background_inert) result.failures.push("menu-background-inert");
  const close = dialog.getByRole("button", { name: "Close menu" });
  await close.focus();
  await page.keyboard.press("Shift+Tab");
  const shiftInside = await page.evaluate((id) => { const dialog = document.getElementById(id); return Boolean(dialog?.contains(document.activeElement)); }, controls);
  await page.keyboard.press("Tab");
  const tabInside = await page.evaluate((id) => { const dialog = document.getElementById(id); return Boolean(dialog?.contains(document.activeElement)); }, controls);
  result.focus_trap = shiftInside && tabInside;
  if (!result.focus_trap) result.failures.push("menu-focus-trap");
  return {
    result,
    surface: dialog,
    finalize: async () => {
      await page.keyboard.press("Escape");
      await page.waitForTimeout(50);
      result.escape_close = await toggle.getAttribute("aria-expanded") === "false" && await header.locator('[data-testid="mobile-menu"]:visible').count() === 0;
      result.focus_restoration = await page.evaluate(() => document.activeElement?.getAttribute("data-testid") === "mobile-menu-toggle");
      const restored = await page.evaluate(() => ({ body_overflow: document.body.style.overflow, main_inert: document.getElementById("main-content")?.hasAttribute("inert") ?? false, footer_inert: document.querySelector("footer")?.hasAttribute("inert") ?? false }));
      result.body_scroll_restored = restored.body_overflow === "";
      result.background_inert_restored = !restored.main_inert && !restored.footer_inert;
      if (!result.escape_close) result.failures.push("menu-escape-close");
      if (!result.focus_restoration) result.failures.push("menu-focus-restoration");
      if (!result.body_scroll_restored) result.failures.push("menu-body-scroll-restore");
      if (!result.background_inert_restored) result.failures.push("menu-background-inert-restore");
      await toggle.click();
      await page.waitForFunction((id) => document.getElementById(id)?.getAttribute("aria-modal") === "true", controls, { timeout: 5000 });
      const destination = state.route === "/library" ? "/pricing" : "/library";
      const routeActionTestId = destination === "/pricing" ? "mobile-nav-reading-passes" : "mobile-nav-library";
      const routeAction = header.locator(`[data-testid="mobile-menu"] [data-testid="${routeActionTestId}"]:visible`);
      result.route_action_destination = destination;
      if (await routeAction.count() !== 1) {
        result.failures.push("menu-route-action");
        return result;
      }
      await routeAction.focus();
      await page.keyboard.press("Enter");
      await page.waitForURL((url) => canonicalPathname(url) === destination, { timeout: 5000 }).catch(() => {});
      await page.waitForFunction(() => [...document.querySelectorAll('[data-testid="mobile-menu"]')].every((node) => { const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display === "none" || rect.width === 0 || rect.height === 0; }), undefined, { timeout: 5000 }).catch(() => {});
      const navigated = canonicalPathname(page.url()) === destination && await page.locator('[data-testid="mobile-menu"]:visible').count() === 0;
      result.route_action_urls.push(page.url());
      await page.goBack({ waitUntil: "domcontentloaded" }).catch(() => {});
      await page.waitForURL((url) => canonicalPathname(url) === state.route, { timeout: 5000 }).catch(() => {});
      await page.waitForFunction(() => [...document.querySelectorAll('[data-testid="mobile-menu"]')].every((node) => { const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display === "none" || rect.width === 0 || rect.height === 0; }), undefined, { timeout: 5000 }).catch(() => {});
      const returned = canonicalPathname(page.url()) === state.route && await page.locator('[data-testid="mobile-menu"]:visible').count() === 0;
      result.route_action_urls.push(page.url());
      result.route_action_navigated = navigated;
      result.route_action_returned = returned;
      result.route_action_result = navigated && returned ? "PASS" : "FAIL";
      if (result.route_action_result !== "PASS") result.failures.push("menu-route-action");
      return result;
    },
  };
}

async function libraryFilterInteraction(page, state) {
  const trigger = page.locator('button.reference-filter-trigger:visible');
  const result = { kind: "library-filters", trigger_count: await trigger.count(), panel_count: 0, aria_expanded_before: null, aria_expanded_after: null, focus_trap: false, close_result: false, focus_restoration: false, body_scroll_lock: false, background_inert: false, body_scroll_restored: false, background_inert_restored: false, apply_filters_reachable: false, url_mutation_count: 0, failures: [] };
  if (result.trigger_count !== 1) { result.failures.push("filters-trigger"); return { result, surface: undefined, finalize: async () => result }; }
  result.aria_expanded_before = await trigger.getAttribute("aria-expanded");
  const initialUrl = page.url();
  await trigger.click();
  const panel = page.locator('.reference-library-drawer[role="dialog"][aria-modal="true"]:visible');
  await panel.waitFor({ state: "visible", timeout: 5000 });
  result.panel_count = await panel.count(); result.aria_expanded_after = await trigger.getAttribute("aria-expanded");
  if (result.panel_count !== 1) result.failures.push("filters-panel-count");
  if (result.aria_expanded_before !== "false" || result.aria_expanded_after !== "true") result.failures.push("filters-aria-contract");
  if (result.panel_count !== 1) return { result, surface: panel, finalize: async () => result };
  result.geometry = await page.evaluate(() => {
    const box = (node) => { const rect = node?.getBoundingClientRect(); return rect ? { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height } : null; };
    const visible = (node) => { const style = node && getComputedStyle(node); const rect = node?.getBoundingClientRect(); return Boolean(style && rect && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0); };
    const trigger = [...document.querySelectorAll('button.reference-filter-trigger')].find(visible); const panel = [...document.querySelectorAll('.reference-library-drawer[role="dialog"][aria-modal="true"]')].find(visible); const content = panel?.firstElementChild; const apply = [...panel?.querySelectorAll("button") || []].find((node) => /apply filters/i.test(node.textContent || "")); const close = panel?.querySelector('button[aria-label="Close filters"]'); const style = panel && getComputedStyle(panel);
    return { viewport: { width: innerWidth, height: innerHeight }, trigger: box(trigger), panel: box(panel), panel_content: box(content), panel_client_height: panel?.clientHeight ?? 0, panel_scroll_height: panel?.scrollHeight ?? 0, content_client_height: content?.clientHeight ?? 0, content_scroll_height: content?.scrollHeight ?? 0, computed_position: style?.position ?? "", width: style?.width ?? "", height: style?.height ?? "", overflow: style?.overflowY ?? "", body_overflow: document.body.style.overflow, header_inert: document.querySelector('[data-testid="site-header"]')?.hasAttribute("inert") ?? false, footer_inert: document.querySelector("footer")?.hasAttribute("inert") ?? false, apply_filters: box(apply), close_action: box(close), horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth };
  });
  const geometry = result.geometry;
  result.apply_filters_reachable = Boolean(geometry.apply_filters && geometry.apply_filters.width > 0 && geometry.apply_filters.bottom <= geometry.viewport.height && geometry.close_action && geometry.close_action.bottom <= geometry.viewport.height);
  if (!(geometry.panel && geometry.panel.width >= geometry.viewport.width - 2 && geometry.panel.height >= geometry.viewport.height - 2 && geometry.panel_client_height > 0 && !geometry.horizontal_overflow)) result.failures.push("filters-geometry");
  result.body_scroll_lock = geometry.body_overflow === "hidden"; result.background_inert = geometry.header_inert && geometry.footer_inert;
  if (!result.body_scroll_lock) result.failures.push("filters-body-scroll-lock"); if (!result.background_inert) result.failures.push("filters-background-inert");
  const close = panel.getByRole("button", { name: "Close filters" }); await close.focus(); await page.keyboard.press("Shift+Tab"); const shiftInside = await page.evaluate(() => Boolean(document.querySelector('.reference-library-drawer')?.contains(document.activeElement))); await page.keyboard.press("Tab"); const tabInside = await page.evaluate(() => Boolean(document.querySelector('.reference-library-drawer')?.contains(document.activeElement))); result.focus_trap = shiftInside && tabInside; if (!result.focus_trap) result.failures.push("filters-focus-trap");
  return { result, surface: panel, finalize: async () => { await panel.locator(":scope > div").evaluate((node) => { node.scrollTop = node.scrollHeight; }); await page.waitForTimeout(50); result.apply_filters_reachable = await page.evaluate(() => { const panel = document.querySelector('.reference-library-drawer'); const apply = [...panel?.querySelectorAll("button") || []].find((node) => /apply filters/i.test(node.textContent || "")); const close = panel?.querySelector('button[aria-label="Close filters"]'); const applyRect = apply?.getBoundingClientRect(); const closeRect = close?.getBoundingClientRect(); return Boolean(applyRect && closeRect && applyRect.width > 0 && applyRect.bottom <= innerHeight && closeRect.bottom <= innerHeight); }); if (!result.apply_filters_reachable) result.failures.push("filters-actions-reachable"); await page.keyboard.press("Escape"); await page.waitForTimeout(50); result.close_result = await panel.count() === 0; result.focus_restoration = await page.evaluate(() => document.activeElement?.classList.contains("reference-filter-trigger")); const restored = await page.evaluate(() => ({ body_overflow: document.body.style.overflow, header_inert: document.querySelector('[data-testid="site-header"]')?.hasAttribute("inert") ?? false, footer_inert: document.querySelector("footer")?.hasAttribute("inert") ?? false })); result.body_scroll_restored = restored.body_overflow === ""; result.background_inert_restored = !restored.header_inert && !restored.footer_inert; result.url_mutation_count = page.url() === initialUrl ? 0 : 1; if (!result.close_result) result.failures.push("filters-close"); if (!result.focus_restoration) result.failures.push("filters-focus-restoration"); if (!result.body_scroll_restored) result.failures.push("filters-body-scroll-restore"); if (!result.background_inert_restored) result.failures.push("filters-background-inert-restore"); if (result.url_mutation_count !== 0) result.failures.push("filters-url-mutation"); return result; } };
}

async function beginInteraction(page, state) {
  if (state.interaction === "open-mobile-menu") return ownerScopedMobileMenu(page, state);
  if (state.interaction === "open-library-filters") return libraryFilterInteraction(page, state);
  if (state.interaction === "scroll-to-footer") return footerScrollInteraction(page, state);
  return { result: undefined, surface: undefined, finalize: async () => undefined };
}

async function footerScrollInteraction(page, state) {
  const footer = page.locator('[data-testid="site-footer"]:visible');
  const brandRow = footer.locator('[data-testid="footer-brand-paper-row"]:visible');
  const lockup = brandRow.locator('[data-testid="earnalism-brand-lockup"]:visible');
  const result = { kind: "scroll-to-footer", footer_count: await footer.count(), footer_brand_row_count: await brandRow.count(), footer_lockup_count: await lockup.count(), footer_in_view: false, navigation_reachable: false, legal_links_reachable: false, geometry: undefined, failures: [] };
  if (result.footer_count !== 1 || result.footer_brand_row_count !== 1 || result.footer_lockup_count !== 1) {
    result.failures.push("footer-brand-surface");
    return { result, capture_surface: brandRow, capture_lockup: lockup, finalize: async () => result };
  }
  await brandRow.evaluate((node) => {
    const stickyHeader = document.querySelector('[data-testid="site-header"]');
    const headerHeight = stickyHeader ? stickyHeader.getBoundingClientRect().height : 0;
    window.scrollTo({ top: Math.max(0, node.getBoundingClientRect().top + window.scrollY - headerHeight), behavior: "instant" });
  });
  await page.waitForTimeout(50);
  result.geometry = await page.evaluate(() => {
    const box = (node) => { const rect = node?.getBoundingClientRect(); return rect ? { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height } : null; };
    const area = (first, second) => !first || !second ? 0 : Math.max(0, Math.min(first.right, second.right) - Math.max(first.left, second.left)) * Math.max(0, Math.min(first.bottom, second.bottom) - Math.max(first.top, second.top));
    const footer = document.querySelector('[data-testid="site-footer"]'); const row = footer?.querySelector('[data-testid="footer-brand-paper-row"]'); const lockup = row?.querySelector('[data-testid="earnalism-brand-lockup"]'); const image = lockup?.querySelector("img"); const navigation = [...(footer?.querySelectorAll("nav a") || [])]; const legal = [...(footer?.querySelectorAll("a") || [])]; const logo = box(lockup); const navBoxes = navigation.map(box).filter(Boolean); const legalBoxes = legal.map(box).filter(Boolean); const wrapper = lockup && getComputedStyle(lockup);
    const clipped = (rect) => Boolean(rect && (rect.left < 0 || rect.right > innerWidth));
    return { viewport: { width: innerWidth, height: innerHeight }, footer: box(footer), brand_row: box(row), logo, navigation: navBoxes, legal_links: legalBoxes, logo_navigation_overlap_area: navBoxes.reduce((sum, item) => sum + area(logo, item), 0), clipped_control_count: [...navBoxes, ...legalBoxes].filter(clipped).length, horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, footer_in_view: Boolean(logo && logo.bottom > 0 && logo.top < innerHeight), navigation_reachable: navBoxes.length > 0 && navBoxes.every((item) => item.width > 0 && item.height > 0 && !clipped(item)), legal_links_reachable: legalBoxes.length > 0 && legalBoxes.every((item) => item.width > 0 && item.height > 0 && !clipped(item)), wrapper: lockup ? { background: wrapper.backgroundColor, border_width: wrapper.borderWidth, border_radius: wrapper.borderRadius, box_shadow: wrapper.boxShadow, padding: wrapper.padding, transform: image ? getComputedStyle(image).transform : "" } : null };
  });
  result.footer_in_view = result.geometry.footer_in_view; result.navigation_reachable = result.geometry.navigation_reachable; result.legal_links_reachable = result.geometry.legal_links_reachable;
  if (!result.footer_in_view || !result.navigation_reachable || !result.legal_links_reachable || result.geometry.logo_navigation_overlap_area !== 0 || result.geometry.clipped_control_count !== 0 || result.geometry.horizontal_overflow || result.geometry.wrapper?.background !== "rgba(0, 0, 0, 0)" || result.geometry.wrapper?.border_width !== "0px" || result.geometry.wrapper?.border_radius !== "0px" || result.geometry.wrapper?.box_shadow !== "none" || result.geometry.wrapper?.padding !== "0px" || result.geometry.wrapper?.transform !== "none") result.failures.push("footer-zoom-contract");
  return { result, capture_surface: brandRow, capture_lockup: lockup, finalize: async () => { await page.evaluate(() => window.scrollTo(0, 0)); return result; } };
}

async function captureManifestState(browser, browserName, state, baseUrl, outputDirectory, contextIndex, routeInventory) {
  const stateDirectory = stateOutputDirectory(outputDirectory, state.id);
  const requiredScreenshots = requestedScreenshotNames(state.capture);
  if (!requiredScreenshots.includes("viewport.png")) throw new Error(`State ${state.id} capture declaration must include viewport.`);
  fs.mkdirSync(stateDirectory, { recursive: true });
  const context = await browser.newContext({ viewport: state.viewport, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", colorScheme: "dark", serviceWorkers: "block" });
  const initialStorage = await context.storageState();
  const page = await context.newPage();
  const statusFixture = state.fixture === "error-404-contract" || state.fixture === "tombstone-410-contract";
  const statusResponse = statusFixture ? statusFixtureResponse(state) : null;
  const routeRecord = routeInventory.routes.find((route) => route.path === state.route)
    || routeInventory.routes.find((route) => route.path === "UNKNOWN_URL" && state.fixture === "error-404-contract");
  const consoleErrors = []; const pageErrors = []; const failedRequests = []; const apiRequests = []; const httpErrorResponses = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push({ url: request.url(), failure: request.failure()?.errorText || "unknown" }));
  page.on("request", (request) => { if (new URL(request.url()).pathname.includes("/api/")) apiRequests.push({ url: request.url(), method: request.method() }); });
  page.on("response", (response) => { if (response.status() >= 400) httpErrorResponses.push({ url: response.url(), status: response.status() }); });
  await page.route("**/api/**", routeFixture);
  if (statusFixture) await page.route((url) => new URL(url).pathname === state.route, (route) => route.fulfill({ status: statusResponse.status, headers: statusResponse.headers, body: statusResponse.body }));
  await page.route("https://theearnalism.com/assets/brand/earnalism-brand-lockup.png", (route) => route.fulfill({ path: "frontend/public/assets/brand/earnalism-brand-lockup.png", contentType: "image/png" }));
  await page.goto(fixtureUrl(baseUrl, state), { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  if (statusFixture) consoleErrors.length = 0;
  await page.evaluate(async ({ zoom, fontSpecs }) => {
    await document.fonts.ready;
    await Promise.all(Object.values(fontSpecs).map((font) => document.fonts.load(font, "অA").catch(() => [])));
    await Promise.all([...document.images].filter((image) => { const style = getComputedStyle(image); const rect = image.getBoundingClientRect(); return style.display !== "none" && rect.width > 0 && rect.height > 0; }).map((image) => image.decode().catch(() => undefined)));
    const style = document.createElement("style"); style.textContent = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}"; document.head.append(style);
    document.documentElement.style.zoom = `${zoom}%`;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, { zoom: state.zoom, fontSpecs: REQUIRED_FONT_SPECS });
  await page.emulateMedia({ reducedMotion: "reduce" });
  const header = page.locator(statusFixture ? 'header[data-testid="status-brand-masthead"]:visible' : 'header[data-testid="site-header"]:visible, header.experience-header:visible');
  const headerCount = await header.count();
  if (headerCount !== 1) throw new Error(`State ${state.id}: expected exactly one visible header; received ${headerCount}.`);
  const lockup = header.locator(statusFixture ? 'img[src*="earnalism-brand-lockup"]:visible' : '[data-testid="earnalism-brand-lockup"]:visible');
  const lockupCount = await lockup.count();
  if (lockupCount !== 1) throw new Error(`State ${state.id}: expected exactly one visible canonical lockup; received ${lockupCount}.`);
  const interactionSession = await beginInteraction(page, state);
  const captureSurface = interactionSession.capture_surface || header;
  const captureLockup = interactionSession.capture_lockup || lockup;
  let stable = false; const stabilityAttempts = []; let finalFiles = {};
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const first = await captureRequestedScreenshots(page, stateDirectory, state.capture, `attempt-${attempt}-first`, captureSurface, captureLockup);
    await page.waitForTimeout(500);
    const second = await captureRequestedScreenshots(page, stateDirectory, state.capture, `attempt-${attempt}-second`, captureSurface, captureLockup);
    const matches = stableHashSet(first, second);
    stabilityAttempts.push({ attempt, stable: matches, first: Object.fromEntries(Object.entries(first).map(([name, file]) => [name, file.sha256])), second: Object.fromEntries(Object.entries(second).map(([name, file]) => [name, file.sha256])) });
    if (matches) { stable = true; for (const [name, file] of Object.entries(second)) { const target = path.join(stateDirectory, name); fs.copyFileSync(file.path, target); finalFiles[name] = { path: name, sha256: digest(target) }; } break; }
  }
  const interactionResult = await interactionSession.finalize();
  const fontResults = await page.evaluate(async (fontSpecs) => {
    await document.fonts.ready;
    return Object.fromEntries(await Promise.all(Object.entries(fontSpecs).map(async ([name, spec]) => {
      await document.fonts.load(spec, "অA").catch(() => []);
      return [name, document.fonts.check(spec, "অA")];
    })));
  }, REQUIRED_FONT_SPECS);
  const data = await page.evaluate((statusFixture) => {
    const visible = (node) => { if (!node) return false; const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0; };
    const headers = statusFixture ? [...document.querySelectorAll('header[data-testid="status-brand-masthead"]')].filter(visible) : [...document.querySelectorAll('header[data-testid="site-header"],header.experience-header')].filter(visible); const header = headers[0];
    const lockups = statusFixture ? [...document.querySelectorAll('img[src*="earnalism-brand-lockup"]')].filter(visible) : (header ? [...header.querySelectorAll('[data-testid="earnalism-brand-lockup"]')].filter(visible) : []); const lockup = lockups[0]; const image = lockup?.matches("img") ? lockup : lockup?.querySelector("img"); const rect = lockup?.getBoundingClientRect(); const wrapper = lockup && getComputedStyle(lockup); const parent = header && getComputedStyle(header);
    const intersects = (a, b) => Math.max(a.left, b.left) < Math.min(a.right, b.right) && Math.max(a.top, b.top) < Math.min(a.bottom, b.bottom);
    const overlap = Boolean(lockup && [...header.querySelectorAll("a,button")].filter((node) => node !== lockup && !lockup.contains(node) && !node.contains(lockup) && visible(node)).some((node) => intersects(rect, node.getBoundingClientRect())));
    const media = [...document.querySelectorAll("audio,source")].map((node) => ({ src: node.getAttribute("src"), autoplay: node.hasAttribute("autoplay"), preload: node.getAttribute("preload") }));
    const requestEntries = performance.getEntriesByType("resource").map((entry) => entry.name);
    const protectedRequest = requestEntries.some((url) => /\/api\/reader\/(book\/.*\/pages|chapter\/.*(4|5|6|7|8|9))/.test(url));
    const balanceRequestCount = requestEntries.filter((url) => /reading-pass|wallet|lease|session/i.test(url)).length;
    const accountFixture = document.querySelector('[data-testid="account-visual-fixture"]');
    const accountText = accountFixture?.textContent || "";
    const accountHasSanitizedEmail = accountText.includes("review@example.invalid");
    const accountAtSignCount = (accountText.match(/@/g) || []).length;
    const myLibraryFixture = document.querySelector('[data-testid="my-library-mobile"]');
    const myLibraryText = myLibraryFixture?.textContent || "";
    const privateFixtureVisible = Boolean(accountFixture || myLibraryFixture);
    const sensitivePrivateFixtureValues = accountFixture
      ? !accountHasSanitizedEmail || accountAtSignCount !== 1
      : myLibraryFixture
        ? /@|\b(?:account id|transaction id|device id)\b/i.test(myLibraryText)
        : false;
    const myLibraryEmptyStateVisible = Boolean(myLibraryFixture && [...myLibraryFixture.querySelectorAll("h1,h2,p")].some((node) => /Your shelf is ready\.|Saved editions will appear here/.test(node.textContent || "")));
    const menuReachable = [...document.querySelectorAll('[data-testid="mobile-menu-toggle"],button[aria-label*="menu" i]')].some(visible);
    const searchReachable = [...document.querySelectorAll('[data-testid="nav-search"],button[aria-label*="search" i],a[aria-label*="search" i]')].some(visible);
    const actionRow = document.querySelector(".reader-v2__mobile-topbar,.listener-v2__mobile-top"); const actionRect = actionRow?.getBoundingClientRect(); const headerRect = header?.getBoundingClientRect();
    const text = document.body.textContent || "";
    const journalCards = [...document.querySelectorAll('[data-testid^="journal-card-"],a[href="/journal/how-reading-shapes-better-founders"]')].filter(visible);
    return { document_height: document.documentElement.scrollHeight, scroll_width: document.documentElement.scrollWidth, client_width: document.documentElement.clientWidth, visible_header_count: headers.length, visible_canonical_lockup_count: lockups.length, logo: lockup ? { natural_width: image.naturalWidth, natural_height: image.naturalHeight, rendered_width: rect.width, rendered_height: rect.height, aspect_ratio: rect.width / rect.height, transform: getComputedStyle(image).transform, wrapper_background: wrapper.backgroundColor, wrapper_border_width: wrapper.borderWidth, wrapper_border_radius: wrapper.borderRadius, wrapper_box_shadow: wrapper.boxShadow, wrapper_padding: wrapper.padding, parent_background: parent.backgroundColor, clipped: rect.left < 0 || rect.top < 0 || rect.right > innerWidth || rect.bottom > innerHeight } : null, overlap, horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, menu_reachable: menuReachable, search_reachable: searchReachable, reader: { protected_content_exposed: Boolean(document.querySelector('[data-testid="reader-protected-content"],[data-testid="protected-reader-content"]')) || protectedRequest, protected_prefetch: protectedRequest, balance_consumption: balanceRequestCount }, listener: { raw_media_url: media.some((item) => item.src) ? "present" : "absent", playable_source: media.some((item) => item.src) ? "present" : "absent", autoplay: media.some((item) => item.autoplay), preload: media.some((item) => item.preload) ? "present" : "absent", balance_consumption: balanceRequestCount, cover_visible: [...document.querySelectorAll(".listener-v2 img")].some(visible) }, account: { visual_fixture_present: Boolean(accountFixture), sensitive_fixture_values_present: Boolean(accountFixture && sensitivePrivateFixtureValues) }, private_fixture: { fixture_visible: privateFixtureVisible, sensitive_fixture_values_present: sensitivePrivateFixtureValues, my_library_empty_state_visible: myLibraryEmptyStateVisible }, action_row_below_brand: !actionRect || !headerRect || actionRect.top >= headerRect.bottom, editorial: { hydrated_title: document.title, hydrated_canonical_logo_source: image?.getAttribute("src") || "", journal_article_link_count: journalCards.length, selected_article_route_present: journalCards.some((node) => node.getAttribute("href") === "/journal/how-reading-shapes-better-founders"), article_title_present: Boolean(document.querySelector('[data-testid="journal-article"] h1')) && !text.includes("Article not found"), generic_home_fallback_absent: !text.includes("Welcome to The Earnalism"), contact_form_labels_present: document.querySelectorAll('[data-testid="contact-form"] label').length >= 4, contact_submit_visible: visible(document.querySelector('[data-testid="contact-submit"]')), micro_story_campaign_state: visible(document.querySelector(".micro-story-hero")) && visible(document.querySelector(".micro-story-hero__cta")) ? "ACTIVE_CAMPAIGN" : "INACTIVE", micro_story_primary_cta_present: visible(document.querySelector(".micro-story-hero__cta")), micro_story_product_truth_result: text.includes("No auto-renewal") && text.includes("Reading Pass") ? "PASS" : "FAIL" } };
  }, statusFixture);
  const zoomResults = await page.evaluate((requestedZoom) => {
    const visible = (node) => { if (!node) return false; const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0; };
    const box = (node) => { const rect = node?.getBoundingClientRect(); return rect ? { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height } : null; };
    const area = (first, second) => { if (!first || !second) return 0; return Math.max(0, Math.min(first.right, second.right) - Math.max(first.left, second.left)) * Math.max(0, Math.min(first.bottom, second.bottom) - Math.max(first.top, second.top)); };
    const header = [...document.querySelectorAll('[data-testid="site-header"],header.experience-header')].find(visible);
    const lockup = header && [...header.querySelectorAll('[data-testid="earnalism-brand-lockup"]')].find(visible);
    const logo = box(lockup);
    const menu = [...document.querySelectorAll('[data-testid="mobile-menu-toggle"]')].find(visible);
    const search = [...document.querySelectorAll('[data-testid="mobile-header-search"],[data-testid="nav-search"]')].find(visible);
    const main = document.getElementById("main-content");
    const primary = [...(main?.querySelectorAll("a[href],button") || [])].find((node) => visible(node) && !node.closest("header"));
    const headerControls = [...(header?.querySelectorAll("a[href],button") || [])].filter((node) => visible(node) && !lockup?.contains(node) && !node.contains(lockup));
    const viewportControls = [...document.querySelectorAll("a[href],button,input,select")].filter((node) => { const rect = node.getBoundingClientRect(); return visible(node) && rect.bottom > 0 && rect.top < innerHeight && rect.right > 0 && rect.left < innerWidth; });
    const controlBoxes = { menu: box(menu), search: box(search), primary_cta: box(primary) };
    const clippedArea = (rect) => !rect ? 0 : Math.max(0, rect.width * rect.height - Math.max(0, Math.min(rect.right, innerWidth) - Math.max(rect.left, 0)) * Math.max(0, Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0)));
    const controlInfo = (node) => { const rect = box(node); const style = node && getComputedStyle(node); return { box: rect, flex_basis: style?.flexBasis ?? "", flex_grow: style?.flexGrow ?? "", flex_shrink: style?.flexShrink ?? "", min_inline_size: style?.minInlineSize ?? "", max_inline_size: style?.maxInlineSize ?? "", clipped_area: clippedArea(rect), viewport_intersection: Boolean(rect && rect.right > 0 && rect.left < innerWidth && rect.bottom > 0 && rect.top < innerHeight) }; };
    const readerTopbar = document.querySelector(".reader-v2__mobile-topbar"); const readerTopbarStyle = readerTopbar && getComputedStyle(readerTopbar); const readerTopbarBox = box(readerTopbar); const readerBack = readerTopbar?.querySelector('button[aria-label="Back to book"]'); const readerStatus = readerTopbar?.querySelector(":scope > span"); const readerCluster = readerTopbar?.querySelector(":scope > div"); const readerDecrease = readerCluster?.querySelector('button[aria-label="Decrease text size"]'); const readerIncrease = readerCluster?.querySelector('button[aria-label="Increase text size"]'); const readerSettings = readerCluster?.querySelector('button[aria-label="Reader settings"]'); const readerChildren = [readerBack, readerStatus, readerCluster].filter(Boolean).map(controlInfo); const readerGap = Number.parseFloat(readerTopbarStyle?.columnGap || readerTopbarStyle?.gap || "0") || 0; const readerPadding = (Number.parseFloat(readerTopbarStyle?.paddingInlineStart || "0") || 0) + (Number.parseFloat(readerTopbarStyle?.paddingInlineEnd || "0") || 0); const readerCanvas = document.querySelector(".reader-v2__canvas");
    // A normal document may extend below the viewport at high zoom. Treat only
    // horizontal visual-boundary loss as clipping here; vertical reachability is
    // recorded separately and may use ordinary page scrolling.
    const clippedControls = viewportControls.filter((node) => { const rect = node.getBoundingClientRect(); return rect.left < 0 || rect.right > innerWidth; });
    const zoomValue = document.documentElement.style.zoom || getComputedStyle(document.documentElement).zoom || "100%";
    const numericZoom = Number.parseFloat(zoomValue);
    const effectiveZoomPercent = zoomValue.includes("%") ? numericZoom : numericZoom * 100;
    const visual = window.visualViewport;
    return {
      requested_zoom_percent: requestedZoom,
      effective_zoom_percent: effectiveZoomPercent,
      zoom_method: "document.documentElement.style.zoom",
      layout_viewport: { width: document.documentElement.clientWidth, height: document.documentElement.clientHeight },
      visual_viewport: { width: visual?.width ?? innerWidth, height: visual?.height ?? innerHeight },
      window_inner: { width: innerWidth, height: innerHeight },
      device_pixel_ratio: devicePixelRatio,
      controls: controlBoxes,
      reader_topbar: readerTopbar ? { box: readerTopbarBox, client_width: readerTopbar.clientWidth, scroll_width: readerTopbar.scrollWidth, display: readerTopbarStyle.display, flex_direction: readerTopbarStyle.flexDirection, flex_wrap: readerTopbarStyle.flexWrap, justify_content: readerTopbarStyle.justifyContent, align_items: readerTopbarStyle.alignItems, gap: readerTopbarStyle.gap, padding: readerTopbarStyle.padding, overflow: readerTopbarStyle.overflow, available_topbar_inline_size: readerTopbar.clientWidth, required_single_row_inline_size: readerChildren.reduce((sum, item) => sum + item.box.width, 0) + Math.max(0, readerChildren.length - 1) * readerGap + readerPadding, children: { back: controlInfo(readerBack), canonical_page_status: controlInfo(readerStatus), control_cluster: controlInfo(readerCluster), decrease: controlInfo(readerDecrease), increase: controlInfo(readerIncrease), settings: controlInfo(readerSettings) }, content_begins_below_topbar: !readerCanvas || readerCanvas.getBoundingClientRect().top >= readerTopbar.getBoundingClientRect().bottom, action_row_content_overlap_area: area(readerTopbarBox, box(readerCanvas)) } : null,
      minimum_visible_control_size: viewportControls.length ? { width: Math.min(...viewportControls.map((node) => node.getBoundingClientRect().width)), height: Math.min(...viewportControls.map((node) => node.getBoundingClientRect().height)) } : null,
      logo_control_overlap_area: headerControls.reduce((sum, node) => sum + area(logo, box(node)), 0),
      clipped_control_count: clippedControls.length,
      search_supported_location: search ? "masthead" : "current-supported-location-not-visible",
      first_content: box(main?.querySelector(".reference-home__hero,.account-page,.my-library-page,[data-testid='account-visual-fixture'],[data-testid='my-library-mobile']")),
      masthead_row_count: header ? 1 : 0,
      content_begins_below_masthead: !header || !main?.querySelector(".reference-home__hero,.account-page,.my-library-page,[data-testid='account-visual-fixture'],[data-testid='my-library-mobile']") || main.querySelector(".reference-home__hero,.account-page,.my-library-page,[data-testid='account-visual-fixture'],[data-testid='my-library-mobile']").getBoundingClientRect().top >= header.getBoundingClientRect().bottom,
      logo_regions: { non_clipping_visibility: Boolean(logo && logo.left >= 0 && logo.top >= 0 && logo.right <= innerWidth && logo.bottom <= innerHeight), detailed_optical_metrics: "DEFERRED_TO_FINAL_ARTIFACT" },
    };
  }, state.zoom);
  zoomResults.screenshot_dimensions = Object.fromEntries(Object.entries(finalFiles).map(([name, file]) => {
    const bytes = fs.readFileSync(path.join(stateDirectory, file.path));
    return [name, bytes.subarray(0, 8).equals(Buffer.from("89504e470d0a1a0a", "hex")) ? { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) } : null];
  }));
  const balanceMutationCount = apiRequests.filter(({ url, method }) => !["GET", "HEAD", "OPTIONS"].includes(method) && /reading-pass|wallet|lease|session/i.test(url)).length;
  const statusLogoCard = statusFixture && await page.evaluate(() => {
    const logo = document.querySelector('img[src*="earnalism-brand-lockup"]');
    let node = logo?.parentElement;
    while (node && node !== document.body) {
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      const logoRect = logo.getBoundingClientRect();
      const tightlyWrapsLogo = rect.width < innerWidth * 0.95 && rect.width <= logoRect.width + 160;
      const hasCardTreatment = style.borderTopWidth !== "0px" || style.borderRadius !== "0px" || style.boxShadow !== "none";
      if (tightlyWrapsLogo && hasCardTreatment) return true;
      node = node.parentElement;
    }
    return false;
  });
  const contactApiCallCount = apiRequests.filter(({ url }) => /\/api\/contact(?:[/?]|$)/.test(new URL(url).pathname)).length;
  const classifiedHttpErrors = httpErrorResponses.filter(({ url, status }) => statusFixture && canonicalPathname(url) === state.route && status === statusResponse.status);
  const unclassifiedHttpErrors = httpErrorResponses.filter((entry) => !classifiedHttpErrors.includes(entry));
  data.reader.balance_consumption = balanceMutationCount;
  data.listener.balance_consumption = balanceMutationCount;
  data.editorial.contact_submission_count = contactApiCallCount;
  data.editorial.production_contact_api_calls = contactApiCallCount;
  const statusHeaders = Object.fromEntries(Object.entries(statusResponse?.headers || {}).map(([key, value]) => [key.toLowerCase(), String(value)]));
  const statusContract = statusFixture ? {
    expected_status: state.fixture === "error-404-contract" ? 404 : 410,
    handler_status: statusResponse.status,
    content_type: statusHeaders["content-type"] || "",
    x_robots_tag: statusHeaders["x-robots-tag"] || "",
    cache_control: statusHeaders["cache-control"] || "",
    result: statusResponse.status === (state.fixture === "error-404-contract" ? 404 : 410)
      && /text\/html;\s*charset=utf-8/i.test(statusHeaders["content-type"] || "")
      && /noindex/i.test(statusHeaders["x-robots-tag"] || "")
      && Boolean(statusHeaders["cache-control"])
      ? "PASS" : "FAIL",
  } : undefined;
  const defects = [];
  if (data.visible_header_count !== 1 || data.visible_canonical_lockup_count !== 1 || data.logo?.clipped || data.overlap || data.horizontal_overflow || consoleErrors.length || pageErrors.length || failedRequests.length) defects.push("brand-shell-contract");
  if (state.fixture === "public-safe" && state.zoom === 200 && (!data.menu_reachable || !data.search_reachable)) defects.push("home-mobile-controls");
  if (state.fixture === "reader-visual-safe" && ((state.viewport.width < 768 && !data.action_row_below_brand) || data.reader.protected_content_exposed || data.reader.protected_prefetch || data.reader.balance_consumption !== 0)) defects.push("reader-fixture-contract");
  if (state.fixture === "listener-non-playable" && ((state.viewport.width < 768 && !data.action_row_below_brand) || !data.listener.cover_visible || data.listener.raw_media_url !== "absent" || data.listener.playable_source !== "absent" || data.listener.autoplay || data.listener.preload !== "absent" || data.listener.balance_consumption !== 0)) defects.push("listener-fixture-contract");
  if (statusLogoCard) defects.push("legacy-error-logo-card");
  if (statusContract && statusContract.result !== "PASS") defects.push("status-contract");
  if (!Object.values(fontResults).every(Boolean)) defects.push("required-font-load");
  if (unclassifiedHttpErrors.length) defects.push("unclassified-http-error");
  const privateFixture = state.fixture === "sanitized-account";
  const productionAuthenticationUsed = privateFixture && (initialStorage.cookies.length !== 0 || initialStorage.origins.length !== 0 || apiRequests.some(({ url }) => !url.startsWith(baseUrl)));
  const productionAccountApiCalled = privateFixture && apiRequests.some(({ url }) => !url.startsWith(baseUrl));
  const mutationCount = apiRequests.filter(({ method }) => !["GET", "HEAD", "OPTIONS"].includes(method)).length;
  if (privateFixture && (!data.private_fixture.fixture_visible || data.private_fixture.sensitive_fixture_values_present || productionAuthenticationUsed || productionAccountApiCalled || mutationCount !== 0)) defects.push("sanitized-private-fixture-contract");
  const editorialCampaignState = state.introduced_in === "editorial-campaign-2b3";
  const staticSnapshot = editorialCampaignState ? staticSnapshotParity(state.route) : undefined;
  if (editorialCampaignState && (!staticSnapshot.snapshot_exists || staticSnapshot.static_logo_url !== "https://theearnalism.com/assets/brand/earnalism-brand-lockup.png" || !data.editorial.generic_home_fallback_absent)) defects.push("editorial-static-parity-contract");
  if (state.id.startsWith("journal-") && (!data.editorial.journal_article_link_count || !data.editorial.selected_article_route_present)) defects.push("journal-fixture-contract");
  if (state.id.startsWith("article-") && !data.editorial.article_title_present) defects.push("article-fixture-contract");
  if (state.id.startsWith("contact-") && (!data.editorial.contact_form_labels_present || !data.editorial.contact_submit_visible || mutationCount !== 0)) defects.push("contact-contract");
  if (state.id.startsWith("micro-story-") && (data.editorial.micro_story_campaign_state !== "ACTIVE_CAMPAIGN" || !data.editorial.micro_story_primary_cta_present || data.editorial.micro_story_product_truth_result !== "PASS" || mutationCount !== 0)) defects.push("micro-story-contract");
  if (state.introduced_in === "core-zoom-2c2a" && (Math.abs(zoomResults.requested_zoom_percent - zoomResults.effective_zoom_percent) > 0.01 || zoomResults.logo_control_overlap_area !== 0 || zoomResults.clipped_control_count !== 0)) defects.push("core-zoom-geometry-contract");
  if (state.introduced_in === "core-zoom-2c2a" && state.route === "/" && (!data.menu_reachable || !data.search_reachable || !zoomResults.content_begins_below_masthead)) defects.push("core-home-zoom-contract");
  if (state.introduced_in === "experience-footer-zoom-2c2b" && (Math.abs(zoomResults.requested_zoom_percent - zoomResults.effective_zoom_percent) > 0.01 || zoomResults.logo_control_overlap_area !== 0 || zoomResults.clipped_control_count !== 0)) defects.push("experience-footer-zoom-geometry-contract");
  if (interactionResult?.failures?.length) defects.push(...interactionResult.failures);
  const safetyResults = { reader: { ...data.reader, production_reader_api_called: false }, listener: { ...data.listener, production_listener_api_called: false }, production_api_call_count: 0, production_mutation_count: mutationCount, footer: interactionResult?.kind === "scroll-to-footer" ? interactionResult.geometry : undefined };
  const metadata = { source_head: gitReference("rev-parse", "HEAD"), tree_sha: gitReference("rev-parse", "HEAD^{tree}"), state_id: state.id, route: state.route, route_classification: routeRecord?.classification || "CONTROLLED_APPROVED_LISTENER", initial_url: fixtureUrl(baseUrl, state), final_url: page.url(), viewport: state.viewport, zoom: state.zoom, zoom_method: "document.documentElement.style.zoom", fixture: state.fixture, interaction: state.interaction, browser: browserName, browser_version: browser.version(), context_id: `context-${contextIndex}`, initial_storage: { cookies: initialStorage.cookies.length, origins: initialStorage.origins.length }, screenshot_paths: Object.fromEntries(Object.entries(finalFiles).map(([name, file]) => [name.replace(".png", "").replaceAll("-", "_"), file.path])), screenshot_sha256: Object.fromEntries(Object.entries(finalFiles).map(([name, file]) => [name.replace(".png", "").replaceAll("-", "_"), file.sha256])), stability_attempts: stabilityAttempts, stable, ...data, font_results: fontResults, http_error_responses: httpErrorResponses, unclassified_http_error_responses: unclassifiedHttpErrors, zoom_results: zoomResults, interaction_result: interactionResult, private_fixture: privateFixture ? { ...data.private_fixture, fixture_sha256: SANITIZED_PRIVATE_FIXTURE_SHA256, production_authentication_used: productionAuthenticationUsed, production_account_api_called: productionAccountApiCalled, mutation_count: mutationCount } : undefined, static_snapshot: staticSnapshot, status_contract: statusContract, production_mutation_count: mutationCount, production_api_call_count: 0, intercepted_api_request_count: apiRequests.length, console_error_count: consoleErrors.length, page_error_count: pageErrors.length, failed_required_request_count: failedRequests.length, rendered_ui_result: defects.length ? "RENDERED_UI_DEFECT_FOUND" : "PASS", rendered_ui_defects: defects };
  fs.writeFileSync(path.join(stateDirectory, "metadata.json"), JSON.stringify(metadata, null, 2) + "\n"); fs.writeFileSync(path.join(stateDirectory, "console-errors.json"), JSON.stringify(consoleErrors, null, 2) + "\n"); fs.writeFileSync(path.join(stateDirectory, "page-errors.json"), JSON.stringify(pageErrors, null, 2) + "\n"); fs.writeFileSync(path.join(stateDirectory, "failed-requests.json"), JSON.stringify(failedRequests, null, 2) + "\n");
  if (interactionResult) { fs.writeFileSync(path.join(stateDirectory, "interaction-results.json"), JSON.stringify(interactionResult, null, 2) + "\n"); fs.writeFileSync(path.join(stateDirectory, "geometry-results.json"), JSON.stringify(interactionResult.geometry || {}, null, 2) + "\n"); }
  fs.writeFileSync(path.join(stateDirectory, "zoom-results.json"), JSON.stringify(zoomResults, null, 2) + "\n");
  fs.writeFileSync(path.join(stateDirectory, "safety-results.json"), JSON.stringify(safetyResults, null, 2) + "\n");
  if (statusContract) fs.writeFileSync(path.join(stateDirectory, "status-contract-results.json"), JSON.stringify(statusContract, null, 2) + "\n");
  await context.close();
  if (!stable) throw new Error(`State ${state.id} is unstable after three bounded capture attempts.`);
  return { metadata, screenshotCount: Object.keys(finalFiles).length };
}

async function runManifestCapture(options) {
  if (!options.output) throw new Error("--capture requires --output."); if (!options.baseUrl) throw new Error("--capture requires --base-url."); if (!options.browser) throw new Error("--capture requires --browser chromium, firefox, or webkit."); if (!SUPPORTED_BROWSERS.has(options.browser)) throw new Error(`Unsupported browser ${JSON.stringify(options.browser)}; expected chromium, firefox, or webkit.`);
  const baseUrl = String(options.baseUrl).replace(/\/$/, ""); if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("--base-url must be a loopback http://127.0.0.1:<port> URL.");
  const selection = loadManifestSelection(options); if (!selection.selected.length) throw new Error("--capture requires at least one selected state.");
  const outputDirectory = path.resolve(options.output); validateUniqueOutputDirectories(outputDirectory, selection.selected); fs.mkdirSync(outputDirectory, { recursive: true });
  if (process.env.SEAMLESS_BRAND_BROWSER_IMPORT_SENTINEL === "1") throw new Error("Browser import sentinel reached during --capture.");
  const browser = await launchRequestedBrowser(options.browser); const captured = [];
  try { for (let index = 0; index < selection.selected.length; index += 1) captured.push(await captureManifestState(browser, options.browser, selection.selected[index], baseUrl, outputDirectory, index + 1, selection.routeInventory)); } finally { await browser.close(); }
  const stableCount = captured.filter((record) => record.metadata.stable).length;
  const coreZoomRun = selection.selected.some((state) => state.introduced_in === "core-zoom-2c2a");
  const reusedStateIds = coreZoomRun ? selection.selected.filter((state) => state.introduced_in !== "core-zoom-2c2a").map((state) => state.id) : selection.selected.filter((state) => Array.isArray(state.reuse_in) && state.reuse_in.length > 0).map((state) => state.id);
  const newlyAddedStateIds = selection.selected.filter((state) => coreZoomRun ? state.introduced_in === "core-zoom-2c2a" : typeof state.introduced_in === "string" && state.introduced_in.length > 0).map((state) => state.id);
  const sensitiveDataDefectStates = captured.filter((record) => record.metadata.private_fixture?.sensitive_fixture_values_present).map((record) => record.metadata.state_id);
  const interactionRecords = captured.filter((record) => record.metadata.interaction_result);
  const zoomRecords = captured.filter((record) => record.metadata.zoom_results);
  const zoomCount = (percent) => zoomRecords.filter((record) => record.metadata.zoom_results.requested_zoom_percent === percent).length;
  const routeHashes = routeSurfaceHashes();
  const countBy = (values) => Object.fromEntries([...values].sort().map((value) => [value, values.filter((item) => item === value).length]));
  const logoCardStates = captured.filter((record) => record.metadata.rendered_ui_defects.includes("legacy-error-logo-card") || record.metadata.logo?.wrapper_border_width !== "0px" || record.metadata.logo?.wrapper_border_radius !== "0px" || record.metadata.logo?.wrapper_box_shadow !== "none").map((record) => record.metadata.state_id);
  const summary = { source_head: gitReference("rev-parse", "HEAD"), tree_sha: gitReference("rev-parse", "HEAD^{tree}"), manifest_path: selection.manifestPath, manifest_sha256: digest(selection.manifestPath), route_inventory_path: selection.routeInventoryPath, route_inventory_sha256: digest(selection.routeInventoryPath), production_surface_sha256: productionSurfaceHash(), route_surface_hashes: routeHashes, canonical_logo_sha256: digest("frontend/public/assets/brand/earnalism-brand-lockup.png"), article_route: "/journal/how-reading-shapes-better-founders", article_fixture_source: EDITORIAL_FIXTURE_PATH, article_fixture_sha256: editorialFixture().sha256, requested_state_ids: selection.selected.map((state) => state.id), reused_state_ids: reusedStateIds, newly_added_state_ids: newlyAddedStateIds, captured_state_ids: captured.map((record) => record.metadata.state_id), manifest_order_execution_list: selection.selected.map((state) => state.id), missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], expected_state_count: selection.selected.length, captured_state_count: captured.length, generated_screenshot_count: captured.reduce((sum, record) => sum + record.screenshotCount, 0), stable_state_count: stableCount, unstable_state_count: captured.length - stableCount, capture_type_counts: Object.fromEntries(["viewport", "full_page", "brand_close_up", "parent_surface_close_up"].map((type) => [type, selection.selected.filter((state) => state.capture[type]).length])), route_family_counts: countBy(captured.map((record) => record.metadata.route_classification)), fixture_counts: countBy(captured.map((record) => record.metadata.fixture)), interaction_counts: countBy(captured.map((record) => record.metadata.interaction)), zoom_100_state_count: zoomCount(100), zoom_150_state_count: zoomCount(150), zoom_200_state_count: zoomCount(200), reader_state_count: captured.filter((record) => record.metadata.fixture === "reader-visual-safe").length, listener_state_count: captured.filter((record) => record.metadata.fixture === "listener-non-playable").length, footer_state_count: captured.filter((record) => record.metadata.interaction === "scroll-to-footer").length, active_logo_placement_count: captured.reduce((sum, record) => sum + record.metadata.visible_canonical_lockup_count, 0), raw_duplicate_logo_states: captured.filter((record) => record.metadata.visible_canonical_lockup_count !== 1).map((record) => record.metadata.state_id), transform_logo_states: captured.filter((record) => record.metadata.logo?.transform !== "none").map((record) => record.metadata.state_id), logo_card_states: logoCardStates, clipped_logo_states: captured.filter((record) => record.metadata.logo?.clipped).map((record) => record.metadata.state_id), multiple_header_states: captured.filter((record) => record.metadata.visible_header_count !== 1).map((record) => record.metadata.state_id), horizontal_overflow_states: captured.filter((record) => record.metadata.horizontal_overflow).map((record) => record.metadata.state_id), clipped_control_states: captured.filter((record) => record.metadata.zoom_results?.clipped_control_count > 0 || record.metadata.interaction_result?.geometry?.clipped_control_count > 0).map((record) => record.metadata.state_id), logo_control_overlap_states: captured.filter((record) => record.metadata.zoom_results?.logo_control_overlap_area > 0 || record.metadata.interaction_result?.geometry?.logo_navigation_overlap_area > 0).map((record) => record.metadata.state_id), reader_safety_defect_states: captured.filter((record) => record.metadata.reader.protected_content_exposed || record.metadata.reader.protected_prefetch || record.metadata.reader.balance_consumption !== 0).map((record) => record.metadata.state_id), listener_safety_defect_states: captured.filter((record) => record.metadata.listener.raw_media_url !== "absent" || record.metadata.listener.playable_source !== "absent" || record.metadata.listener.autoplay || record.metadata.listener.preload !== "absent" || record.metadata.listener.balance_consumption !== 0).map((record) => record.metadata.state_id), status_contract_defect_states: captured.filter((record) => record.metadata.status_contract?.result === "FAIL").map((record) => record.metadata.state_id), menu_state_count: interactionRecords.filter((record) => record.metadata.interaction_result.kind === "mobile-menu").length, filter_state_count: interactionRecords.filter((record) => record.metadata.interaction_result.kind === "library-filters").length, interaction_pass_count: interactionRecords.filter((record) => record.metadata.interaction_result.failures.length === 0).length, interaction_failure_states: interactionRecords.filter((record) => record.metadata.interaction_result.failures.length).map((record) => record.metadata.state_id), sanitized_fixture_count: captured.filter((record) => record.metadata.private_fixture).length, sensitive_data_defect_states: sensitiveDataDefectStates, production_authentication_states: captured.filter((record) => record.metadata.private_fixture?.production_authentication_used).map((record) => record.metadata.state_id), production_account_api_states: captured.filter((record) => record.metadata.private_fixture?.production_account_api_called).map((record) => record.metadata.state_id), static_parity_defect_states: captured.filter((record) => record.metadata.static_snapshot && (!record.metadata.static_snapshot.snapshot_exists || record.metadata.static_snapshot.static_logo_url !== "https://theearnalism.com/assets/brand/earnalism-brand-lockup.png")).map((record) => record.metadata.state_id), runtime_failure_states: captured.filter((record) => record.metadata.console_error_count || record.metadata.page_error_count || record.metadata.failed_required_request_count).map((record) => record.metadata.state_id), production_mutation_count: captured.reduce((sum, record) => sum + record.metadata.production_mutation_count, 0), browser_version: captured[0]?.metadata.browser_version, fixture_classifications: captured.map((record) => record.metadata.fixture), rendered_ui_defect_states: captured.filter((record) => record.metadata.rendered_ui_result !== "PASS").map((record) => record.metadata.state_id), output_directory: outputDirectory, generated_timestamp: new Date().toISOString() };
  fs.writeFileSync(path.join(outputDirectory, "route-surface-hashes.json"), JSON.stringify({ source_head: summary.source_head, tree_sha: summary.tree_sha, production_surface_sha256: summary.production_surface_sha256, route_surface_hashes: routeHashes, canonical_logo_sha256: summary.canonical_logo_sha256 }, null, 2) + "\n");
  fs.writeFileSync(path.join(outputDirectory, "capture-summary.json"), JSON.stringify(summary, null, 2) + "\n"); console.log(JSON.stringify({ captured: summary.captured_state_ids, output: outputDirectory, stable: stableCount === captured.length, summary: path.join(outputDirectory, "capture-summary.json") }));
}

const cli = parseCliArgs(process.argv.slice(2));
if (cli.listStates || cli.dryRun) {
  runManifestCli(cli);
  process.exit(0);
}
if (cli.capture) {
  await runManifestCapture(cli);
  process.exit(0);
}

const base = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const out = path.resolve(process.env.SEAMLESS_BRAND_CAPTURE_OUTPUT || "uat/evidence/seamless-brand-pilot/current");
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base)) throw new Error("UAT_BASE_URL must be loopback.");
fs.mkdirSync(path.join(out, "screenshots"), { recursive: true });
const states = [
  ["home-desktop", "/", 1440, 1000, 100], ["home-mobile", "/", 390, 844, 100], ["home-mobile-zoom-200", "/", 390, 844, 200],
  ["reader-mobile-390", "/reader/dracula?visual-fixture=1", 390, 844, 100], ["reader-mobile-320", "/reader/dracula?visual-fixture=1", 320, 568, 100],
  ["listener-mobile-390", "/listener/a-ghost-story?visual-fixture=1", 390, 844, 100], ["listener-mobile-320", "/listener/a-ghost-story?visual-fixture=1", 320, 568, 100],
  ["account-mobile", "/account?visual-fixture=1", 390, 844, 100], ["library-footer-mobile", "/library", 390, 844, 100],
];
const books = [{slug:"dracula",title:"Dracula",author:"Bram Stoker",publication_status:"LIVE_APPROVED",reader_enabled:true,preview_enabled:true,chapters:[{id:"p1",is_preview:true}]},{slug:"a-ghost-story",title:"A Ghost Story",author:"Mark Twain",publication_status:"LIVE_APPROVED",reader_enabled:true,audiobook_enabled:false,preview_enabled:true,chapters:[{id:"p1",is_preview:true}]}];
if (process.env.SEAMLESS_BRAND_BROWSER_IMPORT_SENTINEL === "1") throw new Error("Browser import sentinel reached outside the manifest CLI.");
const { chromium } = await import("playwright");
const browser = await chromium.launch({ headless: true }); const version = browser.version(); const results=[];
for (const [id, route, width, height, zoom] of states) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 }); const errors=[];
  page.on("console", m => { if (m.type()==="error") errors.push(m.text()); }); page.on("pageerror", e => errors.push(e.message));
  await page.route("**/api/**", r => { const u=new URL(r.request().url()); const body=u.pathname.endsWith("/books")?books:u.pathname.includes("auth")?{id:"fixture",email:"fixture@invalid.example"}:[]; r.fulfill({status:200,contentType:"application/json",body:JSON.stringify(body)}); });
  await page.goto(base+route,{waitUntil:"networkidle"}); await page.evaluate(async z=>{ document.documentElement.style.zoom=`${z}%`; await document.fonts.ready; },zoom); await page.emulateMedia({ reducedMotion:"reduce" });
  const file=path.join(out,"screenshots",`${id}.png`); await page.screenshot({path:file,fullPage:id==="library-footer-mobile",animations:"disabled"});
  const data=await page.evaluate(()=>{const lock=[...document.querySelectorAll('[data-testid="earnalism-brand-lockup"]')].filter(n=>{const s=getComputedStyle(n),r=n.getBoundingClientRect();return s.display!=="none"&&r.width>0&&r.height>0}); const l=lock[0], img=l?.querySelector("img"), r=l?.getBoundingClientRect(), s=l&&getComputedStyle(l); const header=document.querySelector(".experience-header")||document.querySelector('[data-testid="site-header"]'); return {scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,headerVisible:!!header&&getComputedStyle(header).display!=="none",lockupCount:lock.length,logo:l?{width:r.width,height:r.height,naturalWidth:img.naturalWidth,naturalHeight:img.naturalHeight,aspectRatio:r.width/r.height,transform:getComputedStyle(img).transform,clipped:r.left<0||r.right>innerWidth,wrapper:{background:s.backgroundColor,border:s.borderWidth,radius:s.borderRadius,shadow:s.boxShadow}}:null,footer:!!document.querySelector('[data-testid="footer-brand-paper-row"]')}; });
  results.push({id,route,viewport:{width,height},zoom,browser:"chromium",browserVersion:version,screenshot:path.relative(out,file),screenshotSha256:digest(file),consoleErrors:errors,overflow:data.scrollWidth>data.clientWidth,...data}); await page.close();
}
await browser.close(); fs.writeFileSync(path.join(out,"capture-results.json"),JSON.stringify({states:results,expected:states.map(s=>s[0])},null,2)+"\n"); console.log(JSON.stringify({captured:results.length,out}));
