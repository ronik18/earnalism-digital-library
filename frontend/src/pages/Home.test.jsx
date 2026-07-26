import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/pages/Home.jsx"), "utf8");

describe("Home curated shelf integration", () => {
  test("replaces the internal below-hero panels with the public shelf collage", () => {
    expect(source).toContain("CuratedShelfCollage");
    expect(source).toContain("homeCuration?.shelf_collage");
    expect(source).not.toContain("ComingSoonBoard");
    expect(source).not.toContain("ApprovedAudiobookSpotlight");
    expect(source).not.toContain("reference-pipeline-shelf");
    expect(source).not.toMatch(/Release truth preserved|No unapproved audio|Reader-only editions live|release gates/i);
  });
});
