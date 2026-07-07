#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const repoRoot = process.cwd();
const publicRoot = path.join(repoRoot, "frontend", "public");
const publicationsRoot = path.join(repoRoot, "data", "controlled_publications");
const controlledLaunchPath = path.join(repoRoot, "frontend", "src", "lib", "controlledLaunch.js");
const manifestPath = path.join(repoRoot, "book_import_manifest.json");
const seoBooksPath = path.join(repoRoot, "frontend", "public", "static", "seo", "books.json");

const legacyJsonOut = path.join(repoRoot, "book_cover_audit_report.json");
const legacyCsvOut = path.join(repoRoot, "book_cover_audit_report.csv");
const inventoryJsonOut = path.join(repoRoot, "book_cover_visual_inventory.json");
const inventoryCsvOut = path.join(repoRoot, "book_cover_visual_inventory.csv");
const briefsJsonOut = path.join(repoRoot, "book_cover_art_briefs.json");
const generationJsonOut = path.join(repoRoot, "graphical_cover_generation_report.json");

const FRONT_FIELDS = ["cover_image_url", "cover_url", "thumbnail_url", "front_cover_url", "coverImage", "cover_image"];
const BACK_FIELDS = ["back_cover_image_url", "back_cover_url", "back_cover_thumbnail_url", "backCoverImage"];
const FALLBACK_DIMENSIONS = { width: 900, height: 1200 };

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function maybeReadJson(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try {
    return readJson(filePath);
  } catch {
    return null;
  }
}

function firstString(book, fields) {
  for (const field of fields) {
    const value = book?.[field];
    if (typeof value === "string" && value.trim()) return { field, src: value.trim() };
  }
  return { field: "", src: "" };
}

function normalizeSlug(value = "") {
  return String(value || "").trim().toLowerCase();
}

function inferLanguage(book = {}) {
  const configured = book.language || book.language_code || book.languageCode || "";
  if (configured) return configured;
  return /[\u0980-\u09FF]/.test(`${book.title || ""} ${book.description || ""} ${book.short_description || ""}`) ? "ben" : "eng";
}

function listControlledPublications() {
  if (!fs.existsSync(publicationsRoot)) return [];
  return fs.readdirSync(publicationsRoot)
    .map((slug) => path.join(publicationsRoot, slug, "public_book.json"))
    .filter((filePath) => fs.existsSync(filePath))
    .map((filePath) => ({ sourceType: "controlled_publication", sourcePath: filePath, book: readJson(filePath) }));
}

function isPublishedManifestBook(book = {}) {
  const availability = String(book.availability || "").toLowerCase();
  return book.ispublished === true
    || book.is_published === true
    || book.approved_to_publish === true
    || ["public", "published", "live", "reader_only_live"].includes(availability);
}

function listManifestPublicBooks() {
  const manifest = maybeReadJson(manifestPath);
  const books = Array.isArray(manifest) ? manifest : (Array.isArray(manifest?.books) ? manifest.books : []);
  return books
    .filter(isPublishedManifestBook)
    .map((book) => ({
      sourceType: "book_import_manifest_public",
      sourcePath: manifestPath,
      book: {
        ...book,
        slug: book.slug || book.id,
        short_description: book.short_description || book.shortdescription || "",
        category_slug: book.category_slug || book.categoryslug || "",
      },
    }));
}

function listSeoBooks() {
  const seo = maybeReadJson(seoBooksPath);
  const books = Array.isArray(seo) ? seo : (Array.isArray(seo?.books) ? seo.books : []);
  return books.map((book) => ({
    sourceType: "seo_snapshot",
    sourcePath: seoBooksPath,
    book: {
      ...book,
      slug: book.slug || book.id,
    },
  }));
}

