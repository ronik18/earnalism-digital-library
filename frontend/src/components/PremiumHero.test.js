import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/PremiumHero.jsx"), "utf8");
const styles = fs.readFileSync(path.join(process.cwd(), "src/components/PremiumHero.css"), "utf8");

describe("PremiumHero public contract", () => {
  test("uses dynamic catalog records rather than hardcoded public books", () => {
    expect(source).toContain("{books.map");
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
    expect(source).toContain("premium-library-reference-exact.webp");
    expect(source).toContain('onError={() => setReferenceArtFailed(true)}');
    expect(source).toContain('width="2180"');
    expect(source).toContain('height="1032"');
    expect(source).toContain("fetchPriority=\"high\"");
    expect(source).toContain("premium-reference-hero--exact");
    expect(source).toContain("premium-reference-catalog--exact");
    expect(source).toContain("premium-hero-action--primary");
    expect(source).toContain("premium-hero-action--secondary");
    expect(fs.statSync(referenceAsset).size).toBeLessThan(1_800_000);
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

  test("renders the live header above the cropped reference art and separates device surfaces", () => {
    expect(source).toContain("premium-reference-hero__art");
    expect(source).toContain("premium-reference-device-group");
    expect(source).toContain("premium-reference-tablet__screen");
    expect(source).toContain("premium-reader-screen-preview");
    expect(source).toContain('to="/reader/dracula"');
    expect(source).not.toContain("premium-reference-brand-overlay");
    expect(styles).toContain("--reference-header-height: var(--site-header-height);");
    expect(styles).toContain("height: calc(100% - var(--reference-header-height));");
    expect(styles).toContain("height: min(calc(var(--reference-header-height) + 48.0861vw), 100vh);");
    expect(styles).toContain("--reference-header-height: 0px;");
    expect(styles).toContain("height: min(48.0861vw, calc(100vh - var(--site-header-height)));");
    expect(styles).toContain("object-fit: fill;");
    expect(styles).toContain("aspect-ratio: 246 / 376;");
    expect(styles).toContain("inset: 5.2% 7.7% 5% 7.7%;");
    expect(styles).toContain("overflow: visible;");
    expect(styles).toContain("overflow: hidden;");
    expect(styles).toContain("z-index: 3;");
    expect(styles).toContain("z-index: 1;");
    expect(styles).toContain("left: 56.6%;");
    expect(source).toContain("[0, 1, 2, 3].map");
    expect(source).toContain("featuredBooks.slice(0, 4)");
    expect(source).not.toContain("premium-reference-slot--reader-cover");
  });

  test("keeps mobile cover loading light and analytics scoped by surface", () => {
    expect(source).toContain("eager={index === 0}");
    expect(source).toContain("calc((100vw - 3.45rem) / 4)");
    expect(source).toContain("analyticsNamespace = \"home\"");
    expect(source).toContain("headerMode === \"in-flow\"");
  });
});
