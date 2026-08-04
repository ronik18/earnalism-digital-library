import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookHeart,
  BookOpen,
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Globe2,
  Headphones,
  MoonStar,
  Pause,
  Play,
  Sparkles,
  WalletCards,
} from "lucide-react";
import BookCoverImage from "./BookCoverImage";
import { bookCoverImageSources } from "../lib/images";
import {
  activeHeroSlide,
  canRotateCarousel,
  carouselSlideState,
  heroCarouselBooks,
  relativeCarouselPosition,
  stepCarouselIndex,
  wrapCarouselIndex,
} from "../lib/heroCarousel";
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
const HERO_CAROUSEL_INTERVAL_MS = 7000;

const DEFAULT_HEADLINE = "A premium reading and listening sanctuary for timeless Bengali and English classics.";
const DEFAULT_SUBHEADLINE = "Beautifully designed editions. Immersive audiobooks. Calm reading modes. A curated literary experience that stays with you.";

const FEATURE_CHIPS = [
  "Curated Classics",
  "Premium Reading Experience",
  "Immersive Audiobooks",
  "Beautiful Graphical Covers",
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

function useNarrowViewport() {
  const [isNarrow, setIsNarrow] = useState(() => (
    typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(max-width: 767px)").matches
  ));

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const media = window.matchMedia("(max-width: 767px)");
    const syncViewport = (event) => setIsNarrow(event.matches);
    setIsNarrow(media.matches);
    media.addEventListener("change", syncViewport);
    return () => media.removeEventListener("change", syncViewport);
  }, []);

  return isNarrow;
}

function preloadHeroBook(book) {
  if (typeof window === "undefined" || typeof window.Image !== "function") {
    return Promise.resolve(true);
  }

  return new Promise((resolve) => {
    const sources = bookCoverImageSources(book, {
      width: 360,
      widths: [240, 360, 480],
      quality: 82,
    });
    if (!sources.src) {
      resolve(false);
      return;
    }

    const image = new window.Image();
    let settled = false;
    let timeoutId;
    image.decoding = "async";
    image.sizes = "(min-width: 1280px) 230px, (min-width: 768px) 200px, 176px";
    if (sources.srcSet) image.srcset = sources.srcSet;
    const settle = async () => {
      if (settled) return;
      settled = true;
      try {
        if (typeof image.decode === "function") await image.decode();
      } catch {
        // A completed image can still reject decode in memory-constrained
        // browsers. The live BookCoverImage retains its own fail-closed path.
      }
      window.clearTimeout(timeoutId);
      resolve(image.complete && image.naturalWidth > 0);
    };
    const fail = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeoutId);
      resolve(false);
    };
    image.onload = settle;
    image.onerror = fail;
    timeoutId = window.setTimeout(fail, 3500);
    image.src = sources.src;
    if (image.complete && image.naturalWidth > 0) settle();
  });
}

