#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const DEFAULT_FRONTEND_URL = "https://theearnalism.com";
const DEFAULT_API_URL = "https://api.theearnalism.com/api";
const OUTPUT_DIR = path.join(ROOT, "output", "catalog_audit");
const CACHE_DIR = path.join(OUTPUT_DIR, "cache");
const FRONTEND_PUBLIC_DIR = path.join(ROOT, "frontend", "public");

export const ACTIONS = ["KEEP", "REWRITE", "NOINDEX", "QUARANTINE", "ARCHIVE", "DELETE"];

export const BLOCKED_PREFIXES = [
  "/apparel",
  "/clothing",
  "/fashion",
  "/product",
  "/products",
  "/product-category",
  "/shop",
  "/tag/apparel",
  "/tag/clothing",
  "/tag/fashion",
];

export const BLOCKED_TERMS = [
  "apparel",
  "clothing",
  "denim-jacket",
  "denim-jackets",
  "fashion",
  "lorem-ipsum",
  "patterned-wrap-dress",
  "placeholder-product",
  "sample-product",
  "woocommerce",
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
  "/blog/denim-jackets",
  "/denim-jackets",
  "/fashion",
  "/clothing",
  "/apparel",
  "/product-category/clothing",
  "/tag/fashion",
];

const AUDIO_SUFFIXES = [
  "_highlight.vtt",
  "_timestamps.json",
  "_meta.json",
  "_chapters.json",
  ".mp3",
];

const CTA_POSITIVE_TYPES = new Set([
  "homepage",
  "library",
  "library_category",
  "book_page",
  "pricing_page",
  "campaign_page",
]);

const CTA_OPTIONAL_TYPES = new Set([
  "journal_index",
  "journal_page",
  "about_page",
  "contact_page",
  "audio_asset",
  "book_asset",
]);

export function argValue(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return process.env[name.replace(/^--/, "").replace(/-/g, "_").toUpperCase()] || fallback;
}

export function normalizeBase(value) {
  return String(value || "").replace(/\/+$/, "");
}

export function csvEscape(value) {
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
  if (record && typeof record === "object" && record.rights_metadata && typeof record.rights_metadata === "object") {
    return Object.keys(record.rights_metadata).length > 0 ? "yes" : "no";
  }
  return "unknown";
}

