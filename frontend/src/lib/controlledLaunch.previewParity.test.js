import {
  BATCH_2_AUDIOBOOK_SLUGS,
  DRACULA_FALLBACK_BOOK,
  PAID_ONLY_READER_SLUGS,
  canShowAudioCTA,
  canShowPreview,
  canShowStartReading,
} from "./controlledLaunch";

function paidOnlyBook(slug) {
  return {
    slug,
    publication_status: "LIVE_APPROVED",
    reader_enabled: true,
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
  test.each(PAID_ONLY_READER_SLUGS)("keeps %s readable without a preview CTA", (slug) => {
    const book = paidOnlyBook(slug);

    expect(canShowStartReading(book)).toBe(true);
    expect(canShowPreview(book)).toBe(false);
  });

  test("rejects stale preview flags when no chapter is explicitly previewable", () => {
    const book = {
      ...paidOnlyBook(PAID_ONLY_READER_SLUGS[0]),
      preview_enabled: true,
      preview_url: `/reader/${PAID_ONLY_READER_SLUGS[0]}`,
    };

    expect(canShowPreview(book)).toBe(false);
  });

  test("requires matching preview flag, URL, and explicit chapter evidence", () => {
    const markedBook = {
      ...paidOnlyBook(PAID_ONLY_READER_SLUGS[0]),
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

  test.each(BATCH_2_AUDIOBOOK_SLUGS)("allows checksum-gated audio for %s", (slug) => {
    const book = {
      ...paidOnlyBook(slug),
      audio_enabled: true,
      audiobook_enabled: true,
      audio_qa_status: "QA_PASSED",
    };

    expect(canShowStartReading(book)).toBe(true);
    expect(canShowAudioCTA(book)).toBe(true);
  });

  test.each(BATCH_2_AUDIOBOOK_SLUGS)("keeps %s audio hidden until QA passes", (slug) => {
    const book = {
      ...paidOnlyBook(slug),
      audio_enabled: true,
      audiobook_enabled: true,
      audio_qa_status: "PENDING",
    };

    expect(canShowStartReading(book)).toBe(true);
    expect(canShowAudioCTA(book)).toBe(false);
  });
});
