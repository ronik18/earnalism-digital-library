import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookHeart,
  BookOpen,
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Feather,
  Globe2,
  Headphones,
  MoonStar,
  Pause,
  Play,
  Sparkles,
} from "lucide-react";
import BookCoverImage from "./BookCoverImage";
import "./PremiumHero.css";

const PUBLIC_URL = process.env.PUBLIC_URL || "";
const REFERENCE_HERO_IMAGE = `${PUBLIC_URL}/assets/hero/premium-library-reference-exact-1440.webp`;
const REFERENCE_HERO_FULL_IMAGE = `${PUBLIC_URL}/assets/hero/premium-library-reference-exact.webp`;
const REFERENCE_HERO_SRCSET = [
  `${PUBLIC_URL}/assets/hero/premium-library-reference-exact-1024.webp 1024w`,
  `${REFERENCE_HERO_IMAGE} 1440w`,
  `${REFERENCE_HERO_FULL_IMAGE} 2180w`,
].join(", ");
const REFERENCE_HERO_AVIF_SRCSET = [
  `${PUBLIC_URL}/assets/hero/premium-library-reference-exact-1024.avif 1024w`,
  `${PUBLIC_URL}/assets/hero/premium-library-reference-exact-1440.avif 1440w`,
  `${PUBLIC_URL}/assets/hero/premium-library-reference-exact.avif 2180w`,
].join(", ");
const HERO_BOOKS_PER_FRAME = 4;
const HERO_CAROUSEL_INTERVAL_MS = 7000;

const DEFAULT_HEADLINE = "A premium reading and listening sanctuary for timeless Bengali and English classics.";
const DEFAULT_SUBHEADLINE = "Beautifully designed editions. Immersive audiobooks. Calm reading modes. A curated literary experience that stays with you.";

const FEATURE_CHIPS = [
  "Curated Classics",
  "Premium Reading Experience",
  "Immersive Audiobooks",
  "Beautiful Graphical Covers",
];

const PREMIUM_CARDS = [
  {
    title: "Curated Classics",
    description: "Handpicked Bengali & English classics you’ll love forever.",
    Icon: BookOpen,
  },
  {
    title: "Immersive Audiobooks",
    description: "Studio-quality narration for deeper connection.",
    Icon: Headphones,
  },
  {
    title: "Beautiful Editions",
    description: "Thoughtful design. Elegant covers. Collector’s delight.",
    Icon: Feather,
  },
  {
    title: "Calm Reading Modes",
    description: "Distraction-free reading for perfect focus.",
    Icon: MoonStar,
  },
];

const FEATURE_RAIL = [
  { title: "Curated Bengali & English Classics", Icon: BookHeart },
  { title: "Immersive Audiobook Rooms", Icon: Headphones },
  { title: "Beautiful Graphical Editions", Icon: BookOpen },
  { title: "Calm Reader Modes", Icon: MoonStar },
  { title: "Your Library, Everywhere", Icon: Bookmark },
];

function track(onTrack, event, metadata) {
  if (typeof onTrack === "function") onTrack(event, metadata);
}

function useDesktopReference() {
  const [isDesktop, setIsDesktop] = useState(() => (
    typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(min-width: 1024px)").matches
  ));

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const media = window.matchMedia("(min-width: 1024px)");
    const syncViewport = (event) => setIsDesktop(event.matches);
    setIsDesktop(media.matches);
    media.addEventListener("change", syncViewport);
    return () => media.removeEventListener("change", syncViewport);
  }, []);

  return isDesktop;
}

function useReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(() => (
    typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  ));

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncPreference = (event) => setReducedMotion(event.matches);
    setReducedMotion(media.matches);
    media.addEventListener("change", syncPreference);
    return () => media.removeEventListener("change", syncPreference);
  }, []);

  return reducedMotion;
}

