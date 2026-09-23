import fs from "fs";
import path from "path";

describe("public static SEO contract", () => {
  test("keeps sitemap generation fail-closed while the public publication release is held", () => {
    const generator = fs.readFileSync(path.join(process.cwd(), "scripts/generate-static-seo-snapshots.mjs"), "utf8");
    const sitemapGenerator = fs.readFileSync(path.join(process.cwd(), "scripts/generate-seo-assets.mjs"), "utf8");

    expect(generator).toContain("earnalism.static-seo-public.v2");
    expect(generator).toContain("Reader and listening editions are temporarily unavailable");
    expect(generator).toContain("public_release_held");
    expect(sitemapGenerator).toContain("loadPublicEditorialPosts");
    expect(sitemapGenerator).toContain("editorial-public.json");
    expect(sitemapGenerator).toContain("publicReaderExposureEnabled = config.public_reader_exposure_enabled === true");
  });
});
