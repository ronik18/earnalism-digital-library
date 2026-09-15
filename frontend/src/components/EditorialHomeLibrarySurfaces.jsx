import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  Building2,
  Check,
  Clock3,
  ChevronLeft,
  ChevronRight,
  Headphones,
  Landmark,
  Lock,
  Search,
  SlidersHorizontal,
  Sparkles,
  Eye,
  ShieldCheck,
  Focus,
  X,
} from "lucide-react";
import { api } from "../lib/api";
import { PUBLIC_ACCESS_COPY, PUBLIC_PREVIEW_COPY, READING_TIME_COPY } from "../lib/publicAccessCopy";
import { audiobookReleaseState } from "../lib/audioReleaseSafety";
import {
  canShowPreview,
  canShowStartReading,
  notifyUrl,
} from "../lib/controlledLaunch";
import { availabilityOfBook } from "../lib/libraryCatalog";
import BookCoverImage from "./BookCoverImage";
import LibraryBrowseShelf from "./LibraryBrowseShelf";
import LibraryReadingPassCard from "./LibraryReadingPassCard";
import ReaderTestimonialsSection from "./ReaderTestimonialsSection";
import { bookCoverImageSources } from "../lib/images";
import "./ReferencePublicPages.css";
import "../styles/quiet-heritage.css";
import "../styles/library-paper-review.css";
import "../styles/home-compact-burgundy.css";

const HOME_FEATURES = [
  [BookOpen, "Curated Classics", "Old favourites. New companions."],
  [Sparkles, "Beautiful Editions", "Words given room to breathe."],
  [Eye, "A Beginning on Us", "Read the first 3 pages free."],
  [Focus, "Time to Linger", "A quiet space, one page at a time."],
];

const TRUST_FACTS = [
  [BookOpen, "Meet your next favourite", "Return to a beloved classic, or meet a world you haven’t known."],
  [Eye, "Begin with curiosity", "The first 3 pages are free. Let the words win you over."],
  [Clock3, "Keep your own rhythm", "Reading time counts only while you read. No subscription."],
];

function titleFor(book) {
  return book?.title_en || book?.title || "Untitled edition";
}

function isLive(book) {
  return canShowStartReading(book);
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
          {canShowPreview(book) ? <Link to={`/reader/${book.slug}`}>Read</Link> : live ? <Link to={href}>Details</Link> : <Link to={href}>Notify me</Link>}
          {audio.releaseApproved ? <span className="reference-book-tile__locked-audio">{audio.canShowControls ? "Reading Pass required" : "Listening unavailable"}</span> : null}
        </div>
      </div>
    </article>
  );
}

