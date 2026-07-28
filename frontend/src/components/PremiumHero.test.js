import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/PremiumHero.jsx"), "utf8");
const styles = fs.readFileSync(path.join(process.cwd(), "src/components/PremiumHero.css"), "utf8");
const publicIndex = fs.readFileSync(path.join(process.cwd(), "public/index.html"), "utf8");

describe("PremiumHero public contract", () => {
  test("uses dynamic catalog records rather than hardcoded public books", () => {
    expect(source).toContain("{books.map");
    expect(source).toContain("hero.carousel_books");
    expect(source).toContain("heroCarouselBooks(curation)");
    expect(source).toContain("book.front_cover_url");
    expect(source).toContain("book.cover_alt_text");
    expect(source).toContain("approvedAudiobooks.find");
    expect(source).toContain("data-canonical-cover-url={book.front_cover_url}");
    expect(source).not.toMatch(/Devdas|Pather Panchali|Great Expectations|Gitanjali|Jane Eyre/);
  });

  test("keeps the listening phone bound only to the approved audiobook shelf", () => {
    expect(source).toContain("approvedAudiobooks.find");
    expect(source).toContain("featuredSlugs.has(book.slug)");
    expect(source).toContain("to={listeningBook.cta_url}");
    expect(source).toContain("Premium Listening Rooms");
  });

  test("uses the owner reference as a high-priority visual layer with exact transparent CTA hotspots", () => {
    const referenceAsset = path.join(process.cwd(), "public/assets/hero/premium-library-reference-exact.webp");
    const responsiveReferenceAssets = [
      "premium-library-reference-exact-1024.webp",
      "premium-library-reference-exact-1440.webp",
    ].map((filename) => path.join(process.cwd(), "public/assets/hero", filename));
    expect(source).toContain("premium-library-reference-exact.webp");
    expect(source).toContain("premium-library-reference-exact-1024.webp 1024w");
    expect(source).toContain("premium-library-reference-exact-1440.webp");
    expect(source).toContain("${REFERENCE_HERO_IMAGE} 1440w");
    expect(source).toContain("REFERENCE_HERO_AVIF_SRCSET");
    expect(source).toContain('type="image/avif"');
    expect(publicIndex).toContain("premium-library-reference-exact-1440.avif");
    expect(publicIndex).toContain('imagesizes="100vw"');
    expect(publicIndex).not.toContain('href="%PUBLIC_URL%/assets/hero/premium-library-reference-exact.webp"');
    expect(source).toContain('sizes="100vw"');
    expect(source).toContain('onError={() => setReferenceArtFailed(true)}');
    expect(source).toContain('width="2180"');
    expect(source).toContain('height="1032"');
    expect(source).toContain("fetchPriority=\"high\"");
    expect(source).toContain("premium-reference-hero--exact");
    expect(source).toContain("premium-reference-catalog--exact");
    expect(source).toContain("premium-hero-action--primary");
    expect(source).toContain("premium-hero-action--secondary");
    expect(fs.statSync(referenceAsset).size).toBeLessThan(300_000);
    expect(responsiveReferenceAssets.every((asset) => fs.statSync(asset).size < 160_000)).toBe(true);
    expect(fs.statSync(path.join(process.cwd(), "public/assets/hero/premium-library-reference-exact.avif")).size).toBeLessThan(200_000);

    const hoverRule = styles.match(
      /\.premium-hero-action:hover\s*\{([\s\S]*?)\}/,
    )?.[1];
    expect(hoverRule).toContain("background: transparent;");
    expect(hoverRule).toContain("box-shadow: none;");
  });

  test("keeps canonical desktop book jackets visible over the blank reference slots", () => {
    expect(styles).toContain(
      ".premium-reference-slot .book-cover-image--loaded .book-cover-image__img",
    );
    expect(styles).toMatch(
      /\.premium-reference-slot \.book-cover-image--loaded \.book-cover-image__img\s*\{\s*opacity: 1;/,
    );
    expect(source).toContain('fetchPriority={eager ? "high" : undefined}');
    expect(source).toContain("eager");
  });

  test("renders the owner-approved reader-facing feature copy", () => {
    expect(source).toContain("Curated Classics");
    expect(source).toContain("Immersive Audiobooks");
    expect(source).toContain("Beautiful Editions");
    expect(source).toContain("Calm Reading Modes");
    expect(source).toContain("Your Library, Everywhere");
  });

  test("contains no engineering status language in the public hero", () => {
    expect(source).not.toMatch(/release gates|QA_PASSED|PUBLIC_AUDIO|Audio gated by evidence|typographic-only cover fallback/i);
  });

  test("keeps the full reference artwork below the live header at its native aspect ratio", () => {
    expect(source).toContain("premium-reference-hero__art");
    expect(source).toContain("premium-reference-device-group");
    expect(source).toContain("premium-reference-tablet__screen");
    expect(source).toContain("premium-reader-screen-preview");
    expect(source).toContain('to="/reader/dracula"');
    expect(source).not.toContain("premium-reference-brand-overlay");
    expect(styles).toContain("--reference-header-height: var(--site-header-height);");
    expect(styles).toContain("height: calc(100% - var(--reference-header-height));");
    expect(styles).toContain("height: calc(var(--reference-header-height) + 47.33945vw);");
    expect(styles).not.toContain("--reference-header-height: 0px;");
    expect(styles).not.toContain("48.0861vw");
    expect(styles).toContain("object-fit: contain;");
    expect(styles).toContain("object-position: center top;");
    expect(styles).toContain("aspect-ratio: 246 / 376;");
    expect(styles).toContain("inset: 5.2% 7.7% 5% 7.7%;");
    expect(styles).toContain("overflow: visible;");
    expect(styles).toContain("overflow: hidden;");
    expect(styles).toContain("z-index: 3;");
    expect(styles).toContain("z-index: 1;");
    expect(styles).toContain("left: 56.6%;");
    expect(source).toContain("[0, 1, 2, 3].map");
    expect(source).toContain("HERO_BOOKS_PER_FRAME = 4");
    expect(source).not.toContain("premium-reference-slot--reader-cover");
  });

  test("uses a fixed four-book grid with external 3D right spines and explicit no-overlap clearance", () => {
    expect(source).toContain("premium-reference-catalog-books");
    expect(styles).toContain("grid-template-columns: 1.02fr 0.98fr 1.02fr 1fr;");
    expect(styles).toContain("--book-depth: clamp(6px, 0.58vw, 12px);");
    expect(styles).toContain("--book-clearance: clamp(2px, 0.16vw, 3px);");
    expect(styles).toContain("column-gap: calc(var(--book-depth) + var(--book-clearance));");
    expect(styles).toMatch(
      /\.premium-reference-slot img\s*\{[\s\S]*?object-fit: cover;/,
    );
    expect(styles).toMatch(
      /\.premium-reference-slot::after\s*\{[\s\S]*?right: calc\(-1 \* var\(--book-depth\)\);[\s\S]*?width: var\(--book-depth\);[\s\S]*?rotateY\(-18deg\);/,
    );
    expect(styles).toMatch(
      /\.premium-reference-slot::before\s*\{[\s\S]*?right: calc\(-0\.92 \* var\(--book-depth\)\);[\s\S]*?clip-path:/,
    );
    expect(styles).toContain(".premium-reference-slot > .book-cover-image");
    expect(styles).toContain("transform-style: preserve-3d;");
    expect(styles).not.toMatch(/\.premium-reference-slot--desk-1\s*\{[\s\S]*?left:/);
    expect(styles).not.toMatch(/\.premium-reference-slot--desk-4\s*\{[\s\S]*?left:/);
  });

  test("rotates bounded frames and exposes accessible transparent carousel controls", () => {
    expect(source).toContain("HERO_CAROUSEL_INTERVAL_MS = 7000");
    expect(source).toContain("window.setInterval");
    expect(source).toContain("document.visibilityState");
    expect(source).toContain("prefers-reduced-motion: reduce");
    expect(source).toContain("onMouseEnter={() => carousel.setInteractionPaused(true)}");
    expect(source).toContain('aria-label="Show previous four books"');
    expect(source).toContain('aria-label="Show next four books"');
    expect(source).toContain("Pause featured books carousel");
    expect(source).toContain('aria-roledescription="carousel"');
    expect(styles).toContain("background: rgba(10, 4, 2, 0.18);");
  });

  test("keeps mobile cover loading light and analytics scoped by surface", () => {
    expect(source).toContain("eager={index === 0}");
    expect(source).toContain("calc((100vw - 3.45rem) / 4)");
    expect(source).toContain("analyticsNamespace = \"home\"");
    expect(source).toContain("headerMode === \"in-flow\"");
  });
});
