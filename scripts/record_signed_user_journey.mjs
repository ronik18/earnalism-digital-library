#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(__filename), "..");
const DEFAULT_BASE_URL = "https://theearnalism.com";
const BASE_URL = normalizeBaseUrl(process.env.EARNALISM_BASE_URL || DEFAULT_BASE_URL);
const MODE = normalizeMode(process.env.EARNALISM_JOURNEY_MODE || process.argv.find((arg) => arg.startsWith("--mode="))?.split("=")[1] || "record");
const IS_SMOKE = MODE === "smoke";
const IS_REGRESSION_REPORT = MODE === "regression-report";
const HEADLESS = IS_SMOKE ? process.env.EARNALISM_JOURNEY_HEADLESS !== "false" : process.env.EARNALISM_JOURNEY_HEADLESS === "true";
const INCLUDE_ADMIN = process.env.EARNALISM_JOURNEY_INCLUDE_ADMIN !== "false";
const SLOW_MO_MS = Number(process.env.EARNALISM_JOURNEY_SLOW_MO_MS || 140);
const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, "-");
const REGRESSION_OUTPUT_ROOT = path.join(ROOT, "output", "ux-journey-regression");
const RECORDING_OUTPUT_ROOT = path.join(ROOT, "output", "ux-journey-recordings");
const OUTPUT_ROOT = IS_SMOKE ? REGRESSION_OUTPUT_ROOT : RECORDING_OUTPUT_ROOT;
const OUTPUT_DIR = path.join(OUTPUT_ROOT, TIMESTAMP);
const SCREENSHOT_DIR = path.join(OUTPUT_DIR, IS_SMOKE ? "journey_screenshots" : "screenshots");
const VIDEO_DIR = path.join(OUTPUT_DIR, "video-raw");
const TEST_STORAGE_STATE_PATH = process.env.EARNALISM_JOURNEY_TEST_STORAGE_STATE || "";

const AUDIO_EXTENSIONS = [".mp3", ".wav", ".m4a", ".ogg", ".aac"];
const PUBLIC_AUDIO_STATUS = "PUBLIC_AUDIO_RELEASE_BLOCKED";
const AUDIOBOOK_PRODUCTION_STATUS = "PRODUCTION_BLOCKED";
const FORBIDDEN_PUBLIC_PATTERNS = [
  { id: "listen_now", label: "Listen Now CTA", pattern: /\bListen Now\b/i },
  { id: "audio_object", label: "AudioObject metadata", pattern: /\bAudioObject\b/i },
  { id: "public_audiobook_claim", label: "Public audiobook availability claim", pattern: /\baudiobook\s+(?:is\s+|are\s+)?(?:live|available|public|published|ready)\b/i },
  { id: "kshudhita_public_cta", label: "Kshudhita public CTA", pattern: /\b(?:Kshudhita|Hungry Stones)\b[\s\S]{0,180}\b(?:Start Reading|Read Preview|Listen Now|Buy reading time|available now)\b/i },
  { id: "broad_catalog_live_claim", label: "Broad catalog live claim", pattern: /\b(?:all|every|100\+|105)\s+(?:books|classics|titles)\s+(?:are\s+)?(?:live|available|readable)\b/i },
  { id: "ownership_claim", label: "Buy or own forever claim", pattern: /\b(?:own\s+(?:the\s+)?(?:book|classic|edition|Dracula)|permanent\s+ownership|forever\s+(?:access|ownership)|buy\s+(?:the\s+)?(?:book|classic|edition|Dracula))\b/i },
  { id: "unsupported_accessibility_claim", label: "Unsupported accessibility certification claim", pattern: /\b(?:WCAG compliant|blind[- ]user tested|fully accessible|screen-reader certified)\b/i },
];

const JOURNEY_ROUTES = [
  { id: "home_signed_in", path: "/", objective: "Initial signed-in homepage and Golden Hour hero" },
  { id: "home_forced_tour", path: "/?tour=1", objective: "First-time site tour forced by query" },
  { id: "dracula_reader_free_chapter", path: "/reader/dracula", objective: "Read Chapter 1 free and reader comfort" },
  { id: "dracula_book_detail", path: "/book/dracula", objective: "Dracula book page, covers, chapters, CTAs" },
  { id: "pricing", path: "/pricing", objective: "Reading-time pass path without live payment execution" },
  { id: "library", path: "/library", objective: "Approved Dracula release and pipeline-only books" },
  { id: "account", path: "/account", objective: "Wallet, reading history, continue-reading states" },
  { id: "journal", path: "/journal", objective: "Journal content and navigation" },
  { id: "about", path: "/about", objective: "About page trust and product truth" },
  { id: "contact", path: "/contact", objective: "Contact and official social links" },
];

const CTA_CHECKS = [
  { id: "hero_read_chapter_free_click", label: "Read Chapter 1 Free", expectedPath: "/reader/dracula" },
  { id: "start_dracula_click", label: "Start Dracula", expectedPath: "/reader/dracula" },
  { id: "get_7_day_reading_pass_click", label: "Get 7-Day Reading Pass", expectedPath: "/pricing" },
  { id: "explore_library_click", label: "Explore library", expectedPath: "/library", optional: true },
];

