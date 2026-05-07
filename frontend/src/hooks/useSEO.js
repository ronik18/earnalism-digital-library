import { useEffect } from "react";
import { useSettings } from "../context/SettingsContext";

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

const DEFAULT_DESCRIPTION = "Buy reading time. Read beautifully. Return whenever you wish.";
// Premium hero/library image used as the fallback OG image until an admin uploads
// a brand-specific share image in Settings → Brand identity.
const FALLBACK_OG_IMAGE =
  "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1200&q=80";

/**
 * Set <title>, meta description, canonical link, and OpenGraph + Twitter card meta.
 *
 * Usage: useSEO({ title, description, image, type })
 *
 * The hook auto-fills missing fields with brand defaults:
 *   - description → DEFAULT_DESCRIPTION
 *   - image → admin's `brand.og_image_url` setting if set, else FALLBACK_OG_IMAGE
 */
export default function useSEO({ title, description, image, type = "website" } = {}) {
  const { brand } = useSettings();
  const ogImage = image || brand?.og_image_url || FALLBACK_OG_IMAGE;
  const desc = description || DEFAULT_DESCRIPTION;
  useEffect(() => {
    if (title) document.title = title;
    const url = typeof window !== "undefined" ? window.location.href : "";
    setLink("canonical", url);
    setMeta("description", desc);
    setMeta("og:site_name", "The Earnalism Digital Library", true);
    setMeta("og:type", type, true);
    setMeta("og:title", title || "The Earnalism Digital Library", true);
    setMeta("og:description", desc, true);
    setMeta("og:image", ogImage, true);
    setMeta("og:url", url, true);
    setMeta("twitter:card", "summary_large_image");
    setMeta("twitter:title", title || "The Earnalism Digital Library");
    setMeta("twitter:description", desc);
    setMeta("twitter:image", ogImage);
  }, [title, desc, ogImage, type]);
}
