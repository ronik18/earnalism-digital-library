import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.resolve(__dirname, "../public");
const siteUrl = (process.env.REACT_APP_SITE_URL || process.env.SITE_URL || "https://theearnalism.com").replace(/\/+$/, "");
const apiBase = resolveApiBase();
const today = new Date().toISOString().slice(0, 10);

const coreRoutes = [
  { path: "/", changefreq: "daily", priority: "1.0" },
  { path: "/library", changefreq: "daily", priority: "0.9" },
  { path: "/journal", changefreq: "weekly", priority: "0.8" },
  { path: "/about", changefreq: "monthly", priority: "0.7" },
  { path: "/contact", changefreq: "monthly", priority: "0.6" },
  { path: "/pricing", changefreq: "monthly", priority: "0.6" },
  { path: "/micro-story", changefreq: "monthly", priority: "0.5" },
];

function resolveApiBase() {
  const raw = (
    process.env.REACT_APP_BACKEND_URL ||
    process.env.REACT_APP_API_URL ||
    process.env.SEO_API_BASE_URL ||
    "https://api.theearnalism.com"
  ).replace(/\/+$/, "");

  if (!raw || raw.startsWith("/")) return "https://api.theearnalism.com/api";
  return raw.endsWith("/api") ? raw : `${raw}/api`;
}

function escapeXml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function absolutePageUrl(pagePath) {
  return new URL(pagePath, `${siteUrl}/`).href.replace(/\/$/, pagePath === "/" ? "/" : "");
}

function dateOnly(value) {
  if (!value) return today;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return today;
  return date.toISOString().slice(0, 10);
}

async function fetchJson(endpoint) {
  const url = `${apiBase}${endpoint}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.warn(`[seo] Could not load ${url}: ${error.message}`);
    return [];
  } finally {
    clearTimeout(timeout);
  }
}

function sitemapEntry({ path: pagePath, changefreq, priority, lastmod = today }) {
  return [
    "  <url>",
    `    <loc>${escapeXml(absolutePageUrl(pagePath))}</loc>`,
    `    <lastmod>${escapeXml(lastmod)}</lastmod>`,
    `    <changefreq>${escapeXml(changefreq)}</changefreq>`,
    `    <priority>${escapeXml(priority)}</priority>`,
    "  </url>",
  ].join("\n");
}

async function main() {
  const [books, posts] = await Promise.all([
    fetchJson("/books"),
    fetchJson("/blog"),
  ]);

  const bookRoutes = books
    .filter((book) => book?.slug && book.is_published !== false)
    .map((book) => ({
      path: `/book/${book.slug}`,
      changefreq: "weekly",
      priority: "0.8",
      lastmod: dateOnly(book.updated_at || book.created_at),
    }));

  const journalRoutes = posts
    .filter((post) => post?.slug && post.is_published !== false)
    .map((post) => ({
      path: `/journal/${post.slug}`,
      changefreq: "monthly",
      priority: "0.7",
      lastmod: dateOnly(post.updated_at || post.created_at),
    }));

  const seen = new Set();
  const routes = [...coreRoutes, ...bookRoutes, ...journalRoutes].filter((route) => {
    if (seen.has(route.path)) return false;
    seen.add(route.path);
    return true;
  });

  const sitemap = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...routes.map(sitemapEntry),
    "</urlset>",
    "",
  ].join("\n");

  const robots = [
    "User-agent: *",
    "Allow: /",
    "Disallow: /admin",
    "Disallow: /admin/",
    "Disallow: /account",
    "Disallow: /reader/",
    "Disallow: /secure-reader-test",
    "Disallow: /login",
    "Disallow: /signup",
    "Disallow: /api/",
    "",
    `Sitemap: ${siteUrl}/sitemap.xml`,
    "",
  ].join("\n");

  await mkdir(publicDir, { recursive: true });
  await Promise.all([
    writeFile(path.join(publicDir, "sitemap.xml"), sitemap),
    writeFile(path.join(publicDir, "robots.txt"), robots),
  ]);

  console.log(`[seo] Wrote ${routes.length} sitemap URLs from ${bookRoutes.length} books and ${journalRoutes.length} journal posts.`);
}

main().catch((error) => {
  console.error(`[seo] ${error.stack || error.message}`);
  process.exitCode = 1;
});
