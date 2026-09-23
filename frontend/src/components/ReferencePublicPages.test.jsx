import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/EditorialHomeLibrarySurfaces.jsx"), "utf8");
const commerce = fs.readFileSync(path.join(process.cwd(), "src/components/ReadingPassesSurface.jsx"), "utf8");
const home = fs.readFileSync(path.join(process.cwd(), "src/pages/Home.jsx"), "utf8");
const libraryFallback = fs.readFileSync(path.join(process.cwd(), "src/lib/libraryFallbackBooks.js"), "utf8");
const styles = fs.readFileSync(path.join(process.cwd(), "src/components/ReferencePublicPages.css"), "utf8");
const perspectives = fs.readFileSync(path.join(process.cwd(), "src/components/ReaderPerspectives.jsx"), "utf8");
const perspectiveStyles = fs.readFileSync(path.join(process.cwd(), "src/components/ReaderPerspectives.css"), "utf8");
const homeLaunchStyles = fs.readFileSync(path.join(process.cwd(), "src/styles/home-compact-burgundy.css"), "utf8");
const evidence = JSON.parse(fs.readFileSync(path.join(process.cwd(), "src/data/publicEvidenceSnapshot.json"), "utf8"));

describe("Reference public page surfaces", () => {
  test("keeps listening controls behind release truth", () => {
    expect(source).toContain('import { audiobookReleaseState } from "../lib/audioReleaseSafety"');
    expect(source).toContain("audiobookReleaseState(book).releaseApproved");
    expect(source).toContain("Listening discovery comes from the public /home/listening contract");
    expect(home).toContain("fetchHomeListening(controller.signal, 3)");
    expect(source).toContain("Titles without approval show no listening action.");
  });

  test("uses the approved canonical preview and non-recurring pass language", () => {
    expect(source).toContain('PUBLIC_PREVIEW_COPY');
    expect(source).toContain('PUBLIC_ACCESS_COPY');
    expect(source).toContain("No subscription or autorenewal");
    expect(source).not.toContain("Chapter 1 free");
    expect(source).not.toContain("Most Popular");
  });

  test("does not advertise paid checkout or listening before those launch features are enabled", () => {
    expect(home).toContain("home-reference-page--no-commerce");
    expect(home).toContain("home-reference-page--no-audio");
    expect(homeLaunchStyles).toContain(".home-reference-page--no-commerce .reference-home__pass");
    expect(homeLaunchStyles).toContain(".home-reference-page--no-commerce .reference-home__policy > p:nth-of-type(2)");
    expect(homeLaunchStyles).toContain(".home-reference-page--no-audio .reference-home__cta-row a[href=\"/library?availability=approved-audiobook\"]");
    expect(home).toContain("if (!PUBLIC_PAID_COMMERCE_ENABLED) return undefined;");
    expect(home).toContain("if (!PUBLIC_AUDIO_EXPOSURE_ENABLED) return undefined;");
  });

  test("binds offer presentation to current configured offer fields", () => {
    expect(commerce).toContain("pack.price_inr");
    expect(commerce).toContain("pack.minutes");
    expect(commerce).toContain("pack.recommended === true || pack.is_recommended === true");
    expect(commerce).toContain("See current pass details at checkout");
  });

  test("uses one truthful Commerce composition without an obsolete research rail", () => {
    expect(commerce).not.toContain('reference-commerce__insight-rail');
    expect(commerce).not.toContain('reference-commerce__hero-proof');
    expect(commerce).not.toContain("Use study across 2,400+ readers");
    expect(commerce).not.toContain("Reader satisfaction");
  });

  test("keeps illustrative reader perspectives distinct from customer testimonials", () => {
    expect(source).toContain("Made for the love of reading");
    expect(home).toContain("<ReferenceHomeSurface");
    expect(home).toContain("<ReaderPerspectives />");
    expect(perspectives).not.toMatch(/ReaderTestimonialsSection|What Our Readers Say|REAL READERS|verified reader/);
    expect(perspectives).toContain("What reading can feel like");
    expect(perspectives).toContain("Reader perspectives · imagined with care");
    expect(perspectives).toContain("Illustrative reader perspective");
    expect(perspectives).toContain("Four imagined reader perspectives.");
    expect(perspectives).toContain('to="/library" className="reference-button reference-button--gold" data-testid="reader-perspectives-cta"');
    for (const city of ["kolkata", "london", "chennai", "new-delhi"]) expect(perspectives).toContain(`${city}-reader.webp`);
    expect(perspectiveStyles).toContain(".reference-reader-perspectives__grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))");
    expect(perspectiveStyles).toContain(".reference-reader-perspectives__grid{grid-template-columns:repeat(2,minmax(0,1fr))");
    expect(perspectiveStyles).toContain(".reference-reader-perspectives__grid{grid-template-columns:1fr");
  });

  test("uses the reviewed operational-facts fallback when public metrics are not eligible", () => {
    expect(commerce).toContain("Price and validity together");
    expect(commerce).toContain("No auto-renewal");
    expect(evidence.status).toBe("FALLBACK_OPERATIONAL_FACTS_ONLY");
    expect(evidence.metrics).toEqual([]);
    expect(evidence.fallback_notice).toBe("Verified behavioral metrics will appear after the publication threshold is met.");
    expect(evidence.publication_policy.minimum_eligible_unique_readers).toBe(100);
    expect(evidence.publication_policy.minimum_eligible_reading_sessions).toBe(500);
  });

  test("uses one dark, constrained shared public surface and book-tile contract", () => {
    expect(styles).toContain("EARNALISM_GILDED_BURGUNDY_V1");
    expect(styles).toContain("var(--book-card-width-desktop)");
    expect(styles).toContain("grid-auto-columns:var(--book-card-width-desktop)");
    expect(styles).toContain("grid-template-columns:repeat(auto-fill,var(--book-card-width-desktop))");
    expect(styles).toContain("aspect-ratio:2/3");
    expect(styles).toContain("background:var(--reference-surface)");
    expect(styles).toContain("background:var(--reference-elevated)");
    expect(styles).not.toContain("background:var(--reference-paper);color:#1e2822");
  });

  test("uses the release-safe Home curation snapshot when the catalogue is temporarily unavailable", () => {
    expect(source).toContain("ReferenceHomeSurface({ curation, readingPasses = [], listeningItems = [], illustrativePasses = false })");
    expect(source).toContain("curation?.hero?.featured_books");
    expect(source).toContain("liveBooks.length ? liveBooks : curatedBooks.filter(isLive)");
    expect(source).toContain("canShowPreview(book)");
    expect(source).toContain("canShowStartReading(book)");
    expect(source).toContain(">Details</Link>");
  });

  test("fits nine cover slots only at wide desktop without altering release eligibility", () => {
    expect(homeLaunchStyles).toContain("@media (min-width: 1440px)");
    expect(homeLaunchStyles).toContain("grid-auto-columns: calc((100% - 8 * 12px) / 9)");
    expect(homeLaunchStyles).toContain("aspect-ratio: 2/3");
    expect(homeLaunchStyles).toContain("object-fit: contain");
    expect(source).toContain("books.filter(isLive)");
    expect(source).not.toContain("books.length ? books : curatedBooks");
    expect(source).toContain(".slice(0, 10)");
  });

  test("keeps the controlled Library fallback reader-ready and audio-hidden", () => {
    expect(libraryFallback).toContain('reader_enabled: true');
    expect(libraryFallback).toContain('public_route: "/book/devdas"');
    expect(libraryFallback).toContain('reader_url: "/reader/devdas"');
    expect(libraryFallback).toContain('preview_enabled: true');
    expect(libraryFallback).toContain('audiobook_enabled: false');
    expect(libraryFallback).not.toContain('audio_url');
  });

  test("keeps the mobile Library filter panel route-driven and release-safe", () => {
    expect(source).toContain('reference-library-drawer');
    expect(source).toContain('reference-filter-reset');
    expect(source).toContain('hideAll');
    expect(source).toContain('showAllForGroups={["listening"]}');
    expect(source).toContain('shouldHideAllOption(key, slug)');
    expect(source).toContain('"Genre"');
    expect(source).toContain('element.setAttribute("inert", "")');
    expect(source).toContain('document.body.style.overflow = "hidden"');
    expect(source).not.toContain('Free audiobook preview');
  });
});
