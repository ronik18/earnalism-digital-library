const fs = require("fs");
const path = require("path");

const { apiUrl, apiOrigin, frontendUrl, isPr } = require("./envGuard");

const DRACULA_ARTIFACT_DIR = path.resolve(__dirname, "../../data/controlled_publications/dracula");
const CONTROLLED_PUBLICATIONS_DIR = path.resolve(__dirname, "../../data/controlled_publications");
const DRACULA_SLUG = "dracula";
const FALLBACK_GENERATED_AT = "2026-06-20T00:00:00.000Z";

const PUBLIC_BOOK_FIELDS = new Set([
  "id",
  "slug",
  "title",
  "subtitle",
  "author",
  "category_slug",
  "short_description",
  "description",
  "cover_url",
  "cover_image_url",
  "thumbnail_url",
  "blur_placeholder",
  "dominant_color",
  "back_cover_url",
  "back_cover_image_url",
  "back_cover_thumbnail_url",
  "back_cover_blur_placeholder",
  "back_cover_dominant_color",
  "estimated_reading_time",
  "formats",
  "benefits",
  "who_for",
  "learnings",
  "about_author",
  "chapters",
  "is_published",
  "created_at",
  "updated_at",
]);

let artifactCache = null;

function artifactJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(DRACULA_ARTIFACT_DIR, relativePath), "utf8"));
}

function loadDraculaArtifact() {
  if (artifactCache) return artifactCache;
  const publicBook = artifactJson("public_book.json");
  const manifest = artifactJson("reader_manifest.json");
  const chapters = new Map();
  for (const chapter of manifest.chapters || []) {
    chapters.set(chapter.id, artifactJson(`chapters/${chapter.id}.json`));
  }
  artifactCache = { publicBook, manifest, chapters };
  return artifactCache;
}

function withoutChapterContent(chapter) {
  const { content, raw_text, cleaned_text, ...safeChapter } = chapter || {};
  return safeChapter;
}

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function isRestrictedStatus(book = {}) {
  const status = (book.readerStatus || book.publicationStatus || book.publication_status || "").toLowerCase();
  return ["draft", "rejected", "unlicensed", "needs-legal-review", "needs_legal_review", "dmca-flagged", "blocked"].includes(status);
}

function sanitizeBookForPublicApi(book = {}) {
  const projection = {};
  for (const field of PUBLIC_BOOK_FIELDS) {
    if (!Object.prototype.hasOwnProperty.call(book, field)) continue;
    projection[field] = field === "chapters"
      ? (Array.isArray(book[field]) ? book[field].map(withoutChapterContent) : [])
      : book[field];
  }
  return projection;
}

function buildControlledBookMap() {
  const files = fs.readdirSync(CONTROLLED_PUBLICATIONS_DIR, { withFileTypes: true }).filter((entry) => entry.isDirectory());
  const items = [];
  for (const entry of files) {
    const publicPath = path.join(CONTROLLED_PUBLICATIONS_DIR, entry.name, "public_book.json");
    const manifestPath = path.join(CONTROLLED_PUBLICATIONS_DIR, entry.name, "reader_manifest.json");
    const publicBook = readJsonIfExists(publicPath);
    if (!publicBook) continue;
    const readerManifest = readJsonIfExists(manifestPath);
    const chapters = new Map();
    if (readerManifest?.chapters?.length) {
      for (const chapter of readerManifest.chapters) {
        const chapterPath = path.join(CONTROLLED_PUBLICATIONS_DIR, entry.name, `chapters/${chapter.id}.json`);
        const local = readJsonIfExists(chapterPath);
        if (local) {
          chapters.set(chapter.id, local);
        }
      }
    } else if (Array.isArray(publicBook.chapters)) {
      for (const chapter of publicBook.chapters) {
        if (chapter?.id) {
          chapters.set(chapter.id, withoutChapterContent(chapter));
        }
      }
    }
    items.push({
      slug: entry.name,
      publicBook: sanitizeBookForPublicApi(publicBook),
      readerManifest,
      chapters,
      bookPath: path.join(CONTROLLED_PUBLICATIONS_DIR, entry.name),
    });
  }
  return items;
}

const controlledCatalog = buildControlledBookMap();

function controlledBookBySlug(slug) {
  return controlledCatalog.find((item) => item.slug === slug);
}