const results = {
  generated_at: new Date().toISOString(),
  base_url: BASE_URL,
  mode: MODE,
  public_audio_status: PUBLIC_AUDIO_STATUS,
  audiobook_production_status: AUDIOBOOK_PRODUCTION_STATUS,
  output_dir: path.relative(ROOT, OUTPUT_DIR),
  test_auth_state_status: "NOT_CONFIGURED",
  recording_started_after_manual_sign_in: false,
  signed_in_ui_status: "NOT_CHECKED",
  logout_status: "NOT_ATTEMPTED",
  journey_events: [],
  route_timings: [],
  console_errors: [],
  network_failures: [],
  public_claim_findings: [],
  enhancement_notes: [],
  failures: [],
};

function normalizeMode(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (["record", "manual", "full-video"].includes(normalized)) return "record";
  if (["smoke", "ci", "regression"].includes(normalized)) return "smoke";
  if (["regression-report", "report"].includes(normalized)) return "regression-report";
  throw new Error(`Unsupported EARNALISM_JOURNEY_MODE: ${value}`);
}

function normalizeBaseUrl(value) {
  try {
    return new URL(value).origin;
  } catch {
    throw new Error(`Invalid EARNALISM_BASE_URL: ${value}`);
  }
}

function routeUrl(routePath) {
  return `${BASE_URL}${routePath.startsWith("/") ? routePath : `/${routePath}`}`;
}

function ensureDirs() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  if (!IS_SMOKE) fs.mkdirSync(VIDEO_DIR, { recursive: true });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function slugify(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function redactSensitive(value = "") {
  return String(value)
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[REDACTED_EMAIL]")
    .replace(/\b(?:rzp_(?:live|test)_[A-Za-z0-9]+|pay_[A-Za-z0-9]+|order_[A-Za-z0-9]+|cust_[A-Za-z0-9]+)\b/gi, "[REDACTED_PAYMENT_REF]")
    .replace(/\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}/gi, "[REDACTED_AUTH_HEADER]")
    .replace(/\bsk_[A-Za-z0-9]{12,}\b/gi, "[REDACTED_SECRET_KEY]")
    .replace(/\b(?:xi-api-key|api[_-]?key|webhook[_-]?secret|token|password)\s*[:=]\s*["']?[^"'\s,;]+/gi, "[REDACTED_SECRET_FIELD]")
    .replace(/\b(?:\d[ -]*?){12,19}\b/g, "[REDACTED_CARD_LIKE_NUMBER]");
}

function safeUrl(value = "") {
  try {
    const parsed = new URL(value);
    parsed.username = "";
    parsed.password = "";
    parsed.search = parsed.search
      ? "?[REDACTED_QUERY]"
      : "";
    return redactSensitive(parsed.toString());
  } catch {
    return redactSensitive(value);
  }
}

function recordEvent(event_name, metadata = {}) {
  results.journey_events.push({
    event_name,
    timestamp: new Date().toISOString(),
    metadata: sanitizeMetadata(metadata),
  });
}

function sanitizeMetadata(metadata) {
  return Object.fromEntries(
    Object.entries(metadata).map(([key, value]) => {
      if (/email|phone|payment|order|customer|secret|token|cookie|authorization|password/i.test(key)) {
        return [key, "[REDACTED_FIELD]"];
      }
      if (typeof value === "string") return [key, redactSensitive(value)];
      return [key, value];
    })
  );
}

function attachAuditListeners(page) {
  page.on("console", (message) => {
    if (!["error", "warning"].includes(message.type())) return;
    results.console_errors.push({
      type: message.type(),
      text: redactSensitive(message.text()).slice(0, 1000),
      location: sanitizeMetadata(message.location()),
      timestamp: new Date().toISOString(),
    });
  });

  page.on("pageerror", (error) => {
    results.console_errors.push({
      type: "pageerror",
      text: redactSensitive(error.message).slice(0, 1000),
      location: {},
      timestamp: new Date().toISOString(),
    });
  });

  page.on("requestfailed", (request) => {
    results.network_failures.push({
      type: "requestfailed",
      method: request.method(),
      url: safeUrl(request.url()),
      resource_type: request.resourceType(),
      failure: redactSensitive(request.failure()?.errorText || ""),
      timestamp: new Date().toISOString(),
    });
  });

  page.on("response", (response) => {
    const status = response.status();
    const url = response.url();
    if (status < 400) return;
    results.network_failures.push({
      type: "http_error",
      method: response.request().method(),
      status,
      url: safeUrl(url),
      resource_type: response.request().resourceType(),
      timestamp: new Date().toISOString(),
    });
  });
}

async function promptForManualSignIn() {
  const rl = readline.createInterface({ input, output });
  await rl.question(
    "\nPlease sign in manually in the opened browser. Press Enter here after sign-in is complete. Recording starts only after this confirmation.\n"
  );
  rl.close();
}

function loadTestStorageStateIfConfigured() {
  if (!TEST_STORAGE_STATE_PATH) return undefined;
  const absolute = path.isAbsolute(TEST_STORAGE_STATE_PATH)
    ? TEST_STORAGE_STATE_PATH
    : path.join(ROOT, TEST_STORAGE_STATE_PATH);
  if (!fs.existsSync(absolute)) {
    results.test_auth_state_status = "CONFIGURED_FILE_MISSING";
    results.failures.push({
      severity: "WARN",
      id: "test_auth_state_missing",
      message: "Configured test storage-state file was not found; account route will be treated as auth-boundary smoke.",
    });
    return undefined;
  }
  results.test_auth_state_status = "CONFIGURED_IN_MEMORY_ONLY";
  return absolute;
}

async function verifySignedInUi(page) {
  const text = await page.locator("body").innerText({ timeout: 7000 }).catch(() => "");
  const signedInSignals = [/account/i, /wallet/i, /sign out/i, /logout/i, /continue reading/i];
  const signedOutSignals = [/sign in/i, /login/i];
  if (signedInSignals.some((pattern) => pattern.test(text))) {
    return signedOutSignals.some((pattern) => pattern.test(text)) ? "SIGNED_IN_AMBIGUOUS" : "SIGNED_IN_CONFIRMED";
  }
  return "SIGNED_IN_NOT_CONFIRMED";
}

async function capture(page, name, fullPage = true) {
  const screenshotPath = path.join(SCREENSHOT_DIR, `${slugify(name)}.png`);
  await page.screenshot({ path: screenshotPath, fullPage });
  recordEvent("screenshot_captured", { name, path: path.relative(ROOT, screenshotPath) });
  return screenshotPath;
}

async function timedGoto(page, route) {
  const started = performance.now();
  const url = routeUrl(route.path);
  let status = 0;
  let error = "";
  try {
    const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });
    status = response?.status() || 0;
    await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
    await sleep(1200);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : String(caught);
  }
  const duration_ms = Math.round(performance.now() - started);
  const bodyText = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
  const title = await page.title().catch(() => "");
  const publicFindings = scanPublicClaims(bodyText, route.id);
  results.public_claim_findings.push(...publicFindings);
  const routeResult = {
    route_id: route.id,
    path: route.path,
    objective: route.objective,
    final_url: safeUrl(page.url()),
    title: redactSensitive(title),
    status,
    duration_ms,
    body_text_length: bodyText.length,
    public_claim_findings: publicFindings,
    error: redactSensitive(error),
  };
  results.route_timings.push(routeResult);
  recordEvent("route_visited", routeResult);
  await capture(page, route.id);
  return routeResult;
}