function heroCarouselBooks(curation = {}) {
  const hero = curation.hero || {};
  const suppliedCarousel = Array.isArray(hero.carousel_books) ? hero.carousel_books : [];
  const featured = Array.isArray(hero.featured_books) ? hero.featured_books : [];
  const groups = Array.isArray(curation.literary_shelves)
    ? curation.literary_shelves
    : Array.isArray(curation.groups)
      ? curation.groups
      : Array.isArray(curation.shelf_collage?.groups)
        ? curation.shelf_collage.groups
        : Array.isArray(curation.shelves)
          ? curation.shelves
          : [];
  const shelfBooks = groups.flatMap((group) => (
    group.visible_books || group.books || []
  ));
  const candidates = suppliedCarousel.length > 0
    ? suppliedCarousel
    : [...featured, ...shelfBooks];

  return Array.from(new Map(
    candidates
      .filter((book) => (
        book?.slug
        && book.reader_enabled !== false
        && book.cover_valid !== false
        && book.front_cover_url
      ))
      .map((book) => [book.slug, book]),
  ).values());
}

function useHeroBookCarousel(books) {
  const reducedMotion = useReducedMotion();
  const [pageIndex, setPageIndex] = useState(0);
  const [manualPaused, setManualPaused] = useState(false);
  const [interactionPaused, setInteractionPaused] = useState(false);
  const [documentVisible, setDocumentVisible] = useState(() => (
    typeof document === "undefined" || document.visibilityState !== "hidden"
  ));
  const [announcement, setAnnouncement] = useState("");
  const pageCount = Math.max(1, Math.ceil(books.length / HERO_BOOKS_PER_FRAME));
  const bookSignature = books.map((book) => book.slug).join("|");

  useEffect(() => {
    setPageIndex(0);
  }, [bookSignature]);

  useEffect(() => {
    const syncVisibility = () => setDocumentVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", syncVisibility);
    return () => document.removeEventListener("visibilitychange", syncVisibility);
  }, []);

  const moveToPage = useCallback((nextIndex) => {
    setPageIndex((currentIndex) => {
      const resolved = ((typeof nextIndex === "function" ? nextIndex(currentIndex) : nextIndex) + pageCount) % pageCount;
      return resolved;
    });
  }, [pageCount]);

  useEffect(() => {
    if (
      pageCount <= 1
      || reducedMotion
      || manualPaused
      || interactionPaused
      || !documentVisible
    ) return undefined;
    const rotation = window.setInterval(() => {
      moveToPage((currentIndex) => currentIndex + 1);
    }, HERO_CAROUSEL_INTERVAL_MS);
    return () => window.clearInterval(rotation);
  }, [
    documentVisible,
    interactionPaused,
    manualPaused,
    moveToPage,
    pageCount,
    reducedMotion,
  ]);

  const visibleBooks = useMemo(() => {
    if (books.length <= HERO_BOOKS_PER_FRAME) return books;
    const start = pageIndex * HERO_BOOKS_PER_FRAME;
    return Array.from(
      { length: HERO_BOOKS_PER_FRAME },
      (_, offset) => books[(start + offset) % books.length],
    );
  }, [books, pageIndex]);

  const previous = useCallback(() => {
    const previousIndex = (pageIndex - 1 + pageCount) % pageCount;
    setPageIndex(previousIndex);
    setAnnouncement(`Showing featured books ${previousIndex + 1} of ${pageCount}.`);
  }, [pageCount, pageIndex]);
  const next = useCallback(() => {
    const nextIndex = (pageIndex + 1) % pageCount;
    setPageIndex(nextIndex);
    setAnnouncement(`Showing featured books ${nextIndex + 1} of ${pageCount}.`);
  }, [pageCount, pageIndex]);
  const togglePaused = useCallback(() => {
    setManualPaused(!manualPaused);
    setAnnouncement(manualPaused ? "Featured books carousel resumed." : "Featured books carousel paused.");
  }, [manualPaused]);

  return {
    announcement,
    canAutoRotate: !reducedMotion,
    manualPaused,
    next,
    pageCount,
    pageIndex,
    previous,
    setInteractionPaused,
    togglePaused,
    visibleBooks,
  };
}