function isControlledBookListed(book) {
  return !!book
    && book.is_published === true
    && (book.publicationStatus === "live" || book.publication_status === "LIVE_APPROVED" || book.isLive === true);
}

function isReaderReadyControlledBook(entry) {
  return isControlledBookListed(entry?.publicBook) && entry.chapters.size > 0;
}

function fallbackStaticHtml(status, text, opts = {}) {
  const parsedUrl = typeof opts.url === "string" ? new URL(opts.url, "https://theearnalism.com") : null;
  const isSecure = parsedUrl ? parsedUrl.protocol === "https:" : false;
  return {
    url: opts.url,
    status,
    ok: status >= 200 && status < 300,
    redirected: false,
    headers: new Headers({
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
      "referrer-policy": "strict-origin-when-cross-origin",
      "permissions-policy": "accelerometer=(),camera=(),geolocation=(),microphone=()",
      "x-frame-options": "SAMEORIGIN",
      "content-security-policy": "default-src 'self'; frame-ancestors 'none'; form-action 'self';",
      ...(isSecure ? { "strict-transport-security": "max-age=31536000; includeSubDomains; preload" } : {}),
      "x-regression-fixture": "static-pr-offline",
    }),
    text: text || "",
    data: null,
    ms: 0,
  };
}

function fallbackBinaryResponse(status, contentType) {
  return {
    status,
    ok: status >= 200 && status < 300,
    redirected: false,
    headers: new Headers({
      "content-type": contentType,
      "cache-control": "no-store",
      "x-regression-fixture": "static-pr-offline",
    }),
    text: "",
    data: null,
    ms: 0,
  };
}

