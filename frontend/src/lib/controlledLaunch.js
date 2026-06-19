export const LIVE_APPROVED_SLUG = "dracula";

export const DRACULA_SOURCE_NOTE = "Project Gutenberg eBook #345";
export const DRACULA_RIGHTS_NOTE = "Approved Tier A core reading candidate";
export const DRACULA_CHAPTER_COUNT = 27;

export const DRACULA_FALLBACK_BOOK = {
  slug: LIVE_APPROVED_SLUG,
  title: "Dracula",
  subtitle: "A controlled Earnalism core reading release",
  author: "Bram Stoker",
  category_slug: "gothic-fiction",
  short_description:
    "Begin Bram Stoker's gothic classic in a quiet digital reading room. Chapter 1 is free; the full core reading experience continues with reading time.",
  description:
    "Dracula is the first controlled Earnalism release: a Tier A approved core reading candidate with 27 chapters, a rights-safe source trail, and no audiobook enabled yet.",
  estimated_reading_time: "14 min",
  chapters: Array.from({ length: DRACULA_CHAPTER_COUNT }, (_, index) => ({
    id: `dracula-chapter-${index + 1}`,
    title: index === 0 ? "Chapter 1" : `Chapter ${index + 1}`,
    order: index,
    is_preview: index === 0,
  })),
  audiobook_enabled: false,
  generate_audiobook: false,
  audiobook_assets: {},
};

export const PIPELINE_BOOKS = [
  {
    slug: "frankenstein",
    title: "Frankenstein",
    author: "Mary Wollstonecraft Shelley",
    category_slug: "gothic-fiction",
    statusLabel: "Coming through rights review",
  },
  {
    slug: "sherlock-holmes",
    title: "Sherlock Holmes",
    author: "Arthur Conan Doyle",
    category_slug: "classic-literature",
    statusLabel: "Logic workbook candidate",
  },
  {
    slug: "sultanas-dream",
    title: "Sultana's Dream",
    author: "Rokeya Sakhawat Hossain",
    category_slug: "science-fiction",
    statusLabel: "Rights-safe pipeline",
  },
  {
    slug: "calculus-made-easy",
    title: "Calculus Made Easy",
    author: "Silvanus P. Thompson",
    category_slug: "study-material",
    statusLabel: "Visual guide candidate",
  },
];

export const DRACULA_CTA_EVENTS = {
  homepagePrimary: "homepage_dracula_cta_click",
  bookView: "dracula_book_view",
  previewStart: "dracula_preview_start",
  startReading: "dracula_start_reading_click",
  readingPass: "dracula_reading_pass_click",
  readerStart: "dracula_reader_start",
  chapterOneComplete: "dracula_chapter_1_complete",
  notifyMe: "dracula_notify_me_click",
};

export function isLiveApprovedBook(book = {}) {
  return book?.slug === LIVE_APPROVED_SLUG;
}

export function bookLaunchStatus(book = {}) {
  if (isLiveApprovedBook(book)) return "LIVE_APPROVED";
  return "COMING_SOON_PIPELINE";
}

export function mergeDraculaBook(book) {
  if (!book || book.slug !== LIVE_APPROVED_SLUG) return DRACULA_FALLBACK_BOOK;
  return {
    ...DRACULA_FALLBACK_BOOK,
    ...book,
    chapters: Array.isArray(book.chapters) && book.chapters.length > 0
      ? book.chapters
      : DRACULA_FALLBACK_BOOK.chapters,
    audiobook_enabled: false,
    generate_audiobook: false,
    audiobook_assets: {},
  };
}

export function readingPassUrl(source = "dracula_launch") {
  return `/pricing?source=${source}&book=${LIVE_APPROVED_SLUG}`;
}

export function notifyUrl(slug = "dracula") {
  return `/contact?interest=${encodeURIComponent(slug)}`;
}
