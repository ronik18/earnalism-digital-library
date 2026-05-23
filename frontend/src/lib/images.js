const LOCAL_ASSET_RE = /^\/?assets\//i;
const IMAGE_EXTENSION_RE = /\.(avif|gif|jpe?g|png|svg|webp)(?:[?#].*)?$/i;
const FALLBACK_EXTENSIONS = ["jpg", "png", "webp", "jpeg", "gif"];

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