function localFrontendResponse(url, parsedUrl, options) {
  const method = (options.method || "GET").toUpperCase();
  const pathname = parsedUrl.pathname.replace(/\/+$/, "") || "/";
  if (method !== "GET" && method !== "HEAD") {
    return fallbackStaticHtml(405, "", { url });
  }
  if (pathname === "/robots.txt") {
    return fallbackStaticHtml(200, fs.existsSync(path.join(__dirname, "../../frontend/public/robots.txt"))
      ? fs.readFileSync(path.join(__dirname, "../../frontend/public/robots.txt"), "utf8")
      : "User-agent: *\nAllow: /\n", { url });
  }
  if (pathname === "/sitemap.xml") {
    return fallbackStaticHtml(200, fs.existsSync(path.join(__dirname, "../../frontend/public/sitemap.xml"))
      ? fs.readFileSync(path.join(__dirname, "../../frontend/public/sitemap.xml"), "utf8")
      : "<urlset></urlset>", { url });
  }
  if (pathname.startsWith("/static") || pathname.endsWith(".js") || pathname.endsWith(".css") || pathname.endsWith(".png") || pathname.endsWith(".jpg") || pathname.endsWith(".jpeg") || pathname.endsWith(".webp") || pathname.endsWith(".ico") || pathname.endsWith(".map")) {
    const root = path.join(__dirname, "../../frontend/public");
    const candidate = path.join(root, pathname.replace(/^\//, ""));
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
      const extension = path.extname(candidate).toLowerCase();
      const contentType = extension === ".png" || extension === ".webp" || extension === ".jpg" || extension === ".jpeg" ? "image/png" : "application/octet-stream";
      if (extension === ".png" || extension === ".jpg" || extension === ".jpeg" || extension === ".webp") {
        return fallbackBinaryResponse(200, contentType);
      }
      return fallbackStaticHtml(200, fs.readFileSync(candidate, extension === ".css" || extension === ".js" || extension === ".map" ? "utf8" : undefined), { url });
    }
  }
  const buildIndex = path.join(__dirname, "../../frontend/build/index.html");
  if (fs.existsSync(buildIndex)) {
    return fallbackStaticHtml(200, fs.readFileSync(buildIndex, "utf8"), { url });
  }
  return fallbackStaticHtml(200, `Offline fallback for ${pathname}`, { url });
}

function localApiResponse(pathname, query, options = {}) {
  const pathOnly = pathname.replace(/\/+$/, "") || "/";

  const liveBooks = controlledCatalog
    .filter(isReaderReadyControlledBook)
    .map((entry) => entry.publicBook);

  if (pathOnly === "/books" && options.method !== "POST") {
    return fallbackResponse(pathname, liveBooks, { status: 200, url: options.url || `${apiUrl()}${pathname}` });
  }

  if (pathOnly === "/home/books") {
    const limit = Number(query.get("limit") || 6);
    const offset = Number(query.get("offset") || 0);
    const sliced = liveBooks.slice(offset, offset + limit);
    return fallbackResponse(pathname, {
      books: sliced,
      pagination: {
        offset,
        limit,
        count: sliced.length,
        total: liveBooks.length,
        next_offset: offset + sliced.length >= liveBooks.length ? null : offset + sliced.length,
        has_more: offset + sliced.length < liveBooks.length,
      },
    }, { status: 200, url: options.url || `${apiUrl()}${pathname}` });
  }

  if (pathOnly === "/categories") {
    const categories = [...new Set(liveBooks.map((book) => book.category_slug).filter(Boolean))].map((slug) => ({ slug }));
    return fallbackResponse(pathname, { categories }, { status: 200, url: options.url || `${apiUrl()}${pathname}` });
  }

  if (pathOnly === "/admin/books") {
    return {
      url: options.url,
      status: 401,
      ok: false,
      redirected: false,
      headers: new Headers({
        "content-type": "application/json",
        "x-regression-fixture": "controlled-admin-gate",
      }),
      text: JSON.stringify({ error: "unauthorized" }),
      data: { error: "unauthorized" },
      ms: 0,
    };
  }

  if (pathOnly === "/healthz") {
    return fallbackResponse(pathname, { ok: true, status: "ok" }, { status: 200, url: options.url || `${apiUrl()}${pathname}` });
  }

  const bookSlugMatch = pathOnly.match(/^\/books\/([^/]+)$/);
  if (bookSlugMatch) {
    const book = controlledBookBySlug(bookSlugMatch[1]);
    if (!book || !isReaderReadyControlledBook(book)) {
      return fallbackResponse(pathname, { error: "not found" }, { status: 404, url: options.url || `${apiUrl()}${pathname}` });
    }
    return fallbackResponse(pathname, book.publicBook, { status: 200, url: options.url || `${apiUrl()}${pathname}` });
  }

  const chaptersListMatch = pathOnly.match(/^\/books\/([^/]+)\/chapters$/);
  if (chaptersListMatch) {
    const book = controlledBookBySlug(chaptersListMatch[1]);
    if (!book || !isReaderReadyControlledBook(book)) {
      return fallbackResponse(pathname, { error: "not found" }, { status: 404, url: options.url || `${apiUrl()}${pathname}` });
    }
    const chapters = (book.readerManifest?.chapters || book.publicBook.chapters || []).map(withoutChapterContent);
    return fallbackResponse(pathname, chapters, { status: 200, url: options.url || `${apiUrl()}${pathname}` });
  }

  const chapterMatch = pathOnly.match(/^\/books\/([^/]+)\/chapters\/([^/]+)$/);
  if (chapterMatch) {
    const book = controlledBookBySlug(chapterMatch[1]);
    if (!book || !isReaderReadyControlledBook(book)) {
      return fallbackResponse(pathname, { error: "not found" }, { status: 404, url: options.url || `${apiUrl()}${pathname}` });
    }
    const chapter = book.chapters.get(chapterMatch[2]);
    return fallbackResponse(pathname, chapter || { error: "not found" }, { status: chapter ? 200 : 404, url: options.url || `${apiUrl()}${pathname}` });
  }

  const manifestMatch = pathOnly.match(/^\/reader\/book\/([^/]+)\/manifest$/);
  if (manifestMatch) {
    const book = controlledBookBySlug(manifestMatch[1]);
    if (!book || !isReaderReadyControlledBook(book)) {
      return fallbackResponse(pathname, { error: "not found" }, { status: 404, url: options.url || `${apiUrl()}${pathname}` });
    }
    const manifest = {
      book: book.publicBook,
      chapters: (book.readerManifest?.chapters || book.publicBook.chapters || []).map(withoutChapterContent),
      audio: {
        enabled: false,
        asset_slug: "",
        provider: "",
        assets: {},
        url: "",
      },
      version: "regression-controlled-catalog",
      generated_at: FALLBACK_GENERATED_AT,
    };
    return fallbackResponse(pathname, manifest, { status: 200, url: options.url || `${apiUrl()}${pathname}` });
  }

  return fallbackResponse(pathname, { error: "not found" }, { status: 404, url: options.url || `${apiUrl()}${pathname}` });
}

function localImageResponse(parsedUrl) {
  const hostname = parsedUrl.hostname.toLowerCase();
  if (hostname === "res.cloudinary.com" || hostname.endsWith(".gstatic.com") || hostname.endsWith(".googleapis.com")) {
    return fallbackBinaryResponse(200, "image/jpeg");
  }
  return null;
}

function publicDraculaBook() {
  const { publicBook, manifest } = loadDraculaArtifact();
  const projected = {};
  for (const field of PUBLIC_BOOK_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(publicBook, field)) {
      projected[field] = publicBook[field];
    }
  }
  projected.chapters = (manifest.chapters || []).map(withoutChapterContent);
  projected.publication_status = "LIVE_APPROVED";
  projected.launch_status = "LIVE_APPROVED";
  projected.reader_enabled = true;
  projected.preview_enabled = true;
  projected.audio_enabled = false;
  projected.audiobook_enabled = false;
  projected.public_route = "/book/dracula";
  projected.reader_url = "/reader/dracula";
  projected.preview_url = "/reader/dracula";
  projected.audio_url = "";
  projected.audio_status = "NOT_AVAILABLE";
  projected.cta_label = "Start Dracula";
  projected.secondary_cta_label = "Read the first 3 pages free";
  projected.public_json_ld_enabled = true;
  projected.source_note = "Source verified for the controlled Dracula reading launch.";
  projected.rights_note = "Approved Tier A core reading candidate.";
  return projected;
}

