import {
  availabilityOfBook,
  languageOfBook,
  listeningFilterFromSearch,
  libraryPresentationForBook,
  matchesLibraryFacets,
} from "./libraryCatalog";

describe("libraryCatalog", () => {
  it("maps the established reader-ready URL to the existing reader-only filter", () => {
    expect(listeningFilterFromSearch(new URLSearchParams("language=bn&availability=reader-ready"))).toBe("hidden");
    expect(listeningFilterFromSearch(new URLSearchParams("availability=approved-audiobook"))).toBe("available");
    expect(listeningFilterFromSearch(new URLSearchParams("availability=reader-ready&listening=all"))).toBe("all");
  });

  it("prefers explicit Bengali language metadata", () => {
    expect(languageOfBook({ language: "ben", title: "Dracula" })).toBe("bn");
  });

  it("maps live reader-only titles to reader-ready with hidden audio", () => {
    const presentation = libraryPresentationForBook({
      slug: "devdas",
      title: "দেবদাস",
      author: "Sarat Chandra Chattopadhyay",
      publication_status: "LIVE_APPROVED",
      reader_enabled: true,
      public_route: "/book/devdas",
      reader_url: "/reader/devdas",
      preview_enabled: true,
      preview_url: "/reader/devdas",
      chapters: [{ id: "devdas-page-1", is_preview: true }],
      audiobook_enabled: false,
    });
    expect(presentation.languageLabel).toBe("Bengali");
    expect(presentation.availabilityLabel).toBe("Reader Ready");
    expect(presentation.audioBadgeLabel).toBe("Audio Hidden");
  });

  it("classifies a verified public audio release without treating it as operational listening", () => {
    const book = {
      slug: "book-2b9853ec52",
      title: "দুই বিঘা জমি",
      publication_status: "LIVE_APPROVED",
      reader_enabled: true,
      public_route: "/book/book-2b9853ec52",
      reader_url: "/reader/book-2b9853ec52",
      audio_enabled: true,
      audiobook_enabled: true,
      audiobook_release_gate: "APPROVED",
      audio_qa_status: "QA_PASSED",
      audio_url: "",
    };
    expect(availabilityOfBook(book)).toBe("approved-audiobook");
    expect(matchesLibraryFacets(book, "bn", "approved-audiobook")).toBe(true);
    expect(libraryPresentationForBook(book).audioBadgeLabel).toBe("Listening unavailable");
  });

  it("keeps pipeline titles in preparation", () => {
    const presentation = libraryPresentationForBook({
      slug: "pipeline-title",
      title: "Pipeline Title",
      author: "Author",
      publication_status: "DRAFT",
    });
    expect(presentation.availabilityLabel).toBe("In Preparation");
    expect(presentation.audioBadgeLabel).toBe("Release Gated");
  });

  it("does not promote a batch-listed draft or a reader-disabled edition from raw status alone", () => {
    const batchListedDraft = {
      slug: "frankenstein",
      title: "Batch listed draft",
      publication_status: "DRAFT",
      reader_enabled: false,
      audiobook_enabled: false,
    };
    const readerDisabledEdition = {
      slug: "reader-disabled-edition",
      title: "Reader disabled edition",
      publication_status: "LIVE_APPROVED",
      reader_enabled: false,
      audiobook_enabled: false,
    };

    [batchListedDraft, readerDisabledEdition].forEach((book) => {
      expect(availabilityOfBook(book)).toBe("in-preparation");
      expect(matchesLibraryFacets(book, "bn", "audio-hidden")).toBe(false);
    });
  });

  it("keeps a reader-approved edition visible while its preview remains unavailable", () => {
    const previewDisabledEdition = {
      slug: "book-d19e96859f",
      title: "গিন্নি",
      language: "bn",
      publication_status: "LIVE_APPROVED",
      reader_enabled: true,
      public_route: "/book/book-d19e96859f",
      reader_url: "/reader/book-d19e96859f",
      preview_enabled: false,
      preview_url: "",
      chapters: [{ id: "chapter-001", is_preview: false }],
      audiobook_enabled: false,
      audio_enabled: false,
    };

    expect(availabilityOfBook(previewDisabledEdition)).toBe("reader-ready");
    expect(matchesLibraryFacets(previewDisabledEdition, "bn", "audio-hidden")).toBe(true);
  });
});
