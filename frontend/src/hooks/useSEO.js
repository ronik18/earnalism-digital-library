import { useEffect } from "react";
import { useSettings } from "../context/SettingsContext";

const SITE_URL = (process.env.REACT_APP_SITE_URL || "https://theearnalism.com").replace(/\/+$/, "");
const DEFAULT_TITLE = "Earnalism Digital Library | Audiobooks, Bengali Books & Reading-Time Access";
const DEFAULT_DESCRIPTION = "Earnalism is a premium digital library for Bengali books, English classics, audiobooks, and flexible reading-time access — where learning becomes earning.";
const DEFAULT_KEYWORDS = "Earnalism, digital library, audiobooks, Bengali books, reading-time access, where learning becomes earning";
// Premium hero/library image used as the fallback OG image until an admin uploads
// a brand-specific share image in Settings -> Brand identity.
const FALLBACK_OG_IMAGE =
  "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1200&q=80";
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
const LOCALES = {
  en: "en_US",
  bn: "bn_BD",
};

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

function setLink(rel, href, attrs = {}) {
  if (!href) return;
  const selectorParts = [`rel="${rel}"`];
  if (attrs.hreflang) selectorParts.push(`hreflang="${attrs.hreflang}"`);
  let el = document.querySelector(`link[${selectorParts.join("][")}]`);
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", rel);
    Object.entries(attrs).forEach(([key, value]) => {
      if (value) el.setAttribute(key, value);
    });
    document.head.appendChild(el);
  }
  el.setAttribute("data-seo-managed", "true");
  el.setAttribute("href", href);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value) el.setAttribute(key, value);
  });
}

function clearManagedAlternateLinks() {
  document.querySelectorAll('link[rel="alternate"][data-seo-managed="true"]').forEach((el) => el.remove());
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
  keywords,
  language = "en",
  alternates = [],
} = {}) {
  const { brand } = useSettings();
  const ogImage = absoluteUrl(image || brand?.og_image_url || FALLBACK_OG_IMAGE);
  const desc = description || DEFAULT_DESCRIPTION;
  const keywordContent = keywords || DEFAULT_KEYWORDS;
  useEffect(() => {
    const pageTitle = title || DEFAULT_TITLE;
    const normalizedLanguage = language || "en";
    const previousLang = document.documentElement.getAttribute("lang") || "en";
    document.title = pageTitle;
    document.documentElement.setAttribute("lang", normalizedLanguage);
    const url = normalizedCanonical(canonicalPath);
    setLink("canonical", url);
    clearManagedAlternateLinks();
    setLink("alternate", url, { hreflang: normalizedLanguage });
    setLink("alternate", url, { hreflang: "x-default" });
    alternates.forEach((alternate) => {
      if (alternate?.href && alternate?.hreflang) {
        setLink("alternate", absoluteUrl(alternate.href), { hreflang: alternate.hreflang });
      }
    });
    setMeta("application-name", "Earnalism");
    setMeta("author", "Earnalism by Reo Enterprise");
    setMeta("description", desc);
    setMeta("keywords", keywordContent);
    setMeta("robots", robots);
    setMeta("og:locale", LOCALES[normalizedLanguage] || "en_US", true);
    setMeta("og:site_name", "Earnalism Digital Library", true);
    setMeta("og:type", type, true);
    setMeta("og:title", pageTitle, true);
    setMeta("og:description", desc, true);
    setMeta("og:image", ogImage, true);
    setMeta("og:image:secure_url", ogImage, true);
    setMeta("og:image:alt", imageAlt || pageTitle, true);
    setMeta("og:url", url, true);
    setMeta("twitter:card", "summary_large_image");
    setMeta("twitter:site", "@theearnalism");
    setMeta("twitter:title", pageTitle);
    setMeta("twitter:description", desc);
    setMeta("twitter:image", ogImage);
    setMeta("twitter:image:alt", imageAlt || pageTitle);
    return () => {
      document.documentElement.setAttribute("lang", previousLang);
    };
  }, [title, desc, ogImage, imageAlt, type, robots, canonicalPath, keywordContent, language, alternates]);
}

export { SITE_URL, DEFAULT_DESCRIPTION, DEFAULT_KEYWORDS, FALLBACK_OG_IMAGE, normalizedCanonical, absoluteUrl };
