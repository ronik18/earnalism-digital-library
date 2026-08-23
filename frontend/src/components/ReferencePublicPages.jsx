import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  Building2,
  Check,
  Headphones,
  Landmark,
  Lock,
  Search,
  SlidersHorizontal,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "../lib/api";
import { audiobookReleaseState } from "../lib/audioReleaseSafety";
import {
  bookLaunchStatus,
  canShowPreview,
  notifyUrl,
} from "../lib/controlledLaunch";
import BookCoverImage from "./BookCoverImage";
import "./ReferencePublicPages.css";

const HOME_FEATURES = [
  [BookOpen, "Curated classics", "Bengali and English literature"],
  [Sparkles, "Premium editions", "Designed for calm reading"],
  [Headphones, "Approved listening", "Only where release truth allows"],
  [Lock, "A private library", "Reading time stays with you"],
];

const TRUST_FACTS = [
  [Lock, "Private by design", "Your account and reading remain yours."],
  [BookOpen, "Preview first", "The first 3 canonical pages are free."],
  [Check, "Release truth", "Listening appears only when approved."],
  [Sparkles, "Beautiful editions", "Made for a slower kind of reading."],
];

function titleFor(book) {
  return book?.title_en || book?.title || "Untitled edition";
}

function isLive(book) {
  return bookLaunchStatus(book) === "LIVE_APPROVED";
}

function BookTile({ book, compact = false, priority = false, showListen = false }) {
  const title = titleFor(book);
  const live = isLive(book);
  const audio = audiobookReleaseState(book);
  const href = live ? `/book/${book.slug}` : notifyUrl(book.slug);

  return (
    <article className={`reference-book-tile${compact ? " reference-book-tile--compact" : ""}`} data-testid={`reference-book-${book.slug}`}>
      <Link to={href} className="reference-book-tile__cover" aria-label={`Open ${title}`}>
        <BookCoverImage
          book={book}
          alt=""
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : "auto"}
          width={320}
          widths={[180, 240, 320]}
          quality={80}
          sizes="(min-width: 1100px) 13vw, (min-width: 640px) 20vw, 44vw"
          data-visual-mask="cover-art"
        />
        <span className={`reference-book-tile__status ${live ? "is-live" : "is-soon"}`} data-visual-mask="availability">
          {live ? "Live" : "Coming soon"}
        </span>
      </Link>
      <div className="reference-book-tile__details">
        <Link to={href} className="reference-book-tile__title" data-visual-mask="book-title">{title}</Link>
        <span className="reference-book-tile__author" data-visual-mask="book-author">{book.author || "Earnalism edition"}</span>
        <div className="reference-book-tile__actions">
          {canShowPreview(book) ? <Link to={`/reader/${book.slug}`}>Read</Link> : <Link to={href}>Notify me</Link>}
          {showListen && audio.canShowControls ? <Link to={`/reader/${book.slug}?listen=1`}>Listen now</Link> : null}
        </div>
      </div>
    </article>
  );
}

function usePublicBooks() {
  const [books, setBooks] = useState([]);

  useEffect(() => {
    const controller = new AbortController();
    api.get("/books", { signal: controller.signal })
      .then(({ data }) => setBooks(Array.isArray(data) ? data : []))
      .catch(() => setBooks([]));
    return () => controller.abort();
  }, []);

  return books;
}

function SectionHeading({ eyebrow, title, action, children }) {
  return (
    <div className="reference-section-heading">
      <div>
        {eyebrow ? <p>{eyebrow}</p> : null}
        <h2>{title}</h2>
        {children}
      </div>
      {action}
    </div>
  );
}

