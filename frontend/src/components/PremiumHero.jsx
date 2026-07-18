import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookHeart,
  BookOpen,
  Bookmark,
  Feather,
  Globe2,
  Headphones,
  MoonStar,
  Sparkles,
} from "lucide-react";
import { optimizedImageUrl } from "../lib/images";
import { useSettings } from "../context/SettingsContext";
import "./PremiumHero.css";

const PUBLIC_URL = process.env.PUBLIC_URL || "";
const REFERENCE_HERO_IMAGE = `${PUBLIC_URL}/assets/hero/premium-library-reference.webp`;
const DEFAULT_BRAND_LOCKUP = `${PUBLIC_URL}/assets/brand/earnalism-brand-lockup.png`;

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

function responsiveCoverSources(book, widths = [180, 360]) {
  if (!book?.front_cover_url) return "";
  return widths
    .map((width) => `${optimizedImageUrl(book.front_cover_url, { width, quality: 82 })} ${width}w`)
    .join(", ");
}

function CatalogCoverLink({
  book,
  className,
  destination = "book_url",
  sizes,
  widths,
  eager = false,
  testId,
}) {
  if (!book) {
    return <span className={`${className} premium-hero-cover-mask`} aria-hidden="true" />;
  }

  const href = book[destination] || book.book_url;
  return (
    <Link
      to={href}
      className={className}
      aria-label={`Open ${book.title} by ${book.author}`}
      data-testid={testId || `hero-book-${book.slug}`}
      data-book-slug={book.slug}
    >
      <img
        src={book.front_cover_url}
        srcSet={responsiveCoverSources(book, widths)}
        sizes={sizes}
        alt={book.cover_alt_text}
        data-canonical-cover-url={book.front_cover_url}
        width="240"
        height="360"
        loading={eager ? "eager" : "lazy"}
        fetchPriority={eager ? "high" : "auto"}
        decoding="async"
      />
    </Link>
  );
}

function ReferenceCatalogStage({ featuredBooks, approvedAudiobooks }) {
  const readingBook = featuredBooks[0] || null;
  const featuredSlugs = new Set(featuredBooks.map((book) => book.slug));
  const listeningBook = approvedAudiobooks.find((book) => (
    book.slug !== readingBook?.slug && featuredSlugs.has(book.slug)
  ))
    || approvedAudiobooks[0]
    || null;
  const excludedSlugs = new Set([readingBook?.slug, listeningBook?.slug].filter(Boolean));
  const deskBooks = featuredBooks.filter((book) => !excludedSlugs.has(book.slug)).slice(0, 3);

  return (
    <div className="premium-reference-catalog" aria-label="Featured Sprint 1 classics">
      <CatalogCoverLink
        book={readingBook}
        destination="reader_url"
        className="premium-reference-slot premium-reference-slot--reader"
        sizes="13vw"
        widths={[220, 440]}
        eager
        testId={readingBook ? `hero-reader-${readingBook.slug}` : undefined}
      />

      {listeningBook ? (
        <Link
          to={listeningBook.cta_url}
          className="premium-reference-listening"
          aria-label={`Listen to ${listeningBook.title} by ${listeningBook.author}`}
          data-testid="hero-listening-visual"
          data-book-slug={listeningBook.slug}
        >
          <span className="premium-reference-listening__eyebrow">Now listening</span>
          <img
            src={listeningBook.front_cover_url}
            srcSet={responsiveCoverSources(listeningBook, [120, 240])}
            sizes="6vw"
            alt={listeningBook.cover_alt_text}
            data-canonical-cover-url={listeningBook.front_cover_url}
            width="120"
            height="180"
            loading="eager"
            fetchPriority="high"
            decoding="async"
          />
          <strong>{listeningBook.title}</strong>
          <small>{listeningBook.author}</small>
          <span className="premium-reference-listening__wave" aria-hidden="true" />
        </Link>
      ) : (
        <div className="premium-reference-listening premium-reference-listening--generic" data-testid="hero-listening-visual">
          <Headphones aria-hidden="true" />
          <strong>Premium Listening Rooms</strong>
        </div>
      )}

      {[0, 1, 2].map((index) => (
        <CatalogCoverLink
          key={deskBooks[index]?.slug || `empty-${index}`}
          book={deskBooks[index]}
          className={`premium-reference-slot premium-reference-slot--desk-${index + 1}`}
          sizes="9vw"
          widths={[160, 320]}
          eager={index === 0}
        />
      ))}
    </div>
  );
}

