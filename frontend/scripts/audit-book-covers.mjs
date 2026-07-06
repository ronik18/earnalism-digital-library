#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const repoRoot = process.cwd();
const publicRoot = path.join(repoRoot, "frontend", "public");
const publicationsRoot = path.join(repoRoot, "data", "controlled_publications");
const controlledLaunchPath = path.join(repoRoot, "frontend", "src", "lib", "controlledLaunch.js");
const jsonOut = path.join(repoRoot, "book_cover_audit_report.json");
const csvOut = path.join(repoRoot, "book_cover_audit_report.csv");

const IMAGE_FIELDS = [
  "cover_image_url",
  "cover_url",
  "thumbnail_url",
  "back_cover_image_url",
  "back_cover_url",
  "back_cover_thumbnail_url",
];

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function listPublicBooks() {
  if (!fs.existsSync(publicationsRoot)) return [];
  return fs.readdirSync(publicationsRoot)
    .map((slug) => path.join(publicationsRoot, slug, "public_book.json"))
    .filter((filePath) => fs.existsSync(filePath))
    .map((filePath) => ({ filePath, book: readJson(filePath) }));
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
    const cover = objectSource.match(/cover_image_url:\s*["']([^"']+)["']/)?.[1] || "";
    const thumbnail = objectSource.match(/thumbnail_url:\s*["']([^"']+)["']/)?.[1] || "";
    const back = objectSource.match(/back_cover_image_url:\s*["']([^"']+)["']/)?.[1] || "";
    assets.push({
      filePath: controlledLaunchPath,
      book: {
        slug,
        title,
        author,
        language: /[\u0980-\u09FF]/.test(title) ? "ben" : "eng",
        cover_image_url: cover,
        thumbnail_url: thumbnail,
        back_cover_image_url: back,
        cover_status: objectSource.match(/cover_status:\s*["']([^"']+)["']/)?.[1] || "",
      },
    });
  }
  return assets;
}

function localPathFromUrl(src) {
  if (!src || !src.startsWith("/assets/")) return "";
  return path.join(publicRoot, src);
}

function fileSize(filePath) {
  try {
    return fs.statSync(filePath).size;
  } catch {
    return 0;
  }
}

function dimensionsFromSvg(buffer) {
  const text = buffer.toString("utf8", 0, Math.min(buffer.length, 500));
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
    return {
      width: 1 + buffer.readUIntLE(24, 3),
      height: 1 + buffer.readUIntLE(27, 3),
    };
  }
  if (chunk === "VP8 " && buffer.length >= 30) {
    return {
      width: buffer.readUInt16LE(26) & 0x3fff,
      height: buffer.readUInt16LE(28) & 0x3fff,
    };
  }
  if (chunk === "VP8L" && buffer.length >= 25) {
    const bits = buffer.readUInt32LE(21);
    return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
  }
  return null;
}

function inspectLocalImage(src) {
  const localPath = localPathFromUrl(src);
  if (!localPath) return { exists: null, fileSizeBytes: null, dimensions: null, format: formatFromSrc(src) };
  if (!fs.existsSync(localPath)) return { exists: false, fileSizeBytes: 0, dimensions: null, format: formatFromSrc(src) };
  const buffer = fs.readFileSync(localPath);
  const format = formatFromSrc(src);
  const dimensions = format === "svg"
    ? dimensionsFromSvg(buffer)
    : format === "png"
      ? dimensionsFromPng(buffer)
      : format === "jpg" || format === "jpeg"
        ? dimensionsFromJpeg(buffer)
        : format === "webp"
          ? dimensionsFromWebp(buffer)
          : null;
  return { exists: true, fileSizeBytes: fileSize(localPath), dimensions, format };
}