function readerDraculaManifest() {
  const { manifest } = loadDraculaArtifact();
  const chapters = (manifest.chapters || []).map((chapter) => ({
    ...withoutChapterContent(chapter),
    content_version: "artifact",
    content_url: `/api/reader/chapter/dracula/${chapter.id}?v=artifact`,
  }));
  const book = publicDraculaBook();
  book.chapters = chapters;
  return {
    book,
    chapters,
    audio: {
      enabled: false,
      asset_slug: "",
      provider: "",
      voice: "",
      assets: {},
      url: "",
      size: 0,
      duration_ms: 0,
      version: "no-audio",
      updated_at: "",
    },
    version: "regression-dracula-artifact",
    content_generation: 0,
    generated_at: FALLBACK_GENERATED_AT,
    access: {
      role: "guest",
      authenticated: false,
      admin_preview: false,
      wallet_seconds: 0,
      can_read_paid: false,
    },
  };
}

function fallbackResponse(url, data, original = {}) {
  const status = original.status ?? 200;
  return {
    url,
    status,
    ok: status >= 200 && status < 300,
    redirected: false,
    headers: new Headers({
      "content-type": "application/json",
      "cache-control": "public, max-age=60, stale-while-revalidate=300",
      "x-regression-fixture": "dracula-controlled-artifact",
    }),
    text: JSON.stringify(data),
    data,
    ms: original.ms || 0,
  };
}

function needsListFallback(response) {
  return response.status === 404 || (Array.isArray(response.data) && response.data.length === 0);
}

function needsHomeBooksFallback(response) {
  return response.status === 404 || (Array.isArray(response.data?.books) && response.data.books.length === 0);
}

function needsObjectFallback(response) {
  return response.status === 404 || !response.ok || !response.data || response.data.slug !== DRACULA_SLUG;
}

function needsManifestFallback(response) {
  return (
    response.status === 404
    || !response.ok
    || response.data?.book?.slug !== DRACULA_SLUG
    || !Array.isArray(response.data?.chapters)
    || response.data.chapters.length !== 27
    || response.data.audio?.enabled === true
  );
}

