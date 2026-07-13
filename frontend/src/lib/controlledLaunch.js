export const LIVE_APPROVED_SLUG = "dracula";
export const KSHUDHITA_PASHAN_SLUG = "kshudhita-pashan";
export const BATCH_1_READER_ONLY_SLUGS = [
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
export const PAID_ONLY_READER_SLUGS = [
  "book-d19e96859f",
  "book-f5d593e1f4",
];
export const LIVE_APPROVED_READER_SLUGS = [
  LIVE_APPROVED_SLUG,
  ...BATCH_1_READER_ONLY_SLUGS,
  ...PAID_ONLY_READER_SLUGS,
];

export const DRACULA_SOURCE_NOTE = "Project Gutenberg eBook #345";
export const DRACULA_RIGHTS_NOTE = "Approved classic reading release";
export const DRACULA_CHAPTER_COUNT = 27;
export const DRACULA_COVER_IMAGE = "/assets/books/dracula/dracula-front-cover.webp";
export const DRACULA_BACK_COVER_IMAGE = "/assets/books/dracula/dracula-back-cover.webp";
export const KSHUDHITA_PASHAN_FRONT_COVER_IMAGE = "/assets/books/kshudhita-pashan/kshudhita-pashan-front.webp";
export const KSHUDHITA_PASHAN_BACK_COVER_IMAGE = "/assets/books/kshudhita-pashan/kshudhita-pashan-back.webp";
export const SULTANAS_DREAM_FRONT_COVER_IMAGE = "/assets/books/sultanas-dream/front-cover.svg";

function smartTitleCaseSegment(value = "") {
  const text = String(value || "").trim();
  const letters = text.match(/[A-Za-z]/g) || [];
  const upperLetters = text.match(/[A-Z]/g) || [];
  if (!letters.length || upperLetters.length / letters.length < 0.72) return text;
  return text
    .toLowerCase()
    .replace(/\b([a-z])([a-z'’.]*)/g, (_match, first, rest) => `${first.toUpperCase()}${rest}`)
    .replace(/\bDr\b\.?/g, "Dr.")
    .replace(/\bMr\b\.?/g, "Mr.")
    .replace(/\bMrs\b\.?/g, "Mrs.")
    .replace(/\bMs\b\.?/g, "Ms.");
}

export function normalizeChapterDisplayTitle(title = "") {
  const original = String(title || "").trim();
  if (!original) return "";
  const withoutContinuation = original
    .replace(/[_*`]+/g, "")
    .replace(/\s*[.:]?\s*(?:--|—|-)\s*continued\.?\s*$/i, "")
    .replace(/\s+(?:continued)\.?\s*$/i, "")
    .replace(/\s+/g, " ")
    .trim();

  const chapterMatch = withoutContinuation.match(/^chapter\s+([ivxlcdm]+|\d+)\.?\s*(.*)$/i);
  if (!chapterMatch) return smartTitleCaseSegment(withoutContinuation);
  const [, numeral, remainder] = chapterMatch;
  const normalizedRemainder = smartTitleCaseSegment(remainder);
  return normalizedRemainder
    ? `Chapter ${String(numeral).toUpperCase()}. ${normalizedRemainder}`
    : `Chapter ${String(numeral).toUpperCase()}`;
}

export const DRACULA_FALLBACK_BOOK = {
  slug: LIVE_APPROVED_SLUG,
  title: "Dracula",
  subtitle: "A controlled Earnalism core reading release",
  author: "Bram Stoker",
  category_slug: "gothic-fiction",
  short_description:
    "Begin Bram Stoker's gothic classic in a quiet digital reading room. Chapter 1 is free; the full core reading experience continues with reading time.",
  description:
    "Dracula is an approved classic reading release with 27 chapters and a rights-safe source trail. Audio availability remains evidence-gated and hidden unless release approval is proven.",
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
  reader_enabled: true,
  preview_enabled: true,
  reader_url: `/reader/${LIVE_APPROVED_SLUG}`,
  preview_url: `/reader/${LIVE_APPROVED_SLUG}`,
  audiobook_enabled: false,
  generate_audiobook: false,
  audiobook_assets: {},
};

export const PIPELINE_BOOKS = [
  {
    slug: KSHUDHITA_PASHAN_SLUG,
    title: "ক্ষুধিত পাষাণ",
    displayTitle: "Kshudhita Pashan",
    titleNative: "ক্ষুধিত পাষাণ",
    title_en: "The Hungry Stones",
    author: "Rabindranath Tagore",
    category_slug: "bengali-gothic",
    statusLabel: "Rights-safe preparation",
    short_description:
      "A Bengali Gothic candidate in rights-safe preparation. It is not public reading inventory yet.",
    pipeline_stage: "PIPELINE_ONLY",
    rights_tier: "A",
    verification_status: "candidate_review",
    audio_preview_status: "AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA",
    audiobook_enabled: false,
    cover_status: "OWNER_PROVIDED_LOCAL_COVER_READY",
    cover_image_url: "/assets/books/kshudhita-pashan/front-cover.webp",
    thumbnail_url: "/assets/books/kshudhita-pashan/front-cover.webp",
    back_cover_image_url: KSHUDHITA_PASHAN_BACK_COVER_IMAGE,
    back_cover_thumbnail_url: KSHUDHITA_PASHAN_BACK_COVER_IMAGE,
    dominant_color: "#111820",
  },
  {
    slug: "frankenstein",
    title: "Frankenstein",
    author: "Mary Wollstonecraft Shelley",
    category_slug: "gothic-fiction",
    statusLabel: "Rights-safe preparation",
    short_description: "A future Gothic shelf candidate. Cover evidence remains pending, so this card stays in preparation.",
    pipeline_stage: "PIPELINE_ONLY",
    cover_status: "DESIGNED_PLACEHOLDER_READY",
    cover_image_url: "/assets/books/frankenstein/front-cover.webp",
    thumbnail_url: "/assets/books/frankenstein/front-cover.webp",
    dominant_color: "#111820",
  },
  {
    slug: "sherlock-holmes",
    title: "Sherlock Holmes",
    author: "Arthur Conan Doyle",
    category_slug: "classic-literature",
    statusLabel: "Rights-safe preparation",
    short_description: "A reasoning and classic-detective candidate awaiting rights-safe production evidence.",
    pipeline_stage: "PIPELINE_ONLY",
    cover_status: "DESIGNED_PLACEHOLDER_READY",
    cover_image_url: "/assets/books/sherlock-holmes/front-cover.webp",
    thumbnail_url: "/assets/books/sherlock-holmes/front-cover.webp",
    dominant_color: "#11140F",
  },
  {
    slug: "sultanas-dream",
    title: "Sultana's Dream",
    author: "Rokeya Sakhawat Hossain",
    category_slug: "science-fiction",
    statusLabel: "Rights-safe preparation",
    short_description: "A science-fiction classic candidate held until source, rights, and QA gates are complete.",
    pipeline_stage: "PIPELINE_ONLY",
    cover_status: "EDITORIAL_COVER_READY",
    cover_image_url: SULTANAS_DREAM_FRONT_COVER_IMAGE,
    thumbnail_url: SULTANAS_DREAM_FRONT_COVER_IMAGE,
    dominant_color: "#283E31",
  },
  {
    slug: "calculus-made-easy",
    title: "Calculus Made Easy",
    author: "Silvanus P. Thompson",
    category_slug: "study-material",
    statusLabel: "Visual guide candidate",
    short_description: "A study-material candidate for future guided reading, not a live paid reading product.",
    pipeline_stage: "PIPELINE_ONLY",
    cover_status: "DESIGNED_PLACEHOLDER_NO_SAFE_LOCAL_COVER",
  },
];

export const KSHUDHITA_PASHAN_PIPELINE = {
  slug: KSHUDHITA_PASHAN_SLUG,
  titleBn: "ক্ষুধিত পাষাণ",
  titleEn: "The Hungry Stones",
  author: "Rabindranath Tagore",
  headline: "Kshudhita Pashan",
  subcopy: "A Bengali Gothic classic moving through editorial preparation.",
  statusLabel: "Pipeline only: source, rights, CC BY-SA compliance, text QA, and audio provider QA are still gated.",
  frontCoverImage: KSHUDHITA_PASHAN_FRONT_COVER_IMAGE,
  backCoverImage: KSHUDHITA_PASHAN_BACK_COVER_IMAGE,
  coverStatus: "OWNER_PROVIDED_COVER_READY",
};

export const DRACULA_CTA_EVENTS = {
  homepagePrimary: "hero_read_chapter_free_click",
  bookView: "dracula_book_page_view",
  previewStart: "start_dracula_click",
  startReading: "start_dracula_click",
  readingPass: "pricing_page_view",
  readerStart: "reader_opened",
  chapterOneComplete: "continue_reading_click",
  notifyMe: "",
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
  if (!LIVE_APPROVED_READER_SLUGS.includes(slug)) return false;
  const tier = normalizedRightsTier(book);
  const status = normalizedVerificationStatus(book);
  if (tier && tier !== "A") return false;
  if (status && !["approved", "published_core_reading_only"].includes(status)) return false;
  if (slug !== LIVE_APPROVED_SLUG) {
    const publicationStatus = String(book?.publication_status || book?.launch_status || book?.publicationStatus || "").trim().toUpperCase();
    const readerEnabled = book?.reader_enabled === true || book?.allowPublicReading === true;
    const published = book?.is_published !== false && book?.isPublic !== false && book?.isLive !== false;
    const noCommerce = book?.allowCheckout !== true && book?.allowPayment !== true;
    const noAudio = book?.audio_enabled !== true && book?.audiobook_enabled !== true && book?.generate_audiobook !== true;
    return publicationStatus === "LIVE_APPROVED" && readerEnabled && published && noCommerce && noAudio;
  }
  return true;
}

export function isPipelineCandidate(book = {}) {
  const slug = normalizedSlug(book);
  if (!slug) return false;
  if (isLiveApprovedBook(book)) return false;
  if (normalizedRightsTier(book) === "C") return false;
  return PIPELINE_BOOKS.some((candidate) => candidate.slug === slug)
    || String(book?.pipeline_stage || "").toUpperCase().includes("PIPELINE")
    || !isLiveApprovedBook(book);
}

export function canShowStartReading(book = {}) {
  return isLiveApprovedBook(book);
}

export function canShowPreview(book = {}) {
  if (!isLiveApprovedBook(book)) return false;
  const hasExplicitPreview = Array.isArray(book?.chapters)
    && book.chapters.some((chapter) => chapter?.id && chapter?.is_preview === true);
  const previewUrl = String(book?.preview_url || "").trim();
  return hasExplicitPreview && book?.preview_enabled === true && Boolean(previewUrl);
}

export function canShowReadingPass(book = {}) {
  return normalizedSlug(book) === LIVE_APPROVED_SLUG && isLiveApprovedBook(book);
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
    cover_image_url: DRACULA_COVER_IMAGE,
    cover_url: DRACULA_COVER_IMAGE,
    thumbnail_url: DRACULA_COVER_IMAGE,
    back_cover_image_url: DRACULA_BACK_COVER_IMAGE,
    back_cover_url: DRACULA_BACK_COVER_IMAGE,
    back_cover_thumbnail_url: DRACULA_BACK_COVER_IMAGE,
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
