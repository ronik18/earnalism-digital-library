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
import "./PremiumHero.css";

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

function CoverStack({ books, loading }) {
  if (loading && books.length === 0) {
    return (
      <div className="premium-hero-cover-stack premium-hero-cover-stack--loading" aria-hidden="true">
        {Array.from({ length: 5 }).map((_, index) => (
          <span key={index} className="premium-hero-cover-skeleton" />
        ))}
      </div>
    );
  }

  return (
    <div className="premium-hero-cover-stack" aria-label="Featured Sprint 1 classics">
      {books.map((book, index) => (
        <Link
          key={book.slug}
          to={book.book_url}
          className="premium-hero-book-volume"
          style={{ "--book-index": index, "--book-offset": index % 2 }}
          aria-label={`Open ${book.title} by ${book.author}`}
          data-testid={`hero-book-${book.slug}`}
        >
          <span className="premium-hero-book-volume__pages" aria-hidden="true" />
          <img
            src={book.front_cover_url}
            alt={book.cover_alt_text}
            width="240"
            height="360"
            loading={index < 2 ? "eager" : "lazy"}
            fetchPriority={index === 0 ? "high" : "auto"}
          />
        </Link>
      ))}
    </div>
  );
}

function ReadingTablet({ book }) {
  return (
    <div className="premium-hero-tablet" aria-hidden={!book}>
      <div className="premium-hero-device-camera" aria-hidden="true" />
      {book ? (
        <Link to={book.reader_url} className="premium-hero-tablet__screen" aria-label={`Read ${book.title} by ${book.author}`}>
          <img src={book.front_cover_url} alt={book.cover_alt_text} width="260" height="390" />
          <span className="premium-hero-tablet__caption">
            <strong>{book.title}</strong>
            <small>{book.author}</small>
          </span>
        </Link>
      ) : (
        <div className="premium-hero-tablet__empty">
          <BookOpen aria-hidden="true" />
          <span>Premium Reading Rooms</span>
        </div>
      )}
    </div>
  );
}

function ListeningPhone({ book }) {
  return (
    <div className="premium-hero-phone" data-testid="hero-listening-visual">
      <div className="premium-hero-phone__speaker" aria-hidden="true" />
      {book ? (
        <Link to={book.cta_url} className="premium-hero-phone__screen" aria-label={`Listen to ${book.title} by ${book.author}`}>
          <span className="premium-hero-phone__eyebrow"><Headphones size={12} aria-hidden="true" /> Now listening</span>
          <img src={book.front_cover_url} alt={book.cover_alt_text} width="160" height="240" />
          <strong>{book.title}</strong>
          <small>{book.author}</small>
          <span className="premium-hero-wave" aria-hidden="true">
            {Array.from({ length: 12 }).map((_, index) => <i key={index} />)}
          </span>
          <span className="premium-hero-phone__room">Listening Room</span>
        </Link>
      ) : (
        <div className="premium-hero-phone__generic">
          <Headphones size={30} strokeWidth={1.35} aria-hidden="true" />
          <strong>Premium Listening Rooms</strong>
          <span className="premium-hero-wave" aria-hidden="true">
            {Array.from({ length: 12 }).map((_, index) => <i key={index} />)}
          </span>
        </div>
      )}
    </div>
  );
}