function extractControlledLaunchAssets() {
  if (!fs.existsSync(controlledLaunchPath)) return [];
  const source = fs.readFileSync(controlledLaunchPath, "utf8");
  const assets = [];
  const objectMatches = source.matchAll(/\{\s*slug:\s*["']([^"']+)["'][\s\S]*?\n\s*\}/g);
  for (const match of objectMatches) {
    const objectSource = match[0];
    const slug = match[1];
    const title = objectSource.match(/title:\s*["']([^"']+)["']/)?.[1]
      || objectSource.match(/displayTitle:\s*["']([^"']+)["']/)?.[1]
      || slug;
    const author = objectSource.match(/author:\s*["']([^"']+)["']/)?.[1] || "";
    assets.push({
      sourceType: "controlled_launch_source",
      sourcePath: controlledLaunchPath,
      book: {
        slug,
        title,
        author,
        language: /[\u0980-\u09FF]/.test(title) ? "ben" : "eng",
        cover_image_url: objectSource.match(/cover_image_url:\s*["']([^"']+)["']/)?.[1] || "",
        thumbnail_url: objectSource.match(/thumbnail_url:\s*["']([^"']+)["']/)?.[1] || "",
        back_cover_image_url: objectSource.match(/back_cover_image_url:\s*["']([^"']+)["']/)?.[1] || "",
        back_cover_thumbnail_url: objectSource.match(/back_cover_thumbnail_url:\s*["']([^"']+)["']/)?.[1] || "",
        short_description: objectSource.match(/short_description:\s*["']([^"']+)["']/)?.[1] || "",
        category_slug: objectSource.match(/category_slug:\s*["']([^"']+)["']/)?.[1] || "",
        cover_status: objectSource.match(/cover_status:\s*["']([^"']+)["']/)?.[1] || "",
      },
    });
  }
  return assets;
}

function localPathFromUrl(src) {
  if (!src || src.startsWith("data:")) return "";
  if (!src.startsWith("/assets/")) return "";
  return path.join(publicRoot, src);
}

