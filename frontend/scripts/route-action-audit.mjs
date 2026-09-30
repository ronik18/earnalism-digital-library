#!/usr/bin/env node

import { chromium } from "playwright";
import { existsSync } from "node:fs";
import { readFileSync } from "node:fs";

const baseUrl = (process.argv[2] || "https://theearnalism.com").replace(/\/$/, "");
const baseOrigin = new URL(baseUrl).origin;
const blockExternalOrigins = process.env.AUDIT_BLOCK_EXTERNAL === "1";
const useVercelOidc = process.env.AUDIT_USE_VERCEL_OIDC === "1";
const vercelOidcToken = useVercelOidc ? process.env.VERCEL_OIDC_TOKEN : "";
const useVercelProtectionBypass = process.env.AUDIT_USE_VERCEL_PROTECTION_BYPASS === "1";
const vercelProtectionBypass = useVercelProtectionBypass ? process.env.VERCEL_PROTECTION_BYPASS : "";
if (useVercelOidc && !vercelOidcToken) throw new Error("AUDIT_USE_VERCEL_OIDC requires a VERCEL_OIDC_TOKEN from the authenticated Vercel CLI.");
if (useVercelOidc && !new URL(baseUrl).hostname.endsWith(".vercel.app")) throw new Error("OIDC audit headers are restricted to an exact Vercel deployment URL.");
if (useVercelProtectionBypass && !vercelProtectionBypass) throw new Error("AUDIT_USE_VERCEL_PROTECTION_BYPASS requires the VERCEL_PROTECTION_BYPASS environment variable.");
if (useVercelProtectionBypass && !new URL(baseUrl).hostname.endsWith(".vercel.app")) throw new Error("Vercel protection bypass is restricted to an exact Vercel deployment URL.");
const publicationContract = JSON.parse(readFileSync(new URL("../static-seo/controlled-publication-public.json", import.meta.url), "utf8"));
const canonicalTitleRoutes = (publicationContract.publications || []).flatMap(({ slug }) => [
  `/book/${encodeURIComponent(slug)}`,
  `/book/${encodeURIComponent(slug)}/`,
  `/reader/${encodeURIComponent(slug)}`,
  `/reader/${encodeURIComponent(slug)}/`,
  `/listener/${encodeURIComponent(slug)}`,
  `/listener/${encodeURIComponent(slug)}/`,
  `/reader-legacy/${encodeURIComponent(slug)}`,
  `/listener-legacy/${encodeURIComponent(slug)}`,
]);
const historicalTitleRoutes = [
  "/book/the-selfish-giant",
  "/book/the-selfish-giant/",
  "/reader/the-selfish-giant",
  "/reader/the-selfish-giant/",
  "/listener/the-selfish-giant",
  "/listener/the-selfish-giant/",
  "/book/moby-dick-or-the-whale",
  "/book/moby-dick-or-the-whale/",
  "/reader/moby-dick-or-the-whale",
  "/reader/moby-dick-or-the-whale/",
  "/book/the-count-of-monte-cristo",
  "/book/the-count-of-monte-cristo/",
  "/reader/the-count-of-monte-cristo",
  "/reader/the-count-of-monte-cristo/",
  "/book/dracula/",
  "/reader/dracula/",
  "/listener/dracula/",
];
const routes = [
  "/",
  "/library",
  "/library?language=bn&availability=reader-ready",
  "/library?language=en",
  "/library?availability=approved-audiobook",
  "/library?sort=author",
  "/library?source=reading_invitation",
  "/pricing",
  "/about",
  "/about-legacy",
  "/contact",
  "/contact?interest=route-audit",
  "/contact?intent=reader",
  "/contact?intent=rights",
  "/privacy",
  "/terms",
  "/copyright",
  "/journal",
  "/journal/how-reading-shapes-better-founders",
  "/journal/why-every-small-business-needs-a-story-before-a-strategy",
  "/micro-story",
  "/login",
  "/signup",
  "/signin",
  "/account",
  "/my-library",
  "/publishing",
  "/publishing/route-audit",
  "/book/dracula",
  "/reader/dracula",
  "/listener/dracula",
  ...historicalTitleRoutes,
  "/reader-legacy/dracula",
  "/listener-legacy/dracula",
  "/admin/login",
  "/admin",
  "/admin/launch-monitor",
  "/secure-reader-test",
  "/route-audit-unknown",
  ...canonicalTitleRoutes,
];
const requestedRoutes = process.env.AUDIT_ROUTES?.split(",").map((route) => route.trim()).filter((route) => route.startsWith("/"));
if (requestedRoutes?.some((route) => !routes.includes(route))) throw new Error("AUDIT_ROUTES includes a route outside the explicit audit route list.");
const routesToAudit = requestedRoutes?.length ? routes.filter((route) => requestedRoutes.includes(route)) : routes;
const viewports = [
  { label: "desktop", width: 1440, height: 900 },
  { label: "mobile", width: 390, height: 844 },
];

