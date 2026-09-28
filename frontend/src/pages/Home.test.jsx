import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/pages/Home.jsx"), "utf8");

describe("Option B homepage composition", () => {
  test("mounts one editorial surface and removes obsolete homepage sections", () => {
    expect(source).toContain("<ReferenceHomeSurface");
    expect(source).not.toContain("HomeShelfArchitecture");
    expect(source).not.toContain("home-quick-paths");
    expect(source).not.toContain("reading-time-library-path");
    expect(source).not.toContain("reference-home__legacy-content");
  });

  test("keeps unsupported listening out of the homepage composition", () => {
    const surface = fs.readFileSync(path.join(process.cwd(), "src/components/EditorialHomeLibrarySurfaces.jsx"), "utf8");
    expect(source).not.toContain("fetchHomeListening");
    expect(surface).not.toContain("reference-home__listening");
    expect(surface).toContain("audiobookReleaseState(book)");
  });

  test("places the four discovery cards before Reading Pass", () => {
    const surface = fs.readFileSync(path.join(process.cwd(), "src/components/EditorialHomeLibrarySurfaces.jsx"), "utf8");
    expect(surface).toContain("reference-home__discovery-grid");
    expect(surface.indexOf("reference-home__discovery-grid")).toBeLessThan(surface.indexOf('section className="reference-home__pass"'));
    expect(surface).toContain('["The Listening Room", <>Stories to hear in quiet moments,<br />on walks, and along the way.</>');
    expect(surface).toContain('"/library?availability=approved-audiobook"');
    expect(surface).toContain("<span><h3>{title}</h3><small>{copy}</small>");
  });

  test("uses one H1 and the requested section heading hierarchy", () => {
    const surface = fs.readFileSync(path.join(process.cwd(), "src/components/EditorialHomeLibrarySurfaces.jsx"), "utf8");
    const perspectives = fs.readFileSync(path.join(process.cwd(), "src/components/ReaderPerspectives.jsx"), "utf8");
    expect(surface.match(/<h1 id="reference-home-title"/g)).toHaveLength(1);
    expect(surface).toContain("A calmer place for<br />timeless reading.");
    expect(surface).toContain("Discover. Read. Listen. Belong.");
    expect(perspectives).toContain("A gentler, richer way to be in the world.");
    expect(surface).toContain("More books. A calmer you.");
    expect(source).toContain("Letters for thoughtful readers.");
  });

  test("adds the release-aware Listening Room between reading perspectives and Reading Pass", () => {
    const surface = fs.readFileSync(path.join(process.cwd(), "src/components/EditorialHomeLibrarySurfaces.jsx"), "utf8");
    const perspectivesIndex = surface.indexOf("<ReaderPerspectives />");
    const listeningIndex = surface.indexOf("<HomepageListeningRoom />");
    const passIndex = surface.indexOf('section className="reference-home__pass"');
    expect(perspectivesIndex).toBeGreaterThanOrEqual(0);
    expect(perspectivesIndex).toBeLessThan(listeningIndex);
    expect(listeningIndex).toBeLessThan(passIndex);
    expect(surface).toContain('PUBLIC_AUDIO_EXPOSURE_ENABLED && <Link');
  });

  test("keeps Listening Room language release-aware and Reading Pass claims time-based", () => {
    const listening = fs.readFileSync(path.join(process.cwd(), "src/components/HomepageListeningRoom.jsx"), "utf8");
    const audioGate = fs.readFileSync(path.join(process.cwd(), "src/lib/homepageAudioGate.js"), "utf8");
    const surface = fs.readFileSync(path.join(process.cwd(), "src/components/EditorialHomeLibrarySurfaces.jsx"), "utf8");
    expect(listening).toContain("homepageAudiobooksForExposure");
    expect(audioGate).toContain('audiobookReleaseState(book).canShowControls === true');
    expect(listening).toContain("Audiobooks, thoughtfully arriving");
    expect(listening).toContain('aria-label={`Listen to ${featured.title_en || featured.title}`}');
    expect(listening).not.toContain("<audio");
    expect(surface).toContain("Listen where available");
    expect(surface).toContain("One-time purchase · unused time never expires.");
    expect(surface).not.toMatch(/unlimited.{0,30}listen|listen.{0,30}unlimited/i);
  });

  test("uses the approved Option B hero with a single readable library CTA", () => {
    const surface = fs.readFileSync(
      path.join(process.cwd(), "src/components/EditorialHomeLibrarySurfaces.jsx"),
      "utf8",
    );
    expect(surface).toContain("A calmer place for<br />timeless reading.");
    expect(surface).toContain("Explore the Library");
    expect(surface).not.toContain("Come for a story.");
    expect(surface).not.toContain("earnalism-black-burgundy-reading-room.webp");
    expect(surface).toContain("/assets/home-option-b/hero-reading-room.webp");
  });

  test("reuses the validated Reading Circle form after the literary quote banner", () => {
    expect(source).toContain("A good story has a gentle way of slowing a busy day.");
    expect(source).toContain("A reflection from the reading room");
    expect(source).toContain("Letters for thoughtful readers.");
    expect(source).toContain("New arrivals, reading lists, essays and more");
    expect(source).toContain('data-testid="newsletter-card"');
    expect(source).toContain('id="newsletter-name"');
    expect(source).toContain('id="newsletter-email"');
    expect(source).toContain('aria-live="polite"');
    expect(source).toContain('api.post("/newsletter", { name, email })');
    expect(source).not.toContain("newly opened listening rooms");
    expect(source).not.toContain("Intimate listening rooms");
  });

  test("leaves one shared social area in the site footer", () => {
    expect(source).not.toContain('className="home-social-navigation"');
    expect(source).not.toContain('data-testid="home-socials"');
  });
});
