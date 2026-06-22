export const LIVE_APPROVED_SLUG = "dracula";
export const KSHUDHITA_PASHAN_SLUG = "kshudhita-pashan";

export const DRACULA_SOURCE_NOTE = "Project Gutenberg eBook #345";
export const DRACULA_RIGHTS_NOTE = "Approved Tier A core reading candidate";
export const DRACULA_CHAPTER_COUNT = 27;
export const DRACULA_COVER_IMAGE = "/assets/books/dracula/dracula-front-cover.webp";
export const DRACULA_BACK_COVER_IMAGE = "/assets/books/dracula/dracula-back-cover.webp";

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
  cover_image_url: DRACULA_COVER_IMAGE,
  thumbnail_url: DRACULA_COVER_IMAGE,
  back_cover_image_url: DRACULA_BACK_COVER_IMAGE,
  back_cover_thumbnail_url: DRACULA_BACK_COVER_IMAGE,
  dominant_color: "#4A1C27",
  back_cover_dominant_color: "#2A1721",
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
    slug: KSHUDHITA_PASHAN_SLUG,
    title: "ক্ষুধিত পাষাণ",
    title_en: "The Hungry Stones",
    author: "Rabindranath Tagore",
    category_slug: "bengali-gothic",
    statusLabel: "Tier A source-backed candidate with CC BY-SA attribution/share-alike compliance required",
    pipeline_stage: "PIPELINE_ONLY",
    rights_tier: "A",
    verification_status: "candidate_review",
    audio_preview_status: "AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA",
    audiobook_enabled: false,
  },
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

export const KSHUDHITA_PASHAN_PIPELINE = {
  slug: KSHUDHITA_PASHAN_SLUG,
  titleBn: "ক্ষুধিত পাষাণ",
  titleEn: "The Hungry Stones",
  author: "Rabindranath Tagore",
  headline: "Bengali Gothic Premiere: ক্ষুধিত পাষাণ",
  subcopy: "After Dracula, enter a haunted Bengali palace.",
  statusLabel: "Pipeline only: source, rights, CC BY-SA compliance, text QA, and audio provider QA are still gated.",
};

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

function normalizedSlug(book = {}) {
  return String(book?.slug || book?.id || "").trim().toLowerCase();
}

function normalizedRightsTier(book = {}) {
  return String(book?.rights_tier || book?.rights_metadata?.rights_tier || "").trim().toUpperCase();
}

function normalizedVerificationStatus(book = {}) {
  return String(book?.verification_status || book?.rights_metadata?.verification_status || "").trim().toLowerCase();
}

export function isLiveApprovedBook(book = {}) {
  const slug = normalizedSlug(book);
  if (slug !== LIVE_APPROVED_SLUG) return false;
  const tier = normalizedRightsTier(book);
  const status = normalizedVerificationStatus(book);
  if (tier && tier !== "A") return false;
  if (status && !["approved", "published_core_reading_only"].includes(status)) return false;
  return true;
}

export function isPipelineCandidate(book = {}) {
  const slug = normalizedSlug(book);
  if (!slug) return false;
  if (slug === LIVE_APPROVED_SLUG) return false;
  if (normalizedRightsTier(book) === "C") return false;
  return PIPELINE_BOOKS.some((candidate) => candidate.slug === slug)
    || String(book?.pipeline_stage || "").toUpperCase().includes("PIPELINE")
    || !isLiveApprovedBook(book);
}

export function canShowStartReading(book = {}) {
  return isLiveApprovedBook(book);
}

export function canShowPreview(book = {}) {
  return isLiveApprovedBook(book);
}

export function canShowAudioCTA(book = {}) {
  if (!isLiveApprovedBook(book)) return false;
  if (!book?.audiobook_enabled || book?.generate_audiobook) return false;
  const qaStatus = String(book?.audio_qa_status || book?.audiobook?.qa_status || "").trim().toUpperCase();
  return qaStatus === "QA_PASSED";
}

export function bookLaunchStatus(book = {}) {
  if (isLiveApprovedBook(book)) return "LIVE_APPROVED";
  if (normalizedRightsTier(book) === "C") return "QUARANTINED";
  if (normalizedRightsTier(book) === "B") return "REGION_GATED_PIPELINE";
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