function CoverStack({ books, loading }) {
  if (loading && books.length === 0) {
    return (
      <div className="premium-mobile-covers premium-mobile-covers--loading" aria-hidden="true">
        {Array.from({ length: 4 }).map((_, index) => <span key={index} />)}
      </div>
    );
  }

  return (
    <div className="premium-mobile-covers" aria-label="Featured Sprint 1 classics">
      {books.map((book) => (
        <CatalogCoverLink
          key={book.slug}
          book={book}
          className="premium-mobile-cover"
          sizes="(max-width: 520px) 29vw, 145px"
          widths={[180, 360]}
          eager
        />
      ))}
    </div>
  );
}

export default function PremiumHero({ curation, loading = false, error = false, onTrack }) {
  const isDesktopReference = useDesktopReference();
  const { brand } = useSettings();
  const customLogo = brand?.logo_url?.trim() || DEFAULT_BRAND_LOCKUP;
  const hero = curation?.hero || {};
  const shelves = curation?.shelves || {};
  const featuredBooks = Array.isArray(hero.featured_books) ? hero.featured_books.slice(0, 6) : [];
  const approvedAudiobooks = Array.isArray(shelves.approved_audiobooks) ? shelves.approved_audiobooks : [];
  const primaryCta = hero.primary_cta?.url ? hero.primary_cta : { label: "Start Reading", url: "/library" };
  const secondaryCta = hero.secondary_cta?.url
    ? hero.secondary_cta
    : { label: "Explore Audiobooks", url: "/library?availability=approved-audiobook" };
  const headline = hero.headline || DEFAULT_HEADLINE;
  const subheadline = hero.subheadline || DEFAULT_SUBHEADLINE;
  const goldHeadline = "timeless Bengali and English classics.";
  const headlineLead = headline.includes(goldHeadline)
    ? headline.replace(goldHeadline, "").trim()
    : headline;

  return (
    <section
      className="premium-landing-hero premium-dynamic-hero premium-reference-hero"
      data-testid="premium-landing-hero"
      data-catalog-state={loading ? "loading" : error ? "unavailable" : "ready"}
      aria-label={headline}
      aria-busy={loading}
    >
      {isDesktopReference ? (
        <img
          className="premium-reference-hero__art"
          src={REFERENCE_HERO_IMAGE}
          alt=""
          aria-hidden="true"
          width="1672"
          height="941"
          loading="eager"
          fetchPriority="high"
          decoding="async"
        />
      ) : null}
      {isDesktopReference && customLogo ? (
        <div className="premium-reference-brand-overlay" data-testid="premium-reference-brand-overlay">
          <img src={customLogo} alt="" aria-hidden="true" loading="eager" decoding="async" />
        </div>
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
      </div>

      <div className="premium-hero-actions" data-testid="hero-ctas">
        <Link
          to={primaryCta.url}
          className="premium-hero-action premium-hero-action--primary"
          data-testid="hero-cta-library"
          onClick={() => track(onTrack, "hero_primary_cta_click", { cta: "home_hero_start_reading" })}
        >
          <BookOpen size={19} strokeWidth={1.55} aria-hidden="true" />
          <span>{primaryCta.label || "Start Reading"}</span>
          <ArrowRight size={17} strokeWidth={1.6} aria-hidden="true" />
        </Link>
        <Link
          to={secondaryCta.url}
          className="premium-hero-action premium-hero-action--secondary"
          data-testid="hero-cta-audiobooks"
          onClick={() => track(onTrack, "hero_secondary_cta_click", { cta: "home_hero_approved_audiobooks" })}
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

      <div className="premium-hero-catalog-shell" data-testid="hero-catalog-visuals">
        {isDesktopReference ? (
          <ReferenceCatalogStage featuredBooks={featuredBooks} approvedAudiobooks={approvedAudiobooks} />
        ) : (
          <CoverStack books={featuredBooks.slice(0, 4)} loading={loading} />
        )}
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
        {loading ? "Loading featured classics." : `${featuredBooks.length} featured classics loaded.`}
        {error ? " The live catalog is temporarily unavailable." : ""}
      </span>
    </section>
  );
}

export { DEFAULT_HEADLINE, REFERENCE_HERO_IMAGE };
