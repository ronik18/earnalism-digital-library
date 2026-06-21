#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");

const DEFAULT_FRONTEND_URL = "https://theearnalism.com";
const DEFAULT_API_URL = "https://api.theearnalism.com/api";
const DEFAULT_OUTPUT_DIR = path.join(ROOT, "output", "catalog_audit");
const DEFAULT_TIMEOUT_MS = 10_000;
const FRONTEND_PUBLIC_DIR = path.join(ROOT, "frontend", "public");
const RIGHTS_REQUIRED_REASON = "Rights metadata is missing or not exposed; Phase 2 rights verification required.";

export const ACTIONS = ["KEEP", "REWRITE", "NOINDEX", "QUARANTINE", "ARCHIVE", "DELETE"];

export const BLOCKED_PREFIXES = [
  "/apparel",
  "/blog",
  "/cart",
  "/category",
  "/checkout",
  "/clothing",
  "/fashion",
  "/my-account",
  "/post",
  "/product",
  "/products",
  "/product-category",
  "/sample-product",
  "/shop",
  "/tag",
  "/tag/apparel",
  "/tag/clothing",
  "/tag/fashion",
  "/woocommerce",
  "/wp-admin",
  "/wp-content",
  "/wp-json",
];

export const BLOCKED_TERMS = [
  "add-to-cart",
  "apparel",
  "bookstore",
  "clothing",
  "denim-jacket",
  "denim-jackets",
  "fashion",
  "lorem-ipsum",
  "my-account",
  "patterned-wrap-dress",
  "placeholder-product",
  "sample-product",
  "woocommerce",
  "wp-admin",
  "wp-content",
  "wp-json",
];

export const CORE_ROUTES = [
  { path: "/", title: "Earnalism", content_type: "homepage", public_status: "public" },
  { path: "/library", title: "Library", content_type: "library", public_status: "public" },
  { path: "/journal", title: "Journal", content_type: "journal_index", public_status: "public" },
  { path: "/about", title: "About", content_type: "about_page", public_status: "public" },
  { path: "/contact", title: "Contact", content_type: "contact_page", public_status: "public" },
  { path: "/pricing", title: "Pricing", content_type: "pricing_page", public_status: "public" },
  { path: "/micro-story", title: "Micro Story", content_type: "campaign_page", public_status: "public" },
  { path: "/login", title: "Login", content_type: "auth_page", public_status: "restricted" },
  { path: "/signup", title: "Signup", content_type: "auth_page", public_status: "restricted" },
  { path: "/account", title: "Account", content_type: "account_page", public_status: "restricted" },
  { path: "/robots.txt", title: "robots.txt", content_type: "robots_document", public_status: "document" },
  { path: "/sitemap.xml", title: "sitemap.xml", content_type: "sitemap_document", public_status: "document" },
];

export const KNOWN_REMOVED_URLS = [
  "/product/patterned-wrap-dress",
  "/products/patterned-wrap-dress",
  "/shop/patterned-wrap-dress",
  "/journal/denim-jackets",
  "/journal/the-quiet-power-of-a-premium-bookstore-brand",
  "/blog/denim-jackets",
  "/blog/lorem-ipsum",
  "/post/sample-product",
  "/denim-jackets",
  "/fashion",
  "/clothing",
  "/apparel",
  "/product-category/clothing",
  "/tag/fashion",
  "/tag/bookstore",
  "/category/fashion",
  "/woocommerce",
  "/cart",
  "/checkout",
  "/my-account",
];

const AUDIO_SUFFIXES = [
  "_highlight.vtt",
  "_timestamps.json",
  "_meta.json",
  "_chapters.json",
  ".mp3",
];

const CTA_ASSUMED_YES_TYPES = new Set([
  "homepage",
  "library",
  "library_category",
  "book_page",
  "pricing_page",
  "campaign_page",
]);

const CTA_ASSUMED_NO_TYPES = new Set([
  "journal_index",
  "journal_page",
  "about_page",
  "contact_page",
  "audio_asset",
  "book_asset",
]);

function sourceStatusBase(overrides = {}) {
  return {
    ok: false,
    status: "unavailable",
    cached: false,
    error: null,
    item_count: 0,
    degraded_reason: null,
    ...overrides,
  };
}

export function argValue(name, fallback = null) {
  const index = process.argv.indexOf(name);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return process.env[name.replace(/^--/, "").replace(/-/g, "_").toUpperCase()] || fallback;
}

function resolvePathMaybe(value, baseDir = ROOT) {
  if (!value) return null;
  return path.isAbsolute(value) ? value : path.resolve(baseDir, value);
}

export function normalizeBase(value) {
  return String(value || "").replace(/\/+$/, "");
}

