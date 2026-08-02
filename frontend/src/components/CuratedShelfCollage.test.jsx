import fs from "fs";
import path from "path";
import { normalizeHomeCuration } from "../lib/homeCuration";
import {
  allocateUniqueShelfBooks,
  getShelfCountLabel,
  getShelfVariant,
  getUniqueShelfBooks,
} from "../lib/homeShelfRunway";
import { buildShelfGridLayout, normalizeShelfArea } from "../lib/shelfGridLayout";

const componentSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/CuratedShelfCollage.jsx"),
  "utf8",
);
const tileSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/ShelfCollageTile.jsx"),
  "utf8",
);
const listeningSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/SelectedListeningRail.jsx"),
  "utf8",
);
const stylesSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/CuratedShelfCollage.css"),
  "utf8",
);

const readerBook = {
  slug: "reader-book",
  title: "A Reader Book",
  author: "A Canonical Author",
  language: "en",
  front_cover_url: "https://cdn.example.com/reader-book.png",
  cover_alt_text: "A Reader Book by A Canonical Author",
  reader_enabled: true,
  audiobook_enabled: false,
  book_url: "/book/reader-book",
  cta_url: "/reader/reader-book",
};

const approvedBook = {
  ...readerBook,
  slug: "approved-book",
  title: "An Approved Classic",
  audiobook_enabled: true,
  audiobook_release_gate: "PUBLIC_AUDIO_RELEASE_APPROVED",
  audio_qa_status: "QA_PASSED",
  audiobook_url: "/api/reader/book/approved-book/audiobook",
  book_url: "/book/approved-book",
  cta_url: "/reader/approved-book?listen=1",
};

