#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(__filename), "..");
const OUTPUT_DIR = path.join(ROOT, "output", "launch");

const DEFAULT_BASE_URL = "https://theearnalism.com";
const BASE_URL = normalizeBaseUrl(process.env.PRODUCTION_BASE_URL || DEFAULT_BASE_URL);
const API_BASE_URL = process.env.PRODUCTION_API_BASE_URL
  ? normalizeBaseUrl(process.env.PRODUCTION_API_BASE_URL)
  : "";
const TIMEOUT_MS = Number(process.env.POST_DEPLOY_CANARY_TIMEOUT_MS || 10000);
const OPTIONAL_PAYMENT_STATUS_PATH = process.env.PUBLIC_PAYMENT_STATUS_PATH || "";

const AUDIO_EXTENSIONS = [".mp3", ".wav", ".m4a", ".ogg", ".aac"];
const LEGACY_TOMBSTONE_PATHS = [
  "/shop",
  "/product/patterned-wrap-dress",
  "/woocommerce/test",
  "/sample-product/test",
];

const ROUTE_CHECKS = [
  {
    id: "home",
    path: "/",
    expectedStatuses: [200],
    mustContainAny: ["The Earnalism", "Dracula", "Chapter 1"],
  },
  {
    id: "dracula_book",
    path: "/book/dracula",
    expectedStatuses: [200],
    mustContainAny: ["Dracula", "Chapter 1", "reading"],
  },
  {
    id: "dracula_reader",
    path: "/reader/dracula",
    expectedStatuses: [200],
    mustContainAny: ["Dracula", "Chapter 1", "reader"],
  },
  {
    id: "pricing",
    path: "/pricing",
    expectedStatuses: [200],
    mustContainAny: ["pricing", "reading", "wallet", "Razorpay"],
  },
  {
    id: "login",
    path: "/login",
    expectedStatuses: [200],
    mustContainAny: ["login", "sign in", "account"],
  },
  {
    id: "signup",
    path: "/signup",
    expectedStatuses: [200],
    mustContainAny: ["signup", "sign up", "account"],
  },
  {
    id: "account",
    path: "/account",
    expectedStatuses: [200, 302, 401, 403],
    optional: true,
    mustContainAny: ["account", "login", "wallet", "reading"],
  },
  {
    id: "sitemap",
    path: "/sitemap.xml",
    expectedStatuses: [200],
    mustContainAll: ["https://theearnalism.com/book/dracula"],
    mustNotContainAny: ["/audio/", ".mp3", ".wav", ".m4a", ".ogg", ".aac", "/book/kshudhita", "/reader/kshudhita"],
  },
  {
    id: "robots",
    path: "/robots.txt",
    expectedStatuses: [200],
    mustContainAll: ["Disallow: /admin", "Disallow: /api/", "Sitemap:"],
  },
];

const FORBIDDEN_PATTERNS = [
  { label: "Listen Now CTA", pattern: /\bListen Now\b/i },
  { label: "AudioObject metadata", pattern: /\bAudioObject\b/i },
  { label: "public audiobook live claim", pattern: /\b(?:full\s+)?audiobook\s+(?:is\s+|are\s+)?(?:live|available|ready|published)\b/i },
  { label: "Dracula audio live claim", pattern: /\bDracula audio\s+(?:is\s+)?(?:live|available|ready|published)\b/i },
  { label: "audiobook purchase claim", pattern: /\b(?:buy|purchase|get)\s+(?:the\s+)?(?:full\s+)?audiobook\b/i },
  { label: "audiobook pass claim", pattern: /\baudiobook pass\b/i },
  {
    label: "Kshudhita public CTA",
    pattern: /\b(?:Kshudhita|Hungry Stones)\b[\s\S]{0,180}\b(?:Start Reading|Read Preview|Listen Now|public reader|public audio|available now|Buy reading time)\b/i,
  },
  { label: "public audio URL", pattern: /(?:href|src)=["'][^"']*(?:\.mp3|\.wav|\.m4a|\.ogg|\.aac|\/audio\/)[^"']*["']/i },
];

function normalizeBaseUrl(value) {
  try {
    const url = new URL(value);
    return url.origin;
  } catch {
    console.error(`Invalid PRODUCTION_BASE_URL: ${value}`);
    process.exit(2);
  }
}

function joinUrl(baseUrl, routePath) {
  return `${baseUrl}${routePath.startsWith("/") ? routePath : `/${routePath}`}`;
}

async function fetchPublic(routePath, method = "GET", baseUrl = BASE_URL) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(joinUrl(baseUrl, routePath), {
      method,
      redirect: "manual",
      signal: controller.signal,
      headers: {
        accept: "text/html,application/xml,text/plain,*/*",
        "user-agent": "EarnalismReadingOnlyPostDeployCanary/1.0",
      },
    });
    const body = method === "HEAD" ? "" : await response.text();
    return {
      path: routePath,
      url: joinUrl(baseUrl, routePath),
      status: response.status,
      ok: response.ok,
      redirected: response.status >= 300 && response.status < 400,
      location: response.headers.get("location") || "",
      contentType: response.headers.get("content-type") || "",
      body,
      error: "",
    };
  } catch (error) {
    return {
      path: routePath,
      url: joinUrl(baseUrl, routePath),
      status: 0,
      ok: false,
      redirected: false,
      location: "",
      contentType: "",
      body: "",
      error: error instanceof Error ? error.message : String(error),
    };
  } finally {
    clearTimeout(timeout);
  }
}

