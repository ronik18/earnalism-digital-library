import {
  isApprovedHomeAudiobook,
  getHomeCurationSnapshot,
  isSafeHeroCoverUrl,
  normalizeHomeBook,
  normalizeHomeCuration,
} from "./homeCuration";

const baseBook = {
  slug: "reader-book",
  title: "Canonical Title",
  author: "Canonical Author",
  language: "en",
  front_cover_url: "https://cdn.example.com/canonical-cover.png",
  reader_enabled: true,
  audiobook_enabled: false,
  audiobook_release_gate: "PUBLIC_AUDIO_RELEASE_BLOCKED",
  audio_qa_status: "QA_PASSED",
};

describe("homepage curation contract", () => {
  test("omits missing, placeholder, and static-audio cover records", () => {
    expect(isSafeHeroCoverUrl("https://cdn.example.com/cover.png")).toBe(true);
    expect(isSafeHeroCoverUrl("/assets/books/cover.webp")).toBe(true);
    expect(isSafeHeroCoverUrl("")).toBe(false);
    expect(isSafeHeroCoverUrl("/assets/placeholder-cover.svg")).toBe(false);
    expect(isSafeHeroCoverUrl("/audio/cover.png")).toBe(false);
    expect(normalizeHomeBook({ ...baseBook, front_cover_url: "" })).toBeNull();
  });

  test("forces a hidden-audio book back to a reader CTA", () => {
    const book = normalizeHomeBook({
      ...baseBook,
      cta_label: "Listen",
      cta_kind: "listen",
      cta_url: "/reader/reader-book?listen=1",
      audiobook_url: "/api/reader/book/reader-book/audiobook",
    });
    expect(book.audiobook_enabled).toBe(false);
    expect(book.cta_label).toBe("Start Reading");
    expect(book.cta_kind).toBe("read");
    expect(book.cta_url).toBe("/reader/reader-book");
    expect(book).not.toHaveProperty("audiobook_url");
  });

  test("allows listening only with the exact approved API-backed evidence contract", () => {
    const approved = {
      ...baseBook,
      slug: "approved-book",
      audiobook_enabled: true,
      audiobook_release_gate: "PUBLIC_AUDIO_RELEASE_APPROVED",
      audiobook_url: "/api/reader/book/approved-book/audiobook",
    };
    expect(isApprovedHomeAudiobook(approved)).toBe(true);
    expect(normalizeHomeBook(approved)).toMatchObject({
      audiobook_enabled: true,
      cta_label: "Start Listening",
      cta_kind: "listen",
      cta_url: "/reader/approved-book?listen=1",
    });
    expect(isApprovedHomeAudiobook({ ...approved, audiobook_url: "/audio/approved-book.mp3" })).toBe(false);
  });

  test("phone candidates are filtered to approved audiobook records", () => {
    const approved = {
      ...baseBook,
      slug: "approved-book",
      audiobook_enabled: true,
      audiobook_release_gate: "PUBLIC_AUDIO_RELEASE_APPROVED",
      audiobook_url: "/api/reader/book/approved-book/audiobook",
    };
    const payload = normalizeHomeCuration({
      hero: { featured_books: [baseBook, approved] },
      shelves: { approved_audiobooks: [baseBook, approved] },
    });
    expect(payload.hero.featured_books.map((book) => book.slug)).toEqual(["reader-book", "approved-book"]);
    expect(payload.shelves.approved_audiobooks.map((book) => book.slug)).toEqual(["approved-book"]);
  });

  test("ships an immediate truth-gated Sprint 1 snapshot while the live API hydrates", () => {
    const snapshot = getHomeCurationSnapshot();
    expect(snapshot.source).toMatchObject({
      truth_source: "controlled_publications",
      sprint1_active_count: 32,
      approved_audiobook_count: 3,
    });
    expect(snapshot.hero.featured_books).toHaveLength(6);
    expect(snapshot.shelves.approved_audiobooks.map((book) => book.slug).sort()).toEqual([
      "a-ghost-story",
      "book-2b9853ec52",
      "sredni-vashtar",
    ]);
  });
});
