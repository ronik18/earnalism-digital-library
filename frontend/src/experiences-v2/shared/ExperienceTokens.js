// This bridge deliberately consumes the merged public-page tokens. It stays
// feature-local so these experiences do not create a second design system.
export const EXPERIENCE_V2_TOKENS = Object.freeze({
  ink: "var(--eds-ink, #091310)",
  ivory: "var(--eds-paper, #fbf7ef)",
  gold: "var(--eds-gold, #d5ad56)",
  line: "var(--eds-line, rgba(213, 173, 86, 0.24))",
  ui: "var(--eds-ui, Outfit, Noto Sans Bengali, sans-serif)",
  display: "var(--eds-display, Cormorant Garamond, Noto Serif Bengali)",
  surface: "var(--eds-ink, #091310)",
  surfaceRaised: "color-mix(in srgb, var(--eds-ink, #091310) 92%, var(--eds-paper, #fbf7ef))",
});
