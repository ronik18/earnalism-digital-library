import { useEffect } from "react";

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

/**
 * Set document <title>, meta description, and OpenGraph + Twitter tags.
 * Usage: useSEO({ title, description, image })
 */
export default function useSEO({ title, description, image } = {}) {
  useEffect(() => {
    if (title) document.title = title;
    const url = typeof window !== "undefined" ? window.location.href : "";
    setMeta("description", description);
    setMeta("og:site_name", "The Earnalism", true);
    setMeta("og:type", "website", true);
    setMeta("og:title", title, true);
    setMeta("og:description", description, true);
    setMeta("og:image", image, true);
    setMeta("og:url", url, true);
    setMeta("twitter:card", "summary_large_image");
    setMeta("twitter:title", title);
    setMeta("twitter:description", description);
    setMeta("twitter:image", image);
  }, [title, description, image]);
}