export function ReferenceHomeSurface() {
  const books = usePublicBooks();
  const liveBooks = useMemo(() => books.filter(isLive), [books]);
  const shelfBooks = (liveBooks.length ? liveBooks : books).slice(0, 5);
  const listeningBooks = books.filter((book) => audiobookReleaseState(book).canShowControls).slice(0, 5);

  return (
    <div className="reference-home" data-testid="home-reference-surface">
      <section className="reference-home__hero" aria-labelledby="reference-home-title">
        <div className="reference-home__hero-copy">
          <p className="reference-kicker">THE EARNALISM DIGITAL LIBRARY</p>
          <h1 id="reference-home-title">A library<br />made for lingering.</h1>
          <p className="reference-home__lede">Timeless Bengali and English classics. Beautiful editions. A calm reading room for stories that stay with you.</p>
          <div className="reference-home__cta-row">
            <Link to="/library" className="reference-button reference-button--gold">Enter the Library</Link>
            <Link to="/library?availability=approved-audiobook" className="reference-button reference-button--outline">Enter the Listening Room</Link>
          </div>
          <p className="reference-home__policy"><Check aria-hidden="true" /> First 3 pages free to preview <span /> <ClockMark aria-hidden="true" /> Reading time is used only while you read</p>
        </div>
        <img className="reference-home__hero-art" src="/assets/hero/premium-library-reference-exact-1440.webp" alt="" fetchPriority="high" decoding="async" />
      </section>

      <section className="reference-feature-strip" aria-label="Earnalism reading room features">
        {HOME_FEATURES.map(([Icon, title, copy]) => (
          <article key={title}><Icon aria-hidden="true" /><div><strong>{title}</strong><span>{copy}</span></div></article>
        ))}
      </section>

      <section className="reference-home__journey" aria-labelledby="reference-journey-title">
        <SectionHeading
          eyebrow="BEGIN YOUR JOURNEY"
          title="Find the language, voice, and story that feels like home."
          action={<Link to="/library" className="reference-text-link">Browse the complete library <ArrowRight aria-hidden="true" /></Link>}
        />
        <div className="reference-book-shelf" data-testid="home-journey-shelf">
          {shelfBooks.map((book, index) => <BookTile key={book.slug} book={book} priority={index === 0} />)}
        </div>
      </section>

      <section className="reference-home__pass" aria-labelledby="reference-pass-title">
        <div className="reference-home__pass-copy">
          <p className="reference-kicker">READING PASS</p>
          <h2 id="reference-pass-title">Stay with a story for as long as it holds you.</h2>
          <ul>
            <li>Read in Bengali and English</li>
            <li>First 3 pages are free on eligible titles</li>
            <li>Reading time is used only while you read</li>
            <li>No subscription or autorenewal</li>
          </ul>
          <Link className="reference-button reference-button--gold" to="/pricing">View Reading Passes</Link>
        </div>
        <div className="reference-home__pass-cards" aria-label="Reading Pass options">
          {["Add time when you want to continue", "One wallet across eligible titles", "Your reading stays private"].map((copy, index) => (
            <article key={copy}><span>{String(index + 1).padStart(2, "0")}</span><p>{copy}</p><Link to="/pricing">View passes</Link></article>
          ))}
        </div>
      </section>

      <section className="reference-home__listening" aria-labelledby="reference-listening-title">
        <SectionHeading
          eyebrow="THE LISTENING ROOM"
          title="Stories in voice, released with care."
          action={<Link to="/library?availability=approved-audiobook" className="reference-text-link">Explore approved audiobooks <ArrowRight aria-hidden="true" /></Link>}
        >
          <p>Approved audiobooks offer their first 3 minutes for preview. Titles without approval show no listening action.</p>
        </SectionHeading>
        {listeningBooks.length ? <div className="reference-book-shelf">{listeningBooks.map((book) => <BookTile key={book.slug} book={book} showListen />)}</div> : <p className="reference-empty-listening">Listening rooms appear here only when an edition is approved for audio.</p>}
      </section>

      <section className="reference-home__trust" aria-labelledby="reference-trust-title">
        <h2 id="reference-trust-title">Why readers choose Earnalism</h2>
        <div>{TRUST_FACTS.map(([Icon, title, copy]) => <article key={title}><Icon aria-hidden="true" /><strong>{title}</strong><p>{copy}</p></article>)}</div>
      </section>
    </div>
  );
}

