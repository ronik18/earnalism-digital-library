import fs from "fs";
import path from "path";
import { normalizeHomeCuration } from "../lib/homeCuration";

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
});
