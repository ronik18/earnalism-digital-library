import fs from "fs";
import path from "path";

describe("public static SEO contract", () => {
  test("keeps sitemap generation fail-closed while the public publication release is held", () => {
    const generator = fs.readFileSync(path.join(process.cwd(), "scripts/generate-static-seo-snapshots.mjs"), "utf8");
    const sitemapGenerator = fs.readFileSync(path.join(process.cwd(), "scripts/generate-seo-assets.mjs"), "utf8");

    expect(generator).toContain("earnalism.static-seo-public.v2");
    expect(generator).toContain("Reader and listening editions are temporarily unavailable");
    expect(generator).toContain('"Open the Library"');
    expect(generator).toContain("books.length === indiaReleasedSlugs.size");
    expect(generator).toContain("text_preview_limit_canonical_pages) === 3");
    const publication = JSON.parse(fs.readFileSync(path.join(process.cwd(), "static-seo/controlled-publication-public.json"), "utf8"));
    expect(publication.publications).toHaveLength(6);
    expect(publication.publications.every((book) => book.text_preview_limit_canonical_pages === 3)).toBe(true);
    expect(generator).toContain("public_release_held");
    expect(sitemapGenerator).toContain("loadPublicEditorialPosts");
    expect(sitemapGenerator).toContain("editorial-public.json");
    expect(sitemapGenerator).toContain("publicReaderExposureEnabled = config.public_reader_exposure_enabled === true");
  });
});
