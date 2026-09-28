import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/pages/Home.jsx"), "utf8");

describe("Home curated shelf integration", () => {
  test("replaces the internal below-hero panels with the public shelf collage", () => {
    expect(source).toContain("HomeShelfArchitecture");
    expect(source).not.toContain("ComingSoonBoard");
    expect(source).not.toContain("ApprovedAudiobookSpotlight");
    expect(source).not.toContain("reference-pipeline-shelf");
    expect(source).not.toMatch(/Release truth preserved|No unapproved audio|Reader-only editions live|release gates/i);
  });

  test("keeps live hero and listening refreshes independent", () => {
    expect(source).toContain("fetchHomeListening(controller.signal, 3)");
    expect(source).toContain("listeningItems={listeningCuration.listening_rooms?.items");
    expect(source).not.toContain("fetchHomeHero(controller.signal)");
    expect(source).not.toContain("<HomeListeningRoom />");
    expect(source).not.toContain("fetchHomeCuration(controller.signal)");
    expect(source).not.toContain("homeCurationLoading");
  });

  test("removes the unreachable legacy hero instead of keeping a second visual architecture", () => {
    expect(source).not.toContain("{false && (");
    expect(source).not.toContain("reference-editorial-index");
    expect(source).not.toContain("home_hero_start_reading");
  });

  test("places three accurate discovery paths before monetization", () => {
    expect(source).toContain("home-quick-paths");
    expect(source).toContain("Enter the Bengali collection");
    expect(source).toContain("Enter the English collection");
    expect(source).toContain("Step into the listening room");
    expect(source.indexOf("home-quick-paths")).toBeLessThan(source.indexOf("reading-time-library-path"));
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
    expect(surface).toContain("golden-hour-library-hero.webp");
  });

  test("reuses the validated Reading Circle form after the literary quote banner", () => {
    expect(source).toContain("Literature is a map of the human heart.");
    expect(source).toContain("Alice Walker");
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