function bodyHasAny(body, needles) {
  const lowerBody = body.toLowerCase();
  return needles.some((needle) => lowerBody.includes(needle.toLowerCase()));
}

function bodyHasAll(body, needles) {
  const lowerBody = body.toLowerCase();
  return needles.every((needle) => lowerBody.includes(needle.toLowerCase()));
}

function evaluateRoute(check, response) {
  const issues = [];
  if (!check.expectedStatuses.includes(response.status)) {
    if (!(check.optional && response.status === 404)) {
      issues.push(`Expected status ${check.expectedStatuses.join(" or ")}, got ${response.status || "no response"}.`);
    }
  }
  if (response.error) issues.push(response.error);
  if (check.mustContainAll && !bodyHasAll(response.body, check.mustContainAll)) {
    issues.push(`Missing required text: ${check.mustContainAll.join(", ")}.`);
  }
  if (check.mustContainAny && response.status === 200 && !bodyHasAny(response.body, check.mustContainAny)) {
    issues.push(`Missing at least one expected text token: ${check.mustContainAny.join(", ")}.`);
  }
  const forbiddenChecks = [...FORBIDDEN_PATTERNS];
  if (check.mustNotContainAny) {
    for (const token of check.mustNotContainAny) {
      forbiddenChecks.push({ label: `forbidden token ${token}`, pattern: new RegExp(escapeRegExp(token), "i") });
    }
  }
  for (const forbidden of forbiddenChecks) {
    if (forbidden.pattern.test(response.body)) issues.push(`Forbidden public claim or asset detected: ${forbidden.label}.`);
  }
  return {
    ...response,
    id: check.id,
    status: response.status,
    pass: issues.length === 0,
    optional: Boolean(check.optional),
    issues,
  };
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function evaluateLegacyRoute(routePath) {
  const response = await fetchPublic(routePath, "GET");
  const issues = [];
  if (![404, 410].includes(response.status)) {
    issues.push(`Expected legacy route to return 404 or 410, got ${response.status || "no response"}.`);
  }
  if (response.redirected) issues.push(`Unexpected redirect to ${response.location || "(missing Location)"}.`);
  if (/The Earnalism Digital Library/i.test(response.body) && !/no longer available|not found|410|404/i.test(response.body)) {
    issues.push("Legacy route appears to serve a generic public app shell.");
  }
  return {
    ...response,
    id: `legacy_${routePath.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "")}`,
    pass: issues.length === 0,
    optional: false,
    issues,
  };
}

async function evaluatePaymentStatusIfConfigured() {
  if (!OPTIONAL_PAYMENT_STATUS_PATH) {
    return {
      id: "razorpay_public_status_optional",
      path: "",
      url: "",
      status: 0,
      ok: true,
      redirected: false,
      location: "",
      contentType: "",
      body: "",
      error: "",
      pass: true,
      optional: true,
      skipped: true,
      issues: ["Skipped because PUBLIC_PAYMENT_STATUS_PATH is not configured."],
    };
  }
  const response = await fetchPublic(OPTIONAL_PAYMENT_STATUS_PATH, "GET");
  const issues = [];
  if (response.status >= 500 || response.status === 0) issues.push(`Payment status endpoint returned ${response.status || "no response"}.`);
  for (const forbidden of FORBIDDEN_PATTERNS) {
    if (forbidden.pattern.test(response.body)) issues.push(`Forbidden public claim detected in payment status response: ${forbidden.label}.`);
  }
  if (/rzp_(?:live|test)_|RAZORPAY_KEY_SECRET|RAZORPAY_WEBHOOK_SECRET|WEBHOOK_SECRET|pay_[A-Za-z0-9]{8,}|order_[A-Za-z0-9]{8,}/i.test(response.body)) {
    issues.push("Payment status response appears to expose a secret or raw payment identifier.");
  }
  return {
    ...response,
    id: "razorpay_public_status_optional",
    pass: issues.length === 0,
    optional: true,
    skipped: false,
    issues,
  };
}

async function evaluateAdminLaunchMonitorApiGuard() {
  const adminSummaryPath = "/api/admin/launch-monitor/summary";
  if (!API_BASE_URL) {
    return {
      id: "admin_launch_monitor_api_auth_guard",
      path: adminSummaryPath,
      url: "",
      status: 0,
      ok: true,
      redirected: false,
      location: "",
      contentType: "",
      body: "",
      error: "",
      pass: true,
      optional: true,
      skipped: true,
      issues: [
        "Skipped because PRODUCTION_API_BASE_URL is not configured. Before deploying the dashboard, run this canary with the production backend origin and manually verify /admin/launch-monitor blocks non-admin users.",
      ],
    };
  }

  const response = await fetchPublic(adminSummaryPath, "GET", API_BASE_URL);
  const issues = [];
  if (![401, 403].includes(response.status)) {
    issues.push(`Expected unauthenticated admin summary to return 401 or 403, got ${response.status || "no response"}. A 404 means the dashboard API is not deployed or PRODUCTION_API_BASE_URL is wrong.`);
  }
  if (/dashboard_status|funnel|payment_success_count|wallet_credit_count|webhook_received_count|OWNER_ADMIN_ONLY/i.test(response.body)) {
    issues.push("Unauthenticated admin summary response appears to expose dashboard data.");
  }
  if (/rzp_(?:live|test)_|RAZORPAY_KEY_SECRET|RAZORPAY_WEBHOOK_SECRET|WEBHOOK_SECRET|pay_[A-Za-z0-9]{8,}|order_[A-Za-z0-9]{8,}|customer_email|customer_phone/i.test(response.body)) {
    issues.push("Unauthenticated admin summary response appears to expose payment/customer data or secrets.");
  }
  return {
    ...response,
    id: "admin_launch_monitor_api_auth_guard",
    pass: issues.length === 0,
    optional: false,
    skipped: false,
    issues,
  };
}

function scanLocalPublicAudio() {
  const roots = ["frontend/public", "frontend/build"].map((relativePath) => path.join(ROOT, relativePath));
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

function writeReports(payload) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.writeFileSync(
    path.join(OUTPUT_DIR, "post_deploy_reading_canary.json"),
    `${JSON.stringify(payload, null, 2)}\n`,
    "utf8",
  );
  const lines = [
    "# Post-Deploy Reading-Only Canary",
    "",
    `Status: \`${payload.status}\``,
    "",
    `Base URL: ${payload.base_url}`,
    "",
    "| Check | Path | Status | Decision | Issues |",
    "| --- | --- | ---: | --- | --- |",
    ...payload.results.map((result) => (
      `| ${result.id} | ${result.path || "(optional)"} | ${result.status || "SKIP"} | ${result.pass ? "PASS" : "FAIL"} | ${result.issues.join("; ")} |`
    )),
    "",
    `Local public audio files: ${payload.local_public_audio_files.length ? payload.local_public_audio_files.join(", ") : "none"}`,
    "",
    "Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
    "Audiobook production: `PRODUCTION_BLOCKED`",
    "Launch completion: do not mark complete until this report is `PASS`.",
    "",
  ];
  fs.writeFileSync(path.join(OUTPUT_DIR, "post_deploy_reading_canary.md"), `${lines.join("\n")}`, "utf8");
}

const routeResults = [];
for (const check of ROUTE_CHECKS) {
  const response = await fetchPublic(check.path, "GET");
  routeResults.push(evaluateRoute(check, response));
}
for (const routePath of LEGACY_TOMBSTONE_PATHS) {
  routeResults.push(await evaluateLegacyRoute(routePath));
}
routeResults.push(await evaluatePaymentStatusIfConfigured());
routeResults.push(await evaluateAdminLaunchMonitorApiGuard());

const localPublicAudioFiles = scanLocalPublicAudio();
const status = routeResults.every((result) => result.pass) && localPublicAudioFiles.length === 0 ? "PASS" : "BLOCKED";
const payload = {
  generated_at: new Date().toISOString(),
  status,
  base_url: BASE_URL,
  mutation_free: true,
  secrets_required: false,
  live_payment_executed: false,
  public_audio_release: "PUBLIC_AUDIO_RELEASE_BLOCKED",
  audiobook_production: "PRODUCTION_BLOCKED",
  results: routeResults,
  local_public_audio_files: localPublicAudioFiles,
};

writeReports(payload);

if (status !== "PASS") {
  console.error("Post-deploy reading-only canary BLOCKED. See output/launch/post_deploy_reading_canary.md.");
  process.exit(1);
}

console.log("Post-deploy reading-only canary PASS.");
