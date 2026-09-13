import fs from "fs";
import path from "path";
import { composeLibraryCatalog } from "../lib/libraryCatalogueComposition";
import { LOCAL_LIBRARY_FALLBACK_BOOKS } from "../lib/libraryFallbackBooks";

const source = fs.readFileSync(path.join(process.cwd(), "src/pages/Library.jsx"), "utf8");
const referenceSource = fs.readFileSync(path.join(process.cwd(), "src/components/ReferencePublicPages.jsx"), "utf8");

describe("Library experience", () => {
  test("uses the single editorial collection architecture and approved copy", () => {
    expect(source).toContain("ReferenceLibrarySurface");
    expect(referenceSource).toContain('import { PUBLIC_ACCESS_COPY, PUBLIC_PREVIEW_COPY, READING_TIME_COPY } from "../lib/publicAccessCopy"');
    expect(referenceSource).toContain("LibraryReadingPassCard");
    expect(source).toContain("Explore the collection.");
    expect(source).toContain("Search the Library");
    expect(source).toContain("Search by title or author");
    expect(source).toContain("No editions match these filters.");
    expect(source).toContain("Try removing a filter or searching for another title or author.");
    expect(source).not.toContain("Choose a shelf without losing the quiet.");
    expect(source).not.toContain("Three ways into the library");
    expect(source).not.toContain("Curated Reader-Ready Shelves");
  });

  test("preserves release-safe book rendering and URL-synced filters", () => {
    expect(source).toContain("<BookCard");
    expect(source).toContain('params.get("language")');
    expect(source).toContain('params.get("reading")');
    expect(source).toContain("listeningFilterFromSearch(params)");
    expect(source).toContain('params.get("sort")');
    expect(source).toContain('params.get("q")');
    expect(source).toContain("Listening appears only where the release evidence allows it.");
    expect(source).toContain("library-filter-drawer");
    expect(source).toContain('aria-modal="true"');
  });

  test("keeps limited fallback selection explicit and a valid empty catalogue distinct", () => {
    expect(source).toContain('setCatalogueState("fallback")');
    expect(source).toContain('setCatalogueState(booksResult.value.data.length ? "ready" : "empty")');
    expect(source).toContain("retryCatalogue");
    expect(referenceSource).toContain("We couldn’t load the full collection. You’re viewing a limited selection.");
    expect(referenceSource).toContain('data-testid="library-catalogue-retry"');
    expect(referenceSource).toContain('data-testid="library-catalogue-empty"');
  });

  test("suppresses the reviewed Bengali pipeline shell only while its canonical publication is present", () => {
    const canonicalKshudhita = {
      slug: "book-edfcf810c5",
      title: "ক্ষুধিত পাষাণ",
      author: "Rabindranath Tagore",
      language: "bn",
      publication_status: "LIVE_APPROVED",
      reader_enabled: false,
      preview_enabled: false,
    };

    const apiSlugs = composeLibraryCatalog([canonicalKshudhita]).map((book) => book.slug);
    expect(apiSlugs).toContain("book-edfcf810c5");
    expect(apiSlugs).not.toContain("kshudhita-pashan");

    const fallbackSlugs = composeLibraryCatalog(LOCAL_LIBRARY_FALLBACK_BOOKS).map((book) => book.slug);
    expect(fallbackSlugs).toContain("kshudhita-pashan");
    expect(fallbackSlugs).not.toContain("book-edfcf810c5");
    expect(fallbackSlugs).toContain("hungry-stones");
  });
});
