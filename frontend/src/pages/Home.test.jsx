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
    expect(source).toContain("fetchHomeHero(controller.signal)");
    expect(source).toContain("<HomeListeningRoom />");
    expect(source).not.toContain("fetchHomeCuration(controller.signal)");
    expect(source).not.toContain("homeCurationLoading");
  });

  test("places three accurate discovery paths before monetization", () => {
    expect(source).toContain("home-quick-paths");
    expect(source).toContain("Enter the Bengali collection");
    expect(source).toContain("Enter the English collection");
    expect(source).toContain("Step into the listening room");
    expect(source.indexOf("home-quick-paths")).toBeLessThan(source.indexOf("reading-time-library-path"));
  });

  test("uses the Reading Circle as a private dispatch conversion close", () => {
    expect(source).toContain("A private letter for readers who linger.");
    expect(source).toContain("Beautiful new editions");
    expect(source).toContain("Intimate listening rooms");
    expect(source).toContain("Letters from the library");
    expect(source).toContain("Share your name and email; we will write only when a story is worth opening together.");
    expect(source).toContain('id="newsletter-name"');
    expect(source).toContain('id="newsletter-email"');
    expect(source).toContain('aria-live="polite"');
    expect(source).not.toContain("rights review");
    expect(source).not.toContain("No audiobook or paid campaign is live from this form.");
  });
});
