import {
  DRACULA_FALLBACK_BOOK,
  canShowAudioCTA,
  canShowPreview,
  canShowStartReading,
  isLiveApprovedBook,
} from "./controlledLaunch";

function readerApprovedBook(slug = "reader-approved-edition") {
  return {
    slug,
    publication_status: "LIVE_APPROVED",
    reader_enabled: true,
    public_route: `/book/${slug}`,
    reader_url: `/reader/${slug}`,
    preview_enabled: false,
    preview_url: "",
    is_published: true,
    isPublic: true,
    isLive: true,
    allowCheckout: false,
    allowPayment: false,
    audio_enabled: false,
    audiobook_enabled: false,
    generate_audiobook: false,
    chapters: [{ id: "chapter-001", title: "Full Text", is_preview: false }],
  };
}

describe("controlled launch preview parity", () => {
  test("keeps a reader-approved edition readable without a preview CTA", () => {
    const book = readerApprovedBook("reader-approved-without-preview");

    expect(canShowStartReading(book)).toBe(true);
    expect(canShowPreview(book)).toBe(false);
  });

  test("accepts only the backend public reader projection, not a raw live label", () => {
    const approved = readerApprovedBook("manifest-approved-edition");
    expect(isLiveApprovedBook(approved)).toBe(true);
    expect(isLiveApprovedBook({ ...approved, reader_url: "" })).toBe(false);
    expect(isLiveApprovedBook({ ...approved, public_route: "/book/another-edition" })).toBe(false);
    expect(isLiveApprovedBook({ ...approved, publication_status: "DRAFT" })).toBe(false);
  });

  test("rejects stale preview flags when no chapter is explicitly previewable", () => {
    const book = {
      ...readerApprovedBook(),
      preview_enabled: true,
      preview_url: "/reader/reader-approved-edition",
    };

    expect(canShowPreview(book)).toBe(false);
  });

  test("requires matching preview flag, URL, and explicit chapter evidence", () => {
    const markedBook = {
      ...readerApprovedBook(),
      chapters: [{ id: "chapter-001", title: "Opening", is_preview: true }],
    };

    expect(canShowPreview(markedBook)).toBe(false);
    expect(canShowPreview({
      ...markedBook,
      preview_enabled: true,
      preview_url: `/reader/${markedBook.slug}`,
    })).toBe(true);
  });

  test("preserves Dracula's explicit Chapter 1 preview", () => {
    expect(canShowStartReading(DRACULA_FALLBACK_BOOK)).toBe(true);
    expect(canShowPreview(DRACULA_FALLBACK_BOOK)).toBe(true);
  });

  test("allows an explicitly approved audiobook projection", () => {
    const book = {
      ...readerApprovedBook("approved-audio-edition"),
      audio_enabled: true,
      audiobook_enabled: true,
      audiobook_release_gate: "APPROVED",
      audio_qa_status: "QA_PASSED",
    };

    expect(canShowStartReading(book)).toBe(true);
    expect(canShowAudioCTA(book)).toBe(true);
  });

  test("keeps audio hidden until its independent release evidence passes", () => {
    const book = {
      ...readerApprovedBook("pending-audio-edition"),
      audio_enabled: true,
      audiobook_enabled: true,
      audiobook_release_gate: "APPROVED",
      audio_qa_status: "PENDING",
    };

    expect(canShowStartReading(book)).toBe(true);
    expect(canShowAudioCTA(book)).toBe(false);
  });
});
