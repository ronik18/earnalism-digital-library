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

/**
 * Set <title>, meta description, canonical link, and OpenGraph + Twitter card meta.
 * Usage: useSEO({ title, description, image, type })
 */
export default function useSEO({ title, description, image, type = "website" } = {}) {
  useEffect(() => {
    if (title) document.title = title;
    const url = typeof window !== "undefined" ? window.location.href : "";
    setLink("canonical", url);
    setMeta("description", description);
    setMeta("og:site_name", "The Earnalism", true);
    setMeta("og:type", type, true);
    setMeta("og:title", title, true);
    setMeta("og:description", description, true);
    setMeta("og:image", image, true);
    setMeta("og:url", url, true);
    setMeta("twitter:card", "summary_large_image");
    setMeta("twitter:title", title);
    setMeta("twitter:description", description);
    setMeta("twitter:image", image);
  }, [title, description, image, type]);
}