function CatalogCoverLink({
  book,
  className,
  destination = "book_url",
  sizes,
  widths,
  eager = false,
  testId,
  carouselLabel,
  onPermanentFailure,
}) {
  const [coverFailed, setCoverFailed] = useState(false);

  if (!book) {
    return <span className={`${className} premium-hero-cover-mask`} aria-hidden="true" />;
  }
  if (coverFailed) {
    return <span className={`${className} premium-hero-cover-mask`} aria-hidden="true" />;
  }

  const href = book[destination] || book.book_url;
  return (
    <Link
      to={href}
      className={className}
      aria-label={carouselLabel || `Open ${book.title} by ${book.author}`}
      aria-roledescription={carouselLabel ? "slide" : undefined}
      data-testid={testId || `hero-book-${book.slug}`}
      data-book-slug={book.slug}
      data-canonical-cover-url={book.front_cover_url}
    >
      <BookCoverImage
        book={book}
        sizes={sizes}
        alt={book.cover_alt_text}
        width={240}
        height={360}
        widths={widths}
        loading={eager ? "eager" : "lazy"}
        fetchPriority={eager ? "high" : undefined}
        allowGraphicalFallback={false}
        onPermanentFailure={() => {
          setCoverFailed(true);
          onPermanentFailure?.(book.slug);
        }}
      />
    </Link>
  );
}

function ReaderScreenPreview() {
  return (
    <Link
      to="/reader/dracula"
      className="premium-reference-tablet"
      aria-label="Open the Dracula reader"
      data-testid="hero-reader-preview-dracula"
      data-reader-preview-book="dracula"
    >
      <span className="premium-reference-tablet__screen">
        <span className="premium-reader-screen-preview">
          <span className="premium-reader-screen-preview__topbar">
            <span>Dracula</span>
            <span>Reader</span>
          </span>
          <span className="premium-reader-screen-preview__chapter">
            <span>Chapter I</span>
            <span>01 / 27</span>
          </span>
          <span className="premium-reader-screen-preview__title">Jonathan Harker&apos;s Journal</span>
          <span className="premium-reader-screen-preview__body">
            <span>3 May. Bistritz. Left Munich at 8:35 P.M. on 1st May, arriving in Vienna early next morning.</span>
            <span>The journey had been beautiful, and the quiet rhythm of the road made the pages feel close at hand.</span>
          </span>
          <span className="premium-reader-screen-preview__progress" aria-hidden="true"><i /></span>
        </span>
      </span>
    </Link>
  );
}

function ListeningPhone({ listeningBook }) {
  const [coverFailed, setCoverFailed] = useState(false);

  if (!listeningBook) {
    return (
      <div className="premium-reference-listening premium-reference-listening--generic" data-testid="hero-listening-visual">
        <Headphones aria-hidden="true" />
        <strong>Premium Listening Rooms</strong>
      </div>
    );
  }
  if (coverFailed) {
    return (
      <div className="premium-reference-listening premium-reference-listening--generic" data-testid="hero-listening-visual">
        <Headphones aria-hidden="true" />
        <strong>Premium Listening Rooms</strong>
      </div>
    );
  }

  return (
    <Link
      to={listeningBook.cta_url}
      className="premium-reference-listening"
      aria-label={`Listen to ${listeningBook.title} by ${listeningBook.author}`}
      data-testid="hero-listening-visual"
      data-book-slug={listeningBook.slug}
    >
      <span className="premium-reference-listening__eyebrow">Now listening</span>
      <BookCoverImage
        book={listeningBook}
        sizes="6vw"
        alt={listeningBook.cover_alt_text}
        width={120}
        height={180}
        widths={[120, 240]}
        loading="eager"
        allowGraphicalFallback={false}
        onPermanentFailure={() => setCoverFailed(true)}
      />
      <strong>{listeningBook.title}</strong>
      <small>{listeningBook.author}</small>
      <span className="premium-reference-listening__wave" aria-hidden="true" />
    </Link>
  );
}