export function csvEscape(value) {
  if (Array.isArray(value)) {
    return csvEscape(value.join("; "));
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function extractLocs(xml) {
  return [...String(xml || "").matchAll(/<loc>([^<]+)<\/loc>/gi)].map((match) => match[1].trim());
}

export function normalizeRouteKey(value, frontendUrl = DEFAULT_FRONTEND_URL) {
  try {
    const url = new URL(String(value || "/"), `${normalizeBase(frontendUrl) || DEFAULT_FRONTEND_URL}/`);
    const pathname = url.pathname || "/";
    const normalizedPath = pathname === "/" ? "/" : pathname.replace(/\/+$/, "");
    return `${normalizedPath}${url.search}`;
  } catch {
    return "/";
  }
}

export function routePath(routeKey = "/") {
  return String(routeKey || "/").split("?")[0] || "/";
}

export function routeType(routeKey = "/") {
  const pagePath = routePath(routeKey);
  if (routeKey === "/") return "homepage";
  if (pagePath === "/library" && routeKey.includes("?category=")) return "library_category";
  if (pagePath === "/library") return "library";
  if (pagePath.startsWith("/book/")) return "book_page";
  if (pagePath === "/journal") return "journal_index";
  if (pagePath.startsWith("/journal/")) return "journal_page";
  if (pagePath.startsWith("/reader/")) return "reader_page";
  if (pagePath === "/pricing") return "pricing_page";
  if (pagePath === "/about") return "about_page";
  if (pagePath === "/contact") return "contact_page";
  if (pagePath === "/login" || pagePath === "/signup") return "auth_page";
  if (pagePath === "/account") return "account_page";
  if (pagePath === "/micro-story") return "campaign_page";
  if (pagePath === "/robots.txt") return "robots_document";
  if (pagePath === "/sitemap.xml") return "sitemap_document";
  return "unknown_public_url";
}

export function isBlockedPath(routeKey = "") {
  const lowered = normalizeRouteKey(routeKey).toLowerCase();
  return (
    BLOCKED_PREFIXES.some((prefix) => lowered === prefix || lowered.startsWith(`${prefix}/`))
    || BLOCKED_TERMS.some((term) => lowered.includes(term))
  );
}

export function parseRobots(text = "") {
  const disallowRules = [];
  const allowRules = [];

  for (const rawLine of String(text || "").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    if (line.toLowerCase().startsWith("disallow:")) {
      const value = line.slice("disallow:".length).trim();
      if (value) disallowRules.push(value);
    }

    if (line.toLowerCase().startsWith("allow:")) {
      const value = line.slice("allow:".length).trim();
      if (value) allowRules.push(value);
    }
  }

  return { disallowRules, allowRules };
}

export function isRobotsDisallowed(routeKey, robotsRules) {
  const pagePath = routePath(routeKey).toLowerCase();
  const rules = Array.isArray(robotsRules?.disallowRules) ? robotsRules.disallowRules : [];

  return rules.some((rule) => {
    const normalizedRule = String(rule || "").trim().toLowerCase();
    if (!normalizedRule || normalizedRule === "/") return true;

    if (normalizedRule.endsWith("/")) {
      const prefix = normalizedRule.slice(0, -1);
      return pagePath === prefix || pagePath.startsWith(`${prefix}/`);
    }

    return pagePath === normalizedRule || pagePath.startsWith(`${normalizedRule}/`);
  });
}

export function robotsStatusForRoute(routeKey, robotsRules) {
  const type = routeType(routeKey);
  if (type === "robots_document") return "document";
  return isRobotsDisallowed(routeKey, robotsRules) ? "disallowed" : "allowed";
}

export function rightsMetadataStatus(record) {
  if (!record || typeof record !== "object" || !Object.prototype.hasOwnProperty.call(record, "rights_metadata")) {
    return "unknown";
  }
  if (record.rights_metadata && typeof record.rights_metadata === "object") {
    return Object.keys(record.rights_metadata).length > 0 ? "yes" : "no";
  }
  return "no";
}

export function ctaStatus(item) {
  const type = item.content_type || routeType(item.path);
  if (CTA_ASSUMED_YES_TYPES.has(type)) return "assumed_yes";
  if (CTA_ASSUMED_NO_TYPES.has(type)) return "assumed_no";
  return "not_applicable";
}

function needsRightsQuarantine(item) {
  if (!["unknown", "no"].includes(item.rights_metadata_present)) return false;

  if (item.content_type === "book_page") return true;
  if (item.content_type === "reader_page") return true;
  if (item.content_type === "audio_asset" && item.related_slug) return true;
  if (item.content_type === "book_asset" && item.related_slug) return true;

  return false;
}

export function growthRelevanceScore(item) {
  if (item.public_status === "removed") return 0;
  if (item.public_status === "orphaned_asset") return 12;

  switch (item.content_type) {
    case "homepage":
      return 100;
    case "pricing_page":
      return 98;
    case "library":
      return 96;
    case "library_category":
      return 92;
    case "book_page":
      return item.audiobook_enabled ? 93 : 89;
    case "reader_page":
      return 84;
    case "journal_index":
      return 80;
    case "journal_page":
      return 76;
    case "campaign_page":
      return 72;
    case "about_page":
    case "contact_page":
      return 68;
    case "audio_asset":
      return item.asset_health === "complete" ? 67 : 48;
    case "book_asset":
      return item.public_status === "public_asset" ? 58 : 16;
    case "robots_document":
    case "sitemap_document":
      return 55;
    case "auth_page":
    case "account_page":
      return 26;
    case "removed_demo_or_ecommerce":
      return 0;
    default:
      return 35;
  }
}

export function recommendedAction(item) {
  if (item.public_status === "removed" || item.content_type === "removed_demo_or_ecommerce" || isBlockedPath(item.path)) {
    return "DELETE";
  }

  if (needsRightsQuarantine(item)) {
    return "QUARANTINE";
  }

  if (item.public_status === "orphaned_asset") {
    return "ARCHIVE";
  }

  if (item.content_type === "auth_page" || item.content_type === "account_page") {
    return "NOINDEX";
  }

  if (item.content_type === "reader_page") {
    return "NOINDEX";
  }

  if (item.content_type === "journal_page" && item.cta_present === "assumed_no") {
    return "REWRITE";
  }

  if ((item.content_type === "audio_asset" || item.content_type === "book_asset") && item.asset_health === "incomplete") {
    return "REWRITE";
  }

  if (item.content_type === "unknown_public_url") {
    return item.robots_status === "disallowed" ? "NOINDEX" : "QUARANTINE";
  }

  if (item.growth_relevance_score >= 85) return "KEEP";
  if (item.growth_relevance_score >= 50) return "REWRITE";
  return "NOINDEX";
}

export function buildReason(item) {
  const reasons = [];

  if (item.public_status === "removed") {
    reasons.push("Legacy demo or ecommerce residue kept only for dry-run governance tracking.");
  }

  if (needsRightsQuarantine(item)) {
    reasons.push(RIGHTS_REQUIRED_REASON);
  }

  if (item.public_status === "orphaned_asset") {
    reasons.push("Public asset does not map to a published book or current audio asset slug.");
  }

  if (item.content_type === "reader_page") {
    reasons.push("Reader route is intentionally gated and disallowed by robots.");
  }

  if (item.content_type === "auth_page" || item.content_type === "account_page") {
    reasons.push("Authentication and account surfaces should stay out of search results.");
  }

  if (item.content_type === "journal_page" && item.cta_present === "assumed_no") {
    reasons.push("Editorial content is live but the CTA status is only inferred, not verified from rendered HTML.");
  }

  if ((item.content_type === "audio_asset" || item.content_type === "book_asset") && item.asset_health === "incomplete") {
    reasons.push("Supporting public asset bundle is incomplete.");
  }

  if (item.content_type === "journal_page" && item.rights_metadata_present === "unknown") {
    reasons.push("Rights metadata is not exposed for public editorial records.");
  }

  if (item.sitemap_status === "excluded" && item.robots_status === "allowed" && item.public_status === "public") {
    reasons.push("URL is publicly reachable but intentionally omitted from sitemap.");
  }

  if (item.robots_status === "disallowed" && item.sitemap_status === "included") {
    reasons.push("Robots and sitemap signals disagree and should be reconciled.");
  }

  if (item.source_warnings?.length) {
    reasons.push(`Source warnings: ${item.source_warnings.join(" | ")}`);
  }

  if (!reasons.length) {
    reasons.push("Aligned with current public catalog governance policy.");
  }

  return reasons.join(" ");
}

async function readTextFileSafe(filePath) {
  try {
    return await fs.readFile(filePath, "utf8");
  } catch {
    return null;
  }
}

async function readCacheValue(cacheDir, cacheName) {
  if (!cacheDir || !cacheName) return null;
  return readTextFileSafe(path.join(cacheDir, cacheName));
}

async function fetchRemoteText(url, timeoutMs) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(new Error(`Timed out after ${timeoutMs}ms`)), timeoutMs);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        Accept: "*/*",
        "User-Agent": "EarnalismCatalogAudit/2.1",
      },
    });
    const text = await response.text();
    return { ok: response.ok, status: response.status, text, error: response.ok ? null : `HTTP ${response.status}` };
  } catch (error) {
    const message = error?.name === "AbortError" ? `Timed out after ${timeoutMs}ms` : error.message;
    return { ok: false, status: 0, text: "", error: message };
  } finally {
    clearTimeout(timeout);
  }
}

