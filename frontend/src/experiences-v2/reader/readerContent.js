import { createElement, Fragment, useMemo } from "react";

const OMIT = new Set(["script", "style", "iframe", "object", "embed", "form", "input", "button", "textarea", "select", "meta", "link", "svg", "math", "template"]);
const ALLOWED = new Set(["p", "div", "section", "article", "span", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr", "strong", "b", "em", "i", "u", "s", "sub", "sup", "small", "blockquote", "pre", "code", "ul", "ol", "li", "dl", "dt", "dd", "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "figure", "figcaption", "a", "img"]);

function safeUrl(value = "") {
  if (/[\u0000-\u0020]/.test(value)) return undefined;
  return /^(https?:\/\/|\/(?!\/)|#)/i.test(value) ? value : undefined;
}

function readableFragment(html) {
  const template = document.createElement("template");
  template.innerHTML = String(html || "");
  template.content.querySelectorAll([...OMIT].join(",")).forEach((node) => node.remove());
  return template.content;
}

function renderNode(node, key) {
  if (node.nodeType === 3) return node.textContent;
  if (node.nodeType !== 1) return null;
  const tag = node.tagName.toLowerCase();
  if (OMIT.has(tag)) return null;
  const children = [...node.childNodes].map((child, index) => renderNode(child, `${key}-${index}`));
  if (!ALLOWED.has(tag)) return createElement(Fragment, { key }, ...children);
  const props = { key };
  if (tag === "td" || tag === "th") {
    ["colspan", "rowspan"].forEach((attribute) => {
      const count = Number(node.getAttribute(attribute));
      if (Number.isInteger(count) && count > 0 && count <= 1000) props[attribute === "colspan" ? "colSpan" : "rowSpan"] = count;
    });
  }
  if (tag === "a") {
    props.href = safeUrl(node.getAttribute("href") || "");
    props.rel = "noopener noreferrer";
  }
  if (tag === "img") {
    props.src = safeUrl(node.getAttribute("src") || "");
    props.alt = node.getAttribute("alt") || "";
    props.loading = "lazy";
    return props.src ? createElement("img", props) : props.alt;
  }
  if (tag === "br" || tag === "hr") return createElement(tag, props);
  if (tag === "table") return createElement("div", { key, className: "reader-v2__table-scroll", tabIndex: 0, role: "region", "aria-label": "Scrollable table" }, createElement(tag, null, ...children));
  // Preserve literary structure without importing scripts, events or styles.
  return createElement(tag, props, ...children);
}

export function ReaderContent({ html = "" }) {
  const content = useMemo(() => {
    if (typeof document === "undefined") return String(html);
    return [...readableFragment(html).childNodes].map((node, index) => renderNode(node, String(index)));
  }, [html]);
  return createElement(Fragment, null, content);
}

export function paragraphsFromHtml(html = "") {
  if (typeof document === "undefined") return String(html).replace(/<[^>]+>/g, " ").trim() ? [String(html).replace(/<[^>]+>/g, " ").trim()] : [];
  const container = readableFragment(html);
  container.querySelectorAll("br").forEach((node) => node.replaceWith("\n"));
  container.querySelectorAll("p,h1,h2,h3,h4,h5,h6,div,section,article,li,blockquote,pre").forEach((node) => node.append("\n"));
  return container.textContent.split(/\n+/).map((value) => value.trim()).filter(Boolean);
}
