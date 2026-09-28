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
const optionBStyles = fs.readFileSync(path.join(process.cwd(), "src/pages/HomeOptionB.css"), "utf8");
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
    expect(homeLaunchStyles).not.toMatch(/\.home-reference-page--no-commerce \.reference-home__pass\s*[,\{]/);
    expect(source).toContain("Pass purchases are not available yet");
    expect(source).toContain('to={PUBLIC_PAID_COMMERCE_ENABLED ? "/pricing" : "/library"}');
    expect(source).toContain("Pass purchases are not available yet");
    expect(homeLaunchStyles).toContain(".home-reference-page--no-commerce .reference-home__policy > p:nth-of-type(2)");
    expect(homeLaunchStyles).toContain(".home-reference-page--no-audio .reference-home__cta-row a[href=\"/library?availability=approved-audiobook\"]");
    expect(home).toContain("if (!PUBLIC_PAID_COMMERCE_ENABLED) return undefined;");
    expect(home).toContain("if (!PUBLIC_AUDIO_EXPOSURE_ENABLED) return undefined;");
  });

  test("keeps Home discovery editorial and avoids a second dynamic catalogue shelf", () => {
    for (const category of ["Bengali Classics", "English Classics", "Modern Favourites", "Curated Collections"]) {
      expect(source).toContain(category);
    }
    expect(source).not.toContain('api.get("/books"');
    expect(source).not.toContain("home-journey-shelf");
    expect(source).toContain('to="/library?availability=approved-audiobook"');
  });

  test("binds offer presentation to current configured offer fields", () => {
    expect(commerce).toContain("pack.price_inr");
    expect(commerce).toContain("pack.minutes");
    expect(commerce).toContain("pack.recommended === true || pack.is_recommended === true");
    expect(commerce).toContain("Purchased unused minutes do not expire");
  });

  test("keeps all four approved Reading Pass offers visible on the responsive Home surface", () => {
    expect(source).toContain(".slice(0, 4)");
    expect(styles).toContain(".reference-home__pass-cards{grid-template-columns:repeat(4,minmax(0,1fr))}");
    expect(styles).toContain(".reference-home__pass-cards{grid-template-columns:repeat(2,minmax(0,1fr))}");
    expect(styles).toContain(".reference-home__pass-cards{grid-template-columns:1fr}");
    expect(homeLaunchStyles).toContain("grid-template-columns: repeat(4, minmax(0, 1fr));");
    expect(homeLaunchStyles).toContain("grid-template-columns: repeat(2, minmax(0, 1fr));");
    expect(homeLaunchStyles).toContain("grid-template-columns: 1fr;");
    expect(homeLaunchStyles).toContain("overflow: visible;");
  });

  test("uses one truthful Commerce composition without an obsolete research rail", () => {
    expect(commerce).not.toContain('reference-commerce__insight-rail');
    expect(commerce).not.toContain('reference-commerce__hero-proof');
    expect(commerce).not.toContain("Use study across 2,400+ readers");
    expect(commerce).not.toContain("Reader satisfaction");
  });

  test("keeps illustrative reader perspectives distinct from customer testimonials", () => {
    expect(home).toContain("<ReferenceHomeSurface");
    expect(source).toContain("<ReaderPerspectives />");
    expect(source.indexOf("<ReaderPerspectives />")).toBeLessThan(source.indexOf('<section className="reference-home__pass"'));
    expect(perspectives).not.toMatch(/ReaderTestimonialsSection|What Our Readers Say|REAL READERS|verified reader/);
    expect(perspectives).toContain("WHAT READING CAN FEEL LIKE");
    expect(perspectives).toContain("A slower mind");
    expect(perspectives).toContain("A wider world");
    expect(perspectives).toContain("A more thoughtful you");
    expect(perspectives).toContain("Explore four illustrative reader perspectives");
    for (const city of ["kolkata", "london", "chennai", "new-delhi"]) expect(perspectives).toContain(`${city}-reader.webp`);
    expect(perspectiveStyles).toContain(".reference-reader-perspectives__benefits");
    expect(perspectiveStyles).toContain(".reference-reader-perspectives__portraits img");
    expect(perspectiveStyles).toContain("@media (max-width: 767px)");
  });

  test("ships the Option B homepage hierarchy and keeps exact responsive offer breakpoints", () => {
    expect(source).toContain("A calmer place for<br />timeless reading.");
    expect(source).toContain("golden-hour-library-hero.webp");
    expect(source).toContain("PUBLIC_AUDIO_EXPOSURE_ENABLED && Array.isArray(listeningItems)");
    expect(home).toContain('import "./HomeOptionB.css"');
    expect(optionBStyles).toContain("grid-template-columns: repeat(4, minmax(0, 1fr))");
    expect(optionBStyles).toContain("grid-template-columns: repeat(2, minmax(0, 1fr))");
    expect(optionBStyles).toContain("grid-template-columns: 1fr");
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

  test("keeps approved audiobook cards behind the public release gate", () => {
    expect(source).toContain("PUBLIC_AUDIO_EXPOSURE_ENABLED && Array.isArray(listeningItems)");
    expect(source).toContain("audiobookReleaseState(book).releaseApproved");
    expect(source).toContain("Titles without approval show no listening action.");
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