function useHeroBookCarousel(books) {
  const reducedMotion = useReducedMotion();
  const narrowViewport = useNarrowViewport();
  const transitionRequest = useRef(0);
  const activeIndexRef = useRef(0);
  const desiredIndex = useRef(0);
  const [activeIndex, setActiveIndex] = useState(0);
  const [manualPaused, setManualPaused] = useState(false);
  const [interactionPaused, setInteractionPaused] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [documentVisible, setDocumentVisible] = useState(() => (
    typeof document === "undefined" || document.visibilityState !== "hidden"
  ));
  const [initialCoverReady, setInitialCoverReady] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const itemCount = books.length;

  useEffect(() => {
    transitionRequest.current += 1;
    setActiveIndex((currentIndex) => {
      const nextIndex = wrapCarouselIndex(currentIndex, itemCount);
      activeIndexRef.current = nextIndex;
      desiredIndex.current = nextIndex;
      return nextIndex;
    });
  }, [itemCount]);

  useEffect(() => {
    const syncVisibility = () => setDocumentVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", syncVisibility);
    return () => document.removeEventListener("visibilitychange", syncVisibility);
  }, []);

  useEffect(() => {
    let active = true;
    setInitialCoverReady(false);
    if (!books.length) return undefined;
    void preloadHeroBook(books[activeIndex] || books[0]).then((ready) => {
      if (active) setInitialCoverReady(ready);
    });
    return () => {
      active = false;
    };
  }, [activeIndex, books]);

  useEffect(() => {
    if (!books.length) return;
    const previousIndex = wrapCarouselIndex(activeIndex - 1, itemCount);
    const nextIndex = wrapCarouselIndex(activeIndex + 1, itemCount);
    void preloadHeroBook(books[previousIndex]);
    if (nextIndex !== previousIndex) void preloadHeroBook(books[nextIndex]);
  }, [activeIndex, books, itemCount]);

  const moveToIndex = useCallback(async (nextIndex, announce = true) => {
    if (!itemCount) return null;
    const resolved = wrapCarouselIndex(nextIndex, itemCount);
    desiredIndex.current = resolved;
    const request = transitionRequest.current + 1;
    transitionRequest.current = request;
    const ready = await preloadHeroBook(books[resolved]);
    if (request !== transitionRequest.current) return null;
    if (!ready) {
      desiredIndex.current = activeIndexRef.current;
      return null;
    }
    activeIndexRef.current = resolved;
    setActiveIndex(resolved);
    if (announce) {
      const book = books[resolved];
      setAnnouncement(`${book.title} by ${book.author}, slide ${resolved + 1} of ${itemCount}.`);
    }
    return resolved;
  }, [books, itemCount]);

  const rotationAllowed = canRotateCarousel({
    itemCount,
    reducedMotion,
    narrowViewport,
    manualPaused,
    interactionPaused,
    dragging,
    documentVisible,
    initialCoverReady,
  });

  useEffect(() => {
    if (!rotationAllowed) return undefined;
    const rotation = window.setInterval(() => {
      void moveToIndex(stepCarouselIndex(desiredIndex.current, 1, itemCount), false);
    }, HERO_CAROUSEL_INTERVAL_MS);
    return () => window.clearInterval(rotation);
  }, [itemCount, moveToIndex, rotationAllowed]);

  const previous = useCallback(async () => {
    await moveToIndex(stepCarouselIndex(desiredIndex.current, -1, itemCount));
  }, [itemCount, moveToIndex]);
  const next = useCallback(async () => {
    await moveToIndex(stepCarouselIndex(desiredIndex.current, 1, itemCount));
  }, [itemCount, moveToIndex]);
  const select = useCallback(async (index) => {
    await moveToIndex(index);
  }, [moveToIndex]);
  const togglePaused = useCallback(() => {
    setManualPaused((paused) => {
      setAnnouncement(paused ? "Featured classics slide rotation started." : "Featured classics slide rotation stopped.");
      return !paused;
    });
  }, []);
  const stopForKeyboardFocus = useCallback(() => {
    setManualPaused(true);
    setInteractionPaused(true);
  }, []);

  return {
    activeSlide: activeHeroSlide(books, activeIndex),
    activeIndex,
    announcement,
    canAutoRotate: itemCount > 1 && !reducedMotion && !narrowViewport,
    dragging,
    isAutoRotating: rotationAllowed,
    itemCount,
    manualPaused,
    next,
    previous,
    select,
    setDragging,
    setInteractionPaused,
    stopForKeyboardFocus,
    togglePaused,
  };
}

function BookJacket({
  book,
  sizes,
  widths,
  eager = false,
  highPriority = false,
  onPermanentFailure,
}) {
  const [coverFailed, setCoverFailed] = useState(false);

  if (!book || coverFailed) return <span className="premium-book-jacket premium-hero-cover-mask" aria-hidden="true" />;
  return (
    <span className="premium-book-jacket" data-canonical-cover-url={book.coverSrc}>
      <span className="premium-book-jacket__spine" aria-hidden="true" />
      <span className="premium-book-jacket__front">
        <BookCoverImage
          book={book}
          sizes={sizes}
          alt={book.coverAlt}
          width={240}
          height={360}
          widths={widths}
          loading={eager ? "eager" : "lazy"}
          fetchPriority={highPriority ? "high" : undefined}
          allowGraphicalFallback={false}
          onPermanentFailure={() => {
            setCoverFailed(true);
            onPermanentFailure?.(book.slug);
          }}
        />
      </span>
      <span className="premium-book-jacket__right-pages" aria-hidden="true" />
      <span className="premium-book-jacket__bottom-pages" aria-hidden="true" />
    </span>
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
  books,
  carousel,
  approvedAudiobooks,
  onCoverFailure,
}) {
  const featuredSlugs = new Set(books.map((book) => book.slug));
  const primaryShelfSlug = carousel.activeSlide?.slug;
  const listeningBook = approvedAudiobooks.find((book) => (
    book.slug !== primaryShelfSlug && featuredSlugs.has(book.slug)
  ))
    || approvedAudiobooks.find((book) => book.slug !== primaryShelfSlug)
    || approvedAudiobooks[0]
    || null;

  return (
    <div
      className="premium-reference-catalog premium-reference-catalog--exact"
    >
      <ReferenceDeviceGroup listeningBook={listeningBook} />
      <div className="premium-reference-catalog-books">
        <EditorialCoverflow
          books={books}
          carousel={carousel}
          onCoverFailure={onCoverFailure}
          variant="reference"
        />
      </div>
    </div>
  );
}

