import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, Check, Headphones, Search, SlidersHorizontal } from "lucide-react";
import { api } from "../lib/api";
import BookCard from "../components/BookCard";
import PremiumHero from "../components/PremiumHero";
import {
  BATCH_1_READER_ONLY_SLUGS,
  LIVE_APPROVED_SLUG,
  PIPELINE_BOOKS,
  mergeDraculaBook,
  notifyUrl,
} from "../lib/controlledLaunch";
import { languageOfBook, matchesLibraryFacets, sortLibraryBooks } from "../lib/libraryCatalog";
import { LOCAL_LIBRARY_FALLBACK_BOOKS } from "../lib/libraryFallbackBooks";
import { fetchHomeCuration, getHomeCurationSnapshot } from "../lib/homeCuration";
import { audiobookReleaseState } from "../lib/audioReleaseSafety";
import useSEO from "../hooks/useSEO";

const LANGUAGE_FILTERS = [
  { slug: "all", name: "All languages" },
  { slug: "bn", name: "Bengali" },
  { slug: "en", name: "English" },
];
const READING_FILTERS = [
  { slug: "all", name: "All forms" },
  { slug: "novel", name: "Novels" },
  { slug: "short-story", name: "Short stories" },
  { slug: "poetry", name: "Poetry & essays" },
];
const LISTENING_FILTERS = [
  { slug: "all", name: "All listening" },
  { slug: "available", name: "Listening available" },
  { slug: "hidden", name: "Audio hidden" },
];
const SORT_OPTIONS = [
  { slug: "recently-approved", name: "Recently approved" },
  { slug: "title", name: "Title" },
  { slug: "author", name: "Author" },
  { slug: "short-reads", name: "Shortest reads" },
];

function readingForm(book = {}) {
  const value = `${book.category_slug || ""} ${book.category || ""} ${book.title || ""} ${book.short_description || ""}`.toLowerCase();
  if (/poem|poetry|essay|verse|কবিতা/.test(value)) return "poetry";
  if (/short|story|গল্প/.test(value)) return "short-story";
  return "novel";
}

function readingMatches(book, value) {
  return value === "all" || readingForm(book) === value;
}

function listeningMatches(book, value) {
  if (value === "all") return true;
  const approved = audiobookReleaseState(book).canShowControls;
  return value === "available" ? approved : !approved;
}