export default function PremiumHero({ curation, loading = false, error = false, onTrack }) {
  const hero = curation?.hero || {};
  const shelves = curation?.shelves || {};
  const featuredBooks = Array.isArray(hero.featured_books) ? hero.featured_books.slice(0, 6) : [];
  const approvedAudiobooks = Array.isArray(shelves.approved_audiobooks) ? shelves.approved_audiobooks : [];
  const readingBook = featuredBooks[1] || featuredBooks[0] || null;
  const listeningBook = approvedAudiobooks[0] || null;
  const primaryCta = hero.primary_cta?.url ? hero.primary_cta : { label: "Start Reading", url: "/library" };
  const secondaryCta = hero.secondary_cta?.url
    ? hero.secondary_cta
    : { label: "Explore Audiobooks", url: "/library?availability=approved-audiobook" };
  const headline = hero.headline || DEFAULT_HEADLINE;
  const goldHeadline = "timeless Bengali and English classics.";
  const headlineLead = headline.includes(goldHeadline)
    ? headline.replace(goldHeadline, "").trim()
    : headline;

  return (
    <section
      className="premium-landing-hero premium-dynamic-hero"
      data-testid="premium-landing-hero"
      data-catalog-state={loading ? "loading" : error ? "unavailable" : "ready"}
      aria-labelledby="premium-hero-title"
      aria-busy={loading}
    >
      <div className="premium-dynamic-hero__glow" aria-hidden="true" />
      <div className="premium-dynamic-hero__inner">
        <div className="premium-dynamic-hero__copy">
          <div className="premium-dynamic-hero__eyebrow">
            <Sparkles size={15} strokeWidth={1.6} aria-hidden="true" />
            <span>Curated Digital Library</span>
          </div>
          <h1 id="premium-hero-title" data-testid="hero-headline">
            {headlineLead}{" "}
            {headline.includes(goldHeadline) && <span>{goldHeadline}</span>}
          </h1>
          <p>{hero.subheadline || DEFAULT_SUBHEADLINE}</p>

          <div className="premium-dynamic-hero__actions" data-testid="hero-ctas">
            <Link
              to={primaryCta.url}
              className="premium-dynamic-hero__primary"
              data-testid="hero-cta-library"
              onClick={() => track(onTrack, "hero_primary_cta_click", { cta: "home_hero_start_reading" })}
            >
              <BookOpen size={19} strokeWidth={1.55} aria-hidden="true" />
              {primaryCta.label || "Start Reading"}
              <ArrowRight size={17} strokeWidth={1.6} aria-hidden="true" />
            </Link>
            <Link
              to={secondaryCta.url}
              className="premium-dynamic-hero__secondary"
              data-testid="hero-cta-audiobooks"
              onClick={() => track(onTrack, "hero_secondary_cta_click", { cta: "home_hero_approved_audiobooks" })}
            >
              <Headphones size={18} strokeWidth={1.55} aria-hidden="true" />
              {secondaryCta.label || "Explore Audiobooks"}
              <ArrowRight size={16} strokeWidth={1.6} aria-hidden="true" />
            </Link>
          </div>

          <div className="premium-dynamic-hero__chips" aria-label="Earnalism experience highlights">
            {FEATURE_CHIPS.map((chip) => (
              <span key={chip}><Globe2 size={12} strokeWidth={1.5} aria-hidden="true" />{chip}</span>
            ))}
          </div>
          {error && (
            <p className="premium-dynamic-hero__catalog-note" role="status">
              The reading room is available; featured editions will return shortly.
            </p>
          )}
        </div>

        <div className="premium-dynamic-hero__stage" data-testid="hero-catalog-visuals">
          <div className="premium-hero-orbit" aria-hidden="true">
            <span><BookOpen size={19} /></span>
            <span><Headphones size={18} /></span>
            <span><Bookmark size={17} /></span>
          </div>
          <ReadingTablet book={readingBook} />
          <ListeningPhone book={listeningBook} />
          <CoverStack books={featuredBooks} loading={loading} />
        </div>

        <aside className="premium-dynamic-hero__cards" aria-label="Premium library features" data-testid="premium-hero-feature-cards">
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
      </div>

      <div className="premium-dynamic-hero__rail" aria-label="Earnalism library benefits">
        {FEATURE_RAIL.map(({ title, Icon }) => (
          <div key={title}>
            <Icon size={25} strokeWidth={1.3} aria-hidden="true" />
            <span>{title}</span>
          </div>
        ))}
      </div>
      <span className="sr-only" aria-live="polite">
        {loading ? "Loading featured classics." : `${featuredBooks.length} featured classics loaded.`}
      </span>
    </section>
  );
}

export { DEFAULT_HEADLINE };