function validateSitemapText(text) {
  const locs = extractLocs(text);
  if (!String(text).includes("<urlset") || locs.length === 0) {
    return {
      ok: false,
      item_count: locs.length,
      error: "Invalid or empty sitemap XML.",
    };
  }
  return { ok: true, item_count: locs.length };
}

function validateRobotsText(text) {
  const robots = parseRobots(text);
  const rulesCount = robots.allowRules.length + robots.disallowRules.length;
  if (!/User-agent:/i.test(String(text))) {
    return {
      ok: false,
      item_count: rulesCount,
      error: "robots.txt does not contain a User-agent directive.",
    };
  }
  return { ok: true, item_count: rulesCount };
}

function validateJsonArrayText(text, label) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    return {
      ok: false,
      item_count: 0,
      error: `${label} is not valid JSON: ${error.message}`,
    };
  }

  if (!Array.isArray(parsed)) {
    return {
      ok: false,
      item_count: 0,
      error: `${label} must be a JSON array.`,
    };
  }

  return {
    ok: true,
    item_count: parsed.length,
    data: parsed,
  };
}

function finalizeSourceFailure(sourceKey, error, required = false) {
  const degradedReason = required
    ? `${sourceKey} is unavailable and no valid fixture/cache was found.`
    : `${sourceKey} is unavailable; this portion of the audit is incomplete.`;

  return sourceStatusBase({
    ok: false,
    status: "unavailable",
    cached: false,
    error,
    item_count: 0,
    degraded_reason: degradedReason,
  });
}

