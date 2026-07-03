const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const BATCH_SLUGS = [
  "frankenstein",
  "jekyll-and-hyde",
  "carmilla",
  "hound-of-the-baskervilles",
  "picture-of-dorian-gray",
  "woman-in-white",
  "hungry-stones",
  "devdas",
  "pather-panchali",
  "eyesore-chokher-bali",
];
const BENGALI_SLUGS = new Set(["devdas", "pather-panchali"]);
const CLAIMABLE_AUDIO_SLUGS = [
  "alices-adventures-in-wonderland",
  "bn-027",
  "lokrahasya",
  "mrinalini",
  "nishkriti",
  "the-wonderful-wizard-of-oz",
  "bn-059",
  "bn-066",
  "the-art-of-money-getting",
];
const BOILERPLATE_RE = /Project Gutenberg|Gutenberg-tm|START OF THE PROJECT|END OF THE PROJECT|Wikisource|Category:|Creative Commons|Download as|Edit this page/i;
const AUDIO_FIELDS = ["audio_enabled", "audiobook_enabled", "generate_audiobook"];

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relativePath), "utf8"));
}

function read(relativePath) {
  return fs.readFileSync(path.join(ROOT, relativePath), "utf8");
}

function chapterFiles(slug) {
  const dir = path.join(ROOT, "content", "books", slug, "chapters");
  return fs.readdirSync(dir).filter((name) => name.endsWith(".json")).sort();
}

function allReaderText(slug) {
  return chapterFiles(slug)
    .map((name) => readJson(path.join("content", "books", slug, "chapters", name)).content || "")
    .join("\n");
}

describe("Reader content quality batch 1", () => {
  const manifest = readJson("book_import_manifest.batch-1.json");
  const quality = readJson("content/books/reader-content-quality-report.json");
  const promotion = readJson("content/books/batch-1-promotion-report.json");
  const launch = readJson("data/controlled_launch.json");

  test("manifest configures the controlled bilingual batch only", () => {
    expect(manifest.books.map((book) => book.slug)).toEqual(BATCH_SLUGS);
    for (const book of manifest.books) {
      expect(book.intendedStatus).toBe("auto_promote_if_all_gates_pass");
      expect(book.legalReviewRequired).toBe(true);
      expect(book.allowAutoLiveAfterValidation).toBe(true);
    }
    const hungry = manifest.books.find((book) => book.slug === "hungry-stones");
    expect(hungry.extractionMode).toBe("extract_single_story");
    expect(hungry.storyTitle).toBe("The Hungry Stones");
    const eyesore = manifest.books.find((book) => book.slug === "eyesore-chokher-bali");
    expect(eyesore.sourceUrl).toBe("https://en.wikisource.org/wiki/Eyesore");
    expect(eyesore.language).toBe("en");
    expect(eyesore.originalLanguage).toBe("bn");
  });

  test("every configured book has source rights, raw source, chapters, and 100 quality score", () => {
    expect(quality.totalBooksConfigured).toBe(BATCH_SLUGS.length);
    expect(quality.passingBooks).toEqual(BATCH_SLUGS);
    expect(quality.heldBooks).toEqual([]);
    for (const slug of BATCH_SLUGS) {
      const bookDir = path.join(ROOT, "content", "books", slug);
      expect(fs.existsSync(path.join(bookDir, "source-rights.md"))).toBe(true);
      expect(fs.readdirSync(path.join(bookDir, "raw")).length).toBeGreaterThan(0);
      expect(chapterFiles(slug).length).toBeGreaterThan(0);
      const result = quality.books.find((item) => item.slug === slug);
      expect(result.status).toBe("PASS_100");
      expect(result.score).toBe(100);
      expect(result.blockers).toEqual([]);
    }
  });

  test("promoted books remain reader-only with no payment, checkout, homepage, or audio exposure", () => {
    expect(launch.live_approved_slugs).toEqual(["dracula", ...BATCH_SLUGS, ...CLAIMABLE_AUDIO_SLUGS]);
    expect(launch.audio_enabled_slugs).toEqual(CLAIMABLE_AUDIO_SLUGS);
    for (const slug of BATCH_SLUGS) {
      const contentBook = readJson(`content/books/${slug}/book.json`);
      const publicBook = readJson(`data/controlled_publications/${slug}/public_book.json`);
      const decision = promotion.books.find((item) => item.slug === slug);
      expect(decision.decision).toBe("PROMOTED_LIVE_READER_ONLY");
      for (const book of [contentBook, publicBook]) {
        expect(book.readerStatus).toBe("reader_ready");
        expect(book.publicationStatus).toBe("live");
        expect(book.isPublic).toBe(true);
        expect(book.isLive).toBe(true);
        expect(book.showInPublicLibrary).toBe(true);
        expect(book.showInHomepage).toBe(false);
        expect(book.allowPublicReading).toBe(true);
        expect(book.allowCheckout).toBe(false);
        expect(book.allowPayment).toBe(false);
        expect(book.is_published).toBe(true);
      }
      for (const field of AUDIO_FIELDS) expect(publicBook[field]).toBe(false);
      expect(publicBook.publication_status).toBe("LIVE_APPROVED");
    }
  });

  test("reader-facing text is sanitized and free of source boilerplate", () => {
    for (const slug of BATCH_SLUGS) {
      const text = allReaderText(slug);
      expect(text).not.toMatch(BOILERPLATE_RE);
      expect(text).not.toContain("�");
      expect(text).not.toMatch(/Ã|Â|â€™|â€œ|â€\u009d|â€”/);
    }
  });

  test("Bengali books remain NFC UTF-8 Bengali text without mojibake", () => {
    for (const slug of BENGALI_SLUGS) {
      const text = allReaderText(slug);
      expect(text).toBe(text.normalize("NFC"));
      const bengaliChars = (text.match(/[\u0980-\u09FF]/g) || []).length;
      const latinChars = (text.match(/[A-Za-z]/g) || []).length;
      expect(bengaliChars).toBeGreaterThan(500);
      expect(bengaliChars).toBeGreaterThan(latinChars * 5);
      expect(text).not.toContain("□");
    }
  });

  test("The Hungry Stones import contains only the approved single story", () => {
    expect(chapterFiles("hungry-stones")).toHaveLength(1);
    const book = readJson("content/books/hungry-stones/book.json");
    expect(book.title).toBe("The Hungry Stones");
    expect(book.displayTitle).toBe("Kshudhita Pashan / The Hungry Stones");
    const text = allReaderText("hungry-stones");
    expect(text).toMatch(/Barich|Susta|marble palace/i);
    expect(text).not.toMatch(/(?:^|\n)(THE VICTORY|The Victory|ONCE THERE WAS A KING|Once There Was a King|THE DEVOTEE|The Devotee|VISION|Vision|THE CABULIWALLAH|The Cabuliwallah)(?:\n|$)/);
  });
});