function ClockMark(props) {
  return <span {...props} className="reference-clock-mark">◷</span>;
}

function CompactFilters({ language, reading, listening, onChange }) {
  const groups = [
    ["Language", language, [["all", "All books"], ["bn", "Bengali"], ["en", "English"]], "language"],
    ["Format", reading, [["all", "All forms"], ["novel", "Reader"], ["short-story", "Short stories"], ["poetry", "Poetry & essays"]], "reading"],
    ["Status", listening, [["all", "All releases"], ["available", "Audiobooks"], ["hidden", "Reader only"]], "listening"],
  ];
  return <>{groups.map(([label, value, options, key]) => <fieldset className="reference-filter-group" key={label}><legend>{label}</legend>{options.map(([slug, name]) => <button type="button" key={slug} aria-pressed={value === slug} onClick={() => onChange(key, slug)}>{name}</button>)}</fieldset>)}</>;
}

export function ReferenceLibrarySurface({
  filteredBooks,
  loading,
  query,
  language,
  reading,
  listening,
  sort,
  onSearch,
  onParam,
  filtersOpen,
  setFiltersOpen,
}) {
  const live = filteredBooks.filter(isLive);
  const comingSoon = filteredBooks.filter((book) => !isLive(book));
  const approvedAudio = filteredBooks.filter((book) => audiobookReleaseState(book).canShowControls);
  const shelves = [
    ["Live now", "Reader-ready editions to open today.", live],
    ["Coming soon", "Titles preparing for a future release.", comingSoon],
    ["Audiobooks", "Only editions with approved listening access.", approvedAudio],
  ];
  const update = (key, value) => onParam(key, value, "all");

  return (
    <div className="reference-library" data-testid="library-reference-surface">
      <header className="reference-library__titlebar">
        <div><p className="reference-kicker">THE EARNALISM LIBRARY</p><h1>The Library</h1><span>Curated classics for every mood and moment.</span></div>
        <div className="reference-library__controls">
          <label className="reference-search"><Search aria-hidden="true" /><input data-testid="library-search" value={query} onChange={(event) => onSearch(event.target.value)} placeholder="Search by title, author or keyword..." aria-label="Search the Library" /></label>
          <label className="reference-sort">Sort by<select data-testid="library-sort" value={sort} onChange={(event) => onParam("sort", event.target.value, "recently-approved")}><option value="recently-approved">Featured</option><option value="title">Title</option><option value="author">Author</option><option value="short-reads">Short reads</option></select></label>
          <button className="reference-filter-trigger" type="button" onClick={() => setFiltersOpen(true)}><SlidersHorizontal aria-hidden="true" /> Filters</button>
        </div>
      </header>
      <main className="reference-library__content">
        <aside className="reference-library__sidebar" aria-label="Library filters"><p>Explore</p><CompactFilters language={language} reading={reading} listening={listening} onChange={update} /><div className="reference-library__pass"><strong>Reading Pass</strong><p>Add time only when a story asks you to stay.</p><Link to="/pricing">View passes</Link></div></aside>
        <section className="reference-library__shelves" aria-live="polite">
          {loading ? <p className="reference-loading">Opening the collection...</p> : shelves.map(([title, copy, books]) => <section key={title} className="reference-library-shelf" aria-labelledby={`shelf-${title}`}><SectionHeading eyebrow={title === "Live now" ? "LIVE NOW" : title.toUpperCase()} title={title} action={<span className="reference-shelf-count">{books.length} editions</span>}><p>{copy}</p></SectionHeading>{books.length ? <div className="reference-library-grid">{books.slice(0, 10).map((book, index) => <BookTile key={book.slug} book={book} compact priority={index < 2} showListen={title === "Audiobooks"} />)}</div> : <p className="reference-empty-listening">No titles currently match this release state.</p>}</section>)}
        </section>
      </main>
      {filtersOpen ? <div className="reference-library-drawer" role="dialog" aria-modal="true" aria-label="Library filters"><div><header><strong>Filters</strong><button type="button" onClick={() => setFiltersOpen(false)} aria-label="Close filters"><X aria-hidden="true" /></button></header><CompactFilters language={language} reading={reading} listening={listening} onChange={update} /><button type="button" className="reference-button reference-button--gold" onClick={() => setFiltersOpen(false)}>Apply filters</button></div></div> : null}
    </div>
  );
}