async function loadTextSource({
  sourceKey,
  url,
  cacheDir,
  cacheName,
  fixtureDir,
  fixtureFile,
  timeoutMs,
  validate,
  required = false,
}) {
  if (fixtureDir) {
    const fixturePath = path.join(fixtureDir, fixtureFile);
    const text = await readTextFileSafe(fixturePath);
    if (text == null) {
      return {
        text: "",
        sourceStatus: finalizeSourceFailure(sourceKey, `Fixture file missing: ${fixturePath}`, required),
      };
    }

    const validation = validate(text);
    if (!validation.ok) {
      return {
        text: "",
        sourceStatus: finalizeSourceFailure(sourceKey, validation.error, required),
      };
    }

    return {
      text,
      sourceStatus: sourceStatusBase({
        ok: true,
        status: "fixture",
        cached: false,
        error: null,
        item_count: validation.item_count,
        degraded_reason: null,
      }),
    };
  }

  await fs.mkdir(cacheDir, { recursive: true });
  const cachePath = path.join(cacheDir, cacheName);
  const remote = await fetchRemoteText(url, timeoutMs);

  if (remote.ok) {
    const validation = validate(remote.text);
    if (validation.ok) {
      await fs.writeFile(cachePath, remote.text, "utf8");
      return {
        text: remote.text,
        sourceStatus: sourceStatusBase({
          ok: true,
          status: remote.status,
          cached: false,
          error: null,
          item_count: validation.item_count,
          degraded_reason: null,
        }),
      };
    }
  }

  const cachedText = await readCacheValue(cacheDir, cacheName);
  if (cachedText != null) {
    const cachedValidation = validate(cachedText);
    if (cachedValidation.ok) {
      return {
        text: cachedText,
        sourceStatus: sourceStatusBase({
          ok: true,
          status: "cached",
          cached: true,
          error: remote.error || (remote.ok ? "Remote response was invalid." : null),
          item_count: cachedValidation.item_count,
          degraded_reason: null,
        }),
      };
    }
  }

  const validationError = remote.ok ? validate(remote.text).error : remote.error;
  return {
    text: "",
    sourceStatus: finalizeSourceFailure(sourceKey, validationError || "Unknown source failure.", required),
  };
}

async function loadJsonArraySource(options) {
  const result = await loadTextSource({
    ...options,
    validate: (text) => validateJsonArrayText(text, options.sourceKey),
  });

  if (!result.sourceStatus.ok) {
    return {
      data: [],
      sourceStatus: result.sourceStatus,
    };
  }

  const validation = validateJsonArrayText(result.text, options.sourceKey);
  if (!validation.ok) {
    return {
      data: [],
      sourceStatus: finalizeSourceFailure(options.sourceKey, validation.error, options.required),
    };
  }

  return {
    data: validation.data,
    sourceStatus: sourceStatusBase({
      ...result.sourceStatus,
      item_count: validation.item_count,
    }),
  };
}

async function listFilesRecursive(dir) {
  const out = [];
  try {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const resolved = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        out.push(...await listFilesRecursive(resolved));
      } else {
        out.push(resolved);
      }
    }
  } catch {
    return [];
  }
  return out;
}

function audioBundleKey(fileName) {
  for (const suffix of AUDIO_SUFFIXES) {
    if (fileName.endsWith(suffix)) return fileName.slice(0, -suffix.length);
  }
  return path.parse(fileName).name;
}

function buildAudioAssetHealth(bundle) {
  return bundle.hasMp3 && bundle.hasMeta && (bundle.hasTimestamps || bundle.hasHighlight) ? "complete" : "incomplete";
}

function buildAudioRowsFromManifest(frontendUrl, manifest, booksBySlug, booksByAudioAssetSlug) {
  return manifest.map((entry) => {
    const bundleName = entry.bundle_name || path.basename(entry.path || "", path.extname(entry.path || "")) || entry.related_slug || "";
    const mappedBook = booksBySlug.get(entry.related_slug) || booksByAudioAssetSlug.get(bundleName) || null;
    const publicStatus = mappedBook ? "public_asset" : "orphaned_asset";
    return {
      path: normalizeRouteKey(entry.path || `/audio/${entry.language || "unknown"}/${bundleName}.mp3`, frontendUrl),
      url: new URL(entry.path || `/audio/${entry.language || "unknown"}/${bundleName}.mp3`, `${frontendUrl}/`).href,
      title: entry.title || mappedBook?.title || bundleName || "Audio asset",
      content_type: "audio_asset",
      public_status: publicStatus,
      sitemap_status: "excluded",
      robots_status: "allowed",
      rights_metadata_present: mappedBook ? rightsMetadataStatus(mappedBook) : "unknown",
      cta_present: "not_applicable",
      source_sets: ["audio_public_dir"],
      related_slug: mappedBook?.slug || entry.related_slug || bundleName,
      language: entry.language || entry.lang || bundleName.split("/")[0] || "unknown",
      audiobook_enabled: Boolean(mappedBook?.audiobook_enabled),
      asset_health: entry.asset_health || "complete",
      asset_files: Array.isArray(entry.asset_files) ? entry.asset_files : [],
    };
  });
}

function buildBookAssetRowsFromManifest(frontendUrl, manifest, booksBySlug) {
  return manifest.map((entry) => {
    const mappedBook = booksBySlug.get(entry.related_slug) || null;
    const assetPath = entry.path || "/";
    return {
      path: normalizeRouteKey(assetPath, frontendUrl),
      url: new URL(assetPath, `${frontendUrl}/`).href,
      title: entry.title || mappedBook?.title || entry.related_slug || "Book asset",
      content_type: "book_asset",
      public_status: mappedBook ? "public_asset" : "orphaned_asset",
      sitemap_status: "excluded",
      robots_status: "allowed",
      rights_metadata_present: mappedBook ? rightsMetadataStatus(mappedBook) : "unknown",
      cta_present: "not_applicable",
      source_sets: ["book_assets_dir"],
      related_slug: entry.related_slug || mappedBook?.slug || "",
      language: entry.language || "",
      asset_health: entry.asset_health || "incomplete",
      asset_files: Array.isArray(entry.asset_files) ? entry.asset_files : [],
    };
  });
}

