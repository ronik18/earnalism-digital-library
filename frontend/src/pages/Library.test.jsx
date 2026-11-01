import { composeLibraryCatalog } from "../lib/libraryCatalogueComposition";
import { canShowStartReading, canShowPreview } from "../lib/controlledLaunch";

describe("Sherlock canonical editorial consolidation", () => {
  const canonical = () => ({
    id: "synthetic-canonical-only",
    slug: "the-adventures-of-sherlock-holmes",
    title: "The Adventures of Sherlock Holmes",
    publication_status: "LIVE_APPROVED",
    reader_enabled: true,
    preview_enabled: true,
    public_route: "/book/the-adventures-of-sherlock-holmes",
    reader_url: "/reader/the-adventures-of-sherlock-holmes",
    preview_url: "/reader/the-adventures-of-sherlock-holmes",
    chapters: Array.from({ length: 12 }, (_, i) => ({ id: `fixture-${i}`, is_preview: i === 0 })),
    cover_image_url: "/assets/books/the-adventures-of-sherlock-holmes/front-cover.webp",
    back_cover_image_url: "/assets/books/the-adventures-of-sherlock-holmes/back-cover.webp",
  });

  test("deduplicates the admitted edition without changing its links or covers", () => {
    const book = canonical();
    const books = composeLibraryCatalog([book, book]);
    expect(books.filter((item) => item.slug === book.slug)).toEqual([book]);
    expect(books.some((item) => item.slug === "sherlock-holmes")).toBe(false);
    expect(canShowStartReading(book)).toBe(true);
    expect(canShowPreview(book)).toBe(true);
  });

  test.each([
    ["absent", null],
    ["reader held", { reader_enabled: false }],
    ["draft", { publication_status: "DRAFT" }],
    ["wrong book route", { public_route: "/book/sherlock-holmes" }],
    ["wrong reader route", { reader_url: "/reader/sherlock-holmes" }],
    ["rights held", { publication_workflow: { rights: { tier: "C" } } }],
  ])("retains the queued shell when canonical is %s", (_, override) => {
    const books = composeLibraryCatalog(override === null ? [] : [{ ...canonical(), ...override }]);
    expect(books.some((item) => item.slug === canonical().slug)).toBe(false);
    const shell = books.find((item) => item.slug === "sherlock-holmes");
    expect(shell).toBeDefined();
    expect(canShowStartReading(shell)).toBe(false);
    expect(canShowPreview(shell)).toBe(false);
  });

  test("the editorial mapping never grants access to the generic slug", () => {
    const shell = { ...canonical(), slug: "sherlock-holmes" };
    expect(canShowStartReading(shell)).toBe(false);
    expect(canShowPreview(shell)).toBe(false);
  });
});