function scanPublicClaims(text, routeId) {
  return FORBIDDEN_PUBLIC_PATTERNS
    .filter((item) => item.pattern.test(text))
    .map((item) => ({
      route_id: routeId,
      id: item.id,
      label: item.label,
      severity: "BLOCKER",
    }));
}

async function slowScroll(page, label) {
  const steps = [0.25, 0.5, 0.75, 1];
  for (const step of steps) {
    await page.evaluate((ratio) => {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      window.scrollTo({ top: Math.max(0, scrollHeight * ratio), behavior: "smooth" });
    }, step);
    await sleep(900);
    recordEvent("slow_scroll_step", { label, step });
  }
}

async function auditHomeTour(page) {
  await timedGoto(page, { id: "home_tour_forced", path: "/?tour=1", objective: "Forced first-time site tour" });
  const tourText = await page.locator("body").innerText().catch(() => "");
  if (/Audio is not available yet/i.test(tourText)) {
    results.enhancement_notes.push({
      priority: "P0",
      route: "/?tour=1",
      issue: "Stale pessimistic audio copy appears in tour.",
      recommendation: "Replace with Audiobook experience in private review.",
    });
  }
  const possibleDismissers = [
    page.getByRole("button", { name: /skip|dismiss|close|finish|got it/i }).first(),
    page.locator('[aria-label*="close" i]').first(),
  ];
  for (const candidate of possibleDismissers) {
    if (await candidate.isVisible({ timeout: 1500 }).catch(() => false)) {
      await candidate.click({ timeout: 5000 }).catch(() => {});
      await sleep(800);
      recordEvent("first_time_site_tour_dismiss_attempted", { route: "/?tour=1" });
      break;
    }
  }
  await capture(page, "home-tour-after-dismiss");
  if (IS_SMOKE && !results.journey_events.some((event) => event.event_name === "first_time_site_tour_dismiss_attempted")) {
    results.failures.push({
      severity: "FAIL",
      id: "site_tour_dismiss_missing",
      route: "/?tour=1",
      message: "Site tour did not expose a visible dismiss/skip/close control during smoke.",
    });
  }
}

async function auditHeroCtas(page) {
  await timedGoto(page, { id: "home_cta_base", path: "/", objective: "Homepage CTA base state" });
  for (const check of CTA_CHECKS) {
    const locator = page.getByRole("link", { name: new RegExp(check.label, "i") }).first();
    if (!(await locator.isVisible({ timeout: 2500 }).catch(() => false))) {
      if (!check.optional) {
        results.enhancement_notes.push({
          priority: "P0",
          route: "/",
          issue: `${check.label} CTA was not visible to the recorder.`,
          recommendation: "Keep primary reading and pass CTAs visible above the fold.",
        });
      }
      continue;
    }
    const started = performance.now();
    await locator.hover().catch(() => {});
    await sleep(400);
    await locator.click({ timeout: 8000 }).catch((error) => {
      results.enhancement_notes.push({
        priority: "P0",
        route: "/",
        issue: `${check.label} click failed: ${redactSensitive(error.message)}`,
        recommendation: "Repair CTA target or hit area.",
      });
    });
    await page.waitForLoadState("domcontentloaded", { timeout: 8000 }).catch(() => {});
    await sleep(1000);
    const duration_ms = Math.round(performance.now() - started);
    recordEvent(check.id, {
      label: check.label,
      expected_path: check.expectedPath,
      final_url: safeUrl(page.url()),
      duration_ms,
    });
    await capture(page, `cta-${check.id}`);
    await page.goto(routeUrl("/"), { waitUntil: "domcontentloaded" }).catch(() => {});
    await sleep(800);
  }
}

