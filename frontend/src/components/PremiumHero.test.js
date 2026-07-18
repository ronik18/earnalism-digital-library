import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/PremiumHero.jsx"), "utf8");

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
    const referenceAsset = path.join(process.cwd(), "public/assets/hero/premium-library-reference.webp");
    expect(source).toContain("premium-library-reference.webp");
    expect(source).toContain("fetchPriority=\"high\"");
    expect(source).toContain("premium-hero-action--primary");
    expect(source).toContain("premium-hero-action--secondary");
    expect(fs.statSync(referenceAsset).size).toBeLessThan(600_000);
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

  test("supports a dynamic custom logo over the desktop reference header strip", () => {
    expect(source).toContain("premium-reference-brand-overlay");
    expect(source).toContain("brand?.logo_url?.trim()");
    expect(source).toContain("earnalism-brand-lockup.png");
    expect(source).toContain('data-testid="premium-reference-brand-overlay"');
  });
});