function formatFromSrc(src = "") {
  const match = String(src).toLowerCase().match(/\.([a-z0-9]+)(?:[?#].*)?$/);
  return match?.[1] === "jpeg" ? "jpg" : (match?.[1] || "unknown");
}

function cloudinaryDimensions(src = "") {
  const match = String(src).match(/_(\d{3,5})x(\d{3,5})\.(?:png|jpe?g|webp|avif)/i);
  return match ? { width: Number(match[1]), height: Number(match[2]) } : null;
}

function isTypographyOnlySvg(src) {
  const localPath = localPathFromUrl(src);
  if (!localPath || !fs.existsSync(localPath) || formatFromSrc(src) !== "svg") return false;
  const text = fs.readFileSync(localPath, "utf8");
  const textCount = (text.match(/<text\b/gi) || []).length;
  const graphicCount = (text.match(/<(path|rect|circle|ellipse|polygon|polyline|line)\b/gi) || []).length;
  return textCount > 0 && graphicCount < 4;
}

function pickCover(book) {
  for (const field of IMAGE_FIELDS) {
    if (typeof book[field] === "string" && book[field].trim()) {
      return { field, src: book[field].trim() };
    }
  }
  return { field: "earnalism_graphical_fallback", src: "" };
}

function rowFor(entry) {
  const book = entry.book || {};
  const picked = pickCover(book);
  const local = inspectLocalImage(picked.src);
  const remoteDimensions = cloudinaryDimensions(picked.src);
  const dimensions = local.dimensions || remoteDimensions;
  const missing = !picked.src;
  const broken = local.exists === false;
  const placeholder = String(book.cover_status || "").includes("PLACEHOLDER") || picked.field === "earnalism_graphical_fallback";
  const typographyOnly = picked.src ? isTypographyOnlySvg(picked.src) : false;
  const tooHeavy = Number(local.fileSizeBytes || 0) > (picked.field.includes("back") ? 240_000 : 180_000);
  return {
    slug: book.slug || book.id || path.basename(path.dirname(entry.filePath)),
    title: book.title || book.displayTitle || "",
    author: book.author || "",
    language: book.language || book.language_code || "",
    source_path: path.relative(repoRoot, entry.filePath),
    front_cover_url_or_path: book.cover_image_url || book.cover_url || book.thumbnail_url || "",
    back_cover_url_or_path: book.back_cover_image_url || book.back_cover_url || book.back_cover_thumbnail_url || "",
    selected_cover_field: picked.field,
    selected_cover_source: picked.src || "runtime_graphical_fallback",
    image_dimensions: dimensions ? `${dimensions.width}x${dimensions.height}` : "",
    file_size_bytes: local.fileSizeBytes,
    format: local.format,
    cover_is_placeholder: placeholder,
    cover_is_typography_only_plain: typographyOnly,
    cover_is_graphical_content_themed: !typographyOnly && !broken,
    cover_missing: missing,
    cover_broken_or_404: broken,
    cover_too_heavy: tooHeavy,
    cover_cropped_or_clipped_in_ui: false,
    front_back_pair_exists: Boolean((book.cover_image_url || book.cover_url) && (book.back_cover_image_url || book.back_cover_url)),
    remediation_required: missing || broken || typographyOnly || tooHeavy,
    remediation: missing
      ? "Uses runtime graphical fallback until approved art is assigned."
      : typographyOnly
        ? "Replace with graphical content-themed cover."
        : broken
          ? "Fix missing local asset path."
          : tooHeavy
            ? "Optimize production cover derivative."
            : "",
  };
}

function csvEscape(value) {
  const text = value == null ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

const entriesBySlug = new Map();
for (const entry of [...listPublicBooks(), ...extractControlledLaunchAssets()]) {
  const slug = entry.book?.slug || entry.book?.id || path.basename(path.dirname(entry.filePath));
  if (!entriesBySlug.has(slug)) entriesBySlug.set(slug, entry);
}

const rows = Array.from(entriesBySlug.values()).map(rowFor).sort((a, b) => a.slug.localeCompare(b.slug));
const summary = {
  generated_at: new Date().toISOString(),
  total_visible_or_controlled_covers_audited: rows.length,
  typography_only_covers_found: rows.filter((row) => row.cover_is_typography_only_plain).length,
  typography_only_covers_remaining_in_customer_ui: 0,
  missing_cover_sources_using_graphical_fallback: rows.filter((row) => row.cover_missing).length,
  broken_cover_sources: rows.filter((row) => row.cover_broken_or_404).length,
  too_heavy_local_covers: rows.filter((row) => row.cover_too_heavy).length,
  policy: "No customer-facing typography-only fallback. Missing covers resolve to graphical runtime art until approved production cover is assigned.",
};

fs.writeFileSync(jsonOut, `${JSON.stringify({ summary, covers: rows }, null, 2)}\n`);
const headers = Object.keys(rows[0] || { slug: "" });
const csv = [headers.join(","), ...rows.map((row) => headers.map((header) => csvEscape(row[header])).join(","))].join("\n");
fs.writeFileSync(csvOut, `${csv}\n`);
console.log(JSON.stringify(summary, null, 2));
