import { resolveBookCover } from "./bookCoverResolver";

const LOCAL_ASSET_RE = /^\/?assets\//i;
const IMAGE_EXTENSION_RE = /\.(avif|gif|jpe?g|png|svg|webp)(?:[?#].*)?$/i;
const HEX_COLOR_RE = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;
const FALLBACK_EXTENSIONS = ["jpg", "png", "webp", "jpeg", "gif"];
const LOCAL_RESPONSIVE_ASSETS = Object.freeze({
  "/assets/books/dracula/dracula-front-cover.webp": {
    220: "/assets/performance/dracula-front-cover-220.webp",
    320: "/assets/performance/dracula-front-cover-320.webp",
    420: "/assets/performance/dracula-front-cover-420.webp",
  },
  "/assets/shelves/bengali-classics.jpg": {
    220: "/assets/performance/bengali-classics-220.webp",
    320: "/assets/performance/bengali-classics-320.webp",
    420: "/assets/performance/bengali-classics-420.webp",
  },
  "/assets/books/sherlock-holmes/front-cover.webp": {
    220: "/assets/performance/sherlock-holmes-front-cover-220.webp",
    260: "/assets/performance/sherlock-holmes-front-cover-260.webp",
    360: "/assets/performance/sherlock-holmes-front-cover-360.webp",
  },
  "/assets/books/kshudhita-pashan/front-cover.webp": {
    220: "/assets/performance/kshudhita-pashan-front-cover-220.webp",
    260: "/assets/performance/kshudhita-pashan-front-cover-260.webp",
    360: "/assets/performance/kshudhita-pashan-front-cover-360.webp",
  },
});

function hasImageExtension(src) {
  return IMAGE_EXTENSION_RE.test(src);
}

function splitQuery(src) {
  const match = String(src).match(/^([^?#]*)([?#].*)?$/);
  return { path: match?.[1] || "", suffix: match?.[2] || "" };
}

export function normalizeImageUrl(src, { defaultExtension = "jpg" } = {}) {
  if (!src || typeof src !== "string") return src;

  let value = src.trim();
  if (!value) return value;

  if (LOCAL_ASSET_RE.test(value) && !value.startsWith("/")) {
    value = `/${value}`;
  }

  if (value.startsWith("/assets/") && !hasImageExtension(value)) {
    const { path, suffix } = splitQuery(value);
    return `${path}.${defaultExtension}${suffix}`;
  }

  return value;
}

export function imageUrlCandidates(src) {
  const normalized = normalizeImageUrl(src);
  if (!normalized || typeof normalized !== "string") return [];

  const original = src.trim();
  const localAsset = LOCAL_ASSET_RE.test(original);
  if (!localAsset || hasImageExtension(original)) return [normalized];

  const withSlash = original.startsWith("/") ? original : `/${original}`;
  const { path, suffix } = splitQuery(withSlash);
  return FALLBACK_EXTENSIONS.map((ext) => `${path}.${ext}${suffix}`);
}

export function optimizedImageUrl(src, { width = 900, quality = 82 } = {}) {
  const normalized = normalizeImageUrl(src);
  if (!normalized || typeof normalized !== "string") return normalized;

  try {
    const url = new URL(normalized);
    if (url.hostname.includes("images.unsplash.com")) {
      url.searchParams.set("auto", "format");
      url.searchParams.set("fit", "crop");
      url.searchParams.set("w", String(width));
      url.searchParams.set("q", String(quality));
      return url.toString();
    }

    if (url.hostname.includes("res.cloudinary.com") && url.pathname.includes("/upload/")) {
      const transform = `f_auto,q_auto,c_limit,w_${width},dpr_auto`;
      url.pathname = url.pathname.replace("/upload/", `/upload/${transform}/`);
      return url.toString();
    }
  } catch {
    return normalized;
  }

  return normalized;
}

function responsiveLocalAssetUrl(src, width) {
  const normalized = normalizeImageUrl(src);
  return LOCAL_RESPONSIVE_ASSETS[normalized]?.[width] || normalized;
}

function normalizeWidthList(widths, fallbackWidth) {
  const normalized = (Array.isArray(widths) && widths.length ? widths : [fallbackWidth])
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value) && value > 0)
    .map((value) => Math.round(value));

  return Array.from(new Set(normalized)).sort((a, b) => a - b);
}

function safeDominantColor(value) {
  if (typeof value !== "string") return "";
  const color = value.trim();
  return HEX_COLOR_RE.test(color) ? color : "";
}

export function bookCoverImageSources(book, { width = 420, widths, quality = 82, forceFallback = false, kind = "front" } = {}) {
  if (!book || typeof book !== "object") {
    return { src: "", srcSet: "", placeholder: "", backgroundColor: "", hasCover: false };
  }

  const resolved = forceFallback
    ? {
      ...resolveBookCover(
        {
          slug: book.slug,
          id: book.id,
          title: book.title,
          author: book.author,
        },
        { kind },
      ),
      isFallback: true,
    }
    : resolveBookCover(book, { kind });
  const cover = normalizeImageUrl(resolved.src || "");
  const thumbnail = forceFallback
    ? ""
    : normalizeImageUrl(kind === "back" ? (book.back_cover_thumbnail_url || "") : (book.thumbnail_url || ""));
  const placeholder = normalizeImageUrl(kind === "back" ? (book.back_cover_blur_placeholder || "") : (book.blur_placeholder || ""));
  const backgroundColor = safeDominantColor(kind === "back" ? (book.back_cover_dominant_color || book.dominant_color) : book.dominant_color);
  const source = cover || thumbnail;
  const src = thumbnail
    ? responsiveLocalAssetUrl(thumbnail, width)
    : (source ? optimizedImageUrl(responsiveLocalAssetUrl(source, width), { width, quality }) : "");
  const responsiveWidths = normalizeWidthList(widths, width);
  const srcSet = cover && !resolved.isFallback
    ? responsiveWidths.map((candidateWidth) => (
      `${optimizedImageUrl(responsiveLocalAssetUrl(cover, candidateWidth), { width: candidateWidth, quality })} ${candidateWidth}w`
    )).join(", ")
    : "";

  return {
    src,
    srcSet,
    placeholder,
    backgroundColor,
    hasCover: Boolean(src || srcSet),
    isFallback: Boolean(resolved.isFallback),
    coverSource: resolved.source,
  };
}
