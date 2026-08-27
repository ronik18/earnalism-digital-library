import fs from "fs";
import path from "path";

describe("public static SEO contract", () => {
  test("states the canonical three-page and zero-free-audio boundaries required by the production canary", () => {
    const generator = fs.readFileSync(path.join(process.cwd(), "scripts/generate-static-seo-snapshots.mjs"), "utf8");
    const sitemapGenerator = fs.readFileSync(path.join(process.cwd(), "scripts/generate-seo-assets.mjs"), "utf8");

    expect(generator).toContain("earnalism.static-seo-public.v2");
    expect(generator).toContain("Read the first 3 pages free. Listening requires an active Reading Pass.");
    expect(generator).toContain("Public audio preview: 0 seconds.");
    expect(sitemapGenerator).toContain("loadPublicEditorialPosts");
    expect(sitemapGenerator).toContain("editorial-public.json");
  });
});