export function ctaStatus(item) {
  const type = item.content_type || routeType(item.path);
  if (CTA_POSITIVE_TYPES.has(type)) return "yes";
  if (CTA_OPTIONAL_TYPES.has(type)) return "no";
  return "not_applicable";
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
  if (item.public_status === "orphaned_asset") {
    return "ARCHIVE";
  }
  if (item.rights_metadata_present === "no") {
    return "QUARANTINE";
  }
  if (item.content_type === "reader_page" || item.content_type === "auth_page" || item.content_type === "account_page") {
    return "NOINDEX";
  }
  if (item.content_type === "journal_page" && item.cta_present === "no") {
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
  if (item.public_status === "orphaned_asset") {
    reasons.push("Public asset does not map to a published book or current audio asset slug.");
  }
  if (item.content_type === "reader_page") {
    reasons.push("Reader route is intentionally gated and disallowed by robots.");
  }
  if (item.content_type === "auth_page" || item.content_type === "account_page") {
    reasons.push("Authentication and account surfaces should stay out of search results.");
  }
  if (item.content_type === "journal_page" && item.cta_present === "no") {
    reasons.push("Editorial content is live but does not expose a strong conversion CTA.");
  }
  if ((item.content_type === "audio_asset" || item.content_type === "book_asset") && item.asset_health === "incomplete") {
    reasons.push("Supporting public asset bundle is incomplete.");
  }
  if (item.content_type === "book_page" && item.rights_metadata_present === "unknown") {
    reasons.push("Rights metadata is not verifiable from the current public API payload.");
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
  if (reasons.length === 0) {
    reasons.push("Aligned with current public catalog governance policy.");
  }

  return reasons.join(" ");
}

export async function fetchText(url, cacheName) {
  await fs.mkdir(CACHE_DIR, { recursive: true });
  const cachePath = path.join(CACHE_DIR, cacheName);
  try {
    const response = await fetch(url, { headers: { Accept: "*/*", "User-Agent": "EarnalismCatalogAudit/2.0" } });
    const text = await response.text();
    await fs.writeFile(cachePath, text, "utf8");
    return { ok: response.ok, status: response.status, text, cached: false };
  } catch (error) {
    try {
      const text = await fs.readFile(cachePath, "utf8");
      return { ok: true, status: 200, text, cached: true, error: error.message };
    } catch {
      return { ok: false, status: 0, text: "", cached: false, error: error.message };
    }
  }
}

export async function fetchJson(url, cacheName) {
  const result = await fetchText(url, cacheName);
  try {
    return { ...result, data: JSON.parse(result.text) };
  } catch {
    return { ...result, data: [] };
  }
}

async function readJsonIfExists(filePath) {
  try {
    const text = await fs.readFile(filePath, "utf8");
    return JSON.parse(text);
  } catch {
    return null;
  }
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

export async function discoverAudioAssets(frontendUrl, booksBySlug, booksByAudioAssetSlug) {
  const audioRoot = path.join(FRONTEND_PUBLIC_DIR, "audio");
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

    if (fileName.endsWith("_meta.json")) {
      bundle.meta = await readJsonIfExists(absolutePath);
    }

    bundles.set(bundleId, bundle);
  }

  const rows = [];
  for (const bundle of bundles.values()) {
    const mappedBook = booksBySlug.get(bundle.bundle_name) || booksByAudioAssetSlug.get(bundle.bundle_name) || null;
    const publicStatus = mappedBook ? "public_asset" : "orphaned_asset";
    const title = bundle.meta?.title || mappedBook?.title || bundle.bundle_name;
    rows.push({
      path: bundle.path,
      url: new URL(bundle.path, `${frontendUrl}/`).href,
      title,
      content_type: "audio_asset",
      public_status: publicStatus,
      sitemap_status: "excluded",
      robots_status: "allowed",
      rights_metadata_present: mappedBook ? rightsMetadataStatus(mappedBook) : "unknown",
      cta_present: "not_applicable",
      growth_relevance_score: 0,
      reason: "",
      recommended_action: "",
      source_sets: ["audio_public_dir"],
      language: bundle.language,
      related_slug: mappedBook?.slug || bundle.meta?.slug || bundle.bundle_name,
      audiobook_enabled: Boolean(mappedBook?.audiobook_enabled),
      asset_health: buildAudioAssetHealth(bundle),
      asset_files: bundle.files.sort(),
    });
  }

  return rows.sort((a, b) => a.path.localeCompare(b.path));
}

export async function discoverBookAssets(frontendUrl, booksBySlug) {
  const booksRoot = path.join(FRONTEND_PUBLIC_DIR, "assets", "books");
  const rows = [];

  try {
    const entries = await fs.readdir(booksRoot, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const slug = entry.name;
      const dirPath = path.join(booksRoot, slug);
      const files = (await listFilesRecursive(dirPath)).map((absolute) => path.relative(FRONTEND_PUBLIC_DIR, absolute));
      if (!files.length) continue;
      const mappedBook = booksBySlug.get(slug) || null;
      rows.push({
        path: `/${files[0].replace(/\\/g, "/")}`,
        url: new URL(`/${files[0].replace(/\\/g, "/")}`, `${frontendUrl}/`).href,
        title: mappedBook?.title || slug,
        content_type: "book_asset",
        public_status: mappedBook ? "public_asset" : "orphaned_asset",
        sitemap_status: "excluded",
        robots_status: "allowed",
        rights_metadata_present: mappedBook ? rightsMetadataStatus(mappedBook) : "unknown",
        cta_present: "not_applicable",
        growth_relevance_score: 0,
        reason: "",
        recommended_action: "",
        source_sets: ["book_asset_dir"],
        related_slug: slug,
        asset_health: files.some((file) => file.endsWith("front-cover.jpg")) ? "complete" : "incomplete",
        asset_files: files.sort(),
      });
    }
  } catch {
    return [];
  }

  return rows.sort((a, b) => a.path.localeCompare(b.path));
}

export function finalizeRow(baseRow) {
  const row = { ...baseRow };
  row.growth_relevance_score = growthRelevanceScore(row);
  row.recommended_action = recommendedAction(row);
  row.reason = buildReason(row);
  return row;
}

export function summarizeRows(rows, extra = {}) {
  const byAction = Object.fromEntries(ACTIONS.map((action) => [action, 0]));
  const byContentType = {};
  const byRobotsStatus = {};
  const bySitemapStatus = {};
  const byPublicStatus = {};

  for (const row of rows) {
    byAction[row.recommended_action] = (byAction[row.recommended_action] || 0) + 1;
    byContentType[row.content_type] = (byContentType[row.content_type] || 0) + 1;
    byRobotsStatus[row.robots_status] = (byRobotsStatus[row.robots_status] || 0) + 1;
    bySitemapStatus[row.sitemap_status] = (bySitemapStatus[row.sitemap_status] || 0) + 1;
    byPublicStatus[row.public_status] = (byPublicStatus[row.public_status] || 0) + 1;
  }

  return {
    generated_at: new Date().toISOString(),
    mode: "dry-run",
    total_items: rows.length,
    action_counts: byAction,
    content_type_counts: byContentType,
    robots_status_counts: byRobotsStatus,
    sitemap_status_counts: bySitemapStatus,
    public_status_counts: byPublicStatus,
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
    `- Dry-run only: no content was mutated or deleted`,
    "",
  ];

  for (const action of ACTIONS) {
    lines.push(`## ${action}`, "");
    lines.push(`- Count: ${summary.action_counts[action] || 0}`);
    const matching = rows.filter((row) => row.recommended_action === action).slice(0, 15);
    for (const row of matching) {
      lines.push(`- ${row.path} | ${row.content_type} | ${row.reason}`);
    }
    if (!matching.length) {
      lines.push("- No items in this category.");
    }
    lines.push("");
  }

  lines.push("## Notes", "");
  lines.push("- This audit is report-only and does not mutate CMS, API, or storage records.");
  lines.push("- `DELETE`, `ARCHIVE`, `QUARANTINE`, and `REWRITE` are recommendations for manual follow-up only.");
  lines.push("- Rights metadata is marked `unknown` when the public API does not expose enough proof to verify it.");
  lines.push("");

  return lines.join("\n");
}

export async function runCatalogAudit(options = {}) {
  const frontendUrl = normalizeBase(options.frontendUrl || process.env.FRONTEND_URL || DEFAULT_FRONTEND_URL);
  const apiUrl = normalizeBase(options.apiUrl || process.env.API_URL || DEFAULT_API_URL);

  const [sitemapResult, robotsResult, booksResult, postsResult, categoriesResult] = await Promise.all([
    fetchText(`${frontendUrl}/sitemap.xml`, "sitemap.xml"),
    fetchText(`${frontendUrl}/robots.txt`, "robots.txt"),
    fetchJson(`${apiUrl}/books`, "books.json"),
    fetchJson(`${apiUrl}/blog`, "blog.json"),
    fetchJson(`${apiUrl}/categories`, "categories.json"),
  ]);

  const books = Array.isArray(booksResult.data) ? booksResult.data : [];
  const posts = Array.isArray(postsResult.data) ? postsResult.data : [];
  const categories = Array.isArray(categoriesResult.data) ? categoriesResult.data : [];
  const sitemapUrls = extractLocs(sitemapResult.text);
  const sitemapRouteSet = new Set(sitemapUrls.map((url) => normalizeRouteKey(url, frontendUrl)));
  const robotsRules = parseRobots(robotsResult.text || await fs.readFile(path.join(FRONTEND_PUBLIC_DIR, "robots.txt"), "utf8").catch(() => ""));

  const booksBySlug = new Map();
  const booksByAudioAssetSlug = new Map();
  for (const book of books) {
    if (!book?.slug || book.is_published === false) continue;
    booksBySlug.set(String(book.slug), book);
    if (book.audio_asset_slug) booksByAudioAssetSlug.set(String(book.audio_asset_slug), book);
  }

  const rows = [];
  const seen = new Set();

  function pushRow(partial) {
    const pathKey = normalizeRouteKey(partial.path || partial.url || "/", frontendUrl);
    if (seen.has(pathKey)) return;
    seen.add(pathKey);

    const row = finalizeRow({
      path: pathKey,
      url: partial.url || new URL(pathKey, `${frontendUrl}/`).href,
      title: partial.title || routePath(pathKey).split("/").filter(Boolean).join(" ") || "Earnalism",
      content_type: partial.content_type || routeType(pathKey),
      public_status: partial.public_status || "public",
      sitemap_status: partial.sitemap_status || (pathKey === "/sitemap.xml" ? "document" : sitemapRouteSet.has(pathKey) ? "included" : "excluded"),
      robots_status: partial.robots_status || robotsStatusForRoute(pathKey, robotsRules),
      rights_metadata_present: partial.rights_metadata_present || "not_applicable",
      cta_present: partial.cta_present || "not_applicable",
      reason: partial.reason || "",
      recommended_action: partial.recommended_action || "",
      growth_relevance_score: partial.growth_relevance_score || 0,
      source_sets: partial.source_sets || [],
      audiobook_enabled: Boolean(partial.audiobook_enabled),
      asset_health: partial.asset_health || "not_applicable",
      related_slug: partial.related_slug || "",
      asset_files: partial.asset_files || [],
    });

    rows.push(row);
  }

  for (const core of CORE_ROUTES) {
    pushRow({
      ...core,
      rights_metadata_present: "not_applicable",
      cta_present: ctaStatus(core),
      source_sets: ["core_routes"],
    });
  }

  for (const category of categories) {
    if (!category?.slug) continue;
    pushRow({
      path: `/library?category=${encodeURIComponent(category.slug)}`,
      title: category.name || category.slug,
      content_type: "library_category",
      public_status: "public",
      rights_metadata_present: "not_applicable",
      cta_present: "yes",
      source_sets: ["categories_api"],
    });
  }

  for (const book of books) {
    if (!book?.slug || book.is_published === false) continue;
    pushRow({
      path: `/book/${book.slug}`,
      title: book.title || book.slug,
      content_type: "book_page",
      public_status: "public",
      rights_metadata_present: rightsMetadataStatus(book),
      cta_present: "yes",
      source_sets: ["books_api"],
      audiobook_enabled: Boolean(book.audiobook_enabled),
      related_slug: book.slug,
    });
    pushRow({
      path: `/reader/${book.slug}`,
      title: `${book.title || book.slug} Reader`,
      content_type: "reader_page",
      public_status: "gated_public",
      sitemap_status: "excluded",
      rights_metadata_present: rightsMetadataStatus(book),
      cta_present: "not_applicable",
      source_sets: ["books_api", "reader_routes"],
      audiobook_enabled: Boolean(book.audiobook_enabled),
      related_slug: book.slug,
    });
  }

  for (const post of posts) {
    if (!post?.slug || post.is_published === false) continue;
    pushRow({
      path: `/journal/${post.slug}`,
      title: post.title || post.slug,
      content_type: "journal_page",
      public_status: "public",
      rights_metadata_present: rightsMetadataStatus(post),
      cta_present: "no",
      source_sets: ["blog_api"],
    });
  }

  for (const removedPath of KNOWN_REMOVED_URLS) {
    pushRow({
      path: removedPath,
      title: routePath(removedPath).split("/").filter(Boolean).join(" "),
      content_type: "removed_demo_or_ecommerce",
      public_status: "removed",
      sitemap_status: "excluded",
      robots_status: robotsStatusForRoute(removedPath, robotsRules),
      rights_metadata_present: "not_applicable",
      cta_present: "not_applicable",
      source_sets: ["known_removed_urls"],
    });
  }

  for (const sitemapUrl of sitemapUrls) {
    const routeKey = normalizeRouteKey(sitemapUrl, frontendUrl);
    if (!seen.has(routeKey)) {
      pushRow({
        path: routeKey,
        title: routePath(routeKey).split("/").filter(Boolean).join(" ") || "Earnalism",
        content_type: routeType(routeKey),
        public_status: "public",
        rights_metadata_present: "unknown",
        cta_present: ctaStatus({ content_type: routeType(routeKey) }),
        source_sets: ["sitemap_only"],
      });
    }
  }

  for (const row of await discoverAudioAssets(frontendUrl, booksBySlug, booksByAudioAssetSlug)) {
    pushRow(row);
  }

  for (const row of await discoverBookAssets(frontendUrl, booksBySlug)) {
    pushRow(row);
  }

  rows.sort((a, b) => a.path.localeCompare(b.path));

  const summary = summarizeRows(rows, {
    frontend_url: frontendUrl,
    api_url: apiUrl,
    sitemap_urls: sitemapUrls.length,
    blocked_terms: BLOCKED_TERMS,
    blocked_prefixes: BLOCKED_PREFIXES,
  });

  return { summary, rows };
}

async function writeOutputs(summary, rows) {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });

  await fs.writeFile(
    path.join(OUTPUT_DIR, "catalog_audit_report.json"),
    `${JSON.stringify({ summary, rows }, null, 2)}\n`,
    "utf8",
  );

  const columns = [
    "url",
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
  ];
  const csv = [
    columns.join(","),
    ...rows.map((row) => columns.map((column) => csvEscape(row[column])).join(",")),
  ].join("\n");
  await fs.writeFile(path.join(OUTPUT_DIR, "catalog_audit_report.csv"), `${csv}\n`, "utf8");

  await fs.writeFile(
    path.join(OUTPUT_DIR, "catalog_cleanup_report.md"),
    `${renderCleanupMarkdown(summary, rows)}\n`,
    "utf8",
  );
}

export async function main() {
  const { summary, rows } = await runCatalogAudit({
    frontendUrl: argValue("--frontend-url", process.env.FRONTEND_URL || DEFAULT_FRONTEND_URL),
    apiUrl: argValue("--api-url", process.env.API_URL || DEFAULT_API_URL),
  });
  await writeOutputs(summary, rows);
  console.log(`[catalog-audit] ${summary.total_items} items audited. Reports written to ${path.relative(ROOT, OUTPUT_DIR)}.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(`[catalog-audit] ${error.stack || error.message}`);
    process.exitCode = 1;
  });
}
