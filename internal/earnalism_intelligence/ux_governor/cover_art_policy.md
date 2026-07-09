# Cover Art Policy

## Non-Negotiables

- No typographic-only public covers.
- Every public book card, shelf, carousel, detail page, reader entry, and marketing module must use graphical/content-themed art or a deterministic graphical fallback.
- Front and back cover pairs are required where the project supports them.
- Motifs must be tied to book content, genre, mood, or setting.

## Text Rules

- Title and author text must be deterministic HTML/SVG text, not AI-garbled image text.
- Generated image text is not allowed unless it is manually verified as legible and faithful.
- Text overlays must use safe margins and remain readable at card size.

## Performance Rules

- Covers must be lightweight.
- Prefer SVG, CSS/vector, WebP, or AVIF derivatives.
- Do not ship huge raster files into LCP-critical paths.
- Lazy-load noncritical covers and reserve dimensions to prevent CLS.

## Accessibility Rules

- Cover alt text must be meaningful.
- Decorative cover flourishes should be aria-hidden.
- Cover clipping and title clipping are blockers.