async function discoverAudioAssets({ frontendUrl, fixtureDir, booksBySlug, booksByAudioAssetSlug }) {
  if (fixtureDir) {
    const manifestResult = await loadJsonArraySource({
      sourceKey: "audio_public_dir",
      fixtureDir,
      fixtureFile: "audio_assets.json",
      cacheDir: null,
      cacheName: null,
      url: "",
      timeoutMs: 0,
      required: false,
    });
    return {
      rows: buildAudioRowsFromManifest(frontendUrl, manifestResult.data, booksBySlug, booksByAudioAssetSlug),
      sourceStatus: manifestResult.sourceStatus,
    };
  }

  const audioRoot = path.join(FRONTEND_PUBLIC_DIR, "audio");
  try {
    const files = await listFilesRecursive(audioRoot);
    const bundles = new Map();

    for (const absolutePath of files) {
      const relative = path.relative(audioRoot, absolutePath);
      const [language = "unknown", fileName = ""] = relative.split(path.sep);
      if (!fileName) continue;

      const bundleName = audioBundleKey(fileName);
      const bundleId = `${language}/${bundleName}`;
      const bundle = bundles.get(bundleId) || {
        path: `/audio/${language}/${bundleName}.mp3`,
        language,
        bundle_name: bundleName,
        files: [],
        hasMp3: false,
        hasMeta: false,
        hasTimestamps: false,
        hasHighlight: false,
        hasChapters: false,
      };

      bundle.files.push(fileName);
      bundle.hasMp3 ||= fileName.endsWith(".mp3");
      bundle.hasMeta ||= fileName.endsWith("_meta.json");
      bundle.hasTimestamps ||= fileName.endsWith("_timestamps.json");
      bundle.hasHighlight ||= fileName.endsWith("_highlight.vtt");
      bundle.hasChapters ||= fileName.endsWith("_chapters.json");
      bundles.set(bundleId, bundle);
    }

    const rows = [];
    for (const bundle of bundles.values()) {
      const mappedBook = booksBySlug.get(bundle.bundle_name) || booksByAudioAssetSlug.get(bundle.bundle_name) || null;
      const publicStatus = mappedBook ? "public_asset" : "orphaned_asset";
      rows.push({
        path: normalizeRouteKey(bundle.path, frontendUrl),
        url: new URL(bundle.path, `${frontendUrl}/`).href,
        title: mappedBook?.title || bundle.bundle_name,
        content_type: "audio_asset",
        public_status: publicStatus,
        sitemap_status: "excluded",
        robots_status: "allowed",
        rights_metadata_present: mappedBook ? rightsMetadataStatus(mappedBook) : "unknown",
        cta_present: "not_applicable",
        source_sets: ["audio_public_dir"],
        related_slug: mappedBook?.slug || bundle.bundle_name,
        language: bundle.language,
        audiobook_enabled: Boolean(mappedBook?.audiobook_enabled),
        asset_health: buildAudioAssetHealth(bundle),
        asset_files: bundle.files.sort(),
      });
    }

    return {
      rows: rows.sort((a, b) => a.path.localeCompare(b.path)),
      sourceStatus: sourceStatusBase({
        ok: true,
        status: "filesystem",
        cached: false,
        error: null,
        item_count: rows.length,
        degraded_reason: null,
      }),
    };
  } catch (error) {
    return {
      rows: [],
      sourceStatus: finalizeSourceFailure("audio_public_dir", error.message, false),
    };
  }
}

async function discoverBookAssets({ frontendUrl, fixtureDir, booksBySlug }) {
  if (fixtureDir) {
    const manifestResult = await loadJsonArraySource({
      sourceKey: "book_assets_dir",
      fixtureDir,
      fixtureFile: "book_assets.json",
      cacheDir: null,
      cacheName: null,
      url: "",
      timeoutMs: 0,
      required: false,
    });
    return {
      rows: buildBookAssetRowsFromManifest(frontendUrl, manifestResult.data, booksBySlug),
      sourceStatus: manifestResult.sourceStatus,
    };
  }

  const booksRoot = path.join(FRONTEND_PUBLIC_DIR, "assets", "books");
  try {
    const entries = await fs.readdir(booksRoot, { withFileTypes: true });
    const rows = [];

    for (const entry of entries) {
      if (!entry.isDirectory()) continue;

      const slug = entry.name;
      const dirPath = path.join(booksRoot, slug);
      const files = (await listFilesRecursive(dirPath)).map((absolute) => path.relative(FRONTEND_PUBLIC_DIR, absolute));
      if (!files.length) continue;

      const mappedBook = booksBySlug.get(slug) || null;
      rows.push({
        path: normalizeRouteKey(`/${files[0].replace(/\\/g, "/")}`, frontendUrl),
        url: new URL(`/${files[0].replace(/\\/g, "/")}`, `${frontendUrl}/`).href,
        title: mappedBook?.title || slug,
        content_type: "book_asset",
        public_status: mappedBook ? "public_asset" : "orphaned_asset",
        sitemap_status: "excluded",
        robots_status: "allowed",
        rights_metadata_present: mappedBook ? rightsMetadataStatus(mappedBook) : "unknown",
        cta_present: "not_applicable",
        source_sets: ["book_assets_dir"],
        related_slug: slug,
        language: "",
        asset_health: files.some((file) => file.endsWith("front-cover.jpg")) ? "complete" : "incomplete",
        asset_files: files.sort(),
      });
    }

    return {
      rows: rows.sort((a, b) => a.path.localeCompare(b.path)),
      sourceStatus: sourceStatusBase({
        ok: true,
        status: "filesystem",
        cached: false,
        error: null,
        item_count: rows.length,
        degraded_reason: null,
      }),
    };
  } catch (error) {
    return {
      rows: [],
      sourceStatus: finalizeSourceFailure("book_assets_dir", error.message, false),
    };
  }
}