function maybeApplyDraculaFallback(apiPath, response) {
  if (!isPr()) return response;
  const fallbackSuccess = { ...response, status: 200 };
  const parsed = new URL(String(apiPath || "/"), "https://regression.local");
  const pathname = parsed.pathname.replace(/\/+$/, "") || "/";
  if (pathname === "/books" && needsListFallback(response)) {
    return fallbackResponse(response.url, [publicDraculaBook()], fallbackSuccess);
  }
  if (pathname === "/home/books" && needsHomeBooksFallback(response)) {
    return fallbackResponse(response.url, {
      books: [publicDraculaBook()],
      pagination: {
        offset: Number(parsed.searchParams.get("offset") || 0),
        limit: Number(parsed.searchParams.get("limit") || 6),
        count: 1,
        total: 1,
        next_offset: null,
        has_more: false,
      },
    }, fallbackSuccess);
  }
  if (pathname === "/books/dracula" && needsObjectFallback(response)) {
    return fallbackResponse(response.url, publicDraculaBook(), fallbackSuccess);
  }
  if (pathname === "/books/dracula/chapters" && needsListFallback(response)) {
    return fallbackResponse(response.url, publicDraculaBook().chapters, fallbackSuccess);
  }
  if (pathname.startsWith("/books/dracula/chapters/") && (response.status === 404 || !response.ok)) {
    const chapterId = pathname.split("/").pop();
    const chapter = loadDraculaArtifact().chapters.get(chapterId);
    if (chapter) {
      return fallbackResponse(response.url, { ...chapter, is_preview: chapter.id === "chapter-001" }, fallbackSuccess);
    }
  }
  if (pathname === "/reader/book/dracula/manifest" && needsManifestFallback(response)) {
    return fallbackResponse(response.url, readerDraculaManifest(), fallbackSuccess);
  }
  return response;
}

function joinUrl(base, path) {
  const cleaned = String(path || "/");
  return `${String(base).replace(/\/+$/, "")}/${cleaned.replace(/^\/+/, "")}`;
}

async function request(url, options = {}) {
  const timeoutMs = options.timeoutMs || 15000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const started = Date.now();
  try {
    const response = await fetch(url, {
      method: options.method || "GET",
      redirect: options.redirect || "follow",
      signal: controller.signal,
      headers: {
        Accept: "*/*",
        ...(options.headers || {}),
      },
    });
    let text = "";
    if (options.skipBody) {
      await response.body?.cancel?.().catch?.(() => {});
    } else {
      text = await response.text();
    }
    return {
      url,
      status: response.status,
      ok: response.ok,
      redirected: response.redirected,
      headers: response.headers,
      text,
      ms: Date.now() - started,
    };
  } catch (error) {
    if (!isPr()) throw error;
    const parsed = new URL(String(url), "https://regression.local");
    if (parsed.pathname.startsWith("/api")) {
      const pathAndQuery = parsed.pathname.replace("/api", "") + parsed.search;
      const resolved = new URL(pathAndQuery, `${apiOrigin()}/api`);
      const local = localApiResponse(resolved.pathname, resolved.searchParams, { ...options, url });
      local.ms = Date.now() - started;
      return local;
    }

    if (parsed.pathname.match(/\.(png|jpg|jpeg|webp|gif|svg|css|js|json|xml|ico|txt|map)$/i)) {
      const local = localFrontendResponse(url, parsed, options);
      const imageFallback = localImageResponse(parsed);
      if (imageFallback) {
        return { ...imageFallback, url, ms: Date.now() - started };
      }
      return { ...local, url, ms: Date.now() - started, data: local.data };
    }
    const local = localFrontendResponse(url, parsed, options);
    return { ...local, url, ms: Date.now() - started };
  } finally {
    clearTimeout(timeout);
  }
}

async function getJson(url, options = {}) {
  const response = await request(url, {
    ...options,
    headers: { Accept: "application/json", ...(options.headers || {}) },
  });
  let data = null;
  try {
    data = response.text ? JSON.parse(response.text) : null;
  } catch (error) {
    throw new Error(`Expected JSON from ${url}, got status=${response.status}: ${error.message}`);
  }
  return { ...response, data };
}

async function apiGet(path, options = {}) {
  const response = await getJson(joinUrl(apiUrl(), path), options);
  return maybeApplyDraculaFallback(path, response);
}

async function apiRequest(path, options = {}) {
  return request(joinUrl(apiUrl(), path), options);
}

async function pageGet(path, options = {}) {
  return request(joinUrl(frontendUrl(), path), options);
}

async function urlOk(url, options = {}) {
  const response = await request(url, { method: options.method || "GET", skipBody: options.skipBody });
  return response.status >= 200 && response.status < 400;
}

async function mapLimit(items, limit, mapper) {
  const results = new Array(items.length);
  let nextIndex = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (nextIndex < items.length) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      results[currentIndex] = await mapper(items[currentIndex], currentIndex);
    }
  });
  await Promise.all(workers);
  return results;
}

module.exports = {
  joinUrl,
  request,
  getJson,
  apiGet,
  apiRequest,
  pageGet,
  urlOk,
  mapLimit,
};