function FilterChips({ label, value, options, onChange, testId }) {
  return (
    <fieldset className="library-explorer__facet" data-testid={testId}>
      <legend>{label}</legend>
      <div className="library-explorer__chips">
        {options.map((option) => (
          <button
            key={option.slug}
            type="button"
            aria-pressed={value === option.slug}
            onClick={() => onChange(option.slug)}
          >
            {option.name}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export default function Library() {
  const [params, setParams] = useSearchParams();
  const [dracula, setDracula] = useState(null);
  const [liveBooks, setLiveBooks] = useState([]);
  const [curation, setCuration] = useState(() => getHomeCurationSnapshot());
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState(params.get("q") || "");
  const language = params.get("language") || "all";
  const reading = params.get("reading") || (params.get("category") && !["all", "live", "pipeline"].includes(params.get("category")) ? params.get("category") : "all");
  const listening = params.get("listening") || (params.get("availability") === "approved-audiobook" ? "available" : "all");
  const sort = params.get("sort") || "recently-approved";

  useSEO({
    title: "Library | Bengali and English Classics on Earnalism",
    description: "Explore Earnalism's Bengali and English classics through one calm, curated collection.",
    image: curation?.featured?.cover_image_url,
    imageAlt: "Earnalism graphical book cover artwork",
    canonicalPath: "/library",
  });

  useEffect(() => {
    const controller = new AbortController();
    Promise.allSettled([
      api.get(`/books/${LIVE_APPROVED_SLUG}`, { signal: controller.signal }),
      api.get("/books", { signal: controller.signal }),
      fetchHomeCuration(controller.signal),
    ]).then(([draculaResult, booksResult, curationResult]) => {
      if (draculaResult.status === "fulfilled") setDracula(draculaResult.value.data);
      setLiveBooks(
        booksResult.status === "fulfilled" && Array.isArray(booksResult.value.data) && booksResult.value.data.length
          ? booksResult.value.data
          : LOCAL_LIBRARY_FALLBACK_BOOKS,
      );
      if (curationResult.status === "fulfilled") setCuration(curationResult.value);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, []);

  const updateParam = (key, value, fallback = "all") => {
    const next = new URLSearchParams(params);
    if (!value || value === fallback) next.delete(key);
    else next.set(key, value);
    if (key === "reading") next.delete("category");
    if (key === "listening") next.delete("availability");
    setParams(next);
  };

  const allBooks = useMemo(() => {
    const bySlug = new Map();
    liveBooks.forEach((book) => book?.slug && bySlug.set(book.slug, book.slug === LIVE_APPROVED_SLUG ? mergeDraculaBook(book) : book));
    if (dracula || bySlug.has(LIVE_APPROVED_SLUG)) bySlug.set(LIVE_APPROVED_SLUG, mergeDraculaBook(dracula || bySlug.get(LIVE_APPROVED_SLUG)));
    PIPELINE_BOOKS.filter((book) => !BATCH_1_READER_ONLY_SLUGS.includes(book.slug)).forEach((book) => {
      if (!bySlug.has(book.slug)) bySlug.set(book.slug, book);
    });
    return Array.from(bySlug.values());
  }, [dracula, liveBooks]);

  const filteredBooks = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return sortLibraryBooks(allBooks.filter((book) => {
      const text = `${book.title || ""} ${book.title_en || ""} ${book.author || ""} ${book.short_description || ""}`.toLowerCase();
      return (!normalized || text.includes(normalized))
        && matchesLibraryFacets(book, language, listening === "available" ? "approved-audiobook" : "all")
        && (listening !== "hidden" || matchesLibraryFacets(book, language, "audio-hidden"))
        && readingMatches(book, reading)
        && listeningMatches(book, listening);
    }), sort);
  }, [allBooks, language, listening, query, reading, sort]);

  const libraryHeroCuration = useMemo(() => ({
    ...curation,
    hero: {
      ...curation?.hero,
      headline: "Find the story that meets you here.",
      subheadline: "Explore Bengali and English classics through one calm, curated collection—filter by language, literary form, access, and listening availability.",
      primary_cta: { label: "EXPLORE THE COLLECTION", url: "#library-collection" },
      secondary_cta: { label: "Explore Audiobooks", url: "/library?availability=approved-audiobook" },
    },
  }), [curation]);

  const handleSearch = (value) => {
    setQuery(value);
    const next = new URLSearchParams(params);
    if (value.trim()) next.set("q", value);
    else next.delete("q");
    setParams(next, { replace: true });
  };

  return (
    <div className="library-page" data-testid="library-page">
      <PremiumHero
        curation={libraryHeroCuration}
        loading={loading}
        error={false}
        headerMode="document"
        analyticsNamespace="library"
        eyebrowLabel="THE EARNALISM LIBRARY"
        fallbackHeadline="Find the story that meets you here."
      />

      <main id="library-collection" className="library-main">
        <section className="library-explorer" aria-labelledby="explorer-title">
          <div className="library-explorer__heading">
            <div>
              <p className="library-overline">THE OPEN SHELF</p>
              <h2 id="explorer-title">Explore the collection.</h2>
              <p>One mixed shelf for Bengali and English classics, with access and listening status kept clear.</p>
            </div>
            <div className="library-explorer__count" aria-live="polite"><Check size={15} aria-hidden="true" /> {filteredBooks.length} editions in view</div>
          </div>
          <div className="library-explorer__toolbar">
            <label className="library-search" htmlFor="library-search-input">
              <span>Search the Library</span>
              <div><Search size={16} aria-hidden="true" /><input id="library-search-input" data-testid="library-search" value={query} onChange={(event) => handleSearch(event.target.value)} placeholder="Search by title or author" /></div>
            </label>
            <label className="library-sort" htmlFor="library-sort-select">
              <span>Arrange</span>
              <select id="library-sort-select" data-testid="library-sort" value={sort} onChange={(event) => updateParam("sort", event.target.value, "recently-approved")}>
                {SORT_OPTIONS.map((option) => <option key={option.slug} value={option.slug}>{option.name}</option>)}
              </select>
            </label>
          </div>
          <div className="library-explorer__filters">
            <FilterChips label="Language" value={language} options={LANGUAGE_FILTERS} onChange={(value) => updateParam("language", value)} testId="language-filters" />
            <FilterChips label="Literary form" value={reading} options={READING_FILTERS} onChange={(value) => updateParam("reading", value)} testId="reading-filters" />
            <FilterChips label="Listening" value={listening} options={LISTENING_FILTERS} onChange={(value) => updateParam("listening", value)} testId="listening-filters" />
          </div>
        </section>

        <section className="library-collection" aria-labelledby="collection-title">
          <div className="library-collection__header">
            <div><p className="library-overline">CURATED EDITIONS</p><h2 id="collection-title">A single shelf, many ways in.</h2></div>
            <p><Headphones size={16} aria-hidden="true" /> Listening appears only where the release evidence allows it.</p>
          </div>
          {loading ? <div className="library-empty" role="status" aria-live="polite">Opening the collection...</div> : filteredBooks.length > 0 ? (
            <div className="library-book-grid" data-testid="library-book-grid">{filteredBooks.map((book, index) => <BookCard key={book.slug} book={book} priority={index < 3} />)}</div>
          ) : (
            <div className="library-empty" data-testid="library-empty"><SlidersHorizontal size={20} aria-hidden="true" /><h3>No editions match these filters.</h3><p>Try removing a filter or searching for another title or author.</p><button type="button" onClick={() => { setQuery(""); setParams(new URLSearchParams()); }}>Clear filters</button></div>
          )}
        </section>

        <aside className="library-pipeline-note" aria-labelledby="pipeline-title">
          <div className="library-pipeline-note__mark" aria-hidden="true">E</div>
          <div><p className="library-overline">THE SHELF KEEPS ITS PROMISE</p><h2 id="pipeline-title">Some stories are still being prepared.</h2><p>Titles in preparation remain visible as invitations, not products. Reader and listening routes open only when their editorial and release checks are complete.</p></div>
          <Link to={notifyUrl("library-release-notes")}>Request an update <ArrowRight size={15} aria-hidden="true" /></Link>
        </aside>
      </main>
    </div>
  );
}
