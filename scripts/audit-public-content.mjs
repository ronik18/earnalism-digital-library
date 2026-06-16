#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const DEFAULT_FRONTEND_URL = "https://theearnalism.com";
const DEFAULT_API_URL = "https://api.theearnalism.com/api";
const OUTPUT_DIR = path.join(ROOT, "output", "catalog_audit");
const CACHE_DIR = path.join(OUTPUT_DIR, "cache");

const BLOCKED_PREFIXES = [
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

const BLOCKED_TERMS = [
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

const CORE_ALLOWED_PATHS = new Set([
  "/",
  "/library",
  "/journal",
  "/about",
  "/contact",
  "/pricing",
  "/login",
  "/signup",
  "/micro-story",
]);

const KNOWN_REMOVED_URLS = [
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

function argValue(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return process.env[name.replace(/^--/, "").replace(/-/g, "_").toUpperCase()] || fallback;
}

function normalizeBase(value) {
  return String(value || "").replace(/\/+$/, "");
}

function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function extractLocs(xml) {
  return [...String(xml || "").matchAll(/<loc>([^<]+)<\/loc>/gi)].map((match) => match[1].trim());
}

function pathFromUrl(value, frontendUrl) {
  try {
    return new URL(value, `${frontendUrl}/`).pathname || "/";
  } catch {
    return "/";
  }
}

function routeType(pagePath) {
  if (pagePath === "/") return "homepage";
  if (pagePath === "/library" || pagePath.startsWith("/library?")) return "library";
  if (pagePath.startsWith("/book/")) return "book";
  if (pagePath === "/journal") return "journal";
  if (pagePath.startsWith("/journal/")) return "journal_post";
  if (pagePath.startsWith("/reader/")) return "reader";
  if (pagePath === "/about") return "about";
  if (pagePath === "/contact") return "contact";
  if (pagePath === "/pricing") return "membership";
  if (pagePath === "/login" || pagePath === "/signup") return "auth";
  return "unknown";
}

function isBlockedPath(pagePath = "") {
  const lowered = String(pagePath || "").toLowerCase();
  return (
    BLOCKED_PREFIXES.some((prefix) => lowered === prefix || lowered.startsWith(`${prefix}/`))
    || BLOCKED_TERMS.some((term) => lowered.includes(term))
  );
}

function relevanceScore(item) {
  const type = item.type || item.content_type;
  if (isBlockedPath(item.path)) return 0;
  if (CORE_ALLOWED_PATHS.has(item.path)) return 100;
  if (type === "book") return item.hasTitle ? 95 : 75;
  if (type === "journal_post") return item.hasTitle ? 88 : 60;
  if (type === "library" || type === "library_category") return 94;
  if (type === "membership") return 90;
  if (type === "auth") return 70;
  return 40;
}

function recommendation(item) {
  if (isBlockedPath(item.path)) return "410";
  if (item.status === "missing") return "NOINDEX";
  if (item.score >= 80) return "KEEP";
  if (item.score >= 55) return "NOINDEX";
  return "REDIRECT";
}

async function fetchText(url, cacheName) {
  await fs.mkdir(CACHE_DIR, { recursive: true });
  const cachePath = path.join(CACHE_DIR, cacheName);
  try {
    const response = await fetch(url, { headers: { Accept: "*/*", "User-Agent": "EarnalismCatalogAudit/1.0" } });
    const text = await response.text();
    await fs.writeFile(cachePath, text, "utf8");
    return { ok: response.ok, status: response.status, text };
  } catch (error) {
    try {
      const text = await fs.readFile(cachePath, "utf8");
      return { ok: true, status: 200, text, cached: true, error: error.message };
    } catch {
      return { ok: false, status: 0, text: "", error: error.message };
    }
  }
}

async function fetchJson(url, cacheName) {
  const result = await fetchText(url, cacheName);
  try {
    return JSON.parse(result.text);
  } catch {
    return [];
  }
}

async function main() {
  const frontendUrl = normalizeBase(argValue("--frontend-url", process.env.FRONTEND_URL || DEFAULT_FRONTEND_URL));
  const apiUrl = normalizeBase(argValue("--api-url", process.env.API_URL || DEFAULT_API_URL));
  const generatedAt = new Date().toISOString();

  const [sitemapResult, books, posts, categories] = await Promise.all([
    fetchText(`${frontendUrl}/sitemap.xml`, "sitemap.xml"),
    fetchJson(`${apiUrl}/books`, "books.json"),
    fetchJson(`${apiUrl}/blog`, "blog.json"),
    fetchJson(`${apiUrl}/categories`, "categories.json"),
  ]);

  const sitemapUrls = extractLocs(sitemapResult.text);
  const sitemapPathSet = new Set(sitemapUrls.map((url) => pathFromUrl(url, frontendUrl)));
  const rows = [];

  function addRow(base) {
    const row = {
      url: new URL(base.path, `${frontendUrl}/`).href,
      path: base.path,
      content_type: base.type || routeType(base.path),
      title: base.title || "",
      status: base.status || "public",
      indexability: base.indexability || (isBlockedPath(base.path) ? "blocked" : "indexable"),
      sitemap_inclusion: sitemapPathSet.has(base.path) ? "included" : "excluded",
      hasTitle: Boolean(base.title),
    };
    row.growth_relevance_score = relevanceScore(row);
    row.recommended_action = recommendation({ ...row, score: row.growth_relevance_score, type: row.content_type });
    rows.push(row);
  }

  ["/", "/library", "/journal", "/about", "/contact", "/pricing", "/login", "/signup", "/micro-story"].forEach((pagePath) => {
    addRow({ path: pagePath, title: pagePath === "/" ? "Earnalism" : pagePath.slice(1), type: routeType(pagePath) });
  });

  for (const category of Array.isArray(categories) ? categories : []) {
    if (!category?.slug) continue;
    addRow({
      path: `/library?category=${encodeURIComponent(category.slug)}`,
      title: category.name || category.slug,
      type: "library_category",
    });
  }

  for (const book of Array.isArray(books) ? books : []) {
    if (!book?.slug || book.is_published === false) continue;
    addRow({
      path: `/book/${book.slug}`,
      title: book.title || book.slug,
      type: "book",
      status: "published",
    });
  }

  for (const post of Array.isArray(posts) ? posts : []) {
    if (!post?.slug || post.is_published === false) continue;
    addRow({
      path: `/journal/${post.slug}`,
      title: post.title || post.slug,
      type: "journal_post",
      status: "published",
    });
  }

  for (const pagePath of KNOWN_REMOVED_URLS) {
    addRow({
      path: pagePath,
      title: pagePath.split("/").filter(Boolean).join(" "),
      type: "removed_demo_or_ecommerce",
      status: "removed",
      indexability: "blocked",
    });
  }

  const unique = [];
  const seen = new Set();
  for (const row of rows) {
    if (seen.has(row.path)) continue;
    seen.add(row.path);
    unique.push(row);
  }

  unique.sort((a, b) => a.path.localeCompare(b.path));
  const summary = {
    generated_at: generatedAt,
    frontend_url: frontendUrl,
    api_url: apiUrl,
    total_urls: unique.length,
    sitemap_urls: sitemapUrls.length,
    recommendations: unique.reduce((acc, row) => {
      acc[row.recommended_action] = (acc[row.recommended_action] || 0) + 1;
      return acc;
    }, {}),
    blocked_terms: BLOCKED_TERMS,
    blocked_prefixes: BLOCKED_PREFIXES,
  };

  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  await fs.writeFile(
    path.join(OUTPUT_DIR, "catalog_audit_report.json"),
    `${JSON.stringify({ summary, rows: unique }, null, 2)}\n`,
    "utf8",
  );
  const columns = [
    "url",
    "content_type",
    "title",
    "status",
    "indexability",
    "sitemap_inclusion",
    "growth_relevance_score",
    "recommended_action",
  ];
  const csv = [
    columns.join(","),
    ...unique.map((row) => columns.map((column) => csvEscape(row[column])).join(",")),
  ].join("\n");
  await fs.writeFile(path.join(OUTPUT_DIR, "catalog_audit_report.csv"), `${csv}\n`, "utf8");

  const md = [
    "# Earnalism Catalog Cleanup Report",
    "",
    `Generated: ${generatedAt}`,
    "",
    "## Summary",
    "",
    `- Total audited URLs: ${summary.total_urls}`,
    `- Sitemap URLs: ${summary.sitemap_urls}`,
    `- KEEP: ${summary.recommendations.KEEP || 0}`,
    `- NOINDEX: ${summary.recommendations.NOINDEX || 0}`,
    `- REDIRECT: ${summary.recommendations.REDIRECT || 0}`,
    `- 410: ${summary.recommendations["410"] || 0}`,
    "",
    "## Removed/Demo/Ecommerce URLs",
    "",
    ...unique
      .filter((row) => row.recommended_action === "410")
      .map((row) => `- ${row.path} -> 410 Gone`),
    "",
    "## Notes",
    "",
    "- This script is dry-run/report-only and does not mutate CMS/database records.",
    "- Use admin/CMS quarantine only after reviewing the JSON and CSV report.",
    "",
  ].join("\n");
  await fs.writeFile(path.join(OUTPUT_DIR, "catalog_cleanup_report.md"), md, "utf8");

  console.log(`[catalog-audit] ${summary.total_urls} URLs audited. Reports written to ${path.relative(ROOT, OUTPUT_DIR)}.`);
}

main().catch((error) => {
  console.error(`[catalog-audit] ${error.stack || error.message}`);
  process.exitCode = 1;
});