function ReferenceDeviceGroup({ listeningBook }) {
  return (
    <div className="premium-reference-device-group" aria-label="Reader and audiobook device preview">
      <ListeningPhone listeningBook={listeningBook} />
      <ReaderScreenPreview />
    </div>
  );
}

function ReferenceCatalogStage({
  featuredBooks,
  approvedAudiobooks,
  onCoverFailure,
  pageIndex,
  pageCount,
}) {
  const featuredSlugs = new Set(featuredBooks.map((book) => book.slug));
  const primaryShelfSlug = featuredBooks[0]?.slug;
  const listeningBook = approvedAudiobooks.find((book) => (
    book.slug !== primaryShelfSlug && featuredSlugs.has(book.slug)
  ))
    || approvedAudiobooks.find((book) => book.slug !== primaryShelfSlug)
    || approvedAudiobooks[0]
    || null;

  return (
    <div
      className="premium-reference-catalog premium-reference-catalog--exact"
      aria-label="Featured library books"
      aria-roledescription="carousel"
      data-carousel-page={pageIndex + 1}
      data-carousel-pages={pageCount}
    >
      <ReferenceDeviceGroup listeningBook={listeningBook} />
      <div className="premium-reference-catalog-books">
        {[0, 1, 2, 3].map((index) => (
          <CatalogCoverLink
            key={`${pageIndex}-${featuredBooks[index]?.slug || `empty-${index}`}`}
            book={featuredBooks[index]}
            className={`premium-reference-slot premium-reference-slot--desk-${index + 1}`}
            sizes="9vw"
            widths={[160, 320]}
            eager={pageIndex === 0 && index === 0}
            carouselLabel={featuredBooks[index]
              ? `Open ${featuredBooks[index].title} by ${featuredBooks[index].author}, book ${index + 1} of ${featuredBooks.length}`
              : undefined}
            onPermanentFailure={onCoverFailure}
          />
        ))}
      </div>
    </div>
  );
}

function CoverStack({
  books,
  loading,
  onCoverFailure,
  pageIndex,
  pageCount,
}) {
  if (loading && books.length === 0) {
    return (
      <div className="premium-mobile-covers premium-mobile-covers--loading" aria-hidden="true">
        {Array.from({ length: 4 }).map((_, index) => <span key={index} />)}
      </div>
    );
  }

  return (
    <div
      className="premium-mobile-covers"
      aria-label="Featured library books"
      aria-roledescription="carousel"
      data-carousel-page={pageIndex + 1}
      data-carousel-pages={pageCount}
    >
      {books.map((book, index) => (
        <CatalogCoverLink
          key={`${pageIndex}-${book.slug}`}
          book={book}
          className="premium-mobile-cover"
          sizes="(max-width: 520px) calc((100vw - 3.45rem) / 4), 145px"
          widths={[180, 360]}
          eager={index === 0}
          onPermanentFailure={onCoverFailure}
        />
      ))}
    </div>
  );
}

function HeroCarouselControls({
  canAutoRotate,
  manualPaused,
  next,
  pageCount,
  pageIndex,
  previous,
  togglePaused,
}) {
  if (pageCount <= 1) return null;
  return (
    <div className="premium-hero-carousel-controls" role="group" aria-label="Featured books carousel controls">
      <button type="button" onClick={previous} aria-label="Show previous four books">
        <ChevronLeft size={17} strokeWidth={1.8} aria-hidden="true" />
      </button>
      {canAutoRotate ? (
        <button
          type="button"
          onClick={togglePaused}
          aria-label={manualPaused ? "Resume featured books carousel" : "Pause featured books carousel"}
          aria-pressed={manualPaused}
        >
          {manualPaused
            ? <Play size={14} strokeWidth={1.8} aria-hidden="true" />
            : <Pause size={14} strokeWidth={1.8} aria-hidden="true" />}
        </button>
      ) : null}
      <span aria-hidden="true">{pageIndex + 1} / {pageCount}</span>
      <button type="button" onClick={next} aria-label="Show next four books">
        <ChevronRight size={17} strokeWidth={1.8} aria-hidden="true" />
      </button>
    </div>
  );
}