function sourceWarningsForRow(sourceSets, sourceStatuses) {
  const warnings = [];

  for (const sourceSet of sourceSets) {
    const status = sourceStatuses[sourceSet];
    if (!status) continue;

    if (status.degraded_reason) {
      warnings.push(`${sourceSet}: ${status.degraded_reason}`);
      continue;
    }

    if (status.cached && status.error) {
      warnings.push(`${sourceSet}: using cached data after ${status.error}`);
      continue;
    }

    if (!status.ok && status.error) {
      warnings.push(`${sourceSet}: ${status.error}`);
    }
  }

  return warnings;
}

function finalizeRow(baseRow, context) {
  const row = {
    path: normalizeRouteKey(baseRow.path || "/", context.frontendUrl),
    url: baseRow.url || new URL(baseRow.path || "/", `${context.frontendUrl}/`).href,
    title: baseRow.title || routePath(baseRow.path).split("/").filter(Boolean).join(" ") || "Earnalism",
    content_type: baseRow.content_type || routeType(baseRow.path),
    public_status: baseRow.public_status || "public",
    sitemap_status: baseRow.sitemap_status || (context.sitemapRouteSet.has(baseRow.path) ? "included" : "excluded"),
    robots_status: baseRow.robots_status || robotsStatusForRoute(baseRow.path, context.robotsRules),
    rights_metadata_present: baseRow.rights_metadata_present || "not_applicable",
    cta_present: baseRow.cta_present || "not_applicable",
    source_sets: Array.isArray(baseRow.source_sets) ? baseRow.source_sets : [],
    related_slug: baseRow.related_slug || "",
    language: baseRow.language || "",
    asset_health: baseRow.asset_health || "not_applicable",
    asset_files: Array.isArray(baseRow.asset_files) ? baseRow.asset_files : [],
    audiobook_enabled: Boolean(baseRow.audiobook_enabled),
  };

  row.source_warnings = sourceWarningsForRow(row.source_sets, context.sourceStatuses);
  row.degraded = row.source_sets.some((sourceSet) => Boolean(context.sourceStatuses[sourceSet]?.degraded_reason));
  row.growth_relevance_score = growthRelevanceScore(row);
  row.recommended_action = recommendedAction(row);
  row.reason = buildReason(row);

  return row;
}

export function summarizeRows(rows, sourceStatuses, extra = {}) {
  const actionCounts = Object.fromEntries(ACTIONS.map((action) => [action, 0]));
  const contentTypeCounts = {};
  const robotsStatusCounts = {};
  const sitemapStatusCounts = {};
  const publicStatusCounts = {};

  for (const row of rows) {
    actionCounts[row.recommended_action] = (actionCounts[row.recommended_action] || 0) + 1;
    contentTypeCounts[row.content_type] = (contentTypeCounts[row.content_type] || 0) + 1;
    robotsStatusCounts[row.robots_status] = (robotsStatusCounts[row.robots_status] || 0) + 1;
    sitemapStatusCounts[row.sitemap_status] = (sitemapStatusCounts[row.sitemap_status] || 0) + 1;
    publicStatusCounts[row.public_status] = (publicStatusCounts[row.public_status] || 0) + 1;
  }

  const degradedReasons = Array.from(
    new Set(
      Object.values(sourceStatuses)
        .map((status) => status?.degraded_reason)
        .filter(Boolean),
    ),
  );

  return {
    generated_at: new Date().toISOString(),
    mode: "dry-run",
    total_items: rows.length,
    action_counts: actionCounts,
    content_type_counts: contentTypeCounts,
    robots_status_counts: robotsStatusCounts,
    sitemap_status_counts: sitemapStatusCounts,
    public_status_counts: publicStatusCounts,
    source_statuses: sourceStatuses,
    degraded: degradedReasons.length > 0,
    degraded_reasons: degradedReasons,
    ...extra,
  };
}

export function renderCleanupMarkdown(summary, rows) {
  const lines = [
    "# Earnalism Catalog Cleanup Report",
    "",
    `Generated: ${summary.generated_at}`,
    "",
    "## Summary",
    "",
    `- Mode: ${summary.mode}`,
    `- Total audited items: ${summary.total_items}`,
    `- Sitemap URLs discovered: ${summary.sitemap_urls}`,
    `- Robots-visible items: ${summary.robots_status_counts.allowed || 0}`,
    `- Degraded: ${summary.degraded ? "yes" : "no"}`,
    `- Dry-run only: no content was mutated or deleted`,
    "",
    "## Source Health",
    "",
  ];

  for (const [sourceKey, status] of Object.entries(summary.source_statuses || {})) {
    lines.push(
      `- ${sourceKey}: ok=${status.ok} status=${status.status} cached=${status.cached} item_count=${status.item_count} error=${status.error || "none"} degraded_reason=${status.degraded_reason || "none"}`,
    );
  }

  lines.push("", "## Degraded Reasons", "");
  if (summary.degraded_reasons.length) {
    for (const reason of summary.degraded_reasons) {
      lines.push(`- ${reason}`);
    }
  } else {
    lines.push("- None");
  }

  for (const action of ACTIONS) {
    lines.push("", `## ${action}`, "");
    lines.push(`- Count: ${summary.action_counts[action] || 0}`);
    const matching = rows.filter((row) => row.recommended_action === action).slice(0, 15);
    if (!matching.length) {
      lines.push("- No items in this category.");
      continue;
    }
    for (const row of matching) {
      lines.push(`- ${row.path} | ${row.content_type} | ${row.reason}`);
    }
  }

  lines.push("", "## Notes", "");
  lines.push("- This audit is report-only and does not mutate CMS, API, or storage records.");
  lines.push("- `DELETE`, `ARCHIVE`, `QUARANTINE`, and `REWRITE` are recommendations for manual follow-up only.");
  lines.push(`- Book and asset rights are conservatively handled until Phase 2: ${RIGHTS_REQUIRED_REASON}`);
  lines.push("");

  return lines.join("\n");
}

