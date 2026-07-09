import {
  availabilityOfBook,
  languageOfBook,
  libraryPresentationForBook,
  matchesLibraryFacets,
} from "./libraryCatalog";

describe("libraryCatalog", () => {
  it("prefers explicit Bengali language metadata", () => {
    expect(languageOfBook({ language: "ben", title: "Dracula" })).toBe("bn");
  });

  it("maps live reader-only titles to reader-ready with hidden audio", () => {
    const presentation = libraryPresentationForBook({
      slug: "devdas",
      title: "দেবদাস",
      author: "Sarat Chandra Chattopadhyay",
      publication_status: "LIVE_APPROVED",
      audiobook_enabled: false,
    });
    expect(presentation.languageLabel).toBe("Bengali");
    expect(presentation.availabilityLabel).toBe("Reader Ready");
    expect(presentation.audioBadgeLabel).toBe("Audio Hidden");
  });

  it("maps approved reader manifest audio to audiobook approved", () => {
    const book = {
      slug: "book-2b9853ec52",
      title: "দুই বিঘা জমি",
      _readerManifest: {
        audio: {
          enabled: true,
          provider: "sarvam",
          version: "v1",
          assets: { mp3: "https://cdn.example.com/audio.mp3" },
        },
      },
    };
    expect(availabilityOfBook(book)).toBe("approved-audiobook");
    expect(matchesLibraryFacets(book, "bn", "approved-audiobook")).toBe(true);
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
});
