// This bridge deliberately consumes the merged public-page tokens. It stays
// feature-local so these experiences do not create a second design system.
export const EXPERIENCE_V2_TOKENS = Object.freeze({
  ink: "var(--eds-ink, #17090e)",
  ivory: "var(--eds-paper, #fff9ee)",
  gold: "var(--eds-gold, #dfb85a)",
  line: "var(--eds-line, rgba(223, 184, 90, 0.28))",
  ui: "var(--eds-ui, Outfit, Noto Sans Bengali, sans-serif)",
  display: "var(--eds-display, Cormorant Garamond, Noto Serif Bengali)",
  surface: "var(--eds-ink, #17090e)",
  surfaceRaised: "color-mix(in srgb, var(--eds-ink, #17090e) 92%, var(--eds-paper, #fff9ee))",
});