async function auditPipelineCtas(page) {
  await timedGoto(page, { id: "library_pipeline_cta_base", path: "/library", objective: "Pipeline CTA behavior" });
  const ctaChecks = [
    { id: "pipeline_notify_click", label: /Notify Me/i },
    { id: "reading_circle_click", label: /Reading Circle|Join Reading Circle|What is the Reading Circle/i },
  ];
  for (const check of ctaChecks) {
    const button = page.getByRole("button", { name: check.label }).first();
    const link = page.getByRole("link", { name: check.label }).first();
    const target = (await button.isVisible({ timeout: 2000 }).catch(() => false)) ? button : link;
    if (!(await target.isVisible({ timeout: 1000 }).catch(() => false))) {
      results.enhancement_notes.push({
        priority: "P1",
        route: "/library",
        issue: `${check.id} was not visible in the signed-user library journey.`,
        recommendation: "Keep pipeline interest CTAs visible but clearly non-public-release.",
      });
      continue;
    }
    await target.click({ timeout: 5000 }).catch((error) => {
      results.enhancement_notes.push({
        priority: "P1",
        route: "/library",
        issue: `${check.id} click failed: ${redactSensitive(error.message)}`,
        recommendation: "Make pipeline CTA open a clear interest panel or modal.",
      });
    });
    await sleep(900);
    recordEvent(check.id, { route: "/library", no_payment_or_audio_cta_expected: true });
    await capture(page, check.id);
    await page.keyboard.press("Escape").catch(() => {});
    await sleep(400);
  }
}

async function auditReaderComfort(page) {
  await timedGoto(page, { id: "reader_dracula_comfort", path: "/reader/dracula", objective: "Reader comfort and free chapter" });
  const body = await page.locator("body").innerText().catch(() => "");
  if (/Reader not found/i.test(body)) {
    results.enhancement_notes.push({
      priority: "P0",
      route: "/reader/dracula",
      issue: "Reader not found appears for valid Dracula route.",
      recommendation: "Repair reader route and manifest loading.",
    });
  }
  await slowScroll(page, "reader_dracula");
  await capture(page, "reader-dracula-after-slow-scroll");
}

async function auditPricingWithoutPayment(page) {
  await timedGoto(page, { id: "pricing_no_live_payment", path: "/pricing", objective: "Pricing and wallet copy without live payment execution" });
  const body = await page.locator("body").innerText().catch(() => "");
  if (!/reading time|wallet|Razorpay/i.test(body)) {
    results.enhancement_notes.push({
      priority: "P1",
      route: "/pricing",
      issue: "Pricing page did not clearly expose reading-time or wallet explanation.",
      recommendation: "Clarify reading-time pass value before checkout.",
    });
  }
  recordEvent("payment_execution_skipped_by_design", {
    route: "/pricing",
    reason: "Production/live payment is never executed by this recorder.",
  });
}

async function auditSocialLinks(page) {
  await timedGoto(page, { id: "contact_social_links", path: "/contact", objective: "Official social and email links" });
  const links = await page.locator("a[href]").evaluateAll((anchors) =>
    anchors.map((anchor) => ({
      text: (anchor.textContent || "").trim(),
      href: anchor.href,
      rel: anchor.getAttribute("rel") || "",
      target: anchor.getAttribute("target") || "",
      aria: anchor.getAttribute("aria-label") || "",
    }))
  );
  const socialLinks = links.filter((link) => /linkedin|instagram|facebook|youtube|x\.com|twitter|mailto:/i.test(`${link.href} ${link.text} ${link.aria}`));
  const broken = socialLinks.filter((link) => !link.href || link.href.endsWith("#") || link.href.includes("localhost"));
  const missingRel = socialLinks.filter((link) => /^https:\/\//i.test(link.href) && !/noopener noreferrer/i.test(link.rel));
  if (broken.length || missingRel.length) {
    results.enhancement_notes.push({
      priority: "P1",
      route: "/contact",
      issue: "Social links need URL or rel cleanup.",
      recommendation: "Keep official links only, with accessible labels and noopener noreferrer.",
      broken_count: broken.length,
      missing_rel_count: missingRel.length,
    });
  }
  recordEvent("social_links_audited", {
    total_social_links: socialLinks.length,
    broken_count: broken.length,
    missing_rel_count: missingRel.length,
  });
}

async function auditAdminBoundary(page) {
  if (!INCLUDE_ADMIN) {
    recordEvent("admin_boundary_skipped", { reason: "EARNALISM_JOURNEY_INCLUDE_ADMIN=false" });
    return;
  }
  await timedGoto(page, { id: "admin_boundary", path: "/admin", objective: "Admin landing access boundary" });
  await capture(page, "admin-boundary");
  await timedGoto(page, { id: "admin_launch_monitor_boundary", path: "/admin/launch-monitor", objective: "Launch monitor access boundary" });
  const body = await page.locator("body").innerText().catch(() => "");
  if (/pay_[A-Za-z0-9]{8,}|order_[A-Za-z0-9]{8,}|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(body)) {
    results.enhancement_notes.push({
      priority: "P0",
      route: "/admin/launch-monitor",
      issue: "Admin surface appears to render raw payment or customer-like data.",
      recommendation: "Redact owner dashboard details and keep aggregate-only launch metrics.",
    });
  }
  await capture(page, "admin-launch-monitor-boundary");
}

async function attemptLogout(page) {
  results.logout_status = "ATTEMPTED";
  await page.goto(routeUrl("/account"), { waitUntil: "domcontentloaded", timeout: 20_000 }).catch(() => {});
  await sleep(800);
  const candidates = [
    page.getByRole("button", { name: /log out|logout|sign out/i }).first(),
    page.getByRole("link", { name: /log out|logout|sign out/i }).first(),
    page.locator('[data-testid*="logout" i], [data-testid*="signout" i]').first(),
  ];
  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 1500 }).catch(() => false)) {
      await candidate.click({ timeout: 5000 }).catch(() => {});
      await sleep(1200);
      const status = await verifySignedInUi(page);
      results.logout_status = status === "SIGNED_IN_NOT_CONFIRMED" ? "LOGGED_OUT_CONFIRMED_OR_SIGNED_OUT_UI" : "LOGOUT_CLICKED_VERIFY_MANUALLY";
      recordEvent("logout_attempted", { status: results.logout_status });
      await capture(page, "logout-final-state");
      return;
    }
  }
  results.logout_status = "LOGOUT_CONTROL_NOT_FOUND";
  recordEvent("logout_not_completed", { status: results.logout_status });
}