function packTitle(pack) {
  return pack.label || pack.name || (pack.minutes ? `${pack.minutes} minutes` : "Reading time");
}

export function ReferenceCommerceSurface({ packs, config, busyId, selectedPackId, onBuy }) {
  const giftEnabled = packs.some((pack) => pack.gift_enabled === true || pack.kind === "gift");
  return (
    <div className="reference-commerce" data-testid="pricing-reference-surface">
      <section className="reference-commerce__hero" aria-labelledby="reference-commerce-title">
        <div><p className="reference-kicker">READING PASSES</p><h1 id="reference-commerce-title">Read more.<br />Live the stories.</h1><p>Unlock unhurried reading time and immerse yourself in timeless Bengali and English classics.</p><ul><li>First 3 pages free on eligible books</li><li>Reading time is used only while you read</li><li>No subscription or autorenewal</li></ul></div>
        <img src="/assets/hero/premium-library-reference-exact-1440.webp" alt="" decoding="async" />
      </section>
      <main className="reference-commerce__main">
        <section className="reference-commerce__offers" aria-labelledby="reference-offers-title"><SectionHeading title="Choose a Reading Pass that fits your rhythm" /><div className="reference-commerce__packs">{packs.map((pack) => { const recommended = pack.recommended === true || pack.is_recommended === true; const selected = selectedPackId === pack.id; return <article key={pack.id} className={`reference-offer${recommended || selected ? " is-emphasized" : ""}`}><p className="reference-offer__minutes">{packTitle(pack)}</p>{pack.description ? <span>{pack.description}</span> : null}<strong data-visual-mask="live-price">{pack.price_inr ? `₹${pack.price_inr}` : "Available at checkout"}</strong>{pack.minutes ? <small>{pack.minutes} minutes of reading time</small> : null}<ul><li>Read on web and mobile</li><li>Continue across eligible titles</li><li>First 3 pages always free</li></ul><button type="button" disabled={busyId === pack.id} onClick={() => onBuy(pack)}>{busyId === pack.id ? "Opening checkout..." : `Choose ${packTitle(pack)}`}</button></article>; })}</div></section>
        <section className="reference-commerce__pathways"><article><Landmark aria-hidden="true" /><h2>For institutions</h2><p>School, college, and library access begins with a conversation.</p><Link to="/contact">Request a pilot</Link></article><article><Building2 aria-hidden="true" /><h2>For publishers</h2><p>Rights holders and authors can explore a careful digital edition pathway.</p><Link to="/contact">Partner with us</Link></article>{giftEnabled ? <article><Sparkles aria-hidden="true" /><h2>Gift a pass</h2><p>Share reading time when a configured gift product is available.</p><Link to="/pricing">View gift options</Link></article> : null}</section>
        <section className="reference-commerce__trust" data-testid="pricing-wallet-explainer"><div><Lock aria-hidden="true" /><strong>Secure payment</strong><span>{config?.configured ? "Configured checkout" : "Checkout availability is confirmed at purchase"}</span></div><div><Check aria-hidden="true" /><strong>Privacy first</strong><span>Your account and reading stay private.</span></div><div><BookOpen aria-hidden="true" /><strong>Reading time</strong><span>Used only while you read.</span></div></section>
        <section className="reference-commerce__final"><p className="reference-kicker">START WITH THE PREVIEW</p><h2>Meet a story before you add time.</h2><p>The first 3 canonical pages are free. Continue with a Reading Pass when you are ready.</p><Link to="/library" className="reference-button reference-button--gold">Browse the library</Link></section>
      </main>
    </div>
  );
}