function resolveRuntimeOptions(options = {}) {
  const frontendUrl = normalizeBase(options.frontendUrl || argValue("--frontend-url", process.env.FRONTEND_URL || DEFAULT_FRONTEND_URL));
  const apiUrl = normalizeBase(options.apiUrl || argValue("--api-url", process.env.API_URL || DEFAULT_API_URL));
  const fixtureDir = resolvePathMaybe(options.fixtureDir || argValue("--fixture", null), ROOT);
  const outputDir = resolvePathMaybe(options.outputDir || argValue("--output-dir", DEFAULT_OUTPUT_DIR), ROOT);
  const timeoutMs = Number.parseInt(options.timeoutMs || argValue("--timeout-ms", DEFAULT_TIMEOUT_MS), 10);
  const cacheDir = path.join(outputDir, "cache");

  return {
    frontendUrl,
    apiUrl,
    fixtureDir,
    outputDir,
    cacheDir,
    timeoutMs: Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : DEFAULT_TIMEOUT_MS,
  };
}

export async function runCatalogAudit(options = {}) {
  const runtime = resolveRuntimeOptions(options);
  const sourceStatuses = {};

  const [sitemapResult, robotsResult, booksResult, blogResult, categoriesResult] = await Promise.all([
    loadTextSource({
      sourceKey: "sitemap",
      url: `${runtime.frontendUrl}/sitemap.xml`,
      cacheDir: runtime.cacheDir,
      cacheName: "sitemap.xml",
      fixtureDir: runtime.fixtureDir,
      fixtureFile: "sitemap.xml",
      timeoutMs: runtime.timeoutMs,
      validate: validateSitemapText,
      required: true,
    }),
    loadTextSource({
      sourceKey: "robots",
      url: `${runtime.frontendUrl}/robots.txt`,
      cacheDir: runtime.cacheDir,
      cacheName: "robots.txt",
      fixtureDir: runtime.fixtureDir,
      fixtureFile: "robots.txt",
      timeoutMs: runtime.timeoutMs,
      validate: validateRobotsText,
      required: true,
    }),
    loadJsonArraySource({
      sourceKey: "books_api",
      url: `${runtime.apiUrl}/books`,
      cacheDir: runtime.cacheDir,
      cacheName: "books.json",
      fixtureDir: runtime.fixtureDir,
      fixtureFile: "books.json",
      timeoutMs: runtime.timeoutMs,
      required: true,
    }),
    loadJsonArraySource({
      sourceKey: "blog_api",
      url: `${runtime.apiUrl}/blog`,
      cacheDir: runtime.cacheDir,
      cacheName: "blog.json",
      fixtureDir: runtime.fixtureDir,
      fixtureFile: "blog.json",
      timeoutMs: runtime.timeoutMs,
      required: false,
    }),
    loadJsonArraySource({
      sourceKey: "categories_api",
      url: `${runtime.apiUrl}/categories`,
      cacheDir: runtime.cacheDir,
      cacheName: "categories.json",
      fixtureDir: runtime.fixtureDir,
      fixtureFile: "categories.json",
      timeoutMs: runtime.timeoutMs,
      required: false,
    }),
  ]);

  sourceStatuses.sitemap = sitemapResult.sourceStatus;
  sourceStatuses.robots = robotsResult.sourceStatus;
  sourceStatuses.books_api = booksResult.sourceStatus;
  sourceStatuses.blog_api = blogResult.sourceStatus;
  sourceStatuses.categories_api = categoriesResult.sourceStatus;

  const books = Array.isArray(booksResult.data) ? booksResult.data : [];
  const blogPosts = Array.isArray(blogResult.data) ? blogResult.data : [];
  const categories = Array.isArray(categoriesResult.data) ? categoriesResult.data : [];
  const sitemapUrls = sourceStatuses.sitemap.ok ? extractLocs(sitemapResult.text) : [];
  const sitemapRouteSet = new Set(sitemapUrls.map((url) => normalizeRouteKey(url, runtime.frontendUrl)));
  const robotsRules = sourceStatuses.robots.ok ? parseRobots(robotsResult.text) : { disallowRules: [], allowRules: [] };

  const booksBySlug = new Map();
  const booksByAudioAssetSlug = new Map();
  for (const book of books) {
    if (!book?.slug || book.is_published === false) continue;
    booksBySlug.set(String(book.slug), book);
    if (book.audio_asset_slug) {
      booksByAudioAssetSlug.set(String(book.audio_asset_slug), book);
    }
  }

  const audioAssets = await discoverAudioAssets({
    frontendUrl: runtime.frontendUrl,
    fixtureDir: runtime.fixtureDir,
    booksBySlug,
    booksByAudioAssetSlug,
  });
  sourceStatuses.audio_public_dir = audioAssets.sourceStatus;

  const bookAssets = await discoverBookAssets({
    frontendUrl: runtime.frontendUrl,
    fixtureDir: runtime.fixtureDir,
    booksBySlug,
  });
  sourceStatuses.book_assets_dir = bookAssets.sourceStatus;

  const rawRows = [];
  const seen = new Set();

  function pushRawRow(row) {
    const pathKey = normalizeRouteKey(row.path || "/", runtime.frontendUrl);
    if (seen.has(pathKey)) return;
    seen.add(pathKey);
    rawRows.push({
      ...row,
      path: pathKey,
    });
  }

  for (const route of CORE_ROUTES) {
    pushRawRow({
      ...route,
      rights_metadata_present: "not_applicable",
      cta_present: ctaStatus(route),
      source_sets: ["core_routes"],
    });
  }

  for (const category of categories) {
    if (!category?.slug) continue;
    pushRawRow({
      path: `/library?category=${encodeURIComponent(category.slug)}`,
      title: category.name || category.slug,
      content_type: "library_category",
      public_status: "public",
      rights_metadata_present: "not_applicable",
      cta_present: "assumed_yes",
      source_sets: ["categories_api"],
    });
  }

  for (const book of books) {
    if (!book?.slug || book.is_published === false) continue;
    pushRawRow({
      path: `/book/${book.slug}`,
      title: book.title || book.slug,
      content_type: "book_page",
      public_status: "public",
      rights_metadata_present: rightsMetadataStatus(book),
      cta_present: "assumed_yes",
      source_sets: ["books_api"],
      related_slug: book.slug,
      audiobook_enabled: Boolean(book.audiobook_enabled),
    });
    pushRawRow({
      path: `/reader/${book.slug}`,
      title: `${book.title || book.slug} Reader`,
      content_type: "reader_page",
      public_status: "gated_public",
      sitemap_status: "excluded",
      rights_metadata_present: rightsMetadataStatus(book),
      cta_present: "not_applicable",
      source_sets: ["books_api"],
      related_slug: book.slug,
      audiobook_enabled: Boolean(book.audiobook_enabled),
    });
  }

  for (const post of blogPosts) {
    if (!post?.slug || post.is_published === false) continue;
    pushRawRow({
      path: `/journal/${post.slug}`,
      title: post.title || post.slug,
      content_type: "journal_page",
      public_status: "public",
      rights_metadata_present: rightsMetadataStatus(post),
      cta_present: "assumed_no",
      source_sets: ["blog_api"],
    });
  }

  for (const removedPath of KNOWN_REMOVED_URLS) {
    pushRawRow({
      path: removedPath,
      title: routePath(removedPath).split("/").filter(Boolean).join(" "),
      content_type: "removed_demo_or_ecommerce",
      public_status: "removed",
      sitemap_status: "excluded",
      rights_metadata_present: "not_applicable",
      cta_present: "not_applicable",
      source_sets: ["known_removed_urls"],
    });
  }

  for (const sitemapUrl of sitemapUrls) {
    const routeKey = normalizeRouteKey(sitemapUrl, runtime.frontendUrl);
    if (seen.has(routeKey)) continue;
    pushRawRow({
      path: routeKey,
      title: routePath(routeKey).split("/").filter(Boolean).join(" ") || "Earnalism",
      content_type: routeType(routeKey),
      public_status: "public",
      rights_metadata_present: "unknown",
      cta_present: ctaStatus({ content_type: routeType(routeKey) }),
      source_sets: ["sitemap"],
    });
  }

  for (const row of audioAssets.rows) {
    pushRawRow(row);
  }

  for (const row of bookAssets.rows) {
    pushRawRow(row);
  }

  rawRows.sort((a, b) => a.path.localeCompare(b.path));

  const rows = rawRows.map((row) => finalizeRow(row, {
    frontendUrl: runtime.frontendUrl,
    sitemapRouteSet,
    robotsRules,
    sourceStatuses,
  }));

  const summary = summarizeRows(rows, sourceStatuses, {
    frontend_url: runtime.frontendUrl,
    api_url: runtime.apiUrl,
    fixture_dir: runtime.fixtureDir ? path.relative(ROOT, runtime.fixtureDir) : null,
    timeout_ms: runtime.timeoutMs,
    sitemap_urls: sitemapUrls.length,
    blocked_terms: BLOCKED_TERMS,
    blocked_prefixes: BLOCKED_PREFIXES,
  });

  return { summary, rows, runtime };
}