function EditorialCoverflow({
  books,
  carousel,
  loading,
  onCoverFailure,
  variant = "flow",
}) {
  const pointerState = useRef(null);
  const pointerFocusIntent = useRef(false);
  const activeSlide = activeHeroSlide(books, carousel.activeIndex);

  if (loading && books.length === 0) {
    return (
      <div className="premium-coverflow premium-coverflow--loading" aria-hidden="true">
        <span />
      </div>
    );
  }

  const onKeyDown = (event) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      void carousel.previous();
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      void carousel.next();
    }
  };
  const onPointerDown = (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    pointerState.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      dragging: false,
    };
  };
  const onPointerMove = (event) => {
    const start = pointerState.current;
    if (!start || start.pointerId !== event.pointerId || start.dragging) return;
    if (Math.hypot(event.clientX - start.x, event.clientY - start.y) < 8) return;
    start.dragging = true;
    carousel.setDragging(true);
  };
  const finishPointer = (event, cancelled = false) => {
    const start = pointerState.current;
    pointerState.current = null;
    if (start?.dragging) carousel.setDragging(false);
    if (!start || cancelled || start.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - start.x;
    const deltaY = event.clientY - start.y;
    if (Math.abs(deltaX) < 42 || Math.abs(deltaX) <= Math.abs(deltaY)) return;
    if (deltaX > 0) void carousel.previous();
    else void carousel.next();
  };

  return (
    <div
      className={`premium-coverflow premium-coverflow--${variant}`}
      role="region"
      aria-roledescription="carousel"
      aria-label="Featured classics"
      data-carousel-index={carousel.activeIndex}
      data-carousel-count={carousel.itemCount}
      data-active-slide-id={activeSlide?.id || ""}
      data-autoplay-running={carousel.isAutoRotating ? "true" : "false"}
      onKeyDown={onKeyDown}
      onPointerDownCapture={() => {
        pointerFocusIntent.current = true;
      }}
      onPointerUpCapture={() => {
        pointerFocusIntent.current = false;
      }}
      onPointerCancelCapture={() => {
        pointerFocusIntent.current = false;
      }}
      onMouseEnter={() => carousel.setInteractionPaused(true)}
      onMouseLeave={() => carousel.setInteractionPaused(false)}
      onFocusCapture={() => {
        if (!pointerFocusIntent.current) carousel.stopForKeyboardFocus();
      }}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) carousel.setInteractionPaused(false);
      }}
    >
      {activeSlide ? (
        <aside
          className="premium-coverflow__plaque"
          aria-label={`Featured classic: ${activeSlide.title} by ${activeSlide.author}`}
          data-slide-id={activeSlide.id}
        >
          <div className="premium-coverflow__metadata" key={activeSlide.id}>
            <span>Featured classic</span>
            <strong>{activeSlide.title}</strong>
            <small>{activeSlide.author}</small>
            <Link
              to={activeSlide.destination}
              data-slide-id={activeSlide.id}
              data-testid="hero-active-book-link"
            >
              Open classic <ArrowRight size={13} strokeWidth={1.7} aria-hidden="true" />
            </Link>
          </div>
          <div
            className={`premium-coverflow__controls${carousel.canAutoRotate ? "" : " premium-coverflow__controls--manual"}`}
            role="group"
            aria-label="Featured classics controls"
          >
            {carousel.canAutoRotate ? (
              <button
                type="button"
                className="premium-coverflow__rotation"
                onClick={carousel.togglePaused}
                aria-label={carousel.manualPaused ? "Start slide rotation" : "Stop slide rotation"}
                aria-pressed={carousel.manualPaused}
              >
                {carousel.manualPaused
                  ? <Play size={16} strokeWidth={1.8} aria-hidden="true" />
                  : <Pause size={16} strokeWidth={1.8} aria-hidden="true" />}
              </button>
            ) : null}
            <div className="premium-coverflow__navigation">
              <button type="button" onClick={carousel.previous} aria-label="Previous book">
                <ChevronLeft size={19} strokeWidth={1.8} aria-hidden="true" />
              </button>
              <span className="premium-coverflow__counter" aria-hidden="true">
                {String(carousel.activeIndex + 1).padStart(2, "0")} / {String(carousel.itemCount).padStart(2, "0")}
              </span>
              <button type="button" onClick={carousel.next} aria-label="Next book">
                <ChevronRight size={19} strokeWidth={1.8} aria-hidden="true" />
              </button>
            </div>
            {carousel.canAutoRotate ? (
              <span className="premium-coverflow__progress" aria-hidden="true">
                <i key={activeSlide.id} />
              </span>
            ) : null}
          </div>
        </aside>
      ) : null}

      <div
        className="premium-coverflow__stage"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={(event) => finishPointer(event)}
        onPointerCancel={(event) => finishPointer(event, true)}
      >
        <span className="premium-coverflow__active-glow" aria-hidden="true" />
        {books.map((book, index) => {
          const slideState = carouselSlideState(index, carousel.activeIndex, books.length);
          const position = relativeCarouselPosition(index, carousel.activeIndex, books.length);
          const isActive = slideState === "active";
          const isAdjacent = slideState === "previous" || slideState === "next";
          const isHidden = !isActive && !isAdjacent;
          const slideLabel = `${index + 1} of ${books.length}: ${book.title} by ${book.author}`;
          const jacket = (
            <BookJacket
              book={book}
              sizes="(min-width: 1280px) 230px, (min-width: 768px) 200px, 176px"
              widths={[180, 240, 360, 480]}
              eager={index === 0 || isActive || isAdjacent}
              highPriority={index === 0 && carousel.activeIndex === 0}
              onPermanentFailure={onCoverFailure}
            />
          );
          return (
            <div
              key={book.id}
              className="premium-coverflow__slide"
              role="group"
              aria-roledescription="slide"
              aria-label={slideLabel}
              aria-hidden={isHidden}
              data-active={isActive ? "true" : "false"}
              data-slide-id={book.id}
              data-book-slug={book.slug}
              data-position={slideState}
              style={{ "--coverflow-distance": position }}
            >
              {isActive ? (
                <Link
                  to={book.destination}
                  className="premium-coverflow__book-action premium-coverflow__book-action--active"
                  aria-label={`Open ${book.title} by ${book.author}`}
                  data-active-cover-id={book.id}
                  data-testid={`hero-book-${book.slug}`}
                >
                  {jacket}
                </Link>
              ) : isAdjacent ? (
                <button
                  type="button"
                  className="premium-coverflow__book-action"
                  onClick={() => carousel.select(index)}
                  aria-label={`Select ${book.title} by ${book.author}`}
                  data-testid={`hero-book-${book.slug}`}
                >
                  {jacket}
                </button>
              ) : (
                <div className="premium-coverflow__book-action" tabIndex={-1}>
                  {jacket}
                </div>
              )}
            </div>
          );
        })}
      </div>
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
      >
        {isDesktopReference ? (
          <ReferenceCatalogStage
            books={carouselBooks}
            carousel={carousel}
            approvedAudiobooks={approvedAudiobooks}
            onCoverFailure={recordCoverFailure}
          />
        ) : (
          <EditorialCoverflow
            books={carouselBooks}
            carousel={carousel}
            loading={loading}
            onCoverFailure={recordCoverFailure}
          />
        )}
      </div>

      <aside className="premium-hero-offer" aria-label="Earnalism Reading Pass" data-testid="premium-hero-reading-pass">
        <div className="premium-hero-offer__eyebrow">
          <WalletCards size={19} strokeWidth={1.45} aria-hidden="true" />
          <span>Reading Pass</span>
        </div>
        <h2>Start free. Continue when the story earns it.</h2>
        <p>Chapter 1 is free. Add reading time only when you choose to continue.</p>
        <Link
          to="/pricing"
          className="premium-hero-offer__cta"
          data-testid="hero-pricing-cta"
          onClick={() => track(onTrack, "hero_pricing_cta_click", { cta: `${analyticsNamespace}_hero_reading_pass` })}
        >
          <span>View Reading Passes</span>
          <ArrowRight size={15} strokeWidth={1.7} aria-hidden="true" />
        </Link>
        <small>Reading time runs only while you read.</small>
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
  HERO_CAROUSEL_INTERVAL_MS,
  REFERENCE_HERO_AVIF_SRCSET,
  REFERENCE_HERO_FULL_IMAGE,
  REFERENCE_HERO_IMAGE,
  REFERENCE_HERO_SRCSET,
  carouselSlideState,
  heroCarouselBooks,
  relativeCarouselPosition,
  stepCarouselIndex,
  wrapCarouselIndex,
};