describe("CuratedShelfCollage", () => {
  test("renders exact catalog metadata and customer-facing shelf actions", () => {
    const normalized = normalizeHomeCuration({
      shelf_collage: {
        groups: [{
          id: "test-shelf",
          title: "A Test Shelf",
          description: "A quiet promise for readers.",
          book_count: 1,
          books: [readerBook],
          cta_label: "Explore this shelf",
          cta_url: "/library?shelf=test-shelf",
          visual_variant: "feature",
          icon: "book-open",
        }],
        selected_audiobooks: [approvedBook],
      },
    });

    expect(normalized.shelf_collage.groups[0]).toMatchObject({
      title: "A Test Shelf",
      cta_url: "/library?shelf=test-shelf",
      books: [{
        title: "A Reader Book",
        author: "A Canonical Author",
        cover_alt_text: "A Reader Book by A Canonical Author",
        book_url: "/book/reader-book",
      }],
    });
    expect(componentSource).toContain('data-testid="curated-shelf-collage"');
    expect(tileSource).toContain('aria-label={`Open ${book.title} by ${book.author}`}');
    expect(tileSource).toContain("to={book.book_url}");
  });

  test("keeps hidden-audio shelves reader-oriented and approved listening customer-facing", () => {
    const normalized = normalizeHomeCuration({
      shelf_collage: { selected_audiobooks: [approvedBook] },
    });

    expect(normalized.shelf_collage.selected_audiobooks[0]).toMatchObject({
      cta_label: "Start Listening",
      cta_kind: "listen",
      cta_url: "/reader/approved-book?listen=1",
    });
    expect(listeningSource).toContain("Listen in Reader");
    expect(componentSource).not.toMatch(/release gate|QA_PASSED|unapproved audio|manifest|endpoint/i);
  });

  test("uses explicit editorial areas and responsive two-column composition", () => {
    expect(componentSource).toContain("buildShelfGridLayout");
    expect(componentSource).toContain("normalizeShelfArea");
    expect(stylesSource).toContain("grid-template-areas: var(--shelf-grid-areas-tablet)");
    expect(stylesSource).toContain("grid-template-areas: var(--shelf-grid-areas-mobile)");
    expect(componentSource).toContain('curated-shelf-collage--missing-short');
    expect(stylesSource).toContain("grid-area: var(--shelf-area)");
    expect(tileSource).toContain("data-layout-area={shelfArea");
  });

  test("normalizes production shelf IDs and keeps missing shelves compact", () => {
    expect(normalizeShelfArea({ id: "bengali-life-and-legacy" })).toBe("bengali");
    expect(normalizeShelfArea({ id: "gothic-and-the-uncanny" })).toBe("gothic");
    expect(normalizeShelfArea({ id: "love-society-and-human-nature" })).toBe("love");
    expect(normalizeShelfArea({ id: "short-masterpieces" })).toBe("short");

    const layout = buildShelfGridLayout([
      { id: "bengali-life-and-legacy" },
      { id: "gothic-and-the-uncanny" },
      { id: "love-society-and-human-nature" },
      { id: "short-masterpieces" },
    ]);

    expect(layout.desktop).toBe('"bengali bengali bengali bengali bengali bengali bengali gothic gothic gothic gothic gothic" "love love love love love love short short short short short short"');
    expect(layout.desktop).not.toContain('"bengali bengali bengali bengali bengali bengali bengali bengali bengali bengali bengali bengali"');
    expect(layout.desktopRowCount).toBe(2);
    expect(layout.tablet).toBe('"bengali bengali" "gothic love" "short short"');
  });

  test("preserves the full editorial five-shelf composition", () => {
    const layout = buildShelfGridLayout([
      { id: "bengali-life-and-legacy" },
      { id: "gothic-and-the-uncanny" },
      { id: "love-society-and-human-nature" },
      { id: "adventure-nature-and-wonder" },
      { id: "short-masterpieces" },
    ]);

    expect(layout.desktop).toBe('"bengali bengali bengali bengali bengali bengali bengali gothic gothic gothic gothic gothic" "love love love love adventure adventure adventure adventure adventure short short short"');
    expect(layout.desktopRowCount).toBe(2);
  });

  test("adapts the card anatomy to the number of valid canonical covers", () => {
    expect(getShelfVariant({ books: [readerBook] })).toBe("spotlight");
    expect(getShelfVariant({ books: [readerBook, { ...readerBook, slug: "second" }] })).toBe("duo-shelf");
    expect(getShelfVariant({ books: [readerBook, { ...readerBook, slug: "second" }, { ...readerBook, slug: "third" }] })).toBe("shelf-feature");
    expect(getShelfVariant({ books: [] })).toBe("editorial");
    expect(getShelfCountLabel({ books: [readerBook] })).toBe("Featured classic");
    expect(getShelfCountLabel({ book_count: 10, books: [readerBook] })).toBe("10 curated titles");
    expect(getUniqueShelfBooks({ books: [readerBook, readerBook, { ...readerBook, slug: "second" }] })).toHaveLength(2);
  });

  test("crops the nested canonical cover image and exposes stable cover-count variants", () => {
    expect(stylesSource).toContain(".curated-shelf-tile__cover .book-cover-image__img");
    expect(stylesSource).toContain("object-fit: cover;");
    expect(tileSource).toContain("data-cover-count={books.length}");
    expect(stylesSource).toContain(".curated-shelf-tile--spotlight .curated-shelf-tile__covers");
    expect(stylesSource).toContain(".curated-shelf-tile--duo-shelf .curated-shelf-tile__covers");
  });

  test("allocates each canonical cover to only one collage tile", () => {
    const duplicate = { ...readerBook, slug: "duplicate" };
    const unique = { ...readerBook, slug: "unique" };
    const groups = allocateUniqueShelfBooks([
      { id: "gothic-and-the-uncanny", books: [duplicate] },
      { id: "short-masterpieces", display_mode: "runway", books: [duplicate, unique] },
    ]);

    expect(groups.map((group) => group.books.map((book) => book.slug))).toEqual([
      ["duplicate"],
      ["unique"],
    ]);
    expect(componentSource).toContain("allocateUniqueShelfBooks");
  });

  test("preserves an editorial shelf when canonical cover art is unavailable", () => {
    const groups = allocateUniqueShelfBooks([{ id: "sparse", book_count: 4, books: [] }]);
    expect(groups).toHaveLength(1);
    expect(groups[0]).toMatchObject({ id: "sparse", book_count: 4, books: [] });
    expect(tileSource).toContain("curated-shelf-tile__editorial-mark");
    const normalized = normalizeHomeCuration({
      shelf_collage: { groups: [{ id: "sparse", book_count: 4, books: [] }] },
    });
    expect(normalized.shelf_collage.groups).toHaveLength(1);
  });

  test("keeps the final production geometry contract collision resistant", () => {
    expect(stylesSource).toContain("Production geometry contract");
    expect(stylesSource).toContain('grid-template-areas:\n    "meta covers"');
    expect(stylesSource).toContain("grid-template-columns: repeat(3, minmax(0, 1fr));");
    expect(stylesSource).toContain("grid-template-rows: repeat(var(--shelf-grid-row-count-mobile), minmax(0, auto));");
    expect(stylesSource).toContain(".curated-shelf-tile--runway .curated-shelf-tile__body > h3");
    expect(stylesSource).toContain("overflow-wrap: normal;");
    expect(stylesSource).toContain("word-break: normal;");
  });

  test("does not use public governance language or placeholder imagery", () => {
    expect(tileSource).toContain("getShelfVariant");
    expect(tileSource).toContain("getShelfThemeChips");
    expect(componentSource).not.toMatch(/release gate|QA_PASSED|unapproved audio|manifest|endpoint/i);
    expect(stylesSource).toContain("prefers-reduced-motion: reduce");
  });

  test("filters placeholder metadata and keeps the collage free of graphical fallbacks", () => {
    const normalized = normalizeHomeCuration({
      shelf_collage: {
        groups: [{
          id: "test-shelf",
          title: "A Test Shelf",
          books: [{ ...readerBook, cover_valid: false, is_placeholder: true }, { ...readerBook, slug: "reader-book-valid", cover_valid: true }],
        }],
      },
    });

    expect(normalized.shelf_collage.groups[0].books).toHaveLength(1);
    expect(normalized.shelf_collage.groups[0].books[0].slug).toBe("reader-book-valid");
    expect(tileSource).toContain("allowGraphicalFallback={false}");
    expect(listeningSource).toContain("allowGraphicalFallback={false}");
    expect(fs.readFileSync(path.join(process.cwd(), "src/components/BookCoverImage.jsx"), "utf8"))
      .toContain("if (!allowGraphicalFallback && !showImage) return null;");
  });

  test("uses canonical counts, routes, and selected listening only", () => {
    const normalized = normalizeHomeCuration({
      shelf_collage: {
        groups: [{
          id: "short-masterpieces",
          layout_area: "short",
          accent: "short",
          book_count: 2,
          books: [readerBook, { ...readerBook, slug: "second", title: "Second Book", book_url: "/book/second" }],
        }],
        selected_audiobooks: [approvedBook, readerBook],
      },
    });

    expect(normalized.shelf_collage.groups[0]).toMatchObject({
      book_count: 2,
      layout_area: "short",
      accent: "short",
    });
    expect(normalized.shelf_collage.selected_audiobooks.map((book) => book.slug)).toEqual(["approved-book"]);
  });
});