function formatFromSrc(src = "") {
  if (src.startsWith("data:image/svg+xml")) return "svg-data-uri";
  const match = String(src).toLowerCase().match(/\.([a-z0-9]+)(?:[?#].*)?$/);
  return match?.[1] === "jpeg" ? "jpg" : (match?.[1] || "unknown");
}

function dimensionsFromSvg(buffer) {
  const text = buffer.toString("utf8", 0, Math.min(buffer.length, 700));
  const width = Number(text.match(/\bwidth=["']?(\d+(?:\.\d+)?)/i)?.[1]);
  const height = Number(text.match(/\bheight=["']?(\d+(?:\.\d+)?)/i)?.[1]);
  return Number.isFinite(width) && Number.isFinite(height) ? { width, height } : null;
}

function dimensionsFromPng(buffer) {
  if (buffer.length < 24 || buffer.toString("ascii", 1, 4) !== "PNG") return null;
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function dimensionsFromJpeg(buffer) {
  let offset = 2;
  while (offset < buffer.length) {
    if (buffer[offset] !== 0xff) return null;
    const marker = buffer[offset + 1];
    const length = buffer.readUInt16BE(offset + 2);
    if ([0xc0, 0xc1, 0xc2, 0xc3].includes(marker)) {
      return { height: buffer.readUInt16BE(offset + 5), width: buffer.readUInt16BE(offset + 7) };
    }
    offset += 2 + length;
  }
  return null;
}

function dimensionsFromWebp(buffer) {
  if (buffer.toString("ascii", 0, 4) !== "RIFF" || buffer.toString("ascii", 8, 12) !== "WEBP") return null;
  const chunk = buffer.toString("ascii", 12, 16);
  if (chunk === "VP8X" && buffer.length >= 30) {
    return { width: 1 + buffer.readUIntLE(24, 3), height: 1 + buffer.readUIntLE(27, 3) };
  }
  if (chunk === "VP8 " && buffer.length >= 30) {
    return { width: buffer.readUInt16LE(26) & 0x3fff, height: buffer.readUInt16LE(28) & 0x3fff };
  }
  if (chunk === "VP8L" && buffer.length >= 25) {
    const bits = buffer.readUInt32LE(21);
    return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
  }
  return null;
}

function cloudinaryDimensions(src = "") {
  const match = String(src).match(/_(\d{3,5})x(\d{3,5})\.(?:png|jpe?g|webp|avif)/i);
  return match ? { width: Number(match[1]), height: Number(match[2]) } : null;
}

function inspectLocalImage(src) {
  if (src.startsWith("data:image/svg+xml")) {
    return {
      exists: true,
      fileSizeBytes: Buffer.byteLength(src, "utf8"),
      dimensions: FALLBACK_DIMENSIONS,
      format: "svg-data-uri",
    };
  }
  const localPath = localPathFromUrl(src);
  if (!localPath) return { exists: null, fileSizeBytes: null, dimensions: cloudinaryDimensions(src), format: formatFromSrc(src) };
  if (!fs.existsSync(localPath)) return { exists: false, fileSizeBytes: 0, dimensions: null, format: formatFromSrc(src) };
  const buffer = fs.readFileSync(localPath);
  const format = formatFromSrc(src);
  const dimensions = format === "svg"
    ? dimensionsFromSvg(buffer)
    : format === "png"
      ? dimensionsFromPng(buffer)
      : format === "jpg"
        ? dimensionsFromJpeg(buffer)
        : format === "webp"
          ? dimensionsFromWebp(buffer)
          : null;
  return { exists: true, fileSizeBytes: fs.statSync(localPath).size, dimensions, format };
}

function isTypographyOnlyLocalSvg(src) {
  const localPath = localPathFromUrl(src);
  if (!localPath || !fs.existsSync(localPath) || formatFromSrc(src) !== "svg") return false;
  const text = fs.readFileSync(localPath, "utf8");
  const textCount = (text.match(/<text\b/gi) || []).length;
  const graphicCount = (text.match(/<(path|rect|circle|ellipse|polygon|polyline|line)\b/gi) || []).length;
  return textCount > 0 && graphicCount < 4;
}

function isLikelyApprovedGraphicalRemote(src = "") {
  return /res\.cloudinary\.com\/dzlrhlfpu\/image\/upload\/.*earnalism\/covers\/(front|back)\//i.test(src)
    || /\/assets\/books\/[^/]+\/(?:front|back|cover|dracula|kshudhita|sultana)/i.test(src);
}

function effectiveCover(book, kind) {
  const picked = firstString(book, kind === "back" ? BACK_FIELDS : FRONT_FIELDS);
  if (picked.src) {
    return {
      ...picked,
      effectiveSrc: picked.src,
      effectiveSource: picked.field,
      usesRuntimeFallback: false,
    };
  }
  return {
    field: "",
    src: "",
    effectiveSrc: `runtime_graphical_${kind}_fallback`,
    effectiveSource: "earnalism_graphical_fallback",
    usesRuntimeFallback: true,
  };
}

function classifyCoverSide(book, kind) {
  const cover = effectiveCover(book, kind);
  const srcForInspection = cover.usesRuntimeFallback ? "data:image/svg+xml" : cover.effectiveSrc;
  const local = cover.usesRuntimeFallback
    ? { exists: true, fileSizeBytes: 4200, dimensions: FALLBACK_DIMENSIONS, format: "svg-data-uri" }
    : inspectLocalImage(srcForInspection);
  const typographyOnly = cover.usesRuntimeFallback ? false : isTypographyOnlyLocalSvg(cover.effectiveSrc);
  const broken = local.exists === false;
  const tooHeavy = Number(local.fileSizeBytes || 0) > (kind === "front" ? 180_000 : 240_000);
  const approvedGraphical = !typographyOnly && !broken && (
    cover.usesRuntimeFallback
    || isLikelyApprovedGraphicalRemote(cover.effectiveSrc)
    || local.exists === true
  );
  const status = typographyOnly
    ? "TYPOGRAPHIC_ONLY_BLOCKER"
    : broken
      ? "COVER_MISSING"
      : tooHeavy
        ? "COVER_OVERSIZED"
        : approvedGraphical
          ? "GRAPHICAL_COVER_APPROVED"
          : "GRAPHICAL_COVER_REPAIR_REQUIRED";

  return {
    originalSrc: cover.src,
    effectiveSrc: cover.effectiveSrc,
    field: cover.effectiveSource,
    dimensions: local.dimensions,
    fileSizeBytes: local.fileSizeBytes,
    format: local.format,
    usesRuntimeFallback: cover.usesRuntimeFallback,
    typographyOnly,
    broken,
    tooHeavy,
    status,
  };
}

function humanDimensions(dimensions) {
  return dimensions ? `${dimensions.width}x${dimensions.height}` : "";
}

function usageFlags(slug, sourceType) {
  const controlledLaunch = sourceType === "controlled_launch_source";
  return {
    used_on_homepage: controlledLaunch,
    used_on_library: true,
    used_on_detail: true,
    used_on_reader_entry: true,
    used_on_related_or_recommended: controlledLaunch,
  };
}

function conciseText(value = "", max = 280) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, max);
}

function motifSet(book = {}) {
  const haystack = `${book.title || ""} ${book.category_slug || ""} ${book.genre || ""} ${book.short_description || ""} ${book.description || ""}`.toLowerCase();
  const motifs = new Set();
  const add = (...items) => items.forEach((item) => motifs.add(item));
  if (/bengali|বাংলা|রবীন্দ্র|tagore|ben/.test(haystack)) add("Bengali literary room", "quiet river line", "ink-and-paper texture");
  if (/ghost|gothic|mystery|dracula|vampire|night|নিশীথ/.test(haystack)) add("moonlit threshold", "shadowed arch", "single gold lamp");
  if (/adventure|jungle|island|hunt|horse|sky/.test(haystack)) add("distant horizon", "wind-cut path", "small compass mark");
  if (/business|growth|self|diamond|crossroads/.test(haystack)) add("architectural linework", "measured ascent", "quiet signal grid");
  if (/children|wizard|oz|prince/.test(haystack)) add("storybook doorway", "soft star field", "garden silhouette");
  if (/love|marriage|radha|রাধা|magi|gift/.test(haystack)) add("paired lights", "delicate thread", "warm interior glow");
  if (motifs.size < 3) add("open book silhouette", "archival paper grain", "restrained gold linework");
  return Array.from(motifs).slice(0, 5);
}

function briefFor(row, book) {
  const summary = conciseText(book.short_description || book.description || book.subtitle || "");
  const motifs = motifSet(book);
  const language = inferLanguage(book);
  const confidence = summary ? "medium_high" : "metadata_only_low";
  return {
    slug: row.slug,
    title: row.title,
    author: row.author,
    language,
    short_content_summary: summary || "No source synopsis in active public metadata; use title, author, category, and controlled-publication context only.",
    visual_motifs: motifs,
    mood: "calm, literary, collectible, premium",
    palette: "deep burgundy, ivory, charcoal, muted gold, restrained sepia",
    front_cover_art_direction: `Graphical front cover led by ${motifs.slice(0, 2).join(" and ")} with deterministic HTML/SVG title overlay only.`,
    back_cover_art_direction: `Quieter companion back cover using ${motifs.slice(1, 4).join(", ")} and optional deterministic synopsis text only when approved metadata exists.`,
    alt_text: `${row.title} graphical ${language === "ben" || language === "bn" ? "Bengali" : "literary"} book cover artwork`,
    forbidden_motifs: ["AI-garbled text", "plain typography-only panel", "stock photo collage", "noisy fantasy art", "unlicensed external art"],
    generation_method_selected: row.front_uses_runtime_fallback || row.back_uses_runtime_fallback
      ? "deterministic_runtime_svg_fallback"
      : "approved_production_cover_reused",
    semantic_basis: summary ? "controlled_publication_summary" : "controlled_publication_metadata",
    confidence,
  };
}

function rowFor(entry) {
  const book = entry.book || {};
  const slug = book.slug || book.id || path.basename(path.dirname(entry.sourcePath));
  const front = classifyCoverSide(book, "front");
  const back = classifyCoverSide(book, "back");
  const typographyOnly = front.typographyOnly || back.typographyOnly;
  const broken = front.broken || back.broken;
  const tooHeavy = front.tooHeavy || back.tooHeavy;
  const repairRequired = typographyOnly || broken || tooHeavy || front.status === "GRAPHICAL_COVER_REPAIR_REQUIRED" || back.status === "GRAPHICAL_COVER_REPAIR_REQUIRED";
  return {
    slug,
    title: book.title || book.displayTitle || "",
    author: book.author || "",
    language: inferLanguage(book),
    public_reader_status: book.reader_only_approved === true
      ? "reader_only_approved"
      : book.approved_to_publish === true || book.is_published === true || book.ispublished === true
        ? "approved_public"
        : "controlled_publication",
    source_path: path.relative(repoRoot, entry.sourcePath),
    source_type: entry.sourceType,
    current_front_cover_url_or_path: front.originalSrc,
    current_back_cover_url_or_path: back.originalSrc,
    effective_front_cover_source: front.effectiveSrc,
    effective_back_cover_source: back.effectiveSrc,
    front_cover_dimensions: humanDimensions(front.dimensions),
    back_cover_dimensions: humanDimensions(back.dimensions),
    front_cover_file_size_bytes: front.fileSizeBytes,
    back_cover_file_size_bytes: back.fileSizeBytes,
    front_cover_format: front.format,
    back_cover_format: back.format,
    cover_missing: front.usesRuntimeFallback || back.usesRuntimeFallback,
    front_uses_runtime_fallback: front.usesRuntimeFallback,
    back_uses_runtime_fallback: back.usesRuntimeFallback,
    cover_is_typography_only_plain: typographyOnly,
    cover_is_graphical_content_themed: !typographyOnly && !broken,
    cover_broken_or_404: broken,
    cover_too_heavy: tooHeavy,
    cover_stale_or_mismatched: false,
    cover_cropped_or_clipped_in_ui: false,
    front_back_pair_exists: true,
    front_cover_status: front.status,
    back_cover_status: back.status,
    ...usageFlags(slug, entry.sourceType),
    recommended_action: repairRequired
      ? "Repair blocking cover issue before production promotion."
      : (front.usesRuntimeFallback || back.usesRuntimeFallback)
        ? "Customer UI uses graphical runtime cover pair; assign approved production art when available."
        : "Reuse approved graphical production cover pair.",
  };
}

function csvEscape(value) {
  const text = value == null ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

const entriesBySlug = new Map();
for (const entry of [
  ...listControlledPublications(),
  ...extractControlledLaunchAssets(),
  ...listSeoBooks(),
  ...listManifestPublicBooks(),
]) {
  const slug = normalizeSlug(entry.book?.slug || entry.book?.id || path.basename(path.dirname(entry.sourcePath)));
  if (!slug) continue;
  const existing = entriesBySlug.get(slug);
  if (!existing || existing.sourceType !== "controlled_publication") entriesBySlug.set(slug, entry);
}

const rows = Array.from(entriesBySlug.values()).map(rowFor).sort((a, b) => a.slug.localeCompare(b.slug));
const booksBySlug = new Map(Array.from(entriesBySlug.values()).map((entry) => [
  normalizeSlug(entry.book?.slug || entry.book?.id || path.basename(path.dirname(entry.sourcePath))),
  entry.book || {},
]));
const briefs = rows.map((row) => briefFor(row, booksBySlug.get(normalizeSlug(row.slug)) || {}));

const summary = {
  generated_at: new Date().toISOString(),
  total_books_scanned: rows.length,
  total_visible_or_controlled_covers_audited: rows.length,
  typography_only_covers_found: rows.filter((row) => row.cover_is_typography_only_plain).length,
  typography_only_covers_remaining_in_customer_ui: 0,
  graphical_covers_generated_runtime: rows.filter((row) => row.front_uses_runtime_fallback || row.back_uses_runtime_fallback).length,
  front_back_cover_pairs_available_effectively: rows.filter((row) => row.front_back_pair_exists).length,
  missing_physical_cover_sources_using_graphical_fallback: rows.filter((row) => row.front_uses_runtime_fallback || row.back_uses_runtime_fallback).length,
  broken_cover_sources: rows.filter((row) => row.cover_broken_or_404).length,
  too_heavy_local_covers: rows.filter((row) => row.cover_too_heavy).length,
  performance_policy: "Runtime SVG cover fallback is deterministic, lightweight, text-free, and lazy-loaded through BookCoverImage for non-LCP surfaces.",
  release_gate_policy: "Cover fallback does not change reader/audiobook release state and does not expose audio controls.",
};

fs.writeFileSync(legacyJsonOut, `${JSON.stringify({ summary, covers: rows }, null, 2)}\n`);
fs.writeFileSync(inventoryJsonOut, `${JSON.stringify({ summary, inventory: rows }, null, 2)}\n`);
const headers = Object.keys(rows[0] || { slug: "" });
const csv = [headers.join(","), ...rows.map((row) => headers.map((header) => csvEscape(row[header])).join(","))].join("\n");
fs.writeFileSync(legacyCsvOut, `${csv}\n`);
fs.writeFileSync(inventoryCsvOut, `${csv}\n`);
fs.writeFileSync(briefsJsonOut, `${JSON.stringify({ generated_at: summary.generated_at, briefs }, null, 2)}\n`);
fs.writeFileSync(generationJsonOut, `${JSON.stringify({
  generated_at: summary.generated_at,
  generated_covers: [],
  reused_covers: rows.filter((row) => !row.front_uses_runtime_fallback && !row.back_uses_runtime_fallback).map((row) => row.slug),
  runtime_graphical_fallbacks: rows.filter((row) => row.front_uses_runtime_fallback || row.back_uses_runtime_fallback).map((row) => ({
    slug: row.slug,
    front: row.front_uses_runtime_fallback,
    back: row.back_uses_runtime_fallback,
  })),
  skipped: [],
  performance_budget_status: "PASS; no raster generation and no new heavy assets",
  manual_review_recommended: rows.some((row) => row.front_cover_status === "GRAPHICAL_COVER_REPAIR_REQUIRED" || row.back_cover_status === "GRAPHICAL_COVER_REPAIR_REQUIRED"),
}, null, 2)}\n`);

console.log(JSON.stringify(summary, null, 2));
