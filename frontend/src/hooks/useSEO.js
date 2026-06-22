import { useEffect } from "react";
import { useSettings } from "../context/SettingsContext";

const SITE_URL = (process.env.REACT_APP_SITE_URL || "https://theearnalism.com").replace(/\/+$/, "");
const DEFAULT_TITLE = "The Earnalism Digital Library";
const DEFAULT_DESCRIPTION = "A quiet digital reading room beginning with Dracula by Bram Stoker. Read Chapter 1 free, then continue with reading time when you are ready.";
// Owner-designed Dracula cover used as the fallback OG image for the
// Dracula-first controlled launch until a separate approved brand share image exists.
const FALLBACK_OG_IMAGE =
  `${SITE_URL}/assets/books/dracula/dracula-front-cover.webp`;
const TRACKING_PARAMS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_term",
  "utm_content",
  "fbclid",
  "gclid",
  "msclkid",
];

function setMeta(name, content, isProperty = false) {
  if (!content) return;
  const attr = isProperty ? "property" : "name";
  let el = document.querySelector(`meta[${attr}="${name}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, name);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

function setLink(rel, href) {
  if (!href) return;
  let el = document.querySelector(`link[rel="${rel}"]`);
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", rel);
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
}

function absoluteUrl(value) {
  if (!value) return "";
  try {
    return new URL(value, SITE_URL).href;
  } catch {
    return value;
  }
}

function normalizedCanonical(canonicalPath) {
  const path = canonicalPath || (typeof window !== "undefined" ? window.location.pathname : "/");
  const url = new URL(path || "/", SITE_URL);
  url.hash = "";
  TRACKING_PARAMS.forEach((param) => url.searchParams.delete(param));
  if (!canonicalPath) url.search = "";
  if (url.pathname !== "/" && url.pathname.endsWith("/")) {
    url.pathname = url.pathname.replace(/\/+$/, "");
  }
  return url.href;
}

/**
 * Set <title>, meta description, canonical link, and OpenGraph + Twitter card meta.
 *
 * Usage: useSEO({ title, description, image, type })
 *
 * The hook auto-fills missing fields with brand defaults:
 *   - description → DEFAULT_DESCRIPTION
 *   - image → admin's `brand.og_image_url` setting if set, else FALLBACK_OG_IMAGE
 */
export default function useSEO({
  title,
  description,
  image,
  imageAlt,
  type = "website",
  robots = "index, follow",
  canonicalPath,
} = {}) {
  const { brand } = useSettings();
  const ogImage = absoluteUrl(image || brand?.og_image_url || FALLBACK_OG_IMAGE);
  const desc = description || DEFAULT_DESCRIPTION;
  useEffect(() => {
    const pageTitle = title || DEFAULT_TITLE;
    document.title = pageTitle;
    const url = normalizedCanonical(canonicalPath);
    setLink("canonical", url);
    setMeta("application-name", "Earnalism");
    setMeta("author", "The Earnalism");
    setMeta("description", desc);
    setMeta("robots", robots);
    setMeta("og:locale", "en_US", true);
    setMeta("og:site_name", "The Earnalism Digital Library", true);
    setMeta("og:type", type, true);
    setMeta("og:title", pageTitle, true);
    setMeta("og:description", desc, true);
    setMeta("og:image", ogImage, true);
    setMeta("og:image:alt", imageAlt || pageTitle, true);
    setMeta("og:url", url, true);
    setMeta("twitter:card", "summary_large_image");
    setMeta("twitter:title", pageTitle);
    setMeta("twitter:description", desc);
    setMeta("twitter:image", ogImage);
    setMeta("twitter:image:alt", imageAlt || pageTitle);
  }, [title, desc, ogImage, imageAlt, type, robots, canonicalPath]);
}
