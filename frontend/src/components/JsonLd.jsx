import { useEffect } from "react";

/**
 * JsonLd — injects a JSON-LD <script> into <head> for the current page.
 * Removes the script on unmount so navigation between pages doesn't leak schema.
 */
export default function JsonLd({ id, data }) {
  const json = data ? JSON.stringify(data) : null;
  useEffect(() => {
    if (!json) return undefined;
    const elId = `jsonld-${id}`;
    let el = document.getElementById(elId);
    if (!el) {
      el = document.createElement("script");
      el.type = "application/ld+json";
      el.id = elId;
      document.head.appendChild(el);
    }
    el.text = json;
    return () => {
      const found = document.getElementById(elId);
      if (found && found.parentNode) found.parentNode.removeChild(found);
    };
  }, [id, json]);
  return null;
}