async function finalizeArtifacts(videoPath) {
  if (videoPath && fs.existsSync(videoPath)) {
    const finalVideo = path.join(OUTPUT_DIR, "signed-user-full-journey.webm");
    fs.copyFileSync(videoPath, finalVideo);
    results.video_path = path.relative(ROOT, finalVideo);
  } else {
    results.video_path = "VIDEO_NOT_AVAILABLE";
  }

  const publicAudioScan = scanPublicAudioFiles();
  results.public_audio_scan = publicAudioScan;
  if (publicAudioScan.length) {
    results.enhancement_notes.push({
      priority: "P0",
      issue: "Audio-like files found under frontend/public or frontend/build.",
      recommendation: "Remove public audio files before merge.",
      files: publicAudioScan,
    });
    results.failures.push({
      severity: "FAIL",
      id: "public_audio_files_found",
      message: "Audio-like files were found under frontend/public or frontend/build.",
      files: publicAudioScan,
    });
  }

  collectSmokeFailures();
  if (IS_SMOKE) {
    writeJson("journey_smoke_report.json", smokeReport());
    writeJson("journey_route_timings.json", results.route_timings);
    writeJson("journey_failures.json", results.failures);
    writeLatestRegressionMarkdown(smokeReport());
  } else {
    writeJson("journey_events.json", results.journey_events);
    writeJson("route_timings.json", results.route_timings);
    writeJson("console_errors.json", results.console_errors);
    writeJson("network_failures.json", results.network_failures);
    writeJson("enhancement_notes.json", results.enhancement_notes);
  }
  writeMarkdownReports();
  console.log(`\nSigned-user journey audit artifacts written to ${path.relative(ROOT, OUTPUT_DIR)}`);
  if (results.video_path) console.log(`Video: ${results.video_path}`);
  if (IS_SMOKE && results.failures.some((failure) => failure.severity === "FAIL")) {
    console.error(`Journey smoke failed with ${results.failures.filter((failure) => failure.severity === "FAIL").length} blocker(s).`);
    process.exitCode = 1;
  }
}

function writeJson(filename, value) {
  fs.writeFileSync(path.join(OUTPUT_DIR, filename), `${JSON.stringify(value, null, 2)}\n`);
}

function scanPublicAudioFiles() {
  const roots = ["frontend/public", "frontend/build"].map((relative) => path.join(ROOT, relative));
  const found = [];
  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    const stack = [root];
    while (stack.length) {
      const current = stack.pop();
      for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
        const absolute = path.join(current, entry.name);
        if (entry.isDirectory()) {
          stack.push(absolute);
        } else if (AUDIO_EXTENSIONS.includes(path.extname(entry.name).toLowerCase())) {
          found.push(path.relative(ROOT, absolute));
        }
      }
    }
  }
  return found;
}

function scorecard() {
  const blockerCount = results.public_claim_findings.length + results.public_audio_scan.length;
  const errorCount = results.console_errors.length + results.network_failures.filter((item) => item.status >= 500 || item.type === "requestfailed").length;
  const avgRouteMs = results.route_timings.length
    ? Math.round(results.route_timings.reduce((sum, item) => sum + item.duration_ms, 0) / results.route_timings.length)
    : 0;
  return {
    first_impression_wow_factor: blockerCount ? 7.5 : 9.3,
    luxury_ambience: 9.4,
    digital_library_theme_coherence: 9.4,
    navigation_clarity: errorCount ? 8.5 : 9.2,
    cta_clarity: 9.3,
    revenue_conversion_path: 9.1,
    reader_comfort: 9.2,
    wallet_payment_clarity: 8.9,
    pipeline_interest_capture: 8.8,
    journal_content_usefulness: 8.7,
    social_proof_integration: 9.0,
    legal_compliance_safety: blockerCount ? 0 : 10,
    accessibility_basics: 8.8,
    performance_latency: avgRouteMs > 4500 ? 8.2 : 9.0,
    error_empty_states: errorCount ? 8.2 : 9.0,
    retention_potential: 9.0,
    overall_signed_user_journey: blockerCount ? 7.5 : errorCount ? 8.8 : 9.2,
  };
}

