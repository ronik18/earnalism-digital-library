import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.resolve(__dirname, "../public");
const rootDir = path.resolve(__dirname, "../..");
const siteUrl = (process.env.REACT_APP_SITE_URL || process.env.SITE_URL || "https://theearnalism.com").replace(/\/+$/, "");
const apiBase = resolveApiBase();
const today = new Date().toISOString().slice(0, 10);
const controlledLiveSlugs = await loadControlledLiveSlugs();

const coreRoutes = [
  { path: "/", changefreq: "daily", priority: "1.0" },
  { path: "/library", changefreq: "daily", priority: "0.9" },
  { path: "/journal", changefreq: "weekly", priority: "0.8" },
  { path: "/about", changefreq: "monthly", priority: "0.7" },
  { path: "/contact", changefreq: "monthly", priority: "0.6" },
  { path: "/pricing", changefreq: "monthly", priority: "0.6" },
  { path: "/micro-story", changefreq: "monthly", priority: "0.5" },
];

const blockedPublicPathPrefixes = [
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

const blockedPublicTerms = [
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

async function loadControlledLiveSlugs() {
  try {
    const configPath = path.join(rootDir, "data", "controlled_launch.json");
    const config = JSON.parse(await readFile(configPath, "utf8"));
    const slugs = Array.isArray(config.live_approved_slugs)
      ? config.live_approved_slugs.map((slug) => String(slug || "").trim().toLowerCase()).filter(Boolean)
      : [];
    return new Set(slugs.length > 0 ? slugs : ["dracula"]);
  } catch (error) {
    console.warn(`[seo] Could not load controlled launch config: ${error.message}`);
    return new Set(["dracula"]);
  }
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

function isBlockedPublicRoute(pagePath = "") {
  const path = String(pagePath || "").toLowerCase();
  return (
    blockedPublicPathPrefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))
    || blockedPublicTerms.some((term) => path.includes(term))
  );
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

async function loadLocalControlledBooks() {
  const controlledDir = path.join(rootDir, "data", "controlled_publications");
  const books = [];
  let entries = [];
  try {
    entries = await readdir(controlledDir, { withFileTypes: true });
  } catch {
    return books;
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const slug = entry.name.trim().toLowerCase();
    if (!controlledLiveSlugs.has(slug)) continue;
    try {
      const book = JSON.parse(await readFile(path.join(controlledDir, slug, "public_book.json"), "utf8"));
      if (
        book?.slug
        && book.is_published !== false
        && book.publication_status === "LIVE_APPROVED"
        && book.allowCheckout !== true
        && book.allowPayment !== true
        && book.audio_enabled !== true
        && book.audiobook_enabled !== true
      ) {
        books.push(book);
      }
    } catch (error) {
      console.warn(`[seo] Could not load local controlled book ${slug}: ${error.message}`);
    }
  }

  return books;
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
  const [remoteBooks, posts, localControlledBooks] = await Promise.all([
    fetchJson("/books"),
    fetchJson("/blog"),
    loadLocalControlledBooks(),
  ]);
  const booksBySlug = new Map();
  for (const book of [...remoteBooks, ...localControlledBooks]) {
    if (book?.slug) booksBySlug.set(book.slug, book);
  }
  const books = Array.from(booksBySlug.values());

  const publishedBooks = books.filter((book) => (
    book?.slug
    && book.is_published !== false
    && controlledLiveSlugs.has(book.slug)
  ));
  const categoryLastmod = new Map();
  publishedBooks.forEach((book) => {
    const slug = book.category_slug;
    if (!slug) return;
    const next = dateOnly(book.updated_at || book.created_at);
    const current = categoryLastmod.get(slug);
    if (!current || next > current) categoryLastmod.set(slug, next);
  });

  const categorySlugs = new Set([
    ...publishedBooks.map((book) => book?.category_slug).filter(Boolean),
  ]);

  const categoryRoutes = Array.from(categorySlugs).sort().map((slug) => ({
    path: `/library?category=${encodeURIComponent(slug)}`,
    changefreq: "weekly",
    priority: "0.85",
    lastmod: categoryLastmod.get(slug) || today,
  }));

  const bookRoutes = publishedBooks
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
  const routes = [...coreRoutes, ...categoryRoutes, ...bookRoutes, ...journalRoutes].filter((route) => {
    if (isBlockedPublicRoute(route.path)) return false;
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
    ...Array.from(controlledLiveSlugs).sort().map((slug) => `Allow: /reader/${slug}`),
    "Disallow: /reader/",
    "Disallow: /secure-reader-test",
    "Disallow: /login",
    "Disallow: /signup",
    "Disallow: /signin",
    "Disallow: /api/",
    "",
    "# Removed demo/ecommerce URLs are intentionally crawlable during deindexing",
    "# so crawlers can observe the 410 + X-Robots-Tag response. Robots blocking",
    "# can be reconsidered later after search indexes have dropped those URLs.",
    "",
    `Sitemap: ${siteUrl}/sitemap.xml`,
    "",
  ].join("\n");

  await mkdir(publicDir, { recursive: true });
  await Promise.all([
    writeFile(path.join(publicDir, "sitemap.xml"), sitemap),
    writeFile(path.join(publicDir, "robots.txt"), robots),
  ]);

  console.log(`[seo] Wrote ${routes.length} sitemap URLs from ${categoryRoutes.length} categories, ${bookRoutes.length} books, and ${journalRoutes.length} journal posts.`);
}

main().catch((error) => {
  console.error(`[seo] ${error.stack || error.message}`);
  process.exitCode = 1;
});