async function writeOutputs(summary, rows, outputDir) {
  await fs.mkdir(outputDir, { recursive: true });

  const jsonPath = path.join(outputDir, "catalog_audit_report.json");
  const csvPath = path.join(outputDir, "catalog_audit_report.csv");
  const markdownPath = path.join(outputDir, "catalog_cleanup_report.md");

  await fs.writeFile(jsonPath, `${JSON.stringify({ summary, rows }, null, 2)}\n`, "utf8");

  const columns = [
    "url",
    "path",
    "title",
    "content_type",
    "public_status",
    "sitemap_status",
    "robots_status",
    "growth_relevance_score",
    "rights_metadata_present",
    "cta_present",
    "reason",
    "recommended_action",
    "source_sets",
    "related_slug",
    "language",
    "asset_health",
    "asset_files",
    "degraded",
    "source_warnings",
  ];

  const csv = [
    columns.join(","),
    ...rows.map((row) => columns.map((column) => csvEscape(row[column])).join(",")),
  ].join("\n");
  await fs.writeFile(csvPath, `${csv}\n`, "utf8");

  await fs.writeFile(markdownPath, `${renderCleanupMarkdown(summary, rows)}\n`, "utf8");
}

export async function main() {
  const { summary, rows, runtime } = await runCatalogAudit();
  await writeOutputs(summary, rows, runtime.outputDir);
  console.log(`[catalog-audit] ${summary.total_items} items audited. Reports written to ${path.relative(ROOT, runtime.outputDir)}.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(`[catalog-audit] ${error.stack || error.message}`);
    process.exitCode = 1;
  });
}
