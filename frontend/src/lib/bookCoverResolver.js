const IMAGE_FIELD_GROUPS = {
  front: ["cover_image_url", "cover_url", "thumbnail_url", "front_cover_url"],
  back: ["back_cover_image_url", "back_cover_url", "back_cover_thumbnail_url"],
};

const FALLBACK_PALETTES = [
  ["#4A1C27", "#17080D", "#D8B97A"],
  ["#24362E", "#101D18", "#C8A85E"],
  ["#2F243B", "#15101D", "#D2B06D"],
  ["#4A2E1D", "#1C100A", "#D9B06C"],
];

function stableHash(value = "") {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash >>> 0);
}

function svgDataUri(svg) {
  return `data:image/svg+xml,${encodeURIComponent(svg)
    .replace(/%20/g, " ")
    .replace(/%3D/g, "=")
    .replace(/%3A/g, ":")
    .replace(/%2F/g, "/")}`;
}

export function graphicalCoverFallbackDataUri(book = {}, { kind = "front" } = {}) {
  const seed = stableHash(`${book?.slug || book?.id || ""}:${book?.title || ""}:${kind}`);
  const [primary, ink, accent] = FALLBACK_PALETTES[seed % FALLBACK_PALETTES.length];
  const motifOffset = 130 + (seed % 90);
  const secondaryOffset = 980 - (seed % 140);
  const isBack = kind === "back";
  const svg = `
<svg width="900" height="1200" viewBox="0 0 900 1200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Graphical Earnalism book cover">
  <defs>
    <linearGradient id="bg" x1="90" y1="0" x2="830" y2="1200" gradientUnits="userSpaceOnUse">
      <stop stop-color="${primary}"/>
      <stop offset="0.58" stop-color="${ink}"/>
      <stop offset="1" stop-color="#080504"/>
    </linearGradient>
    <radialGradient id="lamp" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(${isBack ? secondaryOffset : motifOffset} 250) rotate(90) scale(380 330)">
      <stop stop-color="${accent}" stop-opacity="0.72"/>
      <stop offset="0.54" stop-color="${accent}" stop-opacity="0.18"/>
      <stop offset="1" stop-color="${accent}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="line" x1="180" y1="260" x2="720" y2="930" gradientUnits="userSpaceOnUse">
      <stop stop-color="${accent}" stop-opacity="0.82"/>
      <stop offset="1" stop-color="${accent}" stop-opacity="0.18"/>
    </linearGradient>
  </defs>
  <rect width="900" height="1200" fill="#080504"/>
  <rect x="30" y="30" width="840" height="1140" rx="34" fill="url(#bg)"/>
  <rect x="30" y="30" width="840" height="1140" rx="34" fill="url(#lamp)"/>
  <rect x="74" y="74" width="752" height="1052" rx="24" fill="none" stroke="${accent}" stroke-opacity="0.28" stroke-width="4"/>
  <path d="M198 840C284 710 386 676 480 724C568 769 648 755 724 640" fill="none" stroke="url(#line)" stroke-width="16" stroke-linecap="round" stroke-opacity="0.34"/>
  <path d="M210 880C298 790 394 766 490 804C579 839 657 817 728 736" fill="none" stroke="${accent}" stroke-width="5" stroke-linecap="round" stroke-opacity="0.46"/>
  <path d="M236 372C340 308 434 301 520 350C592 391 656 389 716 342" fill="none" stroke="${accent}" stroke-width="4" stroke-linecap="round" stroke-opacity="0.32"/>
  <circle cx="${isBack ? 650 : 278}" cy="318" r="96" fill="${accent}" fill-opacity="0.08"/>
  <circle cx="${isBack ? 650 : 278}" cy="318" r="56" fill="none" stroke="${accent}" stroke-opacity="0.38" stroke-width="3"/>
  <path d="M450 204C472 260 526 315 600 344C526 372 472 426 450 482C428 426 374 372 300 344C374 315 428 260 450 204Z" fill="${accent}" fill-opacity="0.13"/>
  <g opacity="0.24">
    <path d="M166 1024H734" stroke="${accent}" stroke-width="2"/>
    <path d="M210 1000H690" stroke="${accent}" stroke-width="1.4"/>
    <path d="M252 976H648" stroke="${accent}" stroke-width="1"/>
  </g>
</svg>`;
  return svgDataUri(svg);
}

function firstString(value) {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

export function resolveBookCover(book = {}, { kind = "front" } = {}) {
  const fields = IMAGE_FIELD_GROUPS[kind] || IMAGE_FIELD_GROUPS.front;
  for (const field of fields) {
    const src = firstString(book?.[field]);
    if (src) {
      return {
        src,
        source: field,
        kind,
        isFallback: false,
        isGraphical: true,
      };
    }
  }

  return {
    src: graphicalCoverFallbackDataUri(book, { kind }),
    source: "earnalism_graphical_fallback",
    kind,
    isFallback: true,
    isGraphical: true,
  };
}

export function hasApprovedCover(book = {}, options = {}) {
  return !resolveBookCover(book, options).isFallback;
}
