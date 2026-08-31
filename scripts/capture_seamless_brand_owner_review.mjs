#!/usr/bin/env node
import crypto from "node:crypto";
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
const SANITIZED_PRIVATE_FIXTURE_SHA256 = crypto.createHash("sha256").update(JSON.stringify({ version: "sanitized-private-v1", identity: "Review Reader", email: "review@example.invalid", saved_library: [] })).digest("hex");

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

async function captureRequestedScreenshots(page, stateDirectory, capture, label, header, lockup) {
  const files = {};
  const attemptDirectory = path.join(stateDirectory, "attempts", label);
  fs.mkdirSync(attemptDirectory, { recursive: true });
  const write = async (name, action) => {
    const target = path.join(attemptDirectory, name);
    await action(target);
    files[name] = { path: target, sha256: digest(target) };
  };
  if (capture.viewport) await write("viewport.png", (target) => page.screenshot({ path: target, fullPage: false, animations: "disabled", caret: "hide", scale: "css" }));
  if (capture.full_page) await write("full-page.png", (target) => page.screenshot({ path: target, fullPage: true, animations: "disabled", caret: "hide", scale: "css" }));
  if (capture.brand_close_up) await write("brand-close-up.png", (target) => lockup.screenshot({ path: target, animations: "disabled", caret: "hide", scale: "css" }));
  if (capture.parent_surface_close_up) await write("parent-surface-close-up.png", (target) => header.screenshot({ path: target, animations: "disabled", caret: "hide", scale: "css" }));
  return files;
}