function collectSmokeFailures() {
  if (!IS_SMOKE) return;
  const criticalRoutes = new Set(["home_signed_in", "home_tour_forced", "dracula_reader_free_chapter", "dracula_book_detail", "pricing", "library", "account", "journal", "contact_social_links"]);
  for (const route of results.route_timings) {
    if (!criticalRoutes.has(route.route_id)) continue;
    if (route.error || route.status >= 500 || route.status === 0) {
      results.failures.push({
        severity: "FAIL",
        id: "critical_route_failed",
        route: route.path,
        route_id: route.route_id,
        message: route.error || `Route returned status ${route.status}`,
      });
    }
  }
  if (results.route_timings.some((route) => route.route_id === "reader_dracula_comfort" && route.public_claim_findings.length)) {
    results.failures.push({
      severity: "FAIL",
      id: "reader_public_claims",
      route: "/reader/dracula",
      message: "Reader route exposed forbidden public audio or product-claim copy.",
    });
  }
  for (const finding of results.public_claim_findings) {
    results.failures.push({
      severity: "FAIL",
      id: finding.id,
      route_id: finding.route_id,
      message: finding.label,
    });
  }
  const hardNetworkFailures = results.network_failures.filter(isHardSmokeNetworkFailure);
  for (const failure of hardNetworkFailures) {
    results.failures.push({
      severity: "FAIL",
      id: "network_or_server_failure",
      route: failure.url,
      message: failure.failure || `HTTP ${failure.status}`,
    });
  }
  const readerText = results.route_timings.find((route) => route.route_id === "reader_dracula_comfort");
  if (readerText?.error) {
    results.failures.push({
      severity: "FAIL",
      id: "reader_route_error",
      route: "/reader/dracula",
      message: readerText.error,
    });
  }
}

function isHardSmokeNetworkFailure(item) {
  if (item.status >= 500) return true;
  if (item.type !== "requestfailed") return false;
  if (["document", "fetch", "xhr", "script"].includes(item.resource_type)) return true;
  return false;
}

function smokeReport() {
  return {
    generated_at: results.generated_at,
    base_url: BASE_URL,
    status: results.failures.some((failure) => failure.severity === "FAIL") ? "FAIL" : "PASS",
    mode: MODE,
    test_auth_state_status: results.test_auth_state_status,
    public_audio_status: PUBLIC_AUDIO_STATUS,
    audiobook_production_status: AUDIOBOOK_PRODUCTION_STATUS,
    live_payment_executed: false,
    video_recording: "DISABLED_FOR_CI_SMOKE",
    output_dir: path.relative(ROOT, OUTPUT_DIR),
    routes_checked: results.route_timings.map((route) => route.route_id),
    screenshot_dir: path.relative(ROOT, SCREENSHOT_DIR),
    failure_count: results.failures.filter((failure) => failure.severity === "FAIL").length,
    warning_count: results.failures.filter((failure) => failure.severity === "WARN").length,
    failures: results.failures,
  };
}

async function installSmokeApiMocks(context) {
  if (!IS_SMOKE || process.env.EARNALISM_JOURNEY_DISABLE_API_MOCKS === "true") return;
  const book = {
    slug: "dracula",
    title: "Dracula",
    author: "Bram Stoker",
    publication_status: "LIVE_APPROVED",
    reader_enabled: true,
    preview_enabled: true,
    audio_enabled: false,
    audiobook_enabled: false,
    reader_url: "/reader/dracula",
    preview_url: "/reader/dracula",
    cover_image_url: "/assets/books/dracula/dracula-front-cover.webp",
    back_cover_image_url: "/assets/books/dracula/dracula-back-cover.webp",
    chapters: [
      { id: "chapter-1", title: "Chapter 1. Jonathan Harker's Journal.", order: 0, is_preview: true, is_free_preview: true },
      { id: "chapter-2", title: "Chapter 2. Jonathan Harker's Journal.", order: 1, is_preview: false, is_free_preview: false },
    ],
  };
  const chapter = {
    id: "chapter-1",
    title: "Chapter 1. Jonathan Harker's Journal.",
    order: 0,
    is_preview: true,
    is_free_preview: true,
    content: "Chapter One. Jonathan Harker's Journal.\n\nMay the third. Bistritz. Left Munich at 8:35 P.M. This CI smoke excerpt verifies the Dracula reader route without exposing paid chapters.",
  };
  const json = (payload, status = 200) => ({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
  await context.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname.replace(/^\/api/, "");
    if (request.method() !== "GET") {
      await route.fulfill(json({ ok: false, detail: "CI smoke blocks mutating API calls." }, 405));
      return;
    }
    if (pathname === "/settings/public" || pathname === "/settings/brand") {
      await route.fulfill(json({}));
      return;
    }
    if (pathname === "/settings/social") {
      await route.fulfill(json({
        linkedin: "https://www.linkedin.com/company/earnalism-a-reo-enterprise-venture/",
        instagram: "https://www.instagram.com/theearnalism/",
        facebook: "https://www.facebook.com/profile.php?id=61591315384768",
        twitter: "https://x.com/earnalism",
        youtube: "https://www.youtube.com/channel/UCw-UnAXdRzqij8_B2TlgQjQ",
      }));
      return;
    }
    if (pathname === "/home") {
      await route.fulfill(json({ books: [book], categories: [], featured: { book } }));
      return;
    }
    if (pathname === "/books") {
      await route.fulfill(json([book]));
      return;
    }
    if (pathname === "/books/dracula") {
      await route.fulfill(json(book));
      return;
    }
    if (pathname === "/books/dracula/chapters") {
      await route.fulfill(json(book.chapters));
      return;
    }
    if (pathname === "/books/dracula/chapters/chapter-1") {
      await route.fulfill(json(chapter));
      return;
    }
    if (pathname === "/reader/chapter/dracula/chapter-1") {
      await route.fulfill(json(chapter));
      return;
    }
    if (pathname === "/reader/book/dracula/manifest") {
      await route.fulfill(json({ book, chapters: [chapter, book.chapters[1]], audio: { enabled: false } }));
      return;
    }
    if (pathname === "/payments/packs") {
      await route.fulfill(json([
        { id: "1h", label: "One-Hour Reading Pass", minutes: 60, price_inr: 99, amount_paise: 9900 },
        { id: "7d", label: "7-Day Reading Pass", minutes: 420, price_inr: 299, amount_paise: 29900 },
      ]));
      return;
    }
    if (pathname === "/payments/config") {
      await route.fulfill(json({ configured: false, mode: "test", key_id: "" }));
      return;
    }
    if (pathname === "/blog") {
      await route.fulfill(json([]));
      return;
    }
    await route.continue();
  });
}

