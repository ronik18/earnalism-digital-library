import { memo } from "react";

function linkedCredits(text) {
  const parts = [];
  let cursor = 0;
  for (const match of text.matchAll(/https:\/\/[^\s<>]+/g)) {
    parts.push(text.slice(cursor, match.index));
    const suffix = match[0].match(/[),.;!?]+$/)?.[0] || "";
    const label = suffix ? match[0].slice(0, -suffix.length) : match[0];
    let safe = false;
    try {
      const url = new URL(label);
      safe = url.protocol === "https:" && !url.username && !url.password;
    } catch { /* Invalid URLs remain ordinary escaped text. */ }
    parts.push(safe
      ? <a key={match.index} href={label} target="_blank" rel="noopener noreferrer">{label}</a>
      : label);
    parts.push(suffix);
    cursor = match.index + match[0].length;
  }
  parts.push(text.slice(cursor));
  return parts;
}

export default memo(function NarrationCredits({ disclosure = "" }) {
  if (typeof disclosure !== "string" || !disclosure.trim()) return null;
  return <section className="listener-v2__credits" aria-label="Narration and music credits" data-testid="listener-narration-credits">
    <h2>Narration and music credits</h2>
    <p>{linkedCredits(disclosure.trim())}</p>
  </section>;
});