function HomeCoverTile({ book, priority }) {
  const [unavailable, setUnavailable] = useState(false);
  const title = titleFor(book);
  const href = isLive(book) ? `/book/${book.slug}` : notifyUrl(book.slug);
  if (unavailable) return null;
  return <article className="reference-home-cover" data-testid={`home-cover-${book.slug}`}>
    <Link to={href} aria-label={`Open ${title} by ${book.author || "Earnalism"}${isLive(book) ? "" : " — coming soon"}`} title={title}>
      <BookCoverImage book={book} alt="" width={320} height={480} widths={[180,240,320]} sizes="(min-width:1100px) 16vw, (min-width:640px) 26vw, 48vw" loading={priority ? "eager" : "lazy"} fetchPriority={priority ? "high" : "auto"} allowGraphicalFallback={false} onPermanentFailure={() => setUnavailable(true)} />
    </Link>
  </article>;
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

function ReferenceShelf({ books, className = "", label, testId, compact = false, coversOnly = false, ...regionProps }) {
  const shelfRef = useRef(null);
  const scroll = (direction) => shelfRef.current?.scrollBy({ left: direction * Math.max(220, shelfRef.current.clientWidth * 0.64), behavior: "smooth" });
  return (
    <div className={`reference-shelf-frame ${className}`.trim()} data-testid={testId} {...regionProps}>
      <div ref={shelfRef} className="reference-book-shelf" aria-label={label}>
        {books.map((book, index) => coversOnly ? <HomeCoverTile key={book.slug} book={book} priority={index < 5} /> : <BookTile key={book.slug} book={book} compact={compact} priority={index === 0} />)}
      </div>
      <div className="reference-shelf-frame__controls" aria-label={`${label} controls`}>
        <button type="button" aria-label="Previous titles" onClick={() => scroll(-1)}><ChevronLeft aria-hidden="true" /></button>
        <button type="button" aria-label="Next titles" onClick={() => scroll(1)}><ChevronRight aria-hidden="true" /></button>
      </div>
    </div>
  );
}

export function ReferenceHomeSurface({ curation, readingPasses = [], listeningItems = [], illustrativePasses = false }) {
  const books = usePublicBooks();
  const curatedBooks = useMemo(() => (
    Array.isArray(curation?.hero?.featured_books) ? curation.hero.featured_books : []
  ), [curation]);
  const liveBooks = useMemo(() => books.filter(isLive), [books]);
  // The Home route already carries a server-curated, release-safe shelf snapshot.
  // Keep that visible during a transient catalogue failure instead of collapsing the
  // reference shelf. These cards still use the same fail-closed CTA rules as live data.
  const shelfBooks = (liveBooks.length ? liveBooks : (books.length ? books : curatedBooks))
    .filter((book) => { const cover = bookCoverImageSources(book); return cover.hasCover && !cover.isFallback; })
    .slice(0, 10);
  const passes = readingPasses.filter((pack) => pack && Number.isFinite(pack.minutes) && pack.minutes > 0 && Number.isFinite(pack.price_inr) && pack.price_inr >= 0).slice(0, 3);
  // Listening discovery comes from the public /home/listening contract. That
  // contract carries release-safe metadata only; package and media details
  // remain available solely after the Listener's authenticated authorization.
  const listeningBooks = (Array.isArray(listeningItems) ? listeningItems : [])
    .filter((book) => audiobookReleaseState(book).releaseApproved)
    .slice(0, 5);

  return (
    <div className="reference-home" data-testid="home-reference-surface">
      <section className="reference-home__hero" aria-labelledby="reference-home-title">
        <div className="reference-home__hero-copy">
          <h1 id="reference-home-title">Come for a story.<br />Stay a little longer.</h1>
          <p className="reference-home__lede">Bengali and English classics, waiting for you.<br />A familiar voice. A world you haven’t met.<br />Open a page. Let the day grow quiet.</p>
          <div className="reference-home__cta-row">
            <Link to="/library" className="reference-button reference-button--gold" data-testid="home-reference-primary-cta">Enter the Library</Link>
            <Link to="/library?availability=approved-audiobook" className="reference-button reference-button--outline">Discover listening</Link>
          </div>
          <div className="reference-home__policy"><p><BookOpen aria-hidden="true" /><span>{PUBLIC_PREVIEW_COPY}</span></p><p><ClockMark aria-hidden="true" /><span>{READING_TIME_COPY}</span></p></div>
        </div>
        <picture className="reference-home__hero-art">
          <img src="/assets/hero/earnalism-black-burgundy-reading-room.webp" alt="" fetchPriority="high" decoding="async" />
        </picture>
      </section>

      <section className="reference-feature-strip" aria-label="Earnalism reading room features">
        {HOME_FEATURES.map(([Icon, title, copy]) => (
          <article key={title}><Icon aria-hidden="true" /><div><strong>{title}</strong><span>{copy}</span></div></article>
        ))}
      </section>

      <section className="reference-home__journey" aria-label="Begin Your Journey">
        <SectionHeading
          title="Begin Your Journey"
        ><p>Which cover calls to you?</p></SectionHeading>
        <ReferenceShelf books={shelfBooks} coversOnly label="Featured classics" className="reference-home__journey-shelf" data-testid="home-journey-shelf" />
      </section>

      <ReaderTestimonialsSection />

      <section className="reference-home__pass" aria-labelledby="reference-pass-title">
        <div className="reference-home__pass-copy">
          <h2 id="reference-pass-title">Make time for a good story.</h2>
          <p className="reference-home__pass-intro">With Reading Passes, you pay for reading time.</p>
          <ul>
            <li><Clock3 aria-hidden="true" />{READING_TIME_COPY}</li>
            <li><BookOpen aria-hidden="true" />One wallet across eligible editions</li>
            <li><ShieldCheck aria-hidden="true" />No subscription or autorenewal</li>
          </ul>
          <Link className="reference-button reference-button--gold" to="/pricing">Find your Reading Pass</Link>
        </div>
        <div className="reference-home__pass-options">
          <div className="reference-home__pass-cards" aria-label="Reading Pass options">
            {passes.length ? passes.map((pack) => <article key={pack.id} className={pack.recommended ? "is-featured" : ""}>
              {pack.recommended && <span className="reference-home__pass-badge">{illustrativePasses ? "Featured plan" : "Recommended"}</span>}
              <h3>{pack.minutes} Minutes</h3>
              <strong className="reference-home__pass-price">₹{pack.price_inr}</strong>
              <p>{Number.isFinite(pack.validity_days) && pack.validity_days > 0 ? `Valid for ${pack.validity_days} days` : "See current pass details"}</p>
              <Link to="/pricing" aria-label={`View ${pack.minutes}-minute Reading Pass`}>View Pass</Link>
            </article>) : ["A little escape", "A longer chapter", "Time to linger"].map((title) => <article key={title}><h3>{title}</h3><strong className="reference-home__pass-price reference-home__pass-price--message">Your time</strong><p>Discover available Reading Passes</p><Link to="/pricing">View Passes</Link></article>)}
          </div>
          {illustrativePasses && <p className="reference-home__sample-note">Illustrative plans · Confirm current prices on Reading Passes.</p>}
        </div>
      </section>

      {listeningBooks.length > 0 && <section className="reference-home__listening" aria-labelledby="reference-listening-title">
        <SectionHeading
          eyebrow="THE LISTENING ROOM"
          title="Stories in voice, released with care."
          action={<Link to="/library?availability=approved-audiobook" className="reference-text-link">Explore approved audiobooks <ArrowRight aria-hidden="true" /></Link>}
        >
          <p>Approved audiobooks require an active Reading Pass. Titles without approval show no listening action.</p>
        </SectionHeading>
        <ReferenceShelf books={listeningBooks} label="Approved audiobooks" />
      </section>}

      <section className="reference-home__trust" aria-labelledby="reference-trust-title">
        <h2 id="reference-trust-title">Made for the love of reading</h2>
        <div>{TRUST_FACTS.map(([Icon, title, copy]) => <article key={title}><Icon aria-hidden="true" /><strong>{title}</strong><p>{copy}</p></article>)}</div>
      </section>
    </div>
  );
}

function ClockMark(props) {
  return <Clock3 {...props} />;
}

function CompactFilters({ language, reading, listening, genre, genres, sort, hideAll = false, showAllForGroups = [], drawer = false, onChange }) {
  const groups = [
    ["Language", language, [["all", "All languages"], ["bn", "Bengali"], ["en", "English"]], "language"],
    ["Format", reading, [["all", "All forms"], ["novel", "Novels"], ["short-story", "Short stories"], ["poetry", "Poetry & essays"]], "reading"],
    ["Status", listening, [["all", "All releases"], ["available", "Audiobooks"], ["hidden", "Reader only"]], "listening"],
    ["Genre", genre, [["all", "All genres"], ...genres.map((value) => [value, value.replace(/-/g, " ")])], "genre"],
  ];
  const drawerGroups = [groups[0], groups[1], groups[2]];
  const shouldHideAllOption = (groupId, slug) => hideAll && slug === "all" && !showAllForGroups.includes(groupId);
  if (drawer) {
    return <>
      <label className="reference-filter-sort">Sort by<select value={sort} onChange={(event) => onChange("sort", event.target.value)}><option value="recently-approved">Featured</option><option value="title">Title A–Z</option><option value="author">Author A–Z</option><option value="short-reads">Shortest first</option></select></label>
      {drawerGroups.map(([label, value, options, key]) => <fieldset className="reference-filter-group" data-filter-group={key} key={label}><legend>{label}</legend>{options.filter(([slug]) => !shouldHideAllOption(key, slug)).map(([slug, name]) => <button type="button" key={slug} aria-pressed={value === slug} onClick={() => onChange(key, slug)}>{name}</button>)}</fieldset>)}
      <fieldset className="reference-filter-group" data-filter-group="genre"><legend>Genre</legend><label className="reference-filter-select"><span className="sr-only">Genre</span><select value={genre} onChange={(event) => onChange("genre", event.target.value)}>{groups[3][2].map(([slug, name]) => <option value={slug} key={slug}>{name}</option>)}</select></label></fieldset>
    </>;
  }
  return <>{groups.map(([label, value, options, key]) => <fieldset className="reference-filter-group" data-filter-group={key} key={label}><legend>{label}</legend>{options.filter(([slug]) => !shouldHideAllOption(key, slug)).map(([slug, name]) => <button type="button" key={slug} aria-pressed={value === slug} onClick={() => onChange(key, slug)}>{name}</button>)}</fieldset>)}{sort !== undefined ? <label className="reference-filter-sort">Sort by<select value={sort} onChange={(event) => onChange("sort", event.target.value)}><option value="recently-approved">Featured</option><option value="title">Title A–Z</option><option value="author">Author A–Z</option><option value="short-reads">Shortest first</option></select></label> : null}</>;
}

function getRenderedFocusableControls(container) {
  if (!container) return [];
  const selector = "a[href], button:not([disabled]), input:not([disabled]):not([type='hidden']), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";
  const hasExcludedAncestor = (element) => {
    for (let node = element; node; node = node.parentElement) {
      if (node.hasAttribute("inert") || node.getAttribute("aria-hidden") === "true") return true;
    }
    return false;
  };
  return [...container.querySelectorAll(selector)].filter((element) => {
    if (hasExcludedAncestor(element)) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none"
      && style.visibility !== "hidden"
      && style.visibility !== "collapse"
      && element.getClientRects().length > 0
      && rect.width > 0
      && rect.height > 0;
  });
}

export function ReferenceLibrarySurface({
  filteredBooks,
  loading,
  catalogueState,
  retryingCatalogue,
  onRetryCatalogue,
  query,
  language,
  reading,
  listening,
  genre,
  genres,
  sort,
  onSearch,
  onParam,
  onResetFilters,
  filtersOpen,
  setFiltersOpen,
}) {
  const filterTriggerRef = useRef(null);
  const filterDrawerRef = useRef(null);
  const searchRef = useRef(null);
  const activeFilters = [
    ["language", language, {bn:"Bengali",en:"English"}[language] || language],
    ["reading", reading, {novel:"Novels","short-story":"Short stories",poetry:"Poetry & essays"}[reading] || reading],
    ["listening", listening, {available:"Audiobooks",hidden:"Reader only"}[listening] || listening],
    ["genre", genre, genre?.replace(/-/g," ")],
  ].filter(([,value]) => value && value !== "all");
  const resultLabel = `${filteredBooks.length} ${filteredBooks.length === 1 ? "edition" : "editions"}`;
  const filterKey = JSON.stringify([query,language,reading,listening,genre,sort,catalogueState]);
  const clearSearch = () => { onSearch(""); requestAnimationFrame(() => searchRef.current?.focus()); };
  const clearFilters = () => { onResetFilters(); requestAnimationFrame(() => searchRef.current?.focus()); };
  const live = filteredBooks.filter(isLive);
  const comingSoon = filteredBooks.filter((book) => !isLive(book));
  const approvedAudio = filteredBooks.filter((book) => audiobookReleaseState(book).releaseApproved);
  const showingFallback = catalogueState === "fallback";
  const catalogueIsEmpty = catalogueState === "empty";
  const shelves = [
    ["Live now", "Meet the editions on our shelves. Open a book for its reading options.", live],
    ["Coming soon", "More stories are on their way. Leave your interest with us.", comingSoon],
    ["Audiobooks", "Stories with an approved audio edition. Each book shows whether listening is available.", approvedAudio],
  ];
  const update = (key, value) => onParam(key, value, key === "sort" ? "recently-approved" : "all");
  const closeFilters = () => {
    setFiltersOpen(false);
    requestAnimationFrame(() => filterTriggerRef.current?.focus());
  };

  useEffect(() => {
    if (!filtersOpen) return undefined;
    const trigger = filterTriggerRef.current;
    const drawer = filterDrawerRef.current;
    const header = document.querySelector("header[data-testid='site-header']");
    const footer = document.querySelector("footer");
    const backgroundChildren = drawer ? [...drawer.parentElement.children].filter((element) => element !== drawer) : [];
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const backgroundState = [...backgroundChildren, header, footer].filter(Boolean).map((element) => ({
      element,
      inert: element.hasAttribute("inert"),
      inertValue: element.getAttribute("inert"),
      ariaHidden: element.hasAttribute("aria-hidden"),
      ariaHiddenValue: element.getAttribute("aria-hidden"),
    }));
    backgroundState.forEach(({ element }) => {
      element.setAttribute("inert", "");
      element.setAttribute("aria-hidden", "true");
    });
    const close = () => {
      setFiltersOpen(false);
      requestAnimationFrame(() => trigger?.focus());
    };
    const focusFirstControl = () => drawer?.querySelector("button[aria-label='Close filters']")?.focus();
    focusFirstControl();
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }
      if (event.key !== "Tab" || !drawer) return;
      const controls = getRenderedFocusableControls(drawer);
      if (!controls.length) return;
      event.preventDefault();
      const currentIndex = controls.indexOf(document.activeElement);
      const nextIndex = event.shiftKey
        ? (currentIndex <= 0 ? controls.length - 1 : currentIndex - 1)
        : (currentIndex < 0 || currentIndex >= controls.length - 1 ? 0 : currentIndex + 1);
      controls[nextIndex].focus();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      backgroundState.forEach(({ element, inert, inertValue, ariaHidden, ariaHiddenValue }) => {
        if (inert) element.setAttribute("inert", inertValue ?? "");
        else element.removeAttribute("inert");
        if (ariaHidden) element.setAttribute("aria-hidden", ariaHiddenValue ?? "");
        else element.removeAttribute("aria-hidden");
      });
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [filtersOpen, setFiltersOpen]);

  return (
    <div className="reference-library" data-testid="library-reference-surface">
      <header className="reference-library__titlebar">
        <div><p className="reference-kicker">THE EARNALISM LIBRARY</p><h1>The Library</h1><span>Find a familiar favourite. Make room for a new one.</span></div>
        <div className="reference-library__controls">
          <div className="reference-search"><Search aria-hidden="true" /><input ref={searchRef} type="search" data-testid="library-search" value={query} onChange={(event) => onSearch(event.target.value)} placeholder="Title or author" aria-label="Search the Library" />{query && <button type="button" className="reference-search-clear" aria-label="Clear search" onClick={clearSearch}><X aria-hidden="true" /></button>}</div>
          <label className="reference-sort">Sort by<select data-testid="library-sort" value={sort} onChange={(event) => onParam("sort", event.target.value, "recently-approved")}><option value="recently-approved">Featured</option><option value="title">Title A–Z</option><option value="author">Author A–Z</option><option value="short-reads">Shortest first</option></select></label>
          <button ref={filterTriggerRef} className="reference-filter-trigger" type="button" aria-haspopup="dialog" aria-expanded={filtersOpen} onClick={() => setFiltersOpen(true)}><SlidersHorizontal aria-hidden="true" /> Filters{activeFilters.length > 0 && <span className="reference-filter-count">{activeFilters.length}</span>}</button>
        </div>
      </header>
      <div className="reference-library__results-bar">
        <p role="status" aria-live="polite" aria-atomic="true">{loading ? "Finding your next read…" : `${resultLabel}${showingFallback ? " in this limited selection" : query ? " found" : " to explore"}`}</p>
        {activeFilters.length > 0 && <div className="reference-active-filters" aria-label="Active filters">{activeFilters.map(([key,,label]) => <button key={key} type="button" aria-label={`Remove ${label} filter`} onClick={() => { update(key,"all"); requestAnimationFrame(() => searchRef.current?.focus()); }}>{label}<X aria-hidden="true" /></button>)}<button type="button" className="reference-clear-filters" onClick={clearFilters}>Clear filters</button></div>}
      </div>
      <div className="reference-library__content">
        <aside className="reference-library__sidebar" aria-label="Library filters"><p>Explore</p><CompactFilters language={language} reading={reading} listening={listening} genre={genre} genres={genres} onChange={update} /><LibraryReadingPassCard /></aside>
        <section className="reference-library__shelves" aria-label="Library editions" aria-busy={loading}>
          {showingFallback ? <div className="reference-library__recovery" role="status" data-testid="library-catalogue-fallback"><p>We couldn’t load the full collection. You’re viewing a limited selection.</p><button type="button" className="reference-button reference-library__recovery-retry" data-testid="library-catalogue-retry" onClick={onRetryCatalogue} disabled={retryingCatalogue}>{retryingCatalogue ? "Trying again…" : "Try again"}</button></div> : null}
          {loading ? <p className="reference-loading" role="status">Opening the collection…</p> : catalogueIsEmpty && !filteredBooks.length ? <div className="reference-library__no-results" data-testid="library-catalogue-empty"><BookOpen aria-hidden="true" /><h2>The shelves are quiet for now.</h2><p>There are no editions in this collection yet. Please visit again soon.</p></div> : !filteredBooks.length ? <div className="reference-library__no-results" data-testid="library-no-results"><Search aria-hidden="true" /><h2>No stories found this time.</h2><p>{query ? <>Nothing matches “{query}”{activeFilters.length ? " with these filters" : ""}. Try another title or author.</> : "Try a different language, form or release option."}</p><div>{query && <button type="button" onClick={clearSearch}>Clear search</button>}{activeFilters.length > 0 && <button type="button" onClick={clearFilters}>Clear filters</button>}</div></div> : shelves.map(([title,copy,books]) => <LibraryBrowseShelf key={`${title}-${filterKey}`} title={title} copy={copy} books={books} renderBook={(book,index) => <BookTile key={book.slug} book={book} compact priority={index < 2} />} />)}
        </section>
      </div>
      <LibraryReadingPassCard compact />
      {filtersOpen ? <div ref={filterDrawerRef} className="reference-library-drawer" role="dialog" aria-modal="true" aria-label="Library filters" onMouseDown={(event) => { if (event.target === event.currentTarget) closeFilters(); }}><div><header><strong>Filters</strong><div><button type="button" className="reference-filter-reset" onClick={onResetFilters}>Reset</button><button type="button" onClick={closeFilters} aria-label="Close filters"><X aria-hidden="true" /></button></div></header><div className="reference-library-drawer__body"><CompactFilters language={language} reading={reading} listening={listening} genre={genre} genres={genres} sort={sort} hideAll showAllForGroups={["listening"]} drawer onChange={update} /></div><div className="reference-library-drawer__footer"><p role="status" aria-live="polite">Filters update as you choose.</p><button type="button" className="reference-button reference-button--gold" onClick={closeFilters}>{loading ? "Return to Library" : `Show ${resultLabel}`}</button></div></div></div> : null}
    </div>
  );
}


export { default as ReferenceCommerceSurface } from "./ReadingPassesSurface";