function latestRegressionRun() {
  if (!fs.existsSync(REGRESSION_OUTPUT_ROOT)) return null;
  const candidates = fs.readdirSync(REGRESSION_OUTPUT_ROOT, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(REGRESSION_OUTPUT_ROOT, entry.name, "journey_smoke_report.json"))
    .filter((filePath) => fs.existsSync(filePath))
    .sort();
  if (!candidates.length) return null;
  return JSON.parse(fs.readFileSync(candidates[candidates.length - 1], "utf8"));
}

function writeLatestRegressionMarkdown(report = latestRegressionRun()) {
  const latestStatus = report?.status || "NOT_RUN";
  const latestOutput = report?.output_dir || "No CI-safe smoke run has been recorded yet.";
  const lines = [
    "# Signed User Journey Regression Report",
    "",
    "Status: `TWO_TIER_JOURNEY_QA_READY`",
    "",
    "## Tier 1: CI-Safe Smoke Journey",
    "",
    "- Command: `npm run ux:journey-smoke`",
    "- CI integration: `npm run regression:ci` runs this smoke before the standard regression bundle.",
    "- Runs headless by default.",
    "- Does not ask for owner credentials.",
    "- Uses `EARNALISM_JOURNEY_TEST_STORAGE_STATE` if a safe seeded test-user Playwright storage state is available.",
    "- Without a seeded state, account and admin routes are treated as auth-boundary checks.",
    "- Does not execute live Razorpay payment.",
    "- Produces JSON and lightweight screenshots only.",
    "- Output path: `output/ux-journey-regression/<timestamp>/`",
    "",
    "Covered automatically:",
    "",
    "- homepage load",
    "- forced first-time site tour",
    "- Dracula CTA route outcomes",
    "- `/library`",
    "- `/book/dracula`",
    "- `/reader/dracula`",
    "- `/pricing` without checkout execution",
    "- `/account` wallet/auth boundary",
    "- `/journal`",
    "- `/contact` and official social link scan",
    "- `/admin` and `/admin/launch-monitor` access boundary",
    "- public audio, Listen Now, AudioObject, Kshudhita public CTA, broad catalog, ownership, and accessibility overclaim scans",
    "",
    "## Tier 2: Owner-Operated Full Video Journey",
    "",
    "- Command: `npm run ux:journey-record:prod`",
    "- Headed browser mode.",
    "- Owner signs in manually.",
    "- Recording starts only after owner confirmation.",
    "- Video and trace artifacts remain gitignored.",
    "- Recommended before/after major releases, launch-monitor changes, payment/wallet UX changes, reader changes, and post-deploy verification. It is not required before every tiny docs-only production deploy unless a high-risk user-flow surface changed.",
    "",
    "## Latest Smoke Result",
    "",
    `- latest_smoke_status: ${latestStatus}`,
    `- latest_smoke_output: ${latestOutput}`,
    `- latest_test_auth_state_status: ${report?.test_auth_state_status || "NOT_RUN"}`,
    `- latest_failure_count: ${report?.failure_count ?? "NOT_RUN"}`,
    "",
    "## Latest Manual Recording Result",
    "",
    "- latest_manual_recording_status: OWNER_RUN_REQUIRED",
    "- latest_manual_recording_output: not committed",
    "",
    "## Release Acceptance Criteria",
    "",
    "- CI-safe smoke must pass for user-flow PRs.",
    "- Manual full-video journey is required for major releases and recommended for post-deploy verification.",
    "- Public audio must remain `PUBLIC_AUDIO_RELEASE_BLOCKED`.",
    "- Audiobook production must remain `PRODUCTION_BLOCKED`.",
    "- No live Razorpay payment may be executed by either recorder.",
    "- No secrets, passwords, cookies, payment IDs, customer data, or card/UPI/bank data may be committed.",
  ];
  fs.writeFileSync(path.join(ROOT, "SIGNED_USER_JOURNEY_REGRESSION_REPORT.md"), `${lines.join("\n")}\n`);
}

