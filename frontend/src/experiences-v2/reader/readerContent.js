export function paragraphsFromHtml(html = "") {
  if (typeof document === "undefined") return String(html).replace(/<[^>]+>/g, " ").trim() ? [String(html).replace(/<[^>]+>/g, " ").trim()] : [];
  const container = document.createElement("div");
  container.innerHTML = html;
  const paragraphs = [...container.querySelectorAll("p")].map((node) => node.textContent?.trim()).filter(Boolean);
  if (paragraphs.length) return paragraphs;
  // Some approved canonical packages use heading/div markup rather than p
  // elements. Preserve their readable text instead of rendering an empty
  // Reader body merely because their source structure differs.
  container.querySelectorAll("br").forEach((node) => node.replaceWith("\n"));
  container.querySelectorAll("h1,h2,h3,h4,h5,h6,div,section,article,li,blockquote,pre").forEach((node) => node.append("\n"));
  return container.textContent.split(/\n+/).map((value) => value.trim()).filter(Boolean);
}
