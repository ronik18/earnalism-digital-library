import fs from "fs";
import path from "path";

describe("public static SEO contract", () => {
  test("keeps public snapshots aligned to the controlled launch and release-aware copy", () => {
    const generator = fs.readFileSync(path.join(process.cwd(), "scripts/generate-static-seo-snapshots.mjs"), "utf8");
    const sitemapGenerator = fs.readFileSync(path.join(process.cwd(), "scripts/generate-seo-assets.mjs"), "utf8");
    const publication = JSON.parse(fs.readFileSync(path.join(process.cwd(), "static-seo/controlled-publication-public.json"), "utf8"));
    const controlledLaunch = JSON.parse(fs.readFileSync(path.join(process.cwd(), "../data/controlled_launch.json"), "utf8"));

    expect(generator).toContain("earnalism.static-seo-public.v2");
    expect(generator).toContain("Reader and listening editions are temporarily unavailable");
    expect(generator).toContain('"Explore released editions"');
    expect(generator).toContain("const indiaReleasedSlugs = new Set(liveApprovedSlugs)");
    expect(generator).toContain('releasedBookCount + " released India Reader previews."');
    expect(generator).toContain("books.length === liveApprovedSlugs.length");
    expect(generator).toContain("text_preview_limit_canonical_pages) === 3");
    expect(publication.publications.map((book) => book.slug).sort()).toEqual([...controlledLaunch.live_approved_slugs].sort());
    expect(publication.publications.every((book) => book.text_preview_limit_canonical_pages === 3)).toBe(true);
    expect(generator).toContain("public_release_held");
    expect(sitemapGenerator).toContain("loadPublicEditorialPosts");
    expect(sitemapGenerator).toContain("editorial-public.json");
    expect(sitemapGenerator).toContain("publicReaderExposureEnabled = config.public_reader_exposure_enabled === true");
  });
});