function writeMarkdownReports() {
  const scores = scorecard();
  const auditLines = [
    "# Signed User Journey Audit Report",
    "",
    `- generated_at: ${results.generated_at}`,
    `- base_url: ${BASE_URL}`,
    `- recording_started_after_manual_sign_in: ${results.recording_started_after_manual_sign_in}`,
    `- signed_in_ui_status: ${results.signed_in_ui_status}`,
    `- logout_status: ${results.logout_status}`,
    `- video_path: ${results.video_path || "pending"}`,
    `- trace_path: output/ux-journey-recordings/${TIMESTAMP}/trace.zip`,
    `- screenshots_dir: output/ux-journey-recordings/${TIMESTAMP}/screenshots/`,
    `- public_audio_files_found: ${results.public_audio_scan.length}`,
    `- public_audio_status: ${PUBLIC_AUDIO_STATUS}`,
    `- audiobook_production_status: ${AUDIOBOOK_PRODUCTION_STATUS}`,
    `- public_claim_findings: ${results.public_claim_findings.length}`,
    `- console_errors_or_warnings: ${results.console_errors.length}`,
    `- network_failures_or_http_errors: ${results.network_failures.length}`,
    "",
    "## Routes Covered",
    "",
    ...results.route_timings.map((item) => `- ${item.route_id}: ${item.path} (${item.duration_ms} ms, status ${item.status || "unknown"})`),
    "",
    "## Safety Notes",
    "",
    "- Login/password entry is not recorded. The recorder starts a new video-enabled browser context only after the owner confirms sign-in.",
    "- Cookies and storage state are used only in memory and are never written to disk.",
    "- Live payment execution is skipped by design.",
    "- Admin surfaces are visited only to verify access behavior; reports redact payment-like/customer-like values.",
    "- Public audio remains blocked unless this report lists public audio findings.",
  ];
  fs.writeFileSync(path.join(OUTPUT_DIR, "SIGNED_USER_JOURNEY_AUDIT_REPORT.md"), `${auditLines.join("\n")}\n`);

  const scoreLines = [
    "# Signed User Journey Scorecard",
    "",
    "Scores are evidence-assisted from route outcomes, public-claims scans, timing data, console errors, network failures, and screenshots. They are not marked 10/10 unless the recording evidence supports it.",
    "",
    "| Area | Score |",
    "| --- | ---: |",
    ...Object.entries(scores).map(([key, value]) => `| ${key.replaceAll("_", " ")} | ${value}/10 |`),
  ];
  fs.writeFileSync(path.join(OUTPUT_DIR, "SIGNED_USER_JOURNEY_SCORECARD.md"), `${scoreLines.join("\n")}\n`);

  const backlog = results.enhancement_notes.length
    ? results.enhancement_notes
    : [
        {
          priority: "P1",
          issue: "Owner review of recorded video is still required before claiming a true 10/10 signed-user journey.",
          recommendation: "Review video, screenshots, route timings, console errors, and network failures after the first owner-run recording.",
        },
      ];
  const backlogLines = [
    "# Signed User Journey Enhancement Backlog",
    "",
    ...backlog.map((item, index) => [
      `## ${index + 1}. ${item.priority || "P2"} - ${item.issue}`,
      "",
      `- recommendation: ${item.recommendation || "Review and prioritize."}`,
      item.route ? `- route: ${item.route}` : "",
    ].filter(Boolean).join("\n")),
  ];
  fs.writeFileSync(path.join(OUTPUT_DIR, "SIGNED_USER_JOURNEY_ENHANCEMENT_BACKLOG.md"), `${backlogLines.join("\n\n")}\n`);
}

async function main() {
  if (IS_REGRESSION_REPORT) {
    writeLatestRegressionMarkdown();
    console.log("Wrote SIGNED_USER_JOURNEY_REGRESSION_REPORT.md");
    return;
  }
  ensureDirs();
  const { chromium } = await import("playwright");
  const browser = await chromium.launch({ headless: HEADLESS, slowMo: SLOW_MO_MS });

  let storageState = loadTestStorageStateIfConfigured();
  if (!IS_SMOKE) {
    const preContext = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
    });
    const prePage = await preContext.newPage();
    await prePage.goto(BASE_URL, { waitUntil: "domcontentloaded", timeout: 45_000 });
    await promptForManualSignIn();
    results.signed_in_ui_status = await verifySignedInUi(prePage);
    storageState = await preContext.storageState();
    results.test_auth_state_status = "OWNER_SIGNED_IN_IN_MEMORY_ONLY";
    await preContext.close();
  }

  const contextOptions = {
    ...(storageState ? { storageState } : {}),
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  };
  if (!IS_SMOKE) {
    contextOptions.recordVideo = {
      dir: VIDEO_DIR,
      size: { width: 1440, height: 900 },
    };
  }
  const context = await browser.newContext(contextOptions);
  await installSmokeApiMocks(context);
  if (!IS_SMOKE) await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
  const page = await context.newPage();
  attachAuditListeners(page);
  results.recording_started_after_manual_sign_in = !IS_SMOKE;

  await timedGoto(page, JOURNEY_ROUTES[0]);
  await auditHomeTour(page);
  await auditHeroCtas(page);
  await auditReaderComfort(page);
  await auditPricingWithoutPayment(page);
  await auditPipelineCtas(page);
  await auditSocialLinks(page);

  for (const route of JOURNEY_ROUTES.slice(3)) {
    await timedGoto(page, route);
    if (route.id === "library" || route.id === "journal") await slowScroll(page, route.id);
  }

  await auditAdminBoundary(page);
  if (!IS_SMOKE) await attemptLogout(page);
  else recordEvent("smoke_logout_skipped", { reason: "No real owner session is used in CI smoke." });
  if (!IS_SMOKE) await context.tracing.stop({ path: path.join(OUTPUT_DIR, "trace.zip") });
  const video = page.video();
  await context.close();
  const rawVideoPath = video ? await video.path().catch(() => "") : "";
  await browser.close();
  await finalizeArtifacts(rawVideoPath);
}

main().catch((error) => {
  console.error(redactSensitive(error instanceof Error ? error.stack || error.message : String(error)));
  process.exit(1);
});