const systemChrome = process.platform === "darwin"
  ? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  : "";
const executablePath = process.env.CHROME_PATH || (systemChrome && existsSync(systemChrome) ? systemChrome : undefined);
const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
const previewHeaders = useVercelOidc
  ? { "x-vercel-trusted-oidc-idp-token": vercelOidcToken }
  : useVercelProtectionBypass
    ? { "x-vercel-protection-bypass": vercelProtectionBypass }
    : {};
const page = await browser.newPage(Object.keys(previewHeaders).length ? { extraHTTPHeaders: previewHeaders } : {});
const blockedWrites = [];
const blockedExternalRequests = [];
await page.route("**/*", async (route) => {
  const request = route.request();
  const requestUrl = new URL(request.url());
  if (request.method() !== "GET") {
    blockedWrites.push({ method: request.method(), origin: requestUrl.origin, path: requestUrl.pathname });
    return route.abort("blockedbyclient");
  }
  if (blockExternalOrigins && requestUrl.origin !== baseOrigin) {
    blockedExternalRequests.push({ method: request.method(), origin: requestUrl.origin, path: requestUrl.pathname });
    return route.abort("blockedbyclient");
  }
  return route.continue();
});
const report = {
  auditedAt: new Date().toISOString(),
  baseUrl,
  safety: `Read-only GET navigation at desktop and mobile viewports. Forms are not filled or submitted; buttons are not activated.${blockExternalOrigins ? " Non-base origins are blocked." : ""}`,
  titleSlugsFromPublicStaticContract: (publicationContract.publications || []).map(({ slug }) => slug),
  requestedRouteFilter: routesToAudit.length === routes.length ? null : routesToAudit,
  blockedNonGetRequests: blockedWrites,
  blockedExternalRequests,
  routes: [],
  linkedRoutes: [],
};

