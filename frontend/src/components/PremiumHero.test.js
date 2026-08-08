import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/PremiumHero.jsx"), "utf8");
const styles = fs.readFileSync(path.join(process.cwd(), "src/components/PremiumHero.css"), "utf8");
const carouselSource = fs.readFileSync(path.join(process.cwd(), "src/lib/heroCarousel.js"), "utf8");
const publicIndex = fs.readFileSync(path.join(process.cwd(), "public/index.html"), "utf8");

describe("PremiumHero public contract", () => {
  test("uses only valid dynamic Sprint 1 carousel records", () => {
    expect(source).toContain("{books.map");
    expect(carouselSource).toContain("hero.carousel_books");
    expect(source).toContain("heroCarouselBooks(curation)");
    expect(carouselSource).not.toContain("[...featured, ...shelfBooks]");
    expect(carouselSource).toContain("book.front_cover_url");
    expect(carouselSource).toContain("book.cover_alt_text");
    expect(source).toContain("data-canonical-cover-url={book.coverSrc}");
    expect(carouselSource).toContain("HERO_CAROUSEL_EXCLUDED_SLUGS");
    expect(carouselSource).toContain('"devdas"');
    expect(source).not.toMatch(/Devdas|Pather Panchali|Great Expectations|Gitanjali|Jane Eyre/);
  });

  test("derives the active cover, metadata, route, counter, and identity from one active slide", () => {
    expect(source).toContain("const activeSlide = activeHeroSlide(books, carousel.activeIndex)");
    expect(source).toContain("data-active-slide-id={activeSlide?.id");
    expect(source).toContain("data-active-cover-id={book.id}");
    expect(source).toContain("data-slide-id={activeSlide.id}");
    expect(source).toContain("to={activeSlide.destination}");
    expect(source).toContain("to={book.destination}");
    expect(source).toContain("{activeSlide.title}");
    expect(source).toContain("{activeSlide.author}");
    expect(source).not.toContain("carousel.activeBook");
  });

  test("keeps the listening phone bound only to approved audiobook records", () => {
    expect(source).toContain("approvedAudiobooks.find");
    expect(source).toContain("featuredSlugs.has(book.slug)");
    expect(source).toContain("to={listeningBook.cta_url}");
    expect(source).toContain("Premium Listening Rooms");
  });

  test("keeps the owner reference artwork and existing transparent CTA hotspots unchanged", () => {
    const referenceAsset = path.join(process.cwd(), "public/assets/hero/premium-library-reference-exact.webp");
    const responsiveReferenceAssets = [
      "premium-library-reference-exact-1024.webp",
      "premium-library-reference-exact-1440.webp",
    ].map((filename) => path.join(process.cwd(), "public/assets/hero", filename));

    expect(source).toContain("premium-library-reference-exact.webp");
    expect(source).toContain('versionedHeroAsset("/assets/hero/premium-library-reference-exact-1024.webp")');
    expect(source).toContain("HERO_ASSET_VERSION");
    expect(source).toContain("premium-library-reference-exact-1440.webp");
    expect(source).toContain("REFERENCE_HERO_AVIF_SRCSET");
    expect(source).toContain('type="image/avif"');
    expect(publicIndex).toContain("premium-library-reference-exact-1440.avif");
    expect(publicIndex).toContain('imagesizes="100vw"');
    expect(source).toContain('width="2180"');
    expect(source).toContain('height="1032"');
    expect(source).toContain('fetchPriority="high"');
    expect(source).toContain("premium-hero-action--primary");
    expect(source).toContain("premium-hero-action--secondary");
    expect(fs.statSync(referenceAsset).size).toBeLessThan(300_000);
    expect(responsiveReferenceAssets.every((asset) => fs.statSync(asset).size < 160_000)).toBe(true);
    expect(fs.statSync(path.join(process.cwd(), "public/assets/hero/premium-library-reference-exact.avif")).size).toBeLessThan(200_000);

    const hoverRule = styles.match(/\.premium-hero-action:hover\s*\{([\s\S]*?)\}/)?.[1];
    expect(hoverRule).toContain("background: transparent;");
    expect(hoverRule).toContain("box-shadow: none;");
  });

  test("renders one mathematical slide set with exactly three meaningful states", () => {
    expect(source).toContain("carouselSlideState(index, carousel.activeIndex, books.length)");
    expect(source).toContain('slideState === "active"');
    expect(source).toContain('slideState === "previous" || slideState === "next"');
    expect(source).toContain("aria-hidden={isHidden}");
    expect(source).toContain('data-position={slideState}');
    expect(source).toContain('data-active={isActive ? "true" : "false"}');
    expect(source).not.toContain("clone");
    expect(source).not.toContain("premium-reference-catalog-frame");
    expect(carouselSource).toContain('if (position === -1) return "previous"');
    expect(carouselSource).toContain('if (position === 1) return "next"');
  });

  test("uses separated position, tilt, and front-face wrappers for a dimensional book shell", () => {
    expect(source).toContain("premium-coverflow__slide");
    expect(source).toContain("premium-coverflow__book-action");
    expect(source).toContain("premium-book-jacket__front");
    expect(source).toContain("premium-book-jacket__spine");
    expect(source).toContain("premium-book-jacket__right-pages");
    expect(source).toContain("premium-book-jacket__bottom-pages");
    expect(styles).toContain("perspective: 1100px;");
    expect(styles).toContain("transform-style: preserve-3d;");
    expect(styles).toContain("--slide-z: 60px;");
    expect(styles).toContain("--slide-rotate-y: -4deg;");
    expect(styles).toContain("--slide-z: -90px;");
    expect(styles).toContain("--slide-scale: 0.81;");
    expect(styles).toContain("object-fit: contain;");
    expect(styles).toContain("filter: drop-shadow");
    expect(styles).toContain("radial-gradient(circle, rgba(222, 163, 70, 0.25)");
  });

  test("implements the WAI carousel controls and hidden-slide focus rules", () => {
    expect(source).toContain('role="region"');
    expect(source).toContain('aria-roledescription="carousel"');
    expect(source).toContain('aria-label="Featured classics"');
    expect(source).toContain('aria-roledescription="slide"');
    expect(source).toContain('aria-label="Previous book"');
    expect(source).toContain('aria-label="Next book"');
    expect(source).toContain('"Start slide rotation"');
    expect(source).toContain('"Stop slide rotation"');
    expect(source).toContain("tabIndex={-1}");
    expect(source).toContain("isAdjacent ? (");
    expect(source).toContain("stopForKeyboardFocus");
    expect(styles).toContain("outline: 2px solid #e8bb64;");
    expect(styles).toContain("width: 2.75rem;");
    expect(styles).toContain("height: 2.75rem;");
  });

  test("uses a stable editorial plaque and a transform-based autoplay dock", () => {
    expect(source).toContain("premium-coverflow__plaque");
    expect(source).toContain("premium-coverflow__metadata");
    expect(source).toContain("premium-coverflow__progress");
    expect(source).toContain("premium-coverflow__navigation");
    expect(styles).toContain("border-radius: 17px;");
    expect(styles).toContain("backdrop-filter: blur(14px);");
    expect(styles).toContain("rgba(42, 25, 15, 0.94)");
    expect(styles).toContain("transform: scaleX(0);");
    expect(styles).toContain("animation-play-state: paused;");
    expect(styles).not.toContain("premium-coverflow__caption");
  });

  test("supports bounded autoplay, visibility pause, focus stop, keyboard, and swipe", () => {
    expect(source).toContain("HERO_CAROUSEL_INTERVAL_MS = 7000");
    expect(source).toContain("window.setInterval");
    expect(source).toContain("desiredIndex.current = activeIndexRef.current");
    expect(source).toContain("document.visibilityState");
    expect(source).toContain("initialCoverReady");
    expect(source).toContain("prefers-reduced-motion: reduce");
    expect(source).toContain("(max-width: 767px)");
    expect(source).toContain('event.key === "ArrowLeft"');
    expect(source).toContain('event.key === "ArrowRight"');
    expect(source).toContain("onPointerDown={onPointerDown}");
    expect(source).toContain("onPointerCancel");
    expect(styles).toContain("touch-action: pan-y;");
    expect(styles).toContain("720ms var(--coverflow-ease)");
    expect(styles).not.toMatch(/animation:\s*[^;]*(infinite|alternate)/);
  });

  test("loads only the initial and adjacent covers eagerly and decodes before rotation", () => {
    expect(source).toContain("preloadHeroBook");
    expect(source).toContain("image.decode");
    expect(source).toContain("index === 0 || isActive || isAdjacent");
    expect(source).toContain("index === 0 && carousel.activeIndex === 0");
    expect(source).toContain('fetchPriority={highPriority ? "high" : undefined}');
    expect(source).toContain('loading={eager ? "eager" : "lazy"}');
    expect(source).toContain("initialCoverReady,");
  });

  test("reserves responsive safe zones without fixed screenshot-only horizontal offsets", () => {
    expect(styles).toContain("width: clamp(484px, 37.4vw, 605px);");
    expect(styles).toContain("right: clamp(32px, 3.4vw, 56px);");
    expect(styles).toContain("--coverflow-active-height: clamp(189px, 12.6vw, 202px);");
    expect(styles).toContain('grid-template-areas: "plaque stage";');
    expect(styles).toContain("@media (min-width: 1024px) and (max-height: 800px)");
    expect(styles).toContain("@media (max-width: 767px)");
    expect(styles).toContain("overflow: visible;");
  });

  test("retains approved reader-facing copy and excludes engineering status language", () => {
    expect(source).toContain("Curated Classics");
    expect(source).toContain("Immersive Audiobooks");
    expect(source).toContain("Beautiful Graphical Editions");
    expect(source).toContain("Calm Reader Modes");
    expect(source).toContain("Your Library, Everywhere");
    expect(source).toContain("Featured classic");
    expect(source).toContain("Reading Pass");
    expect(source).toContain("Chapter 1 is free");
    expect(source).not.toContain("PREMIUM_CARDS");
    expect(source).not.toMatch(/release gates|QA_PASSED|PUBLIC_AUDIO|Audio gated by evidence|typographic-only cover fallback/i);
  });
});
