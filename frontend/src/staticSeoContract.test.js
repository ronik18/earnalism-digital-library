import fs from "fs";
import path from "path";

describe("Dracula static SEO contract", () => {
  test("states the canonical three-page boundary required by the production canary", () => {
    const generator = fs.readFileSync(path.join(process.cwd(), "scripts/generate-static-seo-snapshots.mjs"), "utf8");

    expect(generator).toContain("The first 3 canonical pages are public.");
    expect(generator).toContain("Read the first 3 pages free. Listening requires an active Reading Pass.");
  });
});