for (const viewport of viewports) {
  await page.setViewportSize({ width: viewport.width, height: viewport.height });
for (const route of routesToAudit) {
  const apiCalls = new Map();
  const releaseConfig = [];
  const pageErrors = [];
  const requestFailures = [];
  const onRequest = (request) => {
    const url = new URL(request.url());
    if (!url.pathname.startsWith("/api/")) return;
    const key = `${request.method()} ${url.pathname}`;
    apiCalls.set(key, { method: request.method(), path: url.pathname, status: null });
  };
  const onResponse = async (response) => {
    const request = response.request();
    const url = new URL(response.url());
    if (!url.pathname.startsWith("/api/")) return;
    const key = `${request.method()} ${url.pathname}`;
    if (apiCalls.has(key)) apiCalls.set(key, { ...apiCalls.get(key), status: response.status() });
    if (request.method() === "GET" && ["/api/payments/config", "/api/payments/offers"].includes(url.pathname)) {
      const body = await response.json().catch(() => null);
      const config = body?.config || body;
      if (body && typeof body === "object") {
        const safeConfig = {};
        for (const [name, value] of Object.entries(config)) {
          if (!/(configured|mode|enabled|status|provider|environment|currency|checkout)/i.test(name)) continue;
          if (/(key|secret|token|url|id|credential)/i.test(name)) continue;
          if (["string", "boolean", "number"].includes(typeof value)) safeConfig[name] = value;
        }
        releaseConfig.push({ endpoint: url.pathname, ...safeConfig });
      }
    }
  };
  const onPageError = (error) => pageErrors.push(error.message);
  const onRequestFailed = (request) => {
    if (request.method() !== "GET") return;
    requestFailures.push({ method: request.method(), path: new URL(request.url()).pathname, error: request.failure()?.errorText || "request failed" });
  };
  page.on("request", onRequest);
  page.on("response", onResponse);
  page.on("pageerror", onPageError);
  page.on("requestfailed", onRequestFailed);
  let response = null;
  let navigationError = null;
  try {
    response = await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.waitForLoadState("networkidle", { timeout: 1200 }).catch(() => {});
  } catch (error) {
    navigationError = error.message;
  }

  let dom = null;
  if (response) {
    dom = await page.evaluate(() => {
      const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const sameOriginLinks = Array.from(document.querySelectorAll("a[href]"))
        .map((link) => {
          const target = new URL(link.href, location.href);
          if (target.origin !== location.origin) return null;
          return { label: clean(link.innerText || link.getAttribute("aria-label")), path: target.pathname, search: target.search, hash: target.hash };
        })
        .filter(Boolean);
      const forms = Array.from(document.forms).map((form) => ({
        action: new URL(form.action || location.href, location.href).pathname,
        method: (form.method || "get").toUpperCase(),
        fields: Array.from(form.querySelectorAll("input, textarea, select, button[type=submit]"))
          .map((field) => ({ name: field.name || "", type: field.type || field.tagName.toLowerCase(), autocomplete: field.autocomplete || "" })),
      }));
      const buttons = Array.from(document.querySelectorAll("button"))
        .filter((button) => button.getClientRects().length > 0)
        .map((button) => ({
          label: clean(button.innerText || button.getAttribute("aria-label")),
          type: button.type || "button",
          disabled: button.disabled,
          testId: button.getAttribute("data-testid") || "",
        }));
      return {
        title: document.title,
        headings: Array.from(document.querySelectorAll("h1, h2")).slice(0, 12).map((node) => clean(node.innerText)),
        internalLinks: sameOriginLinks,
        forms,
        buttons,
        horizontalOverflow: Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth || 0) > window.innerWidth,
      };
    });
  }

  report.routes.push({ viewport: viewport.label, route, viewportSize: { width: viewport.width, height: viewport.height }, finalUrl: page.url(), status: response?.status() ?? null, navigationError, ...dom, pageErrors, requestFailures, apiCalls: [...apiCalls.values()], runtimePaymentConfig: releaseConfig[0] || null });
  page.off("request", onRequest);
  page.off("response", onResponse);
  page.off("pageerror", onPageError);
  page.off("requestfailed", onRequestFailed);
  }
}

const configProbe = await page.request.get(`${baseUrl}/api/payments/config`, { timeout: 15000 }).catch(() => null);
const configBody = configProbe ? await configProbe.json().catch(() => null) : null;
const safeRuntimeConfig = {};
for (const [name, value] of Object.entries(configBody && typeof configBody === "object" ? (configBody.config || configBody) : {})) {
  if (!/(configured|mode|enabled|status|provider|environment|currency|checkout)/i.test(name)) continue;
  if (/(key|secret|token|url|id|credential)/i.test(name)) continue;
  if (["string", "boolean", "number"].includes(typeof value)) safeRuntimeConfig[name] = value;
}
report.paymentConfigProbe = { method: "GET", path: "/api/payments/config", status: configProbe?.status() ?? null, config: safeRuntimeConfig };

const internalTargets = [...new Set(report.routes.filter((route) => route.viewport === "desktop").flatMap((route) => route.internalLinks || [])
  .map((link) => `${link.path}${link.search || ""}`)
  .filter(Boolean))].slice(0, 100);
const visitedTargets = new Set();
const pendingTargets = [...internalTargets];
while (pendingTargets.length && visitedTargets.size < 100) {
  const route = pendingTargets.shift();
  if (visitedTargets.has(route)) continue;
  visitedTargets.add(route);
  let response = null;
  let navigationError = null;
  try {
    response = await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.waitForLoadState("networkidle", { timeout: 800 }).catch(() => {});
  } catch (error) {
    navigationError = error.message;
  }
  const pageInfo = response ? await page.evaluate(() => {
    const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
    const sameOriginLinks = Array.from(document.querySelectorAll("a[href]"))
      .map((link) => {
        const target = new URL(link.href, location.href);
        return target.origin === location.origin ? `${target.pathname}${target.search}` : null;
      })
      .filter(Boolean);
    return {
      title: document.title,
      heading: clean(document.querySelector("h1")?.innerText || ""),
      discoveredLinks: sameOriginLinks,
    };
  }) : {};
  report.linkedRoutes.push({ route, finalUrl: page.url(), status: response?.status() ?? null, navigationError, ...pageInfo });
  for (const target of pageInfo.discoveredLinks || []) {
    if (!visitedTargets.has(target) && pendingTargets.length < 100) pendingTargets.push(target);
  }
}

await browser.close();
process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