async function runOneStateCapture(options) {
  if (!options.output) throw new Error("--capture requires --output.");
  if (!options.baseUrl) throw new Error("--capture requires --base-url.");
  if (!options.browser) throw new Error("--capture requires --browser chromium.");
  if (options.browser !== "chromium") throw new Error(`Unsupported browser ${JSON.stringify(options.browser)}; expected chromium.`);
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
  const { chromium } = await import("playwright");
  const browser = await chromium.launch({ headless: true });
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
  await page.evaluate(async (zoom) => {
    await document.fonts.ready;
    await Promise.all(["16px Inter", "16px 'Noto Sans Bengali'", "16px 'Noto Serif Bengali'"].map((font) => document.fonts.load(font, "অA").catch(() => [])));
    await Promise.all([...document.images].filter((image) => {
      const style = getComputedStyle(image); const rect = image.getBoundingClientRect();
      return style.display !== "none" && rect.width > 0 && rect.height > 0;
    }).map((image) => image.decode().catch(() => undefined)));
    const style = document.createElement("style");
    style.textContent = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}";
    document.head.append(style);
    document.documentElement.style.zoom = `${zoom}%`;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, state.zoom);
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
  const data = await page.evaluate(() => {
    const visible = (node) => { const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0; };
    const headers = [...document.querySelectorAll('[data-testid="site-header"]')].filter(visible);
    const header = headers[0];
    const lockups = header ? [...header.querySelectorAll('[data-testid="earnalism-brand-lockup"]')].filter(visible) : [];
    const lockup = lockups[0]; const image = lockup?.querySelector("img"); const rect = lockup?.getBoundingClientRect(); const wrapper = lockup && getComputedStyle(lockup); const parent = header && getComputedStyle(header);
    const intersects = (a, b) => Math.max(a.left, b.left) < Math.min(a.right, b.right) && Math.max(a.top, b.top) < Math.min(a.bottom, b.bottom);
    const overlap = Boolean(lockup && [...header.querySelectorAll("a,button")].filter((node) => node !== lockup && !lockup.contains(node) && !node.contains(lockup) && visible(node)).some((node) => intersects(rect, node.getBoundingClientRect())));
    return { document_height: document.documentElement.scrollHeight, scroll_width: document.documentElement.scrollWidth, client_width: document.documentElement.clientWidth, visible_header_count: headers.length, visible_canonical_lockup_count: lockups.length, logo: lockup ? { natural_width: image.naturalWidth, natural_height: image.naturalHeight, rendered_width: rect.width, rendered_height: rect.height, aspect_ratio: rect.width / rect.height, transform: getComputedStyle(image).transform, wrapper_background: wrapper.backgroundColor, wrapper_border_width: wrapper.borderWidth, wrapper_border_radius: wrapper.borderRadius, wrapper_box_shadow: wrapper.boxShadow, wrapper_padding: wrapper.padding, parent_background: parent.backgroundColor, clipped: rect.left < 0 || rect.top < 0 || rect.right > innerWidth || rect.bottom > innerHeight } : null, overlap, horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth };
  });
  const metadata = { state_id: state.id, route: state.route, final_url: page.url(), viewport: state.viewport, zoom: state.zoom, fixture: state.fixture, interaction: state.interaction, browser: "chromium", browser_version: browser.version(), screenshot_paths: Object.fromEntries(Object.entries(finalFiles).map(([name, file]) => [name.replace(".png", "").replaceAll("-", "_"), file.path])), screenshot_sha256: Object.fromEntries(Object.entries(finalFiles).map(([name, file]) => [name.replace(".png", "").replaceAll("-", "_"), file.sha256])), stability_attempts: stabilityAttempts, stable, ...data, console_error_count: consoleErrors.length, page_error_count: pageErrors.length, failed_required_request_count: failedRequests.length };
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
  const books = [{ slug: "dracula", title: "Dracula", author: "Bram Stoker", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, chapters: [{ id: "p1", is_preview: true }] }, { slug: "a-ghost-story", title: "A Ghost Story", author: "Mark Twain", publication_status: "LIVE_APPROVED", reader_enabled: true, audiobook_enabled: false, preview_enabled: true, chapters: [{ id: "p1", is_preview: true }] }];
  const body = requestUrl.pathname.endsWith("/books") ? books : requestUrl.pathname.includes("auth") ? { id: "fixture", email: "fixture@invalid.example" } : [];
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

async function captureManifestState(browser, state, baseUrl, outputDirectory, contextIndex) {
  const stateDirectory = stateOutputDirectory(outputDirectory, state.id);
  const requiredScreenshots = requestedScreenshotNames(state.capture);
  if (!requiredScreenshots.includes("viewport.png")) throw new Error(`State ${state.id} capture declaration must include viewport.`);
  fs.mkdirSync(stateDirectory, { recursive: true });
  const context = await browser.newContext({ viewport: state.viewport, deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", colorScheme: "dark", serviceWorkers: "block" });
  const initialStorage = await context.storageState();
  const page = await context.newPage();
  const consoleErrors = []; const pageErrors = []; const failedRequests = []; const apiRequests = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push({ url: request.url(), failure: request.failure()?.errorText || "unknown" }));
  page.on("request", (request) => { if (new URL(request.url()).pathname.includes("/api/")) apiRequests.push({ url: request.url(), method: request.method() }); });
  await page.route("**/api/**", routeFixture);
  await page.route("https://theearnalism.com/assets/brand/earnalism-brand-lockup.png", (route) => route.fulfill({ path: "frontend/public/assets/brand/earnalism-brand-lockup.png", contentType: "image/png" }));
  await page.goto(fixtureUrl(baseUrl, state), { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.evaluate(async (zoom) => {
    await document.fonts.ready;
    await Promise.all(["16px Inter", "16px 'Noto Sans Bengali'", "16px 'Noto Serif Bengali'"].map((font) => document.fonts.load(font, "অA").catch(() => [])));
    await Promise.all([...document.images].filter((image) => { const style = getComputedStyle(image); const rect = image.getBoundingClientRect(); return style.display !== "none" && rect.width > 0 && rect.height > 0; }).map((image) => image.decode().catch(() => undefined)));
    const style = document.createElement("style"); style.textContent = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}"; document.head.append(style);
    document.documentElement.style.zoom = `${zoom}%`;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, state.zoom);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const header = page.locator('header[data-testid="site-header"]:visible, header.experience-header:visible');
  const headerCount = await header.count();
  if (headerCount !== 1) throw new Error(`State ${state.id}: expected exactly one visible header; received ${headerCount}.`);
  const lockup = header.locator('[data-testid="earnalism-brand-lockup"]:visible');
  const lockupCount = await lockup.count();
  if (lockupCount !== 1) throw new Error(`State ${state.id}: expected exactly one visible canonical lockup; received ${lockupCount}.`);
  let stable = false; const stabilityAttempts = []; let finalFiles = {};
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const first = await captureRequestedScreenshots(page, stateDirectory, state.capture, `attempt-${attempt}-first`, header, lockup);
    await page.waitForTimeout(500);
    const second = await captureRequestedScreenshots(page, stateDirectory, state.capture, `attempt-${attempt}-second`, header, lockup);
    const matches = stableHashSet(first, second);
    stabilityAttempts.push({ attempt, stable: matches, first: Object.fromEntries(Object.entries(first).map(([name, file]) => [name, file.sha256])), second: Object.fromEntries(Object.entries(second).map(([name, file]) => [name, file.sha256])) });
    if (matches) { stable = true; for (const [name, file] of Object.entries(second)) { const target = path.join(stateDirectory, name); fs.copyFileSync(file.path, target); finalFiles[name] = { path: name, sha256: digest(target) }; } break; }
  }
  const data = await page.evaluate(() => {
    const visible = (node) => { const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0; };
    const headers = [...document.querySelectorAll('header[data-testid="site-header"],header.experience-header')].filter(visible); const header = headers[0];
    const lockups = header ? [...header.querySelectorAll('[data-testid="earnalism-brand-lockup"]')].filter(visible) : []; const lockup = lockups[0]; const image = lockup?.querySelector("img"); const rect = lockup?.getBoundingClientRect(); const wrapper = lockup && getComputedStyle(lockup); const parent = header && getComputedStyle(header);
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
    return { document_height: document.documentElement.scrollHeight, scroll_width: document.documentElement.scrollWidth, client_width: document.documentElement.clientWidth, visible_header_count: headers.length, visible_canonical_lockup_count: lockups.length, logo: lockup ? { natural_width: image.naturalWidth, natural_height: image.naturalHeight, rendered_width: rect.width, rendered_height: rect.height, aspect_ratio: rect.width / rect.height, transform: getComputedStyle(image).transform, wrapper_background: wrapper.backgroundColor, wrapper_border_width: wrapper.borderWidth, wrapper_border_radius: wrapper.borderRadius, wrapper_box_shadow: wrapper.boxShadow, wrapper_padding: wrapper.padding, parent_background: parent.backgroundColor, clipped: rect.left < 0 || rect.top < 0 || rect.right > innerWidth || rect.bottom > innerHeight } : null, overlap, horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, menu_reachable: menuReachable, search_reachable: searchReachable, reader: { protected_content_exposed: Boolean(document.querySelector('[data-testid="reader-protected-content"],[data-testid="protected-reader-content"]')) || protectedRequest, protected_prefetch: protectedRequest, balance_consumption: balanceRequestCount }, listener: { raw_media_url: media.some((item) => item.src) ? "present" : "absent", playable_source: media.some((item) => item.src) ? "present" : "absent", autoplay: media.some((item) => item.autoplay), preload: media.some((item) => item.preload) ? "present" : "absent", balance_consumption: balanceRequestCount, cover_visible: [...document.querySelectorAll(".listener-v2 img")].some(visible) }, account: { visual_fixture_present: Boolean(accountFixture), sensitive_fixture_values_present: Boolean(accountFixture && sensitivePrivateFixtureValues) }, private_fixture: { fixture_visible: privateFixtureVisible, sensitive_fixture_values_present: sensitivePrivateFixtureValues, my_library_empty_state_visible: myLibraryEmptyStateVisible }, action_row_below_brand: !actionRect || !headerRect || actionRect.top >= headerRect.bottom };
  });
  const defects = [];
  if (data.visible_header_count !== 1 || data.visible_canonical_lockup_count !== 1 || data.logo?.clipped || data.overlap || data.horizontal_overflow || consoleErrors.length || pageErrors.length || failedRequests.length) defects.push("brand-shell-contract");
  if (state.fixture === "public-safe" && state.zoom === 200 && (!data.menu_reachable || !data.search_reachable)) defects.push("home-mobile-controls");
  if (state.fixture === "reader-visual-safe" && (!data.action_row_below_brand || data.reader.protected_content_exposed || data.reader.protected_prefetch || data.reader.balance_consumption !== 0)) defects.push("reader-fixture-contract");
  if (state.fixture === "listener-non-playable" && (!data.action_row_below_brand || !data.listener.cover_visible || data.listener.raw_media_url !== "absent" || data.listener.playable_source !== "absent" || data.listener.autoplay || data.listener.preload !== "absent" || data.listener.balance_consumption !== 0)) defects.push("listener-fixture-contract");
  const privateFixture = state.fixture === "sanitized-account";
  const productionAuthenticationUsed = privateFixture && (initialStorage.cookies.length !== 0 || initialStorage.origins.length !== 0 || apiRequests.some(({ url }) => !url.startsWith(baseUrl)));
  const productionAccountApiCalled = privateFixture && apiRequests.some(({ url }) => !url.startsWith(baseUrl));
  const mutationCount = apiRequests.filter(({ method }) => !["GET", "HEAD", "OPTIONS"].includes(method)).length;
  if (privateFixture && (!data.private_fixture.fixture_visible || data.private_fixture.sensitive_fixture_values_present || productionAuthenticationUsed || productionAccountApiCalled || mutationCount !== 0)) defects.push("sanitized-private-fixture-contract");
  const metadata = { state_id: state.id, route: state.route, final_url: page.url(), viewport: state.viewport, zoom: state.zoom, zoom_method: "document.documentElement.style.zoom", fixture: state.fixture, interaction: state.interaction, browser: "chromium", browser_version: browser.version(), context_id: `context-${contextIndex}`, initial_storage: { cookies: initialStorage.cookies.length, origins: initialStorage.origins.length }, screenshot_paths: Object.fromEntries(Object.entries(finalFiles).map(([name, file]) => [name.replace(".png", "").replaceAll("-", "_"), file.path])), screenshot_sha256: Object.fromEntries(Object.entries(finalFiles).map(([name, file]) => [name.replace(".png", "").replaceAll("-", "_"), file.sha256])), stability_attempts: stabilityAttempts, stable, rendered_ui_result: defects.length ? "RENDERED_UI_DEFECT_FOUND" : "PASS", rendered_ui_defects: defects, ...data, private_fixture: privateFixture ? { ...data.private_fixture, fixture_sha256: SANITIZED_PRIVATE_FIXTURE_SHA256, production_authentication_used: productionAuthenticationUsed, production_account_api_called: productionAccountApiCalled, mutation_count: mutationCount } : undefined, production_api_call_count: 0, intercepted_api_request_count: apiRequests.length, console_error_count: consoleErrors.length, page_error_count: pageErrors.length, failed_required_request_count: failedRequests.length };
  fs.writeFileSync(path.join(stateDirectory, "metadata.json"), JSON.stringify(metadata, null, 2) + "\n"); fs.writeFileSync(path.join(stateDirectory, "console-errors.json"), JSON.stringify(consoleErrors, null, 2) + "\n"); fs.writeFileSync(path.join(stateDirectory, "page-errors.json"), JSON.stringify(pageErrors, null, 2) + "\n"); fs.writeFileSync(path.join(stateDirectory, "failed-requests.json"), JSON.stringify(failedRequests, null, 2) + "\n");
  await context.close();
  if (!stable) throw new Error(`State ${state.id} is unstable after three bounded capture attempts.`);
  return { metadata, screenshotCount: Object.keys(finalFiles).length };
}

async function runManifestCapture(options) {
  if (!options.output) throw new Error("--capture requires --output."); if (!options.baseUrl) throw new Error("--capture requires --base-url."); if (!options.browser) throw new Error("--capture requires --browser chromium."); if (options.browser !== "chromium") throw new Error(`Unsupported browser ${JSON.stringify(options.browser)}; expected chromium.`);
  const baseUrl = String(options.baseUrl).replace(/\/$/, ""); if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("--base-url must be a loopback http://127.0.0.1:<port> URL.");
  const selection = loadManifestSelection(options); if (!selection.selected.length) throw new Error("--capture requires at least one selected state.");
  const outputDirectory = path.resolve(options.output); validateUniqueOutputDirectories(outputDirectory, selection.selected); fs.mkdirSync(outputDirectory, { recursive: true });
  if (process.env.SEAMLESS_BRAND_BROWSER_IMPORT_SENTINEL === "1") throw new Error("Browser import sentinel reached during --capture.");
  const { chromium } = await import("playwright"); const browser = await chromium.launch({ headless: true }); const captured = [];
  try { for (let index = 0; index < selection.selected.length; index += 1) captured.push(await captureManifestState(browser, selection.selected[index], baseUrl, outputDirectory, index + 1)); } finally { await browser.close(); }
  const stableCount = captured.filter((record) => record.metadata.stable).length;
  const reusedStateIds = selection.selected.filter((state) => Array.isArray(state.reuse_in) && state.reuse_in.length > 0).map((state) => state.id);
  const newlyAddedStateIds = selection.selected.filter((state) => typeof state.introduced_in === "string" && state.introduced_in.length > 0).map((state) => state.id);
  const sensitiveDataDefectStates = captured.filter((record) => record.metadata.private_fixture?.sensitive_fixture_values_present).map((record) => record.metadata.state_id);
  const summary = { manifest_path: selection.manifestPath, manifest_sha256: digest(selection.manifestPath), route_inventory_path: selection.routeInventoryPath, route_inventory_sha256: digest(selection.routeInventoryPath), production_surface_sha256: productionSurfaceHash(), canonical_logo_sha256: digest("frontend/public/assets/brand/earnalism-brand-lockup.png"), requested_state_ids: selection.selected.map((state) => state.id), reused_state_ids: reusedStateIds, newly_added_state_ids: newlyAddedStateIds, captured_state_ids: captured.map((record) => record.metadata.state_id), manifest_order_execution_list: selection.selected.map((state) => state.id), missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [], expected_state_count: selection.selected.length, captured_state_count: captured.length, generated_screenshot_count: captured.reduce((sum, record) => sum + record.screenshotCount, 0), stable_state_count: stableCount, unstable_state_count: captured.length - stableCount, sanitized_fixture_count: captured.filter((record) => record.metadata.private_fixture).length, sensitive_data_defect_states: sensitiveDataDefectStates, browser_version: captured[0]?.metadata.browser_version, fixture_classifications: captured.map((record) => record.metadata.fixture), rendered_ui_defect_states: captured.filter((record) => record.metadata.rendered_ui_result !== "PASS").map((record) => record.metadata.state_id), output_directory: outputDirectory, generated_timestamp: new Date().toISOString() };
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