export default function PremiumHero({
  curation,
  loading = false,
  error = false,
  onTrack,
  headerMode = "overlay",
  analyticsNamespace = "home",
  fallbackHeadline = DEFAULT_HEADLINE,
}) {
  const isDesktopReference = useDesktopReference();
  const [referenceArtFailed, setReferenceArtFailed] = useState(false);
  const [failedCoverSlugs, setFailedCoverSlugs] = useState(() => new Set());
  const hero = curation?.hero || {};
  const carouselBooks = useMemo(
    () => heroCarouselBooks(curation).filter((book) => !failedCoverSlugs.has(book.slug)),
    [curation, failedCoverSlugs],
  );
  const carousel = useHeroBookCarousel(carouselBooks);
  const recordCoverFailure = useCallback((slug) => {
    setFailedCoverSlugs((current) => {
      if (current.has(slug)) return current;
      return new Set([...current, slug]);
    });
  }, []);
  const approvedAudiobooks = Array.isArray(curation?.listening_rooms?.items)
    ? curation.listening_rooms.items
    : Array.isArray(curation?.selected_audiobooks)
      ? curation.selected_audiobooks
      : Array.isArray(curation?.audiobook_shelf?.books)
        ? curation.audiobook_shelf.books
        : [];
  const primaryCta = hero.primary_cta?.url ? hero.primary_cta : { label: "Start Reading", url: "/library" };
  const secondaryCta = hero.secondary_cta?.url
    ? hero.secondary_cta
    : { label: "Explore Audiobooks", url: "/library?availability=approved-audiobook" };
  const headline = hero.headline || fallbackHeadline;
  const subheadline = hero.subheadline || DEFAULT_SUBHEADLINE;
  const goldHeadline = "timeless Bengali and English classics.";
  const headlineLead = headline.includes(goldHeadline)
    ? headline.replace(goldHeadline, "").trim()
    : headline;

  return (
    <section
      className={`premium-landing-hero premium-dynamic-hero premium-reference-hero premium-reference-hero--exact${headerMode === "in-flow" ? " premium-reference-hero--in-flow" : ""}${referenceArtFailed ? " premium-reference-hero--art-failed" : ""}`}
      data-testid="premium-landing-hero"
      data-catalog-state={loading ? "loading" : error ? "unavailable" : "ready"}
      aria-label={headline}
      aria-busy={loading}
    >
      {isDesktopReference ? (
        <picture>
          <source type="image/avif" srcSet={REFERENCE_HERO_AVIF_SRCSET} sizes="100vw" />
          <source type="image/webp" srcSet={REFERENCE_HERO_SRCSET} sizes="100vw" />
          <img
            className="premium-reference-hero__art"
            src={REFERENCE_HERO_IMAGE}
            alt=""
            aria-hidden="true"
            width="2180"
            height="1032"
            loading="eager"
            fetchPriority="high"
            decoding="async"
            onError={() => setReferenceArtFailed(true)}
          />
        </picture>
      ) : null}
      <div className="premium-hero-copy">
        <div className="premium-hero-eyebrow">
          <Sparkles size={15} strokeWidth={1.6} aria-hidden="true" />
          <span>Curated Digital Library</span>
        </div>
        <h1 id="premium-hero-title" data-testid="hero-headline">
          {headlineLead}{" "}
          {headline.includes(goldHeadline) ? <span>{goldHeadline}</span> : null}
        </h1>
        <p>{subheadline}</p>
        <p className="sr-only">Reading time is used only while you read. Chapter 1 remains free to preview.</p>
      </div>

      <div className="premium-hero-actions" data-testid="hero-ctas">
        <Link
          to={primaryCta.url}
          className="premium-hero-action premium-hero-action--primary"
          data-testid="hero-cta-library"
          onClick={() => track(onTrack, "hero_primary_cta_click", { cta: `${analyticsNamespace}_hero_start_reading` })}
        >
          <BookOpen size={19} strokeWidth={1.55} aria-hidden="true" />
          <span>{primaryCta.label || "Start Reading"}</span>
          <ArrowRight size={17} strokeWidth={1.6} aria-hidden="true" />
        </Link>
        <Link
          to={secondaryCta.url}
          className="premium-hero-action premium-hero-action--secondary"
          data-testid="hero-cta-audiobooks"
          onClick={() => track(onTrack, "hero_secondary_cta_click", { cta: `${analyticsNamespace}_hero_approved_audiobooks` })}
        >
          <Headphones size={18} strokeWidth={1.55} aria-hidden="true" />
          <span>{secondaryCta.label || "Explore Audiobooks"}</span>
          <ArrowRight size={16} strokeWidth={1.6} aria-hidden="true" />
        </Link>
      </div>

      <div className="premium-hero-chips" aria-label="Earnalism experience highlights">
        {FEATURE_CHIPS.map((chip) => (
          <span key={chip}><Globe2 size={12} strokeWidth={1.5} aria-hidden="true" />{chip}</span>
        ))}
      </div>

      <div
        className="premium-hero-catalog-shell"
        data-testid="hero-catalog-visuals"
        onMouseEnter={() => carousel.setInteractionPaused(true)}
        onMouseLeave={() => carousel.setInteractionPaused(false)}
        onFocusCapture={() => carousel.setInteractionPaused(true)}
        onBlurCapture={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) carousel.setInteractionPaused(false);
        }}
      >
        {isDesktopReference ? (
          <ReferenceCatalogStage
            featuredBooks={carousel.visibleBooks}
            approvedAudiobooks={approvedAudiobooks}
            onCoverFailure={recordCoverFailure}
            pageIndex={carousel.pageIndex}
            pageCount={carousel.pageCount}
          />
        ) : (
          <CoverStack
            books={carousel.visibleBooks}
            loading={loading}
            onCoverFailure={recordCoverFailure}
            pageIndex={carousel.pageIndex}
            pageCount={carousel.pageCount}
          />
        )}
        <HeroCarouselControls
          canAutoRotate={carousel.canAutoRotate}
          manualPaused={carousel.manualPaused}
          next={carousel.next}
          pageCount={carousel.pageCount}
          pageIndex={carousel.pageIndex}
          previous={carousel.previous}
          togglePaused={carousel.togglePaused}
        />
      </div>

      <aside className="premium-hero-cards" aria-label="Premium library features" data-testid="premium-hero-feature-cards">
        {PREMIUM_CARDS.map(({ title, description, Icon }) => (
          <article key={title}>
            <Icon size={23} strokeWidth={1.35} aria-hidden="true" />
            <div>
              <h2>{title}</h2>
              <p>{description}</p>
            </div>
          </article>
        ))}
      </aside>

      <div className="premium-hero-rail" aria-label="Earnalism library benefits">
        {FEATURE_RAIL.map(({ title, Icon }) => (
          <div key={title}>
            <Icon size={25} strokeWidth={1.3} aria-hidden="true" />
            <span>{title}</span>
          </div>
        ))}
      </div>

      <span className="sr-only" aria-live="polite">
        {loading ? "Loading featured classics." : `${carouselBooks.length} featured classics loaded.`}
        {error ? " The live catalog is temporarily unavailable." : ""}
        {carousel.announcement ? ` ${carousel.announcement}` : ""}
      </span>
    </section>
  );
}

export {
  DEFAULT_HEADLINE,
  HERO_BOOKS_PER_FRAME,
  HERO_CAROUSEL_INTERVAL_MS,
  REFERENCE_HERO_AVIF_SRCSET,
  REFERENCE_HERO_FULL_IMAGE,
  REFERENCE_HERO_IMAGE,
  REFERENCE_HERO_SRCSET,
  heroCarouselBooks,
};
