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

  test("uses the Reading Circle as a private dispatch conversion close", () => {
    expect(source).toContain("A private letter for readers who linger.");
    expect(source).toContain("Reader-ready editions");
    expect(source).toContain("Listening-room openings");
    expect(source).toContain("Notes from the library");
    expect(source).toContain("Leave your name and email to receive the next genuine release note.");
    expect(source).toContain('id="newsletter-name"');
    expect(source).toContain('id="newsletter-email"');
    expect(source).toContain('aria-live="polite"');
    expect(source).not.toContain("rights review");
    expect(source).not.toContain("No audiobook or paid campaign is live from this form.");
  });
});
